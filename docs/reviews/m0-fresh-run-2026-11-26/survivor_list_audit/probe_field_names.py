"""Auditor probe: print field NAMES and value TYPES only (no values, no figures)
of the four fix-4 survivor manifests at 7cd0ac5a. Standard library only."""
import json
import subprocess

REPO = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"


def show(rev_path: str) -> bytes:
    return subprocess.run(["git", "-C", REPO, "show", rev_path], check=True, capture_output=True).stdout


def shape(x, depth=0):
    if isinstance(x, dict):
        return {k: (shape(v, depth + 1) if depth < 1 else type(v).__name__) for k, v in x.items()}
    if isinstance(x, list):
        out = {"list_of": sorted({type(e).__name__ for e in x}), "len": len(x)}
        keys = set()
        for e in x:
            if isinstance(e, dict):
                keys |= set(e.keys())
        if keys:
            out["element_keys"] = sorted(keys)
        return out
    return type(x).__name__


for ev in ("r1", "r2", "m1", "c1"):
    obj = json.loads(show(f"7cd0ac5a:studies/m0/manifests/{ev}_fix4_survivors.json"))
    print(ev, json.dumps(shape(obj), indent=1, sort_keys=True))
