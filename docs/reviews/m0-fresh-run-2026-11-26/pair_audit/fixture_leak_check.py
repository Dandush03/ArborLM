"""Pair audit: fixtures carry no answer. For every authoring fixture item: (a) fields of the line; (b) is the builder key equal
(as a string) to any scalar leaf of `structured`, and if so does that leaf value also appear in the question text (a stated input);
(c) per lineage, scalar leaves of `structured` whose string form never appears in the question text (possible hidden information).
Reads fixtures and keys trees only. Standard library only."""
import json, glob, collections, re, sys
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126"
K = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_keys_20261126"

def leaves(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from leaves(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from leaves(v, f"{path}[]")
    else:
        yield path, o

tot_eq = collections.Counter(); eq_not_in_text = collections.Counter(); hidden = collections.defaultdict(collections.Counter)
n = 0
for p in sorted(glob.glob(F + "/*/*/fixtures.jsonl")):
    ev, lid = p.split("/")[-3:-1]
    if ev == "C1":
        continue  # C1 structured is the program tree; handled separately below
    keys = {(r["level"], r["index"]): r["key"] for r in map(json.loads, open(f"{K}/{ev}/{lid}/keys.jsonl"))}
    for line in open(p):
        r = json.loads(line); n += 1
        q = r["question"]; key = keys[(r["level"], r["index"])]
        for path, v in leaves(r["structured"]):
            s = str(v) if not isinstance(v, bool) else str(v)
            if s == key:
                tot_eq[lid] += 1
                if not re.search(r"(?<![\w.])" + re.escape(s) + r"(?![\w])", q):
                    eq_not_in_text[(lid, path)] += 1
            if isinstance(v, str) and v and v not in q:
                hidden[lid][path] += 1
            elif isinstance(v, (int, float)) and not isinstance(v, bool) and not re.search(r"(?<!\d)" + re.escape(str(v)) + r"(?!\d)", q.replace(",", "")):
                hidden[lid][path] += 1
print("non-C1 items", n)
print("items x leaves where a structured leaf equals the key (string), per lineage:", dict(tot_eq))
print("... of which the leaf value does not appear in the question text:", {f"{a}{b}": c for (a, b), c in eq_not_in_text.items()})
print("scalar leaves whose value does not appear literally in the question text (lineage: path: count):")
for lid in sorted(hidden):
    print(" ", lid, dict(hidden[lid]))
# C1: key vs leaves of program tree, and key in source
c1 = collections.Counter(); c1n = 0
for p in sorted(glob.glob(F + "/C1/*/fixtures.jsonl")):
    lid = p.split("/")[-2]
    keys = {(r["level"], r["index"]): r["key"] for r in map(json.loads, open(f"{K}/C1/{lid}/keys.jsonl"))}
    for line in open(p):
        r = json.loads(line); c1n += 1
        key = keys[(r["level"], r["index"])]
        if key in r["question"].split("What exactly")[0].split("program.", 1)[1].split("print(")[-1].split(")")[0:1]:
            c1[lid] += 1
print("C1 items", c1n, "items whose key equals the literal argument text of the last print(...) in the source (key visible in source):", dict(c1))
