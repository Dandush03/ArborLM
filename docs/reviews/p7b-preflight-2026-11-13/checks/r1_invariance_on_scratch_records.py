"""ADR-0014 section 4 / 10 R = 1 requirement, checked on the scratch calibration-as-stream records
written by the implementer's simulator (no evaluation trace): at R = 1 the distinct pages per query,
the first-touch misses and the capacity misses at C = 8 must be identical across ALL layouts; at
larger C they may differ (eviction tie depends on page numbers). The registered workers do not test
this at run time (finding m-R1). Standard library only. argv: simulate_dir
"""

import json
import sys
from pathlib import Path


def main() -> int:
    workers = Path(sys.argv[1]) / "workers"
    bad = []
    larger_c_differ = 0
    n = 0
    for path in sorted(workers.glob("*.result.json")):
        rec = json.loads(path.read_text())["record"]
        groups = {k: v for k, v in rec["streams"]["actual"].items() if k.endswith("|R1")}
        ref_key = sorted(groups)[0]
        ref = groups[ref_key]
        for key, g in groups.items():
            n += 1
            if g["stats"]["hist"] != ref["stats"]["hist"]:
                bad.append((path.name, key, "hist"))
            for c, ties in g["by_c"].items():
                for tie, e in ties.items():
                    r = ref["by_c"][c][tie]
                    if (e["first_touch_all"], e["first_touch_warm"]) != (r["first_touch_all"], r["first_touch_warm"]):
                        bad.append((path.name, key, c, tie, "first_touch"))
                    cap, rcap = e["misses_warm"] - e["first_touch_warm"], r["misses_warm"] - r["first_touch_warm"]
                    if c == "8" and cap != rcap:
                        bad.append((path.name, key, c, tie, "capacity_C8"))
                    if c != "8" and cap != rcap:
                        larger_c_differ += 1
    print(json.dumps({"groups_checked": n, "violations": bad[:20], "violation_count": len(bad),
                      "larger_C_layout_differences_allowed": larger_c_differ}, indent=1))
    print("R1 INVARIANCE", "PASS" if not bad else "FAIL")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
