# ruff: noqa: E501
"""M1 fix round 3, shared pieces (audit AUDIT3_M1, lead rulings 2 and 3).

NEW revisions with ids ``M1.<stem>_r3`` in their OWN registry (``FIX3``), never ``core.REGISTRY``. Rules for every builder here:
  * R-1/R-13: nothing is redrawn conditional on a heuristic or on the answer. A builder never raises ``Retry``. Loops (``until``) are on VALIDITY only
    (a size cap, distinct values, pairwise coprime moduli, a unique answer). Where a validity loop could itself create a tell (the audit's mixture case) the
    parameters are built so the answer is valid by construction instead.
  * R-4: the answer format and every convention (units, rounding, inclusive or exclusive, sign, whether a leading zero is allowed) are stated in the item.
  * R-5/R-10/R-11: capacity is counted on structure (names, setting sentence and the order of commutative parts are not distinct; every numeric value is).
Not a registration: nothing here enters ``core.REGISTRY``; no model was run.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from fractions import Fraction
from typing import Any

from studies.m0.core import Built, Lineage

FIX3: list[Lineage] = []
STEM_OF: dict[str, str] = {}  # r3 id -> stem (the batch-1 / existing lineage it revises, without prefix and suffix)
FAMILY_OF: dict[str, str] = {}

WHOLE = "Answer with a whole number."
WHOLE_SIGNED = "Answer with a whole number (write a minus sign if it is negative)."
DECIMAL = "Answer with a number; if it is not whole, write it as a decimal with no more than two decimal places and no trailing zeros."

Builder = Callable[[int, random.Random], Built]


def r3(stem: str, family: str) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"M1.{stem}_r3"
        if any(x.id == lid for x in FIX3):
            raise ValueError(f"duplicate lineage id {lid}")
        FIX3.append(Lineage(lid, "M1", family, fn))
        STEM_OF[lid] = stem
        FAMILY_OF[lid] = family
        return fn

    return deco


def until(fn: Callable[[], Any], tries: int = 20000) -> Any:
    """Loop on VALIDITY only (``fn`` returns None for an invalid draw). Never conditional on a heuristic or on the answer."""
    for _ in range(tries):
        out = fn()
        if out is not None:
            return out
    raise RuntimeError("no valid draw")


def fmt_exact(v: Fraction) -> str:
    """Canonical text of a value that is exactly a number of cents; the builders construct their parameters so that this always holds (an AssertionError is a bug, not a retry)."""
    c = v * 100
    assert c.denominator == 1, v
    n = c.numerator
    sign = "-" if n < 0 else ""
    whole, cents = divmod(abs(n), 100)
    return f"{sign}{whole}" if cents == 0 else f"{sign}{whole}.{cents:02d}".rstrip("0")


def money(cents: int) -> str:
    return f"${cents // 100}.{cents % 100:02d}"


def pl(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def and_(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def ctx(r: random.Random) -> str:
    """One setting sentence (name, town, one of four wordings): surface frame only, NOT structural variety (not counted by the capacity key)."""
    from studies.m0.vocab import NAMES, TOWNS

    n, t = r.choice(NAMES), r.choice(TOWNS)
    return r.choice((f"{n} from {t} found this problem in a puzzle book.", f"This problem comes from a quiz held in {t}, set by {n}.", f"{n} of {t} wrote this problem for a maths club.", f"At a maths club in {t}, {n} is asked this."))


def adding(m: int) -> str:
    return f"adding {m}" if m >= 0 else f"subtracting {-m}"
