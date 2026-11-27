import json, re, sys, collections
F = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R2"
L = ["grid_sum","list_ops","luhn_check","min_heap_ops","run_length","sort_list","string_rewrite_nonidentity","to_base_wide"]
for l in L:
    c = collections.Counter(); keys = collections.Counter(); extra = collections.Counter()
    n = 0
    for line in open(f"{F}/R2.{l}/fixtures.jsonl"):
        it = json.loads(line); n += 1
        q = it["question"]
        t = re.sub(r"'[a-z]*'", "'S'", q)
        t = re.sub(r"-?\d+", "N", t)
        t = re.sub(r"\b[a-z]{2,}\b", lambda m: m.group(0) if m.group(0) in WORDS else "W", t) if False else t
        if l in ("run_length","string_rewrite_nonidentity"):
            t = re.sub(r"(Compress|string) [a-z]+([ .])", r"\1 STR\2", t)
        if l == "grid_sum":
            t = re.sub(r"(N ?)+(/ (N ?)+)*", "ROWS ", t)
            extra[it["structured"]["what"].replace("0","N").replace("1","N").replace("2","N").replace("3","N").replace("4","N").replace("5","N").replace("6","N").replace("7","N").replace("8","N").replace("9","N")] += 1
        if l == "list_ops":
            m = re.search(r"in order: (.*?)\. What", q)
            for p in m.group(1).split("; "):
                extra[re.sub(r"-?\d+","N",p)] += 1
            t = re.sub(r"in order: .*?\. What", "in order: OPS. What", t)
            for o in it["structured"]["ops"]: keys[o[0]] += 1
        if l == "string_rewrite_nonidentity":
            m = re.search(r"starts: (.*?)\. What", q)
            for p in m.group(1).split("; "):
                extra[re.sub(r"'[a-z]*'","'S'",p)] += 1
            t = re.sub(r"starts: .*?\. What", "starts: RULES. What", t)
        t = re.sub(r"(N, )+N", "LIST", t)
        c[t] += 1
        keys[tuple(sorted(it["structured"].keys()))] += 1
        if l == "luhn_check": extra[it["structured"]["ask"]] += 1
        if l == "sort_list": extra[it["structured"]["desc"]] += 1
        if l == "to_base_wide": extra[it["structured"]["base"]] += 1
        if l == "min_heap_ops": extra[it["structured"]["removals"]] += 1
    print("=====", l, n)
    for t, k in c.most_common(): print(k, "|", t)
    print("keys", dict(keys)); print("extra", dict(extra))
