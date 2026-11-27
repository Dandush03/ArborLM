"""Enumerate distinct sentence templates per lineage (names, numbers, words masked)."""
import json, re, sys
from collections import Counter
D = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R1/"
lin = sys.argv[1]
vocab = set()
rows = [json.loads(l) for l in open(D + lin + "/fixtures.jsonl")]
def strings(o):
    if isinstance(o, str): yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield k; yield from strings(v)
    elif isinstance(o, list):
        for v in o: yield from strings(v)
for r in rows:
    for x in strings(r["structured"]):
        for part in x.split("|"):
            if part and part not in ("yes","no","abstain","walk","turn","swap","rotate","left","right","around","north","south","east","west") and not part.startswith(("cw","ccw")):
                vocab.add(part)
vocab = sorted(vocab, key=len, reverse=True)
pat = re.compile("|".join(re.escape(v) for v in vocab)) if vocab else None
C = Counter()
for r in rows:
    q = r["question"]
    if pat: q = pat.sub("X", q)
    q = re.sub(r"-?\d+", "N", q)
    sents = re.split(r'(?<=[.?])\s+(?=[A-Z"])', q)
    for s in sents:
        s = re.sub(r"(X, )+X", "X..", s)
        s = re.sub(r"(N, )+N", "N..", s)
        s = re.sub(r"(, then (turn N degrees (counter)?clockwise|turn (left|right|around)|walk N steps?))+", ", then ...", s)
        s = re.sub(r"(, then (north|south|east|west))+", ", then ...", s)
        C[s] += 1
for s, n in sorted(C.items(), key=lambda t: -t[1]):
    print(n, "|", s)
