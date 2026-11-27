"""(v2: v1 double-counted every heredoc write; this version counts each write once) Pair audit: in each solver author's transcript, find files written more than once (heredoc `cat > path`, `open(path, "w")`,
Write/Edit tool) - an in-place rewrite of an existing file, which the brief's keep-files rule forbids. Approximate (pattern based)."""
import json, re, collections
P = "/Users/daniellaloush/.claude/projects/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/subagents"
AUTH = {"r1": "a0a39fa7049de297d", "r2a": "ac3245ec6b3bff4d9", "r2b": "a97587d8e6861f387", "m1a": "a90da052935dbd22d",
        "m1b": "a81e926c35707d9b4", "m1c": "a731dc5ec95fae7c2", "c1": "a5304ab5549718b32"}
for name, aid in AUTH.items():
    w = collections.Counter()
    for line in open(f"{P}/agent-{aid}.jsonl"):
        r = json.loads(line)
        if r.get("type") != "assistant":
            continue
        for b in r["message"].get("content", []):
            if b.get("type") != "tool_use":
                continue
            inp = b["input"]
            if b["name"] in ("Write", "Edit"):
                w[inp.get("file_path")] += 1
            cmd = inp.get("command", "")
            for m in re.findall(r"cat >\s*(\S+)\s*<<", cmd):
                w[m] += 1
            for m in re.findall(r"open\(\s*(p|['\"][^'\"]+['\"])\s*,\s*['\"]w['\"]", cmd):
                if m == "p":
                    pm = re.findall(r"^p\s*=\s*['\"]([^'\"]+)['\"]", cmd, re.M)
                    m = pm[-1] if pm else "p?"
                w[m.strip("'\"")] += 1
            # v2: plain redirections only, excluding the `cat > X <<` heredocs counted above (v1 counted those twice)
            for m in re.findall(r"(?<![>])(?<!cat )>\s*(\$\w+/[\w.]+|/\S+\.(?:md|py|out|jsonl|txt))(?!\s*<<)", cmd):
                w[m] += 1
    rep = {k: v for k, v in w.items() if v > 1}
    print(f"{name}: files written {len(w)}; written more than once: {rep}")
