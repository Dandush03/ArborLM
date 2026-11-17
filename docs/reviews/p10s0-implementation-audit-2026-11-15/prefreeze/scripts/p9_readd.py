# N8: after plan.json is removed and re-added, the latest addition is the freeze commit; the older one is refused.
import sys, json
from pathlib import Path
from studies.p10s0 import stages
repo, old, new = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
out = {}
for name, c in (("old_first_addition", old), ("new_latest_addition", new)):
    try:
        r = stages.check_preconditions(stages.REGISTERED, repo, c); out[name] = {"accepted": True, "result_keys": sorted(r) if isinstance(r, dict) else r}
    except Exception as e:
        out[name] = {"accepted": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
print(json.dumps(out, indent=1))
