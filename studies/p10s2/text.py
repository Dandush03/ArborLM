# ruff: noqa: E501
"""Text, chrF-norm, gap closed and intervals (ADR-0022 sections 5.2, 10.1).

chrF-norm is implemented here exactly as section 10.1 specifies, because ``sacrebleu`` is not in ``uv.lock``: chrF2 on normalized strings, character n-grams n = 1..6, no word
n-grams, whitespace removed before n-gram extraction, precision and recall averaged over the *effective* orders (orders at which both hypothesis and reference have at least one
n-gram), then F with beta = 2 (as sacrebleu 2.5.1's default, ``eps_smoothing=False``); an item with no effective order scores 0; scale 0-1; the item score is the maximum over
references; the panel score is the mean over items. The cross-check against ``sacrebleu`` is made in the data-generation step (``datagen``), where the package is available.
"""

import math
import unicodedata
from collections import Counter
from collections.abc import Sequence

import torch

from . import core

# Fixed contraction list of section 5.2 (applied to the lower-cased raw text before punctuation is stripped).
CONTRACTIONS = {
    "don't": "do not", "doesn't": "does not", "didn't": "did not", "can't": "cannot", "won't": "will not", "isn't": "is not", "aren't": "are not", "wasn't": "was not",
    "weren't": "were not", "haven't": "have not", "hasn't": "has not", "hadn't": "had not", "wouldn't": "would not", "couldn't": "could not", "shouldn't": "should not",
    "i'm": "i am", "you're": "you are", "he's": "he is", "she's": "she is", "it's": "it is", "we're": "we are", "they're": "they are", "i've": "i have", "you've": "you have",
    "we've": "we have", "they've": "they have", "i'll": "i will", "you'll": "you will", "he'll": "he will", "she'll": "she will", "we'll": "we will", "they'll": "they will",
    "i'd": "i would", "you'd": "you would", "he'd": "he would", "she'd": "she would", "we'd": "we would", "they'd": "they would", "that's": "that is", "there's": "there is",
    "what's": "what is", "let's": "let us", "who's": "who is", "where's": "where is",
}  # fmt: skip


def normalize(text: str) -> str:
    """Unicode NFC, lower case, punctuation (category P*) stripped, whitespace collapsed (section 5.2)."""
    t = unicodedata.normalize("NFC", text).lower()
    t = "".join(c for c in t if not unicodedata.category(c).startswith("P"))
    return " ".join(t.split())


def _is_punctuation(c: str) -> bool:
    return unicodedata.category(c).startswith("P")


def _expand_token(w: str) -> str:
    """One whitespace-delimited token: the punctuation attached to its ends (everything of category P* except the apostrophe) is set aside, the core is looked up in the contraction list
    (if the core is wrapped in apostrophes, as in a single-quoted word, those are set aside too) and the punctuation is put back. So "can't." expands like "can't" (audit A-M2)."""
    a = 0
    while a < len(w) and _is_punctuation(w[a]) and w[a] != "'":
        a += 1
    b = len(w)
    while b > a and _is_punctuation(w[b - 1]) and w[b - 1] != "'":
        b -= 1
    head, core_, tail = w[:a], w[a:b], w[b:]
    if core_ in CONTRACTIONS:
        return head + CONTRACTIONS[core_] + tail
    c, d = 0, len(core_)
    while c < d and core_[c] == "'":
        c += 1
    while d > c and core_[d - 1] == "'":
        d -= 1
    inner = core_[c:d]
    if (c or d < len(core_)) and inner in CONTRACTIONS:
        return head + core_[:c] + CONTRACTIONS[inner] + core_[d:] + tail
    return w


def expand_contractions(text: str) -> str:
    """The raw text, lower-cased, with the fixed contraction list expanded (the apostrophe may be straight or curly); punctuation attached to a word does not hide its contraction."""
    t = unicodedata.normalize("NFC", text).lower().replace("’", "'")
    return " ".join(_expand_token(w) for w in t.split())


def words(text: str) -> list[str]:
    return normalize(text).split()


# --- chrF-norm ----------------------------------------------------------------------------------------------------------------------------------
def _ngrams(s: str, n: int) -> Counter[str]:
    return Counter(s[i : i + n] for i in range(len(s) - n + 1))


def chrf_pair(hyp: str, ref: str, max_order: int | None = None, beta: float | None = None) -> float:
    """chrF-norm of one hypothesis against one reference (both normalized here)."""
    order = max_order if max_order is not None else core.CFG["scoring"]["chrf_max_order"]
    b = beta if beta is not None else core.CFG["scoring"]["chrf_beta"]
    h, r = "".join(normalize(hyp).split()), "".join(normalize(ref).split())
    sum_p = sum_r = 0.0
    effective = 0
    for n in range(1, order + 1):
        gh, gr = _ngrams(h, n), _ngrams(r, n)
        nh, nr = sum(gh.values()), sum(gr.values())
        if nh > 0 and nr > 0:
            match = sum((gh & gr).values())
            sum_p += match / nh
            sum_r += match / nr
            effective += 1
    if effective == 0:
        return 0.0
    p, rec = sum_p / effective, sum_r / effective
    factor = b * b
    denom = factor * p + rec
    return (1 + factor) * p * rec / denom if p + rec > 0 and denom > 0 else 0.0


def chrf_item(hyp: str, refs: Sequence[str]) -> float:
    """The item score: the maximum over references (an item with no reference scores 0)."""
    return max((chrf_pair(hyp, r) for r in refs), default=0.0)


def mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else math.nan


def panel_chrf(hyps: Sequence[str], refs: Sequence[Sequence[str]]) -> tuple[float, list[float]]:
    items = [chrf_item(h, r) for h, r in zip(hyps, refs, strict=True)]
    return mean(items), items


# --- gap closed -----------------------------------------------------------------------------------------------------------------------------------
def gap_closed(arm: float, stage0: float, teacher: float) -> float | None:
    """G = (s(arm) - s(Stage 0)) / (s(teacher) - s(Stage 0)) on the same panel; ``None`` (NOT_EVALUATED) if the denominator is below 0.30 or any input is not finite."""
    if not all(math.isfinite(x) for x in (arm, stage0, teacher)):
        return None
    denom = teacher - stage0
    if denom < core.GAP_MIN:
        return None
    return (arm - stage0) / denom


# --- intervals -----------------------------------------------------------------------------------------------------------------------------------
def wilson(successes: int, n: int, z: float | None = None) -> tuple[float, float]:
    """Wilson score interval (lower, upper); (0, 1) for n = 0."""
    if n <= 0:
        return 0.0, 1.0
    zz = z if z is not None else core.CFG["filter"]["wilson_z"]
    p = successes / n
    denom = 1 + zz * zz / n
    centre = (p + zz * zz / (2 * n)) / denom
    half = zz * math.sqrt(p * (1 - p) / n + zz * zz / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def bootstrap_interval(values: Sequence[float], generator: torch.Generator, resamples: int | None = None, level: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap interval of the mean over items. Descriptive; enters no rule. ``generator`` is the bootstrap generator (seed 220906)."""
    n = len(values)
    if n == 0:
        return math.nan, math.nan
    m = resamples if resamples is not None else core.CFG["scoring"]["bootstrap_resamples"]
    x = torch.tensor(list(values), dtype=torch.float64)
    means: list[float] = []
    done = 0
    while done < m:
        chunk = min(1000, m - done)
        idx = torch.randint(0, n, (chunk, n), generator=generator)
        means.extend(x[idx].mean(dim=1).tolist())
        done += chunk
    means.sort()
    lo = means[int((1 - level) / 2 * (m - 1))]
    hi = means[int((1 + level) / 2 * (m - 1))]
    return lo, hi
