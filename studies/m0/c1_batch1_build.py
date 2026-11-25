# ruff: noqa: E501
"""Builds the C1 batch-1 bookkeeping: fixtures, the schema document for the second-solver agent, the manifest and the honest log.

Run (after the shortcut check has written ``manifests/c1_batch1_shortcuts.json``):
``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.c1_batch1_build``.
No threshold is registered here. The capacity factor (10 at the G = 300 demand) is the only registered rule; everything else is a measurement.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from studies.m0 import lineage_gates as lg
from studies.m0.c1_batch1_capacity import alpha_rows
from studies.m0.core import ALL_LEVELS, build_item, draw_items, lineages_of, stream
from studies.m0.lineages_c1_common import FAMILY_MODULES, load_batch1

ROOT = Path(__file__).resolve().parents[2]
FIX_DIR = ROOT / "studies" / "m0" / "fixtures" / "c1_batch1"
SCHEMA = ROOT / "studies" / "m0" / "fixtures" / "C1_BATCH1_SCHEMA.md"
MANIFEST = ROOT / "studies" / "m0" / "manifests" / "c1_batch1_manifest.json"
SHORTCUTS = ROOT / "studies" / "m0" / "manifests" / "c1_batch1_shortcuts.json"
FIXTURE_SEED = 953601

# ------------------------------------------------------------------------------------------------ strict reading of the EXISTING 14

EXISTING_STRICT: dict[str, tuple[str, str]] = {
    "C1.loop_sum": ("range-loop accumulation: add a term to one accumulator, on iterations selected by a modular test", "E1"),
    "C1.nested_pairs": ("range-loop accumulation over a double loop: count or add when a predicate on (i, j) holds", "E1"),
    "C1.list_build": ("range-loop accumulation: append a formula of the index to a list, then sum, maximum or print", "E1"),
    "C1.string_build": ("range-loop accumulation: append one of a few letters chosen by index modulo tests, then print, length or reverse", "E1"),
    "C1.while_counter": ("while loop to a stopping test with a step counter (grow, Collatz or subtract shapes)", "E2"),
    "C1.fib_like": ("two-register recurrence a, b = b, (a + b) [mod m] through a temporary", "E3"),
    "C1.string_methods": ("compose a chain of string methods and slices on a literal string, then read text, length or a count", "E4"),
    "C1.slices": ("evaluate two slices (start, stop, step) of a literal string or list and join or sum them", "E4"),
    "C1.func_branch": ("evaluate a piecewise non-recursive function at a few arguments and combine the results", "E5"),
    "C1.func_compose": ("evaluate a composition of non-recursive linear functions at one argument", "E5"),
    "C1.counter_list": ("histogram: add one to counts[data[i] % k] over a literal list", "E6"),
    "C1.bubble_pass": ("one or more adjacent-swap bubble passes over a literal list", "E7"),
    "C1.minmax_track": ("running argmax / argmin scan keeping the best value and its position", "E8"),
    "C1.cond_chain": ("repeated compare-and-subtract on two values (subtractive reduction) for a fixed number of rounds", "E9"),
}
EXISTING_GROUPS = {
    "E1": ["C1.loop_sum", "C1.nested_pairs", "C1.list_build", "C1.string_build"],
    "E4": ["C1.string_methods", "C1.slices"],
    "E5": ["C1.func_branch", "C1.func_compose"],
}

# ------------------------------------------------------------------------------------------------ the new lineages: one-line strict procedure, confidence, neighbours

NEW: dict[str, dict[str, str]] = {
    "C1.euclid_gcd": {"procedure": "Euclid's algorithm, remainder form: (a, b) -> (b, a mod b) until b is 0", "confidence": "borderline", "neighbour": "C1.cond_chain (subtractive form of the same gcd reduction; the rules differ in detail: cond_chain doubles on equality and stops after a fixed number of rounds), C1.while_counter (iterate to a stopping test)"},
    "C1.digit_peel": {"procedure": "digit extraction: n mod base, n // base, folded, until n is 0", "confidence": "borderline", "neighbour": "C1.euclid_gcd, C1.fast_power, C1.while_counter (all are 'update one or two numbers in a while loop')"},
    "C1.fast_power": {"procedure": "square-and-multiply modular exponentiation over the binary digits of the exponent", "confidence": "borderline", "neighbour": "C1.euclid_gcd, C1.digit_peel, C1.while_counter"},
    "C1.sieve_marking": {"procedure": "sieve of Eratosthenes marking: for each still-flagged index, strike its multiples in a flag list", "confidence": "clear", "neighbour": "C1.nested_pairs (nested loop with a modular test) is the closest existing one"},
    "C1.binary_search": {"procedure": "halve a sorted-list interval around a midpoint probe until found or empty", "confidence": "clear", "neighbour": "none"},
    "C1.merge_two_sorted": {"procedure": "two-pointer merge of two sorted lists, always moving the smaller front element", "confidence": "clear", "neighbour": "none"},
    "C1.insertion_sort": {"procedure": "insertion: shift larger elements of the sorted prefix right to open a hole for the next element", "confidence": "borderline", "neighbour": "C1.bubble_pass and C1.partition_pass (in-place reordering by swaps or shifts)"},
    "C1.partition_pass": {"procedure": "Lomuto partition: sweep with a boundary index, swap elements not above the pivot behind it, pivot placed last", "confidence": "borderline", "neighbour": "C1.bubble_pass and C1.insertion_sort"},
    "C1.kadane_scan": {"procedure": "maximum-subarray scan: cur = max(cur + x, x), best = max(best, cur)", "confidence": "clear", "neighbour": "C1.minmax_track (scan with a running extremum) is the closest existing one; the state update differs"},
    "C1.majority_vote_scan": {"procedure": "Boyer-Moore pairing scan: a candidate with a count that cancels against different values", "confidence": "clear", "neighbour": "C1.minmax_track, C1.counter_list (both read a list once)"},
    "C1.run_length_scan": {"procedure": "run-length encoding: compare each character with the current run, close the run on a change", "confidence": "clear", "neighbour": "C1.string_build (also builds a string in a loop, but by index tests, not by comparing neighbours)"},
    "C1.mirror_pointers": {"procedure": "two pointers walking inward from both ends of a string, comparing the pair they stand on", "confidence": "borderline", "neighbour": "C1.run_length_scan and the string scans (a lead may count 'scan a string with a pointer' once)"},
    "C1.recursive_calls": {"procedure": "evaluate a recursive definition by expanding its call tree down to the base cases", "confidence": "clear", "neighbour": "C1.func_branch and C1.func_compose are non-recursive"},
    "C1.bracket_matching": {"procedure": "stack (array plus top pointer) of open brackets matched against each closing bracket", "confidence": "borderline", "neighbour": "C1.postfix_evaluation (both keep a stack array with a top pointer)"},
    "C1.postfix_evaluation": {"procedure": "reverse-Polish evaluation: push operands, replace the top two by the operator's result", "confidence": "borderline", "neighbour": "C1.bracket_matching"},
    "C1.coin_change_table": {"procedure": "one-dimensional table over amounts updated from smaller amounts, coin by coin (ways, ordered ways, fewest coins)", "confidence": "borderline", "neighbour": "C1.string_pair_table and C1.grid_path_table (a lead may count dynamic-programming tabulation once)"},
    "C1.string_pair_table": {"procedure": "two-dimensional table over prefixes of two strings (longest common subsequence, edit distance)", "confidence": "borderline", "neighbour": "C1.coin_change_table and C1.grid_path_table"},
    "C1.grid_path_table": {"procedure": "row-wise table of best (largest, least, or count) right-and-down paths over a grid", "confidence": "borderline", "neighbour": "C1.coin_change_table and C1.string_pair_table"},
    "C1.bfs_queue": {"procedure": "breadth-first search with an array queue, head and tail pointers and a distance list", "confidence": "clear", "neighbour": "none"},
    "C1.union_find_links": {"procedure": "parent array: find follows links to a root, union hangs one root under another", "confidence": "clear", "neighbour": "none (pointer chasing appears only here)"},
    "C1.circle_elimination": {"procedure": "Josephus counting: advance K live flags around a ring and strike the flag reached", "confidence": "clear", "neighbour": "none"},
    "C1.cellular_update": {"procedure": "synchronous one-dimensional automaton update from an eight-entry rule table into a fresh row", "confidence": "clear", "neighbour": "none"},
    "C1.turtle_walk": {"procedure": "position-and-heading state machine over a command string (turn counter modulo 4)", "confidence": "borderline", "neighbour": "C1.bytecode_loop (a state machine driven by a command sequence)"},
    "C1.bytecode_loop": {"procedure": "fetch-decode-execute loop over (opcode, argument) pairs with an accumulator, a register and a skip", "confidence": "clear", "neighbour": "C1.turtle_walk"},
    "C1.shared_lists": {"procedure": "track which names share one list through assignment, copy, mutation and function calls", "confidence": "clear", "neighbour": "none (identity, not arithmetic)"},
}

# ------------------------------------------------------------------------------------------------ the honest log of every procedure considered

def _d(pid: str, why: str = "") -> dict[str, Any]:
    return {"procedure": NEW[pid]["procedure"], "status": "delivered", "id": pid, "confidence": NEW[pid]["confidence"], "neighbours": NEW[pid]["neighbour"], "note": why}


LOG: list[dict[str, Any]] = [_d(pid) for pid in sorted(NEW)]
LOG += [
    {"procedure": "trial-division prime count (nested loop, i % d == 0)", "status": "rejected", "id": None, "duplicates": ["C1.nested_pairs (the 'mod' shape counts pairs with a modular test)"], "reason": "same strict procedure as an existing lineage; the sieve is the distinct prime procedure and was kept"},
    {"procedure": "prefix sums / running totals", "status": "rejected", "id": None, "duplicates": ["E1: C1.loop_sum, C1.list_build"], "reason": "range-loop accumulation"},
    {"procedure": "Horner / rolling hash h = h * B + x mod M", "status": "rejected", "id": None, "duplicates": ["E1", "C1.digit_peel (the 'rev' shape is the same fold)", "C1.fib_like"], "reason": "an accumulator fold; no distinct invariant"},
    {"procedure": "base conversion by repeated division", "status": "rejected", "id": None, "duplicates": ["C1.digit_peel (base below 10 shape)"], "reason": "the same digit extraction with another base; a shape"},
    {"procedure": "selection sort", "status": "rejected", "id": None, "duplicates": ["C1.minmax_track (argmin scan) + the swap of C1.bubble_pass"], "reason": "a composition of procedures already present, not a new one"},
    {"procedure": "longest increasing subsequence table", "status": "rejected", "id": None, "duplicates": ["C1.string_pair_table", "C1.grid_path_table"], "reason": "a further max-over-earlier-cells tabulation; the tabulation trio is already borderline"},
    {"procedure": "sliding-window sum (add the entering element, subtract the leaving one)", "status": "rejected", "id": None, "duplicates": ["E1"], "reason": "running accumulation with a removal term; not a distinct invariant"},
    {"procedure": "naive substring search with mismatch restart", "status": "rejected", "id": None, "duplicates": ["C1.nested_pairs", "C1.mirror_pointers"], "reason": "nested loops comparing characters; the early exit is not expressible (no break) and the rest is a predicate over index pairs"},
    {"procedure": "substitution cipher / character table lookup", "status": "rejected", "id": None, "duplicates": ["C1.string_methods (replace chain)"], "reason": "per-character substitution; string methods beyond upper/lower/replace/count are also absent from the second solver"},
    {"procedure": "greedy denominations / Roman numerals (subtract the largest table value that fits)", "status": "rejected", "id": None, "duplicates": ["C1.while_counter (subtract shape)", "C1.digit_peel"], "reason": "repeated subtraction against a table; padding"},
    {"procedure": "pointer walk on a functional graph (x = p[x], k times)", "status": "rejected", "id": None, "duplicates": ["C1.union_find_links (the find loop is this walk)"], "reason": "the same pointer chase without the union"},
    {"procedure": "integer square root by Newton iteration", "status": "rejected", "id": None, "duplicates": ["C1.while_counter", "C1.euclid_gcd"], "reason": "iterate a state update to a fixed point; padding of the numeric-loop group"},
    {"procedure": "Collatz steps", "status": "rejected", "id": None, "duplicates": ["C1.while_counter (collatz shape)"], "reason": "already present"},
    {"procedure": "Pascal triangle row update", "status": "rejected", "id": None, "duplicates": ["C1.coin_change_table"], "reason": "in-place one-dimensional table update"},
    {"procedure": "best buy-and-sell profit (running minimum, best difference)", "status": "rejected", "id": None, "duplicates": ["C1.minmax_track", "C1.kadane_scan"], "reason": "a running-extremum scan"},
    {"procedure": "inversion count", "status": "rejected", "id": None, "duplicates": ["C1.nested_pairs ('less' shape)"], "reason": "pairs i < j with xs[i] > xs[j]"},
    {"procedure": "array rotation by three reversals", "status": "rejected", "id": None, "duplicates": ["C1.mirror_pointers (two pointers inward) + swaps"], "reason": "two-pointer swapping; a composition"},
    {"procedure": "trial-division factorisation (smallest divisor search, divide out)", "status": "held_back", "id": None, "duplicates": ["C1.digit_peel, C1.euclid_gcd, C1.fast_power"], "reason": "a named algorithm, but the fourth of one kind (repeated division of one number in a while loop); held back as padding of the numeric-loop group, which is already borderline"},
    {"procedure": "bitwise operations (and, or, xor, shifts), popcount tricks", "status": "blocked", "id": None, "duplicates": [], "reason": "the grammar has no such operators; adding them needs a grammar and second-solver change (not mine)"},
    {"procedure": "dictionary / set membership counting", "status": "blocked", "id": None, "duplicates": [], "reason": "no dict, no set, no 'in' operator in the grammar"},
    {"procedure": "closures, global scope, nonlocal, default arguments, exceptions", "status": "blocked", "id": None, "duplicates": [], "reason": "the second solver runs a function in its own scope only (parameters and locals), and the grammar has no try, global or defaults"},
    {"procedure": "floating-point arithmetic and rounding", "status": "blocked", "id": None, "duplicates": [], "reason": "no / operator or float literals in the grammar"},
    {"procedure": "string split / join / find / index / format", "status": "blocked", "id": None, "duplicates": [], "reason": "the second solver implements only upper, lower, replace and count"},
    {"procedure": "sorted(), pop(), insert(), list comprehensions, tuple unpacking, break/continue", "status": "blocked", "id": None, "duplicates": [], "reason": "not in the grammar or not implemented by the second solver (sorted is allowed by the runner but absent from the tree walker)"},
]


# ------------------------------------------------------------------------------------------------ fixtures, schema, manifest


def ticks(lin: Any) -> dict[str, str]:
    """Measured size of the trace: node evaluations and statements run by the tree-walking second solver, median/max over 200 items per level."""
    import statistics

    from studies.m0.solvers_c1 import _Interp

    out = {}
    for lv in ALL_LEVELS:
        r = stream(FIXTURE_SEED, "c1-ticks", lin.id, str(lv))
        vals = []
        for _ in range(200):
            it = build_item(lin, lv, r, "A", "t")
            w = _Interp()
            w.run(it.structured["program"], {})
            vals.append(w.steps)
        out[str(lv)] = f"{int(statistics.median(vals))}/{max(vals)}"
    return out


def write_fixtures(lins: list[Any]) -> dict[str, str]:
    FIX_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    for lin in lins:
        lines = []
        for lv in ALL_LEVELS:
            r = stream(FIXTURE_SEED, "c1-fixture", lin.id, str(lv))
            for i, it in enumerate(draw_items(lin, "A", lv, 20, r, set(), "fixture")):
                lines.append(json.dumps({"id": f"{lin.id}/fixture/{lv}/{i}", "lineage": it.lineage, "level": it.level, "question": it.question, "structured": it.structured, "answer": it.answer, "answer_type": it.answer_type, "k": it.k}, sort_keys=True, ensure_ascii=True))
        text = "\n".join(lines) + "\n"
        (FIX_DIR / f"{lin.id}.jsonl").write_text(text)
        out[lin.id] = hashlib.sha256(text.encode()).hexdigest()
    return out


def write_schema(lins: list[Any]) -> None:
    from studies.m0 import c1grammar

    parts = [
        "# C1 batch 1: structured-form schema for the second-solver agent\n",
        "Written by the implementer (Sonnet 5.5) for a separate second-solver and audit context (ADR-0033 section 6.2). Not a result; nothing here approves anything. Own checks only: not independent review, not Astra validation, not human approval.\n",
        "## What is checked and how\n",
        "- Item: `question` (the rendered program and the sentence 'What exactly does it print? It prints a single line.'), `structured = {\"program\": <tree>}`, `answer` = the key. `answer_type` is `line`, `k` is null (open answer, scored by string comparison after the registered normalisation, which lower-cases; generators redraw any program whose output is not already lower-case, trimmed, single-spaced, non-empty and not ending in a full stop).",
        "- The key is what the locked interpreter prints: `c1grammar.run_isolated` runs the rendered source in a fresh restricted process (`python -I -S`, builtins len, sum, max, min, abs, range, sorted, str and a collecting print only, 2 s per program, CPU rlimit); the gate runs it twice. The existing independent second solver is the tree walker `solvers_c1.c1_trace(structured)`; it never calls exec, eval or compile and runs each function in its own scope (parameters and locals only). These batch lineages are NOT yet in `solvers_c1.SOLVERS`; the same walker serves them (`SOLVERS[\"C1.<name>\"] = c1_trace`) once registered.",
        "- A separate solver agent may re-derive each key from `structured` (or from the question text) without the generator code. Fixtures: `studies/m0/fixtures/c1_batch1/<lineage id>.jsonl`, 20 distinct items for each of the 7 levels (0 and 6 are the reserve levels), keys `id, lineage, level, question, structured, answer, answer_type, k`. Agreement on all fixtures is necessary, not sufficient.\n",
        "## Conventions the answer depends on (all fixed by Python 3 and stated by the program itself)\n",
        "- Integer `//` and `%` floor toward minus infinity; negative literals are rendered in parentheses, `(-1)`.",
        "- `print` of an int is its decimal form; of a list is `[1, 2, 3]` with `, ` separators; of a string inside a list uses single quotes; a string prints bare. `str(n)` is decimal. `max` and `min` accept two or more arguments or one list.",
        "- Lists are objects: `b = a` makes two names for one list, `a[:]` and `a + [x]` make new lists; a function that assigns to an element of its list parameter changes the caller's list, one that rebinds the parameter does not (C1.shared_lists is about exactly this). `aug` on a list is never used (`xs += ys` mutates in Python but the tree walker would rebind).",
        "- `and` and `or` short-circuit (the insertion sort and the stack matcher rely on `j >= 0 and xs[j] > key`).",
        "- There is no `break`: loops end by their tests. Every loop is bounded; the runner kills a program after 2 s.",
        "- A function is defined before it is called; recursion is used only by C1.recursive_calls, with at most about 12 nested calls.\n",
        "## Tree grammar (from `studies/m0/c1grammar.py`)\n",
        "```\nExpression nodes:" + (c1grammar.__doc__ or "").split("Expression nodes:")[1] + "```\n",
        "## Lineages (family, strict procedure, builder description)\n",
    ]
    for lin in lins:
        doc = inspect.getdoc(lin.build) or ""
        r = stream(FIXTURE_SEED, "c1-schema-example", lin.id)
        it = build_item(lin, 2, r, "A", "example")
        parts.append(f"### `{lin.id}` (family {lin.family}; strict confidence: {NEW[lin.id]['confidence']})\n\nProcedure: {NEW[lin.id]['procedure']}.\n\n{doc}\n")
        parts.append("Example (level 2):\n\n```\n" + it.question.split("\n\n")[1] + "\n```\n\nstructured (tree): `" + json.dumps(it.structured, sort_keys=True)[:600] + ("...`" if len(json.dumps(it.structured)) > 600 else "`") + f"\n\nanswer: `{it.answer}`\n")
    SCHEMA.write_text("\n".join(parts))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    t0 = time.time()
    new = load_batch1()
    old = lineages_of("C1")
    assert {x.id for x in new} == set(NEW), sorted({x.id for x in new} ^ set(NEW))
    assert set(EXISTING_STRICT) == {x.id for x in old}
    sig = {x.id: lg.signature(x.build) for x in [*old, *new]}
    prof = {x.id: lg.op_profile(x.build) for x in [*old, *new]}
    rows = []
    for lin in new:
        t = time.time()
        cap = lg.capacity_rows(lin)  # the registered gate at G = 300: 1,800 per core level, 1,000 per reserve level
        alpha = alpha_rows(lin, 2000)
        others = [x for x in [*old, *new] if x.id != lin.id]
        best = max(others, key=lambda o: lg.weighted_jaccard(prof[lin.id], prof[o.id]))
        rows.append({"id": lin.id, "capacity_gate_g300": cap, "capacity_passed_all_levels": all(r["passed"] for r in cap), "capacity_up_to_renaming_2000": alpha,
                     "up_to_renaming_passed_all_levels": all(r["passed"] for r in alpha), "signature_unique": sum(1 for v in sig.values() if v == sig[lin.id]) == 1,
                     "max_op_similarity": round(lg.weighted_jaccard(prof[lin.id], prof[best.id]), 3), "max_op_similarity_with": best.id, "seconds": round(time.time() - t, 1)})
        rows[-1]["tree_walker_ticks_median_max_by_level"] = ticks(lin)
        print(lin.id, "gate", rows[-1]["capacity_passed_all_levels"], "renaming", rows[-1]["up_to_renaming_passed_all_levels"], flush=True)
    fx = write_fixtures(new)
    write_schema(new)
    shortcuts = json.loads(SHORTCUTS.read_text()) if SHORTCUTS.exists() else None
    base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT, check=False).stdout.strip()
    manifest = {
        "batch": "c1_batch1",
        "note": "C1 batch 1 of the lineage repair (M0, ADR-0033 revision 4). Lineages here are the STRICT reading: a hand-written base rule with a distinct solution procedure (the general algorithm); numbers, constraint mix, printed value, names and surface frame are shapes of one lineage. None is registered in core.REGISTRY; no second-solver entry exists for them yet (the existing tree walker solvers_c1.c1_trace serves them). Self-checked only; not independent review, not Astra validation, not human approval. Counts of lineages are what was reached, not a target.",
        "base_commit": base,
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "hash_seed": "PYTHONHASHSEED=0"},
        "commands": ["PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.c1_shortcut_check --per-level 2000 --out studies/m0/manifests/c1_batch1_shortcuts.json",
                     "PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.c1_batch1_build", "uv run --locked --offline pytest tests/test_m0_c1_*.py"],
        "g_for_capacity": lg.G_PROPOSED,
        "capacity_factor": lg.CAPACITY_FACTOR,
        "families": {fam: sorted(x.id for x in new if x.family == fam) for fam in FAMILY_MODULES},
        "new_lineages": [
            {"id": lin.id, "family": lin.family, "file": f"studies/m0/lineages_c1_{lin.family}.py", "procedure": NEW[lin.id]["procedure"], "strict_confidence": NEW[lin.id]["confidence"],
             "signature": sig[lin.id], "fixture_sha256": fx[lin.id], "capacity": next(r for r in rows if r["id"] == lin.id),
             "shortcuts_core_levels": (shortcuts or {}).get("lineages", {}).get(lin.id, {}).get("summary", {}).get("core_1_5")}
            for lin in new
        ],
        "existing_c1_strict_reading": {k: {"procedure": v[0], "strict_group": v[1]} for k, v in sorted(EXISTING_STRICT.items())},
        "existing_c1_strict_groups_with_more_than_one_member": EXISTING_GROUPS,
        "existing_c1_distinct_strict_procedures": len({v[1] for v in EXISTING_STRICT.values()}),
        "counts": {"new_delivered": len(new), "new_clear": sum(1 for v in NEW.values() if v["confidence"] == "clear"), "new_borderline": sum(1 for v in NEW.values() if v["confidence"] == "borderline"),
                   "log_entries": len(LOG), "log_rejected": sum(1 for e in LOG if e["status"] == "rejected"), "log_blocked": sum(1 for e in LOG if e["status"] == "blocked"), "log_held_back": sum(1 for e in LOG if e["status"] == "held_back")},
        "log": LOG,
        "source_sha256": {p.name: sha(p) for p in sorted((ROOT / "studies" / "m0").glob("lineages_c1_*.py")) + [ROOT / "studies" / "m0" / "c1_shortcut_check.py", ROOT / "studies" / "m0" / "c1_batch1_capacity.py", ROOT / "studies" / "m0" / "c1_batch1_build.py"]},
        "seconds": round(time.time() - t0, 1),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(json.dumps({"seconds": manifest["seconds"], "counts": manifest["counts"], "python": sys.version.split()[0]}))


if __name__ == "__main__":
    main()
