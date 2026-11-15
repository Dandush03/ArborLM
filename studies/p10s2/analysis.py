# ruff: noqa: E501
"""Analysis of a study record (ADR-0022 section 11): cell gates, mechanism classes, study label, annotations, cost lines; with the recomputation rule of section 13.3.

The input is a plain dict (``study``): ``design``, ``prefreeze``, ``gates``, ``baseline`` (Stage 0 and teacher scores), ``replicates`` (per replicate: ``cells`` by label, ``assembled``, ``retrieval``,
``routers``, ``ensemble``), ``incomplete``, ``engineering``. Missing cells, failed cells, non-finite numbers, rejected consolidations, inertia cells and undefined gaps are all handled here and never
silently dropped: a missing or failed registered cell gives INCOMPLETE and no class for its mechanism; a non-finite or undefined number gives NOT_EVALUATED.

Nothing here prints. ``outcome_record`` attaches the oracle-assisted line to every mapping that carries a class, label, annotation or cost field.
"""

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import classes as C
from . import combined, core, recompute
from .classes import CellEval, ClassResult, LabelInputs, Lexical
from .registry import registry
from .text import gap_closed

MECHANISMS = {"M-append-frozen": ("MAF", "ST1"), "M-ii": ("MII", "ST1"), "M-seq": ("MSEQ", "ST1"), "L-seq": ("LSEQ", "LORA1")}
FIRST_STAGE = {"M-append-frozen": "ST1", "M-ii": "ST1", "M-seq": "ST1", "L-seq": "LORA1"}


def num(x: Any) -> float | None:
    """A number from a record (non-finite values were written as strings); None if absent."""
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def flip(order: str) -> str:
    return order[::-1]


class Study:
    """Read access to a study record with the lookups the rules need."""

    def __init__(self, study: Mapping[str, Any]) -> None:
        self.s = study
        self.reps: list[Mapping[str, Any]] = list(study["replicates"])
        self.n = len(self.reps)
        self.base = study.get("baseline", {})

    def cell(self, r: int, group: str, variant: str) -> Mapping[str, Any] | None:
        c: Mapping[str, Any] | None = self.reps[r]["cells"].get(f"r{r}/{group}/{variant}")
        return c

    def snap(self, r: int, group: str, variant: str, suffix: str = "") -> Mapping[str, Any] | None:
        c = self.cell(r, group, variant)
        if c is None or c.get("status") != "completed":
            return None
        sn: Mapping[str, Any] | None = c.get("scores", {}).get(f"r{r}/{group}/{variant}{suffix}")
        return sn

    def panel(self, r: int, group: str, variant: str, panel: str, key: str = "mean", suffix: str = "", section: str = "panels") -> float | None:
        sn = self.snap(r, group, variant, suffix)
        if sn is None or section not in sn:
            return None
        return num(sn[section].get(panel, {}).get(key))

    def s0(self, panel: str, sub: bool = False) -> float | None:
        v = self.base.get("student", {}).get(panel)
        return None if v is None else num(v["subsample" if sub else "panel"]["mean"])

    def teacher(self, panel: str, sub: bool = False) -> float | None:
        v = self.base.get("teacher", {}).get(panel)
        return None if v is None else num(v["subsample_mean" if sub else "mean"])

    def gap(self, value: float | None, panel: str, sub: bool = False) -> float | None:
        a, b, t = value, self.s0(panel, sub), self.teacher(panel, sub)
        return None if a is None or b is None or t is None else gap_closed(a, b, t)

    def g_panel(self, r: int, group: str, variant: str, panel: str, suffix: str = "", section: str = "panels") -> float | None:
        return self.gap(self.panel(r, group, variant, panel, suffix=suffix, section=section), panel)

    def lexical(self, r: int, group: str, variant: str, panel: str) -> Lexical | None:
        sn = self.snap(r, group, variant)
        if sn is None or "ablations" not in sn or panel not in sn["ablations"]:
            return None
        ab = sn["ablations"][panel]

        def g(kind: str) -> float | None:
            node = ab["unablated"] if kind == "unablated" else ab[kind]
            return self.gap(num(node["mean"]), panel, sub=True)

        return Lexical(g("unablated"), g("value_perm"), g("code_perm"), g("marker_only"))

    def missing_cells(self) -> list[str]:
        out: list[str] = []
        if self.n == 0:
            return out
        for c in registry(self.n):
            rec = self.reps[c.replicate]["cells"].get(c.label)
            if rec is None:
                out.append(f"{c.label}: no record")
            elif rec.get("status") != "completed":
                out.append(f"{c.label}: {rec.get('status')}")
        return out


def cell_evals(st: Study, mech: str, order: str, recompute_ne: set[str]) -> list[CellEval]:
    group, first_group = MECHANISMS[mech]
    f, s = order[0], order[1]
    pf, ps = "E_" + f, "E_" + s
    lora = first_group == "LORA1"
    out: list[CellEval] = []
    for r in range(st.n):
        v1_label, single_label = f"r{r}/{first_group}/{order}", f"r{r}/{first_group}/{flip(order)}"
        me = f"r{r}/{group}/{order}"
        g_v1 = st.g_panel(r, first_group, order, pf)
        s_v1 = st.panel(r, first_group, order, pf)
        a1 = C.acq1(g_v1, None if lora else st.lexical(r, first_group, order, pf))
        s_first_after = st.panel(r, group, order, pf)
        s_second_after = st.panel(r, group, order, ps)
        g_first_after = st.gap(s_first_after, pf)
        g_second = st.gap(s_second_after, ps)
        g_single = st.g_panel(r, first_group, flip(order), ps)
        a2 = C.acq2(g_second, g_single, None if lora else st.lexical(r, group, order, ps))
        rt = C.ret(s_first_after if s_first_after is not None else float("nan"), s_v1 if s_v1 is not None else float("nan"), g_first_after, g_v1)
        cons = (st.cell(r, group, order) or {}).get("extras", {}).get("consolidation", {}) if mech == "M-ii" else {}
        out.append(CellEval(
            a1, a2, rt, C.negative_acquisition(g_second), C.negative_retention(g_first_after, g_v1),
            rejected=bool(cons.get("rejected", False)), below_floor=bool(cons.get("below_floor", False)),
            recompute_ne=bool({me, v1_label, single_label} & recompute_ne),
        ))  # fmt: skip
    return out


def gen_holds(st: Study, group: str, order: str, first_group: str = "ST1") -> bool:
    """GEN holds for an arm in an order if it holds at every one of its memory snapshots (the first-stage snapshot and the stage-2 snapshot) in every replicate; a missing or non-finite value is not a hold
    (reading: the harder one for a positive label)."""
    for r in range(st.n):
        for g, v in ((first_group, order), (group, order)):
            sn = st.snap(r, g, v)
            val = None if sn is None else num(sn.get("gen", {}).get("loss_increase"))
            if C.gen_gate(val) is not True:
                return False
    return True


def _control_panels(group: str, variant: str) -> tuple[str, ...]:
    """The panel(s) a permutation control is read on: the capability the permutation targets (reading: the ADR names no panel)."""
    return {"ST1": ("E_" + variant[0],), "MAGOLD": ("E_" + variant,), "MAF": ("E_" + variant[-1],), "MII": ("E_" + variant[-1],), "MSEQ": ("E_A", "E_B"), "MJOINT": ("E_A", "E_B")}.get(group, ())


def control_failed(st: Study) -> list[str]:
    """CONTROL-FAILED: a value permutation or a word-code permutation gives G >= 0.50 in any cell. The panel read is the one of the capability the permutation targets (reading: the ADR names no panel)."""
    hits: list[str] = []
    for r in range(st.n):
        for cell in st.reps[r]["cells"].values():
            grp = cell["label"].split("/")[1]
            if not _control_panels(grp, "AB") or cell.get("status") != "completed":
                continue
            variant = cell["label"].split("/")[2]
            sn = cell.get("scores", {}).get(cell["label"], {})
            for panel in _control_panels(grp, variant):
                ab = sn.get("ablations", {}).get(panel)
                if ab is None:
                    continue
                for kind in ("value_perm", "code_perm"):
                    gv = st.gap(num(ab[kind]["mean"]), panel, sub=True)
                    if gv is not None and gv >= core.CFG["gates"]["control_failed_gap"]:
                        hits.append(f"{cell['label']}: {kind} gives G {gv:.3f} on {panel}")
    return hits


def mean_of(xs: Sequence[float | None]) -> float | None:
    v = [x for x in xs if x is not None]
    return None if not v or len(v) != len(xs) else sum(v) / len(v)


def annotations(st: Study, classes: Mapping[str, Mapping[str, ClassResult]]) -> dict[str, Any]:
    """Section 11.4. Where the ADR is silent the annotation is read on the mean over replicates (and over both orders where an arm has two), marked reading."""
    n = st.n
    A: dict[str, Any] = {}
    orders = core.ORDERS

    def maf_mean(panel_cap: str) -> float | None:
        return mean_of([st.panel(r, "MAF", o, "E_" + panel_cap) for r in range(n) for o in orders])

    # NO ADVANTAGE OVER SEPARATE ADAPTERS: L-sep's scores on both capabilities within 0.03 of M-append-frozen's or above, in at least one order
    per_order = []
    for o in orders:
        ok = [C.within(mean_of([num((st.reps[r].get("assembled", {}).get("L-sep", {}).get("E_" + c, {}) or {}).get("mean")) for r in range(n)]), mean_of([st.panel(r, "MAF", o, "E_" + c) for r in range(n)])) for c in core.TASKS]
        per_order.append(C.all_or_none(ok))
    A["NO ADVANTAGE OVER SEPARATE ADAPTERS"] = None if all(x is None for x in per_order) else any(x is True for x in per_order)
    # EQUIVALENT TO A WORD TABLE: E-table's G within 0.03 of ST1's or above, on both capabilities, in every replicate
    ev = []
    for r in range(n):
        for c in core.TASKS:
            ev.append(C.within(st.g_panel(r, "ETABLE", c, "E_" + c), st.g_panel(r, "ST1", c + core.other_task(c), "E_" + c)))
    A["EQUIVALENT TO A WORD TABLE"] = C.all_or_none(ev)
    # RETRIEVAL SUFFICES / LEXICON-EQUIVALENT: scores within 0.03 of M-append-frozen's or above on both capabilities
    def retr(names: Sequence[str]) -> bool | None:
        res = []
        for name in names:
            per = [C.within(mean_of([num(st.reps[r].get("retrieval", {}).get(c, {}).get(name, {}).get("mean")) for r in range(n)]), maf_mean(c)) for c in core.TASKS]
            res.append(C.all_or_none(per))
        if any(x is True for x in res):
            return True
        return None if any(x is None for x in res) else False

    A["RETRIEVAL SUFFICES"] = retr(("R-icl", "R-nn"))
    A["LEXICON-EQUIVALENT"] = retr(("R-gloss",))
    # TEACHER-EQUIVALENT-TO-GOLD: MA-gold's G within 0.03 of ST1's or above (both capabilities, mean over replicates)
    A["TEACHER-EQUIVALENT-TO-GOLD"] = C.all_or_none([C.within(mean_of([st.g_panel(r, "MAGOLD", c, "E_" + c) for r in range(n)]), mean_of([st.g_panel(r, "ST1", c + core.other_task(c), "E_" + c) for r in range(n)])) for c in core.TASKS])
    # BELOW JOINT BOUND / BELOW ADAPTER JOINT
    def below(a_group: str, a_var: Sequence[str], b_group: str, b_var: Sequence[str]) -> bool | None:
        res = []
        for c in core.TASKS:
            a = mean_of([st.g_panel(r, a_group, v, "E_" + c) for r in range(n) for v in a_var])
            b = mean_of([st.g_panel(r, b_group, v, "E_" + c) for r in range(n) for v in b_var])
            res.append(None if a is None or b is None else bool(a < core.CFG["gates"]["joint_bound_ratio"] * b))
        if any(x is True for x in res):
            return True
        return None if any(x is None for x in res) else False

    A["BELOW JOINT BOUND"] = below("MAF", orders, "MJOINT", ("-",))
    A["BELOW ADAPTER JOINT"] = below("MJOINT", ("-",), "LJOINT", ("-",))
    # TASK-CODED SPARSE RETENTION / NONE: M-seq's loss of G_first smaller than L-seq's by >= 0.10 in every replicate of both orders
    tc = []
    for r in range(n):
        for o in orders:
            f = "E_" + o[0]
            loss_m = _loss(st.g_panel(r, "ST1", o, f), st.g_panel(r, "MSEQ", o, f))
            loss_l = _loss(st.g_panel(r, "LORA1", o, f), st.g_panel(r, "LSEQ", o, f))
            tc.append(None if loss_m is None or loss_l is None else bool(loss_l - loss_m >= core.CFG["gates"]["task_coded_retention_margin"]))
    A["TASK-CODED SPARSE RETENTION"] = C.all_or_none(tc)
    # ROUTER (keyword-level) QUALIFIED: accuracy >= 0.99 on E_A, E_B and general prefixes, and M-append-frozen passes ACQ2 and RET with learned routes on the task panels, every replicate
    acc_ok, learned_ok = [], []
    for r in range(n):
        acc = (st.reps[r].get("routers", {}).get("AB", {}) or {}).get("accuracy")
        acc_ok.append(None if acc is None else all(num(acc.get(k)) is not None and num(acc[k]) >= core.CFG["gates"]["router_accuracy_min"] for k in ("A", "B", "general")))
        for o in orders:
            f, s = o[0], o[1]
            g2 = st.gap(st.panel(r, "MAF", o, "E_" + s, section="learned_route"), "E_" + s)
            gs = st.gap(st.panel(r, "ST1", flip(o), "E_" + s, section="learned_route"), "E_" + s)
            s_after = st.panel(r, "MAF", o, "E_" + f, section="learned_route")
            s_v1 = st.panel(r, "ST1", o, "E_" + f, section="learned_route")
            a2 = C.acq2(g2, gs, None)
            rt = C.ret(s_after if s_after is not None else float("nan"), s_v1 if s_v1 is not None else float("nan"), st.gap(s_after, "E_" + f), st.gap(s_v1, "E_" + f))
            learned_ok.append(None if a2.ok is None or rt.ok is None else bool(a2.ok and rt.ok))
    A["ROUTER (keyword-level) QUALIFIED"] = C.all_or_none([*acc_ok, *learned_ok])
    # APPEND COST: the first capability's change in G at the append point (reported per replicate and order)
    ap = {}
    for r in range(n):
        for o in orders:
            g_v1 = st.g_panel(r, "ST1", o, "E_" + o[0])
            g_ap = st.g_panel(r, "MAF", o, "E_" + o[0], suffix="@append")
            ap[f"r{r}/{o}"] = None if g_v1 is None or g_ap is None else g_ap - g_v1
    A["APPEND COST"] = {"change_in_G_first_at_append": ap}
    # EXACT-MATCH WEAK: gap closed on exact-match rate < 0.10 for either capability (M-append-frozen after Stage 2, mean over replicates and orders; reading)
    weak = []
    for c in core.TASKS:
        s0 = num(st.base.get("student", {}).get("E_" + c, {}).get("panel", {}).get("exact_rate"))
        t = num(st.base.get("teacher", {}).get("E_" + c, {}).get("exact_rate"))
        a = mean_of([st.panel(r, "MAF", o, "E_" + c, key="exact_rate") for r in range(n) for o in orders])
        gx = None if s0 is None or t is None or a is None else gap_closed(a, s0, t)
        weak.append(None if gx is None else bool(gx < core.CFG["gates"]["exact_match_weak"]))
    A["EXACT-MATCH WEAK"] = None if any(x is None for x in weak) else any(weak)
    return A


COMP_ARMS = {"M-append-frozen": ("MAF", core.ORDERS), "M-ii": ("MII", core.ORDERS), "L-seq": ("LSEQ", core.ORDERS), "M-joint": ("MJOINT", ("-",)), "L-joint": ("LJOINT", ("-",)), "M-i-separate": ("M-i-separate", ("-",)), "L-sep": ("L-sep", ("-",))}  # fmt: skip


def _comb_rec(st: Study, arm: str, r: int, variant: str) -> Mapping[str, Any] | None:
    group = COMP_ARMS[arm][0]
    if arm in ("M-i-separate", "L-sep"):
        rec = (st.reps[r].get("assembled", {}).get(arm) or {}).get("combined")
    else:
        sn = st.snap(r, group, variant)
        rec = None if sn is None else sn.get("combined")
    return rec if rec and "C1" in rec else None


def _t_single(ens: Mapping[str, Any] | None, rec: Mapping[str, Any], kind: str, lang: str) -> float | None:
    if ens is None:
        return None
    idx = rec[kind]["tested_sentences"][lang]
    vals = [num(ens["single"]["scores"][lang][i]) for i in idx]
    return None if not vals or any(v is None for v in vals) else sum(v for v in vals if v is not None) / len(vals)


def _comp_inputs(rec: Mapping[str, Any], kind: str, s0: Mapping[str, Any] | None, ens: Mapping[str, Any] | None) -> C.CompCell:
    langs = core.TASKS
    s_k = {a: combined.tested_mean(rec, kind, a) for a in langs}
    s_single = {a: combined.single_mean_on(rec, kind, a) for a in langs}
    s0_k = {a: None if s0 is None else combined.tested_mean(s0, kind, a) for a in langs}
    s0_single = {a: None if s0 is None else combined.single_mean_on(s0, kind, a) for a in langs}
    t = {a: _t_single(ens, rec, kind, a) for a in langs}
    return C.comp_cell(s_k, s_single, s0_k, s0_single, t)


def composition(st: Study) -> dict[str, Any]:
    """The composition lines of the combined-tasks addendum section 8 for every scored arm and both tasks. Descriptive: nothing here enters a gate, a class or a label."""
    comb = st.base.get("combined") or {}
    s0, ens = comb.get("stage0"), comb.get("ensemble")
    out: dict[str, Any] = {"n_replicates": st.n, "arms": {}}
    for kind in ("C1", "C2"):
        out["arms"][kind] = {}
        for arm, (group, variants) in COMP_ARMS.items():
            orders: dict[str, list[C.CompCell | None]] = {}
            detail: dict[str, Any] = {}
            rejected = False
            pass_rates: list[float] = []
            c_means: dict[str, list[float]] = {}
            s_means: dict[str, list[float]] = {}
            for o in variants:
                orders[o] = []
                detail[o] = []
                for r in range(st.n):
                    rec = _comb_rec(st, arm, r, o)
                    if arm == "M-ii" and ((st.cell(r, "MII", o) or {}).get("extras", {}).get("consolidation", {}).get("rejected", False)):
                        rejected = True
                    if rec is None:
                        orders[o].append(None)
                        detail[o].append(None)
                        continue
                    cell = _comp_inputs(rec, kind, s0, ens)
                    orders[o].append(cell)
                    pr = num(rec[kind].get("pass_rate"))
                    cm = num(rec[kind].get("mean"))
                    sa = [mean_of([num(x) for x in rec["single"]["scores"][a]]) for a in core.TASKS]
                    if pr is not None:
                        pass_rates.append(pr)
                    if cm is not None and all(x is not None for x in sa):
                        c_means.setdefault(o, []).append(cm)
                        s_means.setdefault(o, []).append(sum(x for x in sa if x is not None) / 2)
                    detail[o].append({"replicate": r, "H": dict(cell.h), "single_task_G": dict(cell.g), "passes": cell.passes, "reasons": list(cell.reasons), "pass_rate": pr,
                                      "s_combined": {a: combined.tested_mean(rec, kind, a) for a in core.TASKS}, "s_single": {a: combined.single_mean_on(rec, kind, a) for a in core.TASKS}})  # fmt: skip
            name, reasons = C.composition_class(orders, rejected=rejected)
            ratios: dict[str, float | None] = {}
            for o in variants:
                cbar, sbar = mean_of(c_means.get(o, [])), mean_of(s_means.get(o, []))
                ratios[o] = cbar / (C.G["composes_ratio_min"] * sbar) if cbar is not None and sbar else None
            out["arms"][kind][arm] = {"composition": name, "reasons": list(reasons), "orders": detail, "mean_pass_rate": mean_of(pass_rates), "revision5_ratio_replaced": ratios,
                                      "label": "revision 5's raw-score rule, replaced by the human lead"}  # fmt: skip
        out["arms"][kind]["_stage0"] = _floor(st, kind, s0, ens)
        out["arms"][kind]["_ensemble"] = _ensemble_h(kind, s0, ens)
    return out


def _floor(st: Study, kind: str, s0: Mapping[str, Any] | None, ens: Mapping[str, Any] | None) -> dict[str, Any]:
    if s0 is None:
        return {"values": None}
    return {"s_combined": {a: combined.tested_mean(s0, kind, a) for a in core.TASKS}, "s_single": {a: combined.single_mean_on(s0, kind, a) for a in core.TASKS}, "note": "the floor of the rule; printed without a composition word"}


def _ensemble_h(kind: str, s0: Mapping[str, Any] | None, ens: Mapping[str, Any] | None) -> dict[str, Any]:
    """The ensemble's H_a, by construction at most 1 (equal to 1 when Stage 0's combined score does not exceed its single-task score); printed without a composition word."""
    if s0 is None or ens is None:
        return {"H": None}
    h: dict[str, float | None] = {}
    for a in core.TASKS:
        x, xs = combined.tested_mean(ens, kind, a), combined.single_mean_on(ens, kind, a)
        k0, s00 = combined.tested_mean(s0, kind, a), combined.single_mean_on(s0, kind, a)
        h[a] = None if x is None or xs is None or k0 is None or s00 is None or xs == s00 else (x - max(k0, s00)) / (xs - s00)
    return {"H": h, "note": "BY CONSTRUCTION; printed without a composition word"}


def _loss(g_before: float | None, g_after: float | None) -> float | None:
    return None if g_before is None or g_after is None else g_before - g_after


def cost_lines(st: Study) -> list[str]:
    n = st.n
    def seconds(group: str) -> list[float | None]:
        out: list[float | None] = []
        for r in range(n):
            for o in core.ORDERS:
                c = st.cell(r, group, o)
                if c is not None and c.get("train"):
                    out.append(num(c["train"][0]["wall_seconds"]))
        return out

    maf_s, lora_s = seconds("MAF"), seconds("LORA1")
    lines = [C.training_cost([x for x in maf_s if x is not None], [x for x in lora_s if x is not None])["line"]]
    store_work = [num((st.snap(r, "MAF", o) or {}).get("work", {}).get("value_parameters_read_per_generated_token")) for r in range(n) for o in core.ORDERS]
    key_products = [int((st.snap(r, "MAF", o) or {}).get("work", {}).get("key_products_per_read", 0)) for r in range(n) for o in core.ORDERS]
    ad_work = [num((st.snap(r, "LORA1", o) or {}).get("work", {}).get("adapter_parameters_applied_per_generated_token")) for r in range(n) for o in core.ORDERS]
    sw, aw = [x for x in store_work if x is not None], [x for x in ad_work if x is not None]
    lines.append(C.value_rows(C._median(sw) if sw else None, C._median(aw) if aw else None, max(key_products) if key_products else 0)["line"])
    cfg = core.CFG["student"]
    g1 = mean_of([st.g_panel(r, "MAF", o, "E_" + o[0]) for r in range(n) for o in core.ORDERS])
    g2 = mean_of([st.g_panel(r, "MAF", o, "E_" + o[1]) for r in range(n) for o in core.ORDERS])
    lines.append(C.stored_size_line(int(cfg["parameters"]), 2 * core.ROWS_PER_STAGE, core.CFG["teachers"]["parameters"], g1, g2, int(cfg["width"])))
    tc = st.s.get("prefreeze", {}).get("teacher_inference_cost")
    lines.append(f"teacher inference cost per accepted training item: {tc}" if tc else "teacher inference cost per accepted training item: not recorded")
    return lines


def gen_rows(st: Study) -> list[dict[str, Any]]:
    """General quality under the keyword router, for every ST1 and stage-2 memory snapshot (and L-seq, for comparison): the loss increase over the unmodified student on the 200-window panel, the router's
    false-trigger count per stratum, the always-on diagnostic and the descriptive KL and top-1 share. Printed beside every class line that GEN gates (section 6.4, 11.1)."""
    rows: list[dict[str, Any]] = []
    for r in range(st.n):
        for c in st.reps[r]["cells"].values():
            sn = (c.get("scores") or {}).get(c.get("label", ""), {}) if c.get("status") == "completed" else {}
            g = sn.get("gen")
            if g is not None:
                rows.append({"cell": c["label"], "loss_increase": g.get("loss_increase"), "gen_gate": C.gen_gate(num(g.get("loss_increase"))), "false_triggers": g.get("false_trigger_count"), "stratum_sizes": g.get("stratum_sizes"), "always_on_loss_increase": g.get("always_on_loss_increase"), "mean_kl_to_stage0": g.get("mean_kl_to_stage0"), "top1_unchanged": g.get("top1_unchanged")})
    return rows


def router_rows(st: Study) -> list[dict[str, Any]]:
    """Per replicate and router: its route accuracy and the false-trigger rate on the marker-like windows when the decision is taken at the last token of the first marker-like string within tokens 1-64
    (a diagnostic that enters no rule)."""
    rows: list[dict[str, Any]] = []
    for r in range(st.n):
        for key, rec in (st.reps[r].get("routers") or {}).items():
            rows.append({"replicate": r, "router_tasks": key, "accuracy": rec.get("accuracy"), "diagnostic_first_marker": rec.get("diagnostic_first_marker")})
    return rows


def analyze(study: Mapping[str, Any], recompute_ne: set[str] | None = None) -> dict[str, Any]:
    """The outcome of a study record. ``recompute_ne`` are the cells the recomputation marked NOT_EVALUATED (their mechanisms get that class)."""
    st = Study(study)
    ne = recompute_ne or set()
    missing = st.missing_cells()
    pre = study.get("prefreeze", {})
    incomplete = list(study.get("incomplete", [])) + (missing if st.n > 0 else ["no replicate"])
    engineering = list(study.get("engineering", []))
    for name, g in study.get("gates", {}).items():
        if name in ("G1", "G4", "G5", "G6", "G7", "G8", "G9") and not g.get("ok", False):
            engineering.append(f"gate {name} failed: {g.get('problems', '')}")
    for r in range(st.n):
        ens = st.reps[r].get("ensemble")
        if ens is not None and ens.get("oracle") != ens.get("teacher_own"):
            engineering.append(f"replicate {r}: the oracle-routed ensemble's score differs from the teacher's own")
    if not missing and st.n > 0:
        for r in range(st.n):
            for arm, (group, variants) in COMP_ARMS.items():
                for o in variants:
                    if _comb_rec(st, arm, r, o) is None and not (arm in ("M-i-separate", "L-sep") and not st.reps[r].get("assembled")):
                        incomplete.append(f"r{r} {arm} {o}: the combined-task scores are missing (a registered score)")
    classes: dict[str, dict[str, ClassResult]] = {}
    gates: dict[str, Any] = {}
    mech_missing = {m: any(f"r{r}/{g}/{o}" in x or f"r{r}/{fg}/{o}" in x or f"r{r}/{fg}/{flip(o)}" in x for x in missing for r in range(st.n)) for m, (g, fg) in MECHANISMS.items() for o in core.ORDERS}
    for mech in MECHANISMS:
        classes[mech] = {}
        for o in core.ORDERS:
            group, fg = MECHANISMS[mech]
            pieces = [f"/{group}/{o}", f"/{fg}/{o}", f"/{fg}/{flip(o)}"]
            if any(p in x for x in missing for p in pieces):
                classes[mech][o] = ClassResult("NO CLASS (INCOMPLETE)", ("a cell of the mechanism is missing, failed or skipped",))
                continue
            ev = cell_evals(st, mech, o, ne)
            classes[mech][o] = C.mechanism_class(mech, ev)
            gates[f"{mech}/{o}"] = [{"acq1": {"ok": e.acq1.ok, "reasons": list(e.acq1.reasons)}, "acq2": {"ok": e.acq2.ok, "reasons": list(e.acq2.reasons)}, "ret": {"ok": e.ret.ok, "reasons": list(e.ret.reasons)}, "neg_acq": e.neg_acq, "neg_ret": e.neg_ret, "rejected": e.rejected, "below_floor": e.below_floor} for e in ev]
    del mech_missing
    ctrl = control_failed(st) if not missing else []
    st1_neg = []
    for r in range(st.n):
        for o in core.ORDERS:
            g = st.g_panel(r, "ST1", o, "E_" + o[0])
            st1_neg.append(g is not None and g < core.CFG["gates"]["negative_acquisition"])
    li = LabelInputs(engineering=engineering, incomplete=incomplete, prefreeze_stop=pre.get("stop"), st1_negative_everywhere=bool(st1_neg) and all(st1_neg), control_failed=bool(ctrl), classes=classes, teacher_only=bool(pre.get("teacher_only", False)))
    if not missing and st.n > 0:
        li.gen_maf_holds = all(gen_holds(st, "MAF", o) for o in core.ORDERS)
        li.gen_maf_fails = not li.gen_maf_holds
        li.gen_mii_holds = all(gen_holds(st, "MII", o) for o in core.ORDERS)
    row, label = C.study_label(li)
    reasons: list[str] = []
    if label.startswith("TRANSFER-INCONCLUSIVE"):
        for mech, by in classes.items():
            for o, c in by.items():
                if c.name == "NOT_EVALUATED":
                    reasons += [f"{mech}/{o}: {x}" for x in c.reasons]
    ann = annotations(st, classes) if not missing else {}
    return {
        "design": dict(study.get("design", {})),
        "label_row": row, "label": label, "label_with_design": C.label_with_n(label, st.n, int(study.get("design", {}).get("updates", 0))),
        "classes": {m: {o: c.to_json() for o, c in by.items()} for m, by in classes.items()},
        "gates": gates, "annotations": ann, "cost_lines": cost_lines(st) if not missing and st.n else [],
        "composition": composition(st) if not missing and st.n and not incomplete else {}, "gen_table": gen_rows(st) if not missing else [], "router_table": router_rows(st) if not missing else [],
        "control_failed": ctrl, "engineering": engineering, "incomplete": incomplete, "not_evaluated_reasons": reasons,
        "gen": {"M-append-frozen": li.gen_maf_holds, "M-ii": li.gen_mii_holds},
        "by_construction": {"M-i-separate": "BY CONSTRUCTION", "L-sep": "BY CONSTRUCTION", "general_quality_under_oracle_routes": "BY CONSTRUCTION"},
    }  # fmt: skip


def analyze_with_recomputation(registered: Mapping[str, Any], recomputed_cells: Mapping[str, Mapping[str, Any]] | None, mode: str, *, memory_exceeded: bool = False) -> dict[str, Any]:
    """The study outcome under the recomputation rule: no result without a completed recomputation (INCOMPLETE); ENGINEERING-FAILURE if a listed difference changes a gate, class, annotation or label;
    otherwise the cells with a difference beyond tolerance are NOT_EVALUATED, the recomputed values reported, and their mechanisms get the class NOT_EVALUATED."""
    reg_cells = {lab: rec for rep in registered["replicates"] for lab, rec in rep["cells"].items()}
    if recomputed_cells is None:
        out = analyze({**registered, "incomplete": [*registered.get("incomplete", []), "the independent recomputation has not completed"]})
        out["recomputation"] = recompute.recomputation_status(None, [])
        return strip_classes_if_incomplete(out)
    res = recompute.compare_cells(reg_cells, recomputed_cells, mode, memory_exceeded=memory_exceeded)
    if not res.complete:
        out = analyze({**registered, "incomplete": [*registered.get("incomplete", []), "the recomputation could not be completed" + (" within the memory limits" if memory_exceeded else "")]})
        out["recomputation"] = recompute.recomputation_status(res, [])
        out["recomputation"]["differences"] = [d.to_json() for d in res.differences]
        return strip_classes_if_incomplete(out)
    rep_study = copy.deepcopy(dict(registered))
    reported = recompute.reported_cells(reg_cells, recomputed_cells, res)
    for rep in rep_study["replicates"]:
        rep["cells"] = {lab: reported[lab] for lab in rep["cells"]}
    rec_study = copy.deepcopy(dict(registered))
    for rep in rec_study["replicates"]:
        rep["cells"] = {lab: {**rec, "scores": recomputed_cells.get(lab, rec).get("scores"), "extras": recomputed_cells.get(lab, rec).get("extras")} for lab, rec in rep["cells"].items()}
    a_reg, a_rec = analyze(registered), analyze(rec_study)
    changed = recompute.outcome_changes(a_reg, a_rec)
    if changed:
        out = analyze({**registered, "engineering": [*registered.get("engineering", []), f"a recomputation difference changes {len(changed)} gate, class, annotation or label entries"]})
        out["recomputation"] = recompute.recomputation_status(res, changed)
        out["recomputation"]["differences"] = [d.to_json() for d in res.differences]
        return out
    out = analyze(rep_study, set(res.not_evaluated_cells))
    out["recomputation"] = recompute.recomputation_status(res, [])
    out["recomputation"]["differences"] = [d.to_json() for d in res.differences]
    return out


def strip_classes_if_incomplete(out: dict[str, Any]) -> dict[str, Any]:
    """If the recomputation cannot be completed (INCOMPLETE), no class is printed."""
    if out["label"] == "INCOMPLETE":
        out["classes"] = {m: {o: {"class": "NO CLASS (INCOMPLETE)", "reasons": ["no class is printed: the study is INCOMPLETE"]} for o in by} for m, by in out["classes"].items()}
        out["annotations"] = {}
    return out


def stamp(obj: Any) -> Any:
    """Attach the oracle-assisted line as a field of every mapping that carries a class, label, annotation, cost, router, composition or mechanism field."""
    from .output import GUARDED_KEYS

    if isinstance(obj, Mapping):
        d = {k: stamp(v) for k, v in obj.items()}
        if any(k in d for k in GUARDED_KEYS):
            d = {"oracle_line": core.ORACLE_LINE, **{k: v for k, v in d.items() if k != "oracle_line"}}
        if "composition" in d:
            d = {**d, "combined_line": core.COMBINED_LINE}
        return d
    if isinstance(obj, list | tuple):
        return [stamp(v) for v in obj]
    return obj


def outcome_record(outcome: Mapping[str, Any]) -> dict[str, Any]:
    """The machine-readable outcome record: the oracle-assisted line as a field of the record and of every class, label, annotation and cost mapping."""
    rec = {"oracle_line": core.ORACLE_LINE, "outcome": dict(outcome)}
    stamped: dict[str, Any] = stamp(rec)
    return stamped
