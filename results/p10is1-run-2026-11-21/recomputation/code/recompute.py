# ruff: noqa
"""P10-I-S1 independent recomputation (arbor-auditor, Opus 5.5, written 2026-11-21 before any registered result was read).

Recomputes, from the raw per-cell records of a run directory, every quantity and label of ADR-0024 sections 8-9 (C-CAPACITY, C-SATURATION,
C-EFFICIENCY, the dense labels, the sparse label, KEY-LEARNING-LIMITED, the ladder stop check). Written from the ADR text (ADR-0024 at the
freeze commit 46bf55a, and ADR-0021 where ADR-0024 refers to it). It imports NOTHING from studies/ or arborlm/. Standard library only.

Inputs (all read-only):
  --run-dir      the run directory (evaluate/<label>/uXXXXXXXX.json, baselines/dN_fF.json, ladder/<name>.json, timing/timing.json)
  --plan         the plan whose cells are read (freeze/plan.json for the registered run; view_plan.json for a counting rehearsal)
  --config       configs/p10is1_capacity.toml at the freeze commit (thresholds, grid, steps)
  --qualification  the R2 table (the counting rehearsal record's "qualification", or a file with {"table": ...})
  --madds        JSON {"ARM|slots": analytic multiply-adds per update}: MC-A's cost per update (NOT recomputed here; see NOTE.md)
  --replicates   override the replicate count and the "all"/"at least" counts (only for a one-replicate rehearsal test)
  --out          output JSON
Python >= 3.11 (tomllib).
"""

import argparse
import json
import math
import tomllib
from pathlib import Path

PANELS = ("A", "B")


# ---------------------------------------------------------------------------------------------------------------- arithmetic
def log_binom_pmf(k, n, p):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p)


def binom_cdf_all(n, p):
    """exact P(X <= k) for k = 0..n, summed in log space (stable)."""
    logs = [log_binom_pmf(k, n, p) for k in range(n + 1)]
    out, acc = [], -math.inf
    for lp in logs:
        acc = max(acc, lp) + math.log1p(math.exp(-abs(acc - lp))) if acc != -math.inf else lp
        out.append(math.exp(acc))
    return out


_CHANCE = {}


def chance_interval(n):
    """G2: the exact binomial central interval of level 1 - 0.001/40 around 1/32: lo = smallest k with P(X <= k) > a/2, hi = smallest k with P(X <= k) >= 1 - a/2."""
    if n not in _CHANCE:
        a = 0.001 / 40
        cdf = binom_cdf_all(n, 1 / 32)
        lo = next(k for k, c in enumerate(cdf) if c > a / 2)
        hi = next(k for k, c in enumerate(cdf) if c >= 1 - a / 2)
        _CHANCE[n] = (lo, hi)
    return _CHANCE[n]


_Q = {}


def binom_upper_quantile(m, p, tail):
    """smallest k with P(X <= k) >= 1 - tail (section 8.1 DEP-c, ruling 20)."""
    key = (m, p, tail)
    if key not in _Q:
        if m == 0:
            _Q[key] = 0
        else:
            cdf = binom_cdf_all(m, p)
            _Q[key] = next(k for k, c in enumerate(cdf) if c >= 1 - tail)
    return _Q[key]


def i_of_a(a):
    """ADR-0021 7.1: i = 5 - h2(e) - e log2 31, e = 1 - a_use."""
    e = 1.0 - a
    if e <= 0:
        return 5.0
    if e >= 1:
        return 5.0 - 0.0 - math.log2(31)
    h2 = -e * math.log2(e) - (1 - e) * math.log2(1 - e)
    return 5.0 - h2 - e * math.log2(31)


# ---------------------------------------------------------------------------------------------------------------- records
class Obs:
    def __init__(self, p, base):
        self.n, self.c, self.u = int(p["n"]), int(p["correct"]), int(p["useful"])
        self.dis = None if p.get("disabled_correct") is None else int(p["disabled_correct"])
        self.shu = None if p.get("shuffled_correct") is None else int(p["shuffled_correct"])
        self.un, self.uc = int(p.get("unseen_n", 0)), int(p.get("unseen_correct", 0))
        self.b = base
        self.a_use = self.u / self.n
        lo, hi = chance_interval(self.n)
        self.i = 0.0 if self.u <= hi else max(0.0, i_of_a(self.a_use))
        self.leak = self.un > 0 and self.uc > chance_interval(self.un)[1]


def in_chance(count, n):
    lo, hi = chance_interval(n)
    return lo <= count <= hi


def dep_fail(o, memory, qualified, th):
    """section 8.1: DEP applies at a_use >= 0.25; returns the set of qualified conditions that fail. memory=False: D-OQ (ruling 17: DEP-b not applied)."""
    if o.a_use < th["dep_use_floor"]:
        return set()
    out = set()
    if "a" in qualified and o.dis is not None and not in_chance(o.dis, o.n):
        out.add("a")
    if memory and "b" in qualified and o.shu is not None and not in_chance(o.shu, o.n):
        out.add("b")
    if "c" in qualified and o.b is not None:
        m = o.n - o.u
        p_plus = chance_interval(o.n)[1] / o.n
        q = binom_upper_quantile(m, p_plus, th["dep_c_tail"])
        x = o.c - o.u
        if x > q and (x - m * o.b / o.n) / o.n > th["dep_c_floor"]:
            out.add("c")
    return out


# ---------------------------------------------------------------------------------------------------------------- the analysis
class Recompute:
    def __init__(self, a):
        self.cfg = tomllib.loads(Path(a.config).read_text())
        self.th = dict(self.cfg["thresholds"])
        if a.replicates:
            r = int(a.replicates)
            # test mode only: "all 5" -> all r, "at least 4" -> at least min(r, 4); the "at least 2" counts stay as the ADR fixes them
            self.th.update(replicates=r, paired_all=r, paired_most=min(r, self.th["paired_most"]), sparse_ratio_min_replicates=min(r, self.th["sparse_ratio_min_replicates"]), unloaded_min=min(r, self.th["unloaded_min"]))
        self.R = int(self.th["replicates"])
        self.ALL, self.MOST = int(self.th["paired_all"]), int(self.th["paired_most"])
        self.run_dir = Path(a.run_dir)
        plan = json.loads(Path(a.plan).read_text())
        self.plan = plan
        self.cells = plan["cells"]
        self.by = {(c["arm"], c["facts"], c["slots"], c["draw"]): c for c in self.cells}
        q = json.loads(Path(a.qualification).read_text())
        self.qual = q.get("table", q.get("qualification", q))
        self.madds = json.loads(Path(a.madds).read_text())
        tp = self.run_dir / "timing" / "timing.json"
        self.cpu = json.loads(tp.read_text())["cpu"] if tp.is_file() else None
        self.mct = self.cpu is not None
        self.mc_grid = list(self.cfg["mc"]["grid"])
        self.stops = {}
        ld = self.run_dir / "ladder"
        for c in self.cells:
            if c["ladder_cell"]:
                nm = self.cname(c["facts"], c["slots"])
                p = ld / (nm.replace("/", "_") + ".json")
                if p.is_file():
                    self.stops[nm] = int(json.loads(p.read_text())["u_run"])
        self.base = {}
        for p in sorted((self.run_dir / "baselines").glob("*.json")):
            r = json.loads(p.read_text())
            if r.get("kind") != "baseline":
                continue
            self.base[(int(r["draw"]), int(r["facts"]))] = {k: int(v) for k, v in r["no_memory"].items()}
        self._obs, self._ser, self.missing = {}, {}, []
        self.floor_i = i_of_a(self.th["plateau_floor_a_use"])
        self.r2fail = {}
        self.ref_failed = []
        self.notes = []

    # ---- names and lengths
    @staticmethod
    def size(n):
        return f"{n // 1024}K" if n >= 1024 else str(n)

    def cname(self, f, n):
        return f"{self.size(f)}/{self.size(n)}"

    def spec(self, arm, f, n, d):
        return self.by[(arm, f, n, d)]

    def u_run(self, s):
        return self.stops[self.cname(s["facts"], s["slots"])] if s["ladder_cell"] else int(s["run"])

    def snaps(self, s):
        return [u for u in s["snapshots"] if u <= self.u_run(s)]

    # ---- observations
    def obs(self, s, read, u, panel):
        k = (s["label"], read, u, panel)
        if k not in self._obs:
            p = self.run_dir / "evaluate" / s["label"] / f"u{u:08d}.json"
            rec = json.loads(p.read_text())
            assert rec["label"] == s["label"] and int(rec["update"]) == u
            b = self.base.get((s["draw"], s["facts"]), {}).get(panel)
            self._obs[k] = Obs(rec["reads"][read]["panels"][panel], b)
        return self._obs[k]

    def ser(self, s, read, panel):
        k = (s["label"], read, panel)
        if k not in self._ser:
            self._ser[k] = {u: self.obs(s, read, u, panel) for u in self.snaps(s)}
        return self._ser[k]

    def istar(self, s, read, panel, upto):
        vals = [o.i for u, o in self.ser(s, read, panel).items() if u <= upto]
        return max(vals) if vals else 0.0

    def leakage(self, s, read):
        return any(self.obs(s, read, u, p).leak for u in self.snaps(s) for p in PANELS)

    # ---- DEP with the reference qualification
    def table_q(self, facts, u, u_p):
        f = min(u / u_p, 1.0)
        row = self.qual.get(str(facts), {})
        key = f"{f:.6g}"
        if key not in row:
            return {"a", "b", "c"}
        return set(row[key])

    def compute_reference(self):
        for facts, (rf, rs) in ((int(k), v) for k, v in self.cfg["grid"]["r2_reference_cell"].items()):
            for d in range(1, self.R + 1):
                if ("R2", rf, rs, d) not in self.by:
                    continue
                s = self.spec("R2", rf, rs, d)
                fails = {}
                for u in self.snaps(s):
                    qq = self.table_q(facts, u, s["u_p"])
                    for p in PANELS:
                        f = dep_fail(self.obs(s, "main", u, p), True, qq, self.th)
                        if f:
                            fails.setdefault(u, set()).update(f)
                    if u in fails:
                        self.ref_failed.append({"row": facts, "draw": d, "update": u, "conditions": sorted(fails[u])})
                self.r2fail[(facts, d)] = fails

    def qualified(self, s, u):
        q = self.table_q(s["facts"], u, s["u_p"])
        return q - self.r2fail.get((s["facts"], s["draw"]), {}).get(min(u, s["u_p"]), set())

    def dep_failed(self, s, read, panel):
        mem = s["arm"] != "D-OQ"
        return {u for u in self.snaps(s) if dep_fail(self.obs(s, read, u, panel), mem, self.qualified(s, u), self.th)}

    def dep_any(self, s, read):
        return set().union(*(self.dep_failed(s, read, p) for p in PANELS))

    # ---- REF, fullness
    def ref_ok(self, d, facts):
        rf, rs = self.cfg["grid"]["r2_reference_cell"][str(facts)]
        if ("R2", rf, rs, d) not in self.by:
            return False
        s = self.spec("R2", rf, rs, d)
        return all(self.obs(s, "main", s["u_p"], p).a_use >= self.th["ref_r2_min"] for p in PANELS)

    def plateau_at(self, s, read, u):
        """section 7.2 item 3 / ADR-0021 8.2, on both panels: i*(U) - i*(U/2) <= 0.10 and i*(U/2) >= Fano(0.25)."""
        for p in PANELS:
            a, h = self.istar(s, read, p, u), self.istar(s, read, p, u // 2)
            if not (a - h <= self.th["plateau_max"] and h >= self.floor_i):
                return False
        return True

    def ladder_points(self, upto):
        half = int(self.cfg["ladder"]["half_unit"])
        pts = set()
        j = 1
        while half * 2 ** j <= upto:
            pts.add(half * 2 ** j)
            j += 1
        j = 0
        while half * 3 * 2 ** j <= upto:
            pts.add(half * 3 * 2 ** j)
            j += 1
        return sorted(p for p in pts if p >= int(self.cfg["ladder"]["base"]))

    def full_info(self, s, read):
        run = self.u_run(s)
        if s["ladder_cell"]:
            pts = self.ladder_points(run)
            length = None
            for k, u in enumerate(pts):  # section 7.2 item 6: "the first ladder point at which it was full, read on snapshots up to U_run" (no lower bound at U0;
                prev = pts[k - 1] if k else None  # first comparison run 2026-11-21 had restricted it to >= U0, which the text does not say: corrected, see NOTE.md)
                if self.plateau_at(s, read, u) and prev is not None and self.plateau_at(s, read, prev):
                    length = u
                    break
        else:
            length = run if self.plateau_at(s, read, run) else None
        loaded = length is not None and all(self.istar(s, read, p, length) <= self.th["loaded_i_max"] for p in PANELS)
        return {"length": length, "full": length is not None, "loaded": loaded, "u_run": run}

    def recompute_stop(self, name):
        specs = [c for c in self.cells if c["ladder_cell"] and self.cname(c["facts"], c["slots"]) == name and c["arm"] in ("F-OQ", "T-OQ", "H8")]
        u0, g = int(specs[0]["u0"]), int(specs[0]["run"])
        rec = self.stops[name]
        pts = self.ladder_points(g)
        for k, u in enumerate(pts):
            if u < u0 or u > rec:
                continue
            prev = pts[k - 1] if k else None
            if prev is not None and all(self.plateau_at(s, "main", u) and self.plateau_at(s, "main", prev) for s in specs):
                return u
        return g

    # ---- costs and matched compute
    def cost(self, measure, arm, slots):
        base = "F-OQ" if arm == "F-OQ-IVF" else arm
        if measure == "A":
            return float(self.madds[f"{base}|{slots}"])
        return None if self.cpu is None else float(self.cpu[f"{base}|{slots}"])

    def snap_at_least(self, mult, u_p):
        for g in self.mc_grid:
            if g >= mult - 1e-12:
                return int(round(g * u_p))
        return None

    def mc(self, c_first, c_second, u_p, run_first, run_second, mode="dense"):
        """One measure. Pair (first, second): capacity: first = smaller cell, second = larger cell; dense: first = D-OQ, second = arm.
        Returns (u_first, u_second, status). The costlier cell at U_P, the cheaper at the smallest grid snapshot whose cumulative cost is at least the costlier's at U_P."""
        if mode == "capacity" and c_second <= c_first:  # ruling 1 / section 9.1: where the larger cell costs no more per update than the smaller, U_MC = U_P
            return (u_p, u_p, "OK")
        if c_second >= c_first:  # second costs more (or equal): first (cheaper) read later
            r = c_second / c_first
            u = self.snap_at_least(r, u_p)
            if u is None or u > run_first:
                return (u, u_p, "MC-SHORT")
            return (u, u_p, "OK")
        r = c_first / c_second
        u = self.snap_at_least(r, u_p)
        if u is None or u > run_second:
            return (u_p, u, "MC-SHORT")
        return (u_p, u, "OK")

    def mc_all(self, arm_first, slots_first, arm_second, slots_second, u_p, run_first, run_second, claim, mode="dense"):
        """MC-A, MC-T and MC-C (section 8.2). claim: which cell's advantage would be claimed ('second' = the larger cell on the capacity line; 'second' = the arm in the dense labels)."""
        out = {}
        ca = (self.cost("A", arm_first, slots_first), self.cost("A", arm_second, slots_second))
        out["MC-A"] = self.mc(ca[0], ca[1], u_p, run_first, run_second, mode) + (ca,)
        if not self.mct:
            return out
        ct = (self.cost("T", arm_first, slots_first), self.cost("T", arm_second, slots_second))
        out["MC-T"] = self.mc(ct[0], ct[1], u_p, run_first, run_second, mode) + (ct,)
        da, dt = (ca[1] > ca[0]) - (ca[1] < ca[0]), (ct[1] > ct[0]) - (ct[1] < ct[0])
        if da == 0 or dt == 0 or da == dt:  # agree (an exact tie agrees with the other measure): the reading with the larger multiplier
            def mult(m):
                uf, us, st = m[0], m[1], m[2]
                if uf is None or us is None:
                    return math.inf
                return max(uf, us) / u_p
            pick = max(("MC-A", "MC-T"), key=lambda k: (mult(out[k]), k == "MC-T"))
            # if the two have the same multiplier, they read the same snapshots
            out["MC-C"] = out[pick][:3] + ("agree", pick)
        else:
            rr = max(ca[1] / ca[0], ca[0] / ca[1], ct[1] / ct[0], ct[0] / ct[1])
            u = self.snap_at_least(rr, u_p)
            # the claimed cell (second) at U_P, the other (first) at the later snapshot
            if u is None or u > run_first:
                out["MC-C"] = (u, u_p, "MC-SHORT", "ambiguous")
            else:
                out["MC-C"] = (u, u_p, "OK", "ambiguous")
        return out

    # ---- capacity step, one replicate
    def capacity_step(self, arm, step):
        base, read = ("F-OQ", "ivf") if arm == "F-OQ-IVF" else (arm, "main")
        name, facts, small, large = step[0], int(step[1]), int(step[2]), int(step[3])
        reps = []
        for d in range(1, self.R + 1):
            sm, lg = self.spec(base, facts, small, d), self.spec(base, facts, large, d)
            fs, fl = self.full_info(sm, read), self.full_info(lg, read)
            u_p = int(sm["u_p"])
            mcs = self.mc_all(base, small, base, large, u_p, fs["u_run"], fl["u_run"], "second", mode="capacity")  # first match of the first comparison runs: corrected, see NOTE.md
            dep = bool(self.dep_any(sm, read) or self.dep_any(lg, read))
            refok = self.ref_ok(d, facts)
            leak = self.leakage(sm, read) or self.leakage(lg, read)
            pv, det = {}, {}
            for p in PANELS:
                S, Lg = self.ser(sm, read, p), self.ser(lg, read, p)
                iN, i4 = S[u_p].i, Lg[u_p].i
                d_mu = i4 - iN
                d_mc = {}
                for k, m in mcs.items():
                    uf, us, st = m[0], m[1], m[2]
                    if st != "OK":
                        d_mc[k] = None
                    else:
                        d_mc[k] = Lg[us].i - S[uf].i
                istar_run = self.istar(sm, read, p, fs["u_run"])
                istar_half = self.istar(sm, read, p, fs["u_run"] // 2)
                d_sat = i4 - istar_run
                d_full = self.istar(lg, read, p, fl["u_run"]) - istar_run
                a4 = Lg[u_p].a_use
                g, nm_ = self.th["gain_min"], self.th["null_max"]
                if not refok or leak:
                    v = "NOT_EVALUATED"
                elif dep:
                    v = "DEPENDENCE_FAILED"
                elif iN >= self.th["ceiling_i"]:
                    v = "CEILING"
                elif (d_mu >= g and d_mc.get("MC-A") is not None and d_mc["MC-A"] >= g
                      and (not self.mct or (d_mc.get("MC-T") is not None and d_mc["MC-T"] >= g and d_mc.get("MC-C") is not None and d_mc["MC-C"] >= g))
                      and d_sat >= g and fs["loaded"] and d_sat - 2 * (istar_run - istar_half) >= g and a4 >= self.th["a_use_floor_capacity"]):
                    v = "CAPACITY"
                elif d_mu >= g:
                    v = "GAIN WITHIN BUDGET ONLY"
                elif d_mu <= -g and d_full <= -g:
                    v = "REVERSED"
                elif d_mu <= -g:
                    v = "BEHIND WITHIN BUDGET"
                elif abs(d_mu) < nm_ and abs(d_full) < nm_ and fs["full"] and fl["full"] and fs["loaded"]:
                    v = "NULL"
                elif abs(d_mu) < nm_ and abs(d_full) < nm_ and fs["full"] and fl["full"] and not fs["loaded"]:
                    v = "FLAT, NOT LOADED"
                else:
                    v = "UNRESOLVED"
                pv[p] = v
                det[p] = {"d_mu": d_mu, "d_mc": d_mc, "d_sat": d_sat, "d_full": d_full, "i_small_up": iN, "i_large_up": i4, "a_use_large_up": a4, "slope_small": istar_run - istar_half}
            verdict = pv["A"] if pv["A"] == pv["B"] else "PANEL-DISAGREE"
            reps.append({"replicate": d, "verdict": verdict, "panels": pv, "detail": det, "mc": {k: list(v[:3]) for k, v in mcs.items()}, "small": fs, "large": fl, "ref_ok": refok, "leakage": leak, "dep_failed": dep})
        vs = [r["verdict"] for r in reps]
        cnt = lambda *xs: sum(v in xs for v in vs)  # noqa: E731
        if cnt("NOT_EVALUATED") >= self.th["not_evaluated_min"]:
            cls = "NOT_EVALUATED"
        elif cnt("DEPENDENCE_FAILED") >= self.th["not_evaluated_min"]:
            cls = "DEPENDENCE_FAILED"
        elif cnt("PANEL-DISAGREE") >= self.th["panel_disagree_min"]:
            cls = "NOT REPLICATED"
        elif cnt("CAPACITY") >= self.ALL:
            cls = "CAPACITY STEP"
        elif cnt("CAPACITY", "GAIN WITHIN BUDGET ONLY") >= self.ALL:
            cls = "GAIN WITHIN BUDGET"
        elif cnt("CEILING", "FLAT, NOT LOADED") >= self.th["unloaded_min"]:
            cls = "NOT LOADED"
        elif cnt("REVERSED") >= self.MOST:
            cls = "REVERSED"
        elif cnt("NULL", "REVERSED") >= self.MOST:
            cls = "NO GAIN"
        elif sum(not r["small"]["full"] for r in reps) >= self.th["not_full_min"]:
            cls = "NOT FULL WITHIN BUDGET"
        else:
            cls = "MIXED"
        return {"step": name, "class": cls, "verdicts": vs, "replicates": reps}

    def steps(self):
        return [tuple(s) for s in self.cfg["grid"]["steps"]]

    def transitions(self):
        return {"1K→4K": ["C1", "N1"], "4K→16K": ["C2", "N2"]}

    def a_use_largest(self, arm):
        base, read = ("F-OQ", "ivf") if arm == "F-OQ-IVF" else (arm, "main")
        f, n = self.cfg["grid"]["u_p_larger_step_cell"]["32768"]
        return all(self.obs(self.spec(base, f, n, d), read, int(self.spec(base, f, n, d)["u_p"]), p).a_use >= self.th["arm_a_use_at_largest"] for d in range(1, self.R + 1) for p in PANELS)

    def arm_class(self, steps, arm):
        tr = self.transitions()
        c = {k: v["class"] for k, v in steps.items()}
        if any(all(c[s] == "NOT_EVALUATED" for s in ss) for ss in tr.values()):
            return "NOT_EVALUATED"
        if any(v == "DEPENDENCE_FAILED" for v in c.values()):
            return "DEPENDENCE_FAILED"
        if all(any(c[s] == "CAPACITY STEP" for s in ss) for ss in tr.values()) and not any(v == "REVERSED" for v in c.values()) and self.a_use_largest(arm):
            return "CAPACITY_SUPPORTED"
        if any(v == "CAPACITY STEP" for v in c.values()):
            return "CAPACITY_ONE_TRANSITION"
        if any(all(c[s] in ("NOT LOADED", "NOT FULL WITHIN BUDGET") for s in ss) for ss in tr.values()):
            return "NOT_TESTED_BY_LOAD"
        if all(any(c[s] in ("NO GAIN", "REVERSED") for s in ss) for ss in tr.values()) and not any(v == "CAPACITY STEP" for v in c.values()):
            return "CAPACITY_NOT_SUPPORTED"
        return "INTERMEDIATE"

    # ---- dense comparison at the larger cell of each CAPACITY STEP (section 9.2)
    def dense_cell(self, arm, step):
        base, read = ("F-OQ", "ivf") if arm == "F-OQ-IVF" else (arm, "main")
        facts, large = int(step[1]), int(step[3])
        readings = ["MU", "MC-A"] + (["MC-T", "MC-C"] if self.mct else []) + ["D-BEST"]
        reps = []
        for d in range(1, self.R + 1):
            a, dq = self.spec(base, facts, large, d), self.spec("D-OQ", facts, large, d)
            u_p = int(a["u_p"])
            run_a, run_d = self.u_run(a), self.u_run(dq)
            mcs = self.mc_all("D-OQ", large, base, large, u_p, run_d, run_a, "second")
            dqf = {p: self.dep_failed(dq, "main", p) for p in PANELS}
            dd, st, blocked = {r: {} for r in readings}, {}, {r: False for r in readings}
            for p in PANELS:
                sa, sd = self.ser(a, read, p), self.ser(dq, "main", p)
                dd["MU"][p] = sa[u_p].i - sd[u_p].i
                blocked["MU"] |= u_p in dqf[p]
                best = max((u for u in sd if u <= run_d), key=lambda u: (sd[u].i, -u))
                dd["D-BEST"][p] = sa[u_p].i - sd[best].i
                blocked["D-BEST"] |= best in dqf[p]
                for r in ("MC-A", "MC-T", "MC-C"):
                    if r not in readings:
                        continue
                    m = mcs[r]
                    if m[2] != "OK":
                        dd[r][p] = None
                    else:
                        dd[r][p] = sa[m[1]].i - sd[m[0]].i
                        blocked[r] |= m[0] in dqf[p]
            for r in ("MC-A", "MC-T", "MC-C"):
                if r in readings:
                    st[r] = mcs[r][2]
            reps.append({"replicate": d, "d": dd, "status": st, "blocked": blocked})
        lead = self.th["dense_ahead_bits"]
        counts = {}
        for r in readings:
            counts[r] = sum(1 for x in reps if x["status"].get(r, "OK") == "OK" and any(v is not None and v <= lead for v in x["d"][r].values()))
        ahead_in = [r for r in readings if counts[r] >= self.MOST]
        if ahead_in:
            label = "DENSE AHEAD" if any(r in ("MC-A", "MC-T", "MC-C") for r in ahead_in) else "DENSE AHEAD (NOT AT MATCHED COMPUTE)"
        elif self.mct and all(all(x["status"].get(r, "OK") == "OK" and all(v is not None and v > lead for v in x["d"][r].values()) and not x["blocked"][r] for r in readings) for x in reps) and len(reps) >= self.ALL:
            label = "STORE NOT BEHIND"
        else:
            label = "DENSE COMPARISON SPLIT"
        return {"label": label, "counts": counts, "replicates": reps}

    def dense_sat(self, arm, cell):
        base, read = ("F-OQ", "ivf") if arm == "F-OQ-IVF" else (arm, "main")
        f, n = cell
        reps = []
        for d in range(1, self.R + 1):
            a, dq = self.spec(base, f, n, d), self.spec("D-OQ", f, n, d)
            fa, fd = self.full_info(a, read), self.full_info(dq, "main")
            la, ldq = fa["length"] or fa["u_run"], fd["length"] or fd["u_run"]
            dsat, ratio, blocked = {}, {}, False
            for p in PANELS:
                ia, idq = self.istar(a, read, p, la), self.istar(dq, "main", p, ldq)
                dsat[p] = ia - idq
                ratio[p] = None if idq <= 0 else ia / idq
                sd = self.ser(dq, "main", p)
                best = max((u for u in sd if u <= ldq), key=lambda u: (sd[u].i, -u))
                fails = self.dep_failed(dq, "main", p)
                blocked = blocked or best in fails or (self.u_run(dq) // 2) in fails
            cost_ok = self.mct and self.cost("T", "D-OQ", n) >= self.cost("T", base, n) and self.cost("A", "D-OQ", n) >= self.cost("A", base, n)
            reps.append({"replicate": d, "d_sat": dsat, "ratio": ratio, "dense_full": fd["full"], "cost_ok": bool(cost_ok), "blocked": blocked, "arm_length": la, "dense_length": ldq})
        holds = sum(1 for x in reps if any(v <= self.th["dense_ahead_bits"] for v in x["d_sat"].values()))
        if holds >= self.MOST:
            label = "DENSE HOLDS MORE AT SATURATION"
        elif self.mct and all(all(v is None or v >= self.th["beats_dense_ratio"] for v in x["ratio"].values()) and x["dense_full"] and x["cost_ok"] and not x["blocked"] for x in reps) and len(reps) >= self.ALL:
            label = "STORE HOLDS MORE AT SATURATION"
        else:
            label = "SAME AT SATURATION"
        return {"label": label, "annotation": "DENSE STILL RISING" if label == "SAME AT SATURATION" and any(not x["dense_full"] for x in reps) else None, "replicates": reps}

    def capacity_line(self):
        out = {}
        for arm in ("F-OQ", "F-OQ-IVF", "T-OQ", "H8"):
            steps = {s[0]: self.capacity_step(arm, s) for s in self.steps()}
            cls = self.arm_class(steps, arm)
            cap = [s for s in self.steps() if steps[s[0]]["class"] == "CAPACITY STEP"]
            cells = {self.cname(int(s[1]), int(s[3])): self.dense_cell(arm, s) for s in cap}
            sat = {self.cname(*c): self.dense_sat(arm, tuple(c)) for c in self.cfg["grid"]["loaded_cells"]}
            if not cap:
                arm_dense = "NOT APPLICABLE"
            elif any(v["label"].startswith("DENSE AHEAD") for v in cells.values()) or any(v["label"] == "DENSE HOLDS MORE AT SATURATION" for v in sat.values()):
                arm_dense = "DENSE AHEAD"
            elif all(v["label"] == "STORE NOT BEHIND" for v in cells.values()) and not any(v["label"] == "DENSE HOLDS MORE AT SATURATION" for v in sat.values()):
                arm_dense = "NOT BEHIND DENSE"
            else:
                arm_dense = "DENSE SPLIT"
            out[arm] = {"class": cls, "steps": {k: {"class": v["class"], "verdicts": v["verdicts"]} for k, v in steps.items()}, "steps_detail": steps, "capacity_steps": [s[0] for s in cap],
                        "dense_cells": cells, "dense_at_saturation": sat, "dense_arm": arm_dense, "a_use_largest_all": self.a_use_largest(arm)}
        three = ("F-OQ", "T-OQ", "F-OQ-IVF")
        if any(out[a]["class"] == "CAPACITY_SUPPORTED" and out[a]["dense_arm"] == "NOT BEHIND DENSE" for a in three):
            label = "CAPACITY-POSITIVE"
        elif (out["F-OQ"]["class"] == "CAPACITY_NOT_SUPPORTED" and out["T-OQ"]["class"] == "CAPACITY_NOT_SUPPORTED") or (
                any(out[a]["class"] == "CAPACITY_SUPPORTED" for a in three) and all(out[a]["dense_arm"] == "DENSE AHEAD" for a in three if out[a]["class"] == "CAPACITY_SUPPORTED")):
            label = "CAPACITY-NEGATIVE"
        elif all(out[a]["steps"][s]["class"] in ("NOT LOADED", "NOT FULL WITHIN BUDGET") for a in ("F-OQ", "T-OQ") for s in out[a]["steps"]):
            label = "CAPACITY NOT TESTED"
        else:
            label = "CAPACITY-INCONCLUSIVE"
        return {"outcome": label, "arms": out, "key_learning_limited": out["H8"]["class"] == "CAPACITY_SUPPORTED" and out["F-OQ"]["class"] != "CAPACITY_SUPPORTED", "matched_compute_in_mc_a_only": not self.mct}

    # ---- saturation (section 9.4)
    def saturation_line(self):
        sat256 = bool(self.plan.get("calibration", {}).get("sat256", True))
        pairs = {"F-OQ": [(256, 1024), (1024, 4096)], "F-OQ-IVF": [(1024, 4096)], "T-OQ": [(1024, 4096)], "H8": [(1024, 4096)]}
        cell_of = {tuple(c)[1]: tuple(c) for c in self.cfg["grid"]["saturation_cells"]}
        arms = {}
        for arm, prs in pairs.items():
            base, read = ("F-OQ", "ivf") if arm == "F-OQ-IVF" else (arm, "main")
            pout = {}
            for ns, nl in prs:
                cs, cl = cell_of[ns], cell_of[nl]
                nm = f"{self.size(ns)}→{self.size(nl)}"
                if ns == 256 and not sat256:
                    pout[nm] = {"class": "NOT FULL", "verdicts": ["NOT FULL"] * self.R, "note": "256 NOT MEASURED — NOT FULL WITHIN CEILING"}
                    continue
                vs, reps = [], []
                for d in range(1, self.R + 1):
                    side = []
                    for c in (cs, cl):
                        s = self.spec(base, c[0], c[1], d)
                        fi = self.full_info(s, read)
                        L = fi["length"] or fi["u_run"]
                        side.append({"s": s, "fi": fi, "S": {p: c[0] * self.istar(s, read, p, L) for p in PANELS}, "dep": bool(self.dep_any(s, read)), "leak": self.leakage(s, read)})
                    rho = {p: (math.inf if side[0]["S"][p] <= 0 else side[1]["S"][p] / side[0]["S"][p]) for p in PANELS}
                    if not (self.ref_ok(d, cs[0]) and self.ref_ok(d, cl[0])) or side[0]["leak"] or side[1]["leak"]:
                        v = "NOT_EVALUATED"
                    elif side[0]["dep"] or side[1]["dep"]:
                        v = "DEPENDENCE_FAILED"
                    elif not (side[0]["fi"]["loaded"] and side[1]["fi"]["loaded"]):
                        v = "NOT FULL"
                    elif all(rho[p] >= self.th["saturation_ratio"] for p in PANELS):
                        v = "PROPORTIONAL"
                    else:
                        v = "SUBPROPORTIONAL"
                    vs.append(v)
                    reps.append({"replicate": d, "verdict": v, "rho": rho, "S_small": side[0]["S"], "S_large": side[1]["S"], "full": [side[0]["fi"]["full"], side[1]["fi"]["full"]], "loaded": [side[0]["fi"]["loaded"], side[1]["fi"]["loaded"]]})
                cnt = lambda x: sum(v == x for v in vs)  # noqa: E731
                if cnt("NOT_EVALUATED") >= self.th["not_evaluated_min"]:
                    c_ = "NOT_EVALUATED"
                elif cnt("DEPENDENCE_FAILED") >= self.th["not_evaluated_min"]:
                    c_ = "DEPENDENCE_FAILED"
                elif cnt("NOT FULL") >= self.th["not_full_min"]:
                    c_ = "NOT FULL"
                elif cnt("PROPORTIONAL") >= self.ALL:
                    c_ = "PROPORTIONAL STEP"
                elif cnt("SUBPROPORTIONAL") >= self.MOST:
                    c_ = "SUBPROPORTIONAL STEP"
                else:
                    c_ = "MIXED"
                pout[nm] = {"class": c_, "verdicts": vs, "replicates": reps}
            cl_ = [v["class"] for v in pout.values()]
            if all(c in ("NOT FULL", "NOT_EVALUATED") for c in cl_):
                ac = "SATURATION_NOT_MEASURED"
            elif any(c == "DEPENDENCE_FAILED" for c in cl_):
                ac = "DEPENDENCE_FAILED"
            elif any(c == "SUBPROPORTIONAL STEP" for c in cl_):
                ac = "SATURATION_DOES_NOT_SCALE"
            elif all(c == "PROPORTIONAL STEP" for c in cl_):
                ac = "SATURATION_PROPORTIONAL_ALL_PAIRS"
            else:
                ac = "INTERMEDIATE"
            arms[arm] = {"class": ac, "pairs": pout}
        if any(arms[a]["class"] == "SATURATION_PROPORTIONAL_ALL_PAIRS" for a in ("F-OQ", "T-OQ", "F-OQ-IVF")):
            lab = "SATURATION-PROPORTIONAL"
        elif arms["F-OQ"]["class"] == arms["T-OQ"]["class"] == "SATURATION_DOES_NOT_SCALE":
            lab = "SATURATION-SUBPROPORTIONAL"
        elif arms["F-OQ"]["class"] == arms["T-OQ"]["class"] == "SATURATION_NOT_MEASURED":
            lab = "SATURATION NOT MEASURED"
        else:
            lab = "SATURATION-INCONCLUSIVE"
        return {"outcome": lab, "arms": arms}

    # ---- efficiency (section 9.5, ADR-0021 8.8)
    def u_t(self, s, dep_by_panel, panels=PANELS):
        """ADR-0021 8.8. Returns (kind, lo, hi, s_prev, s_hit, dep_flag): kind 'known' | 'left' | 'right'.
        A first snapshot with i >= i_T on the panels read at which a qualified DEP condition fails: dep_flag True and u_T is treated as
        right-censored (it never qualifies). This follows the study's reading after the first comparison (see NOTE.md): the ADR text says only that
        such a snapshot does not qualify and that row 2 (DEPENDENCE_FAILED) catches it; for the dense-speed label the right-censored reading is the
        one that cannot favour the store."""
        iT = self.th["efficiency_i_t"]
        us = self.snaps(s)
        prev = None
        for u in us:
            vals = {p: self.ser(s, "main", p)[u].i for p in panels}
            if all(v >= iT for v in vals.values()):
                if any(u in dep_by_panel[p] for p in panels):
                    return ("right", float(self.u_run(s)), math.inf, prev, u, True)
                if prev is None:
                    return ("left", 0.0, float(u), None, u, False)
                y0 = min(self.ser(s, "main", p)[prev].i for p in panels)
                y1 = min(vals.values())
                frac = (iT - y0) / (y1 - y0) if y1 > y0 else 1.0
                frac = max(0.0, min(1.0, frac))
                x0, x1 = math.log2(prev), math.log2(u)
                v = 2.0 ** (x0 + frac * (x1 - x0))
                return ("known", v, v, prev, u, False)
            prev = u
        return ("right", float(self.u_run(s)), math.inf, None, None, False)

    def eff_verdict(self, us, ul, run_s, run_l, cs, cl, refok, leak):
        if not refok or leak:
            return "NOT_EVALUATED"
        if us[5] or ul[5]:
            return "DEPENDENCE_FAILED"
        sl, sh = us[1], us[2]  # u_T(N) in [sl, sh] (left: (0, sh]; right: (sl, inf))
        ll, lh = ul[1], ul[2]
        if us[0] == "right" and ul[0] == "right":
            return "NOT_ASSESSED"
        f = self.th["efficiency_updates_factor"]
        cf = self.th["efficiency_cost_factor"]
        conds = []
        # row 4
        r4 = us[0] == "right" and lh <= run_s * f and lh * cl <= cf * cs * run_s
        # row 5: for every allowed value: u_T(4N) <= u_T(N)/2 and c_T(4N) <= 0.8 c_T(N)
        r5u = lh <= f * sl if sl > 0 else False
        r5 = r5u and lh * cl <= cf * sl * cs
        r6 = r5u
        # row 7: u_T(4N) >= 2 u_T(N) for every value; larger right-censored only if U_run(4N) >= 2 u_T(N)
        if ul[0] == "right":
            r7 = sh != math.inf and run_l >= 2 * sh
        else:
            r7 = sh != math.inf and ll >= 2 * sh
        censored = us[0] != "known" or ul[0] != "known"
        for name, ok in (("REACHED ONLY BY THE LARGER", r4), ("FASTER", r5), ("FASTER IN UPDATES ONLY", r6), ("SLOWER", r7)):
            conds.append((name, ok))
        if censored and not any(ok for _, ok in conds):
            return "NOT_ASSESSED"
        for name, ok in conds:
            if ok:
                return name
        return "SAME"

    def efficiency_line(self):
        readings = ["E-A"] + (["E-T"] if self.mct else [])
        steps_ = [s for s in self.steps() if s[0] in ("N1", "N2")]
        res = {}
        arm_cls, dense = {r: {} for r in readings}, {r: {} for r in readings}
        for r in readings:
            meas = "A" if r == "E-A" else "T"
            res[r] = {}
            for arm in ("F-OQ", "T-OQ"):
                st = {}
                for s in steps_:
                    facts, small, large = int(s[1]), int(s[2]), int(s[3])
                    vs, reps = [], []
                    for d in range(1, self.R + 1):
                        sm, lg = self.spec(arm, facts, small, d), self.spec(arm, facts, large, d)
                        us = self.u_t(sm, {p: self.dep_failed(sm, "main", p) for p in PANELS})
                        ul = self.u_t(lg, {p: self.dep_failed(lg, "main", p) for p in PANELS})
                        v = self.eff_verdict(us, ul, self.u_run(sm), self.u_run(lg), self.cost(meas, arm, small), self.cost(meas, arm, large), self.ref_ok(d, facts), self.leakage(sm, "main") or self.leakage(lg, "main"))
                        vs.append(v)
                        reps.append({"replicate": d, "verdict": v, "u_t_small": us[:3], "u_t_large": ul[:3]})
                    cnt = lambda *xs: sum(v in xs for v in vs)  # noqa: E731
                    if cnt("NOT_EVALUATED") >= self.th["not_evaluated_min"]:
                        c_ = "NOT_EVALUATED"
                    elif cnt("DEPENDENCE_FAILED") >= self.th["not_evaluated_min"]:
                        c_ = "DEPENDENCE_FAILED"
                    elif cnt("NOT_ASSESSED") >= self.th["not_evaluated_min"]:
                        c_ = "NOT_ASSESSED"
                    elif cnt("FASTER", "REACHED ONLY BY THE LARGER") >= self.ALL:
                        c_ = "FASTER STEP"
                    elif cnt("FASTER", "FASTER IN UPDATES ONLY") >= self.ALL:
                        c_ = "UPDATES-ONLY STEP"
                    elif cnt("SLOWER") >= self.MOST:
                        c_ = "SLOWER STEP"
                    elif cnt("SAME") >= self.MOST:
                        c_ = "NO DIFFERENCE"
                    else:
                        c_ = "MIXED"
                    st[s[0]] = {"class": c_, "verdicts": vs, "replicates": reps}
                c = {k: v["class"] for k, v in st.items()}
                if any(c[k] in ("NOT_EVALUATED", "NOT_ASSESSED") for k in c):
                    ac = "NOT_EVALUATED"
                elif any(v == "DEPENDENCE_FAILED" for v in c.values()):
                    ac = "DEPENDENCE_FAILED"
                elif all(c[k] == "FASTER STEP" for k in c) and not any(v == "SLOWER STEP" for v in c.values()):
                    ac = "EFFICIENCY_SUPPORTED"
                elif any(v == "FASTER STEP" for v in c.values()):
                    ac = "EFFICIENCY_ONE_TRANSITION"
                elif all(c[k] in ("SLOWER STEP", "NO DIFFERENCE") for k in c):
                    ac = "EFFICIENCY_NOT_SUPPORTED"
                else:
                    ac = "INTERMEDIATE"
                arm_cls[r][arm] = ac
                labels = {}
                for s in steps_:
                    if st[s[0]]["class"] != "FASTER STEP":
                        continue
                    facts, large = int(s[1]), int(s[3])
                    sure = poss_not = 0
                    fc = self.th["dense_faster_cost"]
                    for d in range(1, self.R + 1):  # per panel: DENSE FASTER counts a replicate if EITHER panel is sure; DENSE NOT FASTER needs BOTH panels (see NOTE.md)
                        a, dq = self.spec(arm, facts, large, d), self.spec("D-OQ", facts, large, d)
                        ca, cd = self.cost(meas, arm, large), self.cost(meas, "D-OQ", large)
                        blocked = bool(set().union(*(self.dep_failed(dq, "main", p) for p in PANELS)))
                        pa = [self.u_t(a, {p: self.dep_failed(a, "main", p)}, (p,)) for p in PANELS]
                        pd = [self.u_t(dq, {p: set()}, (p,)) for p in PANELS]  # ruling 17: D-OQ's own DEP never removes its qualification
                        if any(ud[2] * cd <= fc * ua[1] * ca for ua, ud in zip(pa, pd)):
                            sure += 1
                        if all(ud[1] * cd > fc * ua[2] * ca for ua, ud in zip(pa, pd)) and not blocked:
                            poss_not += 1
                    labels[self.cname(facts, large)] = "DENSE FASTER" if sure >= self.MOST else ("DENSE NOT FASTER" if poss_not >= self.ALL else "DENSE SPEED UNDECIDED")
                dense[r][arm] = labels
                res[r][arm] = {"class": ac, "steps": st, "dense_speed": labels}
        two = ("F-OQ", "T-OQ")
        if self.mct and any(arm_cls["E-A"][a] == "EFFICIENCY_SUPPORTED" and arm_cls["E-T"][a] == "EFFICIENCY_SUPPORTED" and all(v == "DENSE NOT FASTER" for r in readings for v in dense[r][a].values()) for a in two):
            lab = "EFFICIENCY-POSITIVE"
        elif any(all(arm_cls[r][a] == "EFFICIENCY_NOT_SUPPORTED" for a in two) for r in readings) or (
                any(all(arm_cls[r][a] == "EFFICIENCY_SUPPORTED" for r in readings) for a in two) and all(any(v == "DENSE FASTER" for r in readings for v in dense[r][a].values()) for a in two if all(arm_cls[r][a] == "EFFICIENCY_SUPPORTED" for r in readings))):
            lab = "EFFICIENCY-NEGATIVE"
        else:
            lab = "EFFICIENCY-INCONCLUSIVE"
        return {"outcome": lab, "readings": res, "e_a_only": not self.mct}

    # ---- sparse (section 9.6)
    def sparse(self):
        out = {}
        cells = [tuple(self.cfg["grid"]["u_p_larger_step_cell"][k]) for k in ("8192", "32768")]
        for tag in ("U_P", "run"):
            reps = []
            for d in range(1, self.R + 1):
                rr = {}
                for f, n in cells:
                    t, v = self.spec("T-OQ", f, n, d), self.spec("F-OQ", f, n, d)
                    u = int(t["u_p"]) if tag == "U_P" else self.u_run(t)
                    rr[self.cname(f, n)] = {p: (lambda it, iv: math.inf if iv <= 0 < it else (1.0 if iv <= 0 else it / iv))(self.ser(t, "main", p)[u].i, self.ser(v, "ivf", p)[u].i) for p in PANELS}
                reps.append(rr)
            def count(th_, c):
                return sum(1 for r in reps if all(x >= th_ for x in r[c].values()))
            names = [self.cname(f, n) for f, n in cells]
            k = self.th["sparse_ratio_min_replicates"]
            if all(count(self.th["tree_ahead_ratio"], c) >= k for c in names):
                lab = "AHEAD"
            elif all(count(self.th["tree_competitive_ratio"], c) >= k for c in names):
                lab = "COMPETITIVE"
            else:
                lab = "BEHIND"
            out[tag] = {"label": lab, "ratios": reps}
        return out

    def run(self):
        exp = []
        for c in self.cells:
            for u in self.snaps(c) if (not c["ladder_cell"] or self.cname(c["facts"], c["slots"]) in self.stops) else []:
                for read in (["main", "ivf"] if c["arm"] == "F-OQ" and c["slots"] != 256 else ["main"]):
                    p = self.run_dir / "evaluate" / c["label"] / f"u{u:08d}.json"
                    if not p.is_file():
                        self.missing.append(f"{c['label']}@{u}")
                    else:
                        if read not in json.loads(p.read_text())["reads"]:
                            self.missing.append(f"{c['label']}@{u}:{read}")
        # section 9.3 rows 1-2 and section 14: item errors refuse; a failed gate is an engineering failure; a failed cell or a missing record is INCOMPLETE
        item_err = sorted(str(p.relative_to(self.run_dir)) for p in self.run_dir.glob("*/item_errors/*.json"))
        gp = self.run_dir / "gates" / "gates.json"
        gates_ok = gp.is_file() and json.loads(gp.read_text()).get("passed") is True
        failed = sorted(str(p.parent.name) for p in self.run_dir.glob("train/cells/*/cell_failed.json"))
        no_dec = sorted({self.cname(c["facts"], c["slots"]) for c in self.cells if c["ladder_cell"]} - set(self.stops))
        out = {"mct_measured": self.mct, "replicates": self.R, "missing": self.missing[:50], "missing_count": len(self.missing), "missing_ladder_decisions": no_dec,
               "chance_intervals": {n: chance_interval(n) for n in (2048, 8192, 32768)}}
        out.update(item_errors=item_err, gates_passed=gates_ok, failed_cells=failed)
        if item_err:
            out["status"] = "ENGINEERING STOP — ITEM ERRORS"
            return out
        if not gates_ok:
            out["status"] = "ENGINEERING-FAILURE (gates record missing or not passed)"
            return out
        if self.missing or no_dec or failed:
            out["status"] = "INCOMPLETE"
            return out
        out["ladder_stop_check"] = {nm: {"recorded": self.stops[nm], "recomputed": self.recompute_stop(nm)} for nm in sorted(self.stops)}
        if any(v["recorded"] != v["recomputed"] for v in out["ladder_stop_check"].values()):
            out["status"] = "ENGINEERING-FAILURE (ladder stop differs)"
        self.compute_reference()
        out["reference_failed_dep"] = self.ref_failed
        out["capacity"] = self.capacity_line()
        out["saturation"] = self.saturation_line()
        out["efficiency"] = self.efficiency_line()
        out["sparse"] = self.sparse()
        out.setdefault("status", "COMPLETE")
        out["lines"] = {"C-CAPACITY": out["capacity"]["outcome"], "C-SATURATION": out["saturation"]["outcome"], "C-EFFICIENCY": out["efficiency"]["outcome"]}
        return out


def main():
    ap = argparse.ArgumentParser()
    for k in ("--run-dir", "--plan", "--config", "--qualification", "--madds", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--replicates", type=int, default=0)
    a = ap.parse_args()
    out = Recompute(a).run()
    Path(a.out).write_text(json.dumps(out, indent=1, sort_keys=True, default=lambda x: sorted(x) if isinstance(x, set) else str(x)))
    print(json.dumps({"status": out.get("status"), "lines": out.get("lines"), "missing_count": out.get("missing_count"), "ladder_stop_check": out.get("ladder_stop_check")}, indent=1))


if __name__ == "__main__":
    main()
