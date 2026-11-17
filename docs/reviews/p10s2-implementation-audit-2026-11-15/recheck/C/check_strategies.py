"""Re-check auditor C: strategies under the strengthened COMPOSES rule, on a toy word-for-word translation world (the
stand-in lexicon of studies/p10s2/synthetic, 60 words; German and French words share their trailing index digits, so
copying one language into the other scores above zero -- a deliberate stress test). Texts are scored with my chrF
(the predecessor's auditor implementation spec_rules.chrf_def); records are built by me (check_composition.build_record);
both my rule (rules_v2) and studies/p10s2/analysis.composition decide. Seeds 229601.. (test range).
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval. Usage: <python> check_strategies.py <pin>"""

import random
import sys
from pathlib import Path

PIN = sys.argv[1]
sys.path.insert(0, PIN)
sys.path.insert(0, PIN + "/src")
sys.path.insert(0, str(Path(__file__).parent))

from studies.p10s2 import analysis  # noqa: E402
from studies.p10s2.synthetic import lexicon  # noqa: E402

import check_composition as K  # noqa: E402
import rules_v2 as S  # noqa: E402
from spec_rules import chrf_def  # noqa: E402

rng = random.Random(229601)
EN, DE, FR = lexicon(60)
N = 200
sents = [[rng.choice(EN) for _ in range(rng.randint(3, 10))] for _ in range(N)]
REF = {"A": [" ".join(DE[w] for w in s) for s in sents], "B": [" ".join(FR[w] for w in s) for s in sents]}
SRC = [" ".join(s) for s in sents]
sigma = list(range(N))
rng.shuffle(sigma)
PAIRS = S.c1_pairs(sigma)


def sc(text, a, i):
    return chrf_def(text, REF[a][i])


def noisy(a, i, p_word):
    """A translation that gets each word right with probability p_word (else the English word)."""
    s = sents[i]
    m = DE if a == "A" else FR
    return " ".join(m[w] if rng.random() < p_word else w for w in s)


def record(single_text, c1_second_text, c2_first_text, c2_second_text):
    single = {a: [sc(single_text(a, i), a, i) for i in range(N)] for a in S.TASKS}
    c1 = [sc(c1_second_text(j, i1, i2, t1, t2), t2, i2) for j, i1, i2, t1, t2 in PAIRS]
    c2a = [sc(c2_first_text(i), "A", i) for i in range(N)]
    c2b = [sc(c2_second_text(i), "B", i) for i in range(N)]
    return K.build_record(N, sigma, single, c1, c2a, c2b)


stage0 = record(lambda a, i: SRC[i], lambda j, i1, i2, t1, t2: SRC[i2], lambda i: SRC[i], lambda i: SRC[i])  # the untrained student echoes the source
ens = record(lambda a, i: REF[a][i], lambda j, i1, i2, t1, t2: REF[t2][i2], lambda i: REF["A"][i], lambda i: REF["B"][i])
good = {(a, i): noisy(a, i, 0.85) for a in S.TASKS for i in range(N)}  # a capable arm's single-task answers


def judge(name, rec):
    cells = {"-": [rec] * 3}
    mine = {k: S.comp_class({"-": [K.mine_inputs(rec, stage0, ens, k, N, sigma)] * 3}) for k in ("C1", "C2")}
    st = analysis.Study(K.study_of(3, {("M-joint", r, "-"): rec for r in range(3)}, stage0, ens, {}))
    out = analysis.composition(st)
    impl = {k: out["arms"][k]["M-joint"]["composition"] for k in ("C1", "C2")}
    h = {k: out["arms"][k]["M-joint"]["orders"]["-"][0]["H"] for k in ("C1", "C2")}
    g = {k: out["arms"][k]["M-joint"]["orders"]["-"][0]["single_task_G"] for k in ("C1", "C2")}
    fmt = lambda d: {a: (None if v is None else round(v, 3)) for a, v in d.items()}  # noqa: E731
    print(f"{name:<62} mine {mine} | impl {impl} | H C1 {fmt(h['C1'])} C2 {fmt(h['C2'])} | single-task G C1 {fmt(g['C1'])}")
    assert mine == impl, (mine, impl)
    return impl
    del cells


print("toy world: |E_C| =", N, "| Stage 0 echoes the English source; the teachers give the reference")
judge("do-nothing (the Stage 0 student itself)", stage0)
judge("first-answer-only (empty second answers; C2 German good)", record(lambda a, i: good[(a, i)], lambda *x: "", lambda i: good[("A", i)], lambda i: ""))
judge("copy-the-first-answer (C1: s1 in T1; C2: the German answer)", record(lambda a, i: good[(a, i)], lambda j, i1, i2, t1, t2: good[(t1, i1)], lambda i: good[("A", i)], lambda i: good[("A", i)]))
judge("right language, wrong sentence (C1: s1 in T2)", record(lambda a, i: good[(a, i)], lambda j, i1, i2, t1, t2: good[(t2, i1)], lambda i: good[("A", i)], lambda i: good[("B", i)]))
judge("wrong language, right sentence (C1: s2 in T1)", record(lambda a, i: good[(a, i)], lambda j, i1, i2, t1, t2: good[(t1, i2)], lambda i: good[("A", i)], lambda i: good[("A", i)]))
judge("echo the source in the second answer", record(lambda a, i: good[(a, i)], lambda j, i1, i2, t1, t2: SRC[i2], lambda i: good[("A", i)], lambda i: SRC[i]))
judge("both answers concatenated in the second slot (C2)", record(lambda a, i: good[(a, i)], lambda j, i1, i2, t1, t2: good[(t2, i2)], lambda i: good[("A", i)], lambda i: good[("A", i)] + " " + good[("B", i)]))
judge("contaminated second answer: first answer then the right one (C1 and C2)", record(lambda a, i: good[(a, i)], lambda j, i1, i2, t1, t2: good[(t1, i1)] + " " + good[(t2, i2)], lambda i: good[("A", i)], lambda i: good[("A", i)] + " " + good[("B", i)]))
judge("contaminated: the right answer twice plus the English source", record(lambda a, i: good[(a, i)], lambda j, i1, i2, t1, t2: good[(t2, i2)] + " " + good[(t2, i2)] + " " + SRC[i2], lambda i: good[("A", i)], lambda i: good[("B", i)] + " " + good[("B", i)] + " " + SRC[i]))
judge("context-blind capable arm (second answer = its single answer)", record(lambda a, i: good[(a, i)], lambda j, i1, i2, t1, t2: good[(t2, i2)], lambda i: good[("A", i)], lambda i: good[("B", i)]))
judge("weak single-task arm (G ~ 0.3), context-blind", record(lambda a, i: noisy(a, i, 0.35), lambda j, i1, i2, t1, t2: noisy(t2, i2, 0.35), lambda i: noisy("A", i, 0.35), lambda i: noisy("B", i, 0.35)))
judge("the ensemble record itself (BY CONSTRUCTION; not a scored arm)", ens)

# random search: each second answer is, independently, the arm's own single answer with probability p, otherwise one of the
# cheap behaviours above (chosen at random per item); the single-task answers are those of the capable arm.
cheap = [lambda a, i, i1, t1: "", lambda a, i, i1, t1: SRC[i], lambda a, i, i1, t1: good[(t1, i1)], lambda a, i, i1, t1: good[(a, i1)],
         lambda a, i, i1, t1: good[(t1, i)], lambda a, i, i1, t1: good[(t1, i1)] + " " + good[(a, i)][: len(good[(a, i)]) // 2]]
print("random search over mixtures (500 strategies): smallest share p of genuine second answers among strategies that print COMPOSES")
best = {"C1": None, "C2": None}
for t in range(500):
    p = rng.random()
    choice = {}

    def second(a, i, i1, t1):
        if rng.random() < p:
            return good[(a, i)]
        return rng.choice(cheap)(a, i, i1, t1)

    rec = record(lambda a, i: good[(a, i)], lambda j, i1, i2, t1, t2: second(t2, i2, i1, t1), lambda i: good[("A", i)], lambda i: second("B", i, i, "A"))
    mine = {k: S.comp_class({"-": [K.mine_inputs(rec, stage0, ens, k, N, sigma)] * 3}) for k in ("C1", "C2")}
    for k in ("C1", "C2"):
        if mine[k] == "COMPOSES" and (best[k] is None or p < best[k]):
            best[k] = p
print("   smallest p with COMPOSES:", {k: (None if v is None else round(v, 3)) for k, v in best.items()})
