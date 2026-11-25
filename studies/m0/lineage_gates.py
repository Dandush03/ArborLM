# ruff: noqa: E501
"""Mechanical gates and measurements for new lineages (lineage repair, pilot batch 1; ruling 5: MEASURE, register no new threshold).

For every lineage (new or existing) this module can compute, with no model involved:
  * a structural signature of the builder (AST with names and constants abstracted) and an operation-multiset similarity;
  * sentence-skeleton overlap between lineages (names, numbers and vocabulary words abstracted) and the item-skeleton diversity;
  * the answer distribution (top-key share = the score of a constant guess, against the chance level mean(1/k));
  * capacity exhibition at the G = 300 demand of ADR-0033 section 6.2 (10 x ceil(24,000 / 300) + tuning draw = 1,800 distinct items per core level);
  * fixtures (20 items per lineage and level) and a schema document for the separate second-solver agent.

Only the capacity gate has a registered rule (the factor 10). Every other number printed here is a measurement; any threshold proposed later
would be set after seeing these generator statistics (not any model score) and is not in force.

Run: ``uv run --locked python -m studies.m0.lineage_gates pilot-r1``.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import math
import re
import textwrap
import time
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from studies.m0.core import (
    ALL_LEVELS,
    CORE_LEVELS,
    Item,
    Lineage,
    build_item,
    lineages_of,
    stream,
    text_hash,
)
from studies.m0.vocab import COLOURS, EVENTS, NAMES, OBJECTS, PSEUDO, SHAPES, TOWNS

ROOT = Path(__file__).resolve().parents[2]
G_PROPOSED = 300
CAPACITY_FACTOR = 10
POOLS_DEMANDED = 24_000  # development 4,000 + sealed 20,000 of one part
TUNING_PER_LEVEL = 100
STAT_SEED = 953601  # test block 953001-953999

_VOCAB = {w.lower() for w in (*NAMES, *OBJECTS, *TOWNS, *PSEUDO, *COLOURS, *SHAPES)} | {w for e in EVENTS for w in e.split() if w != "the"}
_TOK = re.compile(r"[A-Za-z']+|\d+|[^\sA-Za-z\d]")


# ---------------------------------------------------------------- structural signature of a builder


class _Norm(ast.NodeTransformer):
    """Alpha-rename names and abstract constants, so that two builders that differ only in names and constants hash alike."""

    def __init__(self) -> None:
        self.names: dict[str, str] = {}

    def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
        return ast.copy_location(ast.Name(id=self.names.setdefault(node.id, f"v{len(self.names)}"), ctx=node.ctx), node)

    def visit_arg(self, node: ast.arg) -> ast.AST:
        return ast.arg(arg=self.names.setdefault(node.arg, f"v{len(self.names)}"))

    def visit_Constant(self, node: ast.Constant) -> ast.AST:  # noqa: N802
        return ast.Constant(value=type(node.value).__name__)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:  # noqa: N802
        node.name = "f"
        node.decorator_list = []
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]
        self.generic_visit(node)
        return node


def _tree(fn: Any) -> ast.AST:
    src = textwrap.dedent(inspect.getsource(fn))
    return _Norm().visit(ast.parse(src))


def signature(fn: Any) -> str:
    """SHA-256 of the abstracted AST of the builder."""
    return hashlib.sha256(ast.dump(_tree(fn), annotate_fields=False).encode()).hexdigest()


def op_profile(fn: Any) -> Counter[str]:
    """Multiset of node types, operators, called attribute or function names and comprehension kinds in the builder."""
    c: Counter[str] = Counter()
    for n in ast.walk(_tree(fn)):
        c[type(n).__name__] += 1
        if isinstance(n, ast.Call):
            f = n.func
            c["call:" + (f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "?") if not isinstance(f, ast.Name) else "local")] += 1
        if isinstance(n, ast.BinOp | ast.BoolOp | ast.Compare | ast.UnaryOp):
            for sub in ast.iter_child_nodes(n):
                if isinstance(sub, ast.operator | ast.cmpop | ast.boolop | ast.unaryop):
                    c["op:" + type(sub).__name__] += 1
    return c


def weighted_jaccard(a: Counter[str], b: Counter[str]) -> float:
    keys = set(a) | set(b)
    num = sum(min(a[k], b[k]) for k in sorted(keys))
    den = sum(max(a[k], b[k]) for k in sorted(keys))
    return num / den if den else 1.0


# ---------------------------------------------------------------- skeletons


def skeleton(text: str) -> str:
    out = []
    for t in _TOK.findall(text):
        if t.isdigit():
            out.append("#")
        elif t.lower() in _VOCAB:
            out.append("W")
        else:
            out.append(t.lower())
    return " ".join(out)


def sentence_skeletons(text: str) -> set[str]:
    return {skeleton(s) for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 1.0


# ---------------------------------------------------------------- sampling


def sample_items(lin: Lineage, per_level: int, levels: Sequence[int] = CORE_LEVELS, label: str = "stats") -> list[Item]:
    out = []
    for lv in levels:
        r = stream(STAT_SEED, label, lin.id, str(lv))
        out.extend(build_item(lin, lv, r, "A", f"{lin.id}/{label}/{lv}/{i}") for i in range(per_level))
    return out


# ---------------------------------------------------------------- answer distribution


def answer_stats(items: Sequence[Item]) -> dict[str, Any]:
    keys = Counter(it.answer for it in items)
    n = len(items)
    top_key, top = keys.most_common(1)[0]
    chance = sum((1.0 / it.k) if it.k else 0.0 for it in items) / n
    ent = -sum(c / n * math.log(c / n) for c in keys.values())
    ks = [it.k for it in items if it.k]
    return {
        "n": n,
        "distinct_answers": len(keys),
        "top_key": top_key if len(top_key) <= 30 else top_key[:30],
        "top_share": round(top / n, 4),  # the score of always answering the commonest key
        "chance_mean_1_over_k": round(chance, 4),
        "top_over_chance": round(top / n / chance, 3) if chance else None,
        "entropy_over_log_k": round(ent / math.log(sum(ks) / len(ks)), 3) if ks and sum(ks) / len(ks) > 1 else None,
        "types": sorted({it.answer_type for it in items}),
    }


# ---------------------------------------------------------------- capacity (the registered gate: factor 10 at the demanded count)


def demand_at_g(g: int, level: int) -> int:
    """Worst-case demand per lineage and level: the whole development + sealed pools of a part on one level, plus the tuning draw;
    reserve levels demand the tuning draw only (same reading as ggen.demand_per_level)."""
    return TUNING_PER_LEVEL if level in (0, 6) else math.ceil(POOLS_DEMANDED / g) + TUNING_PER_LEVEL


def exhibit(lin: Lineage, level: int, need: int, attempt_factor: int = 3) -> tuple[int, int]:
    taken: set[str] = set()
    rng = stream(STAT_SEED, "capacity", lin.id, str(level))
    attempts = 0
    while len(taken) < need and attempts < attempt_factor * need + 1000:
        attempts += 1
        taken.add(text_hash(build_item(lin, level, rng, "A", "cap").question))
    return len(taken), attempts


def capacity_rows(lin: Lineage, g: int = G_PROPOSED) -> list[dict[str, Any]]:
    rows = []
    for lv in ALL_LEVELS:
        need = CAPACITY_FACTOR * demand_at_g(g, lv)
        t = time.time()
        found, att = exhibit(lin, lv, need)
        rows.append({"level": lv, "need": need, "found": found, "attempts": att, "passed": found >= need, "seconds": round(time.time() - t, 3)})
    return rows


# ---------------------------------------------------------------- per-lineage record


def lineage_record(lin: Lineage, per_level: int = 400) -> dict[str, Any]:
    t0 = time.time()
    items = sample_items(lin, per_level)
    t_sample = time.time() - t0
    t0 = time.time()
    ans = answer_stats(items)
    t_ans = time.time() - t0
    mid = [it for it in items if it.level == 3]
    sk_items = {skeleton(it.question) for it in mid}
    sent = set().union(*(sentence_skeletons(it.question) for it in items))
    return {
        "id": lin.id,
        "family": lin.family,
        "signature": signature(lin.build),
        "answer": ans,
        "item_skeletons_level3": {"items": len(mid), "distinct": len(sk_items)},
        "sentence_skeletons": len(sent),
        "seconds": {"sample_and_build": round(t_sample, 2), "answer_stats": round(t_ans, 3)},
        "_sentences": sorted(sent),
        "_profile": dict(op_profile(lin.build)),
    }


def overlap_table(records: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    ids = sorted(records)
    sents = {i: set(records[i]["_sentences"]) for i in ids}
    prof = {i: Counter(records[i]["_profile"]) for i in ids}
    out = {}
    for i in ids:
        bs = max(((jaccard(sents[i], sents[j]), j) for j in ids if j != i), default=(0.0, ""))
        bo = max(((weighted_jaccard(prof[i], prof[j]), j) for j in ids if j != i), default=(0.0, ""))
        same_sig = [j for j in ids if j != i and records[j]["signature"] == records[i]["signature"]]
        out[i] = {"max_sentence_jaccard": round(bs[0], 3), "with_sentence": bs[1], "max_op_similarity": round(bo[0], 3), "with_op": bo[1], "same_signature": same_sig}
    return out


# ---------------------------------------------------------------- fixtures and schema document for the second-solver agent


def write_fixtures(lins: Sequence[Lineage], out_dir: Path, per_level: int = 20) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for lin in lins:
        lines = []
        for lv in ALL_LEVELS:
            r = stream(STAT_SEED, "fixture", lin.id, str(lv))
            for i in range(per_level):
                it = build_item(lin, lv, r, "A", f"{lin.id}/fixture/{lv}/{i}")
                lines.append(json.dumps({"id": it.id, "lineage": it.lineage, "level": it.level, "question": it.question, "structured": it.structured, "answer": it.answer, "answer_type": it.answer_type, "k": it.k}, sort_keys=True, ensure_ascii=True))
        text = "\n".join(lines) + "\n"
        (out_dir / f"{lin.id}.jsonl").write_text(text)
        hashes[lin.id] = hashlib.sha256(text.encode()).hexdigest()
    return hashes


def write_schema(lins: Sequence[Lineage], path: Path, intended: dict[str, str]) -> None:
    parts = [
        "# R1 pilot lineages: structured-form schema for the second-solver agent\n",
        "Written by the implementer for the separate second-solver context (ADR-0033 section 6.2, audit R6). Not a result; nothing here approves anything.\n",
        "## Interface\n",
        "- One solver function per lineage, `solve(structured: dict) -> str`, returning the answer string exactly as the fixture's `answer` field. It reads ONLY `structured` (parsed from JSON): never the question text, never the generator modules, never the `answer` field.",
        "- Registry: `SOLVERS: dict[str, Callable]` keyed by lineage id (`R1.<name>`); one module per family, `studies/m0/solvers_r1_<family>.py`.",
        "- A solver raises `ValueError` when the structured form does not have exactly one answer (the generators guarantee uniqueness; the raise is a safety net).",
        "- Fixtures: `studies/m0/fixtures/r1_pilot/<lineage id>.jsonl`, 20 items for each of the 7 levels (0 and 6 are the reserve levels); keys `id, lineage, level, question, structured, answer, answer_type, k`. The `answer` field is the generator's key; agreement on all fixtures is necessary, not sufficient (the solver agent should also test its own cases).",
        "- The question text is in the fixture only so that an auditor can check the wording against the structured form; solvers must not parse it.\n",
        "## Lineages (intended part, family, the builder's description of its structured form and answer rule)\n",
    ]
    for lin in lins:
        doc = inspect.getdoc(lin.build) or ""
        parts.append(f"### `{lin.id}` (family {lin.family}, intended part {intended.get(lin.id, '?')})\n\n{doc}\n")
        r = stream(STAT_SEED, "schema-example", lin.id)
        it = build_item(lin, 2, r, "A", "example")
        parts.append("Example (level 2):\n\n```\nquestion: " + it.question + "\nstructured: " + json.dumps(it.structured, sort_keys=True) + f"\nanswer: {it.answer}\n```\n")
    path.write_text("\n".join(parts))


# ---------------------------------------------------------------- command line


def pilot_r1(per_level: int = 400) -> dict[str, Any]:
    """Measurements and bookkeeping for the R1 lineages: statistics (old, pilot, revised, new), capacity, fixtures for the registered pilot lineages, the cluster table,
    the shortcut gate. Ruling E: the operation-profile similarity and the item-skeleton diversity are kept as code but are NOT evidence of distinctness."""
    from studies.m0 import lineages_r1_clusters as cl
    from studies.m0 import lineages_r1_shortcuts as sc
    from studies.m0.lineages_r1_common import INTENDED_PART, load_pilot

    pilot_all = load_pilot()
    old = lineages_of("R1")
    everything = [*old, *pilot_all]
    t_all = time.time()
    records: dict[str, dict[str, Any]] = {lin.id: lineage_record(lin, per_level) for lin in everything}
    overlaps = overlap_table(records)
    cap: dict[str, Any] = {}
    for lin in everything:
        t = time.time()
        rows = capacity_rows(lin)
        cap[lin.id] = {"rows": rows, "passed_all": all(r["passed"] for r in rows), "levels_failed": [r["level"] for r in rows if not r["passed"]], "seconds": round(time.time() - t, 2)}
    t = time.time()
    short = sc.shortcut_gate(everything, per_level)
    t_short = time.time() - t
    registered = [x for x in pilot_all if x.id not in cl.SUPERSEDED and x.id not in cl.NOT_REGISTERED]
    out_dir = ROOT / "studies" / "m0" / "fixtures" / "r1_pilot"
    t = time.time()
    fx = write_fixtures(registered, out_dir)
    t_fix = time.time() - t
    (out_dir / "SUPERSEDED.txt").write_text("Shapes replaced by a revision (ids ending _r2) or not registered; their fixtures, if present, are from the earlier shape and must NOT be solved.\n" + "\n".join(sorted([*cl.SUPERSEDED, *cl.NOT_REGISTERED])) + "\n")
    write_schema(registered, ROOT / "studies" / "m0" / "fixtures" / "R1_PILOT_SCHEMA.md", INTENDED_PART)
    parts = cl.clusters_per_part()
    clusters = {cid: [m.id for m in mem] for cid, mem in sorted(cl.cluster_table().items())}
    manifest = {
        "batch": "r1_pilot_1 plus revisions and round 2",
        "note": "No second solvers exist yet; none of these lineages is registered in core.REGISTRY. Parts are given by lineages_r1_clusters.partition (the registered rule applied to cluster-closed family groups), not by the authors' intended placement.",
        "lineages": [
            {"id": lin.id, "family": lin.family, "status": "SUPERSEDED by " + cl.SUPERSEDED[lin.id] if lin.id in cl.SUPERSEDED else ("NOT REGISTERED: " + cl.NOT_REGISTERED[lin.id] if lin.id in cl.NOT_REGISTERED else "registered"),
             "cluster": cl.cluster_of(lin.id), "file": lin.build.__module__.replace(".", "/") + ".py", "signature": records[lin.id]["signature"],
             "capacity_passed_all_levels": cap[lin.id]["passed_all"], "capacity_levels_failed": cap[lin.id]["levels_failed"], "fixture_sha256": fx.get(lin.id)}
            for lin in pilot_all
        ],
        "g_for_capacity": G_PROPOSED,
        "capacity_factor": CAPACITY_FACTOR,
        "registered_lineages_r1": len(cl.registered_lineages()),
        "strict_clusters_r1": len(clusters),
        "strict_clusters_per_part": {p: len(v) for p, v in parts.items()},
    }
    (ROOT / "studies" / "m0" / "manifests" / "r1_pilot_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    (ROOT / "studies" / "m0" / "manifests" / "r1_clusters.json").write_text(json.dumps({"clusters": clusters, "partition": cl.partition(), "family_groups": cl.family_groups(), "clusters_per_part": parts, "superseded": cl.SUPERSEDED, "not_registered": cl.NOT_REGISTERED}, indent=1, sort_keys=True))
    (ROOT / "studies" / "m0" / "manifests" / "r1_shortcuts.json").write_text(json.dumps(short, indent=1, sort_keys=True))
    (ROOT / "studies" / "m0" / "manifests" / "r1_shortcuts_table.md").write_text(
        "# R1 shortcut gate (measured, not thresholded)\n\nPer lineage: the worst heuristic of the battery of `lineages_r1_shortcuts.py` on 2,000 items (400 per core level), excess = accuracy minus mean chance 1/k "
        "(open answers: chance 0). A heuristic that does not fire guesses at chance. Lineage-specific heuristics read the structured form.\n\n" + sc.markdown(short, list(cl.SUPERSEDED)))
    stats = {
        "per_level_items": per_level,
        "levels": list(CORE_LEVELS),
        "non_evidence_of_distinctness": ["_profile / op similarity (max_op_similarity)", "item_skeletons_level3"],
        "records": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in sorted(records.items())},
        "overlap": overlaps,
        "capacity": cap,
        "seconds": {"all": round(time.time() - t_all, 1), "shortcut_gate": round(t_short, 1), "fixtures": round(t_fix, 2)},
        "new_ids": [lin.id for lin in pilot_all],
    }
    (ROOT / "studies" / "m0" / "manifests" / "r1_pilot_stats.json").write_text(json.dumps(stats, indent=1, sort_keys=True))
    return stats


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["pilot-r1"])
    ap.add_argument("--per-level", type=int, default=400)
    a = ap.parse_args()
    s = pilot_r1(a.per_level)
    print(json.dumps({"seconds": s["seconds"], "n_records": len(s["records"])}))


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------- per-family checks used by tests/test_m0_r1_<family>.py


def check_family(family: str, per_level: int = 40) -> list[str]:
    """Mechanical checks on every pilot lineage of one family. Returns problems (empty when none). These do NOT check the key against an
    independent solver (none exists yet); they check that builds succeed, that answers are in the grammar, that closed answers are among the
    options named in the item, that the structured form is JSON and does not carry the key, and that generation is deterministic."""
    from studies.m0.lineages_r1_common import load_pilot
    from studies.m0.scoring import in_grammar, normalise_answer

    problems: list[str] = []
    lins = [x for x in load_pilot() if x.family == family]
    if not lins:
        return [f"no pilot lineage in family {family}"]
    for lin in lins:
        for lv in ALL_LEVELS:
            r = stream(953602, "family-check", lin.id, str(lv))
            items = [build_item(lin, lv, r, "A", f"{lin.id}/{lv}/{i}") for i in range(per_level)]
            again = [build_item(lin, lv, stream(953602, "family-check", lin.id, str(lv)), "A", "d") for _ in range(1)]
            if again[0].question != items[0].question:
                problems.append(f"{lin.id} L{lv}: not deterministic")
            if len({it.question for it in items}) < 0.9 * per_level:
                problems.append(f"{lin.id} L{lv}: fewer than 90% distinct questions")
            for it in items:
                if not in_grammar(it.answer_type, normalise_answer(it.answer)):
                    problems.append(f"{it.id}: answer {it.answer!r} not in grammar {it.answer_type}")
                if it.k is not None and it.k < 2:
                    problems.append(f"{it.id}: k < 2")
                if it.answer_type in ("name", "text") and it.answer not in it.question:
                    problems.append(f"{it.id}: closed answer {it.answer!r} not named in the question")
                if json.loads(json.dumps(it.structured)) != it.structured:
                    problems.append(f"{it.id}: structured form is not JSON-stable")
                if "answer" in it.structured or "key" in it.structured:
                    problems.append(f"{it.id}: structured form carries the key")
            if items[0].answer_type in ("yn", "ynu") and lv >= 1:
                seen = {it.answer for it in items}
                if len(seen) < 2:
                    problems.append(f"{lin.id} L{lv}: only one answer in {per_level} items")
    return problems
