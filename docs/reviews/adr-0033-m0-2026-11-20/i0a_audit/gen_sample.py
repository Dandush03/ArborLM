# ruff: noqa
# ruff: noqa
"""M0-I0a audit: draw 20 items per chosen lineage from the rehearsal's OPEN development pools
(never the sealed directory). Seeded by the auditor (random.Random('m0-i0a-audit')).
Usage: python3 -I gen_sample.py REHEARSAL_OPEN_DIR OUT.jsonl
"""
import json, random, sys

CHOSEN = {
    "R1": ["R1.knights_knaves", "R1.seating_row", "R1.categories_follow"],
    "R2": ["R2.to_base", "R2.permutation_power", "R2.string_rewrite"],
    "M1": ["M1.linear_equation", "M1.percent_change", "M1.clock_duration"],
    "C1": ["C1.func_compose", "C1.bubble_pass", "C1.string_methods"],
}
src, out = sys.argv[1], sys.argv[2]
rng = random.Random("m0-i0a-audit")
rows = []
for ev, lins in CHOSEN.items():
    for part in ("A", "B"):
        path = f"{src}/{ev}_{part}_development.jsonl"
        by = {}
        for line in open(path):
            r = json.loads(line)
            if r["lineage"] in lins:
                by.setdefault(r["lineage"], []).append(r)
        for lin in sorted(by):
            pick = rng.sample(by[lin], 20)
            rows.extend(pick)
with open(out, "w") as fh:
    for r in rows:
        fh.write(json.dumps(r, sort_keys=True) + "\n")
print(len(rows), "items")
