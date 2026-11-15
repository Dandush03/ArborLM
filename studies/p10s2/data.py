# ruff: noqa: E501
"""Partitions, panels, identity groups, closed vocabulary, no-gold sources and training draws (ADR-0022 sections 5.1, 5.2, 9; gate G1).

Everything here is a function of a ``Corpus`` (Tatoeba-like exports: sentence tables and the two link tables) and of listed seeds. The partition seed 220901 draws, in this order: the assignment of
identity groups, then Q, D_cal, D_con, E_A, E_B, E_C, E_open (section 9); the Q split uses 220902. The replicate draws use +1 (split of shared sources, then A, then B) and +5 (gold, A then B).
Points the ADR leaves open are marked "reading" in comments and listed in the implementer's report.
"""

import bz2
import math
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import torch

from . import core
from .text import expand_contractions, normalize


class CorpusLike(Protocol):
    @property
    def eng(self) -> dict[int, str]: ...
    @property
    def deu(self) -> dict[int, str]: ...
    @property
    def fra(self) -> dict[int, str]: ...
    @property
    def links_de(self) -> list[tuple[int, int]]: ...
    @property
    def links_fr(self) -> list[tuple[int, int]]: ...


# --- sizes (registered values from the config; the dry stage passes smaller ones) ---------------------------------------------------------------------
@dataclass(frozen=True)
class Sizes:
    vocabulary: int
    min_words: int
    max_words: int
    large_group_pairs: int
    evaluation_fraction: float
    panel_eval: int
    panel_eval_min: int
    panel_combined: int
    panel_combined_min: int
    panel_open: int
    panel_q_fit: int
    panel_q_check: int
    panel_d_cal: int
    panel_d_con: int
    accepted_per_replicate: int
    gold_per_replicate: int
    sufficiency_factor: float
    generation_sources_max: int
    check_min_accepted: int

    @staticmethod
    def registered() -> "Sizes":
        d = core.CFG["data"]
        return Sizes(d["vocabulary"], d["min_words"], d["max_words"], d["large_group_pairs"], d["evaluation_fraction"], d["panel_eval"], d["panel_eval_min"], d["panel_combined"], d["panel_combined_min"], d["panel_open"], d["panel_q_fit"], d["panel_q_check"], d["panel_d_cal"], d["panel_d_con"], d["accepted_per_replicate"], d["gold_per_replicate"], d["sufficiency_factor"], d["generation_sources_max"], core.CFG["filter"]["check_min_accepted"])  # fmt: skip

    @staticmethod
    def dry() -> "Sizes":
        d, r = core.CFG["dry"], core.CFG["data"]
        return Sizes(d["vocabulary"], r["min_words"], r["max_words"], r["large_group_pairs"], r["evaluation_fraction"], d["panel_eval"], d["panel_eval_min"], d["panel_combined"], d["panel_combined_min"], d["panel_open"], d["panel_q_fit"], d["panel_q_check"], d["panel_d_cal"], d["panel_d_con"], d["accepted_per_replicate"], d["gold_per_replicate"], r["sufficiency_factor"], 400, 6)  # fmt: skip


# --- parsing the exports (the real exports are bz2-compressed tab-separated files) ---------------------------------------------------------------------
def parse_sentences(data: bytes, compressed: bool = True) -> dict[int, str]:
    """``id <TAB> language <TAB> text`` lines (the plain sentence files, not the detailed ones)."""
    raw = bz2.decompress(data) if compressed else data
    out: dict[int, str] = {}
    for line in raw.decode("utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].isdigit():
            out[int(parts[0])] = parts[2]
    return out


def parse_links(data: bytes, compressed: bool = True) -> list[tuple[int, int]]:
    """``sentence id <TAB> translation id`` lines. The column format is to be verified at download (section 14.1)."""
    raw = bz2.decompress(data) if compressed else data
    out: list[tuple[int, int]] = []
    for line in raw.decode("utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            out.append((int(parts[0]), int(parts[1])))
    return out


def link_symmetry(forward: Sequence[tuple[int, int]], backward: Sequence[tuple[int, int]]) -> dict[str, int]:
    """Symmetry check of the ``eng/`` link file against the ``deu/`` or ``fra/`` one: the count of English sentence ids that have a link in only one direction (reported)."""
    f = {e for e, _ in forward}
    b = {t for _, t in backward}
    return {"english_ids_forward": len(f), "english_ids_backward": len(b), "only_forward": len(f - b), "only_backward": len(b - f)}


# --- items, groups, partition -----------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Item:
    key: str  # normalized English string
    en: str  # representative raw English text
    refs: Mapping[str, tuple[str, ...]]  # capability -> raw references (pooled over all English sentences with this normalized string)
    group: int  # identity group id; -1 for a sentence that has no gold pair

    def to_json(self) -> dict[str, Any]:
        return {"key": self.key, "en": self.en, "refs": {c: list(v) for c, v in sorted(self.refs.items())}, "group": self.group}


@dataclass
class Partition:
    sizes: Sizes
    group_sizes: dict[int, int]  # group id -> number of pairs
    group_side: dict[int, str]  # "train" | "eval"
    large_groups: list[int]
    vocab: list[str]
    vocab_index: dict[str, int]
    panels: dict[str, list[Item]]
    gold_pool: dict[str, list[Item]]  # capability -> training-side gold-bearing items outside Q, D_cal, D_con (in-vocabulary, 3-10 words)
    source_pool: dict[str, list[Item]]  # capability -> no-gold sources (in-vocabulary, 3-10 words)
    eval_strings: frozenset[str]
    counts: dict[str, Any] = field(default_factory=dict)
    group_of_key: dict[str, int] = field(default_factory=dict)

    def panel_hashes(self) -> dict[str, str]:
        return {name: core.digest([i.to_json() for i in items]) for name, items in sorted(self.panels.items())}


def n_words(ne: str) -> int:
    return len(ne.split())


def build_partition(corpus: CorpusLike, mode: str, sizes: Sizes) -> Partition:
    gen = core.partition_gen(mode, "partition", "partition: group assignment, then Q, D_cal, D_con, E_A, E_B, E_C, E_open")
    ne_of = {e: normalize(t) for e, t in corpus.eng.items()}
    nx_of = {e: normalize(expand_contractions(t)) for e, t in corpus.eng.items()}
    tgt = {"A": corpus.deu, "B": corpus.fra}
    links = {"A": corpus.links_de, "B": corpus.links_fr}
    pairs = sorted((cap, e, t) for cap in core.TASKS for e, t in links[cap] if e in corpus.eng and t in tgt[cap])
    # pooled references per normalized English string and capability (raw text kept, de-duplicated by normalized form, first in sorted order)
    refs: dict[str, dict[str, dict[str, str]]] = {c: defaultdict(dict) for c in core.TASKS}
    rep: dict[str, str] = {}
    for eid, etext in sorted(corpus.eng.items()):
        n = ne_of[eid]
        if n and (n not in rep or etext < rep[n]):
            rep[n] = etext
    has_ref_key: dict[str, set[str]] = {c: set() for c in core.TASKS}
    for cap, e, t in pairs:
        nr = normalize(tgt[cap][t])
        refs[cap][ne_of[e]].setdefault(nr, tgt[cap][t])
        has_ref_key[cap].update((ne_of[e], nx_of[e]))
    # identity groups: connected components over gold pairs; an edge on a shared normalized English string, contraction-expanded string, or reference string
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
    # assignment: large groups to training; of the rest the partition seed assigns groups to evaluation until 20% of the remaining pairs (reading: stop at the first group that reaches it)
    large = [g for g, s in group_sizes.items() if s > sizes.large_group_pairs]
    small = [g for g in group_sizes if g not in set(large)]
    remaining = sum(group_sizes[g] for g in small)
    perm = torch.randperm(len(small), generator=gen).tolist() if small else []
    side = {g: "train" for g in group_sizes}
    eval_pairs = 0
    for k in perm:
        if eval_pairs >= sizes.evaluation_fraction * remaining:
            break
        side[small[k]] = "eval"
        eval_pairs += group_sizes[small[k]]
    eval_strings: set[str] = set()
    for i, (_cap, e, _t) in enumerate(pairs):
        if side[group_of_pair[i]] == "eval":
            eval_strings.update((ne_of[e], nx_of[e]))
    # training-side English sentences: every English sentence whose normalized and expanded strings are not on the evaluation side
    train_en = [e for e in sorted(corpus.eng) if ne_of[e] and ne_of[e] not in eval_strings and nx_of[e] not in eval_strings]
    freq: Counter[str] = Counter()
    for e in train_en:
        if sizes.min_words <= n_words(ne_of[e]) <= sizes.max_words:
            freq.update(ne_of[e].split())
    vocab = [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[: sizes.vocabulary]]
    vindex = {w: i for i, w in enumerate(vocab)}
    vset = set(vocab)

    def in_vocab(n: str) -> bool:
        return all(w in vset for w in n.split())

    def ok_len(n: str) -> bool:
        return sizes.min_words <= n_words(n) <= sizes.max_words

    def item(n: str) -> Item:
        return Item(n, rep[n], {c: tuple(v for _, v in sorted(refs[c][n].items())) for c in core.TASKS if n in refs[c]}, group_of_key.get(n, -1))

    all_keys = sorted(rep)
    train_keys = sorted({ne_of[e] for e in train_en})
    eval_keys = sorted(k for k in all_keys if k in eval_strings)
    # candidate lists
    train_both = [k for k in train_keys if k in group_of_key and ok_len(k) and in_vocab(k) and all(k in refs[c] for c in core.TASKS) and side[group_of_key[k]] == "train"]
    used: set[int] = set()
    panels: dict[str, list[Item]] = {}

    def draw_plain(cands: list[str], n: int) -> list[Item]:
        avail = [k for k in cands if group_of_key.get(k, -1) not in used]
        order = torch.randperm(len(avail), generator=gen).tolist() if avail else []
        chosen = [avail[i] for i in order[:n]]
        items = [item(k) for k in chosen]
        used.update(i.group for i in items)
        return items

    def draw_stratified(cands: list[str], n: int, caps: Sequence[str]) -> list[Item]:
        avail = [k for k in cands if group_of_key.get(k, -1) not in used]
        s1 = [k for k in avail if all(len(refs[c][k]) == 1 for c in caps)]
        s2 = [k for k in avail if k not in set(s1)]
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
        used.update(i.group for i in items)
        return items

    q_all = draw_plain(train_both, sizes.panel_q_fit + sizes.panel_q_check)
    q_gen = core.partition_gen(mode, "q_split", "Q split")
    qperm = torch.randperm(len(q_all), generator=q_gen).tolist() if q_all else []
    nfit = min(sizes.panel_q_fit, len(q_all) // 2 if len(q_all) < sizes.panel_q_fit + sizes.panel_q_check else sizes.panel_q_fit)
    panels["Q_fit"] = [q_all[i] for i in qperm[:nfit]]
    panels["Q_check"] = [q_all[i] for i in qperm[nfit:]]
    panels["D_cal"] = draw_plain(train_both, sizes.panel_d_cal)
    panels["D_con"] = draw_plain(train_both, sizes.panel_d_con)
    ev_ok = [k for k in eval_keys if k in group_of_key and ok_len(k) and in_vocab(k)]
    panels["E_A"] = draw_stratified([k for k in ev_ok if k in refs["A"]], sizes.panel_eval, ["A"])
    panels["E_B"] = draw_stratified([k for k in ev_ok if k in refs["B"]], sizes.panel_eval, ["B"])
    panels["E_C"] = draw_stratified([k for k in ev_ok if all(k in refs[c] for c in core.TASKS)], sizes.panel_combined, list(core.TASKS))
    open_c = [k for k in eval_keys if k in group_of_key and ok_len(k) and not in_vocab(k) and any(k in refs[c] for c in core.TASKS)]
    panels["E_open"] = draw_plain(open_c, sizes.panel_open)
    # pools
    gold_pool = {c: [item(k) for k in train_keys if k in group_of_key and side[group_of_key[k]] == "train" and k in refs[c] and ok_len(k) and in_vocab(k) and group_of_key[k] not in {i.group for p in ("Q_fit", "Q_check", "D_cal", "D_con") for i in panels[p]}] for c in core.TASKS}
    source_pool = {c: [item(k) for k in train_keys if ok_len(k) and in_vocab(k) and k not in has_ref_key[c] and expand_key(rep[k]) not in has_ref_key[c]] for c in core.TASKS}
    counts = {
        "pairs": len(pairs), "groups": len(ordered), "group_size_distribution": dict(sorted(Counter(group_sizes.values()).items())), "large_groups": len(large),
        "eval_pairs": eval_pairs, "remaining_pairs": remaining, "vocabulary": len(vocab), "panel_sizes": {k: len(v) for k, v in panels.items()},
        "gold_pool": {c: len(v) for c, v in gold_pool.items()}, "source_pool": {c: len(v) for c, v in source_pool.items()},
        "reference_count_distribution": {name: dict(Counter(min(len(r), 2) for it in items for r in it.refs.values())) for name, items in panels.items()},
    }  # fmt: skip
    return Partition(sizes, group_sizes, {g: s for g, s in side.items()}, large, vocab, vindex, panels, gold_pool, source_pool, frozenset(eval_strings), counts, group_of_key)


def expand_key(raw: str) -> str:
    return normalize(expand_contractions(raw))


# --- sufficiency before generation (section 5.2) ---------------------------------------------------------------------------------------------------
def panel_sufficiency(p: Partition) -> dict[str, Any]:
    """E_A or E_B below 500 items or E_C below 250 gives DATA-INSUFFICIENT (stop before the freeze). The pools are counted before teacher generation is planned."""
    s = p.sizes
    reasons: list[str] = []
    for name, need in (("E_A", s.panel_eval_min), ("E_B", s.panel_eval_min), ("E_C", s.panel_combined_min)):
        if len(p.panels[name]) < need:
            reasons.append(f"{name} has {len(p.panels[name])} items, needs {need}")
    for c in core.TASKS:
        if len(p.source_pool[c]) < s.accepted_per_replicate:
            reasons.append(f"capability {c}: {len(p.source_pool[c])} no-gold sources before filtering, fewer than {s.accepted_per_replicate}")
    return {"ok": not reasons, "reasons": reasons, "outcome": None if not reasons else "TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT"}


def plan_generation(p: Partition, mode: str) -> dict[str, list[Item]]:
    """At most 60,000 sources per capability, a seeded sample (seed 220903; capability A then B)."""
    gen = core.partition_gen(mode, "source_sample", "source sample")
    out: dict[str, list[Item]] = {}
    for c in core.TASKS:
        pool = p.source_pool[c]
        if len(pool) <= p.sizes.generation_sources_max:
            out[c] = list(pool)
        else:
            order = torch.randperm(len(pool), generator=gen).tolist()[: p.sizes.generation_sources_max]
            out[c] = [pool[i] for i in sorted(order)]
    return out


def fixed_subsample(items: Sequence[Item], n: int, mode: str, name: str) -> list[Item]:
    """A subsample drawn once with a listed stream seed (e.g. the 300-item ablation subsample with 220904): first ``n`` of a seeded permutation, in original order."""
    gen = core.partition_gen(mode, name, name)
    order = sorted(torch.randperm(len(items), generator=gen).tolist()[:n])
    return [items[i] for i in order]


# --- replicate training draws (section 5.2, 9) ----------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class TrainItem:
    key: str
    en: str
    target: str
    group: int = -1  # identity group of the source (-1: none)


@dataclass
class Streams:
    t: dict[str, list[TrainItem]]  # T_A^r, T_B^r: accepted teacher outputs
    gold: dict[str, list[TrainItem]]  # Gold_A^r, Gold_B^r
    shared_sources: int
    exclusive: dict[str, int]
    half: int


def sufficiency_after_filter(accepted: Mapping[str, Sequence[TrainItem]], gold_pool: Mapping[str, Sequence[Item]], s: Sizes) -> dict[str, Any]:
    """Each capability: its exclusive accepted sources plus its half of the shared ones >= 8,000 x 1.25, and 8,000 gold pairs outside Q, D_cal and D_con; otherwise DATA-INSUFFICIENT.
    The half is the smaller one when the shared count is odd."""
    ka = {x.key for x in accepted["A"]}
    kb = {x.key for x in accepted["B"]}
    shared = len(ka & kb)
    half = shared // 2
    need = math.ceil(s.accepted_per_replicate * s.sufficiency_factor)
    avail = {"A": len(ka) - shared + half, "B": len(kb) - shared + half}
    reasons = [f"capability {c}: {avail[c]} available accepted sources, needs {need}" for c in core.TASKS if avail[c] < need]
    reasons += [f"capability {c}: {len(gold_pool[c])} gold pairs, needs {s.gold_per_replicate}" for c in core.TASKS if len(gold_pool[c]) < s.gold_per_replicate]
    return {"ok": not reasons, "reasons": reasons, "available": avail, "shared": shared, "half": half, "needed": need, "outcome": None if not reasons else "TRANSFER-INCONCLUSIVE: DATA-INSUFFICIENT"}


def draw_streams(plan: core.SeedPlan, accepted: Mapping[str, Sequence[TrainItem]], gold_pool: Mapping[str, Sequence[Item]], s: Sizes) -> Streams:
    """One replicate's draw. +1: the shared sources are split into two halves assigned to A and B (a seeded permutation), then A is drawn, then B; +5: gold A, then B (fresh generators)."""
    g1 = plan.gen(1, "training draw")
    by = {c: {x.key: x for x in sorted(accepted[c], key=lambda x: x.key)} for c in core.TASKS}
    shared = sorted(set(by["A"]) & set(by["B"]))
    half = len(shared) // 2
    perm = torch.randperm(len(shared), generator=g1).tolist() if shared else []
    to_a = {shared[i] for i in perm[:half]}
    to_b = {shared[i] for i in perm[half : 2 * half]}
    avail = {"A": [by["A"][k] for k in sorted(by["A"]) if k not in set(shared) or k in to_a], "B": [by["B"][k] for k in sorted(by["B"]) if k not in set(shared) or k in to_b]}
    t: dict[str, list[TrainItem]] = {}
    for c in core.TASKS:
        order = torch.randperm(len(avail[c]), generator=g1).tolist()[: s.accepted_per_replicate]
        t[c] = [avail[c][i] for i in order]
    g5 = plan.gen(5, "gold draw")
    gold: dict[str, list[TrainItem]] = {}
    for c in core.TASKS:
        pool = sorted(gold_pool[c], key=lambda x: x.key)
        order = torch.randperm(len(pool), generator=g5).tolist()[: s.gold_per_replicate]
        gold[c] = [TrainItem(pool[i].key, pool[i].en, pool[i].refs[c][0], pool[i].group) for i in order]  # reading: the first reference in sorted order
    excl = {c: len(by[c]) - len(shared) for c in core.TASKS}
    return Streams(t, gold, len(shared), excl, half)


def replicate_overlap(streams: Sequence[Streams]) -> dict[str, float]:
    """The share of training items common to each pair of replicates (section 5.2): |intersection| / |T|, per capability, for every pair."""
    out: dict[str, float] = {}
    for i in range(len(streams)):
        for j in range(i + 1, len(streams)):
            for c in core.TASKS:
                a = {x.key for x in streams[i].t[c]}
                b = {x.key for x in streams[j].t[c]}
                out[f"r{i}-r{j}-{c}"] = len(a & b) / max(1, len(a))
    return out


# --- gate G1 -----------------------------------------------------------------------------------------------------------------------------------
def gate_g1(p: Partition, streams: Sequence[Streams], accepted_outputs: Mapping[str, Iterable[str]], eval_ref_norms: Iterable[str] | None = None, *, pool_level: bool = False) -> dict[str, Any]:
    """Gate G1 (partitions): every pair of panels is disjoint in identity groups; every training stream is disjoint from every evaluation panel in identity groups and in English; no normalized
    reference or teacher output of any training stream equals a normalized reference of any evaluation panel; vocabulary closure holds. The pair of two training streams of one side is not
    required to be group-disjoint (reading, reported): T_A and T_B are checked to be disjoint in English. The share of evaluation items with a training neighbour at word-level Levenshtein
    distance 1 is reported."""
    problems: list[str] = []
    eval_names = ("E_A", "E_B", "E_C", "E_open")
    groups = {n: {i.group for i in items if i.group >= 0} for n, items in p.panels.items()}
    names = sorted(p.panels)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if groups[a] & groups[b]:
                problems.append(f"panels {a} and {b} share identity groups")
    eval_groups = set().union(*(groups[n] for n in eval_names))
    eval_keys = {i.key for n in eval_names for i in p.panels[n]}
    eval_refs = set(eval_ref_norms) if eval_ref_norms is not None else {normalize(r) for n in eval_names for it in p.panels[n] for refs in it.refs.values() for r in refs}
    for r, s in enumerate(streams):
        for c in core.TASKS:
            for stream_name, items in (("T", s.t[c]), ("Gold", s.gold[c])):
                keys = {x.key for x in items}
                if keys & eval_keys:
                    problems.append(f"replicate {r} stream {stream_name}_{c} shares English with an evaluation panel")
                gs = {x.group for x in items if x.group >= 0}
                if gs & eval_groups:
                    problems.append(f"replicate {r} stream {stream_name}_{c} shares identity groups with an evaluation panel")
                for x in items:
                    if normalize(x.target) in eval_refs:
                        problems.append(f"replicate {r} stream {stream_name}_{c} has a target equal to an evaluation reference")
                        break
        if not pool_level and {x.key for x in s.t["A"]} & {x.key for x in s.t["B"]}:
            problems.append(f"replicate {r}: T_A and T_B share English sources")
    for c, outs in accepted_outputs.items():
        for o in outs:
            if normalize(o) in eval_refs:
                problems.append(f"teacher output of capability {c} equals an evaluation reference")
                break
    vocab = set(p.vocab)
    for n in ("E_A", "E_B", "E_C"):
        for it in p.panels[n]:
            if not all(w in vocab for w in it.key.split()):
                problems.append(f"panel {n} item outside the closed vocabulary")
                break
    train_keys = {x.key for s in streams for c in core.TASKS for x in s.t[c]} | {i.key for n in ("Q_fit", "Q_check", "D_cal", "D_con") for i in p.panels[n]}
    neighbours = neighbour_share([i.key for n in ("E_A", "E_B", "E_C") for i in p.panels[n]], train_keys)
    return {"ok": not problems, "problems": problems, "neighbour_share_distance_1": neighbours}


def neighbour_share(eval_keys: Sequence[str], train_keys: Iterable[str]) -> float:
    """Share of evaluation items having a training sentence at word-level Levenshtein distance 1 (substitution, insertion or deletion of one word)."""
    by_len: dict[int, list[tuple[str, ...]]] = defaultdict(list)
    for k in train_keys:
        w = tuple(k.split())
        by_len[len(w)].append(w)
    hits = 0
    for k in eval_keys:
        w = tuple(k.split())
        found = False
        for ln in (len(w) - 1, len(w), len(w) + 1):
            for t in by_len.get(ln, ()):
                if word_distance_one(w, t):
                    found = True
                    break
            if found:
                break
        hits += int(found)
    return hits / max(1, len(eval_keys))


def word_distance_one(a: tuple[str, ...], b: tuple[str, ...]) -> bool:
    if a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) == 1
    if abs(len(a) - len(b)) != 1:
        return False
    s, l = (a, b) if len(a) < len(b) else (b, a)  # noqa: E741
    return any(l[:i] + l[i + 1 :] == s for i in range(len(l)))
