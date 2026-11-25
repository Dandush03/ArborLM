# ruff: noqa
"""Audit D0: one task. Outputs go to audit_d0_out/{gate,stats,passes}/ (new files only, each followed by a .done marker).

  gate <r> <o>   identities of ADR-0035 section 4 on the real snapshots (every query of both panels, per item as the scorer reads them) and the four
                 reproduction passes (M1 on E_first; M-append@append on E_first; M-append on E_first and E_second) compared with item_records.json.
  cell <r> <o>   refuses unless all six gate files exist and pass; then read statistics (section 5.2) and the 16 counted passes (section 4), one file
                 per pass; a pass whose file is done is skipped (resume).

Usage (from the D0 worktree): env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline python d0a_task.py gate 0 AB
"""
import json
import math
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d0a_lib as L  # noqa: E402
import torch  # noqa: E402

torch.set_num_threads(6)
torch.use_deterministic_algorithms(True)

FIRST_PASSES = [("M1", "reg"), ("app", "a"), ("app", "d1"), ("fin", "a"), ("fin", "b1"), ("fin", "c"), ("fin", "d1"), ("fin", "e1"), ("fin", "g1")]
SECOND_PASSES = [("fin", "a"), ("fin", "b2"), ("fin", "c"), ("fin", "d2"), ("fin", "e2"), ("fin", "g2"), ("fin", "e1")]


def pass_names():
    return [f"first__{s}__{c}" for s, c in FIRST_PASSES] + [f"second__{s}__{c}" for s, c in SECOND_PASSES]


def gate_ok(r, o):
    p = L.OUT / "gate" / f"gate_r{r}_{o}.json"
    if not Path(str(p) + ".done").exists():
        return False
    return json.loads(p.read_text())["gate_pass"] is True


class Cell:
    def __init__(self, r, o):
        self.r, self.o = r, o
        self.first, self.second = o[0], o[1]
        t0 = time.perf_counter()
        self.data = L.Data(check_hashes=True)
        self.model = L.Model(self.data)
        self.dec = L.Decoder(self.model)
        self.codes = L.Codes(L.BASES[r] + L.CODE_OFF)
        m1, i1 = L.load_snapshot(r, "M1", o)
        app, i2 = L.load_snapshot(r, "M-append", o, at_append=True)
        fin, i3 = L.load_snapshot(r, "M-append", o)
        self.inputs = [i1, i2, i3]
        self.raw = {"M1": m1, "app": app, "fin": fin}
        self.m1 = L.Store(m1)
        self.cond = {"app": L.Conditions(app), "fin": L.Conditions(fin)}
        self.panels = {c: self.data.panel(c) for c in (self.first, self.second)}
        self.load_seconds = time.perf_counter() - t0

    def item_reads(self, p):
        reads = L.oracle_reads(p)
        return reads, self.codes.queries(reads)

    def read_vectors(self, store, cond, p):
        reads, q = self.item_reads(p)
        if store == "M1":
            assert cond == "reg"
            return reads, self.m1.read(q)
        out = self.cond[store].compute(q)
        return reads, out["a_ref" if cond == "reg" else cond]

    def run_pass(self, store, cond, cap):
        prompts, refs = self.panels[cap]
        rec = {"items": [], "sequences": []}
        t0 = time.perf_counter()
        for p, rf in zip(prompts, refs):
            reads, rv = self.read_vectors(store, cond, p)
            add = L.scatter_add(rv, reads, len(p["ids"]), self.raw["M1"]["width"] if store == "M1" else self.raw[store]["width"])
            g = self.dec.decode(p["ids"], add)
            rec["items"].append(L.chrf(self.data.answer_text(g), rf))
            rec["sequences"].append(g)
        rec["seconds"] = time.perf_counter() - t0
        rec["mean"] = L.fmean(rec["items"])
        return rec


def do_gate(r, o):
    d = L.OUT / "gate"
    d.mkdir(exist_ok=True)
    path = d / f"gate_r{r}_{o}.json"
    if Path(str(path) + ".done").exists():
        print("done already", path)
        return
    T0 = time.perf_counter()
    C = Cell(r, o)
    checks = {}
    m1, app, fin = C.raw["M1"], C.raw["app"], C.raw["fin"]
    # stage-1 tensors of both M-append snapshots torch.equal to M1's
    for nm, st in (("app", app), ("fin", fin)):
        ok = all(torch.equal(st[f][0], m1[f][0]) for f in ("keys", "values", "gates")) and int(st["stage_rows"][0]) == int(m1["stage_rows"][0])
        checks[f"stage1_equal_M1[{nm}]"] = {"pass": bool(ok)}
    g2a = app["gates"][1]
    checks["g2_zero_at_append"] = {"pass": bool(torch.equal(g2a, torch.zeros_like(g2a))), "g2_append": g2a.tolist(), "g2_final": fin["gates"][1].tolist(),
                                   "g1": m1["gates"][0].tolist(), "stage_rows_app": list(map(int, app["stage_rows"])), "stage_rows_fin": list(map(int, fin["stage_rows"]))}
    # read identities on every query of both panels, computed per item exactly as scored
    agg = {k: {"pass": True, "queries": 0, "violations": 0, "max_dev": 0.0} for k in
           ("a_weightpath_equal_read[app]", "a_weightpath_equal_read[fin]", "b1_equal_M1[app]", "b1_equal_M1[fin]", "e1_equal_a[app]",
            "a_eq_e1_plus_e2[app]", "a_eq_e1_plus_e2[fin]")}
    rel_bound_max = 0.0
    for cap in (C.first, C.second):
        for p in C.panels[cap][0]:
            reads, q = C.item_reads(p)
            rm1 = C.m1.read(q)
            for nm in ("app", "fin"):
                out = C.cond[nm].compute(q)
                pairs = [(f"a_weightpath_equal_read[{nm}]", out["a"], out["a_ref"]), (f"b1_equal_M1[{nm}]", out["b1"], rm1)]
                if nm == "app":
                    pairs.append(("e1_equal_a[app]", out["e1"], out["a"]))
                for k, x, y in pairs:
                    a = agg[k]
                    a["queries"] += q.shape[0]
                    if not torch.equal(x, y):
                        a["pass"] = False
                        a["violations"] += 1
                    a["max_dev"] = max(a["max_dev"], float((x - y).abs().max()))
                k = f"a_eq_e1_plus_e2[{nm}]"
                dev = float((out["a"] - (out["e1"] + out["e2"])).abs().max())
                bound = 1e-6 * max(1.0, float(out["a"].abs().max()))
                agg[k]["queries"] += q.shape[0]
                agg[k]["max_dev"] = max(agg[k]["max_dev"], dev)
                rel_bound_max = max(rel_bound_max, dev / bound)
                if dev > bound:
                    agg[k]["pass"] = False
                    agg[k]["violations"] += 1
    checks.update(agg)
    checks["a_eq_e1_plus_e2_max_dev_over_bound"] = rel_bound_max
    # reproduction passes against the registered item records
    stored = json.loads((L.RUN / "item_records.json").read_text())["items"]
    repro = {}
    for label, store, cap, key in (("M1_first", "M1", C.first, f"M1|{o}|{r}|s:{L.PANEL[C.first]}"),
                                   ("app_first", "app", C.first, f"M-append@append|{o}|{r}|s:{L.PANEL[C.first]}"),
                                   ("fin_first", "fin", C.first, f"M-append|{o}|{r}|s:{L.PANEL[C.first]}"),
                                   ("fin_second", "fin", C.second, f"M-append|{o}|{r}|s:{L.PANEL[C.second]}")):
        rec = C.run_pass(store, "reg", cap)
        s = stored[key]
        dmax = max(abs(a - b) for a, b in zip(rec["items"], s["items"]))
        seqdiff = sum(1 for a, b in zip(rec["sequences"], s["sequences"]) if a != b)
        repro[label] = {"key": key, "n": len(rec["items"]), "n_stored": len(s["items"]), "max_abs_item_diff": dmax, "sequence_mismatches": seqdiff,
                        "mean_mine": rec["mean"], "mean_stored": L.fmean(s["items"]), "pass": bool(dmax <= 1e-6 and seqdiff == 0 and len(rec["items"]) == len(s["items"])),
                        "exact_zero": dmax == 0.0, "seconds": rec["seconds"], "items": rec["items"], "sequences": rec["sequences"]}
    gate_pass = all(v["pass"] for v in checks.values() if isinstance(v, dict)) and all(v["pass"] for v in repro.values())
    out = {"cell": [r, o], "gate_pass": gate_pass, "checks": checks, "reproduction": repro, "inputs": C.inputs, "load_seconds": C.load_seconds,
           "decode_calls": C.dec.calls, "memo_hits": C.dec.hits, "wall_seconds": time.perf_counter() - T0, "pid": os.getpid(), "torch": torch.__version__,
           "threads": torch.get_num_threads(), "deterministic": torch.are_deterministic_algorithms_enabled()}
    L.write_json_once(path, out)
    print(f"gate r{r} {o}: {'PASS' if gate_pass else 'FAIL'}", {k: v["pass"] for k, v in checks.items() if isinstance(v, dict)},
          {k: (v["max_abs_item_diff"], v["sequence_mismatches"]) for k, v in repro.items()}, f"{out['wall_seconds']:.0f}s")


def qstats(x):
    x = torch.tensor(x, dtype=torch.float64)
    return {"n": int(x.numel()), "mean": float(x.mean()), "median_linear": float(torch.quantile(x, 0.5)), "p05_linear": float(torch.quantile(x, 0.05)),
            "p95_linear": float(torch.quantile(x, 0.95)), "median_lower": float(torch.quantile(x, 0.5, interpolation="lower"))}


def read_stats(C, store, cap, p_):
    """Section 5.2 for protected stage p_ (1 on E_first, 2 on E_second); reference read R_ref = b(p_) (= M1's read when p_ = 1, gate-checked)."""
    o_ = 3 - p_
    n1 = C.cond[store].n1
    rows = {"word": {}, "marker": {}}
    tie_claim_viol = 0
    for p in C.panels[cap][0]:
        reads, q = C.item_reads(p)
        out = C.cond[store].compute(q)
        order, w, mask = out["_order"], out["_w"], out["_mask"]
        sub = C.cond[store].sub[p_]
        ref_order, _sel, ref_w = sub.select(q)
        if p_ == 2:
            ref_order = ref_order + n1  # global row index of stage-2 rows
        R = out[f"b{p_}"]
        Rn = R.norm(dim=-1)
        for i, (_pos, _t, j) in enumerate(reads):
            kind = "marker" if j == L.MARKER else "word"
            d = rows[kind]
            G = set(order[i].tolist())
            np_ = int(mask[p_][i].sum())
            kept = [int(x) for x in order[i][mask[p_][i]].tolist()]
            if sorted(kept) != sorted(ref_order[i][:np_].tolist()):
                tie_claim_viol += 1
            disp_w = float(sum(float(ref_w[i, k]) for k in range(L.TOP) if int(ref_order[i, k]) not in G))
            d.setdefault(f"n{p_}", []).append(np_)
            d.setdefault(f"m{p_}", []).append(float((w[i] * mask[p_][i]).sum()))
            d.setdefault("displaced_ref_weight", []).append(disp_w)
            d.setdefault("ref_top_row_kept", []).append(1.0 if int(ref_order[i, 0]) in G else 0.0)
            for x in ("a", "c", f"d{p_}", f"e{p_}", f"g{p_}"):
                d.setdefault(f"rel[{x}]", []).append(float((out[x][i] - R[i]).norm() / Rn[i]))
            d.setdefault(f"norm_e{o_}_over_ref", []).append(float(out[f"e{o_}"][i].norm() / Rn[i]))
            d.setdefault("ref_norm_zero", []).append(1.0 if float(Rn[i]) == 0.0 else 0.0)
    res = {kind: {k: qstats(v) for k, v in d.items()} for kind, d in rows.items()}
    res["G_cap_S_p_is_top_n_of_T8_violations"] = tie_claim_viol
    res["g1"] = C.raw[store]["gates"][0].tolist()
    res["g2"] = C.raw[store]["gates"][1].tolist()
    return res


def seed_memo_from_gate(C, r, o):
    """Seed the decode memo with MY OWN gate-pass sequences (registered read: M1 / app / fin, keyed by the bit-exact add tensor). A counted pass hits
    only if its add tensor is bit-identical; decoding is deterministic (the gate reproduced the registered sequences across processes)."""
    g = json.loads((L.OUT / "gate" / f"gate_r{r}_{o}.json").read_text())["reproduction"]
    n = 0
    for label, store, cap in (("M1_first", "M1", C.first), ("app_first", "app", C.first), ("fin_first", "fin", C.first), ("fin_second", "fin", C.second)):
        for p, seq in zip(C.panels[cap][0], g[label]["sequences"]):
            reads, rv = C.read_vectors(store, "reg", p)
            add = L.scatter_add(rv, reads, len(p["ids"]), C.raw[store]["width"])
            flat = add.contiguous().reshape(-1).tolist()
            key = (tuple(p["ids"]), L.hashlib.sha256(L.struct.pack(f"<{len(flat)}f", *flat)).hexdigest(), tuple(add.shape))
            C.dec.memo[key] = list(seq)
            n += 1
    print(f"seeded {n} memo entries from gate r{r} {o}", flush=True)
    return n


def do_cell(r, o):
    if not all(gate_ok(rr, oo) for rr, oo in L.CELLS):
        raise SystemExit("REFUSED: not every gate file exists and passes; no counterfactual is computed")
    T0 = time.perf_counter()
    C = Cell(r, o)
    seeded = seed_memo_from_gate(C, r, o)
    sd = L.OUT / "stats"
    sd.mkdir(exist_ok=True)
    sp = sd / f"stats_r{r}_{o}.json"
    if not Path(str(sp) + ".done").exists():
        t0 = time.perf_counter()
        st = {"append_first": read_stats(C, "app", C.first, 1), "final_first": read_stats(C, "fin", C.first, 1), "final_second": read_stats(C, "fin", C.second, 2)}
        st["seconds"] = time.perf_counter() - t0
        st["cell"] = [r, o]
        L.write_json_once(sp, st)
    pd = L.OUT / "passes"
    pd.mkdir(exist_ok=True)
    for name in pass_names():
        path = pd / f"r{r}_{o}__{name}.json"
        if Path(str(path) + ".done").exists():
            continue
        panel, store, cond = name.split("__")
        cap = C.first if panel == "first" else C.second
        h0, c0 = C.dec.hits, C.dec.calls
        rec = C.run_pass(store, cond, cap)
        rec.update({"cell": [r, o], "pass": name, "panel": L.PANEL[cap], "memo_hits": C.dec.hits - h0, "decode_calls": C.dec.calls - c0, "pid": os.getpid()})
        L.write_json_once(path, rec)
        print(f"r{r} {o} {name}: {rec['seconds']:.0f}s calls={rec['decode_calls']} hits={rec['memo_hits']}", flush=True)
    rec = {"cell": [r, o], "memo_seeded_from_gate": seeded, "wall_seconds": time.perf_counter() - T0, "load_seconds": C.load_seconds, "decode_calls": C.dec.calls, "memo_hits": C.dec.hits,
           "inputs": C.inputs, "pid": os.getpid(), "torch": torch.__version__, "threads": torch.get_num_threads(), "deterministic": torch.are_deterministic_algorithms_enabled()}
    L.write_json_once(L.OUT / "passes" / f"cellrun_r{r}_{o}_{int(time.time())}.json", rec)


def main():
    mode, r, o = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    assert o in ("AB", "BA")
    {"gate": do_gate, "cell": do_cell}[mode](r, o)


if __name__ == "__main__":
    main()
