# ruff: noqa
"""Final R1 audit: compare the stored key with solvers_final (text only) on n items per shape and level at seed base B.
usage: python check_keys_final.py <n> <B> <out.jsonl>   (prints per-shape counts; writes every mismatch / ambiguous / parse error)"""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fgen, solvers_final as SV
n, B, outp = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
L = fgen.lineages()
assert sorted(L) == sorted(SV.SOLVERS), (sorted(L), sorted(SV.SOLVERS))
h = hashlib.sha256()
tot = {}
with open(outp, "w") as fo:
    for lid in sorted(L):
        row = []
        for lv in range(7):
            c = {"n": 0, "agree": 0, "mismatch": 0, "ambiguous": 0, "parse": 0}
            for i, b in enumerate(fgen.items(L[lid], lv, n, B)):
                h.update(b.question.encode()); h.update(b"\0"); h.update(b.answer.encode()); h.update(b"\1")
                c["n"] += 1
                try:
                    a, st = SV.SOLVERS[lid](b.question)
                except SV.ParseError as e:
                    c["parse"] += 1
                    fo.write(json.dumps({"lineage": lid, "level": lv, "i": i, "kind": "parse", "err": str(e), "q": b.question, "key": b.answer}) + "\n")
                    continue
                if st != "ok":
                    c["ambiguous"] += 1
                    fo.write(json.dumps({"lineage": lid, "level": lv, "i": i, "kind": "ambiguous", "why": st, "q": b.question, "key": b.answer}) + "\n")
                elif a == b.answer:
                    c["agree"] += 1
                else:
                    c["mismatch"] += 1
                    fo.write(json.dumps({"lineage": lid, "level": lv, "i": i, "kind": "mismatch", "mine": a, "q": b.question, "key": b.answer}) + "\n")
            row.append(c)
        tot[lid] = row
        s = {k: sum(r[k] for r in row) for k in row[0]}
        print(f"{lid:38s} n={s['n']} agree={s['agree']} mismatch={s['mismatch']} ambiguous={s['ambiguous']} parse={s['parse']}  per-level mismatch={[r['mismatch'] for r in row]} amb={[r['ambiguous'] for r in row]}", flush=True)
print("digest", h.hexdigest())
json.dump(tot, open(outp + ".counts.json", "w"), indent=1)
