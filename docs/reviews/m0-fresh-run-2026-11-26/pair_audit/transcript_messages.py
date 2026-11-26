"""Pair audit, provenance: for each solver author's transcript, count user messages that are NOT tool results after the initial brief
(mid-task messages from the lead, e.g. feedback from a comparison with keys), print their first 300 characters, and report the
timestamps of the first and last record and of the last write of solver2_<name>.py; compare with the mtime of the lead's compare outputs."""
import json, os, re
P = "/Users/daniellaloush/.claude/projects/-Users-daniellaloush-dandush03-ArborLM--claude-worktrees-arborlm-consolidation-experiment-2b31c1/cfc0efd5-b7ca-4602-959a-07fe6b8d4e7d/subagents"
AUTH = {"r1": "a0a39fa7049de297d", "r2a": "ac3245ec6b3bff4d9", "r2b": "a97587d8e6861f387", "m1a": "a90da052935dbd22d",
        "m1b": "a81e926c35707d9b4", "m1c": "a731dc5ec95fae7c2", "c1": "a5304ab5549718b32"}
for name, aid in AUTH.items():
    n_user = 0; extra = []; ts = []; last_solver_write = None
    for line in open(f"{P}/agent-{aid}.jsonl"):
        r = json.loads(line)
        if "timestamp" in r:
            ts.append(r["timestamp"])
        if r.get("type") == "user":
            c = r["message"]["content"]
            is_tr = isinstance(c, list) and any(b.get("type") == "tool_result" for b in c)
            if not is_tr:
                n_user += 1
                if n_user > 1:
                    extra.append((r.get("timestamp"), (c if isinstance(c, str) else json.dumps(c))[:300]))
        if r.get("type") == "assistant":
            for b in r["message"].get("content", []):
                if b.get("type") == "tool_use" and re.search(rf"solver2_{name}\.py", json.dumps(b["input"])) and re.search(r"cat > \S*solver2_|Write|open\([^)]*solver2_[a-z0-9]+\.py[^)]*['\"]w", json.dumps(b["input"]) + b["name"]):
                    last_solver_write = r.get("timestamp")
    print(f"{name}: records {ts[0]} .. {ts[-1]}; non-tool-result user messages {n_user} (1 = brief only); last write touching solver2_{name}.py {last_solver_write}")
    for t, s in extra:
        print(f"   EXTRA MESSAGE {t}: {s!r}")
C = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_solver2_compare_20261126"
import datetime
for f in sorted(os.listdir(C)):
    print("compare file", f, datetime.datetime.fromtimestamp(os.path.getmtime(f"{C}/{f}"), datetime.timezone.utc).isoformat())
