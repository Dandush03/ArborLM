# ruff: noqa: E501
"""Analysis of a study record (ADR-0022 section 11): cell gates, mechanism classes, study label, annotations, cost lines; with the recomputation rule of section 13.3.

The input is a plain dict (``study``): ``design``, ``prefreeze``, ``gates``, ``baseline`` (Stage 0 and teacher scores), ``replicates`` (per replicate: ``cells`` by label, ``assembled``, ``retrieval``,
``routers``, ``ensemble``), ``incomplete``, ``engineering``. Missing cells, failed cells, non-finite numbers, rejected consolidations, inertia cells and undefined gaps are all handled here and never
silently dropped: a missing or failed registered cell gives INCOMPLETE and no class for its mechanism; a non-finite or undefined number gives NOT_EVALUATED.

Nothing here prints. ``outcome_record`` attaches the oracle-assisted line to every mapping that carries a class, label, annotation or cost field.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from . import classes as C
from . import combined, core
from .classes import CellEval, ClassResult, LabelInputs, Lexical
from .registry import registry
from .text import bootstrap_interval, gap_closed

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
        """The four control gaps of a memory cell on a panel; None if the cell has no ablation record, or the panel or any of the four entries is absent (a missing control is NOT_EVALUATED, never "not
        applicable": the lead's ruling on C-M1). A present entry with a non-finite or undefined value gives a None field."""
        sn = self.snap(r, group, variant)
        ab = None if sn is None else (sn.get("ablations") or {}).get(panel)
        if not isinstance(ab, Mapping):
            return None
        nodes: dict[str, Mapping[str, Any]] = {}
        for k in ("unablated", "value_perm", "code_perm", "marker_only"):
            v = ab.get(k)
            if not isinstance(v, Mapping) or "mean" not in v:
                return None
            nodes[k] = v

        def g(kind: str) -> float | None:
            return self.gap(num(nodes[kind]["mean"]), panel, sub=True)

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
        a1 = C.acq1(g_v1, None if lora else st.lexical(r, first_group, order, pf), lexical_applies=not lora)
        s_first_after = st.panel(r, group, order, pf)
        s_second_after = st.panel(r, group, order, ps)
        g_first_after = st.gap(s_first_after, pf)
        g_second = st.gap(s_second_after, ps)
        g_single = st.g_panel(r, first_group, flip(order), ps)
        a2 = C.acq2(g_second, g_single, None if lora else st.lexical(r, group, order, ps), lexical_applies=not lora)
        rt = C.ret(s_first_after if s_first_after is not None else float("nan"), s_v1 if s_v1 is not None else float("nan"), g_first_after, g_v1)
        cons = (st.cell(r, group, order) or {}).get("extras", {}).get("consolidation", {}) if mech == "M-ii" else {}
        out.append(CellEval(
            a1, a2, rt, C.negative_acquisition(g_second), C.negative_retention(g_first_after, g_v1),
            rejected=bool(cons.get("rejected", False)), below_floor=bool(cons.get("below_floor", False)),
            recompute_ne=bool({me, v1_label, single_label} & recompute_ne),
        ))  # fmt: skip
    return out


def gen_values(st: Study, r: int, group: str, variant: str) -> tuple[float | None, float | None]:
    """A snapshot's GEN loss increases under the two decisions (token 64 as registered; the last token of the first marker-like string): None where the record or value is missing."""
    sn = st.snap(r, group, variant)
    g = None if sn is None else sn.get("gen")
    if not isinstance(g, Mapping):
        return None, None
    return num(g.get("loss_increase")), num(g.get("loss_increase_first_marker"))


def gen_status(st: Study, group: str, order: str, first_group: str = "ST1") -> str:
    """GEN for an arm in an order, over its memory snapshots (the first-stage snapshot and the stage-2 snapshot) in every replicate, each judged under both decisions (C-M6): "fails" if any measured value
    breaks the 0.02 nats threshold; otherwise "not_evaluated" if any value is missing or not finite (reading 4: never a measured failure, never a hold); otherwise "holds"."""
    verdicts = [C.gen_gate(*gen_values(st, r, g, order)) for r in range(st.n) for g in (first_group, group)]
    if any(v is False for v in verdicts):
        return "fails"
    return "holds" if verdicts and all(v is True for v in verdicts) else "not_evaluated"


def gen_holds(st: Study, group: str, order: str, first_group: str = "ST1") -> bool:
    return gen_status(st, group, order, first_group) == "holds"


def _control_panels(group: str, variant: str) -> tuple[str, ...]:
    """The panel(s) a permutation control is read on: the capability the permutation targets (reading: the ADR names no panel)."""
    return {"ST1": ("E_" + variant[0],), "MAGOLD": ("E_" + variant,), "MAF": ("E_" + variant[-1],), "MII": ("E_" + variant[-1],), "MSEQ": ("E_A", "E_B"), "MJOINT": ("E_A", "E_B")}.get(group, ())


def controls(st: Study) -> list[dict[str, Any]]:
    """Every permutation control of every completed memory cell: its G on the 300-item subsample and the verdict "gives G >= 0.50" (True: CONTROL-FAILED), False, or None (NOT_EVALUATED: the record, the
    panel or the entry is missing, or the gap is undefined or not finite). Only the LoRA path has no permutation control (it has no rows or codes to permute); a memory cell with a missing record is
    NOT_EVALUATED, never skipped (C-M1)."""
    out: list[dict[str, Any]] = []
    for r in range(st.n):
        for cell in st.reps[r]["cells"].values():
            label = str(cell.get("label", ""))
            parts = label.split("/")
            if len(parts) != 3 or cell.get("status") != "completed" or not _control_panels(parts[1], parts[2]):
                continue
            sn = (cell.get("scores") or {}).get(label) or {}
            for panel in _control_panels(parts[1], parts[2]):
                ab = (sn.get("ablations") or {}).get(panel) if isinstance(sn, Mapping) else None
                for kind in ("value_perm", "code_perm"):
                    node = ab.get(kind) if isinstance(ab, Mapping) else None
                    if not isinstance(node, Mapping) or "mean" not in node:
                        out.append({"cell": label, "panel": panel, "kind": kind, "g": None, "failed": None, "reason": "control record missing"})
                        continue
                    gv = st.gap(num(node["mean"]), panel, sub=True)
                    out.append({"cell": label, "panel": panel, "kind": kind, "g": gv, "failed": None if gv is None else bool(gv >= core.CFG["gates"]["control_failed_gap"]), "reason": "undefined gap" if gv is None else ""})
    return out


def control_failed(st: Study) -> list[str]:
    """CONTROL-FAILED: a value permutation or a word-code permutation gives G >= 0.50 in any cell. The panel read is the one of the capability the permutation targets (reading: the ADR names no panel)."""
    return [f"{c['cell']}: {c['kind']} gives G {c['g']:.3f} on {c['panel']}" for c in controls(st) if c["failed"] is True]


def control_not_evaluated(st: Study) -> list[str]:
    return [f"{c['cell']}: {c['kind']} control on {c['panel']} NOT_EVALUATED ({c['reason']})" for c in controls(st) if c["failed"] is None]


# --- gates and the ensemble check (section 11.3 rows 1 and 2) ---------------------------------------------------------------------------------------------
REQUIRED_GATES = ("G1", "G2", "G4", "G5", "G6", "G7", "G8", "G9")  # every one must be present and passed for any row other than ENGINEERING-FAILURE and INCOMPLETE (G2 included: the lead's ruling of 2026-11-15)
CHECKED_GATES = REQUIRED_GATES  # a failed G2 (scored identically twice) is an engineering defect too; G3 (qualification) stops before the freeze: its failure is not read here, its absence is


def gate_verdicts(gates: Mapping[str, Any]) -> dict[str, bool | None]:
    """Each gate's verdict: True only if its record is present and its ``ok`` is the boolean True; False if present and not passed; None if its record is missing (never read as passed)."""
    out: dict[str, bool | None] = {}
    for name in sorted({*CHECKED_GATES, *REQUIRED_GATES}):
        g = gates.get(name) if isinstance(gates, Mapping) else None
        out[name] = None if not isinstance(g, Mapping) else bool(g.get("ok") is True)
    return out


def gate_findings(gates: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    """(engineering defects, incomplete): a present gate that did not pass (G2 included) is a defect found by the gates (row 1); a missing gates record, or a missing gate (G2 and G3 included), is a missing
    registered quantity (row 2: INCOMPLETE). Neither is ever read as passed."""
    eng: list[str] = []
    inc: list[str] = []
    if not gates:
        inc.append("the gates record is missing: the gates are not evaluated")
        return eng, inc
    for name, v in gate_verdicts(gates).items():
        if v is False:
            eng.append(f"gate {name} failed: {(gates.get(name) or {}).get('problems', '')}")
        elif v is None and name in REQUIRED_GATES:
            inc.append(f"gate {name} has no record: not evaluated, never read as passed")
    if not isinstance(gates.get("G3"), Mapping):
        inc.append("gate G3 has no record: not evaluated, never read as passed")
    return eng, inc


def ensemble_check(ens: Mapping[str, Any] | None) -> bool | None:
    """The oracle-routed ensemble's score equals the teacher's own on both capabilities: True; differs: False (ENGINEERING-FAILURE); the record or a value missing or not finite: None (NOT_EVALUATED)."""
    if not isinstance(ens, Mapping) or not isinstance(ens.get("oracle"), Mapping) or not isinstance(ens.get("teacher_own"), Mapping):
        return None
    pairs = [(num(ens["oracle"].get(c)), num(ens["teacher_own"].get(c))) for c in core.TASKS]
    if any(a is None or b is None or not C.finite_all(a, b) for a, b in pairs):
        return None
    return all(a == b for a, b in pairs)


def mean_of(xs: Sequence[float | None]) -> float | None:
    v = [x for x in xs if x is not None]
    return None if not v or len(v) != len(xs) else sum(v) / len(v)


def any_rule(xs: Sequence[bool | None]) -> bool | None:
    """A warning that holds in ANY replicate or order: True if one holds; otherwise None if one is undefined; otherwise False."""
    if any(x is True for x in xs):
        return True
    return None if any(x is None for x in xs) else False


def annotations(st: Study, classes: Mapping[str, Mapping[str, ClassResult]]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Section 11.4. Returns (annotations, detail). The warnings that guard against a claim (NO ADVANTAGE OVER SEPARATE ADAPTERS, RETRIEVAL SUFFICES, LEXICON-EQUIVALENT, TEACHER-EQUIVALENT-TO-GOLD, BELOW
    JOINT BOUND, EXACT-MATCH WEAK) are printed if they hold in ANY replicate or order (the lead's ruling on reading 5), with the mean beside them in ``detail``. Where the ADR states "every replicate"
    (EQUIVALENT TO A WORD TABLE, TASK-CODED SPARSE RETENTION, ROUTER) the rule is that one. Elsewhere the annotation is read on the mean (marked reading)."""
    n = st.n
    A: dict[str, Any] = {}
    D: dict[str, Any] = {}
    orders = core.ORDERS
    gt = core.CFG["gates"]

    def maf(r: int, o: str, c: str) -> float | None:
        return st.panel(r, "MAF", o, "E_" + c)

    def lsep(r: int, c: str) -> float | None:
        return num(((st.reps[r].get("assembled") or {}).get("L-sep", {}).get("E_" + c) or {}).get("mean"))

    def detail(rule: str, values: Mapping[str, Any], means: Mapping[str, Any]) -> dict[str, Any]:
        return {"rule": rule, "values": dict(values), "mean": dict(means)}

    maf_means = {f"M-append-frozen {c}": mean_of([maf(r, o, c) for r in range(n) for o in orders]) for c in core.TASKS}

    # NO ADVANTAGE OVER SEPARATE ADAPTERS: L-sep's scores on both capabilities within 0.03 of M-append-frozen's or above, in any replicate and order
    vals = {f"r{r}/{o}": C.all_or_none([C.within(lsep(r, c), maf(r, o, c)) for c in core.TASKS]) for r in range(n) for o in orders}
    A["NO ADVANTAGE OVER SEPARATE ADAPTERS"] = any_rule(list(vals.values()))
    D["NO ADVANTAGE OVER SEPARATE ADAPTERS"] = detail("any replicate or order", vals, {**{f"L-sep {c}": mean_of([lsep(r, c) for r in range(n)]) for c in core.TASKS}, **maf_means})

    # EQUIVALENT TO A WORD TABLE: E-table's G within 0.03 of ST1's or above, on both capabilities, in every replicate
    ev = {f"r{r}/{c}": C.within(st.g_panel(r, "ETABLE", c, "E_" + c), st.g_panel(r, "ST1", c + core.other_task(c), "E_" + c)) for r in range(n) for c in core.TASKS}
    A["EQUIVALENT TO A WORD TABLE"] = C.all_or_none(list(ev.values()))
    D["EQUIVALENT TO A WORD TABLE"] = detail("every replicate", ev, {f"E-table G {c}": mean_of([st.g_panel(r, "ETABLE", c, "E_" + c) for r in range(n)]) for c in core.TASKS})

    # RETRIEVAL SUFFICES / LEXICON-EQUIVALENT: scores within 0.03 of M-append-frozen's or above on both capabilities, in any replicate and order
    def rscore(r: int, c: str, name: str) -> float | None:
        return num(((st.reps[r].get("retrieval") or {}).get(c, {}).get(name) or {}).get("mean"))

    def retr(names: Sequence[str]) -> tuple[bool | None, dict[str, Any], dict[str, Any]]:
        v: dict[str, Any] = {}
        for r in range(n):
            for o in orders:
                v[f"r{r}/{o}"] = any_rule([C.all_or_none([C.within(rscore(r, c, name), maf(r, o, c)) for c in core.TASKS]) for name in names])
        m = {**{f"{name} {c}": mean_of([rscore(r, c, name) for r in range(n)]) for name in names for c in core.TASKS}, **maf_means}
        return any_rule(list(v.values())), v, m

    A["RETRIEVAL SUFFICES"], v1, m1 = retr(("R-icl", "R-nn"))
    D["RETRIEVAL SUFFICES"] = detail("any replicate or order", v1, m1)
    A["LEXICON-EQUIVALENT"], v2, m2 = retr(("R-gloss",))
    D["LEXICON-EQUIVALENT"] = detail("any replicate or order", v2, m2)

    # TEACHER-EQUIVALENT-TO-GOLD: MA-gold's G within 0.03 of ST1's or above on both capabilities, in any replicate
    tg = {f"r{r}": C.all_or_none([C.within(st.g_panel(r, "MAGOLD", c, "E_" + c), st.g_panel(r, "ST1", c + core.other_task(c), "E_" + c)) for c in core.TASKS]) for r in range(n)}
    A["TEACHER-EQUIVALENT-TO-GOLD"] = any_rule(list(tg.values()))
    gold_means = {f"MA-gold G {c}": mean_of([st.g_panel(r, "MAGOLD", c, "E_" + c) for r in range(n)]) for c in core.TASKS}
    D["TEACHER-EQUIVALENT-TO-GOLD"] = detail("any replicate", tg, {**gold_means, **{f"ST1 G {c}": mean_of([st.g_panel(r, "ST1", c + core.other_task(c), "E_" + c) for r in range(n)]) for c in core.TASKS}})

    # BELOW JOINT BOUND: M-append-frozen's G on either capability < 0.90 x M-joint's, in any replicate and order
    ratio = gt["joint_bound_ratio"]
    bj: dict[str, Any] = {}
    for r in range(n):
        for o in orders:
            res: list[bool | None] = []
            for c in core.TASKS:
                a, b = st.g_panel(r, "MAF", o, "E_" + c), st.g_panel(r, "MJOINT", "-", "E_" + c)
                res.append(None if a is None or b is None else bool(a < ratio * b))
            bj[f"r{r}/{o}"] = any_rule(res)
    A["BELOW JOINT BOUND"] = any_rule(list(bj.values()))
    D["BELOW JOINT BOUND"] = detail("any replicate or order", bj, {
        **{f"M-append-frozen G {c}": mean_of([st.g_panel(r, "MAF", o, "E_" + c) for r in range(n) for o in orders]) for c in core.TASKS},
        **{f"M-joint G {c}": mean_of([st.g_panel(r, "MJOINT", "-", "E_" + c) for r in range(n)]) for c in core.TASKS},
    })  # fmt: skip

    def below(a_group: str, a_var: Sequence[str], b_group: str, b_var: Sequence[str]) -> bool | None:
        res: list[bool | None] = []
        for c in core.TASKS:
            a = mean_of([st.g_panel(r, a_group, v, "E_" + c) for r in range(n) for v in a_var])
            b = mean_of([st.g_panel(r, b_group, v, "E_" + c) for r in range(n) for v in b_var])
            res.append(None if a is None or b is None else bool(a < ratio * b))
        return any_rule(res)

    A["BELOW ADAPTER JOINT"] = below("MJOINT", ("-",), "LJOINT", ("-",))
    # TASK-CODED SPARSE RETENTION / NONE: M-seq's loss of G_first smaller than L-seq's by >= 0.10 in every replicate of both orders
    tc = []
    for r in range(n):
        for o in orders:
            f = "E_" + o[0]
            loss_m = _loss(st.g_panel(r, "ST1", o, f), st.g_panel(r, "MSEQ", o, f))
            loss_l = _loss(st.g_panel(r, "LORA1", o, f), st.g_panel(r, "LSEQ", o, f))
            tc.append(None if loss_m is None or loss_l is None else bool(loss_l - loss_m >= gt["task_coded_retention_margin"]))
    A["TASK-CODED SPARSE RETENTION"] = C.all_or_none(tc)
    # ROUTER (keyword-level) QUALIFIED: accuracy >= 0.99 on E_A, E_B and general prefixes, and M-append-frozen passes ACQ2 and RET with learned routes on the task panels, every replicate
    acc_ok: list[bool | None] = []
    learned_ok: list[bool | None] = []
    for r in range(n):
        acc = (st.reps[r].get("routers") or {}).get("AB")
        accs = None if not isinstance(acc, Mapping) or not isinstance(acc.get("accuracy"), Mapping) else [num(acc["accuracy"].get(k)) for k in ("A", "B", "general")]
        acc_ok.append(None if accs is None or any(x is None or not C.finite_all(x) for x in accs) else all(x is not None and x >= gt["router_accuracy_min"] for x in accs))  # a missing accuracy is NOT_EVALUATED, never a measured miss
        for o in orders:
            f, s = o[0], o[1]
            g2 = st.gap(st.panel(r, "MAF", o, "E_" + s, section="learned_route"), "E_" + s)
            gs = st.gap(st.panel(r, "ST1", flip(o), "E_" + s, section="learned_route"), "E_" + s)
            s_after = st.panel(r, "MAF", o, "E_" + f, section="learned_route")
            s_v1 = st.panel(r, "ST1", o, "E_" + f, section="learned_route")
            a2 = C.acq2(g2, gs, None, lexical_applies=False)
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
    # EXACT-MATCH WEAK: gap closed on exact-match rate < 0.10 for either capability, in any replicate and order (M-append-frozen after Stage 2). The definedness floor of 0.30 on the exact-match gap is
    # implemented as written (gap_closed), so this annotation is expected to print NOT_EVALUATED: teacher-minus-student exact-match rates are likely below 0.30 (C-m8).
    em: dict[str, Any] = {}
    for r in range(n):
        for o in orders:
            res = []
            for c in core.TASKS:
                s0 = num(st.base.get("student", {}).get("E_" + c, {}).get("panel", {}).get("exact_rate"))
                t = num(st.base.get("teacher", {}).get("E_" + c, {}).get("exact_rate"))
                a = st.panel(r, "MAF", o, "E_" + c, key="exact_rate")
                gx = None if s0 is None or t is None or a is None else gap_closed(a, s0, t)
                res.append(None if gx is None else bool(gx < gt["exact_match_weak"]))
            em[f"r{r}/{o}"] = any_rule(res)
    A["EXACT-MATCH WEAK"] = any_rule(list(em.values()))
    D["EXACT-MATCH WEAK"] = detail("any replicate or order", em, {f"M-append-frozen exact-match rate {c}": mean_of([st.panel(r, "MAF", o, "E_" + c, key="exact_rate") for r in range(n) for o in orders]) for c in core.TASKS})
    return A, D


COMP_ARMS = {"M-append-frozen": ("MAF", core.ORDERS), "M-ii": ("MII", core.ORDERS), "L-seq": ("LSEQ", core.ORDERS), "M-joint": ("MJOINT", ("-",)), "L-joint": ("LJOINT", ("-",)), "M-i-separate": ("M-i-separate", ("-",)), "L-sep": ("L-sep", ("-",))}  # fmt: skip


def _comb_rec(st: Study, arm: str, r: int, variant: str) -> Mapping[str, Any] | None:
    group = COMP_ARMS[arm][0]
    if arm in ("M-i-separate", "L-sep"):
        rec = (st.reps[r].get("assembled", {}).get(arm) or {}).get("combined")
    else:
        sn = st.snap(r, group, variant)
        rec = None if sn is None else sn.get("combined")
    return rec if isinstance(rec, Mapping) and all(k in rec for k in ("C1", "C2", "single")) else None  # a partial combined record is a missing registered score


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
    """General quality under the keyword router, for every ST1 and stage-2 memory snapshot (and L-seq, for comparison): the loss increase over the unmodified student on the 200-window panel under the
    registered decision (token 64) and under the decision at the last token of the first marker-like string (C-M6), the gate under each and under both, the router's false-trigger count per stratum, the
    always-on diagnostic and the descriptive KL and top-1 share. Printed beside every class line that GEN gates (section 6.4, 11.1)."""
    rows: list[dict[str, Any]] = []
    for r in range(st.n):
        for c in st.reps[r]["cells"].values():
            sn = (c.get("scores") or {}).get(c.get("label", ""), {}) if c.get("status") == "completed" else {}
            g = sn.get("gen")
            if g is not None:
                a, m = num(g.get("loss_increase")), num(g.get("loss_increase_first_marker"))
                rows.append({
                    "cell": c["label"], "loss_increase": g.get("loss_increase"), "loss_increase_first_marker": g.get("loss_increase_first_marker"),
                    "gate_registered_decision": C.gen_gate(a), "gate_first_marker_decision": C.gen_gate(m), "gen_gate": C.gen_gate(a, m),
                    "false_triggers": g.get("false_trigger_count"), "false_triggers_first_marker": g.get("false_trigger_count_first_marker"), "stratum_sizes": g.get("stratum_sizes"),
                    "always_on_loss_increase": g.get("always_on_loss_increase"), "mean_kl_to_stage0": g.get("mean_kl_to_stage0"), "top1_unchanged": g.get("top1_unchanged"),
                })  # fmt: skip
    return rows


def router_rows(st: Study) -> list[dict[str, Any]]:
    """Per replicate and router: its route accuracy and the false-trigger rate on the marker-like windows when the decision is taken at the last token of the first marker-like string within tokens 1-64
    (a diagnostic that enters no rule)."""
    rows: list[dict[str, Any]] = []
    for r in range(st.n):
        for key, rec in (st.reps[r].get("routers") or {}).items():
            rows.append({"replicate": r, "router_tasks": key, "accuracy": rec.get("accuracy"), "general_prefixes": rec.get("general_prefixes"), "diagnostic_first_marker": rec.get("diagnostic_first_marker")})
    return rows


# --- bootstrap intervals (the lead's ruling: 220906 is drawn in the analysis stage and nowhere else) -------------------------------------------------------
def _items(node: Any) -> list[float] | None:
    if not isinstance(node, Mapping) or not isinstance(node.get("items"), list):
        return None
    vals = [num(x) for x in node["items"]]
    return None if not vals or any(v is None or not C.finite_all(v) for v in vals) else [float(v) for v in vals if v is not None]


def _comb_items(rec: Mapping[str, Any] | None, kind: str) -> list[float] | None:
    """Per-item combined scores of a combined record (the ensemble record has no ``item_scores``: the mean of an item's two answer scores)."""
    k = None if not isinstance(rec, Mapping) else rec.get(kind)
    if not isinstance(k, Mapping):
        return None
    if isinstance(k.get("item_scores"), list):
        raw: list[Any] = k["item_scores"]
    elif isinstance(k.get("items"), list):
        raw = [None if not isinstance(it.get("scores"), list) or len(it["scores"]) != 2 else (num(it["scores"][0]) or 0.0) + (num(it["scores"][1]) or 0.0) for it in k["items"]]
        raw = [None if x is None else x / 2 for x in raw]
    else:
        return None
    vals = [num(x) for x in raw]
    return None if not vals or any(v is None or not C.finite_all(v) for v in vals) else [float(v) for v in vals if v is not None]


def interval_targets(st: Study) -> list[dict[str, Any]]:
    """Every printed score that has per-item values, in a fixed order: Stage 0 and teacher panels (sorted by panel), the combined Stage 0 and ensemble records, then every registered cell in registry order
    (its snapshot, then its append-point snapshot; each panel, then its combined C1 and C2), the assembled arms of each replicate, and the retrieval baselines of each replicate. Each is
    ``{name, items, mean, single_reference}``; ``items`` is None where a value is missing or not finite."""
    out: list[dict[str, Any]] = []

    def add(name: str, node: Mapping[str, Any] | None, items: list[float] | None, mean_value: Any = None) -> None:
        sr: Any = None
        if isinstance(node, Mapping):
            sr = node.get("single_reference")
            if sr is None and "single_reference_mean" in node:  # a combined-task record (addendum section 6): the single-reference subset of the combined score
                sr = {"n": node.get("single_reference_items"), "mean": node.get("single_reference_mean")}
        value = mean_value if mean_value is not None else (node.get("mean") if isinstance(node, Mapping) else None)
        out.append({"name": name, "items": items, "mean": num(value), "single_reference": sr, "reference_counts": node.get("reference_counts") if isinstance(node, Mapping) else None})

    for kind in ("student", "teacher"):
        for panel in sorted(st.base.get(kind, {})):
            rec = st.base[kind][panel]
            node = rec.get("panel") if kind == "student" else rec
            add(f"Stage 0 {kind} {panel}" if kind == "student" else f"teacher {panel}", node, _items(node))
    comb = st.base.get("combined") or {}
    for which in ("stage0", "ensemble"):
        rec = comb.get(which)
        for kind in ("C1", "C2"):
            if isinstance(rec, Mapping) and isinstance(rec.get(kind), Mapping):
                add(f"{'Stage 0 student' if which == 'stage0' else 'ensemble'} {kind}", rec[kind], _comb_items(rec, kind), rec[kind].get("mean"))
    for c in registry(st.n) if st.n else []:
        rec = st.reps[c.replicate]["cells"].get(c.label)
        if not isinstance(rec, Mapping) or rec.get("status") != "completed":
            continue
        scores = rec.get("scores") or {}
        for suffix in ("", "@append"):
            sn = scores.get(c.label + suffix)
            if not isinstance(sn, Mapping):
                continue
            for panel in sorted(sn.get("panels") or {}):
                node = sn["panels"][panel]
                add(f"{c.label}{suffix} {panel}", node, _items(node))
            for kind in ("C1", "C2"):
                if isinstance(sn.get("combined"), Mapping) and isinstance(sn["combined"].get(kind), Mapping):
                    add(f"{c.label}{suffix} {kind}", sn["combined"][kind], _comb_items(sn["combined"], kind), sn["combined"][kind].get("mean"))
    for r in range(st.n):
        for arm in ("M-i-separate", "L-sep"):
            rec = (st.reps[r].get("assembled") or {}).get(arm)
            if not isinstance(rec, Mapping):
                continue
            for panel in sorted(k for k in rec if k.startswith("E_")):
                add(f"r{r} {arm} {panel}", rec[panel], _items(rec[panel]))
            for kind in ("C1", "C2"):
                if isinstance(rec.get("combined"), Mapping) and isinstance(rec["combined"].get(kind), Mapping):
                    add(f"r{r} {arm} {kind}", rec["combined"][kind], _comb_items(rec["combined"], kind), rec["combined"][kind].get("mean"))
        for cap in core.TASKS:
            for name in ("R-exact", "R-nn", "R-gloss", "R-icl"):
                node = ((st.reps[r].get("retrieval") or {}).get(cap) or {}).get(name)
                if isinstance(node, Mapping):
                    add(f"r{r} {name} E_{cap}", node, _items(node))
    return out


def bootstrap_intervals(st: Study, mode: str, resamples: int | None = None) -> list[dict[str, Any]]:
    """The 95% percentile bootstrap interval over items of every printed score, 10,000 resamples (the registered count), a fresh generator seeded 220906 per interval in the order of
    ``interval_targets``. Descriptive: nothing here enters a gate, a class or a label."""
    res: list[dict[str, Any]] = []
    for t in interval_targets(st):
        items = t["items"]
        if items is None:
            lo = hi = None
        else:
            lo, hi = bootstrap_interval(items, core.bootstrap_generator(mode, t["name"]), resamples)
        res.append({"name": t["name"], "n": None if items is None else len(items), "mean": t["mean"], "lo": lo, "hi": hi, "single_reference": t["single_reference"], "reference_counts": t["reference_counts"]})
    return res


# --- the analysis -------------------------------------------------------------------------------------------------------------------------------------------
def analyze(study: Mapping[str, Any], recompute_ne: set[str] | None = None, *, bootstrap_mode: str | None = None, bootstrap_resamples: int | None = None) -> dict[str, Any]:
    """The outcome of a study record. ``recompute_ne`` are the cells the recomputation marked NOT_EVALUATED (their mechanisms get that class). ``bootstrap_mode`` ("test" or the registered mode) switches on the
    descriptive bootstrap intervals (the analysis stage passes it; every other caller leaves them off, so that 220906 is drawn there and nowhere else)."""
    st = Study(study)
    ne = recompute_ne or set()
    missing = st.missing_cells()
    pre = study.get("prefreeze", {})
    incomplete = list(study.get("incomplete", [])) + (missing if st.n > 0 else ["no replicate"])
    engineering = list(study.get("engineering", []))
    gates_rec = study.get("gates") or {}
    g_eng, g_inc = gate_findings(gates_rec)
    engineering += g_eng
    incomplete += g_inc
    ens_checks: dict[str, bool | None] = {}
    for r in range(st.n):
        chk = ensemble_check(st.reps[r].get("ensemble"))
        ens_checks[f"r{r}"] = chk
        if chk is False:
            engineering.append(f"replicate {r}: the oracle-routed ensemble's score differs from the teacher's own")
        elif chk is None:
            incomplete.append(f"replicate {r}: the oracle-routed ensemble record is missing or not finite: the ensemble check is NOT_EVALUATED, not skipped")
    if not missing and st.n > 0:
        for r in range(st.n):
            for arm, (group, variants) in COMP_ARMS.items():
                for o in variants:
                    if _comb_rec(st, arm, r, o) is None and not (arm in ("M-i-separate", "L-sep") and not st.reps[r].get("assembled")):
                        incomplete.append(f"r{r} {arm} {o}: the combined-task scores are missing (a registered score)")
    classes: dict[str, dict[str, ClassResult]] = {}
    gates: dict[str, Any] = {}
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
    ctl = controls(st) if not missing else []
    ctrl = control_failed(st) if not missing else []
    ctrl_ne = control_not_evaluated(st) if not missing else []
    st1_neg = []
    for r in range(st.n):
        for o in core.ORDERS:
            g = st.g_panel(r, "ST1", o, "E_" + o[0])
            st1_neg.append(g is not None and g < core.CFG["gates"]["negative_acquisition"])
    li = LabelInputs(engineering=engineering, incomplete=incomplete, prefreeze_stop=pre.get("stop"), st1_negative_everywhere=bool(st1_neg) and all(st1_neg), control_failed=bool(ctrl), control_not_evaluated=bool(ctrl_ne), classes=classes, teacher_only=bool(pre.get("teacher_only", False)))
    gen_status_by: dict[str, dict[str, str]] = {}
    if not missing and st.n > 0:
        for mech in ("M-append-frozen", "M-ii"):
            gen_status_by[mech] = {o: gen_status(st, MECHANISMS[mech][0], o) for o in core.ORDERS}
        maf_s, mii_s = list(gen_status_by["M-append-frozen"].values()), list(gen_status_by["M-ii"].values())
        li.gen_maf_holds = all(x == "holds" for x in maf_s)
        li.gen_maf_fails = any(x == "fails" for x in maf_s)
        li.gen_maf_not_evaluated = not li.gen_maf_holds and not li.gen_maf_fails
        li.gen_mii_holds = all(x == "holds" for x in mii_s)
        li.gen_mii_not_evaluated = any(x == "not_evaluated" for x in mii_s) and not any(x == "fails" for x in mii_s)
    row, label = C.study_label(li)
    reasons: list[str] = []
    if label.startswith("TRANSFER-INCONCLUSIVE"):
        for mech, by in classes.items():
            for o, c in by.items():
                if c.name == "NOT_EVALUATED":
                    reasons += [f"{mech}/{o}: {x}" for x in c.reasons]
        reasons += ctrl_ne
        if li.gen_maf_not_evaluated and not li.gen_maf_fails:
            reasons.append("M-append-frozen: a GEN value is missing or not finite (NOT_EVALUATED; rows 6-8 do not apply)")
    ann, ann_detail = annotations(st, classes) if not missing else ({}, {})
    outcome = {
        "design": dict(study.get("design", {})),
        "label_row": row, "label": label, "label_with_design": C.label_with_n(label, st.n, int(study.get("design", {}).get("updates", 0))),
        "classes": {m: {o: c.to_json() for o, c in by.items()} for m, by in classes.items()},
        "gates": gates, "annotations": ann, "annotation_detail": ann_detail, "cost_lines": cost_lines(st) if not missing and st.n else [],
        "composition": composition(st) if not missing and st.n and not incomplete else {}, "gen_table": gen_rows(st) if not missing else [], "router_table": router_rows(st) if not missing else [],
        "control_failed": ctrl, "controls": ctl, "control_not_evaluated": ctrl_ne, "engineering": engineering, "incomplete": incomplete, "not_evaluated_reasons": reasons,
        "gate_verdicts": gate_verdicts(gates_rec), "ensemble_checks": ens_checks,
        "gen": {"M-append-frozen": li.gen_maf_holds, "M-ii": li.gen_mii_holds, "status": gen_status_by, "M-ii alone fails GEN": bool(li.gen_maf_holds and gen_status_by and any(x == "fails" for x in gen_status_by["M-ii"].values()))},
        "consolidation": consolidation_rows(st) if not missing else [], "training": training_rows(st) if not missing else [],
        "intervals": bootstrap_intervals(st, bootstrap_mode, bootstrap_resamples) if bootstrap_mode is not None and not missing and st.n else [],
        "intervals_computed": bool(bootstrap_mode is not None and not missing and st.n), "bootstrap_resamples": bootstrap_resamples if bootstrap_resamples is not None else core.CFG["scoring"]["bootstrap_resamples"],
        "by_construction": {"M-i-separate": "BY CONSTRUCTION", "L-sep": "BY CONSTRUCTION", "general_quality_under_oracle_routes": "BY CONSTRUCTION"},
    }  # fmt: skip
    return outcome


def consolidation_rows(st: Study) -> list[dict[str, Any]]:
    """M-ii's acceptance and modification statistics per cell (section 6.3): the changed-row share, the g_1 change, the relative change, and "selected on D_con, then confirmed on E"."""
    rows: list[dict[str, Any]] = []
    for r in range(st.n):
        for o in core.ORDERS:
            c = st.cell(r, "MII", o)
            cons = (c or {}).get("extras", {}).get("consolidation") if c else None
            if isinstance(cons, Mapping):
                rows.append({"cell": f"r{r}/MII/{o}", "rejected": cons.get("rejected"), "published": cons.get("published"), "below_floor": cons.get("below_floor"), "relative_change": cons.get("relative_change"), "changed_row_share": cons.get("changed_row_share"), "g1_change": cons.get("g1_change"), "scored_on": cons.get("scored_on", "selected on D_con, then confirmed on E")})
    return rows


def training_rows(st: Study) -> list[dict[str, Any]]:
    """Rows per update and updates per cell (section 6.3: "updates and rows are reported")."""
    rows: list[dict[str, Any]] = []
    for r in range(st.n):
        for c in st.reps[r]["cells"].values():
            for t in c.get("train") or []:
                rows.append({"cell": c.get("label"), "updates": t.get("updates"), "rows_per_update": t.get("rows_per_update"), "replay_rows": t.get("replay_rows"), "batch": t.get("batch"), "device": t.get("device")})
    return rows


# --- verdicts as verdicts (what the recomputation compares) ----------------------------------------------------------------------------------------------
def verdicts_of_outcome(outcome: Mapping[str, Any]) -> dict[str, Any]:
    """Every gate verdict, control verdict (GEN under both decisions, CONTROL-FAILED), class, composition class, annotation and the label of an outcome, as a flat mapping of path to a boolean, None or word.
    No score and no number enters it, so that a difference within a numeric tolerance never differs here by itself (the lead's ruling on C-M3)."""
    v: dict[str, Any] = {"label_row": outcome["label_row"], "label": outcome["label"], "control_failed": bool(outcome.get("control_failed"))}
    for k, x in (outcome.get("gate_verdicts") or {}).items():
        v[f"gate/{k}"] = x
    for k, x in (outcome.get("ensemble_checks") or {}).items():
        v[f"ensemble/{k}"] = x
    for mech, by in outcome.get("classes", {}).items():
        for o, c in by.items():
            v[f"class/{mech}/{o}"] = c["class"]
    for key, reps in (outcome.get("gates") or {}).items():
        for i, g in enumerate(reps):
            for name in ("acq1", "acq2", "ret"):
                v[f"cell/{key}/{i}/{name}"] = g[name]["ok"]
            for name in ("neg_acq", "neg_ret", "rejected", "below_floor"):
                v[f"cell/{key}/{i}/{name}"] = g[name]
    for name, a in (outcome.get("annotations") or {}).items():
        if not isinstance(a, Mapping):
            v[f"annotation/{name}"] = a
    for kind, arms in ((outcome.get("composition") or {}).get("arms") or {}).items():
        for arm, rec in arms.items():
            if isinstance(rec, Mapping) and "composition" in rec:
                v[f"composition/{kind}/{arm}"] = rec["composition"]
    for row in outcome.get("gen_table") or []:
        v[f"gen/{row['cell']}/registered"] = row.get("gate_registered_decision")
        v[f"gen/{row['cell']}/first_marker"] = row.get("gate_first_marker_decision")
        v[f"gen/{row['cell']}/both"] = row.get("gen_gate")
    for mech, by in ((outcome.get("gen") or {}).get("status") or {}).items():
        for o, s in by.items():
            v[f"gen_status/{mech}/{o}"] = s
    for c in outcome.get("controls") or []:
        v[f"control/{c['cell']}/{c['panel']}/{c['kind']}"] = c["failed"]
    return v


def verdicts(study: Mapping[str, Any]) -> dict[str, Any]:
    """The pure function the recomputation compares: every verdict derived from a set of records (a study record), with no randomness, no file access and no interval."""
    return verdicts_of_outcome(analyze(study))


def verdict_changes(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[str]:
    """The verdict paths that differ between two verdict mappings (or two outcomes' verdicts)."""
    return [k for k in sorted({*a, *b}) if a.get(k, "<absent>") != b.get(k, "<absent>")]


def strip_classes_if_incomplete(out: dict[str, Any]) -> dict[str, Any]:
    """If the recomputation cannot be completed (INCOMPLETE), no class is printed."""
    if out["label"] == "INCOMPLETE":
        out["classes"] = {m: {o: {"class": "NO CLASS (INCOMPLETE)", "reasons": ["no class is printed: the study is INCOMPLETE"]} for o in by} for m, by in out["classes"].items()}
        out["annotations"] = {}
        out["annotation_detail"] = {}
    return out


def stamp(obj: Any) -> Any:
    """Attach the oracle-assisted line as a field of every mapping that ``output.needs_line`` says carries a class, label, annotation, cost, router, GEN, composition, mechanism or verdict field or text, and
    the second fixed line beside every composition field."""
    from .output import needs_line

    if isinstance(obj, Mapping):
        d = {k: stamp(v) for k, v in obj.items()}
        if needs_line(d):
            d = {"oracle_line": core.ORACLE_LINE, **{k: v for k, v in d.items() if k != "oracle_line"}}
        if any("compos" in str(k).lower() for k in d):
            d = {**d, "combined_line": core.COMBINED_LINE}
        return d
    if isinstance(obj, list | tuple):
        return [stamp(v) for v in obj]
    return obj


def outcome_record(outcome: Mapping[str, Any]) -> dict[str, Any]:
    """The machine-readable outcome record: the oracle-assisted line as a field of the record and of every class, label, annotation, cost, router and GEN mapping."""
    rec = {"oracle_line": core.ORACLE_LINE, "outcome": dict(outcome)}
    stamped: dict[str, Any] = stamp(rec)
    return stamped
