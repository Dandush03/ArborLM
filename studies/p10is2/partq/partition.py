# ruff: noqa: E501
"""The Part Q partition and panels (ADR-0025 sections 4.1 and 6), a function of a Tatoeba-like corpus and the listed seeds.

Identity groups, the closed vocabulary, the training/evaluation sides and the panel populations are those of ADR-0022 section 5.2 as P10-S2's ``build_partition`` computed them ("as in P10-S2"; section 4.1
step 3); the code here is this study's own because P10-S2's function seeds its generators through its own registry, which refuses this study's seeds. What differs from P10-S2 (the ADR's changes): Q_fit is 2,000,
fixed; there is a Q_check RESERVE of up to 16 blocks of 500 (as many whole blocks as the both-reference supply holds), blocked together with every panel BEFORE the source pools are defined, drawn or not.

Draw order (reading, listed in the report): the partition seed (250901) draws the group assignment, then D_cal, D_con, E_A, E_B, E_C, E_open, in that order; seed 250902 draws Q_fit first of all
training-side panels; seed 250903 draws the reserve (one seeded permutation of the remaining both-reference identity groups; blocks are consecutive runs of 500 in that order). Every panel takes one
representative key per identity group, as P10-S2's did.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import torch

from studies.p10s2.data import CorpusLike, Item, expand_key, n_words
from studies.p10s2.text import expand_contractions, normalize

from ..common import core

TASKS = core.TASKS


@dataclass
class QPartition:
    group_sizes: dict[int, int]
    group_side: dict[int, str]
    vocab: list[str]
    panels: dict[str, list[Item]]  # Q_fit, D_cal, D_con, E_A, E_B, E_C, E_open
    reserve_blocks: list[list[Item]]  # the Q_check reserve, whole blocks of 500 in their seeded order
    source_pool: dict[str, list[Item]]  # capability -> no-gold sources (in-vocabulary, 3-10 words), excluding every panel group and the whole reserve
    eval_strings: frozenset[str]
    counts: dict[str, Any] = field(default_factory=dict)
    group_of_key: dict[str, int] = field(default_factory=dict)

    def panel_groups(self) -> set[int]:
        out = {i.group for items in self.panels.values() for i in items if i.group >= 0}
        out |= {i.group for b in self.reserve_blocks for i in b if i.group >= 0}
        return out


def _gen(seed: int, purpose: str, allowed: frozenset[int] | set[int]) -> torch.Generator:
    return core.seeded_generator(seed, purpose, allowed)


def build_partition(corpus: CorpusLike, cfg: Mapping[str, Any], seeds: Mapping[str, int], allowed: frozenset[int] | set[int], *, sizes: Mapping[str, int] | None = None) -> QPartition:
    d, pn = cfg["data"], dict(cfg["panels"])
    if sizes:
        pn.update(sizes)  # tests use small panels; the registered run passes none
    min_w, max_w = int(d["min_words"]), int(d["max_words"])
    gen = _gen(seeds["partition"], "partition: group assignment, then D_cal, D_con, E_A, E_B, E_C, E_open", allowed)
    ne_of = {e: normalize(t) for e, t in corpus.eng.items()}
    nx_of = {e: normalize(expand_contractions(t)) for e, t in corpus.eng.items()}
    tgt = {"A": corpus.deu, "B": corpus.fra}
    links = {"A": corpus.links_de, "B": corpus.links_fr}
    pairs = sorted((cap, e, t) for cap in TASKS for e, t in links[cap] if e in corpus.eng and t in tgt[cap])
    refs: dict[str, dict[str, dict[str, str]]] = {c: defaultdict(dict) for c in TASKS}
    rep: dict[str, str] = {}
    for eid, etext in sorted(corpus.eng.items()):
        n = ne_of[eid]
        if n and (n not in rep or etext < rep[n]):
            rep[n] = etext
    has_ref_key: dict[str, set[str]] = {c: set() for c in TASKS}
    for cap, e, t in pairs:
        refs[cap][ne_of[e]].setdefault(normalize(tgt[cap][t]), tgt[cap][t])
        has_ref_key[cap].update((ne_of[e], nx_of[e]))
    parent = list(range(len(pairs)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first: dict[tuple[str, str], int] = {}
    for i, (cap, e, t) in enumerate(pairs):
        for kind, s in (("e", ne_of[e]), ("x", nx_of[e]), ("r", normalize(tgt[cap][t]))):
            if (kind, s) in first:
                a, b = find(first[(kind, s)]), find(i)
                if a != b:
                    parent[max(a, b)] = min(a, b)
            else:
                first[(kind, s)] = i
    comp: dict[int, list[int]] = defaultdict(list)
    for i in range(len(pairs)):
        comp[find(i)].append(i)
    ordered = sorted(comp.values(), key=lambda m: m[0])
    group_of_pair = {i: g for g, members in enumerate(ordered) for i in members}
    group_sizes = {g: len(m) for g, m in enumerate(ordered)}
    group_of_key: dict[str, int] = {}
    for i, (_cap, e, _t) in enumerate(pairs):
        group_of_key[ne_of[e]] = group_of_pair[i]
    large = {g for g, s in group_sizes.items() if s > int(d["large_group_pairs"])}
    small = [g for g in group_sizes if g not in large]
    remaining = sum(group_sizes[g] for g in small)
    perm = torch.randperm(len(small), generator=gen).tolist() if small else []
    side = {g: "train" for g in group_sizes}
    eval_pairs = 0
    for k in perm:
        if eval_pairs >= float(d["evaluation_fraction"]) * remaining:
            break
        side[small[k]] = "eval"
        eval_pairs += group_sizes[small[k]]
    eval_strings: set[str] = set()
    for i, (_cap, e, _t) in enumerate(pairs):
        if side[group_of_pair[i]] == "eval":
            eval_strings.update((ne_of[e], nx_of[e]))
    train_en = [e for e in sorted(corpus.eng) if ne_of[e] and ne_of[e] not in eval_strings and nx_of[e] not in eval_strings]
    freq: Counter[str] = Counter()
    for e in train_en:
        if min_w <= n_words(ne_of[e]) <= max_w:
            freq.update(ne_of[e].split())
    vocab = [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[: int(d["vocabulary"])]]
    vset = set(vocab)

    def in_vocab(n: str) -> bool:
        return all(w in vset for w in n.split())

    def ok_len(n: str) -> bool:
        return min_w <= n_words(n) <= max_w

    def item(n: str) -> Item:
        return Item(n, rep[n], {c: tuple(v for _, v in sorted(refs[c][n].items())) for c in TASKS if n in refs[c]}, group_of_key.get(n, -1))

    train_keys = sorted({ne_of[e] for e in train_en})
    eval_keys = sorted(k for k in rep if k in eval_strings and k in group_of_key and side[group_of_key[k]] == "eval")
    train_both = [k for k in train_keys if k in group_of_key and ok_len(k) and in_vocab(k) and all(k in refs[c] for c in TASKS) and side[group_of_key[k]] == "train"]
    used: set[int] = set()

    def group_reps(cands: list[str]) -> list[str]:
        seen: set[int] = set()
        reps: list[str] = []
        for k in cands:
            gid = group_of_key.get(k, -1)
            if gid in used or (gid >= 0 and gid in seen):
                continue
            if gid >= 0:
                seen.add(gid)
            reps.append(k)
        return reps

    def draw_plain(cands: list[str], n: int, g: torch.Generator) -> list[Item]:
        avail = group_reps(cands)
        order = torch.randperm(len(avail), generator=g).tolist() if avail else []
        items = [item(avail[i]) for i in order[:n]]
        used.update(i.group for i in items if i.group >= 0)
        return items

    def draw_stratified(cands: list[str], n: int, caps: Sequence[str]) -> list[Item]:
        avail = group_reps(cands)
        s1 = [k for k in avail if all(len(refs[c][k]) == 1 for c in caps)]
        s1set = set(s1)
        s2 = [k for k in avail if k not in s1set]
        total = len(s1) + len(s2)
        want = min(n, total)
        n1 = min(len(s1), round(want * len(s1) / total)) if total else 0
        n2 = min(len(s2), want - n1)
        n1 = min(len(s1), want - n2)
        chosen: list[str] = []
        for pool_, m in ((s1, n1), (s2, n2)):
            order = torch.randperm(len(pool_), generator=gen).tolist() if pool_ else []
            chosen += [pool_[i] for i in order[:m]]
        items = [item(k) for k in chosen]
        used.update(i.group for i in items if i.group >= 0)
        return items

    panels: dict[str, list[Item]] = {}
    both_groups_at_start = len(group_reps(train_both))
    panels["Q_fit"] = draw_plain(train_both, int(pn["q_fit"]), _gen(seeds["q_fit"], "Q_fit draw", allowed))
    panels["D_cal"] = draw_plain(train_both, int(pn["d_cal"]), gen)
    panels["D_con"] = draw_plain(train_both, int(pn["d_con"]), gen)
    block = int(pn["q_check_block"])
    avail_reserve = group_reps(train_both)
    n_blocks = min(int(pn["q_check_blocks_max"]), len(avail_reserve) // block)
    rg = _gen(seeds["q_check_reserve_order"], "Q_check reserve order", allowed)
    rorder = torch.randperm(len(avail_reserve), generator=rg).tolist() if avail_reserve else []
    reserve_items = [item(avail_reserve[i]) for i in rorder[: n_blocks * block]]
    used.update(i.group for i in reserve_items if i.group >= 0)
    reserve_blocks = [reserve_items[b * block : (b + 1) * block] for b in range(n_blocks)]
    ev_ok = [k for k in eval_keys if k in group_of_key and ok_len(k) and in_vocab(k)]
    panels["E_A"] = draw_stratified([k for k in ev_ok if k in refs["A"]], int(pn["e_eval"]), ["A"])
    panels["E_B"] = draw_stratified([k for k in ev_ok if k in refs["B"]], int(pn["e_eval"]), ["B"])
    panels["E_C"] = draw_stratified([k for k in ev_ok if all(k in refs[c] for c in TASKS)], int(pn["e_combined"]), list(TASKS))
    open_c = [k for k in eval_keys if k in group_of_key and ok_len(k) and not in_vocab(k) and any(k in refs[c] for c in TASKS)]
    panels["E_open"] = draw_plain(open_c, int(pn["e_open"]), gen)
    blocked = {i.group for items in panels.values() for i in items if i.group >= 0} | {i.group for i in reserve_items if i.group >= 0}
    source_pool = {c: [item(k) for k in train_keys if ok_len(k) and in_vocab(k) and k not in has_ref_key[c] and expand_key(rep[k]) not in has_ref_key[c] and group_of_key.get(k, -1) not in blocked] for c in TASKS}
    counts = {
        "pairs": len(pairs), "groups": len(ordered), "vocabulary": len(vocab), "eval_pairs": eval_pairs, "train_both_reference_groups_at_start": both_groups_at_start,
        "panel_sizes": {k: len(v) for k, v in panels.items()}, "reserve_blocks": len(reserve_blocks), "reserve_items": len(reserve_items), "source_pool": {c: len(v) for c, v in source_pool.items()},
        "shared_sources": len({source_unit_key(x) for x in source_pool["A"]} & {source_unit_key(x) for x in source_pool["B"]}),
        "eval_side_candidates": {"E_A": len([k for k in ev_ok if k in refs["A"]]), "E_B": len([k for k in ev_ok if k in refs["B"]]), "E_C": len([k for k in ev_ok if all(k in refs[c] for c in TASKS)])},
    }  # fmt: skip
    return QPartition(group_sizes, side, vocab, panels, reserve_blocks, source_pool, frozenset(eval_strings), counts, group_of_key)


def source_unit_key(x: Item) -> str:
    """The identity unit of a no-gold source (ADR-0022's lane-A ruling): its contraction-expanded normalized string, or its group if it has one."""
    return f"g{x.group}" if x.group >= 0 else "x:" + expand_key(x.en)


def fixed_input_problems(p: QPartition, cfg: Mapping[str, Any], *, ordinary_windows_left: int | None = None, marker_like_windows: int | None = None, sizes: Mapping[str, int] | None = None) -> list[str]:
    """Step 2 of section 4.1, before any teacher runs: E_A and E_B at least 500 items each and E_C at least 250; at least 3,300 training-side in-vocabulary sentences with both references (Q_fit, D_cal, D_con and
    one Q_check block); 44 marker-like and, after the ledger exclusion, at least 100 ordinary GEN windows. A non-empty list is QUALIFICATION-INCONCLUSIVE: DATA-INSUFFICIENT."""
    pn = dict(cfg["panels"])
    if sizes:
        pn.update(sizes)
    out: list[str] = []
    for name, need in (("E_A", pn["e_eval_min"]), ("E_B", pn["e_eval_min"]), ("E_C", pn["e_combined_min"])):
        if len(p.panels[name]) < int(need):
            out.append(f"{name} has {len(p.panels[name])} items, needs {need}")
    train_side = len(p.panels["Q_fit"]) + len(p.panels["D_cal"]) + len(p.panels["D_con"]) + (len(p.reserve_blocks[0]) if p.reserve_blocks else 0)
    need_train = int(pn["q_fit"]) + int(pn["d_cal"]) + int(pn["d_con"]) + int(pn["q_check_block"])
    if train_side < need_train or not p.reserve_blocks:
        out.append(f"training-side both-reference sentences: {train_side} drawn, needs {need_train} (Q_fit, D_cal, D_con and one Q_check block)")
    if marker_like_windows is not None and marker_like_windows != int(pn["gen_marker_like"]):
        out.append(f"{marker_like_windows} marker-like GEN windows, needs exactly {pn['gen_marker_like']}")
    if ordinary_windows_left is not None and ordinary_windows_left < int(pn["gen_ordinary"]):
        out.append(f"{ordinary_windows_left} ordinary GEN windows left after the ledger exclusion, needs {pn['gen_ordinary']}")
    return out


def corpus_supply(corpus: CorpusLike, cfg: Mapping[str, Any]) -> dict[str, int]:
    """The corpus-level supply of the Part Q measuring rehearsal (section 4.1 step 3, third bullet): in-vocabulary identity groups with a German reference, a French reference and both. These counts need no
    partition seed: the vocabulary here is the 2,000 most frequent words of ALL sentences of 3-10 words (reading: the registered vocabulary depends on the partition's sides, so the rehearsal partition's own
    counts are printed beside these)."""
    d = cfg["data"]
    min_w, max_w = int(d["min_words"]), int(d["max_words"])
    ne = {e: normalize(t) for e, t in corpus.eng.items()}
    freq: Counter[str] = Counter()
    for n in {x for x in ne.values() if x and min_w <= n_words(x) <= max_w}:
        freq.update(n.split())
    vset = {w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[: int(d["vocabulary"])]}
    have: dict[str, set[str]] = {c: set() for c in TASKS}
    for cap, links, store in (("A", corpus.links_de, corpus.deu), ("B", corpus.links_fr, corpus.fra)):
        for e, t in links:
            if e in corpus.eng and t in store:
                have[cap].add(ne[e])
    ok = {n for n in have["A"] | have["B"] if min_w <= n_words(n) <= max_w and all(w in vset for w in n.split())}
    return {"in_vocabulary_keys_with_german": len(ok & have["A"]), "in_vocabulary_keys_with_french": len(ok & have["B"]), "in_vocabulary_keys_with_both": len(ok & have["A"] & have["B"])}


def blocks_needed(accepted_per_block_mean: float, target: int) -> int:
    """Whole blocks of the reserve a teacher is expected to need at a given acceptance share: a planning aid for the report, not a rule."""
    return math.ceil(target / max(accepted_per_block_mean, 1e-9))
