"""Work counters, the index rule, the address swap and panel independence (ADR-0021 sections 5.5, 6.3, 7.1, 7.4), checked by the auditor's own means:

1. K and W from the matmul FLOPs of the read (torch FlopCounterMode) at 4,096 / 16,384 / 65,536 slots, against the counters and the section 7.4 table.
2. The IVF candidate rule by brute force (lists in descending centroid cosine until >= 512 keys) against index.candidate_mask; the IVF top-8 equals the
   top-8 by cosine among the brute-force candidates.
3. The address swap: only identifier bytes 8r+1..8r+4 of records of trained facts change, to pi(f)'s; pi has no fixed point and different answers;
   D-OQ's swapped read is the code of pi(f).
4. Panels disjoint from training by a hash of the 64 token bytes (not by fact ids), over a full registered-length run (6 x 8,192 updates) of a small
   test-seed draw; H1/H2 separator and binding bytes absent from training contexts.

Real frozen backbone; test seeds p10s1-test-7 (base 921701). Run:
PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c7_counters_leakage.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import sys

import torch
from torch.nn import functional as F
from torch.utils.flop_counter import FlopCounterMode

from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9 import data as d
from studies.p10s1 import core, index
from studies.p10s1 import model as M
from studies.p10s1 import train as T

torch.set_num_threads(1)
CORPUS = bytes((i * 7 + 3) % 256 for i in range(p9core.CORPUS_ROW_BYTES * 64))
FACTS = 1024


def counters(backbone, data):
    seeds = data.seeds
    tok = T.training_stream_for(data, FACTS).batch(1).tokens[:, :63].contiguous()
    q = tok.shape[0] * 8
    lut = T.fact_lut_for(data, FACTS)
    out = {}
    for n in (4096, 16384, 65536):
        for arm in ("F-OQ", "T-OQ", "H8", "R2", "D-OQ"):
            m = M.build_model(arm, n, 2101, backbone, fact_lut=lut if arm == "R2" else None, r1_seed=seeds.r1_codes, hash_seed=core.h8_seed(seeds), seed_rng=False)
            m.eval()
            with torch.no_grad():
                h = m.embed_block0(tok)
                fc = FlopCounterMode(display=False)
                with fc:
                    read = m.select(h, tok)
                    delta = m.memory_delta(h, read)
                flops = fc.get_total_flops()
            m.counters.reset()
            with torch.no_grad():
                m(tok)
            c = m.counters.per_query()
            if arm == "D-OQ":
                hid = m.addition.hidden
                own_w = flops / 2 / q  # 16 h + 32 h
                out[f"{arm}|{n}"] = {"flop_W_per_query": own_w, "counter_W": c["W"], "table_W": 48 * hid, "ok": abs(own_w - 48 * hid) < 1e-6 and c["W"] == 48 * hid}
            else:
                v = int(read.selected.shape[-1])
                own_k = (flops / 2 / q - 32 * 32) / 16  # read matmuls: K key scores of width 16 plus the 32x32 output projection
                table_k = {"F-OQ": n, "T-OQ": n // 256 + 512, "H8": 0, "R2": 0}[arm]
                table_v = {"F-OQ": 8, "T-OQ": 8, "H8": 8, "R2": 1}[arm]
                own_w = 16 * own_k + 32 * v + 1024
                out[f"{arm}|{n}"] = {"flop_K": own_k, "selected_V": v, "counter_K": c["K"], "counter_V": c["V"], "table_K": table_k, "table_V": table_v, "own_W": own_w, "counter_W": c["W"],
                                     "ok": abs(own_k - table_k) < 1e-6 and v == table_v and c["K"] == table_k and c["V"] == table_v}
    return out


def ivf_check(seed=921777):
    g = torch.Generator().manual_seed(seed)
    out = {}
    for n in (4096, 16384):
        keys = torch.randn(n, 16, generator=g)
        keys[: n // 8] += 3 * torch.randn(1, 16, generator=g)  # one dense region so that lists are unequal
        idx = index.build_index(keys, seed)
        qs = F.normalize(torch.randn(256, 16, generator=g), dim=-1)
        mask, cnt = index.candidate_mask(idx, qs)
        bad = 0
        for i in range(qs.shape[0]):
            sc = (qs[i] @ idx.unit.T).tolist()
            order = sorted(range(idx.lists), key=lambda j: (-sc[j], j))
            got, lists = 0, []
            for j in order:
                lists.append(j)
                got += int(idx.sizes[j])
                if got >= 512:
                    break
            cand = torch.isin(idx.assign, torch.tensor(lists))
            if not torch.equal(cand, mask[i]) or int(cand.sum()) != int(cnt[i]):
                bad += 1
        # IVF memory top-8 equals top-8 among the brute-force candidates
        src = M.S1Memory(M.spec_for("F-OQ", n), 2101, r1_seed=7)
        with torch.no_grad():
            src.keys.copy_(keys)
        idx2 = index.build_index(src.keys.detach(), seed)
        ivf = index.IVFMemory(src, idx2)
        v, ids = ivf._top_flat(qs)
        m2, _ = index.candidate_mask(idx2, qs)
        s = (qs @ F.normalize(keys, dim=-1).T) / 0.2
        s = s.masked_fill(~m2, -torch.inf)
        top = s.topk(8, dim=1)
        same = bool(torch.equal(torch.sort(ids[:, :8], dim=1).values, torch.sort(top.indices, dim=1).values))
        meas = ivf.measured()
        out[n] = {"lists": idx.lists, "candidate_rule_mismatches": bad, "mean_candidates": float(cnt.float().mean()), "min_candidates": int(cnt.min()), "top8_equal": same,
                  "K_mean_measured": meas["K_mean"], "K_expected": idx2.lists + meas["candidates_mean"], "recall": meas["recall_of_exhaustive_top8"]}
    return out


def swap_check(backbone, data):
    stream = d.restrict_stream(data.streams["panel_a"], data.facts, FACTS)
    tok = stream.tokens[:64, :63].contiguous()
    ids = stream.fact_ids[:64]
    answers = data.facts.answer[:FACTS]
    pi = M.derangement(answers, core.mask_seed(data.seeds, 0))
    sw = M.swapped_tokens(tok, ids, pi, data.facts.ident, FACTS)
    diff = (sw != tok)
    allowed = torch.zeros(63, dtype=torch.bool)
    for r in range(8):
        allowed[8 * r + 1: 8 * r + 5] = True
    pos_ok = bool((diff & ~allowed[None, :]).sum() == 0)
    rec_untrained_changed = 0
    for r in range(8):
        rows = ids[:, r] >= FACTS
        rec_untrained_changed += int(diff[rows][:, 8 * r: 8 * r + 8].sum())
    # identifier of pi(f)
    from studies.p9.model import identifier_codes
    from studies.p9.data import encode_identifiers
    codes_sw = identifier_codes(sw)
    want = encode_identifiers(data.facts.ident[pi[ids.clamp_max(FACTS - 1)]].reshape(-1, 5)).reshape(ids.shape)  # attempt 2: reshape (attempt 1 passed [64, 8, 5])
    trained = ids < FACTS
    ident_ok = bool(torch.equal(codes_sw[trained], want[trained]))
    doq = M.build_model("D-OQ", 4096, 2101, backbone, r1_seed=data.seeds.r1_codes, seed_rng=False)
    c_sw = doq.oracle_codes(sw)
    c_want = M.OracleCodes(data.seeds.r1_codes).of_codes(want.reshape(-1)).reshape(*want.shape, 16)
    return {"pi_fixed_points": int((pi == torch.arange(FACTS)).sum()), "pi_same_answer": int((answers[pi] == answers).sum()), "pi_is_permutation": bool(torch.equal(torch.sort(pi).values, torch.arange(FACTS))),
            "only_identifier_bytes_change": pos_ok, "untrained_records_changed_bytes": rec_untrained_changed, "swapped_identifier_is_pi_f": ident_ok, "doq_code_is_pi_f": bool(torch.equal(c_sw[trained], c_want[trained]))}


def row_hash(t):
    t = t.to(torch.int64)
    h = torch.zeros(t.shape[0], dtype=torch.int64)
    for j in range(t.shape[1]):
        h = (h * 1000003 + t[:, j] + 1) & ((1 << 61) - 1)
    return h


def disjoint_check(data):
    sched = T.training_stream_for(data, FACTS)
    updates = 6 * 8192
    hs = []
    seps = set()
    for u in range(1, updates + 1, 1):
        b = sched.batch(u).tokens
        hs.append(row_hash(b))
        if u <= sched.updates_per_epoch * 4:
            seps |= set(b[:, 0::8].reshape(-1).tolist())
    train_h = torch.unique(torch.cat(hs))
    out = {"training_contexts": int(sum(x.numel() for x in hs)), "distinct_training_contexts": int(train_h.numel()), "updates_per_epoch": sched.updates_per_epoch}
    for name in ("panel_a", "panel_b", "h1", "h2", "calibration"):
        st = data.streams[name]
        ph = row_hash(st.tokens)
        out[f"{name}_contexts"] = int(ph.numel())
        out[f"{name}_in_training"] = int(torch.isin(ph, train_h).sum())
    for a, b in (("panel_a", "panel_b"), ("panel_a", "h1"), ("h1", "h2")):
        out[f"{a}_vs_{b}"] = int(torch.isin(row_hash(data.streams[a].tokens), row_hash(data.streams[b].tokens)).sum())
    return out


def main():
    root = p9core.default_experiments_root()
    backbone, _ = controls.load_backbone(p9core.PRIMARY_PARENT, root)
    data = d.build_study_data(core.test_seeds(7), CORPUS, sizes=d.DataSizes(main_trained=FACTS, unseen=64, lane_d_per_set=128))
    out = {"counters": counters(backbone, data)}
    out["counters_all_ok"] = all(v["ok"] for v in out["counters"].values())
    out["ivf"] = ivf_check()
    out["swap"] = swap_check(backbone, data)
    out["disjoint"] = disjoint_check(data)
    json.dump(out, sys.stdout, indent=1, default=str)
    print()


if __name__ == "__main__":
    main()
