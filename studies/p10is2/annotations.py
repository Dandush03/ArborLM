# ruff: noqa: E501
"""The descriptive annotations of ADR-0022 section 11.4 under ADR-0025 section 8.5, and the cost lines (pure functions over the registry and the combined records).

They change no line of section 8.3. Each is printed under the fixed oracle-assisted line. TEACHER-EQUIVALENT-TO-GOLD is not here (section 8.5: removed). The Δρ guard of section 8.3 applies to
TASK-CODED SPARSE RETENTION: NOT EVALUABLE unless both arms have a defined ρ and G_second >= 0.50 in every cell. COMPOSES C1 / C2 uses P10-S2's ``classes.comp_cell`` / ``composition_class`` and its
``combined`` accessors unedited (their thresholds, 0.80 / 0.50 / 0.30 / 0.50, equal this study's config; a test compares them), over the oracle-routed combined records.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from studies.p10s2 import classes as P10C
from studies.p10s2 import combined as combined_mod

from .common import core
from .quantities import CELLS, NONE, ORDERS, REPLICATES, Quantities, Registry, key

MARGIN = 0.03


def _ann(name: str, holds: bool | None, **detail: Any) -> dict[str, Any]:
    return {"name": name, "holds": holds, "detail": detail}


def _every(preds: Sequence[bool | None]) -> bool | None:
    if any(p is None for p in preds):
        return None
    return all(bool(p) for p in preds)


def no_advantage_over_separate(q: Quantities) -> dict[str, Any]:
    """D-sep's scores on both capabilities are within 0.03 of M-append's or above, in at least one order (every replicate of that order)."""
    per_order = {}
    for o in ORDERS:
        per_order[o] = all(q.reg.get("D-sep", NONE, r, f"s:{('E_A' if c == 'A' else 'E_B')}") >= q.score("M-append", o, r, c) - MARGIN for r in REPLICATES for c in core.TASKS)
    return _ann("NO ADVANTAGE OVER SEPARATE ADAPTERS", any(per_order.values()), per_order=per_order)


def equivalent_to_word_table(q: Quantities) -> dict[str, Any]:
    """E-table's G is within 0.03 of M1's or above on both capabilities, in every replicate."""
    ok = []
    for r in REPLICATES:
        for c in core.TASKS:
            order = c + core.other_task(c)
            ge = (q.reg.get("E-table", NONE, r, f"s:{('E_A' if c == 'A' else 'E_B')}") - q.s0(c)) / q.denominator(c)
            gm = q.G("M1", order, r, c)
            ok.append(None if gm is None else ge >= gm - MARGIN)
    return _ann("EQUIVALENT TO A WORD TABLE", _every(ok))


def lookup_within(q: Quantities, names: Sequence[str], label: str, any_of: bool) -> dict[str, Any]:
    """The baselines' score is within 0.03 of M-append's or above on both capabilities (every cell); ``any_of``: the best of the names."""
    ok = []
    for r, o in CELLS:
        for c in core.TASKS:
            p = "E_A" if c == "A" else "E_B"
            b = [q.reg.get(n, NONE, r, f"s:{p}") for n in names]
            ok.append((max(b) if any_of else b[0]) >= q.score("M-append", o, r, c) - MARGIN)
    return _ann(label, all(ok))


def below_joint(q: Quantities, a: str, b: str, label: str) -> dict[str, Any]:
    """arm ``a``'s G on either capability < 0.90 x arm ``b``'s (M-append against M-joint; M-joint against D-joint), in any cell / replicate."""
    hits = []
    for r in REPLICATES:
        for c in core.TASKS:
            for o in ORDERS if a == "M-append" else (NONE,):
                ga, gb = q.G(a, o, r, c), q.G(b, NONE, r, c)
                if ga is not None and gb is not None and ga < 0.90 * gb:
                    hits.append(f"{r}{o}{c}")
    return _ann(label, bool(hits), cells=hits)


def task_coded_sparse_retention(q: Quantities) -> dict[str, Any]:
    """M-seq's loss of G_first is smaller than D-seq's by >= 0.10 in every replicate of both orders. Guard (section 8.3): NOT EVALUABLE unless both arms have a defined rho and G_second >= 0.50 in every cell."""
    diffs = []
    for r, o in CELLS:
        rm, rd, gm, gd = q.rho("M-seq", o, r), q.rho("D-seq", o, r), q.G_second("M-seq", o, r), q.G_second("D-seq", o, r)
        if rm is None or rd is None or gm is None or gd is None or gm < 0.50 or gd < 0.50:
            return _ann("TASK-CODED SPARSE RETENTION", None, reason="NOT EVALUABLE: a rho is undefined or a second stage did not reach G 0.50")
        g1 = q.G_first_v1("M-seq", o, r)
        assert g1 is not None
        loss_m = g1 - (q.G_first("M-seq", o, r) or 0.0)
        loss_d = (q.G_first_v1("D-seq", o, r) or 0.0) - (q.G_first("D-seq", o, r) or 0.0)
        diffs.append(loss_d - loss_m)
    return _ann("TASK-CODED SPARSE RETENTION", all(d >= 0.10 for d in diffs), mean_difference=sum(diffs) / len(diffs))


def append_cost(q: Quantities) -> dict[str, Any]:
    """The first capability's change in G at the append point, before training (M-append's append snapshot against M1)."""
    out = {}
    for r, o in CELLS:
        k = key("M-append@append", o, r, f"s:{('E_A' if o[0] == 'A' else 'E_B')}")
        if k in q.reg.values:
            c = o[0]
            ga = (q.reg.values[k] - q.s0(c)) / q.denominator(c)
            out[f"{r}{o}"] = ga - (q.G("M1", o, r, c) or 0.0)
    return _ann("APPEND COST", None if not out else True, change_in_G_first=out)


def exact_match_weak(reg: Registry, th_den: float = 0.30) -> dict[str, Any]:
    """Gap closed on exact-match rate < 0.10 for either capability (M-append, mean over cells)."""
    gs = {}
    for c in core.TASKS:
        p = "E_A" if c == "A" else "E_B"
        s0, t = reg.get("S0", NONE, NONE, f"em:{p}"), reg.get("TEACHER", NONE, NONE, f"em:{p}")
        vals = [reg.get("M-append", o, r, f"em:{p}") for r, o in CELLS]
        gs[c] = None if t - s0 < th_den else (sum(vals) / len(vals) - s0) / (t - s0)
    if any(v is None for v in gs.values()):
        return _ann("EXACT-MATCH WEAK", None, gap_closed=gs)
    return _ann("EXACT-MATCH WEAK", any(v < 0.10 for v in gs.values()), gap_closed=gs)  # type: ignore[operator]


def router_qualified(q: Quantities, side: Mapping[str, Any]) -> dict[str, Any]:
    """Route accuracy >= 0.99 on E_A, E_B and general prefixes (every stage-2 router of every replicate) and M-append passes ACQ2 and RET with learned routes in every replicate. GEN under the router is a label gate
    and is printed beside this line."""
    accs, ok_acc = {}, []
    for r, o in CELLS:
        acc = side[f"r{r}/M-append/{o}"]["route"]["route_accuracy"]
        accs[f"{r}{o}"] = acc
        ok_acc += [acc.get(k, 0.0) >= 0.99 for k in ("A", "B", "general")]
    swapped = Registry(dict(q.reg.values))
    for r, o in CELLS:
        for p in ("E_A", "E_B"):
            swapped.values[key("M-append", o, r, f"s:{p}")] = q.reg.values[key("M-append", o, r, f"lr:{p}")]
    q2 = Quantities(swapped, q.th)
    learned = all(q2.acq2("M-append", o, r) and q2.ret("M-append", o, r) for r, o in CELLS)
    return _ann("ROUTER (keyword-level)", bool(all(ok_acc) and learned), route_accuracy=accs, learned_route_acq2_and_ret=learned)


def composition(records: Mapping[str, Mapping[str, Any]], arms: Sequence[str] = ("M-append", "M-ii", "D-seq", "D-append")) -> dict[str, Any]:
    """COMPOSES C1 / C2 per arm: the strengthened rule of the combined-tasks addendum section 8 on the oracle-routed records (mean over cells, H_a >= 0.80 per answer, DOES NOT COMPOSE below 0.50 in every
    replicate of an order)."""
    out: dict[str, Any] = {}
    s0, ens = records["S0"], records["ensemble"]

    def t_single(rec: Mapping[str, Any], kind: str, lang: str) -> float | None:
        idx = rec[kind]["tested_sentences"][lang]
        vals = [float(ens["single"]["scores"][lang][i]) for i in idx]
        return sum(vals) / len(vals) if vals else None

    for kind in ("C1", "C2"):
        for a in arms:
            orders = {}
            for o in ORDERS:
                cells = []
                for r in REPLICATES:
                    rec = records.get(f"{a}|{o}|{r}")
                    if rec is None:
                        cells.append(None)
                        continue
                    langs = core.TASKS
                    cells.append(P10C.comp_cell(
                        {x: combined_mod.tested_mean(rec, kind, x) for x in langs}, {x: combined_mod.single_mean_on(rec, kind, x) for x in langs},
                        {x: combined_mod.tested_mean(s0, kind, x) for x in langs}, {x: combined_mod.single_mean_on(s0, kind, x) for x in langs}, {x: t_single(rec, kind, x) for x in langs},
                    ))  # fmt: skip
                orders[o] = cells
            label, reasons = P10C.composition_class(orders)
            out[f"{kind}|{a}"] = {"label": label, "reasons": list(reasons)}
    return out


def all_annotations(q: Quantities, side: Mapping[str, Any] | None = None, comb: Mapping[str, Any] | None = None) -> dict[str, Any]:
    out = {a["name"]: a for a in (
        no_advantage_over_separate(q), equivalent_to_word_table(q), lookup_within(q, ("R-icl", "R-nn"), "RETRIEVAL SUFFICES", True), lookup_within(q, ("R-gloss",), "LEXICON-EQUIVALENT", False),
        below_joint(q, "M-append", "M-joint", "BELOW JOINT BOUND"), below_joint(q, "M-joint", "D-joint", "BELOW ADAPTER JOINT"), task_coded_sparse_retention(q), append_cost(q), exact_match_weak(q.reg),
    )}  # fmt: skip
    if side is not None:
        out["ROUTER (keyword-level)"] = router_qualified(q, side)
    if comb is not None:
        out["COMPOSES"] = {"name": "COMPOSES C1 / C2", "holds": None, "detail": composition(comb)}
    return out


def cost_lines(counted: Mapping[str, float], seconds: Mapping[str, float]) -> list[str]:
    """The cost lines of section 8.5: counted training multiply-adds per update (LOGICAL WORK: it enters no label, it is not measured efficiency and no count here is a speedup) and recorded training seconds
    (recorded without a comparison label: TRAINING COST COMPARABLE is not printed). The stored-size arithmetic is printed by ``classes.stored_size_line``."""
    lines = [f"counted training multiply-adds per update, {k}: {v:.4g} (a count of logical work under the reading of the cost module; enters no label; not measured efficiency)" for k, v in sorted(counted.items())]
    lines += [f"training seconds per stage, {k}: {v:.1f} (recorded, no comparison label)" for k, v in sorted(seconds.items())]
    return lines
