"""Independent auditor derivation of the M0 survivor list of record
(ADR-0033 addendum 1 at d70ba38d, section 4A stage 0, points 1-6).
Standard library only. Reads inputs through `git show` only.
Writes survivor_ids_auditor.json next to this script. Stops (exit 1) on any
hash mismatch, absent field, drop id not found, or count other than the text's."""
import hashlib
import json
import os
import subprocess
import sys

REPO = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

M = "7cd0ac5a:studies/m0/manifests/"
INPUTS = {
    "R1": (M + "r1_fix4_survivors.json", "e1a7a092", "749b"),
    "R2": (M + "r2_fix4_survivors.json", "2456dac6", "a102"),
    "M1": (M + "m1_fix4_survivors.json", "153e6837", "1986"),
    "C1": (M + "c1_fix4_survivors.json", "eaedec75", "3603"),
    "DROPS": ("b78e58b1:docs/reviews/m0-lineage-decision-2026-11-25/"
              "cross_evaluation_map/drops_after_final_checks.txt", "b714f102", "0bd5"),
}
EXPECTED = {"R1": 10, "R2": 17, "M1": 29, "C1": 26}


def stop(msg):
    print("STOP:", msg)
    sys.exit(1)


def show(spec):
    return subprocess.run(["git", "-C", REPO, "show", spec], check=True, capture_output=True).stdout


raw, digests = {}, {}
for key, (spec, pre, suf) in INPUTS.items():
    b = show(spec)
    h = hashlib.sha256(b).hexdigest()
    raw[key], digests[key] = b, h
    ok = h.startswith(pre) and h.endswith(suf)
    print(f"sha256 {key} {spec} {h} text={pre}...{suf} {'MATCH' if ok else 'MISMATCH'}")
    if not ok:
        stop(f"hash of {key} does not match the text")


def need(obj, field, where):
    if not isinstance(obj, dict) or field not in obj:
        stop(f"field {field!r} absent in {where}")
    return obj[field]


lists = {}

# R1: lineage id (field `name`) of every entry of `shapes` whose `status` is SURVIVES.
r1 = json.loads(raw["R1"])
shapes = need(r1, "shapes", "R1")
if not isinstance(shapes, list):
    stop("R1 shapes is not a list")
lists["R1"] = [need(e, "name", "R1.shapes[]") for e in shapes if need(e, "status", "R1.shapes[]") == "SURVIVES"]

# R2: `id` of every entry of `lineages` whose `status_before_capacity` is SURVIVES.
# `lineages` is a dict keyed by id; the entries are its values.
r2 = json.loads(raw["R2"])
lin2 = need(r2, "lineages", "R2")
if not isinstance(lin2, dict):
    stop("R2 lineages is not a dict (reading assumes dict of entries)")
lists["R2"] = []
for k, e in lin2.items():
    if need(e, "status_before_capacity", f"R2.lineages[{k}]") == "SURVIVES":
        i = need(e, "id", f"R2.lineages[{k}]")
        if i != k:
            print(f"NOTE: R2 entry key {k!r} differs from its id {i!r}; id is used")
        lists["R2"].append(i)

# M1: the list `survivors`.
m1 = json.loads(raw["M1"])
surv = need(m1, "survivors", "M1")
if not isinstance(surv, list) or not all(isinstance(s, str) for s in surv):
    stop("M1 survivors is not a list of strings")
lists["M1"] = list(surv)

# C1: lineage id (field `name`) of every entry of `lineages` whose `status` is SURVIVES.
c1 = json.loads(raw["C1"])
lin1 = need(c1, "lineages", "C1")
if not isinstance(lin1, list):
    stop("C1 lineages is not a list")
lists["C1"] = [need(e, "name", "C1.lineages[]") for e in lin1 if need(e, "status", "C1.lineages[]") == "SURVIVES"]

for ev, ids in lists.items():
    if len(ids) != len(set(ids)):
        stop(f"duplicate ids in {ev} reading")
    print(f"read {ev}: {len(ids)} ids before drops")

# Drops: one id per non-blank line; lines starting with '#' are comments.
drops = []
for line in raw["DROPS"].decode("utf-8").splitlines():
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    drops.append(s)
print(f"drops: {len(drops)} ids: {drops}")
if len(drops) != 5:
    stop("drops file does not list five ids")
for d in drops:
    ev = d.split(".", 1)[0]
    if ev not in lists or d not in lists[ev]:
        stop(f"drop id {d!r} not in the list read under point 2")
    lists[ev].remove(d)

out = {ev: sorted(ids) for ev, ids in lists.items()}  # Python str sort = code-point order
for ev, n in EXPECTED.items():
    print(f"count {ev}: {len(out[ev])} (text {n}) {'OK' if len(out[ev]) == n else 'DIFFERS'}")
total = sum(len(v) for v in out.values())
print(f"count total: {total} (text 82)")
if any(len(out[ev]) != n for ev, n in EXPECTED.items()) or total != 82:
    stop("counts differ from the text")
for ev in out:
    for i in out[ev]:
        if not i.startswith(ev + "."):
            stop(f"id {i!r} in {ev} lacks prefix")

text = json.dumps(out, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
path = os.path.join(OUT_DIR, "survivor_ids_auditor.json")
with open(path, "x", encoding="utf-8") as f:
    f.write(text)
print("wrote", path, "sha256", hashlib.sha256(text.encode("utf-8")).hexdigest())
with open(os.path.abspath(__file__), "rb") as f:
    print("script sha256", hashlib.sha256(f.read()).hexdigest())
