"""Auditor's own check of run_plan.json: seeds re-derived from the approved text (stage 1S point 4), their positions in argv/env,
output roots, dry commands not pointing at implementers' smoke folders, C1a --timeout. Stdlib only. Executes nothing of the plan."""
import hashlib, json, sys

plan = json.load(open(sys.argv[1]))
def h8(s): return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big")
TEXT_BASES = {"1": 16103270370041696293, "2": 10773834973117025986, "3": 619660634241804713, "dry": 3342082268851962967}
BASE_LABEL = {"1": "400002|fresh-shortcut|1", "2": "400002|fresh-shortcut|2", "3": "400002|fresh-shortcut|3", "dry": "400002|fresh-shortcut-dry-run"}
ROLES = {"R1a": ["aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat1_fit", "feat1_test", "feat2_fit", "feat2_test"],
         "R1b": ["aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat_fit", "feat_test"], "R1c": ["fit", "test"],
         "R2a": ["tag"], "R2b": ["tag"], "M1a": ["own", "a4", "a3"], "M1b": ["seed"], "M1c": ["seed"], "C1a": ["seed"], "C1b": ["seed"], "C1c": ["seed"]}
problems = []
allints = set()
for s, b in TEXT_BASES.items():
    d = h8(BASE_LABEL[s])
    print(f"base {s}: sha256('{BASE_LABEL[s]}')[:8] = {d}; text {b}; {'OK' if d == b else 'DIFFERS'}")
    allints.add(b)
roots = {"run": "/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126", "dry": "/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_dry_20261126"}
if plan["output_roots"] != roots: problems.append(("output_roots", plan["output_roots"]))
if plan["unit_order"] != ["R1a", "R1b", "R1c", "R2a", "R2b", "M1a", "M1b", "M1c", "C1a", "C1b", "C1c"]: problems.append(("unit_order", plan["unit_order"]))
expect_pos = {  # where each role must appear: ('argv', index after the script token) or ('env', NAME)
}
for u, roles in ROLES.items():
    for s in ["1", "2", "3", "dry"]:
        run = plan["units"][u]["runs"][s]
        want = {r: h8(f"{TEXT_BASES[s]}|{u}|{r}") for r in roles}
        allints.update(want.values())
        got = {x["role"]: x["integer"] for x in run["seeds"]}
        if got != want: problems.append((u, s, "seeds listed", got, want))
        if run["base_integer"] != TEXT_BASES[s]: problems.append((u, s, "base"))
        od = run["output_dir"]
        exp_od = f"{roots['run']}/{u}/seed{s}" if s != "dry" else f"{roots['dry']}/{u}"
        if od != exp_od: problems.append((u, s, "output_dir", od))
        blob = json.dumps(run["commands"])
        # every seed integer appears in the commands exactly as its decimal text
        for r, v in want.items():
            if str(v) not in blob: problems.append((u, s, "seed not in commands", r, v))
        # no integer of another seed set or unit appears
        for c in run["commands"]:
            for p in [*c["argv"], *c["env"].values(), c["stdout_file"], c["stderr_file"], *c.get("writes", [])]:
                if "/" in p and ("_scratch" in p or "smoke" in p.lower() or "m0_fr_dry" in p): problems.append((u, s, "scratch path", p))
                if p.startswith("/Users/") and "/experiments/" in p and not p.startswith(od) and "/worktrees/" not in p: problems.append((u, s, "path outside output dir", p))
            for w in [c["stdout_file"], c["stderr_file"], *c.get("writes", [])]:
                if not w.startswith(od + "/"): problems.append((u, s, "write outside output dir", w))
            e = c["env"]
            if e.get("PYTHONHASHSEED") != "0" or e.get("PYTHONDONTWRITEBYTECODE") != "1": problems.append((u, s, "env", c["name"]))
            if c["cwd"] != plan["worktree_root"]: problems.append((u, s, "cwd", c["cwd"]))
            if c["argv"][:4] != ["uv", "run", "--locked", "python"]: problems.append((u, s, "argv head", c["argv"][:5]))
            if "-I" in c["argv"]: print(f"note: {u} {s} {c['name']}: python -I (environment variables PYTHON* are ignored by that interpreter)")
        # position checks
        cm = run["commands"]
        if u == "R1a":
            a = cm[0]["argv"]; i = a.index("studies.m0.fresh_run.r1.r1_fix4_measure")
            ok = [int(x) for x in a[i + 2:i + 6]] == [want[r] for r in ["aud_seed", "aud_fit", "impl_seed", "impl_fit"]] and int(a[i + 1]) == plan["units"][u]["items_per_level"]["dry" if s == "dry" else "run"]
            ok &= all(cm[0]["env"][f"M0FR_R1A_{r.upper()}"] == str(want[r]) for r in ["feat1_fit", "feat1_test", "feat2_fit", "feat2_test"])
        elif u == "R1b":
            a = cm[0]["argv"]; i = [k for k, x in enumerate(a) if x.endswith("run_rules_final.py")][0]
            ok = [int(x) for x in a[i + 2:i + 8]] == [want[r] for r in ["aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat_fit", "feat_test"]]
            n = plan["units"][u]["items_per_level"]["dry" if s == "dry" else "run"]
            ok &= int(a[i + 1]) == n and int(a[i + 8]) == n
        elif u == "R1c":
            a = cm[0]["argv"]; ok = [int(x) for x in a[-2:]] == [want["fit"], want["test"]]
        elif u in ("R2a", "R2b"):
            ok = all(c["env"].get("M0_FR_TAG") == str(want["tag"]) for c in cm)
        elif u == "M1a":
            ok = all(cm[0]["env"][f"M1A_SEED_{r.upper()}"] == str(want[r]) for r in ["own", "a4", "a3"])
        elif u in ("M1b", "M1c"):
            a = cm[0]["argv"]; ok = int(a[-2]) == want["seed"]
        else:
            a = cm[0]["argv"]; ok = int(a[a.index("--seed") + 1]) == want["seed"]
        if not ok: problems.append((u, s, "seed position"))
        if u == "C1a":
            a4 = [c for c in cm if "c1_fix4_a3_run" in " ".join(c["argv"])][0]["argv"]
            if a4[a4.index("--timeout") + 1] != "3000": problems.append((u, s, "timeout"))
print("distinct integers (bases + per-unit seeds):", len(allints))
print("PROBLEMS:", len(problems))
for p in problems: print("  ", p)
