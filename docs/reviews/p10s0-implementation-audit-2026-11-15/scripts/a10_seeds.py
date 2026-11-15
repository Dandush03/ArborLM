"""ADR-0020 section 7 seed layout recomputed by the auditor; compared with studies.p10s0.core; collisions with every integer under a *seed* key in configs/*.toml
and with the declared ranges of the other studies. Claude (Opus 5.5) review; Astra review: NOT_PERFORMED."""
import json, sys, tomllib
from pathlib import Path
W = Path(sys.argv[1]); sys.path.insert(0, str(W))
def set_values(base):
    v = set()
    for off in (0, 20, 60):
        v |= set(range(base + off, base + off + 20))
    v |= {base + 40, base + 41, base + 44, base + 45, base + 48, base + 49, base + 50, base + 51, base + 52}
    return v
bases = {f"draw-{d}": 200001 + 100 * (d - 1) for d in range(1, 14)} | {"reserve-1": 201301, "reserve-2": 201401, "check": 209001, "rehearsal": 209101}
mine = {k: set_values(b) for k, b in bases.items()}
allv = set().union(*mine.values())
pairwise = [(a, b) for a in mine for b in mine if a < b and mine[a] & mine[b]]
from studies.p10s0 import core
impl = {f"draw-{d}": set(core.registered_set(d).values()) for d in range(1, 14)} | {"reserve-1": set(core.reserve_set(1).values()), "reserve-2": set(core.reserve_set(2).values()), "check": set(core.CHECK_SET.values()), "rehearsal": set(core.REHEARSAL_SET.values())}
diff = {k: (sorted(mine[k] - impl[k])[:5], sorted(impl[k] - mine[k])[:5]) for k in mine if mine[k] != impl[k]}
others = {"P9": [(170001, 171343), (179001, 179933), (1701, 1702)], "P9-I": [(182001, 182020), (180101, 181900), (1791, 1792), (1801, 1802), (900001, 900233)], "review": [(500001, 500004)],
          "P9-II": [(190001, 191599), (1891, 1892), (1901, 1902), (910001, 919999)], "S1": [(210001, 219999), (2101, 2105), (2111, 2111), (2121, 2121), (2112, 2112), (2122, 2122), (2191, 2192), (921001, 921999)], "S2": [(220001, 228999), (229001, 229999)]}
s0_all = allv | {2001, 2002, 2091, 2092}
hits = {o: sorted(v for v in s0_all if any(lo <= v <= hi for lo, hi in rs))[:5] for o, rs in others.items()}
cfg = {}
for p in sorted((W / "configs").glob("*.toml")):
    if p.name.startswith("p10s0"): continue
    data = tomllib.loads(p.read_text())
    found = set()
    def walk(n, s):
        if isinstance(n, dict):
            for k, v in n.items(): walk(v, s or "seed" in k.lower())
        elif isinstance(n, list):
            for v in n: walk(v, s)
        elif isinstance(n, int) and not isinstance(n, bool) and s: found.add(n)
    walk(data, False)
    c = sorted(found & (s0_all | set(range(920001, 921000))))
    if c: cfg[p.name] = c
print(json.dumps({"inside_200001_209999": all(200001 <= v <= 209999 for v in allv), "max": max(allv), "pairwise_overlaps": pairwise, "impl_differs": diff, "other_range_hits": hits, "config_collisions": cfg, "count": len(allv)}, indent=1))
