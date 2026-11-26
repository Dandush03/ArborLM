"""Apply solver2_r2a to the fixtures; write answers_r2a.jsonl; run self-checks."""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver2_r2a as S

F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R2/"
FMT = {
    "R2.caesar_shift": r"[a-z]+( [a-z]+)*",
    "R2.cellular_automaton": r"[01]+",
    "R2.cheapest_network": r"0|[1-9]\d*",
    "R2.count_divisible": r"0|[1-9]\d*",
    "R2.crt_smallest": r"[1-9]\d*",
    "R2.expression_eval": r"0|-?[1-9]\d*",
    "R2.from_base": r"0|[1-9]\d*",
}
out = []
problems = []
stats = collections.Counter()
for lin in S.SOLVERS:
    for line in open(F + lin + "/fixtures.jsonl"):
        r = json.loads(line)
        q, s = r["question"], r["structured"]
        try:
            a = S.SOLVERS[lin](q, s)
        except Exception as e:  # keep going, record
            problems.append((r["id"], r["level"], r["index"], "EXC %r" % e)); a = None
        # cross-check structured vs text
        try:
            p = S.PARSERS[lin](q)
            if p != s:
                problems.append((r["id"], r["level"], r["index"], "PARSE MISMATCH %r vs %r" % (p, s)))
            elif a is not None and S.SOLVERS[lin](q, p) != a:
                problems.append((r["id"], r["level"], r["index"], "TEXT-ANSWER MISMATCH"))
        except Exception as e:
            problems.append((r["id"], r["level"], r["index"], "PARSE EXC %r" % e))
        if a is not None:
            if lin == "R2.binary_search_trace":
                pat = r"-?\d+(, -?\d+)*" if s["ask"] == "values" else r"0|[1-9]\d*"
            elif lin == "R2.dictionary_rank":
                pat = "[a-z]{%d}" % s["length"] if s["ask"] == "word" else r"[1-9]\d*"
            else:
                pat = FMT[lin]
            if not re.fullmatch(pat, a):
                problems.append((r["id"], r["level"], r["index"], "FORMAT %r" % a))
            if lin == "R2.caesar_shift" and len(a.split()) != len(s["text"].split()):
                problems.append((r["id"], r["level"], r["index"], "WORDCOUNT"))
            if lin == "R2.cellular_automaton" and len(a) != len(s["row"]):
                problems.append((r["id"], r["level"], r["index"], "LEN"))
            if lin == "R2.dictionary_rank" and s["length"] <= 7:
                if S.dictionary_rank_brute(s) != a:
                    problems.append((r["id"], r["level"], r["index"], "BRUTE MISMATCH"))
                stats["dict_brute_checked"] += 1
            if lin == "R2.crt_smallest":
                x = int(a)
                ok = all(x % n == rr % n for rr, n in s["congruences"])
                smaller = any(all(y % n == rr % n for rr, n in s["congruences"]) for y in range(1, min(x, 10**6)))
                if not ok or (x <= 10**6 and smaller):
                    problems.append((r["id"], r["level"], r["index"], "CRT BRUTE"))
                stats["crt_brute_checked"] += 1
        stats[lin] += 1
        out.append({"id": r["id"], "level": r["level"], "index": r["index"], "answer": a})
with open(os.path.join(HERE, "answers_r2a.jsonl"), "w") as f:
    for o in out:
        f.write(json.dumps(o) + "\n")
print("items per lineage:", dict((k, v) for k, v in stats.items() if k.startswith("R2.")))
print("other:", dict((k, v) for k, v in stats.items() if not k.startswith("R2.")))
print("problems:", len(problems))
for p in problems:
    print(p)
