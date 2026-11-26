"""Numerical-hazard check on the seeds of stage 1S point 4 (text at d70ba38d), standard library only.
(1) re-derive the three base integers and the dry-run base from their labels with sha256[:8] big-endian and
    compare with the integers the text prints; (2) derive the per-unit role integers as the text defines them;
(3) the R1 scripts seed `random.Random(root + level)` (r1_fix4_gen.py:21, final_r1/fgen.py:23) and
    `random.Random(base * 1000 + level)` (r1_fix3_battery.py:1060): check that no two R1 streams that one run
    can create (root + level, level 0..6, and base*1000 + level) coincide, across all roles and the three
    seeds and the dry-run base. No item is generated."""
import hashlib, itertools, json, sys

def h(s):
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big")

TEXT = {"1": 16103270370041696293, "2": 10773834973117025986, "3": 619660634241804713, "dry": 3342082268851962967}
bases = {"1": h("400002|fresh-shortcut|1"), "2": h("400002|fresh-shortcut|2"), "3": h("400002|fresh-shortcut|3"),
         "dry": h("400002|fresh-shortcut-dry-run")}
ROLES = {"R1a": ["aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat1_fit", "feat1_test", "feat2_fit", "feat2_test"],
         "R1b": ["aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat_fit", "feat_test"], "R1c": ["fit", "test"],
         "R2a": ["tag"], "R2b": ["tag"], "M1a": ["own", "a4", "a3"], "M1b": ["seed"], "M1c": ["seed"],
         "C1a": ["seed"], "C1b": ["seed"], "C1c": ["seed"]}
out = {"bases_match_text": {k: bases[k] == TEXT[k] for k in TEXT}, "bases": bases}
ints = {}
for b, bv in bases.items():
    for u, rs in ROLES.items():
        for r in rs:
            ints[(b, u, r)] = h(f"{bv}|{u}|{r}")
out["n_role_integers"] = {b: sum(1 for k in ints if k[0] == b) for b in bases}
allv = list(ints.values()) + list(bases.values())
out["all_distinct"] = len(set(allv)) == len(allv)
# R1 streams
streams = {}
coll = []
for (b, u, r), v in ints.items():
    if not u.startswith("R1"):
        continue
    kinds = []
    if r.startswith("impl"):
        kinds.append(("x1000", [v * 1000 + lv for lv in range(7)]))
    else:
        kinds.append(("plus", [v + lv for lv in range(7)]))
    for kind, vals in kinds:
        for x in vals:
            if x in streams and streams[x][:3] != (b, u, r):
                coll.append([streams[x], [b, u, r, kind]])
            streams[x] = (b, u, r, kind)
out["r1_stream_collisions"] = coll
md = min(abs(a - c) for a, c in itertools.combinations(sorted(v for (b, u, r), v in ints.items() if u.startswith("R1") and not r.startswith("impl")), 2))
out["r1_min_gap_between_plus_level_roots"] = md
json.dump(out, sys.stdout, sort_keys=True, indent=2, default=str)
sys.stdout.write("\n")
