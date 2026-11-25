# ruff: noqa: E501
"""Fixtures, schema document and manifests for the R1 revision-4 shapes (a new directory; nothing earlier is overwritten).

Writes: ``fixtures/r1_rev4/<id>.jsonl`` (20 items per level, levels 0 to 6, ``lineage_gates.write_fixtures``), ``fixtures/r1_rev4/SUPERSEDED.txt`` (which older fixtures must not be solved),
``fixtures/R1_REV4_SCHEMA.md`` (the schema document for the separate second-solver context), ``manifests/r1_rev4_manifest.json`` and ``manifests/r1_clusters_v2.json`` (the strict map, the borderline
pairs, the authors' notes). Run: ``PYTHONHASHSEED=0 uv run --locked --offline python -m studies.m0.r1_rev4_fixtures``. Nothing is registered; no second solver exists for these shapes.
"""

from __future__ import annotations

import json
from pathlib import Path

from studies.m0 import lineage_gates as lg
from studies.m0 import lineages_r1_clusters_v2 as v2
from studies.m0.lineages_r1_rev4_common import REPLACES, load_rev4

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "studies/m0/fixtures"
MAN = ROOT / "studies/m0/manifests"


def main() -> None:
    lins = load_rev4()
    out = FIX / "r1_rev4"
    hashes = lg.write_fixtures(lins, out, 20)
    lg.write_schema(lins, FIX / "R1_REV4_SCHEMA.md", {})
    schema = (FIX / "R1_REV4_SCHEMA.md").read_text()
    schema = schema.replace("# R1 pilot lineages: structured-form schema for the second-solver agent", "# R1 revision-4 shapes: structured-form schema for the second-solver agent")
    schema = schema.replace("studies/m0/fixtures/r1_pilot/<lineage id>.jsonl", "studies/m0/fixtures/r1_rev4/<shape id>.jsonl").replace("`SOLVERS: dict[str, Callable]` keyed by lineage id (`R1.<name>`)", "`SOLVERS: dict[str, Callable]` keyed by shape id (`R1.<name>_r4`)")
    schema = schema.replace("## Lineages (intended part, family, the builder's description of its structured form and answer rule)", "## Shapes (family, what it replaces, the builder's description of its structured form and answer rule). No part is assigned: the partition is by the registered rule over the final map (see manifests/r1_rev4_parts.md).")
    schema = schema.replace("Written by the implementer for the separate second-solver context (ADR-0033 section 6.2, audit R6). Not a result; nothing here approves anything.", "Written by the implementer for the separate second-solver context (ADR-0033 section 6.2). Not a result; nothing here approves anything. No second solver exists for these shapes; nothing is registered in core.REGISTRY (ruling R-9).")
    (FIX / "R1_REV4_SCHEMA.md").write_text(schema)
    lines = ["Fixtures of shapes that were superseded: they must NOT be solved. Old fixtures live in studies/m0/fixtures/r1_pilot/ (the 20 + 8 pilot and new shapes) and, for the 15 original lineages, in no fixture directory.",
             "The revision-4 shape that replaces each is in THIS directory (fixtures/r1_rev4/). Replaced by redraw on a heuristic's outcome (ruling R-1 withdrawn) or by a design defect of the second audit (docs/reviews/m0-lineage-decision-2026-11-25/audit2_r1/).", "",
             "old shape -> revision-4 shape"]
    lines += [f"{old} -> {new}" for new, old in sorted(REPLACES.items(), key=lambda kv: kv[1])]
    lines += ["", "Earlier superseded shapes (listed in fixtures/r1_pilot/SUPERSEDED.txt) stay superseded.", "Tables: manifests/r1_rev4_two_sided.md replaces manifests/r1_two_sided_table.md for the registered set; the earlier tables are kept unchanged."]
    (out / "SUPERSEDED.txt").write_text("\n".join(lines) + "\n")
    ct = v2.cluster_table_v2(v2.registered_v2())
    man = {
        "note": "Revision-4 shapes of R1 (second audit, lead rulings R-1..R-9). Self-checked only: not independent review, not Astra validation, not human approval. Nothing is in core.REGISTRY; no second solver exists; no part is assigned.",
        "shapes": {x.id: {"family": x.family, "replaces": REPLACES[x.id], "cluster": v2.cluster_of_v2(x.id), "file": f"studies/m0/lineages_r1_{x.build.__module__.rsplit('lineages_r1_', 1)[1]}.py", "signature": lg.signature(x.build),
                          "fixture": f"studies/m0/fixtures/r1_rev4/{x.id}.jsonl", "fixture_sha256": hashes[x.id], "not_registered": v2.NOT_REGISTERED_V2.get(x.id)} for x in lins},
        "not_registered": v2.NOT_REGISTERED_V2,
    }
    (MAN / "r1_rev4_manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
    cm = {
        "n_shapes": sum(len(v) for v in ct.values()), "n_clusters": len(ct),
        "clusters": {cid: sorted(m.id for m in ms) for cid, ms in sorted(ct.items())},
        "strict_merges": [list(g) for g in v2.STRICT_MERGES_V2],
        "borderline_not_merged": [{"a": a, "b": b, "auditor_reason": why} for a, b, why in v2.BORDERLINE],
        "author_notes": [{"merge": m, "who": w, "note": n} for m, w, n in v2.AUTHOR_NOTES],
        "source": "docs/reviews/m0-lineage-decision-2026-11-25/audit2_r1/AUDIT_M0_R1_2.md section 1 (primary strict, 27) and my_clusters.py (BORDER list, strictest 14); ruling R-2 of LEAD_RULINGS_2.md",
    }
    (MAN / "r1_clusters_v2.json").write_text(json.dumps(cm, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(lins)} fixtures, {len(ct)} clusters")


if __name__ == "__main__":
    main()
