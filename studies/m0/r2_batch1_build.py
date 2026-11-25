# ruff: noqa: E501
"""Builds the R2 batch-1 deliverables: capacity record (the registered gate, via ``lineage_gates.capacity_rows`` at G = 300, plus a stricter
count of distinct STRUCTURED forms), builder signatures, fixtures for the second-solver agent, the schema document, and the manifest with the honest log.

Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r2_batch1_build --shortcuts <summary.json>``.
Nothing here is a result about any model. No threshold is registered. Self-checked; not independent review.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import time
from pathlib import Path
from typing import Any

from studies.m0 import lineage_gates as lg
from studies.m0.core import ALL_LEVELS, Lineage, build_item, lineages_of, stream
from studies.m0.lineages_r2_common import load_batch1

ROOT = Path(__file__).resolve().parents[2]

# the strict procedure of each delivered lineage (one line)
PROCEDURE = {
    "R2.lcs_length": "fill a two-string prefix table: longest common subsequence length",
    "R2.coin_change_min": "unbounded-supply capacity table: fewest coins for an exact amount (greedy is wrong in most items)",
    "R2.lis_length": "longest strictly increasing subsequence length",
    "R2.max_subarray_sum": "running best-ending-here scan: largest sum of a contiguous block",
    "R2.gcd_euclid": "Euclid's remainder algorithm (gcd, lcm or step count)",
    "R2.modular_power": "repeated squaring modulo m",
    "R2.crt_smallest": "combine congruences with coprime moduli: smallest positive solution",
    "R2.prime_factor_query": "trial-division prime factorisation (largest prime, or sum of the prime factors with multiplicity)",
    "R2.bst_traversal": "binary-search-tree insertion, then a pre-, post- or level-order walk",
    "R2.min_heap_ops": "array binary min-heap: sift-up insertion and sift-down removal",
    "R2.cache_eviction": "cache with a stated eviction rule (LRU or FIFO): misses, or presence at the end",
    "R2.hash_probe": "open-addressing hash table with linear probing: final slot or number of probes",
    "R2.bracket_match": "last-opened-first-closed matching of three kinds of bracket: validity, or the partner position",
    "R2.expression_eval": "evaluate an infix expression under a stated operator-precedence convention",
    "R2.interval_scheduling": "earliest-finish-time selection of non-overlapping intervals",
    "R2.merge_smallest_cost": "repeatedly merge the two smallest items (Huffman-style total cost)",
    "R2.cheapest_network": "cycle-avoiding cheapest-edge selection (minimum spanning network weight)",
    "R2.deferred_acceptance_partner": "proposal-and-hold rounds (Gale-Shapley deferred acceptance)",
    "R2.subtraction_game": "label pile sizes win/lose from small to large (backward induction)",
    "R2.cellular_automaton": "synchronous three-neighbour table update of a row, repeated",
    "R2.chip_toppling": "topple cells with 2+ chips until stable (abelian sandpile on a path with open ends)",
    "R2.luhn_check": "alternate-digit doubling checksum (Luhn): validity or check digit",
    "R2.hamming_error_position": "parity-check syndrome of a Hamming code: the flipped position",
    "R2.dictionary_rank": "factorial-base ranking or unranking of arrangements in dictionary order",
    "R2.binary_search_trace": "binary search with a stated midpoint rule: values looked at, or the third value",
    "R2.longest_palindromic_substring": "expand around every centre: longest palindromic block length",
}

# every procedure considered: name, status, reason, and what it duplicates (or is adjacent to) under the STRICT reading
CONSIDERED: list[dict[str, str]] = [
    {"name": "lcs_length", "status": "delivered", "note": "dynprog family; same PARADIGM as coin_change_min and lis_length (flag for the lead), different recurrence and data flow"},
    {"name": "coin_change_min", "status": "delivered", "note": "paradigm-adjacent to lcs_length; greedy is the planted wrong shortcut"},
    {"name": "lis_length", "status": "delivered", "note": "paradigm-adjacent to lcs_length"},
    {"name": "max_subarray_sum", "status": "delivered", "note": "single left-to-right scan with carried state; distinct from count_divisible (a predicate count)"},
    {"name": "gcd_euclid", "status": "delivered", "note": "lcm and step-count questions are shapes of this lineage"},
    {"name": "modular_power", "status": "delivered", "note": "distinct from the existing permutation_power (iterate a stated map)"},
    {"name": "crt_smallest", "status": "delivered", "note": "congruence combination; adjacent to numtheory but a different procedure from multiples_between (floor formula) and digit_root"},
    {"name": "prime_factor_query", "status": "delivered", "note": "largest prime and sum of prime factors are shapes of one factorisation lineage"},
    {"name": "bst_traversal", "status": "delivered", "note": "pre-, post- and level order are shapes; distinct data structure from list_ops and stack_machine"},
    {"name": "min_heap_ops", "status": "delivered", "note": "adjacent to bst_traversal and stack_machine as 'simulate a data structure'; kept apart because the invariant and the repair steps differ"},
    {"name": "cache_eviction", "status": "delivered", "note": "LRU and FIFO are shapes of one lineage (changing the eviction rule is a rule change inside one simulation)"},
    {"name": "hash_probe", "status": "delivered", "note": "adjacent to cache_eviction as 'simulate a data structure'"},
    {"name": "bracket_match", "status": "delivered", "note": "distinct from stack_machine (push/pop of numbers with arithmetic): here the stack is for matching"},
    {"name": "expression_eval", "status": "delivered", "note": "the left-to-right convention is a shape (changing a convention), not a second lineage"},
    {"name": "interval_scheduling", "status": "delivered", "note": "adjacent to merge_smallest_cost as 'greedy'; different selection key and structure"},
    {"name": "merge_smallest_cost", "status": "delivered", "note": "priority-queue greedy"},
    {"name": "cheapest_network", "status": "delivered", "note": "same strict procedure as R1.graph_shortest_route? No: Kruskal edge selection versus single-source distance; R1 is a different evaluation"},
    {"name": "deferred_acceptance_partner", "status": "delivered", "note": "matching by proposal rounds"},
    {"name": "subtraction_game", "status": "delivered", "note": "win/lose labelling; nim, misere and multi-pile variants would be shapes, not built"},
    {"name": "cellular_automaton", "status": "delivered", "note": "Game of Life would be a shape of this (synchronous local rule)"},
    {"name": "chip_toppling", "status": "delivered", "note": "asynchronous relaxation to a stable state; kept apart from cellular_automaton (synchronous)"},
    {"name": "luhn_check", "status": "delivered", "note": "ISBN or other weighted-sum checksums would be shapes"},
    {"name": "hamming_error_position", "status": "delivered", "note": "parity-check syndrome"},
    {"name": "dictionary_rank", "status": "delivered", "note": "ranking and unranking are shapes of one lineage"},
    {"name": "binary_search_trace", "status": "delivered", "note": "different midpoint conventions are shapes"},
    {"name": "longest_palindromic_substring", "status": "delivered", "note": "distinct from the existing palindrome_check (a yes/no reverse comparison)"},
    {"name": "edit_distance (Levenshtein)", "status": "rejected", "note": "same strict procedure as lcs_length: two-string prefix table with a different cell rule"},
    {"name": "0/1 knapsack, subset sum, count the ways to make change, stair paths", "status": "rejected", "note": "same strict procedure as coin_change_min (capacity table)"},
    {"name": "grid path counting / minimum-cost grid path", "status": "rejected", "note": "same paradigm as the DP lineages already delivered; a third and fourth table recurrence would pad the dynprog family"},
    {"name": "inversion count / bubble-sort passes / insertion-sort state", "status": "rejected", "note": "same strict procedure as the existing sorting lineages (order relation over a list)"},
    {"name": "Lomuto partition step", "status": "rejected", "note": "a named sorting step; shape of sorting-procedure simulation, near-duplicate of list_ops"},
    {"name": "mode / majority / histogram", "status": "rejected", "note": "same strict procedure as count_letter and count_divisible (tally)"},
    {"name": "pairs with a given sum; pair counting", "status": "rejected", "note": "same strict procedure as count_divisible (count items by a relation)"},
    {"name": "union length of intervals; maximum overlap (rooms needed)", "status": "rejected", "note": "same interval-sweep family as interval_scheduling under the strict reading"},
    {"name": "Collatz / digit-sum iteration / cycle detection / linear recurrence unrolling", "status": "rejected", "note": "iterate a stated rule until a condition: same strict procedure as the existing permutation_power and digit_root"},
    {"name": "Roman numerals, balanced ternary, factorial base conversion, binary XOR/AND", "status": "rejected", "note": "changing the number system: a shape of the existing base-conversion lineages"},
    {"name": "Vigenere / affine / rot-N cipher", "status": "rejected", "note": "same strict procedure as caesar_shift (per-letter modular map)"},
    {"name": "run-length decoding, look-and-say", "status": "rejected", "note": "same strict procedure as run_length"},
    {"name": "substring occurrence count (overlaps), anagram test, longest run", "status": "rejected", "note": "same strict procedure as count_letter or run_length (scan and tally)"},
    {"name": "Markov (priority-ordered) string rewriting to normal form", "status": "rejected", "note": "string rewriting is the existing string_rewrite family; iterating to a fixed point is a change of control, not of procedure"},
    {"name": "set-algebra expression sizes", "status": "rejected", "note": "same strict procedure as expression_eval (evaluate a nested expression)"},
    {"name": "prefix/postfix (Polish) expression evaluation, function composition f(g(x))", "status": "rejected", "note": "same strict procedure as expression_eval or stack_machine"},
    {"name": "matrix product entry, determinant, polynomial coefficient of a product", "status": "rejected", "note": "sum-of-products indexing: same strict procedure as grid_sum (aggregate over indexed cells)"},
    {"name": "spiral / transpose / rotate a grid, then read a cell", "status": "rejected", "note": "index-transform simulation: same strict procedure as grid_sum and list_ops"},
    {"name": "Tower of Hanoi move queries", "status": "rejected", "note": "capacity: (n, move index) has far fewer than 1,800 items at level 1 without padding by decoration"},
    {"name": "Nim (xor of heaps), minimax on a game tree, misere subtraction", "status": "rejected", "note": "same strict procedure as subtraction_game (outcome of an impartial or alternating game)"},
    {"name": "first-fit bin packing", "status": "deferred", "note": "built as a draft idea only; judged simulation-adjacent to cache_eviction and cheaper to leave out than to defend"},
    {"name": "round-robin scheduling finish time", "status": "deferred", "note": "cyclic-queue simulation: adjacent to the R1 Josephus lineage and to cache_eviction; not built"},
    {"name": "tree diameter / longest path in a tree", "status": "deferred", "note": "not built; adjacent to cheapest_network under a strict reading (tree aggregates over weighted edges)"},
    {"name": "bipartite maximum matching size (augmenting paths)", "status": "deferred", "note": "not built; adjacent to deferred_acceptance_partner (matching)"},
    {"name": "connected components / flood fill on a grid", "status": "rejected", "note": "closure: same strict procedure as R1 reachability and equivalence classes"},
    {"name": "topological order (Kahn), longest path in a DAG", "status": "rejected", "note": "R1 audit and notes: same strict procedure as reachability / critical path"},
    {"name": "Dijkstra shortest route, Josephus, queue/stack piles", "status": "rejected", "note": "already R1 pilot lineages (different evaluation); not repeated"},
    {"name": "Hamming distance, parity bit, CRC", "status": "rejected", "note": "CRC polynomial division is a different procedure but too long for a short item; parity/distance are shapes of hamming_error_position or count_letter"},
]


def struct_capacity(lin: Lineage, level: int, need: int, attempt_factor: int = 3) -> int:
    """Distinct STRUCTURED forms (names and wording do not count), up to ``need``."""
    seen: set[str] = set()
    rng = stream(lg.STAT_SEED, "struct-capacity", lin.id, str(level))
    attempts = 0
    while len(seen) < need and attempts < attempt_factor * need + 1000:
        attempts += 1
        seen.add(json.dumps(build_item(lin, level, rng, "A", "cap").structured, sort_keys=True))
    return len(seen)


def write_fixtures(lins: list[Lineage], out_dir: Path, per_level: int = 20) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for lin in lins:
        lines = []
        for lv in ALL_LEVELS:
            r = stream(lg.STAT_SEED, "r2-fixture", lin.id, str(lv))
            for i in range(per_level):
                it = build_item(lin, lv, r, "A", f"{lin.id}/fixture/{lv}/{i}")
                lines.append(json.dumps({"id": it.id, "lineage": it.lineage, "level": it.level, "question": it.question, "structured": it.structured,
                                         "answer": it.answer, "answer_type": it.answer_type, "k": it.k}, sort_keys=True, ensure_ascii=True))
        text = "\n".join(lines) + "\n"
        (out_dir / f"{lin.id}.jsonl").write_text(text)
        hashes[lin.id] = hashlib.sha256(text.encode()).hexdigest()
    return hashes


def write_schema(lins: list[Lineage], path: Path) -> None:
    parts = [
        "# R2 batch 1 lineages: structured-form schema for the second-solver agent\n",
        "Written by the implementer for the separate second-solver context (ADR-0033 section 6.2). Not a result; nothing here approves anything.\n",
        "## Interface\n",
        "- One solver function per lineage, `solve(structured: dict) -> str`, returning the answer string exactly as the fixture's `answer` field. It reads ONLY `structured` (parsed from JSON): never the question text, never the generator modules, never the `answer` field.",
        "- Registry: `SOLVERS: dict[str, Callable]` keyed by lineage id (`R2.<name>`); suggested file `studies/m0/solvers_r2_batch1_<family>.py`.",
        "- A solver raises `ValueError` when the structured form does not have exactly one answer (the generators guarantee uniqueness; the raise is a safety net).",
        "- Answer formats: `number` = a decimal integer (may be negative); `list` = integers separated by `, `; `text` = one line; `yn` = `yes` or `no`; `name` = a name copied from the question.",
        "- Fixtures: `studies/m0/fixtures/r2_batch1/<lineage id>.jsonl`, 20 items for each of the 7 levels (0 and 6 are the reserve levels); keys `id, lineage, level, question, structured, answer, answer_type, k`. The `answer` field is the generator's key; agreement on all fixtures is necessary, not sufficient.",
        "- The question text is in the fixture only so that an auditor can check the wording and the stated conventions against the structured form; solvers must not parse it.",
        "- No intended part is given: the part of each family is fixed by the registered partition seed over the final family list.\n",
        "## Lineages (family, strict procedure, the builder's description of its structured form and answer rule)\n",
    ]
    for lin in lins:
        doc = inspect.getdoc(lin.build) or ""
        parts.append(f"### `{lin.id}` (family {lin.family})\n\nStrict procedure: {PROCEDURE[lin.id]}.\n\n{doc}\n")
        r = stream(lg.STAT_SEED, "r2-schema-example", lin.id)
        it = build_item(lin, 2, r, "A", "example")
        parts.append("Example (level 2):\n\n```\nquestion: " + it.question + "\nstructured: " + json.dumps(it.structured, sort_keys=True) + f"\nanswer: {it.answer}\n```\n")
    path.write_text("\n".join(parts))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shortcuts", type=Path, required=True, help="summary.json written by r2_shortcut_check")
    a = ap.parse_args()
    lins = load_batch1()
    t_all = time.time()
    core_ids = {x.id for x in lineages_of("R2")}
    assert not core_ids & {x.id for x in lins}
    assert set(PROCEDURE) == {x.id for x in lins}, sorted(set(PROCEDURE) ^ {x.id for x in lins})
    short = {row["lineage"]: row for row in json.loads(a.shortcuts.read_text())}
    cap: dict[str, Any] = {}
    for lin in lins:
        t = time.time()
        rows = lg.capacity_rows(lin)
        for row in rows:
            row["structured_forms_found"] = struct_capacity(lin, row["level"], row["need"])
        cap[lin.id] = {"rows": rows, "passed_all": all(x["passed"] for x in rows), "levels_failed": [x["level"] for x in rows if not x["passed"]],
                       "structured_passed_all": all(x["structured_forms_found"] >= x["need"] for x in rows),
                       "structured_levels_short": [x["level"] for x in rows if x["structured_forms_found"] < x["need"]], "seconds": round(time.time() - t, 2)}
    t = time.time()
    fx = write_fixtures(lins, ROOT / "studies" / "m0" / "fixtures" / "r2_batch1")
    t_fix = time.time() - t
    write_schema(lins, ROOT / "studies" / "m0" / "fixtures" / "R2_BATCH1_SCHEMA.md")
    manifest = {
        "batch": "r2_batch1",
        "note": ("New R2 lineages under the STRICT reading (a lineage is a general algorithm; number system, constraint mix, final question, names, order, negation and surface frame are shapes). "
                 "No second solvers exist yet; none is registered in core.REGISTRY. No part is assigned: the registered partition is by seed over the final family list. "
                 "Self-checked only: not independent review, not Astra validation, not human approval."),
        "existing_r2_strict_procedures": {
            "count_letter, count_divisible": "scan items and tally those meeting a predicate (ONE strict procedure)",
            "sort_list, kth_smallest": "order a list (ONE strict procedure)",
            "list_ops, stack_machine": "apply an operation list to a small structure (one strict procedure on the strictest reading; two on the data-structure reading)",
            "to_base, from_base": "positional-numeral conversion (ONE strict procedure on the strictest reading; division versus Horner on a looser one)",
            "string_rewrite": "sequential substitution", "caesar_shift": "per-letter modular map", "run_length": "maximal-run encoding",
            "palindrome_check": "compare with the reverse", "grid_sum": "aggregate along a row, column or diagonal",
            "permutation_power": "iterate a stated map", "multiples_between": "floor-division count", "digit_root": "iterate digit sum",
            "count_of_distinct_strict_procedures": "12 to 14 of the 16 existing lineages, depending on how the pairs above are read",
        },
        "new_lineages": [
            {"id": lin.id, "family": lin.family, "file": f"studies/m0/lineages_r2_{lin.family}.py", "strict_procedure": PROCEDURE[lin.id],
             "signature": lg.signature(lin.build), "capacity_passed_all_levels": cap[lin.id]["passed_all"], "capacity_levels_failed": cap[lin.id]["levels_failed"],
             "structured_capacity_passed_all_levels": cap[lin.id]["structured_passed_all"], "structured_capacity_levels_short": cap[lin.id]["structured_levels_short"],
             "fixture_sha256": fx[lin.id], "shortcut_screen": short.get(lin.id)}
            for lin in lins
        ],
        "g_for_capacity": lg.G_PROPOSED,
        "capacity_factor": lg.CAPACITY_FACTOR,
        "capacity_note": "the registered gate counts distinct question texts (names and wording included); 'structured' counts distinct structured forms, a stricter reading",
        "considered_log": CONSIDERED,
        "seconds": {"all": round(time.time() - t_all, 1), "fixtures": round(t_fix, 2)},
    }
    (ROOT / "studies" / "m0" / "manifests" / "r2_batch1_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(json.dumps({"lineages": len(lins), "capacity_all_pass": all(c["passed_all"] for c in cap.values()), "structured_all_pass": all(c["structured_passed_all"] for c in cap.values()),
                      "seconds": manifest["seconds"]}))
    for lid in sorted(cap):
        if not cap[lid]["passed_all"] or not cap[lid]["structured_passed_all"]:
            print(lid, "text-short", cap[lid]["levels_failed"], "structured-short", cap[lid]["structured_levels_short"])


if __name__ == "__main__":
    main()
