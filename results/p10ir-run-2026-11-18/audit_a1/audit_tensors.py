# ruff: noqa
"""Brute-force float64 recomputation of P10-I-R A1 reads from the checkpoint tensors (auditor's own selection, weights, recall,
attention-mass, candidate and information code). The study code is called ONLY as the object under comparison (studies.p10ir.reads.tree_path,
for the per-fact gate-4-style comparison). P10-S1/P9 functions are used for the data draw, the backbone, loading model.pt, the oracle query
codes and the panel pass (derangement, address swap, answer scoring): the parts gate 2 already ties to P10-S1's registered counts.

Usage (one checkpoint per process):
  PYTHONPATH=<worktree> PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=<scratch>/pycache <worktree>/.venv/bin/python -B audit_tensors.py <T-OQ|F-OQ> <draw> <update>
"""
import json, math, os, sys, time
from pathlib import Path

import torch
from torch.nn import functional as F

torch.set_num_threads(1)
torch.set_num_interop_threads(1)
torch.use_deterministic_algorithms(True)

W = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1")
RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118")
S1 = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117")
EXP = Path("/Users/daniellaloush/dandush03/ArborLM/experiments")
OUT = Path(__file__).resolve().parent
TEMP, EPS, TOP, SOFT = 0.2, 1e-8, 8, 64
PER = 256
TIE, WTOL = 1e-5, 1e-6

from studies.p9 import controls, data as data_mod, core as p9core  # noqa: E402
from studies.p10s1 import core as s1core, evaluate as s1eval, index as s1index  # noqa: E402
from studies.p10s1.model import S1Memory, build_model  # noqa: E402
from studies.p10s1.train import load_model_state  # noqa: E402

arm, draw, update = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
FACTS, SLOTS = 32768, 16384
plan = json.load(open(W / "studies/p10ir/freeze/plan.json"))
item = [i for i in plan["items"]["A1"] if i["arm"] == arm and i["draw"] == draw and i["update"] == update and i["cell_name"] == "32K/16K"][0]
out = {"item": item["id"], "arm": arm, "draw": draw, "update": update, "torch": torch.__version__, "threads": torch.get_num_threads()}
t_start = time.monotonic()


# --- my float64 helpers ---------------------------------------------------------------------------------------------------
def unit64(x):
    x = x.detach().to(torch.float64)
    return x / x.norm(dim=-1, keepdim=True).clamp_min(EPS)


def top_ids(scores, k):
    """Top k per row by score descending, ties to the lower column id. Exact: topk(k+16), then lexicographic sort; rows whose (k+16)-th value equals the k-th fall back to a full stable sort."""
    extra = min(scores.shape[1], k + 16)
    vals, idx = scores.topk(extra, dim=1)
    # lexicographic (-score, id) within the candidates
    o1 = idx.argsort(dim=1, stable=True)
    vals, idx = vals.gather(1, o1), idx.gather(1, o1)
    o2 = (-vals).argsort(dim=1, stable=True)
    vals, idx = vals.gather(1, o2), idx.gather(1, o2)
    if extra < scores.shape[1]:
        unsafe = vals[:, k - 1] <= vals[:, extra - 1]
        if bool(unsafe.any()):
            full = (-scores[unsafe]).argsort(dim=1, stable=True)[:, :extra]
            idx[unsafe] = full
            vals[unsafe] = scores[unsafe].gather(1, full)
    return vals[:, :k], idx[:, :k]


def fano(acc):
    e = 1.0 - acc
    h = 0.0 if e <= 0 or e >= 1 else -(e * math.log2(e) + (1 - e) * math.log2(1 - e))
    return 5.0 - h - e * math.log2(31)


def chance_high(n, tests=40, alpha=0.001, p=1 / 32):
    tail, acc = alpha / tests / 2, 0.0
    for k in range(n, -1, -1):
        acc += math.exp(math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) + k * math.log(p) + (n - k) * math.log1p(-p))
        if acc > tail:
            return k


HIGH = chance_high(FACTS)


def bits(useful, n):
    return 0.0 if useful <= HIGH else fano(useful / n)


# --- data, model -------------------------------------------------------------------------------------------------------------
seeds = s1core.seed_set(item["seed_name"], item["seed_base"])
corpus = p9core.load_trained_corpus(EXP)
data = data_mod.build_study_data(seeds, corpus, sizes=data_mod.DataSizes(main_trained=item["table_facts"], unseen=item["unseen"], lane_d_per_set=s1core.LANE_D_STUB))
man = json.load(open(plan["draw_manifests"][item["seed_name"]]["path"]))
out["draw_hashes_equal_manifest"] = man["sha256s"] == data.sha256s()
_cwd = os.getcwd()
os.chdir(W)  # P5/P4 parent verification reads repository-relative records (read only); back to the scratch folder at once
try:
    backbone = controls.load_backbone(p9core.PRIMARY_PARENT, EXP)[0]
finally:
    os.chdir(_cwd)
model = build_model(arm, SLOTS, item["init_seed"], backbone, r1_seed=seeds.r1_codes, hash_seed=s1core.h8_seed(seeds), seed_rng=False)
snap = S1 / "cells" / item["cell"] / "snapshots" / s1core.snapshot_stem(update)
load_model_state(snap, model)
model.eval()
raw = torch.load(snap / "model.pt", weights_only=True, map_location="cpu")["model"]
src = model.addition
out["keys_equal_raw_tensor"] = bool(torch.equal(raw["addition.keys"], src.keys.detach()))
K = unit64(raw["addition.keys"])  # [N, 16]
RT = unit64(raw["addition.router"]) if arm == "T-OQ" else None
n_branches = SLOTS // PER
key_branch = torch.arange(SLOTS) // PER

all_ident = data.facts.ident
codes_all = s1eval.fact_codes(model, data, int(all_ident.shape[0]))  # [all facts, 16] float32 unit codes (the query)
codes = codes_all[:FACTS]
out["facts_in_table"] = int(all_ident.shape[0])
out["code_norm_max_dev"] = float((codes.double().norm(dim=1) - 1).abs().max())


# --- my tree read ------------------------------------------------------------------------------------------------------------
def tree_read(q32, v, ps, pw, k=SOFT):
    q = q32.to(torch.float64)
    cos = q @ K.T / TEMP
    routes = q @ RT.T / TEMP
    prior = routes.log_softmax(-1)
    _, border = top_ids(routes, n_branches)
    visited = border[:, :v]
    in_c = torch.zeros(q.shape[0], n_branches, dtype=torch.bool).scatter_(1, visited, True)[:, key_branch]
    kp = prior[:, key_branch]
    sel = (cos + kp) if ps else cos.clone()
    sel = sel.masked_fill(~in_c, -math.inf)
    _, ids = top_ids(sel, k)
    wsc = ((cos + kp) if pw else cos).gather(1, ids)
    sel_sc = sel.gather(1, ids)
    return ids, wsc, sel_sc, in_c, visited, routes


def flat_read(q32, cand=None, k=SOFT):
    q = q32.to(torch.float64)
    cos = q @ K.T / TEMP
    sc = cos if cand is None else cos.masked_fill(~cand, -math.inf)
    _, ids = top_ids(sc, k)
    return ids, cos.gather(1, ids), sc.gather(1, ids)


def ivf_mask(q32, idx, minimum):
    q = q32.to(torch.float64)
    unit = unit64(idx.centroids)
    sc = q @ unit.T
    order = (-sc).argsort(dim=1, stable=True)
    cum = idx.sizes.to(torch.int64)[order].cumsum(1)
    reached = cum >= minimum
    need = torch.where(reached.any(1), reached.to(torch.int64).argmax(1), torch.full((q.shape[0],), idx.lists - 1))
    rank = torch.empty_like(order).scatter_(1, order, torch.arange(idx.lists).expand(q.shape[0], -1).contiguous())
    visited = rank <= need[:, None]
    return visited.gather(1, idx.assign[None, :].expand(q.shape[0], -1)), cum.gather(1, need[:, None]).squeeze(1)


def exhaustive8(q32):
    q = q32.to(torch.float64)
    cos = q @ K.T / TEMP
    v, i = top_ids(cos, TOP)
    return i, v


# --- end-task through the panel pass, with my selection served per query ------------------------------------------------------
class MyMemory(S1Memory):
    def __init__(self, source, table_ids, table_w, row_of):
        super().__init__(source.spec, source.seed, r1_seed=source.r1_seed)
        self.load_state_dict(source.state_dict(), strict=True)
        self.table_ids, self.table_w, self.row_of = table_ids, table_w, row_of
        self.miss = 0
        self.fallback = None

    def _lookup(self, q):
        rows = []
        for r in q:
            key = tuple(r.tolist())
            j = self.row_of.get(key)
            if j is None:
                self.miss += 1
                j = -1
            rows.append(j)
        rows = torch.tensor(rows)
        ids = torch.empty(q.shape[0], SOFT, dtype=torch.int64)
        w = torch.empty(q.shape[0], SOFT, dtype=torch.float32)
        ok = rows >= 0
        ids[ok] = self.table_ids[rows[ok]]
        w[ok] = self.table_w[rows[ok]].to(torch.float32)
        if bool((~ok).any()):
            fi, fw = self.fallback(q[~ok])
            ids[~ok], w[~ok] = fi, fw.to(torch.float32)
        return w, ids

    def _top_tree(self, q):
        w, ids = self._lookup(q)
        return w, ids, torch.zeros(q.shape[0], 2, dtype=torch.int64), torch.zeros(q.shape[0], n_branches)

    def _top_flat(self, q):
        return self._lookup(q)


row_of = {tuple(row): j for j, row in enumerate(codes_all.tolist())}
pi = s1eval._deranged(data, FACTS, s1core.mask_seed(seeds, 0))


def end_task(table_ids, table_w, fallback):
    mem = MyMemory(src, table_ids, table_w, row_of)
    mem.fallback = fallback
    old = model.addition
    model.addition = mem
    res = {}
    try:
        for panel in s1core.PANELS:
            stream = s1eval.stream_for(data, FACTS, s1core.PANEL_STREAM[panel])
            c = s1eval.panel_counts(model, data, FACTS, stream, pi=pi, tables=None)
            res[panel] = {"n": int(c["n"]), "correct": int(c["correct"]), "useful": int(c["useful"]), "i": bits(int(c["useful"]), int(c["n"])), "a_use": int(c["useful"]) / int(c["n"])}
    finally:
        model.addition = old
    res["lookup_misses"] = mem.miss
    return res


def recorded(name):
    return json.load(open(RUN / "a1" / "items" / f"A1__{item['cell']}__u{update:07d}" / f"read.{name.replace('/', '~')}.json"))


def compare_counts(mine, rec):
    return {p: {"mine_correct": mine[p]["correct"], "rec_correct": rec["panels"][p]["correct"], "mine_useful": mine[p]["useful"], "rec_useful": rec["panels"][p]["useful"],
                "mine_i": round(mine[p]["i"], 6), "rec_i": round(float(rec["panels"][p]["i"]), 6)} for p in ("A", "B")}


CH = 512
if arm == "T-OQ":
    from studies.p10ir import reads as p10ir_reads  # the object under comparison only

    specs = {"T0": (2, True, True), "T1": (2, False, False), "T1w": (2, True, False), "T3": (64, True, True), "T2": (64, False, False),
             "Tv1_on": (1, True, True), "Tv1_off": (1, False, False), "Tv4_on": (4, True, True), "Tv4_off": (4, False, False), "Tv8_on": (8, True, True), "Tv8_off": (8, False, False)}
    keys32, router32 = src.keys.detach(), src.router.detach()
    results = {}
    store = {}
    # exhaustive E8 once
    E_ids, E_vals = [], []
    for s in range(0, FACTS, CH):
        i, v = exhaustive8(codes[s:s + CH])
        E_ids.append(i); E_vals.append(v)
    E_ids, E_vals = torch.cat(E_ids), torch.cat(E_vals)
    wE = E_vals.softmax(-1)
    for name, (v, ps, pw) in specs.items():
        t0 = time.monotonic()
        ids_all, w_all, sel_all, stats = [], [], [], {k: [] for k in ("cr8", "cr1", "sr8", "am_c", "am_s", "span")}
        g4 = {"facts": 0, "sets_differ": 0, "float_ties": 0, "not_float_ties": 0, "max_weight_diff": 0.0}
        for s in range(0, codes_all.shape[0], CH):
            q = codes_all[s:s + CH]
            ids, wsc, selsc, in_c, visited, routes = tree_read(q, v, ps, pw)
            ids_all.append(ids); w_all.append(wsc); sel_all.append(selsc)
            if s < FACTS:
                n_here = min(CH, FACTS - s)
                e = E_ids[s:s + n_here]
                c8 = in_c[:n_here].gather(1, e)
                sel8 = ids[:n_here, :TOP]
                s_in_e = (sel8[:, :, None] == e[:, None, :]).any(1)
                stats["cr8"].append(c8.double().mean(1)); stats["cr1"].append(c8[:, 0].double())
                stats["sr8"].append((sel8[:, :, None] == e[:, None, :]).any(-1).double().mean(1))
                stats["am_c"].append((c8.double() * wE[s:s + n_here]).sum(1)); stats["am_s"].append((s_in_e.double() * wE[s:s + n_here]).sum(1))
                br = sel8 // PER
                stats["span"].append((br.min(1).values != br.max(1).values).double())
                # gate-4-style comparison with the study's float32 path, per fact
                ref = p10ir_reads.tree_path(keys32, router32, q[:n_here], v, ps, pw, per=PER, chunk_elements=1 << 20)
                a_set, _ = sel8.sort(1)
                b_set, ob = ref.ids[:, :TOP].sort(1)
                same = (a_set == b_set).all(1)
                # tie: 8th and 9th selection scores within 1e-5 in either computation (theirs: recompute selection scores of their 9 in float32)
                gap_mine = (selsc[:n_here, TOP - 1] - selsc[:n_here, TOP]).abs()
                cos32 = (F.normalize(keys32, dim=-1, eps=EPS)[ref.ids[:, :TOP + 1]] @ q[:n_here].unsqueeze(-1)).squeeze(-1) / TEMP
                pr32 = ref.routes.log_softmax(-1).gather(1, ref.ids[:, :TOP + 1] // PER) if ps else 0.0
                s32 = cos32 + pr32
                gap_theirs = (s32[:, TOP - 1] - s32[:, TOP]).abs()
                tie = (gap_mine <= TIE) | (gap_theirs <= TIE)
                g4["facts"] += n_here
                g4["sets_differ"] += int((~same).sum()); g4["float_ties"] += int((~same & tie).sum()); g4["not_float_ties"] += int((~same & ~tie).sum())
                wa = wsc[:n_here, :TOP].softmax(-1).gather(1, sel8.argsort(1))
                wb = ref.values[:, :TOP].to(torch.float64).softmax(-1).gather(1, ob)
                if bool(same.any()):
                    g4["max_weight_diff"] = max(g4["max_weight_diff"], float((wa - wb).abs().max(1).values[same].max()))
        ids_all, w_all = torch.cat(ids_all), torch.cat(w_all)
        store[name] = (ids_all[:FACTS, :TOP], w_all[:FACTS, :TOP])
        facts = {k: float(torch.cat(x).mean()) for k, x in stats.items()}
        rec = recorded(name)
        fb = (lambda q, v=v, ps=ps, pw=pw: tree_read(q, v, ps, pw)[:2])
        et = end_task(ids_all, w_all, fb)
        results[name] = {"facts_mine": facts, "facts_recorded": rec["facts"], "gate4_vs_study_path": g4, "counts": compare_counts(et, rec), "lookup_misses": et["lookup_misses"], "seconds": round(time.monotonic() - t0, 1)}
        print(name, json.dumps(results[name]), flush=True)
    # pair statistics (section 7): T0 vs T1, T1w, T3; T3 vs T2
    def pair(a, b):
        ai, aw = store[a]; bi, bw = store[b]
        aw, bw = aw.softmax(-1), bw.softmax(-1)
        m = ai[:, :, None] == bi[:, None, :]
        changed = ~m.any(-1).all(-1)
        w_b_at_a = (m.double() * bw[:, None, :]).sum(-1)
        tv = 0.5 * ((aw - w_b_at_a).abs().sum(1) + (bw * (~m.any(1)).double()).sum(1))
        return float(changed.double().mean()), float(tv.mean())
    for a, b in (("T1", "T0"), ("T1w", "T0"), ("T3", "T0"), ("T2", "T3")):
        ch, tv = pair(a, b)
        results[a]["pair_mine"] = {"against": b, "share_selected_changed": ch, "tv_mean": tv}
        results[a]["pair_recorded"] = recorded(a).get("pair")
    # P10-S1's recorded tree recall at U_P (seal lifted for this study's registered stages): compare with my float64 version of its definition
    ev = S1 / "cells" / item["cell"] / "eval" / f"u{update:07d}" / "eval.json"
    try:
        rec_tr = json.load(open(ev))["reads"]["main"]["deep"]["separability"].get("tree_recall_of_exhaustive_top8")
    except Exception as exc:  # noqa: BLE001
        rec_tr = f"absent ({type(exc).__name__})"
    out["p10s1_tree_recall_recorded"] = rec_tr
    out["my_cr8_T0"] = results["T0"]["facts_mine"]["cr8"]
    out["reads"] = results
else:
    results = {}
    E_ids, E_vals = [], []
    for s in range(0, FACTS, CH):
        i, v = exhaustive8(codes[s:s + CH])
        E_ids.append(i); E_vals.append(v)
    E_ids, E_vals = torch.cat(E_ids), torch.cat(E_vals)
    wE = E_vals.softmax(-1)
    # F0
    t0 = time.monotonic()
    ids_all, w_all = [], []
    for s in range(0, codes_all.shape[0], CH):
        ids, wsc, _ = flat_read(codes_all[s:s + CH])
        ids_all.append(ids); w_all.append(wsc)
    ids_all, w_all = torch.cat(ids_all), torch.cat(w_all)
    et = end_task(ids_all, w_all, lambda q: flat_read(q)[:2])
    results["F0"] = {"counts": compare_counts(et, recorded("F0")), "lookup_misses": et["lookup_misses"], "facts_recorded": recorded("F0")["facts"],
                     "facts_mine": {"sr8": float((ids_all[:FACTS, :TOP].sort(1).values == E_ids.sort(1).values).all(1).double().mean())}, "seconds": round(time.monotonic() - t0, 1)}
    print("F0", json.dumps(results["F0"]), flush=True)
    seed = 298001
    idx = s1index.build_index(src.keys.detach(), seed, SLOTS // 64)
    for budget in (512, 2048):
        name = f"I64@{budget}/s{seed}"
        rec = recorded(name)
        t0 = time.monotonic()
        ids_all, w_all, st = [], [], {k: [] for k in ("cr8", "cr1", "sr8", "am_c", "am_s", "cand")}
        cand_diff = 0
        for s in range(0, codes_all.shape[0], CH):
            q = codes_all[s:s + CH]
            mask, cnt = ivf_mask(q, idx, budget)
            ids, wsc, _ = flat_read(q, mask)
            ids_all.append(ids); w_all.append(wsc)
            if s < FACTS:
                n_here = min(CH, FACTS - s)
                m32, c32 = s1index.candidate_mask(idx, q[:n_here], budget)  # the object under comparison: P10-S1's float32 mask
                cand_diff += int((m32 != mask[:n_here]).any(1).sum())
                e = E_ids[s:s + n_here]
                c8 = mask[:n_here].gather(1, e)
                sel8 = ids[:n_here, :TOP]
                st["cr8"].append(c8.double().mean(1)); st["cr1"].append(c8[:, 0].double())
                st["sr8"].append((sel8[:, :, None] == e[:, None, :]).any(-1).double().mean(1))
                st["am_c"].append((c8.double() * wE[s:s + n_here]).sum(1))
                st["am_s"].append(((sel8[:, :, None] == e[:, None, :]).any(1).double() * wE[s:s + n_here]).sum(1))
                st["cand"].append(cnt[:n_here].double())
        ids_all, w_all = torch.cat(ids_all), torch.cat(w_all)
        cand = torch.cat(st.pop("cand"))
        facts = {k: float(torch.cat(x).mean()) for k, x in st.items()}
        et = end_task(ids_all, w_all, lambda q, b=budget: flat_read(q, ivf_mask(q, idx, b)[0])[:2])
        results[name] = {"index_sha256_equal_record": idx.sha256() == rec.get("index_sha256"), "facts_mine": facts, "facts_recorded": rec["facts"],
                         "candidates_facts_mine": {"mean": float(cand.mean()), "p99": float(torch.quantile(cand, 0.99))}, "candidates_facts_recorded": rec.get("candidates_facts"),
                         "facts_whose_float64_candidate_set_differs_from_p10s1_float32_mask": cand_diff,
                         "counts": compare_counts(et, rec), "lookup_misses": et["lookup_misses"], "seconds": round(time.monotonic() - t0, 1)}
        print(name, json.dumps(results[name]), flush=True)
    out["reads"] = results
out["seconds"] = round(time.monotonic() - t_start, 1)
(OUT / f"tensors_{arm}_d{draw}_u{update}.json").write_text(json.dumps(out, indent=1))
print("DONE", out["seconds"])
