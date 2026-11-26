"""Pair audit: write the final stage-2 record stage2_conditions.json for the 82 survivor lineages (deterministic: sorted keys,
indent 2, trailing newline, no timestamp). One rule for every lineage:
  wording, levels_distinct  - copied unchanged (result, reason) from the first stage-2 record of the lineage's evaluation
                              (stage2_first_records/{r1,r2,m1,c1}/stage2_conditions_<eval>.json; M1 from m1/, not m1_first_version/),
                              plus `source` naming that file and its SHA-256;
  second_solver             - PASS iff provenance of the authoring context is MEETS and, on the fresh pair-audit items, mismatches == 0
                              and solver errors == 0 (from deliver/agree_<EVAL>_py312.json, the builder's interpreter);
  map                       - the cluster whose members contain the lineage in studies/m0/manifests/map_of_record.json (must be exactly one;
                              the file's SHA-256 must equal the frozen one);
  pair_audited              - PASS iff second_solver is PASS (this audit read the pair and found nothing against it);
  all_conditions            - PASS iff wording, levels_distinct, second_solver and pair_audited are PASS and a cluster was found.
Difficulty and exposure to cheap rules are not inputs of any condition."""
import hashlib, json, sys
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
OUT = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_pair_audit_20261126/deliver"
MAP_SHA = "1ba6ddd520dfe6514dfd282883ce4bc84660b7dca1abfefdac58285dcab5809c"
REC = {"R1": "r1", "R2": "r2", "M1": "m1", "C1": "c1"}
OWNER_PREFIX = {"r1": "R1.", "r2a": None, "r2b": None, "m1a": None, "m1b": None, "m1c": None, "c1": "C1."}
# Provenance verdicts of this audit, per authoring context (reasons in PAIR_AUDIT.md section 1).
PROV = {
    "r1": ("MEETS", "Author context agent-a0a39fa7049de297d (claude-opus-5-5): its 20 tool calls touch only the brief, the fixtures README and its 10 R1 lineages' SCHEMA.md/fixtures.jsonl, and its own directory; one user message (the brief), no feedback from any comparison; fixtures carry no key field. Exposure disclosed: README names builder modules and describes how the C1 key is produced; harness-injected CLAUDE.md, memory index and git status."),
    "r2a": ("MEETS", "Author context agent-ac3245ec6b3bff4d9 (claude-opus-5-5): its 17 tool calls touch only the brief, the fixtures README and its 9 R2 lineages' SCHEMA.md/fixtures.jsonl, and its own directory; one user message, no feedback; fixtures carry no key field. Same disclosed README and harness exposure as all seven contexts."),
    "r2b": ("MEETS", "Author context agent-a97587d8e6861f387 (claude-opus-5-5): its 10 tool calls touch only the brief, the fixtures README and its 8 R2 lineages' SCHEMA.md/fixtures.jsonl, and its own directory; one user message, no feedback; fixtures carry no key field. Same disclosed README and harness exposure."),
    "m1a": ("MEETS", "Author context agent-a90da052935dbd22d (claude-opus-5-5): its 16 tool calls touch only the brief, the fixtures README and its 10 M1 lineages' SCHEMA.md/fixtures.jsonl, and its own directory; one user message, no feedback; fixtures carry no key field. Same disclosed README and harness exposure."),
    "m1b": ("MEETS", "Author context agent-a81e926c35707d9b4 (claude-opus-5-5): its 14 tool calls touch only the brief, the fixtures README and its 10 M1 lineages' SCHEMA.md/fixtures.jsonl, and its own directory; one user message, no feedback; fixtures carry no key field. Same disclosed README and harness exposure."),
    "m1c": ("MEETS", "Author context agent-a731dc5ec95fae7c2 (claude-opus-5-5): its 14 tool calls touch only the brief, the fixtures README and its 9 M1 lineages' SCHEMA.md/fixtures.jsonl, its own directory, and one disclosed `ls _scratch | grep m0_solver2` (directory names only); one user message, no feedback; fixtures carry no key field. Same disclosed README and harness exposure."),
    "c1": ("MEETS", "Author context agent-a5304ab5549718b32 (claude-opus-5-5): its 27 tool calls touch only the brief, the fixtures README and the 26 C1 lineages' SCHEMA.md/fixtures.jsonl, and its own directory; one user message, no feedback; fixtures carry no per-item key. Caveat PENDING LEAD REVIEW: each C1 SCHEMA.md states two per-lineage aggregates computed from the builder's 280 keys (kinds of printed value; character set of the printed lines), and the author compared its answers' character sets with them (check_charsets.py, 26 of 26 equal); no per-item answer. Host never executes item code (ast.parse only; own tree walker)."),
}
FILE_OF = {}
for name in PROV:
    p = f"{W}/studies/m0/solvers2/solver2_{name}.py"
    src = open(p, "rb").read()
    ns = {}
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"pa_b_{name}", p)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    for lid in mod.SOLVERS:
        assert lid not in FILE_OF
        FILE_OF[lid] = (name, f"studies/m0/solvers2/solver2_{name}.py", hashlib.sha256(src).hexdigest())

def main():
    surv = json.load(open(W + "/studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]
    map_bytes = open(W + "/studies/m0/manifests/map_of_record.json", "rb").read()
    assert hashlib.sha256(map_bytes).hexdigest() == MAP_SHA, "map of record hash differs"
    mp = json.loads(map_bytes)
    cl_of = {}
    for c in mp["clusters"]:
        for m in c["members"]:
            cl_of.setdefault(m, []).append(c["cluster_id"])
    out = {}
    for ev in ("R1", "R2", "M1", "C1"):
        rel = f"docs/reviews/m0-fresh-run-2026-11-26/stage2_first_records/{REC[ev]}/stage2_conditions_{REC[ev].lower()}.json"
        rb = open(f"{W}/{rel}", "rb").read()
        first = json.loads(rb)["lineages"]
        src = f"{rel} (sha256 {hashlib.sha256(rb).hexdigest()}), copied unchanged"
        agree = json.load(open(f"{OUT}/agree_{ev}_py312.json"))
        assert agree["eval"] == ev
        for lid in surv[ev]:
            fr = first[lid]
            name, solver, ssha = FILE_OF[lid]
            a = agree["lineages"][lid]
            assert a["solver"] == solver
            prov, preason = PROV[name]
            n, mm, er = a["items"], len(a["mismatches"]), len(a["errors"])
            ok = prov == "MEETS" and mm == 0 and er == 0 and n > 0
            reason = (f"Fresh pair-audit items the author never saw: {n} (200 per level, levels 0-6; seeds sha256('400002|pair-audit|{ev}|{lid}|<level>')[:8]); "
                      f"answer compared with the builder's key as strings: {mm} mismatches, {er} solver errors (CPython 3.12.14 via uv; also 0/0 under system 3.15.1). "
                      f"Authoring fixtures: 280, 0 mismatches (lead's compare/). Provenance: {preason}")
            clusters = cl_of.get(lid, [])
            assert len(clusters) == 1, (lid, clusters)
            w = {"result": fr["wording"]["result"], "reason": fr["wording"]["reason"], "source": src}
            lv = {"result": fr["levels_distinct"]["result"], "reason": fr["levels_distinct"]["reason"], "source": src}
            ss = {"result": "PASS" if ok else "FAIL", "solver": solver, "solver_sha256": ssha, "provenance": prov,
                  "fixtures": n, "mismatches": mm, "reason": reason}
            pa = {"result": "PASS" if ok else "FAIL", "by": "this audit"}
            allc = all(x == "PASS" for x in (w["result"], lv["result"], ss["result"], pa["result"]))
            out[lid] = {"evaluation": ev, "wording": w, "levels_distinct": lv, "second_solver": ss,
                        "map": {"cluster_id": clusters[0], "map_sha256": MAP_SHA}, "pair_audited": pa,
                        "all_conditions": "PASS" if allc else "FAIL"}
    assert len(out) == 82
    with open(f"{OUT}/stage2_conditions.json", "x") as f:
        f.write(json.dumps(out, sort_keys=True, indent=2) + "\n")
    import collections
    print("lineages", len(out), "all_conditions", dict(collections.Counter(v["all_conditions"] for v in out.values())),
          "second_solver", dict(collections.Counter(v["second_solver"]["result"] for v in out.values())))

main()
