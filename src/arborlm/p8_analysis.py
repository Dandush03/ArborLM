# ruff: noqa: E501
"""P8 stage "analyse": every paired quantity, guard and classification of ADR-0015 section 7, from the
evaluation and simulation JSON records only (no model, no trace, no layout is touched here).

Layout of this module
  1. SECTION 7.3 / 7.4 -- THRESHOLDS AND CLASSIFICATION RULES. All registered numbers and every rule
     that turns paired quantities into a class live in the one clearly marked block below. If the
     specification's section 7 changes, only that block (and the matching tests) changes.
  2. Exact helpers (Fractions): ratios with explicit undefined reasons, means, geometric mean.
  3. Record access (``CellData``) and completeness (60 cells, both panels, never silently reduced).
  4. Paired quantities (section 7.2) and their conditions grid (2 settings x 2 tie rules).
  5. Per-case classification, study classification, "beats optimized flat", "architecture advantage".
  6. Controls and descriptive tables, CSV and JSON output, CLI.

All miss counts are integers, so m, E and every ratio are ``fractions.Fraction``; boundaries are
decided exactly (equality at a threshold is detected, never rounded). Undefined quantities are
``None`` with a recorded reason and never satisfy an inequality; they are never skipped silently.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import argparse
import csv
import json
import math
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import p7b_core as b_core
from . import p8_core as core
from . import p8_sim
from .io import file_sha256, read_json, write_json
from .p7b_analysis import ols_adjusted
from .records import allocate_run, utc_now

SCHEMA_ANALYSIS = "P8-analysis-v1"
ANALYSIS_PREFIX, ANALYSIS_PREFIX_DRY = "P8A", "P8AD"
PANELS = ("A", "B")
L_COAX, L_BCOAX = b_core.L_COAX, b_core.L_BCOAX
TAGS = (L_COAX, L_BCOAX)  # classification uses L-COAX; L-BCOAX is reported for trees
CONDITIONS = tuple((r, c, tie) for r, c in core.CRITERION_SETTINGS for tie in core.TIES)
NOT_REPLICATED = "NOT REPLICATED ACROSS PANELS"
INCOMPLETE = "INCOMPLETE"

# =====================================================================================================
# SECTION 7.3 / 7.4 -- THRESHOLDS AND CLASSIFICATION RULES (single place)
# =====================================================================================================


def _fr(x: float) -> Fraction:
    return Fraction(str(x))


T_MATERIAL = _fr(core.MATERIAL_RATIO)  # ratio <= 0.80: material improvement
T_BAND_LOW, T_BAND_HIGH = _fr(core.BAND_LOW), _fr(core.BAND_HIGH)  # [0.90, 1.10]: no difference
T_WORSE = _fr(core.WORSE_RATIO)  # ratio >= 1.25: materially worse
T_QUALITY = _fr(core.QUALITY_DELTA)  # delta NLL <= +0.005 nats/byte
T_RETENTION = _fr(
    core.RETENTION_MIN
)  # revision 2: gain retention and association retention >= 0.75
T_NULL_FLOOR = Fraction(
    1, 20
)  # revision 2: E undefined if null mean under L-FREQ < 0.05 misses/query
T_UTIL_RETAINED, T_UTIL_COLLAPSED = core.UTIL_RETAINED, core.UTIL_COLLAPSED  # 0.80 / 0.50 (floats)
MAX_PAIRS_ABOVE = core.QUALITY_PAIRS_ABOVE_MAX  # at most one of six pairs above +0.005
MIN_PAIRS_E_LOWER = 5  # at least five of six pairs with E_c < E_b
PAIRS_EXPECTED, PARENTS_EXPECTED = 6, 3

QUALITY_FAILED = "QUALITY-FAILED"
COLLAPSED = "COLLAPSED"
POSITIVE = "LOCALITY-POSITIVE (screening)"
REDUCED = "LOCALITY WITH REDUCED UTILIZATION"
CONC_ONLY = "CONCENTRATION-ONLY"
NO_DIFF = "NO DIFFERENCE"
WORSE = "WORSE"
INTERMEDIATE = "INTERMEDIATE"


def quality_guard(
    delta_nll_mean: Fraction | None,
    pairs_above: int | None,
    gain_retention: Fraction | None,
    association_retention: Fraction | None,
) -> dict[str, Any]:
    """Quality guard (7.3, all four): mean dNLL <= +0.005; at most one of six pairs above +0.005;
    gain retention >= 0.75; association retention >= 0.75. Any undefined input fails the guard."""
    if None in (delta_nll_mean, pairs_above, gain_retention, association_retention):
        return {
            "passes": False,
            "reason": "undefined input (e.g. a retention with a baseline mean <= 0)",
            "undefined": [
                n
                for n, v in (
                    ("delta_nll_mean", delta_nll_mean),
                    ("pairs_above", pairs_above),
                    ("gain_retention", gain_retention),
                    ("association_retention", association_retention),
                )
                if v is None
            ],
        }
    assert delta_nll_mean is not None and pairs_above is not None
    assert gain_retention is not None and association_retention is not None
    checks = {
        "mean_delta_ok": delta_nll_mean <= T_QUALITY,
        "at_most_one_pair_above_ok": pairs_above <= MAX_PAIRS_ABOVE,
        "gain_retention_ok": gain_retention >= T_RETENTION,
        "association_retention_ok": association_retention >= T_RETENTION,
    }
    return {"passes": all(checks.values()), **checks}


def utilization_guard(u_ratio: float | None) -> str:
    """Utilization guard (7.3): >= 0.80 retained; [0.50, 0.80) reduced; < 0.50 collapsed."""
    if u_ratio is None:
        return "undefined"
    if u_ratio >= T_UTIL_RETAINED:
        return "retained"
    return "reduced" if u_ratio >= T_UTIL_COLLAPSED else "collapsed"


def _le(x: Fraction | None, bound: Fraction) -> bool:
    return x is not None and x <= bound


def _within(x: Fraction | None) -> bool:
    return x is not None and T_BAND_LOW <= x <= T_BAND_HIGH


def _ge(x: Fraction | None, bound: Fraction) -> bool:
    return x is not None and x >= bound


def classify_case(
    quality_passes: bool, u_ratio: float | None, conditions: list[dict[str, Any]]
) -> tuple[str, dict[str, Any]]:
    """Section 7.4 (revision 2), evaluated in registered order; the first rule that applies is taken.

    ``conditions`` has one entry per (setting, tie rule) -- four -- each with ``m_ratio``,
    ``e_ratio``, ``rho_adj`` (Fractions or None), ``pairs_e_lower`` (int, of six) and
    ``parents_e_below_one`` (int, of three)."""
    why: dict[str, Any] = {
        "quality_guard_passes": quality_passes,
        "u_ratio": u_ratio,
        "undefined_conditions": [
            i
            for i, c in enumerate(conditions)
            if c["m_ratio"] is None or c["e_ratio"] is None or c["rho_adj"] is None
        ],
    }
    if not quality_passes:
        return QUALITY_FAILED, why
    if u_ratio is not None and u_ratio < T_UTIL_COLLAPSED:
        return COLLAPSED, why
    loc = all(
        _le(c["m_ratio"], T_MATERIAL)
        and _le(c["e_ratio"], T_MATERIAL)
        and _le(c["rho_adj"], T_MATERIAL)
        and c["pairs_e_lower"] >= MIN_PAIRS_E_LOWER
        and c["parents_e_below_one"] == PARENTS_EXPECTED
        for c in conditions
    )
    why["loc"] = loc
    if loc:
        if u_ratio is None:
            return INTERMEDIATE, why  # rule 8: LOC holds but the utilization class is undefined
        return (POSITIVE if u_ratio >= T_UTIL_RETAINED else REDUCED), why
    if all(_le(c["m_ratio"], T_MATERIAL) for c in conditions):
        return CONC_ONLY, why
    if all(_within(c["m_ratio"]) and _within(c["e_ratio"]) for c in conditions):
        return NO_DIFF, why
    if all(_ge(c["m_ratio"], T_WORSE) for c in conditions) or all(
        _ge(c["e_ratio"], T_WORSE) for c in conditions
    ):
        return WORSE, why
    return INTERMEDIATE, why


def study_class(class_a: str, class_b: str) -> dict[str, Any]:
    """A case's study classification is its Panel A class if Panel B gives the same class;
    otherwise NOT REPLICATED ACROSS PANELS with both shown."""
    if class_a == class_b:
        return {"class": class_a, "panel_A": class_a, "panel_B": class_b}
    return {"class": NOT_REPLICATED, "panel_A": class_a, "panel_B": class_b}


def _all_le(table: dict[str, dict[str, Any]], key: str) -> bool:
    return all(_le(table[p][i][key], T_MATERIAL) for p in PANELS for i in table[p])


def beats_optimized_flat(
    study: str, vs_c01: dict[str, dict[str, Any]], delta_nll_vs_c01: dict[str, Fraction | None]
) -> dict[str, Any]:
    """LOCALITY-POSITIVE (study level, both panels); M-ratio, E-ratio and utilization-adjusted
    E-ratio against C01 under L-COAX all <= 0.80 (defined) at both settings, both tie rules, both
    panels; dNLL against C01 <= +0.005 on both panels. U-ratio is reported, not a condition."""
    ratios = {k: _all_le(vs_c01, k) for k in ("m_ratio", "e_ratio", "rho_adj")}
    q_ok = all(_le(delta_nll_vs_c01[p], T_QUALITY) for p in PANELS)
    return {
        "holds": study == POSITIVE and all(ratios.values()) and q_ok,
        "study_is_locality_positive": study == POSITIVE,
        "ratios_vs_c01_le_0_80_everywhere": ratios,
        "delta_nll_vs_c01_le_0_005_both_panels": q_ok,
    }


def architecture_advantage(
    beats: bool, vs_flat: dict[str, dict[str, Any]], delta_nll_vs_flat: dict[str, Fraction | None]
) -> dict[str, Any]:
    """Tree case: beats optimized flat AND the same three ratios against its flat counterpart
    <= 0.80 under the same conditions, with dNLL against the counterpart <= +0.005 (both panels)."""
    ratios = {k: _all_le(vs_flat, k) for k in ("m_ratio", "e_ratio", "rho_adj")}
    q_ok = all(_le(delta_nll_vs_flat[p], T_QUALITY) for p in PANELS)
    return {
        "holds": beats and all(ratios.values()) and q_ok,
        "beats_optimized_flat": beats,
        "ratios_vs_flat_le_0_80_everywhere": ratios,
        "delta_nll_vs_flat_le_0_005_both_panels": q_ok,
    }


def concentration_controls_bind(classes: dict[str, dict[str, str]]) -> bool:
    """True if C04 or C05 is itself LOCALITY-POSITIVE on either panel (review M4)."""
    return any(classes[p].get(c) == POSITIVE for p in PANELS for c in ("C04", "C05"))


def decision_option(
    bind: bool,
    study_complete: bool,
    arch: list[str],
    flat_beats: list[str],
) -> tuple[str, str]:
    """Section 8's decision map, mechanically (lead ruling). (a) iff C07 or C09 has an architecture
    advantage and the concentration controls do not bind; else (b) iff C06 or C08 is
    LOCALITY-POSITIVE and beats optimized flat, no tree case has an architecture advantage, and the
    controls do not bind; else (c). The choice stays human."""
    if not study_complete:
        return "none", "INCOMPLETE study: no option is derived"
    if bind:
        return "c", "concentration controls bind (C04 or C05 LOCALITY-POSITIVE): (c)"
    if arch:
        return "a", f"architecture advantage: {', '.join(arch)}"
    if flat_beats:
        return (
            "b",
            f"flat case beats optimized flat, no tree architecture advantage: {', '.join(flat_beats)}",
        )
    return "c", "no flat case beats optimized flat and no tree case has an architecture advantage"


# =====================================================================================================
# exact helpers
# =====================================================================================================
def fmean(values: list[Fraction]) -> Fraction:
    return sum(values, Fraction(0)) / len(values)


def ratio(
    num: Fraction | None, den: Fraction | None, what: str
) -> tuple[Fraction | None, str | None]:
    """num / den with an explicit reason when it is undefined (never a silent skip)."""
    if num is None or den is None:
        return None, f"{what}: undefined input"
    if den == 0:
        return None, f"{what}: denominator is zero"
    return num / den, None


def retention(
    case_mean: Fraction, baseline_mean: Fraction, what: str, noun: str
) -> tuple[Fraction | None, str | None]:
    """Retention = case mean / baseline mean; UNDEFINED when the baseline mean is <= 0 (ADR-0015
    revision 2 ruling). An undefined retention fails the quality guard."""
    if baseline_mean <= 0:
        return None, f"{what}: baseline mean {noun} <= 0 (undefined; fails the quality guard)"
    return case_mean / baseline_mean, None


def fl(x: Fraction | None) -> float | None:
    return None if x is None else float(x)


def fstr(x: Fraction | None) -> str | None:
    return None if x is None else f"{x.numerator}/{x.denominator}"


def geometric_mean_ratio(nums: list[float], dens: list[float]) -> tuple[float | None, str | None]:
    """exp(mean(ln(n/d))); undefined if any value is not positive."""
    if any(v <= 0 for v in nums) or any(v <= 0 for v in dens):
        return None, "geometric mean: a non-positive N_eff"
    return math.exp(
        math.fsum(math.log(n / d) for n, d in zip(nums, dens, strict=True)) / len(nums)
    ), None


# =====================================================================================================
# record access
# =====================================================================================================
class CellData:
    """One cell's evaluation and simulation records."""

    def __init__(self, cell: core.Cell, eval_record: dict[str, Any], sim_record: dict[str, Any]):
        self.cell, self.eval, self.sim = cell, eval_record, sim_record

    @property
    def key(self) -> tuple[int, int, int]:
        return (self.cell.backbone, self.cell.order, self.cell.seed)

    # quality
    def nll(self, panel: str, step: str = "step512", cond: str = "enabled") -> Fraction:
        return Fraction(self.eval["nll"][step][cond][panel])

    def gain(self, panel: str) -> Fraction:
        return self.nll(panel, "step512", "disabled") - self.nll(panel)

    def value_effect(self, panel: str) -> Fraction:
        return self.nll(panel, "step512", "values_permuted") - self.nll(panel)

    # utilization
    def util(self, panel: str) -> dict[str, Any]:
        return dict(self.eval["traces"][panel]["utilization"])

    # simulation
    def m(self, panel: str, rows: int, tie: str, layout: str, stream: str = "actual") -> Fraction:
        return p8_sim.m_fraction(self.sim["panels"][panel], stream, layout, rows, tie)

    def counts(
        self, panel: str, rows: int, tie: str, layout: str, stream: str = "actual"
    ) -> dict[str, Any]:
        group = self.sim["panels"][panel]["streams"][stream][b_core.layout_key(layout, rows)]
        return dict(group["by_c"][str(p8_sim.CAP_FOR_ROWS[rows])][tie])

    def pages_per_query(self, panel: str, rows: int, layout: str) -> float | None:
        group = self.sim["panels"][panel]["streams"]["actual"][b_core.layout_key(layout, rows)]
        pages = group.get("stats", {}).get("pages_sum")
        return None if pages is None else pages / int(self.sim["panels"][panel]["queries"])

    def has_layout(self, panel: str, rows: int, layout: str) -> bool:
        key = b_core.layout_key(layout, rows)
        return key in self.sim["panels"][panel]["streams"]["actual"]

    def null_mean(self, panel: str, rows: int, tie: str, layout: str) -> Fraction:
        return fmean([self.m(panel, rows, tie, layout, s) for s in b_core.STREAMS_NULL])

    def e(self, panel: str, rows: int, tie: str, layout: str) -> tuple[Fraction | None, str | None]:
        """E(L) = m(actual, L) / mean m(three nulls, L-FREQ)."""
        null = self.null_mean(panel, rows, tie, b_core.L_FREQ)
        if null < T_NULL_FLOOR:
            return (
                None,
                f"E({layout}) R{rows} {tie}: null mean {float(null):.4g} < 0.05 (undefined)",
            )
        return ratio(self.m(panel, rows, tie, layout), null, f"E({layout}) R{rows} {tie}")

    def reuse(self, panel: str) -> dict[str, Any]:
        t = self.sim["panels"][panel]["temporal_reuse"]
        nulls = [t[s]["value"] for s in b_core.STREAMS_NULL]
        null_mean = math.fsum(nulls) / len(nulls)
        return {
            "actual": t["actual"]["value"],
            "order_shuffled": t["order_shuffled"]["value"],
            "null_mean": null_mean,
            "ratio_to_null": None if null_mean == 0 else t["actual"]["value"] / null_mean,
        }

    def persistence(self, panel: str) -> dict[str, Any] | None:
        p = self.sim["panels"][panel]["branch_persistence"]
        if p is None:
            return None

        def r(a: float, b: float) -> float | None:
            return None if b == 0 else a / b

        return {
            "top_actual": p["actual"]["top_fraction"],
            "top_order_shuffled": p["order_shuffled"]["top_fraction"],
            "top_ratio": r(p["actual"]["top_fraction"], p["order_shuffled"]["top_fraction"]),
            "pair_actual": p["actual"]["pair_fraction"],
            "pair_order_shuffled": p["order_shuffled"]["pair_fraction"],
            "pair_ratio": r(p["actual"]["pair_fraction"], p["order_shuffled"]["pair_fraction"]),
        }


def check_provenance(
    eval_manifest: dict[str, Any],
    sim_manifest: dict[str, Any],
    records: list[tuple[str, dict[str, Any]]],
    dry_run: bool,
) -> dict[str, Any]:
    """Refuse unless the stage manifests and every record share one source hash, spec hash and
    dry-run flag, every eval record shares the panel-record hash of the eval manifest, and (registered
    runs) both manifests carry the same freeze commit. Raises ``GateError``; never skipped."""
    problems: list[str] = []
    for name, manifest in (("eval", eval_manifest), ("sim", sim_manifest)):
        if bool(manifest.get("dry_run")) != dry_run:
            problems.append(f"{name} manifest dry_run flag differs from this analysis")
    for key in ("source_sha256", "spec_sha256"):
        values = {eval_manifest.get(key), sim_manifest.get(key)}
        values |= {rec.get(key) for _, rec in records}
        if len(values) != 1 or None in values:
            problems.append(
                f"{key} is not one value across manifests and records: {sorted(map(str, values))}"
            )
    for label, rec in records:
        if bool(rec.get("dry_run")) != dry_run:
            problems.append(f"{label}: record dry_run flag differs")
    panel_hashes = {
        rec.get("panel_record_sha256") for label, rec in records if label.startswith("eval:")
    }
    if panel_hashes and panel_hashes != {eval_manifest.get("panel_record_sha256")}:
        problems.append("eval records do not share the eval manifest's panel-record hash")
    freezes = {(m.get("freeze") or {}).get("freeze_commit") for m in (eval_manifest, sim_manifest)}
    if not dry_run and (len(freezes) != 1 or None in freezes):
        problems.append("eval and sim manifests do not carry one freeze commit")
    if problems:
        raise b_core.GateError("refused: inconsistent provenance: " + "; ".join(problems[:5]))
    return {
        "source_sha256": eval_manifest.get("source_sha256"),
        "spec_sha256": eval_manifest.get("spec_sha256"),
        "panel_record_sha256": eval_manifest.get("panel_record_sha256"),
        "freeze_commit": None if dry_run else next(iter(freezes)),
    }


def load_cells(
    eval_run: Path, sim_run: Path, dry_run: bool | None = None
) -> tuple[dict[str, CellData], list[dict[str, Any]]]:
    """Every cell with a completed evaluation and simulation record, and the list of missing ones
    (with the reason). The 60-cell denominator is the registry's, never the number of files found.
    With ``dry_run`` given, the provenance of manifests and records is checked first."""
    cells: dict[str, CellData] = {}
    missing: list[dict[str, Any]] = []
    for cell in core.cells():
        reasons: list[str] = []
        e_path = eval_run / "cells" / cell.label / "eval.json"
        s_path = sim_run / "cells" / cell.label / "sim.json"
        e_rec = s_rec = None
        if not e_path.is_file():
            reasons.append("eval.json missing")
        else:
            e_rec = read_json(e_path)
            if e_rec.get("outcome") != "completed":
                reasons.append("eval record not completed")
        if not s_path.is_file():
            reasons.append("sim.json missing")
        else:
            s_rec = read_json(s_path)
            if s_rec.get("outcome") != "completed" or set(s_rec.get("panels", {})) != set(PANELS):
                reasons.append("sim record not completed for both panels")
        if not reasons and e_rec is not None and s_rec is not None:
            if s_rec["eval_json_sha256"] != file_sha256(e_path):
                reasons.append("sim.json was built from a different eval.json")
        if reasons or e_rec is None or s_rec is None:
            missing.append({"label": cell.label, "reasons": reasons})
        else:
            cells[cell.label] = CellData(cell, e_rec, s_rec)
    if dry_run is not None:
        records = [(f"eval:{c.cell.label}", c.eval) for c in cells.values()]
        records += [(f"sim:{c.cell.label}", c.sim) for c in cells.values()]
        check_provenance(
            read_json(eval_run / "manifest.json"),
            read_json(sim_run / "manifest.json"),
            records,
            dry_run,
        )
    return cells, missing


# =====================================================================================================
# paired quantities (section 7.2)
# =====================================================================================================
def _pair_cells(
    cells: dict[str, CellData], case: str, ref: str
) -> tuple[list[tuple[CellData, CellData]], list[str]]:
    """The six (parent, seed) pairs of ``case`` against ``ref``; the labels of any missing cells."""
    pairs: list[tuple[CellData, CellData]] = []
    missing: list[str] = []
    for backbone, order in core.PARENTS:
        for seed in core.SEEDS:
            c = core.Cell(backbone, order, seed, case)
            r = core.Cell(backbone, order, seed, ref)
            absent = [x.label for x in (c, r) if x.label not in cells]
            if absent:
                missing += absent
            else:
                pairs.append((cells[c.label], cells[r.label]))
    return pairs, missing


def layouts_for(tag: str, case_kind: str, ref_kind: str) -> tuple[str, str]:
    """(layout of the case, layout of the reference) for a tag. L-COAX: both L-COAX. L-BCOAX: a tree
    uses L-BCOAX, a flat memory has none and uses L-COAX (ADR-0014's tree-layout-versus-flat-layout
    pairing)."""
    if tag == L_COAX:
        return L_COAX, L_COAX
    return (
        L_BCOAX if case_kind != "flat" else L_COAX,
        L_BCOAX if ref_kind != "flat" else L_COAX,
    )


def paired_condition(
    pairs: list[tuple[CellData, CellData]],
    panel: str,
    rows: int,
    cap: int,
    tie: str,
    layout_c: str,
    layout_r: str,
) -> dict[str, Any]:
    """M-ratio, E-ratio, utilization-adjusted E-ratio and pair/parent counts for one condition."""
    reasons: list[str] = []
    m_c = [c.m(panel, rows, tie, layout_c) for c, _ in pairs]
    m_r = [r.m(panel, rows, tie, layout_r) for _, r in pairs]
    e_c_all = [c.e(panel, rows, tie, layout_c) for c, _ in pairs]
    e_r_all = [r.e(panel, rows, tie, layout_r) for _, r in pairs]
    for _, why in (*e_c_all, *e_r_all):
        if why and why not in reasons:
            reasons.append(why)
    m_ratio, why = ratio(fmean(m_c), fmean(m_r), "M-ratio")
    if why:
        reasons.append(why)
    out: dict[str, Any] = {
        "R": rows,
        "C": cap,
        "tie": tie,
        "layout_case": layout_c,
        "layout_reference": layout_r,
        "pairs": len(pairs),
        "m_case_mean": fl(fmean(m_c)),
        "m_reference_mean": fl(fmean(m_r)),
        "m_ratio": m_ratio,
        "m_ratio_exact": fstr(m_ratio),
        "pairs_m_lower": sum(1 for a, b in zip(m_c, m_r, strict=True) if a < b),
    }
    e_defined = all(v is not None for v, _ in (*e_c_all, *e_r_all))
    e_ratio: Fraction | None = None
    rho_adj: Fraction | None = None
    if e_defined:
        e_c = [v for v, _ in e_c_all if v is not None]
        e_r = [v for v, _ in e_r_all if v is not None]
        e_ratio, why = ratio(fmean(e_c), fmean(e_r), "E-ratio")
        if why:
            reasons.append(why)
        out.update(
            e_case_mean=fl(fmean(e_c)),
            e_reference_mean=fl(fmean(e_r)),
            pairs_e_lower=sum(1 for a, b in zip(e_c, e_r, strict=True) if a < b),
        )
        keys = [r.key for _, r in pairs]
        x_c = {c.key: float(c.util(panel)["entropy_nats"]) for c, _ in pairs}
        x_r = {r.key: float(r.util(panel)["entropy_nats"]) for _, r in pairs}
        overlap = max(min(x_c.values()), min(x_r.values())) <= min(
            max(x_c.values()), max(x_r.values())
        )
        if overlap:
            fit = ols_adjusted(
                dict(zip(keys, e_r, strict=True)), dict(zip(keys, e_c, strict=True)), x_r, x_c
            )
            rho_adj = fit.pop("_rho_adj", None)
            if rho_adj is None:
                reasons.append(f"utilization-adjusted E-ratio undefined: {fit.get('reason')}")
        else:
            fit = {"defined": False, "reason": "ranges of ln N_eff do not overlap"}
            reasons.append(
                "utilization-adjusted E-ratio undefined: ranges of ln N_eff do not overlap"
            )
        out["adjustment"] = fit
        parents: dict[tuple[int, int], list[int]] = {}
        for i, (c, _) in enumerate(pairs):
            parents.setdefault((c.cell.backbone, c.cell.order), []).append(i)
        below = 0
        for idx in parents.values():
            pr, _ = ratio(
                fmean([e_c[i] for i in idx]), fmean([e_r[i] for i in idx]), "parent E-ratio"
            )
            below += pr is not None and pr < 1
        out["parents_e_below_one"] = below
    else:
        out.update(e_case_mean=None, e_reference_mean=None, pairs_e_lower=0, parents_e_below_one=0)
        reasons.append(
            "E undefined for at least one checkpoint (null mean under L-FREQ below 0.05)"
        )
    parents_m: dict[tuple[int, int], list[int]] = {}
    for i, (c, _) in enumerate(pairs):
        parents_m.setdefault((c.cell.backbone, c.cell.order), []).append(i)
    out["parents_m_below_one"] = sum(
        1
        for idx in parents_m.values()
        if fmean([m_c[i] for i in idx]) < fmean([m_r[i] for i in idx])
    )
    out.update(
        e_ratio=e_ratio,
        e_ratio_exact=fstr(e_ratio),
        rho_adj=rho_adj,
        rho_adj_exact=fstr(rho_adj),
        undefined_reasons=reasons,
    )
    return out


def paired_quality(pairs: list[tuple[CellData, CellData]], panel: str) -> dict[str, Any]:
    deltas = [c.nll(panel) - r.nll(panel) for c, r in pairs]
    gains = [c.gain(panel) for c, _ in pairs]
    effects = [c.value_effect(panel) for c, _ in pairs]
    gains_r = [r.gain(panel) for _, r in pairs]
    effects_r = [r.value_effect(panel) for _, r in pairs]
    gain_ret, why_g = retention(fmean(gains), fmean(gains_r), "gain retention", "gain")
    assoc_ret, why_a = retention(
        fmean(effects), fmean(effects_r), "association retention", "effect"
    )
    breadth_c = [float(c.util(panel)["context_breadth_mean"]) for c, _ in pairs]
    breadth_r = [float(r.util(panel)["context_breadth_mean"]) for _, r in pairs]
    n_c = [float(c.util(panel)["n_eff"]) for c, _ in pairs]
    n_r = [float(r.util(panel)["n_eff"]) for _, r in pairs]
    u, why = geometric_mean_ratio(n_c, n_r)
    parent_idx: dict[tuple[int, int], list[int]] = {}
    for i, (c, _) in enumerate(pairs):
        parent_idx.setdefault((c.cell.backbone, c.cell.order), []).append(i)
    above = sum(1 for d in deltas if d > T_QUALITY)
    return {
        "pairs": len(pairs),
        "delta_nll_mean": fl(fmean(deltas)),
        "delta_nll_mean_exact": fstr(fmean(deltas)),
        "_delta_nll_mean": fmean(deltas),
        "delta_nll_per_pair": [float(d) for d in deltas],
        "pairs_delta_nll_above_0_005": above,
        "memory_gain_mean": fl(fmean(gains)),
        "memory_gain_reference_mean": fl(fmean(gains_r)),
        "gain_retention": gain_ret,
        "value_association_effect_mean": fl(fmean(effects)),
        "value_association_effect_reference_mean": fl(fmean(effects_r)),
        "association_retention": assoc_ret,
        "retention_undefined_reasons": [w for w in (why_g, why_a) if w],
        "context_breadth_case_mean": math.fsum(breadth_c) / len(breadth_c),
        "context_breadth_reference_mean": math.fsum(breadth_r) / len(breadth_r),
        "context_breadth_ratio": (
            None if math.fsum(breadth_r) == 0 else math.fsum(breadth_c) / math.fsum(breadth_r)
        ),
        "u_ratio": u,
        "u_ratio_undefined_reason": why,
        "utilization_guard": utilization_guard(u),
        "n_eff_case_mean": math.fsum(n_c) / len(n_c),
        "n_eff_reference_mean": math.fsum(n_r) / len(n_r),
        "quality_guard": quality_guard(fmean(deltas), above, gain_ret, assoc_ret),
    }


def compare(
    cells: dict[str, CellData], case: str, ref: str, panel: str, tags: tuple[str, ...]
) -> dict[str, Any]:
    """All paired quantities of ``case`` against ``ref`` on one panel: quality/utilization once, and
    the criterion conditions (two settings x two tie rules) under each tag."""
    pairs, missing = _pair_cells(cells, case, ref)
    base: dict[str, Any] = {
        "case": case,
        "reference": ref,
        "panel": panel,
        "pairs_expected": PAIRS_EXPECTED,
        "pairs_available": len(pairs),
        "missing_cells": missing,
    }
    if missing or len(pairs) != PAIRS_EXPECTED:
        return {**base, "status": INCOMPLETE}
    kind_c, kind_r = core.CASE_VARIANT[case], core.CASE_VARIANT[ref]
    out: dict[str, Any] = {
        **base,
        "status": "complete",
        "quality": paired_quality(pairs, panel),
        "tags": {},
    }
    for tag in tags:
        if tag == L_BCOAX and kind_c == "flat":
            continue
        lc, lr = layouts_for(tag, kind_c, kind_r)
        out["tags"][tag] = {
            f"R{r}|C{c}|{tie}": paired_condition(pairs, panel, r, c, tie, lc, lr)
            for r, c, tie in CONDITIONS
        }
    return out


def _conditions(comp: dict[str, Any], tag: str = L_COAX) -> list[dict[str, Any]]:
    return list(comp["tags"][tag].values())


# =====================================================================================================
# per-case classification
# =====================================================================================================
def classify_regularized(
    cells: dict[str, CellData], case: str, panel: str
) -> tuple[str, dict[str, Any]]:
    ref = core.CASE_BASELINE[case]
    comp = compare(cells, case, ref, panel, (L_COAX, L_BCOAX))
    if comp["status"] != "complete":
        return INCOMPLETE, {"comparison": comp}
    quality = comp["quality"]
    label, why = classify_case(
        bool(quality["quality_guard"]["passes"]), quality["u_ratio"], _conditions(comp)
    )
    return label, {"comparison": comp, "rule_trace": why}


def jsonable(obj: Any) -> Any:
    """Replace Fractions by their float value and exact string, and drop private (``_``) keys."""
    if isinstance(obj, Fraction):
        return {"value": float(obj), "exact": fstr(obj)}
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, list | tuple):
        return [jsonable(v) for v in obj]
    return obj


def flat_ratios(comp: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {k: v for k, v in comp["tags"][L_COAX].items()}


def case_means(cells: dict[str, CellData], case: str, panel: str) -> dict[str, Any]:
    """Per-case means over the six cells (descriptive)."""
    members = [cells[c.label] for c in core.cells() if c.case == case and c.label in cells]
    out: dict[str, Any] = {"cells": len(members), "cells_expected": PAIRS_EXPECTED}
    if not members:
        return out

    def avg(fn: Any) -> float | None:
        values = [fn(m) for m in members]
        if any(v is None for v in values):
            return None
        return math.fsum(float(v) for v in values) / len(values)

    out.update(
        nll_step0=avg(lambda m: m.nll(panel, "step0", "enabled")),
        nll=avg(lambda m: m.nll(panel)),
        nll_disabled=avg(lambda m: m.nll(panel, "step512", "disabled")),
        nll_values_permuted=avg(lambda m: m.nll(panel, "step512", "values_permuted")),
        memory_gain=avg(lambda m: m.gain(panel)),
        value_association_effect=avg(lambda m: m.value_effect(panel)),
        n_eff=avg(lambda m: m.util(panel)["n_eff"]),
        distinct_slots=avg(lambda m: m.util(panel)["distinct_slots"]),
        hot64_share=avg(lambda m: m.util(panel)["hot64_share"]),
        context_breadth=avg(lambda m: m.util(panel)["context_breadth_mean"]),
        temporal_reuse=avg(lambda m: m.reuse(panel)["actual"]),
        temporal_reuse_null=avg(lambda m: m.reuse(panel)["null_mean"]),
        temporal_reuse_ratio_to_null=avg(lambda m: m.reuse(panel)["ratio_to_null"]),
    )
    if core.CASE_VARIANT[case] != "flat":
        out.update(
            distinct_branches=avg(lambda m: m.util(panel)["branches"]["distinct_visited"]),
            n_eff_branches=avg(lambda m: m.util(panel)["branches"]["n_eff"]),
            top_branch_share=avg(lambda m: m.util(panel)["branches"]["top_branch_share"]),
            branch_persistence_top=avg(lambda m: (m.persistence(panel) or {}).get("top_actual")),
            branch_persistence_top_ratio=avg(
                lambda m: (m.persistence(panel) or {}).get("top_ratio")
            ),
            branch_persistence_pair=avg(lambda m: (m.persistence(panel) or {}).get("pair_actual")),
            branch_persistence_pair_ratio=avg(
                lambda m: (m.persistence(panel) or {}).get("pair_ratio")
            ),
        )
    layouts: dict[str, Any] = {}
    for r, c, tie in CONDITIONS:
        entry: dict[str, Any] = {}
        names = [b_core.L_ID, b_core.L_FREQ, L_COAX, *b_core.L_PCOAX]
        if core.CASE_VARIANT[case] != "flat":
            names.append(L_BCOAX)
        for name in names:
            m_vals = [m.m(panel, r, tie, name) for m in members]
            e_vals = [m.e(panel, r, tie, name)[0] for m in members]
            entry[name] = {
                "m_mean": float(fmean(m_vals)),
                "E_mean": None
                if any(v is None for v in e_vals)
                else float(fmean([v for v in e_vals if v is not None])),
            }
        entry["null_L-FREQ_mean"] = float(
            fmean([m.null_mean(panel, r, tie, b_core.L_FREQ) for m in members])
        )
        entry["null_L-COAX_mean"] = float(
            fmean([m.null_mean(panel, r, tie, L_COAX) for m in members])
        )
        layouts[f"R{r}|C{c}|{tie}"] = entry
    out["layouts"] = layouts
    return out


def controls(cells: dict[str, CellData], case: str, panel: str) -> dict[str, Any]:
    """Arbitrary-partition control and trained-in layout ratio (reported, enter no class)."""
    members = [cells[c.label] for c in core.cells() if c.case == case and c.label in cells]
    out: dict[str, Any] = {"cells": len(members)}
    if len(members) != PAIRS_EXPECTED:
        out["status"] = INCOMPLETE
        return out
    tree = core.CASE_VARIANT[case] != "flat"
    for r, c, tie in CONDITIONS:
        coax = fmean([m.m(panel, r, tie, L_COAX) for m in members])
        part = fmean([fmean([m.m(panel, r, tie, n) for n in b_core.L_PCOAX]) for m in members])
        ident = fmean([m.m(panel, r, tie, b_core.L_ID) for m in members])
        entry: dict[str, Any] = {}
        v, why = ratio(part, coax, "mean L-PCOAX / L-COAX")
        entry["partition_over_coax"] = fl(v)
        v2, why2 = ratio(ident, coax, "L-ID / L-COAX")
        entry["id_over_coax"] = fl(v2)
        entry["trained_in_layout_reported"] = case in ("C06", "C07", "C10")
        reasons = [w for w in (why, why2) if w]
        if tree:
            bco = fmean([m.m(panel, r, tie, L_BCOAX) for m in members])
            v3, why3 = ratio(bco, part, "L-BCOAX / mean L-PCOAX")
            entry["bcoax_over_partition"] = fl(v3)
            if why3:
                reasons.append(why3)
        entry["undefined_reasons"] = reasons
        out[f"R{r}|C{c}|{tie}"] = entry
    return out


def analyse(cells: dict[str, CellData], missing: list[dict[str, Any]]) -> dict[str, Any]:
    status = "COMPLETE" if not missing else "INCOMPLETE"
    result: dict[str, Any] = {
        "schema": SCHEMA_ANALYSIS,
        "study_status": status,
        "cells_expected": len(core.cells()),
        "cells_with_complete_records": len(cells),
        "missing_cells": missing,
        "thresholds": {
            "material": fstr(T_MATERIAL),
            "band": [fstr(T_BAND_LOW), fstr(T_BAND_HIGH)],
            "worse": fstr(T_WORSE),
            "quality_delta": fstr(T_QUALITY),
            "retention_min": fstr(T_RETENTION),
            "null_floor_misses_per_query": fstr(T_NULL_FLOOR),
            "utilization": [T_UTIL_RETAINED, T_UTIL_COLLAPSED],
            "min_pairs_e_lower": MIN_PAIRS_E_LOWER,
        },
        "conditions": [f"R{r}|C{c}|{tie}" for r, c, tie in CONDITIONS],
        "classification_layout": L_COAX,
        "panels": {},
        "cases": {},
    }
    regularized = list(core.CASE_BASELINE)
    classes: dict[str, dict[str, str]] = {p: {} for p in PANELS}
    traces: dict[str, dict[str, Any]] = {p: {} for p in PANELS}
    for panel in PANELS:
        for case in regularized:
            label, detail = classify_regularized(cells, case, panel)
            classes[panel][case] = label
            traces[panel][case] = detail
    for case in core.CASES:
        entry: dict[str, Any] = {
            "architecture": core.CASE_VARIANT[case],
            "objective": list(core.CASE_OBJECTIVE[case]),
            "baseline": core.CASE_BASELINE.get(case),
            "flat_counterpart": core.CASE_FLAT_COUNTERPART.get(case),
            "panels": {},
        }
        for panel in PANELS:
            pe: dict[str, Any] = {
                "means": case_means(cells, case, panel),
                "controls": controls(cells, case, panel),
            }
            if case in core.CASE_BASELINE:
                detail = traces[panel][case]
                pe["classification"] = classes[panel][case]
                pe["rule_trace"] = detail.get("rule_trace")
                pe["vs_baseline"] = detail["comparison"]
            refs: dict[str, str] = {}
            if case in core.CASE_FLAT_COUNTERPART:
                refs["flat_counterpart"] = core.CASE_FLAT_COUNTERPART[case]
            if case == "C10":
                refs = {"flat_counterpart_C06": "C06", "flat_counterpart_C08": "C08"}
            if case != "C01":
                refs["c01"] = "C01"
            pe["vs_other"] = {
                name: compare(cells, case, ref, panel, (L_COAX, L_BCOAX))
                for name, ref in refs.items()
            }
            entry["panels"][panel] = pe
        if case in core.CASE_BASELINE:
            study = study_class(classes["A"][case], classes["B"][case])
            entry["study_classification"] = study
            vs_c01 = {
                p: {k: v for k, v in flat_ratios(entry["panels"][p]["vs_other"]["c01"]).items()}
                if entry["panels"][p]["vs_other"]["c01"]["status"] == "complete"
                else {}
                for p in PANELS
            }
            complete = all(vs_c01[p] for p in PANELS)
            d_c01 = {
                p: entry["panels"][p]["vs_other"]["c01"].get("quality", {}).get("_delta_nll_mean")
                for p in PANELS
            }
            beats = (
                beats_optimized_flat(study["class"], vs_c01, d_c01)
                if complete
                else {"holds": False, "status": INCOMPLETE}
            )
            entry["beats_optimized_flat"] = beats
            tree_with_flat = (
                case in core.CASE_FLAT_COUNTERPART and core.CASE_VARIANT[case] != "flat"
            )
            if tree_with_flat:
                vs_flat = {
                    p: flat_ratios(entry["panels"][p]["vs_other"]["flat_counterpart"])
                    if entry["panels"][p]["vs_other"]["flat_counterpart"]["status"] == "complete"
                    else {}
                    for p in PANELS
                }
                d_flat = {
                    p: entry["panels"][p]["vs_other"]["flat_counterpart"]
                    .get("quality", {})
                    .get("_delta_nll_mean")
                    for p in PANELS
                }
                entry["architecture_advantage"] = (
                    architecture_advantage(bool(beats["holds"]), vs_flat, d_flat)
                    if all(vs_flat[p] for p in PANELS)
                    else {"holds": False, "status": INCOMPLETE}
                )
            else:
                entry["architecture_advantage"] = {
                    "holds": False,
                    "reason": "no flat counterpart (flat case or C10)",
                }
        result["cases"][case] = entry
    result["concentration_controls_bind"] = concentration_controls_bind(classes)
    result["decision_inputs"] = decision_inputs(result)
    result["open_questions"] = result["decision_inputs"]["open_questions"]
    return result


def decision_inputs(result: dict[str, Any]) -> dict[str, Any]:
    """The facts section 8's decision map reads, its mechanical outcome (a)/(b)/(c), and the open
    questions (every case whose study class is NOT REPLICATED or INTERMEDIATE)."""
    cases = result["cases"]

    def positive(c: str) -> bool:
        return bool(cases[c].get("study_classification", {}).get("class") == POSITIVE)

    arch = [c for c in ("C07", "C09") if cases[c]["architecture_advantage"].get("holds")]
    flat_beats = [
        c for c in ("C06", "C08") if positive(c) and cases[c]["beats_optimized_flat"].get("holds")
    ]
    any_pos = [c for c in core.CASE_BASELINE if positive(c)]
    bind = bool(result["concentration_controls_bind"])
    letter, reason = decision_option(bind, result["study_status"] == "COMPLETE", arch, flat_beats)
    open_questions = [
        {"case": c, **cases[c]["study_classification"]}
        for c in core.CASE_BASELINE
        if cases[c]["study_classification"]["class"] in (NOT_REPLICATED, INTERMEDIATE)
    ]
    return {
        "locality_positive_cases_both_panels": any_pos,
        "architecture_advantage_cases": arch,
        "flat_cases_beating_optimized_flat": flat_beats,
        "concentration_controls_bind": bind,
        "section_8_option_indicated": letter,
        "section_8_reason": reason,
        "open_questions": open_questions,
        "note": "mechanical mapping of section 8; the choice remains the human lead's",
    }


# =====================================================================================================
# CSV output
# =====================================================================================================
def _num(x: Any) -> Any:
    if isinstance(x, Fraction):
        return float(x)
    return x


def write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        for row in rows:
            writer.writerow(["" if v is None else _num(v) for v in row])


def cells_rows(cells: dict[str, CellData]) -> tuple[list[str], list[list[Any]]]:
    names = [b_core.L_ID, b_core.L_FREQ, L_COAX, L_BCOAX, *b_core.L_PCOAX]
    header = [
        "label", "case", "architecture", "backbone", "seed", "panel", "R", "C", "tie",
        *[f"m_{n}" for n in names], "null_L-FREQ_mean", "null_L-COAX_mean",
        *[f"E_{n}" for n in names],
        "nll_step0", "nll", "nll_disabled", "nll_values_permuted", "memory_gain", "value_effect",
        "n_eff", "distinct_slots", "hot64_share", "context_breadth", "temporal_reuse", "temporal_reuse_null_mean",
        "temporal_reuse_ratio", "branch_persistence_top", "branch_persistence_pair",
        "branch_persistence_top_ratio", "branch_persistence_pair_ratio",
        *[f"first_touch_warm_{n}" for n in names],
        *[f"cold_misses_{n}" for n in names],
        *[f"pages_per_query_{n}" for n in names],
    ]  # fmt: skip
    rows: list[list[Any]] = []
    for label in core.all_labels():
        data = cells.get(label)
        if data is None:
            continue
        for panel in PANELS:
            util, reuse, pers = data.util(panel), data.reuse(panel), data.persistence(panel)
            for r, c, tie in CONDITIONS:
                m_vals = [
                    data.m(panel, r, tie, n) if data.has_layout(panel, r, n) else None
                    for n in names
                ]
                e_vals = [
                    data.e(panel, r, tie, n)[0] if data.has_layout(panel, r, n) else None
                    for n in names
                ]
                present = [data.has_layout(panel, r, n) for n in names]
                extra = [
                    *[
                        data.counts(panel, r, tie, n)["first_touch_warm"] if ok else None
                        for n, ok in zip(names, present, strict=True)
                    ],
                    *[
                        data.counts(panel, r, tie, n)["misses_all"] if ok else None
                        for n, ok in zip(names, present, strict=True)
                    ],
                    *[
                        data.pages_per_query(panel, r, n) if ok else None
                        for n, ok in zip(names, present, strict=True)
                    ],
                ]
                rows.append(
                    [
                        label, data.cell.case, data.cell.variant, data.cell.backbone, data.cell.seed,
                        panel, r, c, tie, *m_vals,
                        data.null_mean(panel, r, tie, b_core.L_FREQ),
                        data.null_mean(panel, r, tie, L_COAX), *e_vals,
                        data.nll(panel, "step0", "enabled"), data.nll(panel),
                        data.nll(panel, "step512", "disabled"),
                        data.nll(panel, "step512", "values_permuted"),
                        data.gain(panel), data.value_effect(panel),
                        util["n_eff"], util["distinct_slots"], util["hot64_share"],
                        util["context_breadth_mean"], reuse["actual"], reuse["null_mean"], reuse["ratio_to_null"],
                        None if pers is None else pers["top_actual"],
                        None if pers is None else pers["pair_actual"],
                        None if pers is None else pers["top_ratio"],
                        None if pers is None else pers["pair_ratio"],
                        *extra,
                    ]
                )  # fmt: skip
    return header, rows


def pairs_rows(cells: dict[str, CellData]) -> tuple[list[str], list[list[Any]]]:
    header = [
        "case", "reference_name", "reference", "backbone", "seed", "panel", "R", "C", "tie", "tag",
        "layout_case", "layout_reference", "m_case", "m_reference", "E_case", "E_reference",
        "nll_case", "nll_reference", "delta_nll", "n_eff_case", "n_eff_reference",
    ]  # fmt: skip
    rows: list[list[Any]] = []
    for case in core.CASES:
        refs: dict[str, str] = {}
        if case in core.CASE_BASELINE:
            refs["baseline"] = core.CASE_BASELINE[case]
        if case in core.CASE_FLAT_COUNTERPART:
            refs["flat_counterpart"] = core.CASE_FLAT_COUNTERPART[case]
        if case == "C10":
            refs["flat_counterpart_C06"], refs["flat_counterpart_C08"] = "C06", "C08"
        if case != "C01":
            refs["c01"] = "C01"
        for name, ref in refs.items():
            pairs, _ = _pair_cells(cells, case, ref)
            for c, r in pairs:
                for panel in PANELS:
                    for tag in TAGS:
                        if tag == L_BCOAX and c.cell.variant == "flat":
                            continue
                        lc, lr = layouts_for(tag, c.cell.variant, r.cell.variant)
                        for rr, cc, tie in CONDITIONS:
                            rows.append(
                                [
                                    case, name, ref, c.cell.backbone, c.cell.seed, panel, rr, cc, tie,
                                    tag, lc, lr, c.m(panel, rr, tie, lc), r.m(panel, rr, tie, lr),
                                    c.e(panel, rr, tie, lc)[0], r.e(panel, rr, tie, lr)[0],
                                    c.nll(panel), r.nll(panel), c.nll(panel) - r.nll(panel),
                                    c.util(panel)["n_eff"], r.util(panel)["n_eff"],
                                ]
                            )  # fmt: skip
    return header, rows


def scorecard_rows(result: dict[str, Any]) -> tuple[list[str], list[list[Any]]]:
    header = [
        "case", "architecture", "objective", "baseline", "study_status", "class_A", "class_B",
        "study_class", "beats_optimized_flat", "architecture_advantage",
    ]  # fmt: skip
    per_panel = [
        "nll", "memory_gain", "value_association_effect", "n_eff", "distinct_slots", "hot64_share",
        "context_breadth", "temporal_reuse", "temporal_reuse_ratio_to_null", "branch_persistence_top",
        "branch_persistence_pair", "branch_persistence_top_ratio",
    ]  # fmt: skip
    header += [f"{p}_{k}" for p in PANELS for k in per_panel]
    header += [
        f"{p}_{q}_{cond}" for p in PANELS for q in ("m_ratio", "e_ratio", "rho_adj")
        for cond in result["conditions"]
    ]  # fmt: skip
    header += [f"{p}_delta_nll" for p in PANELS] + [f"{p}_u_ratio" for p in PANELS]
    rows: list[list[Any]] = []
    for case in core.CASES:
        e = result["cases"][case]
        study = e.get("study_classification", {})
        row: list[Any] = [
            case, e["architecture"], "+".join(e["objective"]) or "L", e["baseline"],
            result["study_status"], study.get("panel_A"), study.get("panel_B"), study.get("class"),
            e.get("beats_optimized_flat", {}).get("holds"),
            e.get("architecture_advantage", {}).get("holds"),
        ]  # fmt: skip
        for p in PANELS:
            means = e["panels"][p]["means"]
            row += [means.get(k) for k in per_panel]
        for p in PANELS:
            vb = e["panels"][p].get("vs_baseline")
            for q in ("m_ratio", "e_ratio", "rho_adj"):
                for cond in result["conditions"]:
                    v = None
                    if vb and vb.get("status") == "complete":
                        v = vb["tags"][L_COAX][cond][q]
                    row.append(v)
        for p in PANELS:
            vb = e["panels"][p].get("vs_baseline")
            row.append(
                vb["quality"]["delta_nll_mean"] if vb and vb.get("status") == "complete" else None
            )
        for p in PANELS:
            vb = e["panels"][p].get("vs_baseline")
            row.append(vb["quality"]["u_ratio"] if vb and vb.get("status") == "complete" else None)
        rows.append(row)
    return header, rows


# =====================================================================================================
# stage and CLI
# =====================================================================================================
def run_analysis(
    eval_run: Path,
    sim_run: Path,
    out_root: Path,
    *,
    dry_run: bool,
    allow_incomplete: bool = False,
    freeze_commit: str | None = None,
) -> Path:
    from .p8_pool import require_freeze

    started = time.monotonic()
    freeze = require_freeze(dry_run, freeze_commit)
    cells, missing = load_cells(eval_run, sim_run, dry_run)
    eval_manifest = read_json(eval_run / "manifest.json")
    if freeze is not None:
        if (eval_manifest.get("freeze") or {}).get("freeze_commit") != freeze["freeze_commit"]:
            raise b_core.GateError(
                "refused: the stage manifests' freeze commit differs from this one"
            )
        if eval_manifest.get("source_sha256") != core.source_digest():
            raise b_core.GateError("refused: the stage records used different source files")
    if missing and not allow_incomplete:
        raise b_core.GateError(
            f"refused: {len(missing)} of {len(core.cells())} cells lack complete eval/sim records "
            f"(first: {missing[0]['label']}: {missing[0]['reasons']}); use --allow-incomplete to "
            "stamp the study INCOMPLETE"
        )
    result = analyse(cells, missing)
    result["dry_run"] = dry_run
    result["inputs"] = {
        "eval_run": str(eval_run),
        "sim_run": str(sim_run),
        "eval_manifest_sha256": file_sha256(eval_run / "manifest.json"),
        "sim_manifest_sha256": file_sha256(sim_run / "manifest.json"),
    }
    run = allocate_run(out_root, prefix=ANALYSIS_PREFIX_DRY if dry_run else ANALYSIS_PREFIX)
    clean = jsonable(result)
    write_json(run / "analysis.json", clean)
    write_csv(run / "scorecard.csv", *scorecard_rows(clean_scorecard_source(result)))
    write_csv(run / "cells.csv", *cells_rows(cells))
    write_csv(run / "pairs.csv", *pairs_rows(cells))
    write_json(
        run / "manifest.json",
        {
            "schema": "P8-analysis-stage-v1",
            "family": core.FAMILY,
            "dry_run": dry_run,
            "freeze": freeze,
            "study_status": result["study_status"],
            "spec_sha256": core.spec_sha256(),
            "source_sha256": core.source_digest(),
            "inputs": result["inputs"],
            "outputs": {
                n: file_sha256(run / n)
                for n in ("analysis.json", "scorecard.csv", "cells.csv", "pairs.csv")
            },
            "wall_seconds": time.monotonic() - started,
            "cap_seconds": core.ANALYSIS_CAP,
            "finished_utc": utc_now(),
        },
    )
    return run


def clean_scorecard_source(result: dict[str, Any]) -> dict[str, Any]:
    """The scorecard reads Fractions as floats."""
    cleaned: dict[str, Any] = jsonable_floats(result)
    return cleaned


def jsonable_floats(obj: Any) -> Any:
    if isinstance(obj, Fraction):
        return float(obj)
    if isinstance(obj, dict):
        return {k: jsonable_floats(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, list | tuple):
        return [jsonable_floats(v) for v in obj]
    return obj


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m arborlm.p8_analysis")
    sub = parser.add_subparsers(dest="command", required=True)
    a = sub.add_parser("analyse")
    a.add_argument("--eval-run", type=Path, required=True)
    a.add_argument("--sim-run", type=Path, required=True)
    a.add_argument("--out-root", type=Path, required=True)
    a.add_argument("--allow-incomplete", action="store_true")
    a.add_argument("--freeze-commit")
    a.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        run = run_analysis(
            args.eval_run, args.sim_run, args.out_root, dry_run=args.dry_run,
            allow_incomplete=args.allow_incomplete,
            freeze_commit=args.freeze_commit,
        )  # fmt: skip
    except b_core.GateError as exc:
        print(f"P8 analyse REFUSED: {exc}", file=sys.stderr)
        return 2
    manifest = read_json(run / "manifest.json")
    print(
        json.dumps(
            {"study_status": manifest["study_status"], "wall_seconds": manifest["wall_seconds"]}
        )
    )
    print(f"run directory: {run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
