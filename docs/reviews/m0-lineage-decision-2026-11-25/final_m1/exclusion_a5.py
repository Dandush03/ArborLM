# ruff: noqa
"""Final M1 audit: are the dropped lineages excluded everywhere the fix-4 set is built? Reads the code's loaders, the cluster map, core.REGISTRY,
the fix-4 manifests and the fixture directory; prints one line per check."""
import json
import os
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from studies.m0 import lineages_m1_fix4 as f4
from studies.m0.lineages_m1_fix4_clusters import strict_clusters
from studies.m0.core import lineages_of

DROPPED = sorted(f4.not_registered())
EXCL = ["M1.min_cost_packs_r2", "M1.min_cost_packs"]
REPLACED_R3 = sorted(f4.REPLACES.values())
man = json.load(open("studies/m0/manifests/m1_fix4_survivors.json"))
reg = [x.id for x in f4.load_registered()]
alle = [x.id for x in f4.load_all()]
checks = []
checks.append(("load_registered has none of the NOT REGISTERED (fix3 + fix4)", not set(reg) & set(DROPPED), sorted(set(reg) & set(DROPPED))))
checks.append(("load_registered == manifest survivors (29)", sorted(reg) == sorted(man["survivors"]) and len(reg) == 29, len(reg)))
checks.append(("min_cost_packs absent from load_all", not set(alle) & set(EXCL), sorted(set(alle) & set(EXCL))))
checks.append(("replaced r3 ids (mixture, gcd_lcm, finite_differences, slot_permutations, average_missing, clock_duration) absent from load_all", not set(alle) & set(REPLACED_R3), sorted(set(alle) & set(REPLACED_R3))))
sc = strict_clusters(reg)
checks.append(("strict_clusters(load_registered) has no dropped id and 17 clusters", len(sc) == 17 and not {i for v in sc.values() for i in v} & set(DROPPED), len(sc)))
core_ids = [x.id for x in lineages_of("M1")]
checks.append(("core.REGISTRY['M1'] holds no fix-3/fix-4 id", not [i for i in core_ids if i.endswith(("_r3", "_r4"))], len(core_ids)))
checks.append(("manifest surviving_clusters members == survivors", sorted(i for v in man["surviving_clusters"].values() for i in v) == sorted(man["survivors"]), None))
# scan the manifest sections that describe the surviving set
def ids_in(obj):
    return set(re.findall(r"M1\.[a-z_0-9]+", json.dumps(obj)))
for sec in ("survivors", "surviving_clusters", "surviving_cluster_names", "capacity", "capacity_as_written_failures_listed_for_the_lead"):
    bad = sorted(ids_in(man.get(sec)) & set(DROPPED + EXCL))
    checks.append((f"manifest section '{sec}' mentions no dropped id", not bad, bad))
# the capacity raw inputs may include dropped lineages (measured with --all); report whether the as-written partition used only survivors
cap_aw = man["capacity"]["as_written"]
checks.append(("manifest as-written partition counts 14 + 15 = 29 (survivors only)", sum(cap_aw.get("lineages_in_part", {}).values()) == 29, cap_aw.get("lineages_in_part")))
# fixtures
fx = sorted(os.listdir("studies/m0/fixtures/m1_fix3")) if os.path.isdir("studies/m0/fixtures/m1_fix3") else []
fx_ids = [x.removesuffix(".jsonl") for x in fx if x.endswith(".jsonl")]
checks.append(("fixtures/m1_fix3 holds no dropped lineage", not set(fx_ids) & set(DROPPED), sorted(set(fx_ids) & set(DROPPED))))
checks.append(("a fix-4 fixture set exists (r4 revisions)", any(os.path.isdir(f"studies/m0/fixtures/{d}") for d in ("m1_fix4",)), [d for d in os.listdir("studies/m0/fixtures") if "m1" in d.lower()]))
for name, ok, info in checks:
    print(("PASS " if ok else "FAIL ") + name + ("" if info in (None, [], ()) else f"  [{info}]"))
