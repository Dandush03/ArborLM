# ruff: noqa
# ruff: noqa
"""Per-part cluster counts from the auditor's pair judgement (pairs.py) and the parts in parts.txt.
Also simulates core.family_partition over the 16-family union (read-only import). Usage: python per_part.py <scratch> <agent worktree>"""
import sys, re, importlib.util
S, W = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("pairs", S + "/pairs.py")
sys.argv = ["pairs.py", S + "/pairs_judgement_tmp.csv"]
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
part = {}
for line in open(S + "/parts.txt"):
    m = re.match(r"(OLD|NEW) R1\.(\w+) (?:(\w+) )?([AB])$", line.strip())
    if m: part[m.group(2)] = m.group(4)
assert len(part) == 35
for label, edges in (("strict", list(P.BOTH) + list(P.STRICT)), ("lenient", list(P.BOTH))):
    cs = P.clusters(edges, P.ALL)
    for p in "AB":
        inside = [c for c in cs if all(part[x] == p for x in c)]
        touching = [c for c in cs if any(part[x] == p for x in c)]
        print(f"{label} part {p}: lineages={sum(v==p for v in part.values())} clusters wholly in part={len(inside)} clusters touching part={len(touching)}")
    print(f"  {label} cross-part clusters:", [" + ".join(f'{x}({part[x]})' for x in c) for c in cs if len({part[x] for x in c}) > 1])
sys.path.insert(0, W)
from studies.m0 import core
fams = sorted({'truth','spatial','rules','culprit','temporal','arrangement','order','kinship','tracking','conditional','graph','categories','containers','elimination','boolean_state','equivalence'})
r = core.stream(400004, 'family-partition', 'R1'); sh = fams[:]; r.shuffle(sh); half = len(sh)//2
print("family_partition rule applied to the 16-family union:", {f: ('A' if i < half else 'B') for i, f in enumerate(sh)})
