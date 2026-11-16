"""evaluate.read_swap against the auditor's expectation on a hand-built model whose memory read at an answer site IS the fact's answer (one-hot),
so accuracy, a_use and the tie rule are known in closed form. Test seeds p10s0-test-7 (920701+) only. Claude (Opus 5.5) review; Astra: NOT_PERFORMED."""
import json, torch
from studies.p9 import core as p9core
from studies.p9.data import DataSizes, build_study_data
from studies.p9i.evaluate import stream_for
from studies.p9ii.model import SITES
from studies.p10s0 import core, evaluate

SPEC = core.test_set(7)
g = torch.Generator().manual_seed(12)
corpus = bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())
FACTS = 128
data = build_study_data(SPEC.seeds(2048), corpus, sizes=DataSizes(main_trained=FACTS, unseen=64, lane_d_per_set=128))
ALPH = torch.tensor(p9core.ALPHABET)
answers = evaluate.fact_answers(data, FACTS)
# fact identity of a site from the context tokens (a lookup the fake model owns; evaluation-side test double only)
lut = {}
for panel in ("A", "B"):
    st = stream_for(data, FACTS, core.PANEL_STREAM[panel])
    keep = (st.fact_ids < FACTS).all(dim=1)
    for c, (tok, ids) in enumerate(zip(st.tokens[keep][:, : core.INPUT_LENGTH], st.fact_ids[keep])):
        for r in range(8):
            lut[tuple(tok[: SITES[r] + 1].tolist())] = int(ids[r])
TIE_OWN = set(range(0, 10))      # own read gives a tie between the answer and another symbol -> not correct
TIE_SWAP = set(range(10, 20))    # a read that, used for another fact, also scores that fact's answer equally -> swapped still counts as answer
class Fake:
    training = False
    def eval(self): pass
    def train(self, mode=True): pass
    def embed_block0(self, tok):
        self._tok = tok
        return torch.zeros(tok.shape[0], tok.shape[1], 32)
    def select(self, h, tok):
        return tok
    def memory_delta(self, h, sel):
        d = torch.zeros(h.shape[0], h.shape[1], 32)
        for b in range(sel.shape[0]):
            for r in range(8):
                f = lut[tuple(sel[b, : SITES[r] + 1].tolist())]
                d[b, SITES[r], answers[f]] = 2.0
                if f in TIE_OWN:
                    d[b, SITES[r], (answers[f] + 1) % 32] = 2.0
                if f in TIE_SWAP:
                    d[b, SITES[r], :] = 2.0  # every symbol equal: never correct on its own, and as a swapped read ties with any answer
        return d
    def finish(self, h, delta):
        out = torch.zeros(delta.shape[0], delta.shape[1], 256)
        out[:, :, ALPH] = delta
        return out
perm = evaluate.swap_permutation(data, FACTS, SPEC.swap_seed(2048))
res = {}
for panel in ("A", "B"):
    r = evaluate.read_swap(Fake(), data, FACTS, panel, perm)
    # auditor's closed form: correct iff f not in TIE_OWN and not in TIE_SWAP; swapped prediction for f uses pi(f)'s read:
    # still the answer iff pi(f) in TIE_SWAP (all equal) or (pi(f) in TIE_OWN and answer(f) == answer(pi(f)) + 1 mod 32)
    correct = [f for f in range(FACTS) if f not in TIE_OWN and f not in TIE_SWAP]
    def still(f):
        p = int(perm[f])
        return p in TIE_SWAP or (p in TIE_OWN and int(answers[f]) == (int(answers[p]) + 1) % 32)
    used = [f for f in correct if not still(f)]
    res[panel] = {"impl": {k: r[k] for k in ("facts", "correct", "a_use_count", "a_use", "accuracy", "information_bits")},
                  "auditor": {"facts": FACTS, "correct": len(correct), "a_use_count": len(used)}}
print(json.dumps(res, indent=1))
