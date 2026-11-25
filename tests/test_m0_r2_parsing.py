# ruff: noqa: E501
"""R2 batch 1, family parsing: mechanical checks and test-local cross-checks (not the registered second solvers)."""

from __future__ import annotations

from studies.m0.core import ALL_LEVELS, build_item, stream
from studies.m0.lineages_r2_common import check_family_r2, load_batch1

LIN = {x.id: x for x in load_batch1()}


def items(lid: str, per: int = 40):  # type: ignore[no-untyped-def]
    for lv in ALL_LEVELS:
        r = stream(953804, "t", lid, str(lv))
        for i in range(per):
            yield build_item(LIN[lid], lv, r, "A", f"t/{lv}/{i}")


def test_family_checks() -> None:
    assert check_family_r2("parsing") == []


def test_brackets_by_repeated_reduction() -> None:
    for it in items("R2.bracket_match", 20):
        s = it.structured["s"]
        if it.structured["ask"] == "valid":
            t = s
            while True:
                u = t.replace("()", "").replace("[]", "").replace("{}", "")
                if u == t:
                    break
                t = u
            assert it.answer == ("yes" if t == "" else "no")
        else:
            p = it.structured["p"] - 1
            depth = 0
            for i in range(p, len(s)):
                depth += 1 if s[i] in "([{" else -1
                if depth == 0:
                    assert it.answer == str(i + 1)
                    break


def test_expression_ranked_equals_python_and_left_to_right_by_folding() -> None:
    for it in items("R2.expression_eval", 25):
        text, conv = it.structured["text"], it.structured["convention"]
        if conv == "ranked":
            assert it.answer == str(eval(text))  # noqa: S307 (our own digits, + - * and parentheses)
        else:
            # left to right: replace each parenthesised group (innermost first) by its value, then fold
            def fold(t: str) -> int:
                toks = t.split()
                v = int(toks[0])
                for i in range(1, len(toks), 2):
                    w = int(toks[i + 1])
                    v = v + w if toks[i] == "+" else v - w if toks[i] == "-" else v * w
                return v

            t = text
            while "(" in t:
                i = t.rindex("(")
                j = t.index(")", i)
                t = t[:i] + str(fold(t[i + 1 : j])) + t[j + 1 :]
            assert it.answer == str(fold(t))
