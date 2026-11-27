# ruff: noqa
"""M0 stage 2, M1: print example items (3 per level per survivor lineage) for the auditor's wording read. Same fixture seed as
s2m1_fixtures.py but the label "stage2-read" (so these are not the fixtures). Run from the implementation worktree root with PYTHONPATH=."""
import hashlib, json, sys
from studies.m0.core import build_item, stream
from studies.m0.lineages_m1_fix4 import load_all

FIXTURE_SEED = int.from_bytes(hashlib.sha256(b"400002|stage2-check|M1").digest()[:8], "big")
surv = json.load(open("studies/m0/manifests/survivor_list_of_record.json"))["evaluations"]["M1"]
lins = {x.id: x for x in load_all()}
per = int(sys.argv[1]) if len(sys.argv) > 1 else 3
for lid in sorted(surv):
    for L in range(7):
        rng = stream(FIXTURE_SEED, "stage2-read", "M1", lid, str(L))
        for i in range(per):
            it = build_item(lins[lid], L, rng, "A", f"read/{lid}/L{L}/{i}")
            print(f"== {it.id} key={it.answer}\n{it.question}\n")
