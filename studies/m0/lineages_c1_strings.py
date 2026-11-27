# ruff: noqa: E501
"""C1 batch 1, family "strings" (existing family): scans over a string literal.

Strict procedures: ``run_length_scan`` run-length encoding of a string (compare each character with the run being built);
``mirror_pointers`` two pointers walking inward from both ends of a string, comparing the pair they stand on.
"""

from __future__ import annotations

import random

from studies.m0.core import Built, Retry
from studies.m0.lineages_c1_common import IDX, LETTERS, B, C, N, S, V, batch, finish, names


@batch("strings")
def run_length_scan(level: int, r: random.Random) -> Built:
    """Run-length scan: cur = s[0], n = 1; for each next character: same as cur -> n += 1, else close the run (append cur + str(n) to the
    output) and restart; the last run is closed after the loop. Shapes: the encoded string (every run), the encoded string keeping only runs
    of length 2 or more (a draw with nothing kept is redrawn), only the run lengths written one after another. The string has 3 + level runs of length 1
    to 3 + level // 2 over three letters, adjacent runs differing."""
    s, out, cur, n, i = names(r, 5)
    letters = r.sample(LETTERS, 3)
    runs: list[tuple[str, int]] = []
    for _ in range(3 + level):
        ch = r.choice([c for c in letters if not runs or c != runs[-1][0]])
        runs.append((ch, r.randint(1, 3 + level // 2)))
    text = "".join(c * k for c, k in runs)
    shape = r.choice(("enc", "long", "counts"))
    if shape == "long" and not any(k >= 2 for _, k in runs):
        raise Retry
    emit: list[list] = [["set", out, B("+", V(out), ["call", "str", V(n)])] if shape == "counts" else ["set", out, B("+", B("+", V(out), V(cur)), ["call", "str", V(n)])]]
    close: list[list] = [["if", C(">=", V(n), N(2)), emit, []]] if shape == "long" else emit
    prog: list[list] = [["set", s, S(text)], ["set", out, S("")], ["set", cur, IDX(V(s), N(0))], ["set", n, N(1)]]
    prog.append(["for", i, N(1), ["call", "len", V(s)], 1, [["if", C("==", IDX(V(s), V(i)), V(cur)), [["aug", n, "+", N(1)]], [*close, ["set", cur, IDX(V(s), V(i))], ["set", n, N(1)]]]]])
    prog += close
    prog.append(["print", V(out)])
    return finish(prog)


@batch("strings")
def mirror_pointers(level: int, r: random.Random) -> Built:
    """Two pointers: i = 0, j = len(s) - 1; while i < j compare s[i] with s[j], then i += 1 and j -= 1. Shapes: the left characters of the
    unequal pairs in order, the sum of the left indices of the unequal pairs, both characters of every unequal pair in order (a draw with no
    unequal pair is redrawn). The string has 4 + 2 * level characters over three letters and is a palindrome with each pair broken at random,
    so the answer is not 'is it a palindrome'."""
    s, i, j, tot, out = names(r, 5)
    n = 4 + 2 * level
    letters = r.sample(LETTERS, 3)
    half = [r.choice(letters) for _ in range((n + 1) // 2)]
    p_break = r.choice((0.25, 0.4, 0.55))
    left = half[:]
    right = [c if r.random() > p_break else r.choice(letters) for c in half]
    mid = [left[-1]] if n % 2 else []
    text = "".join(left[: n // 2]) + "".join(mid) + "".join(reversed(right[: n // 2]))
    if all(text[k] == text[n - 1 - k] for k in range(n // 2)):
        raise Retry
    shape = r.choice(("chars", "poss", "pairs"))
    then: list[list]
    if shape == "chars":
        then = [["set", out, B("+", V(out), IDX(V(s), V(i)))]]
    elif shape == "pairs":
        then = [["set", out, B("+", B("+", V(out), IDX(V(s), V(i))), IDX(V(s), V(j)))]]
    else:
        then = [["aug", tot, "+", V(i)]]
    prog: list[list] = [["set", s, S(text)], ["set", i, N(0)], ["set", j, B("-", ["call", "len", V(s)], N(1))]]
    prog.append(["set", tot, N(0)] if shape == "poss" else ["set", out, S("")])
    prog.append(["while", C("<", V(i), V(j)), [["if", C("!=", IDX(V(s), V(i)), IDX(V(s), V(j))), then, []], ["aug", i, "+", N(1)], ["aug", j, "-", N(1)]]])
    prog.append(["print", V(tot) if shape == "poss" else V(out)])
    return finish(prog)
