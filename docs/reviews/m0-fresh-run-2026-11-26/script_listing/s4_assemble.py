"""Assemble script_listing.json from s1_list.out.json (step 1) and s2_resolve_v2.out.json (step 2).
Deterministic: sorted keys, indent 2, trailing newline; lists sorted by path."""
import json, os, sys

H = os.path.dirname(os.path.abspath(__file__))
s1 = json.load(open(os.path.join(H, "s1_list.out.json")))
s2 = json.load(open(os.path.join(H, "s2_resolve_v2.out.json")))
assert s1["commit"] == s2["commit"]
listed = sorted(({k: e[k] for k in ("path", "blob", "sha256", "pattern")} for e in s1["listed"]), key=lambda e: e["path"])
assert {e["path"] for e in listed} == set(s2["entry_path"]), "listing and resolver entry points differ"
deps = sorted(({"path": d["path"], "blob": d["blob"], "sha256": d["sha256"], "reached_by": sorted(d["reached_by"]),
                "how": sorted(d["how"])} for d in s2["dependencies"]), key=lambda e: e["path"])
out = {"commit": s1["commit"], "listed": listed, "dependencies": deps}
with open(os.path.join(H, "script_listing.json"), "w") as f:
    f.write(json.dumps(out, sort_keys=True, indent=2) + "\n")
print(len(listed), "listed;", len(deps), "dependencies")
