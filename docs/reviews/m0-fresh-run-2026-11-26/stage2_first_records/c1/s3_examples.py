# ruff: noqa
"""Stage-2 C1 audit, step 3: print example items to read (wording, levels). Reads the fixture rows only. Usage: python3 -I <this> FIXTURE_DIR LEVELS(comma) N_PER_LEVEL"""
import glob, gzip, json, os, sys
d, levels, k = sys.argv[1], [int(x) for x in sys.argv[2].split(",")], int(sys.argv[3])
for fn in sorted(glob.glob(os.path.join(d, "*.jsonl.gz"))):
    rows = [json.loads(l) for l in gzip.open(fn, "rt")]
    for lv in levels:
        for r in [x for x in rows if x["lv"] == lv][:k]:
            print(f"===== {r['id']}  key={r['key']!r}")
            print(r["q"])
