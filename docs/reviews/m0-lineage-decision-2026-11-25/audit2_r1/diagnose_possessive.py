# ruff: noqa
"""Confirm: in temporal_critical_path the key often appears only in possessive form, which the author's _valid tokeniser
([A-Za-z']+) reads as 'Name's' and so drops from the option set."""
import gzip, json, os, re, sys
d = sys.argv[1]
rows = [json.loads(x) for x in gzip.open(os.path.join(d, "temporal_critical_path.reg.jsonl.gz"), "rt")]
bare = sum(1 for r in rows if r["a"] in re.findall(r"[A-Za-z']+", r["q"]))
print(f"key appears as a bare token (author tokeniser): {bare}/{len(rows)}; only possessive: {len(rows)-bare}/{len(rows)}")
