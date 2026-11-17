# ruff: noqa: E501
"""Retrieval baselines and the ensemble (ADR-0022 section 7). None is trained.

* R-exact: a table from training source to accepted output; zero hits on held-out items confirms the panels are held out.
* R-nn: the nearest training source by character-trigram TF-IDF cosine; return its output.
* R-icl: the 4 nearest accepted pairs in the frozen student's prompt (their longer prompt is a cost, reported).
* R-gloss: a co-occurrence lexicon (Dice) from accepted pairs; word-by-word output.
* Ensemble: the two teachers behind the oracle route, and behind the learned router.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .data import Item, TrainItem
from .text import chrf_item, mean, normalize


def _trigrams(s: str) -> Counter[str]:
    t = f"  {normalize(s)}  "
    return Counter(t[i : i + 3] for i in range(len(t) - 2))


class TfidfIndex:
    def __init__(self, train: Sequence[TrainItem]) -> None:
        self.train = list(train)
        grams = [_trigrams(x.en) for x in self.train]
        df: Counter[str] = Counter()
        for g in grams:
            df.update(g.keys())
        n = max(1, len(grams))
        self.idf = {k: math.log((1 + n) / (1 + v)) + 1.0 for k, v in df.items()}
        self.vecs = [self._vec(g) for g in grams]

    def _vec(self, g: Counter[str]) -> dict[str, float]:
        v = {k: c * self.idf.get(k, 1.0) for k, c in g.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {k: x / norm for k, x in v.items()}

    def nearest(self, source: str, k: int = 1) -> list[int]:
        q = self._vec(_trigrams(source))
        sims = [(-sum(w * v.get(t, 0.0) for t, w in q.items()), i) for i, v in enumerate(self.vecs)]
        return [i for _, i in sorted(sims)[:k]]


def r_exact(train: Sequence[TrainItem], panel: Sequence[Item], capability: str) -> dict[str, Any]:
    table = {normalize(x.en): x.target for x in train}
    hits = [normalize(i.en) in table for i in panel]
    outs = [table.get(normalize(i.en), "") for i in panel]
    scores = [chrf_item(o, i.refs[capability]) for o, i in zip(outs, panel, strict=True)]
    return {"hits": sum(hits), "n": len(panel), "mean": mean(scores), "items": scores}


def r_nn(train: Sequence[TrainItem], panel: Sequence[Item], capability: str, index: TfidfIndex | None = None) -> dict[str, Any]:
    idx = index or TfidfIndex(train)
    outs = [train[idx.nearest(i.en)[0]].target for i in panel]
    scores = [chrf_item(o, i.refs[capability]) for o, i in zip(outs, panel, strict=True)]
    return {"mean": mean(scores), "items": scores, "comparisons_per_item": len(train)}


def gloss_lexicon(train: Sequence[TrainItem]) -> dict[str, str]:
    """For each source word the target word with the highest Dice coefficient over the accepted pairs (ties to the lexicographically smaller word)."""
    cs: Counter[str] = Counter()
    ct: Counter[str] = Counter()
    co: dict[str, Counter[str]] = defaultdict(Counter)
    for x in train:
        sw, tw = set(normalize(x.en).split()), set(normalize(x.target).split())
        cs.update(sw)
        ct.update(tw)
        for a in sw:
            co[a].update(tw)
    lex: dict[str, str] = {}
    for a, row in co.items():
        lex[a] = min(row, key=lambda b: (-2 * row[b] / (cs[a] + ct[b]), b))
    return lex


def r_gloss(train: Sequence[TrainItem], panel: Sequence[Item], capability: str) -> dict[str, Any]:
    lex = gloss_lexicon(train)
    outs = [" ".join(lex.get(w, w) for w in normalize(i.en).split()) for i in panel]
    scores = [chrf_item(o, i.refs[capability]) for o, i in zip(outs, panel, strict=True)]
    return {"mean": mean(scores), "items": scores}


def r_icl_prompt_items(train: Sequence[TrainItem], query: str, k: int = 4, index: TfidfIndex | None = None) -> list[TrainItem]:
    """The k nearest accepted pairs to put before the query in the frozen student's prompt, nearest last (so the closest demonstration sits next to the query)."""
    idx = index or TfidfIndex(train)
    return [train[i] for i in reversed(idx.nearest(query, k))]


def ensemble_scores(teacher_output: Mapping[str, Sequence[str]], refs: Mapping[str, Sequence[Sequence[str]]], route: Callable[[str, int], str]) -> dict[str, float]:
    """The two teachers behind a route: ``route(capability, i)`` returns the capability whose teacher answers item i of that capability's panel ("A", "B" or "none" for no answer). Under the oracle
    route every item goes to its own capability's teacher, so the score equals that teacher's own (a mismatch is ENGINEERING-FAILURE); under a learned route a wrongly routed item scores 0."""
    out: dict[str, float] = {}
    for c in ("A", "B"):
        scores = []
        for i, r in enumerate(refs[c]):
            who = route(c, i)
            text = teacher_output[who][i] if who in ("A", "B") and who == c else ""
            scores.append(chrf_item(text, r))
        out[c] = mean(scores)
    return out
