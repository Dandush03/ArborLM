"""Pair audit, provenance: read the seven solver authors' session transcripts (Claude Code subagent JSONL files of the lead's session)
and list every tool call each author made (tool, path or command), the model recorded on its assistant messages, and flag any call
that touches something the brief forbade: the repository/worktrees (studies/, tests/, docs/, src/, AGENTS.md, CLAUDE.md, git),
the keys tree, the fixtures-impl tree, other m0_fr_* / _scratch directories, other evaluations' or other lineages' fixtures.
Also scans every tool RESULT the author received for generator/first-solver/keys markers. Prints a per-author summary and every flag."""
import json, re, sys, collections
P = "/Users/daniellaloush/.claude/projects/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/subagents"
AUTH = {"r1": "a0a39fa7049de297d", "r2a": "ac3245ec6b3bff4d9", "r2b": "a97587d8e6861f387", "m1a": "a90da052935dbd22d",
        "m1b": "a81e926c35707d9b4", "m1c": "a731dc5ec95fae7c2", "c1": "a5304ab5549718b32"}
FORBID = [r"/studies/", r"/tests/", r"/docs/", r"/src/arborlm", r"AGENTS\.md", r"CLAUDE\.md", r"\bgit\b", r"m0_second_solver_keys",
          r"m0_second_solver_fixtures_impl", r"\.claude/worktrees", r"m0_fr_(?!briefs_20261126/SOLVER2\.md)", r"/MEMORY\.md", r"/memory/",
          r"_scratch/(?!m0_second_solver_fixtures_20261126|m0_solver2_|m0_fr_briefs_20261126/SOLVER2\.md)"]
RESULT_MARK = [r"def build_item", r"def draw_items", r"\"key\":", r"run_inprocess\(", r"def c1_trace", r"from studies\.m0", r"import studies",
               r"keys\.jsonl\"?\s*:", r"ANSWER:", r"\bans=", r"lineages_[a-z0-9_]+\.py:\d+"]
own_lineages = {}
for name, aid in AUTH.items():
    first = None; calls = []; models = collections.Counter(); flags = []; rflags = collections.Counter()
    for line in open(f"{P}/agent-{aid}.jsonl"):
        r = json.loads(line)
        if r.get("type") == "user":
            c = r["message"]["content"]
            if first is None:
                first = c if isinstance(c, str) else json.dumps(c)
            if isinstance(c, list):
                for b in c:
                    if b.get("type") == "tool_result":
                        txt = json.dumps(b.get("content"))
                        for m in RESULT_MARK:
                            if re.search(m, txt):
                                rflags[m] += 1
        elif r.get("type") == "assistant":
            msg = r["message"]; models[msg.get("model")] += 1
            for b in msg.get("content", []):
                if b.get("type") == "tool_use":
                    inp = b["input"]
                    s = inp.get("command") or inp.get("file_path") or inp.get("path") or inp.get("pattern") or json.dumps(inp)
                    if b["name"] in ("Grep", "Glob"):
                        s = json.dumps(inp)
                    calls.append((b["name"], s))
    lins = sorted(set(re.findall(r"\b((?:R1|R2|M1|C1)\.[a-z0-9_]+)", first or "")))
    print(f"==== {name} (agent-{aid}): models {dict(models)}; tool calls {len(calls)}; lineages named in its brief: {len(lins)}")
    for tool, s in calls:
        hit = [f for f in FORBID if re.search(f, s)]
        # other lineages' fixture dirs
        for m in re.findall(r"m0_second_solver_fixtures_20261126/(R1|R2|M1|C1)/((?:R1|R2|M1|C1)\.[a-z0-9_]+)", s):
            if lins and m[1] not in lins:
                hit.append("other lineage " + m[1])
        for m in re.findall(r"m0_second_solver_fixtures_20261126/(R1|R2|M1|C1)\b", s):
            if lins and not any(l.startswith(m + ".") for l in lins):
                hit.append("other evaluation " + m)
        if hit:
            flags.append((tool, s[:400], hit))
    print(f"  flagged calls: {len(flags)}")
    for tool, s, hit in flags:
        print(f"   FLAG {tool}: {s!r} -> {hit}")
    print(f"  tool RESULTS containing markers (marker: count): {dict(rflags)}")
