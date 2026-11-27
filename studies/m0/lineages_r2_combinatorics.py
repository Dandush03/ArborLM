# ruff: noqa: E501
"""R2 batch 1, family "combinatorics": position of an arrangement in dictionary order (factorial-base ranking and unranking)."""

from __future__ import annotations

import math
import random
import string

from studies.m0.core import Built
from studies.m0.lineages_r2_common import batch1


def unrank(letters: list[str], k: int) -> str:
    """k is 1-based; letters sorted."""
    pool = sorted(letters)
    k -= 1
    out = []
    for i in range(len(pool), 0, -1):
        f = math.factorial(i - 1)
        out.append(pool.pop(k // f))
        k %= f
    return "".join(out)


def rank(word: str) -> int:
    pool = sorted(word)
    k = 0
    for i, ch in enumerate(word):
        j = pool.index(ch)
        k += j * math.factorial(len(word) - 1 - i)
        pool.pop(j)
    return k + 1


@batch1("combinatorics")
def dictionary_rank(level: int, r: random.Random) -> Built:
    """Procedure: factorial-base ranking/unranking of arrangements of distinct letters in dictionary order. structured: {"letters": [str] (sorted), "ask": "word" | "position", "k": int or null, "word": str or null}.
    The arrangements of the n letters (each used once) are listed in dictionary order, numbered from 1. Answer, word: the arrangement at position k. Answer, position: the number of the arrangement `word`."""
    n = (4, 4, 5, 5, 6, 6, 7)[level]
    letters = sorted(r.sample(string.ascii_lowercase, n))
    total = math.factorial(n)
    if r.random() < 0.6:
        k = r.randint(2, total - 1)
        w = unrank(letters, k)
        q = (f"Write every arrangement of the letters {', '.join(letters)} (each used exactly once in each arrangement) as a word, and list all the words in dictionary order (as in a dictionary, comparing letter by letter from the left, with a before b before c and so on). "
             f"Number the words 1, 2, 3, ... in that list. Which word has number {k}?")
        return Built(q, {"letters": letters, "ask": "word", "k": k, "word": None}, w, "text", None)
    w = "".join(r.sample(letters, n))
    k = rank(w)
    if k in (1, total):
        w = "".join(r.sample(letters, n))
        k = rank(w)
    q = (f"Write every arrangement of the letters {', '.join(letters)} (each used exactly once in each arrangement) as a word, and list all the words in dictionary order (as in a dictionary, comparing letter by letter from the left, with a before b before c and so on). "
         f"Number the words 1, 2, 3, ... in that list. What is the number of the word {w}?")
    return Built(q, {"letters": letters, "ask": "position", "k": None, "word": w}, str(k), "number", None)
