"""Apply solver2_r1.SOLVERS to the R1 fixtures; write answers_r1.jsonl."""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver2_r1 as S

D = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R1/"
FMT = {
    "R1.boolean_lights_r4": r"(yes|no)",
    "R1.categories_default_exceptions_r4": r"(yes|no)",
    "R1.compass_turns": r"(north|east|south|west)",
    "R1.conditional_threshold_rule_r4": r"(yes|no)",
    "R1.equivalence_exchange_rates_r6": r"[1-9][0-9]*",
    "R1.knights_knaves_r6": r"(knight|knave)",
    "R1.spatial_grid_walk_r5": r"[A-Z][a-z' -]*",
    "R1.swap_tracking_r5": r"[a-z][a-z' -]*",
    "R1.temporal_weekday_shift_r6": r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)",
    "R1.venn_counting_r5": r"(0|[1-9][0-9]*)",
}
out = open(os.path.join(HERE, "answers_r1.jsonl"), "w")
bad = 0
for lin in sorted(S.SOLVERS):
    n = amb = 0
    for line in open(D + lin + "/fixtures.jsonl"):
        r = json.loads(line)
        try:
            a = S.SOLVERS[lin](r["question"], r["structured"])
        except S.AmbiguousItem as e:
            a = None
            amb += 1
            print("AMBIGUOUS", lin, r["level"], r["index"], e)
        if a is not None and not re.fullmatch(FMT[lin], a):
            bad += 1
            print("BADFORMAT", lin, r["level"], r["index"], repr(a))
        out.write(json.dumps({"id": r["id"], "level": r["level"], "index": r["index"], "answer": a}) + "\n")
        n += 1
    print(lin, "items", n, "ambiguous", amb)
print("bad format", bad)
