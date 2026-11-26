"""Copy auditor, step 3: list the lineage ids each unit's own selection code draws from (registries only; builds no item).
Run from the implementation worktree root:
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<wt> uv run --locked python -I <this>   (with -I, sys.path set below)"""
import json, sys
WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
sys.path.insert(0, WT)
out = {}
from studies.m0.lineages_m1_fix4 import load_all, load_registered
out["M1.load_all"] = sorted(x.id for x in load_all())
out["M1.load_registered"] = sorted(x.id for x in load_registered())
from studies.m0.lineages_r1_fix4_clusters import registered_v4, candidates_v4
out["R1.registered_v4"] = sorted(x.id for x in registered_v4())
out["R1.candidates_v4"] = sorted(x.id for x in candidates_v4())
from studies.m0.r2_fix4_set import fix4_set
out["R2.fix4_set"] = sorted(fix4_set())
from studies.m0.lineages_c1_fix4 import all_written
out["C1.all_written"] = sorted(all_written())
from studies.m0 import c1_fix3_battery as bat
out["C1.bat.all_lineages"] = sorted(bat.all_lineages())
print(json.dumps(out, indent=1))
