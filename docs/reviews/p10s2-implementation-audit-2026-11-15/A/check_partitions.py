"""Audit A, check 2: an independent implementation of ADR-0022 section 5.2 (identity groups, assignment, panels, pools) and section 5.2/9
(replicate training draws) on a synthetic Tatoeba-like corpus, compared with studies/p10s2/data.py, plus property checks
(disjointness, contraction handling, Q_fit/Q_check, no-gold rule, draw invariants, sufficiency arithmetic).
Written by the auditor (Claude Opus 5.5). Synthetic text only. Run from the pinned tree:  <python> <this file>
"""

import math
import random
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import torch

PIN = Path.cwd()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
from studies.p10s2 import core, data  # noqa: E402
from studies.p10s2.text import CONTRACTIONS  # noqa: E402  (the ADR says the fixed list is in the code)

out: list[str] = []


def say(s: str) -> None:
    out.append(s)
    print(s)


# ---------------------------------------------------------------- my own text functions (from the ADR's words) ----------------------------
def my_norm(t: str) -> str:
    t = unicodedata.normalize("NFC", t).lower()
    t = "".join(ch for ch in t if not unicodedata.category(ch).startswith("P"))
    return " ".join(t.split())


def my_expand_as_implemented(t: str) -> str:
    """The implementation's reading (whitespace tokens looked up verbatim), re-written by me to compare groups exactly."""
    t = unicodedata.normalize("NFC", t).lower().replace("’", "'")
    return my_norm(" ".join(CONTRACTIONS.get(w, w) for w in t.split()))


def my_expand_corrected(t: str) -> str:
    """What the ADR intends: a contraction is expanded also when punctuation is attached to it ("don't.", "can't,", "(it's")."""
    t = unicodedata.normalize("NFC", t).lower().replace("’", "'")
    words = []
    for w in t.split():
        core_ = w.strip("".join(ch for ch in set(w) if unicodedata.category(ch).startswith("P") and ch != "'"))
        words.append(w.replace(core_, CONTRACTIONS[core_]) if core_ in CONTRACTIONS else w)
    return my_norm(" ".join(words))


# ---------------------------------------------------------------- synthetic corpus -------------------------------------------------------------
@dataclass
class Corpus:
    eng: dict
    deu: dict
    fra: dict
    links_de: list
    links_fr: list


rng = random.Random(4242)  # the auditor's own stand-in generator (not a study seed)
SUBJ = ["Tom", "Mary", "We", "They", "You", "The boy", "The girl", "My father"]
VERB = ["likes", "sees", "wants", "needs", "has", "reads", "eats", "buys"]
OBJ = ["apples", "a book", "the dog", "the cat", "water", "bread", "music", "a car", "the house", "milk"]
ADV = ["", "today", "now", "again", "too", "every day"]
DE = {w: w[::-1] + "e" for w in "tom mary we they you the boy girl my father likes sees wants needs has reads eats buys apples a book dog cat water bread music car house milk today now again too every day i do not don't know no can't cannot swim sorry it is it's ja".split()}
FR = {w: w[::-1] + "u" for w in DE}


def tr(s: str, table: dict, salt: str = "") -> str:
    return " ".join(table.get(w, w) for w in my_norm(s).split()) + salt + "."


eng, deu, fra, lde, lfr = {}, {}, {}, [], []
nid = [1]


def add(d: dict, text: str) -> int:
    i = nid[0]
    nid[0] += 1
    d[i] = text
    return i


plain = set()
while len(plain) < 1400:
    s = f"{rng.choice(SUBJ)} {rng.choice(VERB)} {rng.choice(OBJ)} {rng.choice(ADV)}".strip() + "."
    plain.add(s)
for s in sorted(plain):
    e = add(eng, s)
    r = rng.random()
    if r < 0.45:
        lde.append((e, add(deu, tr(s, DE))))
        lfr.append((e, add(fra, tr(s, FR))))
    elif r < 0.60:
        lde.append((e, add(deu, tr(s, DE))))
    elif r < 0.75:
        lfr.append((e, add(fra, tr(s, FR))))
# contraction pairs inside the sentence (the implementation groups these through the expanded string)
for k, o in enumerate(OBJ):
    for v in ("like", "want"):
        a = add(eng, f"I don't {v} {o} now.")
        b = add(eng, f"I do not {v} {o} now.")
        for e, salt in ((a, " x"), (b, " y")):
            lde.append((e, add(deu, tr(eng[e], DE, salt))))
            lfr.append((e, add(fra, tr(eng[e], FR, salt))))
# contraction pairs with punctuation attached to the contraction (sentence-final, before a comma): ADR wants them in one group
final_pairs = []
for k, o in enumerate(OBJ + ["bread too", "milk again", "music today"]):
    a = add(eng, f"No, {o.split()[0]} says I can't.")
    b = add(eng, f"No, {o.split()[0]} says I cannot.")
    c = add(eng, f"Sorry, I can't, {o} today.")
    d = add(eng, f"Sorry, I cannot, {o} today.")
    for e, salt in ((a, " p"), (b, " q"), (c, " r"), (d, " s")):
        lde.append((e, add(deu, tr(eng[e], DE, salt))))
        lfr.append((e, add(fra, tr(eng[e], FR, salt))))
    final_pairs += [(a, b), (c, d)]
# a large identity group (> 50 pairs) through one shared reference
for k in range(60):
    e = add(eng, f"Yes {SUBJ[k % 8]} {VERB[k % 8]} it {'again' if k % 2 else 'too'} {k}.")
    lde.append((e, add(deu, "Ja.")))
# out-of-vocabulary evaluation-side material (rare words) for E_open, and no-gold sources
for k in range(200):
    s = f"{rng.choice(SUBJ)} {rng.choice(VERB)} the zebra{k} {rng.choice(ADV)}".strip() + "."
    e = add(eng, s)
    lde.append((e, add(deu, tr(s, DE))))
    lfr.append((e, add(fra, tr(s, FR))))
corpus = Corpus(eng, deu, fra, lde, lfr)
say(f"synthetic corpus: {len(eng)} English, {len(deu)} German, {len(fra)} French, {len(lde)} + {len(lfr)} links")

sizes = data.Sizes(vocabulary=60, min_words=3, max_words=10, large_group_pairs=50, evaluation_fraction=0.20, panel_eval=40, panel_eval_min=20, panel_combined=20, panel_combined_min=10, panel_open=10, panel_q_fit=40, panel_q_check=40, panel_d_cal=20, panel_d_con=15, accepted_per_replicate=60, gold_per_replicate=60, sufficiency_factor=1.25, generation_sources_max=400, check_min_accepted=6)
core.reset_seed_record()
P = data.build_partition(corpus, "test", sizes)

# ---------------------------------------------------------------- my implementation ----------------------------------------------------------
TASKS = ("A", "B")
tgt = {"A": deu, "B": fra}
links = {"A": lde, "B": lfr}
pairs = sorted((c, e, t) for c in TASKS for e, t in links[c] if e in eng and t in tgt[c])


def groups_with(expand) -> list[list[int]]:
    adj = defaultdict(set)
    for i, (c, e, t) in enumerate(pairs):
        for key in (("e", my_norm(eng[e])), ("x", expand(eng[e])), ("r", my_norm(tgt[c][t]))):
            adj[key].add(i)
    # BFS over the bipartite graph pair <-> key
    seen, comps = set(), []
    keys_of = defaultdict(list)
    for k, members in adj.items():
        for i in members:
            keys_of[i].append(k)
    for i in range(len(pairs)):
        if i in seen:
            continue
        comp, stack = [], [i]
        seen.add(i)
        while stack:
            j = stack.pop()
            comp.append(j)
            for k in keys_of[j]:
                for m in adj[k]:
                    if m not in seen:
                        seen.add(m)
                        stack.append(m)
        comps.append(sorted(comp))
    return sorted(comps, key=lambda c: c[0])


mine = groups_with(my_expand_as_implemented)
theirs_members = defaultdict(list)
# recover the implementation's pair -> group map through group_of_key (keys) and sizes
same_sizes = sorted(len(c) for c in mine) == sorted(P.group_sizes.values())
say(f"[groups] my components (implementation's expansion rule): {len(mine)}; implementation: {len(P.group_sizes)}; size multisets equal: {same_sizes}")
my_gid = {i: g for g, comp in enumerate(mine) for i in comp}
my_key_group = {}
for i, (c, e, t) in enumerate(pairs):
    my_key_group[my_norm(eng[e])] = my_gid[i]
same_keymap = all(P.group_of_key[k] == g for k, g in my_key_group.items()) and set(P.group_of_key) == set(my_key_group)
say(f"[groups] key -> group map identical to the implementation's (group ids = order of first pair): {same_keymap}")

corr = groups_with(my_expand_corrected)
corr_gid = {i: g for g, comp in enumerate(corr) for i in comp}
say(f"[groups] components with the corrected contraction rule: {len(corr)} (implementation's rule: {len(mine)})")
split_pairs = [(a, b) for a, b in final_pairs if P.group_of_key[my_norm(eng[a])] != P.group_of_key[my_norm(eng[b])]]
straddle = [(a, b) for a, b in split_pairs if P.group_side[P.group_of_key[my_norm(eng[a])]] != P.group_side[P.group_of_key[my_norm(eng[b])]]]
say(f"[contractions] sentence pairs differing only by a contraction with punctuation attached ('can't.' / 'can't,'): {len(final_pairs)}; put in different identity groups by the implementation: {len(split_pairs)}; of these on opposite sides (one evaluation, one training): {len(straddle)}")
if straddle:
    a, b = straddle[0]
    say(f"   example: {eng[a]!r} ({P.group_side[P.group_of_key[my_norm(eng[a])]]}) vs {eng[b]!r} ({P.group_side[P.group_of_key[my_norm(eng[b])]]})")
inside_ok = all(P.group_of_key[my_norm(eng[k])] == P.group_of_key[my_norm(eng[k + 1])] for k in eng if eng[k].startswith("I don't "))
say(f"[contractions] mid-sentence contraction pairs ('I don't like ... now.' / 'I do not like ...') share a group: {inside_ok}")

# my assignment, panel draws and pools, replaying the ADR's draw order with my own generator objects on the same (test-mode) seeds
gs = {g: len(c) for g, c in enumerate(mine)}
large = [g for g, s in gs.items() if s > sizes.large_group_pairs]
small = [g for g in gs if g not in large]
remaining = sum(gs[g] for g in small)
gen = torch.Generator().manual_seed(core.partition_seeds("test")["partition"])
perm = torch.randperm(len(small), generator=gen).tolist()
side = {g: "train" for g in gs}
ev = 0
for k in perm:
    if ev >= sizes.evaluation_fraction * remaining:
        break
    side[small[k]] = "eval"
    ev += gs[small[k]]
say(f"[assignment] large groups (> 50 pairs) to training: {[gs[g] for g in large]}; evaluation pairs {ev} of remaining {remaining} = {ev / remaining:.4f} (target 0.20; the last group may overshoot)")
say(f"[assignment] identical to the implementation's: {side == P.group_side}")

nx = {e: my_expand_as_implemented(t) for e, t in eng.items()}
ne = {e: my_norm(t) for e, t in eng.items()}
eval_str = set()
for i, (c, e, t) in enumerate(pairs):
    if side[my_gid[i]] == "eval":
        eval_str |= {ne[e], nx[e]}
train_en = [e for e in sorted(eng) if ne[e] and ne[e] not in eval_str and nx[e] not in eval_str]
from collections import Counter  # noqa: E402

freq = Counter(w for e in train_en if 3 <= len(ne[e].split()) <= 10 for w in ne[e].split())
vocab = [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[: sizes.vocabulary]]
say(f"[vocabulary] identical to the implementation's: {vocab == P.vocab}")

refs = {c: defaultdict(dict) for c in TASKS}
for c, e, t in pairs:
    refs[c][ne[e]].setdefault(my_norm(tgt[c][t]), tgt[c][t])
kg = my_key_group
vs = set(vocab)
inv = lambda k: all(w in vs for w in k.split())  # noqa: E731
okl = lambda k: 3 <= len(k.split()) <= 10  # noqa: E731
train_keys = sorted({ne[e] for e in train_en})
all_keys = sorted({ne[e] for e in eng if ne[e]})
eval_keys = [k for k in all_keys if k in eval_str]
used: set = set()


def draw_plain(c, n):
    av = [k for k in c if kg.get(k, -1) not in used]
    o = torch.randperm(len(av), generator=gen).tolist() if av else []
    ch = [av[i] for i in o[:n]]
    used.update(kg[k] for k in ch)
    return ch


def draw_strat(c, n, caps):
    av = [k for k in c if kg.get(k, -1) not in used]
    s1 = [k for k in av if all(len(refs[x][k]) == 1 for x in caps)]
    s2 = [k for k in av if k not in set(s1)]
    tot = len(s1) + len(s2)
    want = min(n, tot)
    n1 = min(len(s1), round(want * len(s1) / tot)) if tot else 0
    n2 = min(len(s2), want - n1)
    n1 = min(len(s1), want - n2)
    ch = []
    for pool, m in ((s1, n1), (s2, n2)):
        o = torch.randperm(len(pool), generator=gen).tolist() if pool else []
        ch += [pool[i] for i in o[:m]]
    used.update(kg[k] for k in ch)
    return ch


both = [k for k in train_keys if k in kg and okl(k) and inv(k) and all(k in refs[c] for c in TASKS) and side[kg[k]] == "train"]
q = draw_plain(both, 80)
qg = torch.Generator().manual_seed(core.partition_seeds("test")["q_split"])
qp = torch.randperm(len(q), generator=qg).tolist()
my_panels = {"Q_fit": [q[i] for i in qp[:40]], "Q_check": [q[i] for i in qp[40:]]}
my_panels["D_cal"] = draw_plain(both, 20)
my_panels["D_con"] = draw_plain(both, 15)
evok = [k for k in eval_keys if k in kg and okl(k) and inv(k)]
my_panels["E_A"] = draw_strat([k for k in evok if k in refs["A"]], 40, ["A"])
my_panels["E_B"] = draw_strat([k for k in evok if k in refs["B"]], 40, ["B"])
my_panels["E_C"] = draw_strat([k for k in evok if all(k in refs[c] for c in TASKS)], 20, list(TASKS))
my_panels["E_open"] = draw_plain([k for k in eval_keys if k in kg and okl(k) and not inv(k) and any(k in refs[c] for c in TASKS)], 10)
for name in my_panels:
    say(f"[panels] {name}: mine {len(my_panels[name])}, implementation {len(P.panels[name])}, identical: {my_panels[name] == [i.key for i in P.panels[name]]}")

# ---------------------------------------------------------------- properties the ADR requires ------------------------------------------------------
pg = {n: {kg[k] for k in v} for n, v in my_panels.items()}
names = sorted(pg)
shared = [(a, b, len(pg[a] & pg[b])) for i, a in enumerate(names) for b in names[i + 1 :] if pg[a] & pg[b]]
say(f"[disjointness] panel pairs sharing identity groups: {shared}")
gq = {kg[k] for k in q}
multi = Counter(kg[k] for k in q)
say(f"[Q] identity groups drawn more than once into Q (before the fit/check split): {sum(1 for v in multi.values() if v > 1)}")
g1 = data.gate_g1(P, [], {})
say(f"[G1 on panels only] ok = {g1['ok']}; problems = {g1['problems'][:4]}")
# evaluation-side keys whose group is training-side (eval_keys draws on string membership, not on the group's side)
bad_eval = [k for k in evok if side[kg[k]] != "eval"]
say(f"[eval keys] in-vocabulary evaluation candidates whose identity group is on the training side: {len(bad_eval)}")
# no-gold sources
has_ref = {c: set() for c in TASKS}
for c, e, t in pairs:
    has_ref[c] |= {ne[e], nx[e]}
for c in TASKS:
    mine_src = sorted(k for k in train_keys if okl(k) and inv(k) and k not in has_ref[c] and my_expand_as_implemented(min(eng[e] for e in eng if ne[e] == k)) not in has_ref[c])
    say(f"[sources {c}] mine {len(mine_src)}, implementation {len(P.source_pool[c])}, identical: {mine_src == [i.key for i in P.source_pool[c]]}; any in an evaluation string: {any(k in eval_str for k in mine_src)}")
    qd = {kg[k] for n in ('Q_fit', 'Q_check', 'D_cal', 'D_con') for k in my_panels[n]}
    gp = [k for k in train_keys if k in kg and side[kg[k]] == "train" and k in refs[c] and okl(k) and inv(k) and kg[k] not in qd]
    say(f"[gold pool {c}] mine {len(gp)}, implementation {len(P.gold_pool[c])}, identical: {gp == [i.key for i in P.gold_pool[c]]}")

# ---------------------------------------------------------------- replicate draws (section 5.2, 9) ---------------------------------------------------
# synthetic accepted pools with a shared part, drawn with the implementation and recomputed independently
src_a = [data.TrainItem(f"s{k:04d}", f"S {k}", f"T_A {k}") for k in range(0, 160)]
src_b = [data.TrainItem(f"s{k:04d}", f"S {k}", f"T_B {k}") for k in range(100, 251)]  # 60 shared keys (100..159), shared count even
gold = {c: P.gold_pool[c] for c in TASKS}
s2 = data.Sizes(**{**sizes.__dict__, "accepted_per_replicate": 80, "gold_per_replicate": min(len(gold["A"]), len(gold["B"]), 30)})
acc = {"A": src_a, "B": src_b}
suf = data.sufficiency_after_filter(acc, gold, s2)
shared_n = 60
need = math.ceil(80 * 1.25)
say(f"[sufficiency] implementation available {suf['available']}, needed {suf['needed']}; mine available A = {160 - shared_n + shared_n // 2}, B = {151 - shared_n + shared_n // 2}, needed {need}; ok mine = {160 - 30 >= need and 151 - 30 >= need}, implementation = {suf['ok']}")
streams = []
for r in range(4):
    st = data.draw_streams(core.SeedPlan("test", r), acc, gold, s2)
    streams.append(st)
    g1g = torch.Generator().manual_seed(core.SeedPlan("test", r).seed(1))
    sh = sorted({x.key for x in src_a} & {x.key for x in src_b})
    pm = torch.randperm(len(sh), generator=g1g).tolist()
    ta, tb = {sh[i] for i in pm[:30]}, {sh[i] for i in pm[30:60]}
    av = {"A": sorted(x.key for x in src_a if x.key not in sh or x.key in ta), "B": sorted(x.key for x in src_b if x.key not in sh or x.key in tb)}
    mine_t = {c: [av[c][i] for i in torch.randperm(len(av[c]), generator=g1g).tolist()[:80]] for c in TASKS}
    g5 = torch.Generator().manual_seed(core.SeedPlan("test", r).seed(5))
    mine_g = {c: [sorted(gold[c], key=lambda x: x.key)[i].key for i in torch.randperm(len(gold[c]), generator=g5).tolist()[: s2.gold_per_replicate]] for c in TASKS}
    same = all(mine_t[c] == [x.key for x in st.t[c]] and mine_g[c] == [x.key for x in st.gold[c]] for c in TASKS)
    disj = not ({x.key for x in st.t["A"]} & {x.key for x in st.t["B"]})
    say(f"[draw r{r}] identical to my recomputation: {same}; T_A and T_B disjoint in English: {disj}; sizes {len(st.t['A'])}/{len(st.t['B'])}/{len(st.gold['A'])}/{len(st.gold['B'])}")
say(f"[overlap] implementation's replicate overlap (share of T common to two replicates): { {k: round(v, 3) for k, v in data.replicate_overlap(streams).items() if k.startswith('r0-r1')} }")
# odd shared count: one shared source goes to neither side
src_b_odd = [data.TrainItem(f"s{k:04d}", f"S {k}", f"T_B {k}") for k in range(101, 251)]  # 59 shared
st = data.draw_streams(core.SeedPlan("test", 0), {"A": src_a, "B": src_b_odd}, gold, s2)
say(f"[draw odd] shared 59 -> half {st.half}; T_A and T_B disjoint: {not ({x.key for x in st.t['A']} & {x.key for x in st.t['B']})}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(out) + "\n")
