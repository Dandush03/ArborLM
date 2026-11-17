"""Independent auditor recompute for P10-S2 qualification gate. Own code; imports nothing from studies/ or arborlm.
Usage: python -I recompute.py <data_dir>
"""
import json, math, sys, unicodedata
from collections import Counter

D = sys.argv[1]
Z = 1.959963984540054


def norm(t):
    t = unicodedata.normalize("NFC", t).lower()
    t = "".join(c for c in t if not unicodedata.category(c).startswith("P"))
    return " ".join(t.split())


def chrf(h, r, N=6, beta=2.0):
    h = "".join(norm(h).split()); r = "".join(norm(r).split())
    P = R = 0.0; k = 0
    for n in range(1, N + 1):
        a = Counter(h[i:i + n] for i in range(len(h) - n + 1)); b = Counter(r[i:i + n] for i in range(len(r) - n + 1))
        if a and b:
            m = sum((a & b).values()); P += m / sum(a.values()); R += m / sum(b.values()); k += 1
    if k == 0:
        return 0.0
    P /= k; R /= k
    if P + R == 0:
        return 0.0
    return (1 + beta**2) * P * R / (beta**2 * P + R)


def best(h, refs):
    return max((chrf(h, r) for r in refs), default=0.0)


def wilson(k, n, z=Z):
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - hw), min(1.0, c + hw)


rec = json.load(open(f"{D}/prefreeze_record.json"))
q = rec["qualification"]["detail"]
print("== 1. Wilson / precision / margin arithmetic from the record's counts")
for c in "AB":
    d = q[c]
    for name in ("filter_fit", "filter_check"):
        f = d[name]
        n = f["accepted"]; k = f.get("correct", round(f["precision"] * n))
        lo, hi = wilson(k, n)
        print(f"{c} {name}: n={n} k={k} prec={k/n:.4f} (rec {f['precision']:.4f}) wilson=[{lo:.4f},{hi:.4f}] (rec [{f['wilson'][0]:.4f},{f['wilson'][1]:.4f}]) share={n/500:.4f}")
    m = d["own"] - max(d["other_teacher"], d["student"])
    print(f"{c} own={d['own']:.4f} other={d['other_teacher']:.4f} student={d['student']:.4f} margin={m:.4f} (rec {d['margin']:.4f})"
          f" cond1={d['own']>=0.55} cond2={m>=0.30} check_prec>=0.90={d['filter_check']['precision']>=0.90} check_n>=150={d['filter_check']['accepted']>=150} pool>=8000={d['accepted']>=8000}")
# Wilson lower bound for all-correct n: n/(n+z^2)
nmin = next(n for n in range(1, 500) if wilson(n, n)[0] >= 0.90)
print("smallest n with all correct and Wilson LB>=0.90:", nmin)

part = json.load(open(f"{D}/bundle/partition.json"))
P = part["panels"]
print("\n== Q split checks")
for a in P:
    print(a, len(P[a]), "unique keys", len({i["key"] for i in P[a]}))
fk = {i["key"] for i in P["Q_fit"]}; ck = {i["key"] for i in P["Q_check"]}
fg = {i["group"] for i in P["Q_fit"]}; cg = {i["group"] for i in P["Q_check"]}
print("Q_fit/Q_check key overlap", len(fk & ck), "group overlap", len((fg & cg) - {-1}))
print("Q items with both refs:", sum(1 for i in P["Q_fit"] + P["Q_check"] if i["refs"].get("A") and i["refs"].get("B")))
print("key==norm(en) for all Q:", all(norm(i["en"]) == i["key"] for i in P["Q_fit"] + P["Q_check"]))
de = ("ich", "nicht", "ist", "der", "die", "das", "und", "du", "sie"); fr = ("je", "pas", "est", "le", "la", "les", "et", "tu", "vous", "il")
for c, wl in (("A", de), ("B", fr)):
    toks = Counter(w for i in P["Q_fit"] + P["Q_check"] for r in i["refs"][c] for w in norm(r).split())
    print(c, "ref top words", toks.most_common(8), "de-hits", sum(toks[w] for w in de), "fr-hits", sum(toks[w] for w in fr))

print("\n== teacher_outputs.json panels stored:", {c: sorted(v) for c, v in json.load(open(f"{D}/bundle/teacher_outputs.json")).items()})
to = json.load(open(f"{D}/bundle/teacher_outputs.json"))
print("(descriptive, NOT the gate panel) own-language chrF on stored panels:")
for t in "AB":
    for pn in ("D_cal", "D_con"):
        for c in "AB":
            s = [best(h, i["refs"][c]) for h, i in zip(to[t][pn], P[pn]) if c in i["refs"]]
            print(f"  teacher {t} on {pn} vs {c} refs: n={len(s)} mean={sum(s)/len(s):.4f}")

print("\n== 3. accepted pools")
acc = json.load(open(f"{D}/bundle/accepted.json"))
setting = {c: q[c]["filter_fit"]["setting"] for c in "AB"}
evalref = {norm(r) for pn in ("E_A", "E_B", "E_C", "E_open") for i in P[pn] for refs in i["refs"].values() for r in refs}
train_panel_keys = {i["key"] for pn in ("Q_fit", "Q_check", "D_cal", "D_con", "E_A", "E_B", "E_C", "E_open") for i in P[pn]}
for c in "AB":
    s = setting[c]; L = acc[c]
    ratios = [len(norm(x["target"]).split()) / len(norm(x["en"]).split()) for x in L]
    print(c, "n", len(L), "unique keys", len({x["key"] for x in L}), "ratio in range", sum(s["rho1"] <= r <= s["rho2"] for r in ratios),
          "min/max ratio", round(min(ratios), 3), round(max(ratios), 3), "differs from source", sum(norm(x["target"]) != norm(x["en"]) for x in L),
          "target==eval ref", sum(norm(x["target"]) in evalref for x in L), "key in any panel", sum(x["key"] in train_panel_keys for x in L),
          "key==norm(en)", sum(x["key"] == norm(x["en"]) for x in L), "newline", sum("\n" in x["target"] for x in L))
gold = {c: {i["key"] for i in part["gold_pool"][c]} for c in "AB"}
for c in "AB":
    print(c, "accepted key in own gold pool (should be 0 for no-gold sources):", sum(x["key"] in gold[c] for x in acc[c]))
sa, sb = {x["key"] for x in acc["A"]}, {x["key"] for x in acc["B"]}
sh = len(sa & sb); print("shared keys A&B", sh, "half", sh // 2, "excl+half A", len(sa) - sh + sh // 2, "B", len(sb) - sh + sh // 2,
                          "| record", rec["sufficiency_after_filter"]["available"], "shared", rec["sufficiency_after_filter"]["shared"])
print("dropped_eval_equal", rec["dropped_eval_equal"], "-> passed filter before drop", {c: len(acc[c]) + rec["dropped_eval_equal"][c] for c in "AB"})

print("\n== bank.json stream: any record carrying a target for a Q source?")
qen = {i["en"].strip() for i in P["Q_fit"] + P["Q_check"]}
dec = json.JSONDecoder(); buf = ""; pos = 0; nrec = 0; qtarget = 0; with_target = 0
with open(f"{D}/bundle/bank.json", encoding="utf-8") as fh:
    buf = fh.read(1 << 20); pos = buf.index("[") + 1; eof = False
    while True:
        while pos < len(buf) and buf[pos] in " \n\r\t,":
            pos += 1
        if pos < len(buf) and buf[pos] == "]":
            break
        try:
            obj, end = dec.raw_decode(buf, pos)
        except json.JSONDecodeError:
            more = fh.read(1 << 20)
            if not more:
                raise
            buf = buf[pos:] + more; pos = 0; continue
        pos = end; nrec += 1
        segs = obj["segments"]
        if len(segs) > obj["prompt_segments"]:
            with_target += 1
            if segs[1]["text"].strip() in qen:
                qtarget += 1
        if pos > (1 << 21):
            buf = buf[pos:] + fh.read(1 << 20); pos = 0
print("bank records", nrec, "with target", with_target, "with target and Q source", qtarget)
