# ruff: noqa: E501
# mypy: disable-error-code="type-arg,no-untyped-call,no-any-return,arg-type,assignment,index,call-overload,var-annotated,list-item,unused-ignore,no-untyped-def"
"""Fixtures, schema document and manifests for the R1 fix-round-3 shapes (new directories and files; nothing earlier is overwritten).

Writes: ``fixtures/r1_fix3/<id>.jsonl`` (20 items per level, levels 0 to 6, ``lineage_gates.write_fixtures``) for the registered ``_r5`` shapes ONLY (ruling R-12: no fixture for a NOT REGISTERED shape),
``fixtures/r1_fix3/SUPERSEDED.txt``, ``fixtures/R1_FIX3_SCHEMA.md`` (the schema for the separate second-solver context), ``manifests/r1_fix3_manifest.json`` and ``manifests/r1_fix3_clusters.json``
(the strict map, the NOT REGISTERED list with reasons, the partition readings). Run: ``PYTHONHASHSEED=0 uv run --locked python -m studies.m0.r1_fix3_fixtures``.
Nothing is registered; no second solver exists for these shapes.
"""

from __future__ import annotations

import json
from pathlib import Path

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_fix3_clusters as c3
from studies.m0.lineages_r1_fix3_common import REPLACES, load_fix3

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "studies/m0/fixtures"
MAN = ROOT / "studies/m0/manifests"


def registered_new() -> list:
    return [x for x in load_fix3() if x.id not in c3.NOT_REGISTERED_V3]


def main() -> None:
    lins = registered_new()
    out = FIX / "r1_fix3"
    hashes = lg.write_fixtures(lins, out, 20)
    path = FIX / "R1_FIX3_SCHEMA.md"
    lg.write_schema(lins, path, {})
    schema = path.read_text()
    schema = schema.replace("# R1 pilot lineages: structured-form schema for the second-solver agent", "# R1 fix-round-3 shapes: structured-form schema for the second-solver agent")
    schema = schema.replace("studies/m0/fixtures/r1_pilot/<lineage id>.jsonl", "studies/m0/fixtures/r1_fix3/<shape id>.jsonl").replace("`SOLVERS: dict[str, Callable]` keyed by lineage id (`R1.<name>`)", "`SOLVERS: dict[str, Callable]` keyed by shape id (`R1.<name>_r5`)")
    schema = schema.replace("## Lineages (intended part, family, the builder's description of its structured form and answer rule)", "## Shapes (family, the builder's description of its structured form and answer rule). No part is assigned (see manifests/r1_fix3_parts.md).")
    schema = schema.replace("Written by the implementer for the separate second-solver context (ADR-0033 section 6.2, audit R6). Not a result; nothing here approves anything.", "Written by the implementer for the separate second-solver context (ADR-0033 section 6.2). Not a result; nothing here approves anything. No second solver exists for these shapes; nothing is registered in core.REGISTRY (ruling R-9).")
    path.write_text(schema)
    lines = ["Fixtures of shapes that this round superseded: they must NOT be solved. The shape that replaces each is in THIS directory (fixtures/r1_fix3/).", "",
             "earlier shape -> round-3 shape (registered candidates)"]
    lines += [f"{old} -> {new}" for new, old in sorted(REPLACES.items(), key=lambda kv: kv[1]) if new not in c3.NOT_REGISTERED_V3]
    lines += ["", "NOT REGISTERED (ruling R-12): no fixture exists or may be solved for these (their earlier fixtures, if any, stay in fixtures/r1_pilot/ and fixtures/r1_rev4/ and must not be solved):"]
    lines += [f"{i}: {why}" for i, why in sorted(c3.NOT_REGISTERED_V3.items())]
    (out / "SUPERSEDED.txt").write_text("\n".join(lines) + "\n")
    ct = c3.cluster_table_v3()
    man = {
        "note": "Round-3 shapes of R1 (human lead's fourth decision; lead rulings R-1..R-17). Self-checked only: not independent review, not Astra validation, not human approval. Nothing is in core.REGISTRY; no second solver exists; no part is assigned.",
        "shapes": {x.id: {"family": x.family, "replaces": REPLACES[x.id], "cluster": c3.cluster_of_v3(x.id), "file": f"studies/m0/lineages_r1_fix3_{x.build.__module__.rsplit('lineages_r1_fix3_', 1)[1]}.py", "signature": lg.signature(x.build),
                          "fixture": f"studies/m0/fixtures/r1_fix3/{x.id}.jsonl", "fixture_sha256": hashes[x.id]} for x in lins},
        "not_registered": c3.NOT_REGISTERED_V3,
    }
    (MAN / "r1_fix3_manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    parts = c3.partition_readings_v3()
    cm = {
        "n_shapes": sum(len(v) for v in ct.values()), "n_clusters": len(ct),
        "clusters": {cid: sorted(m.id for m in ms) for cid, ms in sorted(ct.items())},
        "strict_merges": [list(g) for g in c3.STRICT_MERGES_V3],
        "not_registered": c3.NOT_REGISTERED_V3,
        "partition_readings": {k: {"A": sorted(i for i, p in v.items() if p == "A"), "B": sorted(i for i, p in v.items() if p == "B")} for k, v in parts.items()},
        "source": "docs/reviews/m0-lineage-decision-2026-11-25/audit3_r1/AUDIT3_R1.md section 2 (the two further merges) and section 7; lineages_r1_clusters_v2 for the other merges; ruling R-12",
    }
    (MAN / "r1_fix3_clusters.json").write_text(json.dumps(cm, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(lins)} fixtures, {len(ct)} clusters, {cm['n_shapes']} registered shapes")


if __name__ == "__main__":
    main()
