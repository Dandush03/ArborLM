"""Re-check auditor C: GEN measured twice (ADR-0022 ruling on C-M6).
 (1) the marker-string rule and the decision positions: windows.cut_windows against my own implementation of ADR s6.4's
     text on random texts with a GPT-2-style pre-splitting tokenizer (window 16, decision token 8, to hit the boundaries);
 (2) general_quality's two decisions: which hidden-state positions it reads (instrumented), on the stand-in world;
 (3) the predecessor's position-only router (C-M6), trained with the registered recipe, scored at BOTH decision points
     through evaluate.general_quality itself (hidden_at_ends replaced by a position-only feature map; a store arm whose
     read raises the loss), with marker_end positions of real marker windows drawn uniformly over tokens 1-64;
 (4) a "colon-cue" router: fires only when the token at the decision position is ':' -- the cue of a task prompt's last
     token -- never probed by either decision except by chance at token 64.
Seeds 229401.. (test range). Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
Usage: <python> check_gen.py <pin>"""

import math
import random
import re
import sys

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")

import torch  # noqa: E402

from studies.p10s2 import core, evaluate, memory, standins, windows  # noqa: E402
from studies.p10s2.evaluate import GeneralWindow  # noqa: E402
from studies.p10s2.routing import RouterSpec, train_router  # noqa: E402

torch.set_num_threads(2)
STRINGS = ["German", "French", "English", "translation", ":\n"]


class PreSplit:
    bos_id = None

    def encode_offsets(self, text):
        o = [(m.start(), m.end()) for m in re.finditer(r" ?[A-Za-z]+| ?[^\sA-Za-z]+|\s", text)]
        return list(range(len(o))), o


def mine(text, window, decision):
    _ids, offs = PreSplit().encode_offsets(text)
    out = []
    for w0 in range(0, len(offs) - window + 1, window):
        head = "".join(text[s:e] for s, e in offs[w0:w0 + decision])
        whole = "".join(text[s:e] for s, e in offs[w0:w0 + window])
        hits = [(head.find(s), s) for s in STRINGS if head.find(s) >= 0]
        if hits:
            k, s = min(hits)
            end_char = offs[w0][0] + k + len(s) - 1  # the last character of the first marker-like string
            tok = next(i for i in range(w0, w0 + decision) if offs[i][0] <= end_char < offs[i][1])
            out.append((w0, "marker", tok - w0))
        elif not any(s in whole for s in STRINGS):
            out.append((w0, "ordinary", -1))
    return out


rng = random.Random(229401)
VOC = ["the", "cat", "Germany", "German", "german", "French", "french", "English", "Englishman", "translation", "translations", "word", "line", "end", "a", "b"]
PUN = [":", ":\n", "\n", ",", ".", " :", ": \n"]
mismatch = 0
counts = {"marker": 0, "ordinary": 0}
for t in range(3000):
    parts = []
    for _ in range(rng.randint(20, 80)):
        parts.append(" " + rng.choice(VOC) if rng.random() < 0.8 else rng.choice(PUN))
    text = "".join(parts)
    impl = [(i * 0, w.stratum, w.marker_end) for i, w in enumerate(windows.cut_windows(PreSplit(), text, {}, 16, 8))]
    me = mine(text, 16, 8)
    if [(s, m) for _, s, m in impl] != [(s, m) for _, s, m in me]:
        mismatch += 1
        if mismatch < 4:
            print("MISMATCH", repr(text[:200]), impl, me)
    for _, s, _m in me:
        counts[s] += 1
print("(1) cut_windows vs my reading of s6.4 on 3,000 random texts (window 16, decision 8): mismatching texts", mismatch, "; windows by stratum", counts)

# (2) and (3): general_quality on the stand-in world
world, _rec = standins.build_synthetic_world(replicates=1)
ctx = world.ctx
st = ctx.student
W = world.cfg.width
vocab = max(max(w.ids) for w in ctx.windows) + 1
g = torch.Generator().manual_seed(229402)
mpos = torch.randint(0, 64, (100,), generator=g).tolist()
wins = []
for k in range(200):
    ids = tuple(torch.randint(0, vocab, (256,), generator=g).tolist())
    reads = tuple((p, int(torch.randint(0, 20, (1,), generator=g))) for p in range(0, 256, 3))
    wins.append(GeneralWindow(ids, reads, "marker", mpos[k]) if k < 100 else GeneralWindow(ids, reads, "ordinary"))
ctx.windows = wins
ctx.decision_index, ctx.first_nll_index = 63, 64

positions_seen = []
orig_hidden = evaluate.hidden_at_ends


def pos_features(student, layer, sequences, positions=None, batch=64):
    pos = torch.tensor([float(positions[i] if positions is not None else len(s) - 1) for i, s in enumerate(sequences)])
    positions_seen.append(list(positions) if positions is not None else None)
    freqs = torch.exp(-torch.arange(W // 2, dtype=torch.float32) * math.log(1000.0) / (W // 2))
    f = pos[:, None] * freqs[None, :]
    return torch.cat([torch.sin(f), torch.cos(f)], dim=-1)


class PosStudent:
    class cfg:  # noqa: N801
        width = W

    def block_output(self, ids, layer):
        b, t = ids.shape
        pos = torch.arange(t, dtype=torch.float32)
        freqs = torch.exp(-torch.arange(W // 2, dtype=torch.float32) * math.log(1000.0) / (W // 2))
        f = pos[:, None] * freqs[None, :]
        return torch.cat([torch.sin(f), torch.cos(f)], dim=-1)[None].expand(b, t, W).clone()


class Ex:
    def __init__(self, n):
        self.prompt_ids = tuple([1] * n)


gl = torch.Generator().manual_seed(229403)
lengths = torch.randint(9, 26, (4000,), generator=gl).tolist()
prompts = {"A": [Ex(n) for n in lengths[:2000]], "B": [Ex(n) for n in lengths[2000:]]}
router, rec = train_router(PosStudent(), world.layer, ("A", "B"), prompts, [2] * (8300 * 64), core.SeedPlan("test", 0), RouterSpec.registered())
positions_seen.clear()
store = memory.SparseStore.new(W, 32, torch.Generator().manual_seed(229404))
with torch.no_grad():
    v = dict(st.named_parameters())["embed"][0].detach()
    store.values[0].copy_(50.0 * v[None, :].expand_as(store.values[0]))  # every row the same large vector (token 0's embedding): a read that pushes the next-token distribution towards one token
    store.gates[0].fill_(1.0)
arm = memory.MemoryArm(store, world.layer, world.codes(0))
evaluate.hidden_at_ends = pos_features
try:
    res = evaluate.general_quality(ctx, arm, router)
finally:
    evaluate.hidden_at_ends = orig_hidden
print("    raw:", {k: res[k] for k in ("nll_base", "nll_router", "nll_router_first_marker", "loss_increase", "loss_increase_first_marker")})
print("(2) decision positions read by general_quality: call 1 all index 63:", positions_seen[0] == [63] * 200,
      "| call 2 = marker_end for the 100 marker windows and 63 for the ordinary ones:", positions_seen[1] == mpos + [63] * 100)
in_task = sum(9 - 1 <= p <= 25 - 1 for p in mpos)
print("(3) position-only router (registered recipe, 500 updates):",
      "triggers token-64 decision", res["false_trigger_count"], "| first-marker decision", res["false_trigger_count_first_marker"],
      f"| marker windows whose marker_end lies at task-prompt last-token indices 8-24: {in_task}/100")
print("    loss increase token-64 %.4f, first-marker %.4f, passes_registered %s, passes_first_marker %s, passes (both) %s" % (
    res["loss_increase"], res["loss_increase_first_marker"], res["passes_registered_decision"], res["passes_first_marker_decision"], res["passes"]))


# (4) a router keyed on the decision token being a bare ':' that follows a language word (the shape of a task prompt's last two tokens)
rng = random.Random(229406)
lang_colon_windows = probed_first = probed_64 = 0
for t in range(3000):
    parts = [" " + rng.choice(VOC) if rng.random() < 0.8 else rng.choice(PUN) for _ in range(rng.randint(20, 80))]
    text = "".join(parts)
    _ids, offs = PreSplit().encode_offsets(text)
    toks = [text[a:b] for a, b in offs]
    for w in windows.cut_windows(PreSplit(), text, {}, 16, 8):
        if w.stratum != "marker":
            continue
        w0 = next(k for k in range(0, len(offs) - 15, 16) if tuple(range(k, k + 16)) == tuple(range(k, k + 16)) and w.ids == tuple(range(k, k + 16)))
        cues = [k for k in range(1, 8) if toks[w0 + k].strip() == ":" and toks[w0 + k - 1].strip() in ("German", "French")]
        if cues:
            lang_colon_windows += 1
            probed_first += w.marker_end in cues
            probed_64 += 7 in cues
print("(4) marker windows with '<German|French>:' (a bare ':' token right after the language word) inside the decision span:", lang_colon_windows,
      "| of these, first-marker decision ON that ':' token:", probed_first, "| registered decision (last token of the span) on it:", probed_64)
print("    The first-marker decision is the token holding the last character of 'German'/'French'/..., or the newline of ':\\n'; it is never the ':' after a language word."
      " A router keyed on that ':' (the task prompt's own last-token cue) is probed by GEN only when token 64 happens to be such a ':'.")
