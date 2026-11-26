"""Independent integrity check of the M0 fresh run outputs (auditor's own code, stdlib only)."""
import hashlib, json, os, subprocess, sys
IMPL = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
SPEC = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1"
RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126"
REC = IMPL + "/docs/reviews/m0-fresh-run-2026-11-26"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def shab(b): return hashlib.sha256(b).hexdigest()
problems = []
total = 0
for s in (1, 2, 3):
    rec = json.load(open(f"{REC}/run/hashes_seed{s}.json"))
    # copy at the run root must be identical
    if sha(f"{RUN}/hashes_seed{s}.json") != sha(f"{REC}/run/hashes_seed{s}.json"):
        problems.append(f"seed{s}: hash record copy in run dir differs from committed one")
    plan_sha = sha(IMPL + "/studies/m0/fresh_run/run_plan.json")
    if rec.get("plan_sha256") != plan_sha:
        problems.append(f"seed{s}: plan sha {rec.get('plan_sha256')} != {plan_sha}")
    for unit, ud in rec["units"].items():
        atts = ud["attempts"]
        if len(atts) != 1:
            problems.append(f"seed{s} {unit}: {len(atts)} attempts")
        for a in atts:
            for c in a["commands"]:
                if c["exit_status"] != 0:
                    problems.append(f"seed{s} {unit} {c['name']} exit {c['exit_status']}")
            d = a["dir"]
            listed = set(a["files"])
            for rel, fd in a["files"].items():
                p = os.path.join(d, rel)
                total += 1
                if not os.path.exists(p):
                    problems.append(f"missing {p}"); continue
                if os.path.getsize(p) != fd["size"] or sha(p) != fd["sha256"]:
                    problems.append(f"MISMATCH {p}")
            on_disk = set()
            for root, _, files in os.walk(d):
                for fn in files:
                    on_disk.add(os.path.relpath(os.path.join(root, fn), d))
            extra = on_disk - listed
            if extra:
                problems.append(f"seed{s} {unit}: files on disk not in hash record: {sorted(extra)[:10]} (n={len(extra)})")
    print(f"seed{s}: units={len(rec['units'])}")
print("output files checked:", total)
# pooled
for line in open(f"{REC}/run/pooled/SHA256SUMS_pooled.txt"):
    h, name = line.split()
    got = sha(f"{RUN}/pooled/{name}")
    print("pooled", name, "OK" if got == h else f"MISMATCH {got}")
    if got != h: problems.append(f"pooled {name}")
# committed gz copy of pooled_table
import gzip
gzb = gzip.open(f"{REC}/run/pooled/pooled_table.json.gz").read()
print("committed pooled_table.json.gz decompressed equals run pooled_table.json:", shab(gzb) == sha(f"{RUN}/pooled/pooled_table.json"))
for name in ("dropped.json", "per_lineage.json", "report_extras.json", "SUMMARY.md"):
    print("committed copy", name, "same as run dir:", sha(f"{REC}/run/pooled/{name}") == sha(f"{RUN}/pooled/{name}"))
# commit of hash record
start = open(f"{REC}/run/commit_at_start.txt").read().strip()
log = subprocess.run(["git", "-C", IMPL, "log", "--format=%H", "--", "docs/reviews/m0-fresh-run-2026-11-26/HASH_RECORD.json"], capture_output=True, text=True).stdout.split()
print("commit_at_start:", start, "| commits touching HASH_RECORD.json:", log)
if log != [start]: problems.append("HASH_RECORD commit != commit_at_start")
# hashes inside HASH_RECORD vs files: working tree and at the commit
hr = json.load(open(f"{REC}/HASH_RECORD.json"))
def check(path, want, repo=IMPL, commit=start):
    wt = sha(os.path.join(repo, path)) if os.path.exists(os.path.join(repo, path)) else None
    blob = subprocess.run(["git", "-C", repo, "show", f"{commit}:{path}"], capture_output=True).stdout
    atc = shab(blob) if blob else None
    ok = (wt == want) and (atc == want)
    print(("OK  " if ok else "BAD ") + path, "worktree", wt == want, "at-commit", atc == want)
    if not ok: problems.append(f"HASH_RECORD {path}")
n = 0
for k, v in hr.items():
    if isinstance(v, dict) and "path" in v and "sha256" in v:
        if k == "iv_class_table":
            p = "docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev7_uncounted_rules.json"
            check(p, v["sha256"], SPEC, "2c944302"); n += 1
        else:
            check(v["path"], v["sha256"]); n += 1
    elif isinstance(v, dict) and all(isinstance(x, str) and len(x) == 64 for x in v.values()) and v:
        for p, hh in v.items():
            check(p, hh); n += 1
    elif k == "approved_text":
        blob = subprocess.run(["git", "-C", SPEC, "show", f"{v['commit']}:docs/decisions/ADR-0033-addendum-1-lineage-clusters.md"], capture_output=True).stdout
        ok = shab(blob) == v["sha256"]; n += 1
        print(("OK  " if ok else "BAD ") + "approved text at", v["commit"])
        if not ok: problems.append("approved text")
    else:
        print("not a hash entry:", k, str(v)[:80])
print("HASH_RECORD entries checked:", n)
# head vs start: were files changed after?
d = subprocess.run(["git", "-C", IMPL, "diff", "--stat", start, "HEAD", "--", "studies/m0/fresh_run", "studies/m0/manifests"], capture_output=True, text=True).stdout
print("diff start..HEAD on studies/m0/fresh_run and manifests:", repr(d[:500]))
print("PROBLEMS:", len(problems))
for p in problems: print("  ", p)
