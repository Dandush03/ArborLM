# ruff: noqa: E501
"""C1, fix round 3 (the C1 lineage set after the third audit, ``audit3_c1/AUDIT3_C1.md``; lead rulings 2 and 3: R-1/R-13 no redraw conditional on a
heuristic, R-8 the procedure is the program's algorithm, R-12 NOT REGISTERED means excluded, R-14 the traced-state shapes the audit rejected are not reused).

NEW file; nothing existing is edited. Lineages here live in their own registry ``FIX3`` (nothing goes into ``core.REGISTRY``); ids are ``C1.<function name>``
and the function names end in ``_f3``. ``SUPERSEDES3`` names what each one replaces; ``VARIANT`` marks the lineages whose PROGRAM differs from the algorithm the
superseded lineage traced (see below); ``NOT_REGISTERED`` lists what is excluded, with the reason.

Rules followed in every builder of the ``lineages_c1_fix3_*`` modules:
  * a tell is removed BY CONSTRUCTION (the generator's structure, not a redraw conditioned on a heuristic's outcome); ``Retry`` is raised only for a
    validity condition (a program that cannot run, an answer the scorer would normalise, two equal endpoints);
  * every identifier of a program comes out of ``names`` (one ``sample`` per item), so a fixed name cannot collide with a drawn one;
  * the program prints exactly one line, uses only node kinds the second solver ``solvers_c1.c1_trace`` supports, and terminates fast (bounded loops).

On the formula-answerable shapes (audit section 3): a question is kept only if its answer cannot be had from a closed form or a library call that skips the
program's own loop-carried state. For two algorithms no such question exists with the program unchanged (every state of insertion sort is a function of the
sorted prefix, every state of the running maximum a prefix maximum; for Kadane's scan every state is a max-suffix or max-subarray value, and the two variants tried (a restart threshold above or below zero) kept the Formula in 0.3-0.85 of items; for square-and-multiply
every state is a ``pow``). ``insertion_sort``, ``minmax_track`` and ``kadane_scan`` are NOT REGISTERED. ``fast_power_f3`` and ``counter_list_f3`` are VARIANTS: the control
skeleton is that of the superseded algorithm but one update rule is changed (a state-machine bucket in the tally; an added term in the squaring) so that the loop-carried state has
no closed form. Whether a variant is still 'the same algorithm' is a scientific question left to the lead (PENDING LEAD REVIEW); the unmodified programs are listed
as NOT REGISTERED.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from studies.m0.core import Built, Lineage

FIX3: list[Lineage] = []
SUPERSEDES3: dict[str, str] = {}
VARIANT: dict[str, str] = {}
FAMILY_OF: dict[str, str] = {}
Builder = Callable[[int, random.Random], Built]

NOT_REGISTERED: dict[str, str] = {
    "C1.insertion_sort": "every state of insertion sort (the list after any number of rounds, a hole index, the number of shifts) is a function of sorted(prefix) and rank counts (audit section 3: list, at, shifts, hole, holesum all 100 % formula); no question about the unchanged program forces tracing",
    "C1.insertion_sort_traced": "closed form: hole = number of earlier elements that do not satisfy the test, minus one; holesum is the sum of those ranks (audit section 3; ruling R-14)",
    "C1.minmax_track": "every shape (the maximum or minimum, its first index, their sum) is max/min/index of the list (audit section 3); the running state of a one-pass extreme scan has no non-formula quantity",
    "C1.kadane_scan": "every state of Kadane's scan is a max-suffix or max-subarray value (audit section 3: best, cur, curs all 100 %; kadane_scan_traced[cur_at] is the max suffix of a prefix, ruling R-14). Two variants were tried and measured (battery runs bat_r1, bat_r2, kept in the scratch directory): restart when cur < thr with thr 3 to 12 (cur equal to the LAST element in 0.43-0.70 of items, best equal to the largest element in 0.38-0.67, the Kadane formulas 0.3-0.5) and restart only when cur < -thr with thr 1 to 4 (the max-suffix formula for cur 0.76-0.85, for the sum of cur 0.50-0.70). Neither tell could be removed by construction, so the lineage is NOT REGISTERED (no variant is in this round's code)",
    "C1.fast_power[unmodified]": "every state of square-and-multiply is a pow(b, e mod 2^s, m) or a sum of such terms (audit section 3; ruling R-14); the VARIANT fast_power_f3 with an added term in the squaring replaces it (see VARIANT)",
    "C1.counter_list[unmodified]": "the histogram of v % k is a residue count (audit section 3); the state-machine tally counter_list_f3 replaces it",
}


def f3(family: str, supersedes: str | None = None, variant: str | None = None) -> Callable[[Builder], Builder]:
    def deco(fn: Builder) -> Builder:
        lid = f"C1.{fn.__name__}"
        if any(x.id == lid for x in FIX3):
            raise ValueError(f"duplicate lineage id {lid}")
        FIX3.append(Lineage(lid, "C1", family, fn))
        FAMILY_OF[lid] = family
        if supersedes:
            SUPERSEDES3[lid] = supersedes
        if variant:
            VARIANT[lid] = variant
        return fn

    return deco


FIX3_MODULES = ("lineages_c1_fix3_numbers", "lineages_c1_fix3_lists", "lineages_c1_fix3_other")


def load_fix3() -> list[Lineage]:
    import importlib

    for mod in FIX3_MODULES:
        importlib.import_module(f"studies.m0.{mod}")
    return sorted(FIX3, key=lambda x: x.id)
