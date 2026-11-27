# ruff: noqa: E501
"""M1 batch 1: capacity, fixtures, schema document and manifest for the new strict-procedure lineages (no model involved; deterministic).

Calls (does not edit) ``studies.m0.lineage_gates``: ``capacity_rows`` (the registered capacity gate at the G = 300 demand: 10 x demand distinct normalised questions per
lineage and level) and ``write_fixtures``. Adds my own stricter measurement: distinct STRUCTURED forms (names, objects and wording ignored) found in a large draw, and the shortcut
check of ``m1_shortcut_check``. The honest log of every procedure considered is in ``CONSIDERED`` below and goes into the manifest.

Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_batch1_gates [--per-level-structured 6000] [--shortcut-per-level 2000]``.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

from studies.m0.core import ALL_LEVELS, CORE_LEVELS, build_item, lineages_of, stream
from studies.m0.lineage_gates import (
    CAPACITY_FACTOR,
    G_PROPOSED,
    STAT_SEED,
    capacity_rows,
    signature,
    write_fixtures,
)
from studies.m0.lineages_m1_common import FIRMNESS, load_batch

ROOT = Path(__file__).resolve().parents[2]

PROCEDURE: dict[str, str] = {
    "M1.gcd_lcm": "Euclid / prime-exponent comparison: the greatest common divisor, or the least common multiple, of 2-4 whole numbers.",
    "M1.crt_congruence": "Simultaneous congruences with coprime moduli: find the least positive number meeting every remainder condition (search / Chinese remainder construction).",
    "M1.prime_factors": "Prime factorisation of one number by trial division, then read off a divisor count, largest prime, distinct-prime sum or prime-factor count.",
    "M1.last_digit_power": "Cycle detection: the last digit of a power repeats with a short period, so reduce the exponent modulo the period, then combine terms modulo 10.",
    "M1.inclusion_exclusion": "Inclusion-exclusion over 2 or 3 overlapping groups (add sizes, subtract pair overlaps, add the triple overlap) to count the union, its complement, or exactly one / two groups.",
    "M1.binomial_choose": "Unordered selection: choose k of n by the binomial coefficient, optionally with a forced member or an exact split between two groups (product of two coefficients).",
    "M1.slot_permutations": "Ordered slot-filling with position restrictions: count digit strings position by position (most restricted position first), with or without repeats.",
    "M1.change_ways": "Count the non-negative integer solutions of a linear coin equation (dynamic programming / systematic enumeration of the number of each coin).",
    "M1.pigeonhole_worst_case": "Worst-case (adversarial) draw counting: an unlucky draw takes as many of each colour as it can without reaching the goal, then one more.",
    "M1.median_list": "Order statistic: sort the values (expanding a frequency table by its counts), then take the middle value or the mean of the two middle values.",
    "M1.mode_tally": "Frequency tally: count each value's occurrences and select the unique most frequent value (or its count).",
    "M1.recurrence_iterate": "Unroll a stated recurrence (sum of the two previous terms, an affine map, or previous term plus its index) step by step to the asked position.",
    "M1.finite_differences": "Polynomial pattern extension: build the table of differences until it is constant, then extend it to the asked position.",
    "M1.quadratic_area": "Solve a quadratic equation arising from a rectangle (area, or area with perimeter) or from a product or sum of squares of two numbers a given amount apart; keep the positive whole root.",
    "M1.digit_puzzle": "Generate-and-test over all candidate numbers: keep the digit strings that meet every clue until exactly one remains.",
    "M1.pythagoras": "Pythagorean relation: combine or separate squared side lengths of a right triangle (ladder, walk, diagonal, perimeter) with whole-number triples.",
    "M1.grid_perimeter": "Exposed-edge counting: perimeter = 4 x squares - 2 x (number of shared edges between neighbouring squares) for a tiled shape given row by row.",
    "M1.painted_cube": "Region decomposition of a box of unit cubes (corners, edges, faces, interior) to count cubes by number of painted faces, with the bottom possibly unpainted.",
    "M1.min_cost_packs": "Minimum-cost combination: compare mixes of pack deals and single items, including buying more than needed, by searching over how many of each pack to buy.",
    "M1.tiered_pricing": "Marginal-rate accumulation over price steps: charge each unit at the rate of its own step (forward), or invert the step totals to recover the units from a bill.",
    "M1.division_counting": "Whole-number division with floor and ceiling: nested packing (ceil of ceil), counting multiples in a range (floor of the top minus floor of the bottom), and empty seats after filling vehicles.",
}

# Existing M1 lineages (studies/m0/lineages_m1.py): the strict procedure of each, and the strict groups (not edited; my reading, for the lead to audit).
EXISTING_M1: dict[str, dict[str, str]] = {
    "M1.shopping": {"strict": "sum of count x price, subtract from the amount paid", "group": "S1 straight-line arithmetic: a sum of products or differences, then one aggregate (subtract or divide)"},
    "M1.speed_distance": {"strict": "sum of speed x time, optionally divided by total time", "group": "S1"},
    "M1.mixture": {"strict": "weighted mean: sum of amount x price divided by total amount", "group": "S1"},
    "M1.clock_duration": {"strict": "sum of (arrival - departure) over legs", "group": "S1"},
    "M1.percent_change": {"strict": "apply successive percentage multipliers", "group": "S2 multiplicative chain: multiply by a factor (percent, fraction) one or more times, then optionally divide"},
    "M1.tip_split": {"strict": "multiply by 1 + tip, divide by the number of people", "group": "S2"},
    "M1.fraction_remainder": {"strict": "subtract a fraction of the amount, then a fraction of the rest", "group": "S2"},
    "M1.pipes_work": {"strict": "net rate = sum of rates - drain; time = volume / net rate", "group": "S3 combine rates, divide a quantity by the combined rate (arguably the same as S5: solving volume = rate x time)"},
    "M1.ratio_share": {"strict": "divide a total in a ratio: total / sum of parts x the person's part", "group": "S4 proportional split by unit scaling"},
    "M1.linear_equation": {"strict": "solve k x + m = j x + e by undoing operations", "group": "S5 one linear equation in one unknown, solved by inversion"},
    "M1.consecutive": {"strict": "sum of an arithmetic run = n x first + step x n(n-1)/2, solve for the first, give the last", "group": "S5"},
    "M1.ages": {"strict": "k b + t + b + t = total, solve for b", "group": "S5"},
    "M1.average_missing": {"strict": "mean x n - sum of the known scores", "group": "S5"},
    "M1.rectangle": {"strict": "perimeter = 2 (w + k w), solve for w, then area", "group": "S5"},
    "M1.arithmetic_series": {"strict": "closed form n (2 a + (n - 1) d) / 2", "group": "S6 closed-form sum of an arithmetic progression"},
    "M1.coins": {"strict": "two unknown counts from a count equation and a value equation (2 x 2 linear system)", "group": "S7 two linear equations in two unknowns"},
}

# The honest log: every procedure considered. status: delivered | rejected. reason names the check or the existing/new lineage it would duplicate under the strict reading.
CONSIDERED: list[dict[str, str]] = [
    {"procedure": "probability_draws (chance of two reds without replacement, as a percent)", "status": "rejected", "reason": "duplicate of binomial_choose (ratio of two counts of selections) plus percent arithmetic; also the exact-decimal constraint would make the answer space lumpy"},
    {"procedure": "variance / sum of squared deviations from the mean", "status": "rejected", "reason": "duplicate of existing S1 (evaluate a stated formula on given numbers; mean then sum of squares is straight-line arithmetic)"},
    {"procedure": "work_rate_reciprocals (A alone takes a hours, B alone b hours, together?)", "status": "rejected", "reason": "duplicate of existing pipes_work (add rates, divide the quantity); only the fraction arithmetic differs"},
    {"procedure": "meeting / catch-up speeds (relative speed, head start)", "status": "rejected", "reason": "duplicate of pipes_work (net rate, then divide)"},
    {"procedure": "unit_conversion_chain (1 foo = 3 bar, 1 bar = 4 baz)", "status": "rejected", "reason": "duplicate of existing S2 (multiplicative chain); the R1 pilot has exchange_rates for the graph form"},
    {"procedure": "compound or simple interest", "status": "rejected", "reason": "duplicate of existing percent_change (S2)"},
    {"procedure": "reverse a chain of operations ('I think of a number, double it, add 5 ... result X')", "status": "rejected", "reason": "duplicate of existing S5 (linear equation, solved by inversion)"},
    {"procedure": "three-unknown linear system (items sold in bundles)", "status": "rejected", "reason": "duplicate of existing coins (S7) and S5: linear system solving"},
    {"procedure": "area of trapezoid, triangle or composite figures by formula", "status": "rejected", "reason": "duplicate of S1 (evaluate a formula on given values)"},
    {"procedure": "clock-hand angle by formula", "status": "rejected", "reason": "duplicate of S1 (formula evaluation, modulo 360)"},
    {"procedure": "fence posts and gaps (off-by-one)", "status": "rejected", "reason": "duplicate of division_counting (division then add one)"},
    {"procedure": "inverse proportion (workers x days constant)", "status": "rejected", "reason": "duplicate of ratio_share / pipes_work (invariant product, one division)"},
    {"procedure": "magic-square missing entry", "status": "rejected", "reason": "duplicate of S5 (linear equation from a line sum)"},
    {"procedure": "water-jug shortest sequence (breadth-first search)", "status": "rejected", "reason": "scope: an algorithmic puzzle that belongs with R2 (algorithmic tasks), not with M1 word problems; not a duplicate"},
    {"procedure": "lattice paths with blocked cells (grid dynamic programming)", "status": "rejected", "reason": "would be a borderline duplicate of change_ways (additive dynamic-programming count); not delivered to avoid padding"},
    {"procedure": "handshakes / round-robin game counts", "status": "rejected", "reason": "duplicate of binomial_choose (choose 2 of n)"},
    {"procedure": "climbing stairs in steps of 1 or 2 (ways)", "status": "rejected", "reason": "duplicate of recurrence_iterate (Fibonacci) / change_ways"},
    {"procedure": "geometric doubling / growth", "status": "rejected", "reason": "duplicate of recurrence_iterate (affine shape) and of existing S2"},
    {"procedure": "tax brackets", "status": "rejected", "reason": "the same procedure as tiered_pricing"},
    {"procedure": "weighted average of groups", "status": "rejected", "reason": "duplicate of existing mixture (S1)"},
    {"procedure": "average speed over equal distances (harmonic)", "status": "rejected", "reason": "duplicate of existing speed_distance average shape (S1)"},
    {"procedure": "day-of-week after n days (as a number of days)", "status": "rejected", "reason": "duplicate of crt_congruence / last_digit_power (modular arithmetic) and of the R1 weekday_shift lineage"},
    {"procedure": "Gauss pairing / sums of 1..n and of odd numbers", "status": "rejected", "reason": "duplicate of existing arithmetic_series (S6)"},
    {"procedure": "how many numbers have digit sum s (digit counting)", "status": "rejected", "reason": "duplicate of digit_puzzle / change_ways (enumerate integer solutions of a linear constraint)"},
]


def _file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def structured_capacity(lin: Any, per_level: int) -> dict[str, int]:
    out = {}
    for lv in ALL_LEVELS:
        rng = stream(STAT_SEED, "m1-structured", lin.id, str(lv))
        seen: set[str] = set()
        for i in range(per_level):
            it = build_item(lin, lv, rng, "A", f"{lin.id}/st/{lv}/{i}")
            seen.add(json.dumps(it.structured, sort_keys=True))
        out[str(lv)] = len(seen)
    return out


def write_schema(lins: list[Any], path: Path) -> None:
    parts = [
        "# M1 batch 1 lineages: structured-form schema for the second-solver agent\n",
        "Written by the implementer for the separate second-solver context (ADR-0033 section 6.2). Not a result; nothing here approves anything.\n",
        "## Interface\n",
        "- One solver function per lineage, `solve(structured: dict) -> str`, returning the answer string exactly as the fixture's `answer` field: a whole number, or a decimal with at most two places and no trailing zeros (a negative sign never occurs in this batch). It reads ONLY `structured` (parsed from JSON): never the question text, never the generator modules, never the `answer` field.",
        "- Registry: `SOLVERS: dict[str, Callable]` keyed by lineage id (`M1.<name>`); one module per family, `studies/m0/solvers_m1_<family>.py` (family names in the lineage headings below).",
        "- A solver raises `ValueError` when the structured form does not have exactly one answer (the generators guarantee uniqueness; the raise is a safety net).",
        "- Fixtures: `studies/m0/fixtures/m1_batch1/<lineage id>.jsonl`, 20 items for each of the 7 levels (0 and 6 are the reserve levels); keys `id, lineage, level, question, structured, answer, answer_type, k`. `answer_type` is always `number` and `k` is null. The `answer` field is the generator's key; agreement on all fixtures is necessary, not sufficient (the solver agent should also test its own cases).",
        "- The question text is in the fixture only so that an auditor can check the wording, the stated answer format and the units against the structured form; solvers must not parse it.",
        "- Every question states its answer format inside the item (\"Answer with a whole number.\" or the decimal sentence); units are named in the question where they matter (centimetres, seconds, dollars); there is no rounding anywhere: every answer is exact.",
        "- Solvers should use a different method from the one described here where possible (for example brute-force enumeration instead of a closed form), so that the pair is a real check.\n",
        "## Lineages (family, strict procedure, the builder's description of its structured form and answer rule)\n",
    ]
    for lin in lins:
        doc = inspect.getdoc(lin.build) or ""
        parts.append(f"### `{lin.id}` (family {lin.family}, firmness: {FIRMNESS[lin.id]})\n\nStrict procedure: {PROCEDURE[lin.id]}\n\n{doc}\n")
        r = stream(STAT_SEED, "m1-schema-example", lin.id)
        it = build_item(lin, 2, r, "A", "example")
        parts.append("Example (level 2):\n\n```\nquestion: " + it.question + "\nstructured: " + json.dumps(it.structured, sort_keys=True) + f"\nanswer: {it.answer}\n```\n")
    path.write_text("\n".join(parts))


def main() -> None:
    import argparse

    from studies.m0 import m1_shortcut_check

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--per-level-structured", type=int, default=6000)
    ap.add_argument("--shortcut-per-level", type=int, default=2000)
    ap.add_argument("--shortcut-json", default="")
    a = ap.parse_args()
    t0 = time.time()
    lins = load_batch()
    assert set(PROCEDURE) == {x.id for x in lins}, "procedure text missing or extra"
    existing_ids = {x.id for x in lineages_of("M1")}
    assert not existing_ids & {x.id for x in lins}
    cap: dict[str, Any] = {}
    stc: dict[str, Any] = {}
    for lin in lins:
        rows = capacity_rows(lin)
        cap[lin.id] = {"rows": rows, "passed_all": all(r["passed"] for r in rows), "levels_failed": [r["level"] for r in rows if not r["passed"]]}
        stc[lin.id] = structured_capacity(lin, a.per_level_structured)
        print(lin.id, "capacity", "PASS" if cap[lin.id]["passed_all"] else f"FAIL {cap[lin.id]['levels_failed']}", "structured", [stc[lin.id][str(lv)] for lv in ALL_LEVELS], flush=True)
    from studies.m0.lineage_gates import demand_at_g

    sigs: dict[str, list[str]] = {}
    for lin in [*lins, *lineages_of("M1")]:
        sigs.setdefault(signature(lin.build), []).append(lin.id)
    sig_collisions = [v for v in sigs.values() if len(v) > 1]
    sc = m1_shortcut_check.run(a.shortcut_per_level)
    if a.shortcut_json:
        Path(a.shortcut_json).write_text(json.dumps(sc, indent=1, sort_keys=True))
    out_dir = ROOT / "studies" / "m0" / "fixtures" / "m1_batch1"
    fx = write_fixtures(lins, out_dir)
    write_schema(lins, ROOT / "studies" / "m0" / "fixtures" / "M1_BATCH1_SCHEMA.md")
    manifest = {
        "batch": "m1_batch1",
        "note": "New M1 lineages under the STRICT reading (one lineage = one general solution algorithm). Own registry (lineages_m1_common.BATCH), not core.REGISTRY; no second solvers exist yet; nothing here is registered, approved or scored. Measured numbers are labelled by what they are: capacity and shortcut figures are MEASURED on generator output (no model involved); firmness is my judgement.",
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "uv_lock_sha256": _file_hash(ROOT / "uv.lock"), "stat_seed": STAT_SEED, "shortcut_seed": m1_shortcut_check.SEED},
        "commands": ["PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.m1_batch1_gates", "uv run --locked --offline python -m studies.m0.m1_shortcut_check --per-level 2000"],
        "g_for_capacity": G_PROPOSED,
        "capacity_factor": CAPACITY_FACTOR,
        "shortcut_screening_rule": "flag if the best trivial heuristic reaches max(0.25, 2 x the constant most-frequent-answer rate) on any level (my screening choice, not a registered threshold)",
        "lineages": [
            {
                "id": lin.id, "family": lin.family, "firmness": FIRMNESS[lin.id], "file": f"studies/m0/lineages_m1_{lin.family}.py",
                "strict_procedure": PROCEDURE[lin.id], "signature": signature(lin.build),
                "source_sha256": _file_hash(ROOT / "studies" / "m0" / f"lineages_m1_{lin.family}.py"),
                "capacity_passed_all_levels": cap[lin.id]["passed_all"], "capacity_levels_failed": cap[lin.id]["levels_failed"], "capacity_rows": cap[lin.id]["rows"],
                "distinct_structured_forms_found_per_level": stc[lin.id], "structured_draws_per_level": a.per_level_structured,
                "levels_where_text_capacity_relies_on_names_and_settings": [lv for lv in ALL_LEVELS if stc[lin.id][str(lv)] < CAPACITY_FACTOR * demand_at_g(G_PROPOSED, lv)],
                "shortcuts": {"worst_over_levels": sc[lin.id]["worst_over_levels"], "max_constant_rate": sc[lin.id]["max_constant_rate"], "flagged_levels": sc[lin.id]["flagged_levels"],
                              "per_level": {lv: {k: x[k] for k in ("n", "distinct_answers", "constant_most_frequent_rate", "constant_heldout_rate", "top_key", "oracle_answer_is_some_stated_number", "worst_heuristic", "worst_accuracy", "flag")} for lv, x in sc[lin.id]["levels"].items()}},
                "fixture_sha256": fx[lin.id],
            }
            for lin in lins
        ],
        "existing_m1": EXISTING_M1,
        "considered_log": [{"procedure": k.replace("M1.", ""), "status": "delivered", "firmness": FIRMNESS[k], "reason": "see strict_procedure in the lineage record"} for k in sorted(PROCEDURE)] + CONSIDERED,
        "signature_collisions_with_existing_m1_or_within_batch": sig_collisions,
        "seconds": round(time.time() - t0, 1),
    }
    (ROOT / "studies" / "m0" / "manifests" / "m1_batch1_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print("done", round(time.time() - t0, 1), "s;", len(lins), "lineages;", "levels", CORE_LEVELS)


if __name__ == "__main__":
    main()
