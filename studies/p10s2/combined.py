# ruff: noqa: E501
"""The combined tasks C1 and C2 (ADR-0022 combined-tasks addendum, section numbers below are the addendum's).

C1 (two sources, two tasks, one sequence): item j answers the sentence s1 = E_C[sigma(j)] in the task T1 and then, with its own answer left in the context, s2 = E_C[sigma(j+1 mod n)] in the other
task T2; T1 is A (German) for even j and B (French) for odd j (sections 2, 3, 4). C2 (one source, both tasks): s in German, then, with its own German answer in the context, the same s in French; the
source words carry the reads of both tasks, summed (section 5). Both are segment-level: an input is the concatenation of stored segment ids and every read position is a stored position plus an offset.
The oracle route only; no keyword-router lane; never trained on. The step-2 input is the continuation of step 1's sequence: decoding with the cache kept from step 1 must equal full recomputation
(``check_continuation``).

Answer ids a1 are the generated ids strictly before the stop token (all of them if the new-token limit is reached, whose last token is then fed through the model before the step-2 input); the stored
newline segment follows a1 in the context; the stop token itself is not in the context (section 4.1). L-sep (``AdapterRouteArm``) uses position-wise adapters on C1 and a switch per answer on C2
(section 7). Everything here is descriptive and printed under the oracle-assisted line (``report``).
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch

from . import core
from .evaluate import EvalContext, generate
from .memory import Arm
from .model import PositionAdapter
from .text import chrf_item, mean, normalize
from .tokenization import Example
from .train import reads_of

CPU = torch.device("cpu")
LANG = {"A": "German", "B": "French"}


@dataclass(frozen=True)
class Sentence:
    key: str
    ex: Mapping[str, Example]  # task -> the single-task prompt P_task(x)
    refs: Mapping[str, tuple[str, ...]]


@dataclass(frozen=True)
class Pair:
    j: int
    i1: int
    i2: int
    t1: str
    t2: str


@dataclass
class CombinedSet:
    sentences: list[Sentence]
    pairs: list[Pair]
    sigma: list[int] | None  # None: a rehearsal or test set paired in stored order


def draw_sigma(n: int, mode: str) -> list[int]:
    """The listed seed 220911, 'C1 pairing': one uniform permutation of 0..n-1 drawn once, in the partition step, after E_C is built; stored with the data manifest."""
    gen = core.partition_gen(mode, "c1_pairing", "C1 pairing")
    return [int(i) for i in torch.randperm(n, generator=gen).tolist()]


def pair_list(n: int, sigma: Sequence[int] | None) -> list[Pair]:
    """Item j is (s1, s2) = (E_C[sigma(j)], E_C[sigma((j+1) mod n)]); the task order alternates by the parity of j (A first for even j). Without sigma (rehearsal, tests) item i is paired with i+1 mod n in
    stored order, with the same alternation and no seed."""
    if n < 2:
        raise ValueError("C1 needs at least two sentences")
    order = list(range(n)) if sigma is None else [int(i) for i in sigma]
    if sorted(order) != list(range(n)):
        raise ValueError("the pairing is not a permutation")
    out = []
    for j in range(n):
        t1 = "A" if j % 2 == 0 else "B"
        out.append(Pair(j, order[j], order[(j + 1) % n], t1, core.other_task(t1)))
    return out


def pairs_digest(pairs: Sequence[Pair]) -> str:
    """The hash of the pair list with each item's task order, stored in the data manifest."""
    return core.digest([[p.i1, p.i2, p.t1] for p in pairs])


def combined_set(sentences: Sequence[Sentence], sigma: Sequence[int] | None) -> CombinedSet:
    return CombinedSet(list(sentences), pair_list(len(sentences), sigma), None if sigma is None else [int(i) for i in sigma])


def duplicate_normalized(keys: Sequence[str]) -> int:
    """The data-generation step asserts that no two E_C items share a normalized English string, and reports the count (section 3)."""
    seen: dict[str, int] = {}
    for k in keys:
        n = normalize(k)
        seen[n] = seen.get(n, 0) + 1
    return sum(v - 1 for v in seen.values() if v > 1)


# --- one answer ---------------------------------------------------------------------------------------------------------------------------------
def _bos(ex: Example) -> int:
    return len(ex.segments[0].ids) if ex.segments and ex.segments[0].text == "<bos>" else 0


def split_answer(ctx: EvalContext, g: Sequence[int]) -> tuple[list[int], bool, bool]:
    """(a, hit_limit, stop token carried bytes before its newline): a is the generated ids strictly before the stop token; all of them if no stop token was generated."""
    k = ctx.decoder.stop_index(g)
    if k is None:
        return list(g), True, False
    extra = ctx.decoder.table[g[k]].index(b"\n") > 0
    return list(g[:k]), False, extra


@dataclass
class ItemOut:
    g1: list[int]
    g2: list[int]
    hit: tuple[bool, bool]
    extra: tuple[bool, bool]
    length_ok: bool = True


def _tensor(ids: Sequence[int]) -> torch.Tensor:
    return torch.tensor([list(ids)])


def _two_step(ctx: EvalContext, arm: Arm, ids1: list[int], reads1: list[Any], suffix_fn: Any, *, full: bool = False, lsep_owner: tuple[str, str] | None = None) -> ItemOut:
    """Step 1 on ``ids1`` with ``reads1``; step 2 continues the sequence (cache from step 1) or, with ``full``, recomputes the whole step-2 input. ``lsep_owner`` (T1, T2) selects the position-wise
    adapters of L-sep (C1)."""
    from .cells import AdapterRouteArm  # local: cells imports this module

    st = ctx.student
    table = ctx.decoder.table
    bound = [math.inf]
    adapter1: Any
    add1: torch.Tensor | None = None
    pa: PositionAdapter | None = None
    if isinstance(arm, AdapterRouteArm):
        assert lsep_owner is not None
        t1, t2 = lsep_owner
        pa = PositionAdapter({t1: arm.arms[t1].adapter, t2: arm.arms[t2].adapter}, lambda i: t1 if i < bound[0] else t2)
        adapter1 = pa
        st.read_layer = None
    else:
        add1, adapter1 = arm.prepare([reads1], 1, len(ids1), CPU, None)
        st.read_layer = arm.layer
    g1, cache = st.greedy_cached(_tensor(ids1), add=add1, adapter=adapter1, max_new=ctx.max_new, stop_bytes=table)
    a1, hit1, extra1 = split_answer(ctx, g1)
    suffix, reads2 = suffix_fn(a1, hit1)
    cached_len = len(ids1) + len(a1) - (1 if hit1 and a1 else 0)
    ok = cached_len + len(suffix) + ctx.max_new <= st.cfg.max_positions
    if not ok:
        return ItemOut(g1, [], (hit1, False), (extra1, False), False)
    if pa is not None:
        bound[0] = len(ids1) + len(a1)
    if not full:
        if pa is not None:
            adapter2: Any = pa
            add2 = None
        else:
            add2, adapter2 = arm.prepare([reads2], 1, len(suffix), CPU, None)
        g2, _ = st.greedy_cached(_tensor(suffix), add=add2, adapter=adapter2, max_new=ctx.max_new, stop_bytes=table, cache=cache)
    else:
        rest = suffix[1 if hit1 and a1 else 0 :]
        full_ids = ids1 + a1 + rest
        if pa is not None:
            g2 = st.greedy(_tensor(full_ids), add=None, adapter=pa, max_new=ctx.max_new, stop_bytes=table, use_cache=False)
        else:
            reads_full = list(reads1) + [(cached_len + p, t, j) for p, t, j in reads2]
            addf, adapterf = arm.prepare([reads_full], 1, len(full_ids), CPU, None)
            g2 = st.greedy(_tensor(full_ids), add=addf, adapter=adapterf, max_new=ctx.max_new, stop_bytes=table, use_cache=False)
    _a2, hit2, extra2 = split_answer(ctx, g2)
    return ItemOut(g1, g2, (hit1, hit2), (extra1, extra2))


def c1_layout(ctx: EvalContext, cs: CombinedSet, pair: Pair) -> tuple[list[int], list[Any], Any]:
    """Step 1 input P_T1(s1), its reads, and the function giving the step-2 suffix and its reads (positions relative to the suffix) from a1 (section 4.1, 4.2)."""
    s1, s2 = cs.sentences[pair.i1], cs.sentences[pair.i2]
    ex1, ex2 = s1.ex[pair.t1], s2.ex[pair.t2]
    nl = list(ctx.newline_ids)
    body2 = list(ex2.prompt_ids)[_bos(ex2) :]
    src2 = reads_of(ex2, [pair.t2], ctx.marker_index)  # stored positions in P_T2(s2), BOS included

    def suffix_fn(a1: list[int], hit: bool) -> tuple[list[int], list[Any]]:
        pre = [a1[-1]] if hit and a1 else []
        base = len(pre) + len(nl) - _bos(ex2)
        return pre + nl + body2, [(p + base, t, j) for p, t, j in src2]

    return list(ex1.prompt_ids), reads_of(ex1, [pair.t1], ctx.marker_index), suffix_fn


def c2_layout(ctx: EvalContext, cs: CombinedSet, idx: int) -> tuple[list[int], list[Any], Any, int]:
    """Step 1 input P_A(s), its reads (the word reads of both tasks, summed; the marker of A only), the step-2 suffix function (the marker of B, read with its own code where it stands), and the length
    of M_A (section 5)."""
    s = cs.sentences[idx]
    exa, exb = s.ex["A"], s.ex["B"]
    nl = list(ctx.newline_ids)
    marker_b = list(exb.segments[-1].ids)
    reads1 = [*reads_of(exa, ["A"], ctx.marker_index), *[(p, "B", j) for p, j in exa.reads]]

    def suffix_fn(a1: list[int], hit: bool) -> tuple[list[int], list[Any]]:
        pre = [a1[-1]] if hit and a1 else []
        suffix = pre + nl + marker_b
        return suffix, [(len(suffix) - 1, "B", ctx.marker_index)]

    return list(exa.prompt_ids), reads1, suffix_fn, len(exa.segments[-1].ids)


def run_c1(ctx: EvalContext, arm: Arm, cs: CombinedSet, pair: Pair, *, full: bool = False) -> ItemOut:
    ids1, reads1, suffix_fn = c1_layout(ctx, cs, pair)
    return _two_step(ctx, arm, ids1, reads1, suffix_fn, full=full, lsep_owner=(pair.t1, pair.t2))


def run_c2(ctx: EvalContext, arm: Arm, cs: CombinedSet, idx: int, *, full: bool = False) -> ItemOut:
    from .cells import AdapterRouteArm

    ids1, reads1, suffix_fn, marker_a_len = c2_layout(ctx, cs, idx)
    if isinstance(arm, AdapterRouteArm):
        exb = cs.sentences[idx].ex["B"]
        return _lsep_c2(ctx, arm, ids1, marker_a_len, list(ctx.newline_ids), list(exb.segments[-1].ids))
    return _two_step(ctx, arm, ids1, reads1, suffix_fn, full=full)


def _lsep_c2(ctx: EvalContext, arm: Any, ids1: list[int], marker_a_len: int, nl: list[int], marker_b: list[int]) -> ItemOut:
    """L-sep on C2: a switch per answer. Step 1: A's adapter on the whole sequence. Step 2 is computed in full without the step-1 cache: B's adapter on [BOS] E S(s) NL, A's on M_A and a1 (as
    generated), B's on NL, M_B and a2."""
    st = ctx.student
    table = ctx.decoder.table
    st.read_layer = None
    g1, _ = st.greedy_cached(_tensor(ids1), add=None, adapter=arm.arms["A"].adapter, max_new=ctx.max_new, stop_bytes=table)
    a1, hit1, extra1 = split_answer(ctx, g1)
    full_ids = ids1 + a1 + nl + marker_b
    if len(full_ids) + ctx.max_new > st.cfg.max_positions:
        return ItemOut(g1, [], (hit1, False), (extra1, False), False)
    prefix = len(ids1) - marker_a_len
    end_a = len(ids1) + len(a1)
    pa = PositionAdapter({"A": arm.arms["A"].adapter, "B": arm.arms["B"].adapter}, lambda i: "A" if prefix <= i < end_a else "B")
    g2, _ = st.greedy_cached(_tensor(full_ids), add=None, adapter=pa, max_new=ctx.max_new, stop_bytes=table)
    _a2, hit2, extra2 = split_answer(ctx, g2)
    return ItemOut(g1, g2, (hit1, hit2), (extra1, extra2))


def single_ids(ctx: EvalContext, arm: Arm, cs: CombinedSet, idx: int, lang: str) -> list[int]:
    """The single-task answer of E_C sentence ``idx`` in ``lang``: generated from P_lang(x) under route lang."""
    ex = cs.sentences[idx].ex[lang]
    return generate(ctx, arm, ex, [lang])


# --- scoring one arm-cell -------------------------------------------------------------------------------------------------------------------------
def _score(ctx: EvalContext, ids: Sequence[int], refs: Sequence[str]) -> tuple[float, bool]:
    text = ctx.decoder.answer_text(ids)
    return chrf_item(text, refs), normalize(text) in {normalize(r) for r in refs}


def _kind_record(ctx: EvalContext, cs: CombinedSet, kind: str, outs: Sequence[ItemOut], langs: Sequence[tuple[str, str]], sent_idx: Sequence[tuple[int, int]]) -> dict[str, Any]:
    tested_scores: dict[str, list[float]] = {"A": [], "B": []}
    items: list[dict[str, Any]] = []
    first: dict[str, list[float]] = {"A": [], "B": []}
    second: dict[str, list[float]] = {"A": [], "B": []}
    tested: dict[str, list[int]] = {"A": [], "B": []}
    single_ref: list[float] = []
    for j, (o, (l1, l2), (i1, i2)) in enumerate(zip(outs, langs, sent_idx, strict=True)):
        r1, r2 = cs.sentences[i1].refs[l1], cs.sentences[i2].refs[l2]
        if o.length_ok:
            x1, p1 = _score(ctx, o.g1, r1)
            x2, p2 = _score(ctx, o.g2, r2)
        else:
            x1 = x2 = float("nan")
            p1 = p2 = False
        items.append({"j": j, "i": [i1, i2], "langs": [l1, l2], "scores": [x1, x2], "ids": [o.g1, o.g2], "hit_limit": list(o.hit), "stop_extra_bytes": list(o.extra), "length_ok": o.length_ok, "pass": bool(p1 and p2)})
        first[l1].append(x1)
        second[l2].append(x2)
        tested[l2].append(i2)
        tested_scores[l2].append(x2)
        if kind == "C2":  # C2 tests both answers on every item; in C1 the first answer is the single-task answer by construction and tests nothing
            tested[l1].append(i1)
            tested_scores[l1].append(x1)
        if len(r1) == 1 and len(r2) == 1:
            single_ref.append((x1 + x2) / 2)
    item_scores = [(it["scores"][0] + it["scores"][1]) / 2 for it in items]
    return {
        "kind": kind, "n": len(items), "items": items, "mean": mean(item_scores), "pass_rate": mean([float(it["pass"]) for it in items]), "item_scores": item_scores,
        "first_by_language": {a: mean(v) if v else None for a, v in first.items()}, "second_by_language": {a: mean(v) if v else None for a, v in second.items()},
        "tested_sentences": tested, "tested_by_language": {a: mean(v) if v else None for a, v in tested_scores.items()}, "single_reference_mean": mean(single_ref) if single_ref else None, "single_reference_items": len(single_ref),
        "hit_limit": {"first": sum(it["hit_limit"][0] for it in items), "second": sum(it["hit_limit"][1] for it in items)}, "stop_extra_bytes": {"first": sum(it["stop_extra_bytes"][0] for it in items), "second": sum(it["stop_extra_bytes"][1] for it in items)},
        "length_not_ok": sum(not it["length_ok"] for it in items),
    }  # fmt: skip


def score_combined_cell(ctx: EvalContext, arm: Arm, cs: CombinedSet) -> dict[str, Any]:
    """C1, C2 and the single-task answers of one arm-cell on the combined set. The first answer of a C1 item is the single-task answer of its sentence (recorded once, not generated twice);
    the other single-task answers are generated in a separate single-answer scoring (n answers)."""
    n = len(cs.sentences)
    single: dict[tuple[int, str], list[int]] = {}
    c1_outs = []
    for p in cs.pairs:
        o = run_c1(ctx, arm, cs, p)
        c1_outs.append(o)
        single[(p.i1, p.t1)] = o.g1
    separate = 0
    for i in range(n):
        for lang in core.TASKS:
            if (i, lang) not in single:
                single[(i, lang)] = single_ids(ctx, arm, cs, i, lang)
                separate += 1
    c2_outs = [run_c2(ctx, arm, cs, i) for i in range(n)]
    single_scores = {lang: [_score(ctx, single[(i, lang)], cs.sentences[i].refs[lang])[0] for i in range(n)] for lang in core.TASKS}
    return {
        "n": n, "pairs_sha256": pairs_digest(cs.pairs), "routes": "oracle", "arm": arm.kind,
        "C1": _kind_record(ctx, cs, "C1", c1_outs, [(p.t1, p.t2) for p in cs.pairs], [(p.i1, p.i2) for p in cs.pairs]),
        "C2": _kind_record(ctx, cs, "C2", c2_outs, [("A", "B")] * n, [(i, i) for i in range(n)]),
        "single": {"scores": single_scores, "sequences": {lang: [single[(i, lang)] for i in range(n)] for lang in core.TASKS}, "separate_answers": separate},
    }  # fmt: skip


def check_continuation(ctx: EvalContext, arm: Arm, cs: CombinedSet, count: int) -> dict[str, Any]:
    """Cache continuation against full recomputation of the step-2 input, identical tokens, for the first ``count`` C1 items and C2 sentences (section 11 items 3 and 9). A difference is a G4-class
    defect."""
    bad: list[str] = []
    for p in cs.pairs[:count]:
        a, b = run_c1(ctx, arm, cs, p), run_c1(ctx, arm, cs, p, full=True)
        if (a.g1, a.g2) != (b.g1, b.g2):
            bad.append(f"C1 item {p.j}")
    for i in range(min(count, len(cs.sentences))):
        a, b = run_c2(ctx, arm, cs, i), run_c2(ctx, arm, cs, i, full=True)
        if (a.g1, a.g2) != (b.g1, b.g2):
            bad.append(f"C2 item {i}")
    return {"ok": not bad, "differences": bad, "items": min(count, len(cs.pairs))}


# --- the ensemble and the teachers (stored outputs; no context reaches a teacher) ------------------------------------------------------------------------
def ensemble_record(cs: CombinedSet, teacher_text: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """Each answer is the stored output of the teacher of its language on its sentence: inside C1 and C2 it equals the single-task answer by construction. ``teacher_text[lang][i]`` is the stored
    output of the teacher of ``lang`` on E_C sentence i."""
    n = len(cs.sentences)
    single = {lang: [chrf_item(teacher_text[lang][i], cs.sentences[i].refs[lang]) for i in range(n)] for lang in core.TASKS}

    def kind(name: str, langs: Sequence[tuple[str, str]], idx: Sequence[tuple[int, int]]) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        tested: dict[str, list[int]] = {"A": [], "B": []}
        second: dict[str, list[float]] = {"A": [], "B": []}
        tested_scores: dict[str, list[float]] = {"A": [], "B": []}
        for j, ((l1, l2), (i1, i2)) in enumerate(zip(langs, idx, strict=True)):
            x1, x2 = single[l1][i1], single[l2][i2]
            items.append({"j": j, "i": [i1, i2], "langs": [l1, l2], "scores": [x1, x2]})
            second[l2].append(x2)
            tested[l2].append(i2)
            tested_scores[l2].append(x2)
            if name == "C2":
                tested[l1].append(i1)
                tested_scores[l1].append(x1)
        return {"kind": name, "tested_by_language": {a: mean(v) if v else None for a, v in tested_scores.items()}, "n": n, "items": items, "mean": mean([float(it["scores"][0] + it["scores"][1]) / 2 for it in items]), "second_by_language": {a: mean(v) if v else None for a, v in second.items()}, "tested_sentences": tested}

    return {"n": n, "pairs_sha256": pairs_digest(cs.pairs), "arm": "ensemble", "C1": kind("C1", [(p.t1, p.t2) for p in cs.pairs], [(p.i1, p.i2) for p in cs.pairs]), "C2": kind("C2", [("A", "B")] * n, [(i, i) for i in range(n)]), "single": {"scores": single}}


def tested_mean(rec: Mapping[str, Any], kind: str, lang: str) -> float | None:
    """s_a(X, K): the mean over the items in which the language is tested (C2: all items; C1: the items where it is the second answer)."""
    v = rec[kind]["tested_by_language"].get(lang)
    return None if v is None else float(v)


def single_mean_on(rec: Mapping[str, Any], kind: str, lang: str) -> float | None:
    """s_a(X, single) on the same sentences: the single-task scores of the sentences the answer is tested on."""
    idx = rec[kind]["tested_sentences"][lang]
    vals = [float(rec["single"]["scores"][lang][i]) for i in idx]
    return mean(vals) if vals else None
