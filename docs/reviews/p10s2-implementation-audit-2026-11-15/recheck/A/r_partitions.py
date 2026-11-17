"""Re-check A: an independent reimplementation of ADR-0022 section 5.2 / section 9 under the lead's rulings of 2026-11-15
(panels drawn per identity group, one representative per group = the first key in sorted order; contraction expansion with
attached punctuation stripped; T_A and T_B disjoint in identity units), compared with studies/p10s2/data.py at fc08681 on a
synthetic corpus with multi-key groups. Written by the re-check auditor (Claude Opus 5.5). Synthetic text only; test seeds only
(the implementation's test-mode stand-ins 229951..229962 and replicate bases 229001+100i).
Run from the pinned tree:  <python> -I <this file> <pinned tree>
"""

import math
import random
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

PIN = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(PIN))
sys.path.insert(0, str(PIN / "src"))
import torch  # noqa: E402

from studies.p10s2 import core, data  # noqa: E402

OUT: list[str] = []


def say(s: str) -> None:
    OUT.append(s)
    print(s)


# ---------------------------------------------------------------- my text functions, written from the ADR's words --------------------------------
CONTR = {  # the list is "fixed in the code" (section 5.2); I copy it by value from text.py's literal, then use my own lookup
    "don't": "do not", "doesn't": "does not", "didn't": "did not", "can't": "cannot", "won't": "will not", "isn't": "is not", "aren't": "are not", "wasn't": "was not",
    "weren't": "were not", "haven't": "have not", "hasn't": "has not", "hadn't": "had not", "wouldn't": "would not", "couldn't": "could not", "shouldn't": "should not",
    "i'm": "i am", "you're": "you are", "he's": "he is", "she's": "she is", "it's": "it is", "we're": "we are", "they're": "they are", "i've": "i have", "you've": "you have",
    "we've": "we have", "they've": "they have", "i'll": "i will", "you'll": "you will", "he'll": "he will", "she'll": "she will", "we'll": "we will", "they'll": "they will",
    "i'd": "i would", "you'd": "you would", "he'd": "he would", "she'd": "she would", "we'd": "we would", "they'd": "they would", "that's": "that is", "there's": "there is",
    "what's": "what is", "let's": "let us", "who's": "who is", "where's": "where is",
}
from studies.p10s2.text import CONTRACTIONS  # noqa: E402

say(f"[list] my copy of the contraction list equals text.CONTRACTIONS: {CONTR == CONTRACTIONS}")


def isP(c: str) -> bool:
    return unicodedata.category(c)[0] == "P"


def norm(t: str) -> str:
    t = unicodedata.normalize("NFC", t).lower()
    return " ".join("".join(c for c in t if not isP(c)).split())


def expand(t: str) -> str:
    """Lower-cased NFC text, curly apostrophe made straight; in every whitespace token the leading and trailing punctuation other than the apostrophe is
    set aside; if the remaining core (or the core without wrapping apostrophes) is a listed contraction, it is replaced. Then normalized."""
    t = unicodedata.normalize("NFC", t).lower().replace("’", "'")
    outw = []
    for w in t.split():
        i, j = 0, len(w)
        while i < j and isP(w[i]) and w[i] != "'":
            i += 1
        while j > i and isP(w[j - 1]) and w[j - 1] != "'":
            j -= 1
        mid = w[i:j]
        if mid in CONTR:
            w = w[:i] + CONTR[mid] + w[j:]
        else:
            mid2 = mid.strip("'")
            if mid2 != mid and mid2 in CONTR:
                w = w[:i] + mid.replace(mid2, CONTR[mid2], 1) + w[j:]
        outw.append(w)
    return norm(" ".join(outw))


# ---------------------------------------------------------------- synthetic corpus with multi-key groups --------------------------------------
@dataclass
class Corpus:
    eng: dict
    deu: dict
    fra: dict
    links_de: list
    links_fr: list


rng = random.Random(4242)  # my own stand-in generator, not a study seed
SUBJ = ["Tom", "Mary", "We", "They", "You", "The boy", "The girl", "My father"]
VERB = ["likes", "sees", "wants", "needs", "has", "reads", "eats", "buys"]
OBJ = ["apples", "a book", "the dog", "the cat", "water", "bread", "music", "a car", "the house", "milk"]
ADV = ["", "today", "now", "again", "too", "every day"]
eng, deu, fra, lde, lfr = {}, {}, {}, [], []
nid = [1]


def add(d: dict, text: str) -> int:
    i = nid[0]
    nid[0] += 1
    d[i] = text
    return i


def tr(s: str, lang: str, salt: str = "") -> str:
    return " ".join((w[::-1] + ("e" if lang == "de" else "u")) for w in norm(s).split()) + salt + "."


plain = set()
while len(plain) < 1400:
    plain.add(f"{rng.choice(SUBJ)} {rng.choice(VERB)} {rng.choice(OBJ)} {rng.choice(ADV)}".strip() + ".")
for s in sorted(plain):
    e = add(eng, s)
    r = rng.random()
    if r < 0.45:
        lde.append((e, add(deu, tr(s, "de"))))
        lfr.append((e, add(fra, tr(s, "fr"))))
    elif r < 0.60:
        lde.append((e, add(deu, tr(s, "de"))))
    elif r < 0.75:
        lfr.append((e, add(fra, tr(s, "fr"))))
contraction_pairs = []
for o in OBJ:
    for v in ("like", "want"):  # mid-sentence contraction, both forms with both references (a multi-key group of both-reference keys)
        a, b = add(eng, f"I don't {v} {o} now."), add(eng, f"I do not {v} {o} now.")
        for e, salt in ((a, " x"), (b, " y")):
            lde.append((e, add(deu, tr(eng[e], "de", salt))))
            lfr.append((e, add(fra, tr(eng[e], "fr", salt))))
        contraction_pairs.append((a, b))
for o in OBJ + ["bread too", "milk again", "music today"]:  # punctuation attached to the contraction (audit M2)
    a, b = add(eng, f"No, {o.split()[0]} says I can't."), add(eng, f"No, {o.split()[0]} says I cannot.")
    c, d = add(eng, f"Sorry, I can’t, {o} today."), add(eng, f"Sorry, I cannot, {o} today.")
    q1, q2 = add(eng, f"He said 'it's' {o} again."), add(eng, f"He said 'it is' {o} again.")
    for e, salt in ((a, " p"), (b, " q"), (c, " r"), (d, " s"), (q1, " t"), (q2, " u")):
        lde.append((e, add(deu, tr(eng[e], "de", salt))))
        lfr.append((e, add(fra, tr(eng[e], "fr", salt))))
    contraction_pairs += [(a, b), (c, d), (q1, q2)]
# French-only sentences that share a French reference string with a both-reference sentence (a group that joins a no-German source to a gold-bearing key)
bridge = []
for k in range(150):
    s_both = f"Tom {VERB[k % 8]} {OBJ[k % 10]} here {k % 7} {'again' if k % 2 else 'too'}."
    s_fr_only = f"Tom {VERB[(k + 3) % 8]} {OBJ[k % 10]} there {k % 7} {'again' if k % 2 else 'too'}."
    shared_fr = f"pont {k}."
    a = add(eng, s_both)
    lde.append((a, add(deu, tr(s_both, "de", f" b{k}"))))
    lfr.append((a, add(fra, shared_fr)))
    b = add(eng, s_fr_only)
    lfr.append((b, add(fra, shared_fr)))
    bridge.append((a, b))
for k in range(60):  # one large group (> 50 pairs) through one shared reference
    e = add(eng, f"Yes {SUBJ[k % 8]} {VERB[k % 8]} it {'again' if k % 2 else 'too'} {k}.")
    lde.append((e, add(deu, "Ja.")))
for k in range(200):  # out-of-vocabulary material for E_open
    s = f"{rng.choice(SUBJ)} {rng.choice(VERB)} the zebra{k} {rng.choice(ADV)}".strip() + "."
    e = add(eng, s)
    lde.append((e, add(deu, tr(s, "de"))))
    lfr.append((e, add(fra, tr(s, "fr"))))
for k in range(300):  # sentences with no link at all (no-gold sources for both)
    add(eng, f"{rng.choice(SUBJ)} {rng.choice(VERB)} {rng.choice(OBJ)} quietly {k % 5}.")
corpus = Corpus(eng, deu, fra, lde, lfr)
say(f"synthetic corpus: {len(eng)} English, {len(deu)} German, {len(fra)} French, {len(lde)} + {len(lfr)} links")

sizes = data.Sizes(vocabulary=70, min_words=3, max_words=10, large_group_pairs=50, evaluation_fraction=0.20, panel_eval=40, panel_eval_min=20, panel_combined=20, panel_combined_min=10, panel_open=10, panel_q_fit=40, panel_q_check=40, panel_d_cal=20, panel_d_con=15, accepted_per_replicate=60, gold_per_replicate=60, sufficiency_factor=1.25, generation_sources_max=400, check_min_accepted=6)
core.reset_seed_record()
P = data.build_partition(corpus, "test", sizes)
SEEDS = core.partition_seeds("test")

# ---------------------------------------------------------------- my partition ---------------------------------------------------------------------
TASKS = ("A", "B")
tgt = {"A": deu, "B": fra}
links = {"A": lde, "B": lfr}
pairs = sorted((c, e, t) for c in TASKS for e, t in links[c] if e in eng and t in tgt[c])
ne = {e: norm(t) for e, t in eng.items()}
nx = {e: expand(t) for e, t in eng.items()}
# groups: BFS over the bipartite graph pair <-> string node
node_members = defaultdict(set)
for i, (c, e, t) in enumerate(pairs):
    for node in (("e", ne[e]), ("x", nx[e]), ("r", norm(tgt[c][t]))):
        node_members[node].add(i)
nodes_of = defaultdict(list)
for nd, ms in node_members.items():
    for i in ms:
        nodes_of[i].append(nd)
comp_of, comps = {}, []
for i in range(len(pairs)):
    if i in comp_of:
        continue
    stack, members = [i], []
    comp_of[i] = -1
    while stack:
        j = stack.pop()
        members.append(j)
        for nd in nodes_of[j]:
            for m in node_members[nd]:
                if m not in comp_of:
                    comp_of[m] = -1
                    stack.append(m)
    comps.append(sorted(members))
comps.sort(key=lambda m: m[0])
gid = {i: g for g, m in enumerate(comps) for i in m}
gsize = {g: len(m) for g, m in enumerate(comps)}
kg = {}
for i, (c, e, t) in enumerate(pairs):
    kg[ne[e]] = gid[i]
say(f"[groups] mine {len(comps)}, implementation {len(P.group_sizes)}; key->group map identical: {kg == P.group_of_key}; sizes identical: {gsize == P.group_sizes}")
split = [(a, b) for a, b in contraction_pairs if kg[ne[a]] != kg[ne[b]]]
impl_split = [(a, b) for a, b in contraction_pairs if P.group_of_key[ne[a]] != P.group_of_key[ne[b]]]
say(f"[contractions] {len(contraction_pairs)} contraction variant pairs (mid-sentence, 'can't.', curly 'can’t,', quoted ''it's''); split by me: {len(split)}; split by the implementation: {len(impl_split)}")
for a, b in impl_split[:3]:
    say(f"   implementation splits {eng[a]!r} / {eng[b]!r}")
large = [g for g, s in gsize.items() if s > 50]
small = [g for g in gsize if g not in large]
remaining = sum(gsize[g] for g in small)
gen = torch.Generator().manual_seed(SEEDS["partition"])
perm = torch.randperm(len(small), generator=gen).tolist()
side = {g: "train" for g in gsize}
ev = 0
for k in perm:
    if ev >= 0.2 * remaining:
        break
    side[small[k]] = "eval"
    ev += gsize[small[k]]
say(f"[assignment] large groups {[gsize[g] for g in large]}; eval pairs {ev}/{remaining} = {ev / remaining:.4f}; identical: {side == P.group_side}")
eval_str = set()
for i, (c, e, t) in enumerate(pairs):
    if side[gid[i]] == "eval":
        eval_str |= {ne[e], nx[e]}
train_en = [e for e in sorted(eng) if ne[e] and ne[e] not in eval_str and nx[e] not in eval_str]
freq = Counter(w for e in train_en if 3 <= len(ne[e].split()) <= 10 for w in ne[e].split())
vocab = [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:70]]
say(f"[vocabulary] identical: {vocab == P.vocab}")
refs = {c: defaultdict(dict) for c in TASKS}
for c, e, t in pairs:
    refs[c][ne[e]].setdefault(norm(tgt[c][t]), tgt[c][t])
vs = set(vocab)
inv = lambda k: all(w in vs for w in k.split())  # noqa: E731
okl = lambda k: 3 <= len(k.split()) <= 10  # noqa: E731
train_keys = sorted({ne[e] for e in train_en})
all_keys = sorted({ne[e] for e in eng if ne[e]})
eval_keys = [k for k in all_keys if k in eval_str and k in kg and side[kg[k]] == "eval"]
used: set = set()


def reps(cands):
    first = {}
    for k in sorted(cands):
        g = kg.get(k, -1)
        if g in used:
            continue
        first.setdefault(g if g >= 0 else ("solo", k), k)
    return sorted(first.values())


def d_plain(cands, n):
    av = reps(cands)
    o = torch.randperm(len(av), generator=gen).tolist() if av else []
    ch = [av[i] for i in o[:n]]
    used.update(kg[k] for k in ch if k in kg)
    return ch


def d_strat(cands, n, caps):
    av = reps(cands)
    s1 = [k for k in av if all(len(refs[x][k]) == 1 for x in caps)]
    s2 = [k for k in av if k not in set(s1)]
    tot = len(av)
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
q = d_plain(both, 80)
qg = torch.Generator().manual_seed(SEEDS["q_split"])
qp = torch.randperm(len(q), generator=qg).tolist()
mine = {"Q_fit": [q[i] for i in qp[:40]], "Q_check": [q[i] for i in qp[40:]]}
mine["D_cal"] = d_plain(both, 20)
mine["D_con"] = d_plain(both, 15)
evok = [k for k in eval_keys if okl(k) and inv(k)]
mine["E_A"] = d_strat([k for k in evok if k in refs["A"]], 40, ["A"])
mine["E_B"] = d_strat([k for k in evok if k in refs["B"]], 40, ["B"])
mine["E_C"] = d_strat([k for k in evok if all(k in refs[c] for c in TASKS)], 20, list(TASKS))
mine["E_open"] = d_plain([k for k in eval_keys if okl(k) and not inv(k) and any(k in refs[c] for c in TASKS)], 10)
for n in mine:
    say(f"[panels] {n}: mine {len(mine[n])}, implementation {len(P.panels[n])}, identical: {mine[n] == [i.key for i in P.panels[n]]}")
pg = {n: [kg[k] for k in v] for n, v in mine.items()}
dup_in_panel = {n: len(v) - len(set(v)) for n, v in pg.items()}
names = sorted(pg)
cross = [(a, b) for i, a in enumerate(names) for b in names[i + 1:] if set(pg[a]) & set(pg[b])]
say(f"[groups per panel] identity groups repeated inside a panel: {dup_in_panel}; panel pairs sharing a group: {cross}")
multi_in_both = sum(1 for g in set(kg[k] for k in both) if sum(1 for k in both if kg[k] == g) > 1)
say(f"[multi-key] identity groups with more than one both-reference training key (the case of audit M1): {multi_in_both}")
g1 = data.gate_g1(P, [], {})
say(f"[G1, panels only] implementation: ok = {g1['ok']}, problems = {g1['problems'][:3]}")
has_ref = {c: set() for c in TASKS}
for c, e, t in pairs:
    has_ref[c] |= {ne[e], nx[e]}
rep = {}
for e in sorted(eng):
    if ne[e] and (ne[e] not in rep or eng[e] < rep[ne[e]]):
        rep[ne[e]] = eng[e]
qd_groups = {kg[k] for n in ("Q_fit", "Q_check", "D_cal", "D_con") for k in mine[n]}
my_src = {}
for c in TASKS:
    my_src[c] = [k for k in train_keys if okl(k) and inv(k) and k not in has_ref[c] and expand(rep[k]) not in has_ref[c]]
    say(f"[sources {c}] mine {len(my_src[c])}, implementation {len(P.source_pool[c])}, identical: {my_src[c] == [i.key for i in P.source_pool[c]]}; in an evaluation string: {sum(1 for k in my_src[c] if k in eval_str or expand(rep[k]) in eval_str)}")
    gp = [k for k in train_keys if k in kg and side[kg[k]] == "train" and k in refs[c] and okl(k) and inv(k) and kg[k] not in qd_groups]
    say(f"[gold pool {c}] mine {len(gp)}, implementation {len(P.gold_pool[c])}, identical: {gp == [i.key for i in P.gold_pool[c]]}")
    shared_with_trainpanels = [k for k in my_src[c] if kg.get(k, -1) in qd_groups]
    say(f"[sources {c}] no-gold sources whose identity group is also a group of Q, D_cal or D_con: {len(shared_with_trainpanels)} (e.g. {shared_with_trainpanels[:2]})")

# ---------------------------------------------------------------- replicate draws by identity unit -----------------------------------------------
def unit(key: str, en: str, group: int) -> str:
    return f"g{group}" if group >= 0 else "x:" + expand(en)


acc = {}
for c in TASKS:  # synthetic accepted pools: every source of the pool accepted with a dummy output
    acc[c] = [data.TrainItem(i.key, i.en, f"T{c} {i.key}", i.group) for i in P.source_pool[c]]
gold = P.gold_pool
s2 = data.Sizes(**{**sizes.__dict__, "accepted_per_replicate": 40, "gold_per_replicate": 30})
suf = data.sufficiency_after_filter(acc, gold, s2)
ua = defaultdict(list)
ub = defaultdict(list)
for x in acc["A"]:
    ua[unit(x.key, x.en, x.group)].append(x.key)
for x in acc["B"]:
    ub[unit(x.key, x.en, x.group)].append(x.key)
shared_u = sorted(set(ua) & set(ub))
mine_avail = {"A": sum(len(v) for u, v in ua.items() if u not in shared_u) + len(shared_u) // 2, "B": sum(len(v) for u, v in ub.items() if u not in shared_u) + len(shared_u) // 2}
say(f"[sufficiency] implementation available {suf['available']}, shared units {suf['shared']}; mine available {mine_avail}, shared units {len(shared_u)}; needed {math.ceil(40 * 1.25)}")
for r in range(4):
    st = data.draw_streams(core.SeedPlan("test", r), acc, gold, s2)
    g1g = torch.Generator().manual_seed(229001 + 100 * r + 1)
    pm = torch.randperm(len(shared_u), generator=g1g).tolist()
    h = len(shared_u) // 2
    ta, tb = {shared_u[i] for i in pm[:h]}, {shared_u[i] for i in pm[h:2 * h]}
    own = {"A": ta, "B": tb}
    um = {"A": ua, "B": ub}
    av = {c: sorted(x.key for x in acc[c] if unit(x.key, x.en, x.group) not in shared_u or unit(x.key, x.en, x.group) in own[c]) for c in TASKS}
    mt = {c: [av[c][i] for i in torch.randperm(len(av[c]), generator=g1g).tolist()[:40]] for c in TASKS}
    g5 = torch.Generator().manual_seed(229001 + 100 * r + 5)
    mg = {c: [sorted(gold[c], key=lambda x: x.key)[i].key for i in torch.randperm(len(gold[c]), generator=g5).tolist()[:30]] for c in TASKS}
    same = all(mt[c] == [x.key for x in st.t[c]] and mg[c] == [x.key for x in st.gold[c]] for c in TASKS)
    ua_r = {unit(x.key, x.en, x.group) for x in st.t["A"]}
    ub_r = {unit(x.key, x.en, x.group) for x in st.t["B"]}
    gA = {x.group for x in st.t["A"] if x.group >= 0}
    gB = {x.group for x in st.t["B"] if x.group >= 0}
    evg = {kg[k] for n in ("E_A", "E_B", "E_C", "E_open") for k in mine[n]}
    sg = data.gate_g1(P, [st], {c: [x.target for x in st.t[c]] for c in TASKS})
    trainpanel_share = {c: len({x.group for x in st.t[c] if x.group >= 0} & qd_groups) for c in TASKS}
    say(f"[draw r{r}] identical to mine: {same}; T_A/T_B share units: {len(ua_r & ub_r)}, groups: {len(gA & gB)}; streams share eval groups: {len((gA | gB) & evg)}; stream groups shared with Q/D_cal/D_con {trainpanel_share}; implementation G1 ok = {sg['ok']}")
Path(__file__).with_suffix(".out.txt").write_text("\n".join(OUT) + "\n")
