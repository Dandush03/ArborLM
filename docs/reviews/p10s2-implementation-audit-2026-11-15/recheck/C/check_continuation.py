"""Re-check auditor C: scoring under continuation (combined-tasks addendum s4.1, s11 item 3) on the synthetic stand-in
world, with arms whose parameters are randomized so that they change the outputs (seeds 229301..). For every arm type:
my own full recomputation of step 2 (a plain non-cached greedy loop written here over student.forward) against
combined.run_c1/run_c2 (the cache continuation), at the frozen stand-in limit and at forced small limits so that the
first answer hits the limit. Also: the read positions of step 2 against the addendum formula (my own derivation),
L-sep on C2 against my own construction, C1 first answers against single-task answers, C2 first answers of
adapter arms against their single-task answers, and _kind_record's summary fields against my own computation.
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
Usage: <python> check_continuation.py <pin>"""

import sys
from collections import Counter

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")

import torch  # noqa: E402

from studies.p10s2 import cells, combined, core, evaluate, memory, standins  # noqa: E402
from studies.p10s2.model import PositionAdapter  # noqa: E402

torch.set_num_threads(2)
import os
world, rec = standins.build_synthetic_world(replicates=1, add_bos=bool(os.environ.get("BOS")))
ctx = world.ctx
ctx.seed_plan = core.SeedPlan("test", 0)
cs = ctx.ec
st = ctx.student
table = ctx.decoder.table
W = world.cfg.width


def g(seed):
    return torch.Generator().manual_seed(seed)


def store_arm(seed, stages=2, rows=16):
    s = memory.SparseStore.new(W, rows, g(seed))
    for k in range(1, stages):
        s.append_stage(rows, g(seed + 50 + k))
    with torch.no_grad():
        for k in range(stages):
            s.values[k].copy_(0.8 * torch.randn(s.values[k].shape, generator=g(seed + 100 + k)))
            s.gates[k].fill_(1.0)
    return memory.MemoryArm(s, world.layer, world.codes(0))


def lora_arm(seed):
    ad = memory.LoRAAdapter(world.cfg, 4, g(seed))
    with torch.no_grad():
        for k, b in enumerate(ad.b):
            b.copy_(0.5 * torch.randn(b.shape, generator=g(seed + 1000 + k)))
    return memory.LoRAArm(ad)


ARMS = {
    "Stage 0 (NullArm)": memory.NullArm(),
    "M-append-frozen / M-ii (2-stage store)": store_arm(229301),
    "M-joint (one 2N store)": store_arm(229311, stages=1, rows=32),
    "M-i-separate (CompositeStoreArm)": cells.CompositeStoreArm({"A": store_arm(229321, 1), "B": store_arm(229331, 1)}),
    "L-joint / L-seq (one LoRA)": lora_arm(229341),
    "L-sep (AdapterRouteArm)": cells.AdapterRouteArm({"A": lora_arm(229351), "B": lora_arm(229361)}),
}


@torch.no_grad()
def plain_greedy(ids, add_rows, adapter, max_new, layer):
    """My reference decoder: every step recomputes the whole sequence; add_rows: {pos: vector}; generated positions are never read."""
    st.read_layer = layer
    out = []
    seq = list(ids)
    for _ in range(max_new):
        add = None
        if add_rows:
            add = torch.zeros(1, len(seq), W)
            for p, v in add_rows.items():
                add[0, p] += v
        logits = st(torch.tensor([seq]), add=add, adapter=adapter)
        nxt = int(torch.argmax(logits[0, -1]))
        out.append(nxt)
        if b"\n" in table[nxt]:
            break
        seq.append(nxt)
    return out


def answer(gen):
    for k, t in enumerate(gen):
        if b"\n" in table[t]:
            return gen[:k], False
    return list(gen), True


def add_of(arm, reads, length):
    add, adapter = arm.prepare([reads], 1, length, torch.device("cpu"), None)
    rows = {} if add is None else {p: add[0, p].clone() for p in range(length) if add[0, p].abs().sum() > 0}
    return rows, adapter


def bos(ex):
    return len(ex.segments[0].ids) if ex.segments and ex.segments[0].text == "<bos>" else 0


def my_c1(arm, pair, max_new):
    """My construction of C1 from the addendum: step 1 P_T1(s1); step 2 = [BOS] E S(s1) NL M_T1 a1 NL E S(s2) NL M_T2 with reads at
    stored positions + offset; recomputed in full."""
    ex1, ex2 = cs.sentences[pair.i1].ex[pair.t1], cs.sentences[pair.i2].ex[pair.t2]
    nl = list(ctx.newline_ids)
    r1 = [(p, pair.t1, j) for p, j in ex1.reads] + [(ex1.marker, pair.t1, ctx.marker_index)]
    is_lsep = isinstance(arm, cells.AdapterRouteArm)
    if is_lsep:
        ad1 = arm.arms[pair.t1].adapter
        g1 = plain_greedy(list(ex1.prompt_ids), {}, ad1, max_new, None)
    else:
        rows1, ad1 = add_of(arm, r1, len(ex1.prompt_ids))
        g1 = plain_greedy(list(ex1.prompt_ids), rows1, ad1, max_new, arm.layer)
    a1, hit = answer(g1)
    off = len(ex1.prompt_ids) + len(a1) + len(nl)
    full = list(ex1.prompt_ids) + a1 + nl + list(ex2.prompt_ids)[bos(ex2):]
    r2 = [(p - bos(ex2) + off, pair.t2, j) for p, j in ex2.reads] + [(ex2.marker - bos(ex2) + off, pair.t2, ctx.marker_index)]
    if is_lsep:
        b = len(ex1.prompt_ids) + len(a1)
        pa = PositionAdapter({pair.t1: arm.arms[pair.t1].adapter, pair.t2: arm.arms[pair.t2].adapter}, lambda i: pair.t1 if i < b else pair.t2)
        g2 = plain_greedy(full, {}, pa, max_new, None)
    else:
        rows2, ad2 = add_of(arm, r1 + r2, len(full))
        g2 = plain_greedy(full, rows2, ad2, max_new, arm.layer)
    return g1, g2, hit, r2, off


def my_c2(arm, i, max_new):
    exa, exb = cs.sentences[i].ex["A"], cs.sentences[i].ex["B"]
    nl = list(ctx.newline_ids)
    mb = list(exb.segments[-1].ids)
    ma_len = len(exa.segments[-1].ids)
    words = [(p, "A", j) for p, j in exa.reads] + [(p, "B", j) for p, j in exa.reads]
    r1 = words + [(exa.marker, "A", ctx.marker_index)]
    if isinstance(arm, cells.AdapterRouteArm):
        g1 = plain_greedy(list(exa.prompt_ids), {}, arm.arms["A"].adapter, max_new, None)
        a1, hit = answer(g1)
        full = list(exa.prompt_ids) + a1 + nl + mb
        lo, hi = len(exa.prompt_ids) - ma_len, len(exa.prompt_ids) + len(a1)
        pa = PositionAdapter({"A": arm.arms["A"].adapter, "B": arm.arms["B"].adapter}, lambda k: "A" if lo <= k < hi else "B")
        return g1, plain_greedy(full, {}, pa, max_new, None), hit
    rows1, ad1 = add_of(arm, r1, len(exa.prompt_ids))
    g1 = plain_greedy(list(exa.prompt_ids), rows1, ad1, max_new, arm.layer)
    a1, hit = answer(g1)
    full = list(exa.prompt_ids) + a1 + nl + mb
    r2 = [(len(full) - 1, "B", ctx.marker_index)]
    rows2, ad2 = add_of(arm, r1 + r2, len(full))
    return g1, plain_greedy(full, rows2, ad2, max_new, arm.layer), hit


print("stand-in world: |E_C| =", len(cs.sentences), "frozen max_new =", ctx.max_new, "BOS segment:", bos(cs.sentences[0].ex["A"]))
print("marker is the last prompt token in every E_C prompt:", all(s.ex[c].marker == len(s.ex[c].prompt_ids) - 1 for s in cs.sentences for c in core.TASKS))
frozen = ctx.max_new
tally = Counter()
for limit in (frozen, 1, 2, 3):
    ctx.max_new = limit
    for name, arm in ARMS.items():
        bad = []
        hits = 0
        for p in cs.pairs:
            o = combined.run_c1(ctx, arm, cs, p)
            of = combined.run_c1(ctx, arm, cs, p, full=True)
            g1, g2, hit, _r2, _off = my_c1(arm, p, limit)
            hits += hit
            if (o.g1, o.g2) != (g1, g2) or (of.g1, of.g2) != (g1, g2):
                bad.append(f"C1 j={p.j}")
        for i in range(len(cs.sentences)):
            o = combined.run_c2(ctx, arm, cs, i)
            of = combined.run_c2(ctx, arm, cs, i, full=True)
            g1, g2, hit = my_c2(arm, i, limit)
            hits += hit
            if (o.g1, o.g2) != (g1, g2) or (of.g1, of.g2) != (g1, g2):
                bad.append(f"C2 i={i}")
        tally[(limit, name)] = len(bad)
        print(f"limit {limit:>2} | {name:<40} | first answers at the limit: {hits:>3} | differences (impl cache, impl full, mine): {len(bad)} {bad[:4]}")
ctx.max_new = frozen

# the read positions of step 2 against the addendum formula, and that a1 and the NL after it are never read
pos_bad = 0
arm = ARMS["M-append-frozen / M-ii (2-stage store)"]
for p in cs.pairs:
    for hit in (False, True):
        a1 = [5, 6, 7]
        ids1, reads1, sfx = combined.c1_layout(ctx, cs, p)
        suffix, reads2 = sfx(a1, hit)
        cached = len(ids1) + len(a1) - (1 if hit else 0)
        absolute = sorted((cached + q, t, j) for q, t, j in reads2)
        ex2 = cs.sentences[p.i2].ex[p.t2]
        off = len(ids1) + len(a1) + len(ctx.newline_ids)
        want = sorted([(q - bos(ex2) + off, p.t2, j) for q, j in ex2.reads] + [(ex2.marker - bos(ex2) + off, p.t2, ctx.marker_index)])
        never = set(range(len(ids1), off))
        if absolute != want or any(x[0] in never for x in absolute) or any(x[0] >= len(ids1) for x in reads1):
            pos_bad += 1
print("C1 read positions against the formula (both hit cases, every item): mismatches", pos_bad)

# C1 first answers = single-task answers; C2 first answers of adapter arms = their single-task German answers (by construction)
for name, arm in ARMS.items():
    rec_ = combined.score_combined_cell(ctx, arm, cs)
    same_c1 = all(it["ids"][0] == evaluate.generate(ctx, arm, cs.sentences[it["i"][0]].ex[it["langs"][0]], [it["langs"][0]]) for it in rec_["C1"]["items"])
    same_c2 = sum(it["ids"][0] == rec_["single"]["sequences"]["A"][it["i"][0]] for it in rec_["C2"]["items"])
    # my recomputation of the summary fields from the items
    ok_fields = True
    for kind in ("C1", "C2"):
        for a in core.TASKS:
            if kind == "C1":
                sel = [it for it in rec_["C1"]["items"] if it["langs"][1] == a]
                sK = sum(it["scores"][1] for it in sel) / len(sel)
                sents = [it["i"][1] for it in sel]
            else:
                k = 0 if a == "A" else 1
                sK = sum(it["scores"][k] for it in rec_["C2"]["items"]) / len(rec_["C2"]["items"])
                sents = list(range(len(cs.sentences)))
            sS = sum(rec_["single"]["scores"][a][i] for i in sents) / len(sents)
            ok_fields &= abs(combined.tested_mean(rec_, kind, a) - sK) < 1e-12 and abs(combined.single_mean_on(rec_, kind, a) - sS) < 1e-12
    print(f"{name:<40} | C1 first answers == single-task: {same_c1} | C2 German answers identical to single-task German: {same_c2}/{len(cs.sentences)} | summary fields == my recomputation: {ok_fields} | separate single answers {rec_['single']['separate_answers']}")

# the adapters and stores used above do change the answers (otherwise "identical" would be trivial)
for name, arm in ARMS.items():
    diff = sum(evaluate.generate(ctx, arm, s.ex[c], [c]) != evaluate.generate(ctx, memory.NullArm(), s.ex[c], [c]) for s in cs.sentences for c in core.TASKS)
    print(f"{name:<40} | single-task answers differing from Stage 0: {diff}/{2 * len(cs.sentences)}")
