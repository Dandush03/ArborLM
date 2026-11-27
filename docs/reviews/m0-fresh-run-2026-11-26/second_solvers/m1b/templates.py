"""Enumerate distinct question templates per lineage (digits masked, intro sentence and names masked)."""
import json, re, sys, collections
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/M1"
LIN = sys.argv[1:]
INTRO = [
    (re.compile(r"^[A-Z][a-z]+ of [A-Z][a-z]+ wrote this problem for a maths club\. "), "<INTRO:X of P wrote>"),
    (re.compile(r"^At a maths club in [A-Z][a-z]+, [A-Z][a-z]+ is asked this\. "), "<INTRO:At a maths club in P>"),
    (re.compile(r"^This problem comes from a quiz held in [A-Z][a-z]+, set by [A-Z][a-z]+\. "), "<INTRO:quiz held in P>"),
    (re.compile(r"^[A-Z][a-z]+ from [A-Z][a-z]+ found this problem in a puzzle book\. "), "<INTRO:X from P found>"),
]
for lin in LIN:
    c = collections.Counter(); intros = collections.Counter()
    for line in open(f"{F}/M1.{lin}/fixtures.jsonl"):
        d = json.loads(line); q = d["question"]
        tag = "<no intro>"
        for rx, t in INTRO:
            if rx.match(q):
                q = rx.sub("", q); tag = t; break
        intros[tag] += 1
        q = re.sub(r"-?\d+", "N", q)
        if lin == "gcd_lcm_r4":
            q = re.sub(r"^[A-Z][a-z]+ has", "X has", q); q = re.sub(r"\. [A-Z][a-z]+ cuts", ". X cuts", q)
            q = re.sub(r"(N, )+N and N", "LIST", q); q = re.sub(r"N and N", "LIST", q)
            q = re.sub(r"one flashes every N seconds(, another every N seconds)*,? (and )?(the other|the last) every N seconds", "FLASHLIST", q)
        if lin == "inclusion_exclusion_r3":
            for s in ["ride a bike","swim","paint","play chess","read comics","sing in the choir","play tennis"]:
                q = q.replace(s, "ACT")
        if lin == "grid_perimeter_r3":
            q = re.sub(r"Row N \(counting from the top\): [^.]*\. ", "", q)
        if lin == "last_digit_power_r3":
            q = re.sub(r"(N factors equal to N(, | and ))+N factors equal to N", "FLIST", q)
            q = re.sub(r"(the product of N factors, each equal to N(, | and ))+the product of N factors, each equal to N", "PLIST", q)
        if lin == "median_list_r3":
            q = re.sub(r"(N, )*N and N", "LIST", q)
        if lin == "percent_change_r3":
            q = re.sub(r"(rises|falls) by N percent(, then (rises|falls) by N percent)*", "STEPS", q)
        c[q] += 1
    print("=====", lin, dict(intros))
    for k, v in c.most_common(): print(v, "|", k)
