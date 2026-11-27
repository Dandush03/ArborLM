# ruff: noqa: E501
"""The split of the strict clusters of R1 into parts A and B under each reading the second audit tabulates (ruling R-6). This script REPORTS; it does not choose (the choice is the human lead's).

Readings (all use the registered rule of ``core.family_partition``: sorted keys shuffled with ``stream(400004, "family-partition", "R1")``, the first half is part A):
  literal             the keys are the families as written; a cluster whose members are in families of both parts straddles (the words of ADR-0033 section 6.4, "splits the families", read literally);
  family_closure      families joined by a strict cluster are ONE key (the earlier author's reading; no cluster straddles; imbalance is the price);
  cluster_keys        the clusters themselves are the keys (not the registered unit; no cluster straddles; families are split across parts);
  literal_move_to_B   the literal split, then every straddling cluster is moved whole to part B (the earlier author's alternative; families are then split across parts).
Run: ``uv run --locked --offline python -m studies.m0.r1_rev4_parts`` (writes studies/m0/manifests/r1_rev4_parts.json and .md).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from studies.m0 import lineages_r1_clusters_v2 as v2

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "studies/m0/manifests"


def analyse() -> dict[str, Any]:
    lins = v2.registered_v2()
    ct = v2.cluster_table_v2(lins)
    readings = v2.partition_readings(lins)
    out: dict[str, Any] = {"n_lineages": len(lins), "n_clusters": len(ct), "readings": {}}
    for name, pmap in readings.items():
        wholly_a, wholly_b, both = [], [], []
        for cid, members in sorted(ct.items()):
            ps = {pmap[m.id] for m in members}
            (both if len(ps) == 2 else (wholly_a if ps == {"A"} else wholly_b)).append(cid)
        keys = sorted({x.family for x in lins}) if name in ("literal", "literal_move_to_B") else (sorted(set(v2.family_groups_v2(lins).values())) if name == "family_closure" else sorted(ct))
        out["readings"][name] = {
            "keys": len(keys),
            "lineages_A": sum(1 for v in pmap.values() if v == "A"), "lineages_B": sum(1 for v in pmap.values() if v == "B"),
            "clusters_wholly_A": len(wholly_a), "clusters_wholly_B": len(wholly_b), "clusters_in_both_parts": len(both),
            "wholly_A": wholly_a, "wholly_B": wholly_b,
            "in_both": {cid: {m.id: pmap[m.id] for m in ct[cid]} for cid in both},
            "families_split_across_parts": sorted({x.family for x in lins if len({pmap[y.id] for y in lins if y.family == x.family}) > 1}),
        }
    return out


def markdown(res: dict[str, Any]) -> str:
    lines = ["# R1: the split of the strict clusters under each partition reading (ruling R-6; REPORTED, NOT CHOSEN)", "",
             f"{res['n_clusters']} strict clusters ({res['n_lineages']} registered shapes in the revision-4 set). Rule for every reading: sorted keys shuffled with stream(400004, \"family-partition\", \"R1\"), first half A. "
             "Whether a held-out part may contain a cluster whose procedure also sits in the teaching part is a question for the human lead (ruling R-7).", "",
             "| reading | keys | shapes A / B | clusters wholly A | wholly B | in BOTH parts | families split across parts |", "|---|---|---|---|---|---|---|"]
    for name, r in res["readings"].items():
        lines.append(f"| {name} | {r['keys']} | {r['lineages_A']} / {r['lineages_B']} | {r['clusters_wholly_A']} | {r['clusters_wholly_B']} | {r['clusters_in_both_parts']} | {len(r['families_split_across_parts'])} |")
    for name, r in res["readings"].items():
        lines += ["", f"## {name}", "", f"- wholly A ({r['clusters_wholly_A']}): {', '.join(c.removeprefix('R1.') for c in r['wholly_A'])}", f"- wholly B ({r['clusters_wholly_B']}): {', '.join(c.removeprefix('R1.') for c in r['wholly_B'])}"]
        if r["in_both"]:
            lines.append(f"- in BOTH parts ({r['clusters_in_both_parts']}):")
            for cid, mem in r["in_both"].items():
                lines.append(f"  - {cid.removeprefix('R1.')}: " + ", ".join(f"{m.removeprefix('R1.')} ({p})" for m, p in mem.items()))
        else:
            lines.append("- in BOTH parts: none")
        if r["families_split_across_parts"]:
            lines.append(f"- families with shapes in both parts: {', '.join(r['families_split_across_parts'])}")
    return "\n".join(lines) + "\n"


def main() -> None:
    res = analyse()
    (OUT / "r1_rev4_parts.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    (OUT / "r1_rev4_parts.md").write_text(markdown(res))
    print(markdown(res))


if __name__ == "__main__":
    main()
