"""Registry, run lengths, snapshots, calibration counts and gate G9, enumerated by the auditor from the ADR text (sections 5.1, 5.4, 6.1-6.3, 10.1)
and compared with studies/p10s1/core.py. G9 is recomputed from the ADR's ranges and from an own scan of configs/*.toml (every integer under a key
containing 'seed', and separately every integer >= 1000 anywhere in those configs).

Run: PYTHONPATH=. uv run --locked python docs/reviews/p10s1-implementation-audit-2026-11-15/c4_registry_seeds.py
Claude (Opus 5.5) review; Astra review: NOT_PERFORMED; not a human approval.
"""

import json
import sys
import tomllib
from collections import Counter
from pathlib import Path

from studies.p10s1 import core  # object under test
from studies.p10s1 import frozen as fz

ROOT = Path(__file__).resolve().parents[3]
U = 8192
CELLS = [(2048, 4096), (8192, 4096), (8192, 16384), (8192, 65536), (32768, 4096), (32768, 16384), (32768, 65536)]
DOQ = [(2048, 4096), (8192, 16384), (8192, 65536), (32768, 16384), (32768, 65536)]
R2 = [(2048, 4096), (8192, 16384), (8192, 65536), (32768, 65536)]
RUN = {4096: 6 * U, 16384: 4 * U, 65536: 2 * U}


def my_registry(overload=None, sb=(1,), cut=()):
    out = []
    cells = list(CELLS) + ([(65536, 16384), (65536, 65536)] if overload else [])
    for r in range(1, 6):
        for arm in ("F-OQ", "T-OQ", "H8"):
            out += [("P", arm, f, n, r, 2100 + r) for f, n in cells]
        out += [("P", "D-OQ", f, n, r, 2100 + r) for f, n in DOQ + ([(65536, 65536)] if overload else []) if f"{f // 1024}K/{n // 1024}K" not in cut]
        out += [("P", "R2", f, n, r, 2100 + r) for f, n in R2 + ([(65536, 65536)] if overload else [])]
    seeds = {(1, 1): 2111, (2, 1): 2121, (1, 2): 2112, (2, 2): 2122}
    for d in sb:
        for k in (1, 2):
            out += [("SB", "F-OQ", f, n, d, seeds[(k, d)]) for f, n in CELLS]  # ADR: 'on all seven cells'
    return out


def impl_registry(plan):
    return [(c.kind, c.arm, c.facts, c.slots, c.draw, c.init_seed) for c in core.registered_cells(plan)]


def snapshots_mine(u_p, run, mc=()):
    s = {int(u_p * f) for f in (1 / 16, 1 / 8, 1 / 4, 1 / 2, 1, 2, 4) if u_p * f <= run} | {run // 2, run} | {m for m in mc if m <= run}
    return tuple(sorted(s))


def ranges_from_adr():
    return {
        "P9": [(170001, 171343), (179001, 179933), (1701, 1702)],
        "P9-I": [(182001, 182020), (180101, 181900), (1791, 1792), (1801, 1802), (900001, 900233)],
        "review diagnostics": [(500001, 500004), (941001, 941001)],
        "P9-II": [(190001, 191599), (1891, 1892), (1901, 1902), (910001, 919999)],
        "S0": [(200001, 209999), (2001, 2002), (2091, 2092), (920001, 920999)],
        "S2": [(220001, 228999), (229001, 229999)],
    }


def my_s1_seeds():
    def set_of(base):
        return set(range(base, base + 14)) | {base + 20, base + 21, base + 22, base + 30, base + 31, base + 32, base + 40, base + 60} | set(range(base + 50, base + 60))

    reg = set().union(*(set_of(210001 + 100 * (r - 1)) for r in range(1, 6)))
    cal = set_of(219001) | set_of(219101)
    reh = set_of(219201)
    inits = {2101, 2102, 2103, 2104, 2105, 2111, 2121, 2112, 2122, 2191, 2192}
    derived = {i + k for i in inits for k in (1000, 2000, 3000, 4000, 5000)}
    test = set(range(921001, 922000))
    return {"registered": reg, "calibration": cal, "rehearsal": reh, "init": inits, "derived": derived, "test": test}


def scan_configs():
    seedkeys, anyint = set(), set()

    def walk(v, key):
        if isinstance(v, dict):
            for k, x in v.items():
                walk(x, k)
        elif isinstance(v, list):
            for x in v:
                walk(x, key)
        elif isinstance(v, int) and not isinstance(v, bool):
            if "seed" in key.lower():
                seedkeys.add(v)
            if v >= 1000:
                anyint.add(v)

    files = []
    for p in sorted((ROOT / "configs").glob("*.toml")):
        if p.name.startswith(("p9", "p10")):
            continue
        files.append(p.name)
        walk(tomllib.loads(p.read_text()), "")
    return files, seedkeys, anyint


def main():
    out = {}
    for name, plan, kw in (("default", core.Plan(seed_block_draws=()), {"sb": ()}), ("sb1", core.Plan(seed_block_draws=(1,)), {"sb": (1,)}), ("sb12", core.Plan(seed_block_draws=(1, 2)), {"sb": (1, 2)}),
                           ("cut_both", core.Plan(seed_block_draws=(), dense_cut=("8K/64K", "32K/16K")), {"sb": (), "cut": ("8K/64K", "32K/16K")}),
                           ("overload_sb0", core.Plan(overload_u_p=16384, seed_block_draws=()), {"sb": (), "overload": True}), ("overload_sb1", core.Plan(overload_u_p=16384, seed_block_draws=(1,)), {"sb": (1,), "overload": True})):
        mine, impl = Counter(my_registry(**kw)), Counter(impl_registry(plan))
        out[f"registry_{name}"] = {"mine": sum(mine.values()), "impl": sum(impl.values()), "only_mine": sorted(map(str, mine - impl))[:6], "only_impl": sorted(map(str, impl - mine))[:6],
                                   "configs_per_replicate_impl": len({(a, f, n) for k, a, f, n, d, i in impl if k == "P" and d == 1})}
    # run lengths and u_p of every registered cell
    bad = [c.label for c in core.registered_cells(core.Plan(overload_u_p=16384, seed_block_draws=(1, 2))) if c.run_updates != (c.u_p if c.arm == "R2" else RUN[c.slots] * c.u_p // U)]
    out["run_length_mismatches"] = bad
    out["overload_cells_u_p"] = sorted({(c.arm, c.facts, c.slots, c.u_p, c.run_updates) for c in core.registered_cells(core.Plan(overload_u_p=16384, seed_block_draws=())) if c.facts == 65536 and c.draw == 1})
    # calibration
    cal = core.calibration_cells(True)
    out["calibration"] = {"runs": len(core.calibration_cells()), "with_overload": len(cal), "by_item": {f"{a}|{u}": v for (a, u), v in Counter((c.arm, c.run_updates) for c in cal).items()},
                          "load_cells": sorted((c.slots, c.facts) for c in core.load_calibration_cells() if c.draw == 1), "dense_cells": sorted({(c.facts, c.slots, c.lr, c.run_updates) for c in core.dense_rate_cells()})}
    out["load_snapshots"] = {n: core.load_snapshots(n) for n in (4096, 16384)}
    # snapshots: default frozen (placeholder table) vs own
    fro = fz.Frozen.build(core.Plan(seed_block_draws=()), fz.default_cpu_table())
    mism = []
    need = fz.required_snapshots(fro.plan, fro.mc)
    for c in core.registered_cells(fro.plan):
        mine = snapshots_mine(c.u_p, c.run_updates, need.get((c.arm, c.facts, c.slots), ()))
        if mine != fro.snapshots(c):
            mism.append((c.label, mine, fro.snapshots(c)))
    out["snapshot_mismatches"] = mism[:5]
    out["snapshot_examples"] = {c.label: fro.snapshots(c) for c in core.registered_cells(fro.plan) if c.draw == 1 and c.arm in ("F-OQ", "R2")}
    out["me_updates"] = {f: core.me_updates(f) for f in (2048, 8192, 32768)}
    # G9
    mine = my_s1_seeds()
    files, seedkeys, anyint = scan_configs()
    overl = []
    names = list(mine)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if mine[a] & mine[b]:
                overl.append((a, b, sorted(mine[a] & mine[b])[:5]))
    for a, vals in mine.items():
        for study, rs in ranges_from_adr().items():
            hit = [v for v in vals if any(lo <= v <= hi for lo, hi in rs)]
            if hit:
                overl.append((a, study, hit[:5]))
        if vals & seedkeys:
            overl.append((a, "P1-P8 seed keys", sorted(vals & seedkeys)[:5]))
        if vals & anyint:
            overl.append((a, "P1-P8 any integer >= 1000 (informative)", sorted(vals & anyint)[:10]))
    other_inits = {1701, 1702, 1791, 1792, 1801, 1802, 1891, 1892, 1901, 1902, 2001, 2002, 2091, 2092}
    other_derived = {i + k for i in other_inits for k in (1000, 2000, 3000, 4000, 5000)}
    for a, vals in mine.items():
        if vals & (other_derived | other_inits):
            overl.append((a, "other studies' init/derived", sorted(vals & (other_derived | other_inits))[:5]))
    impl = core.seed_namespaces()
    out["g9"] = {"overlaps_auditor": overl, "impl_seed_check_passed": core.seed_check()["passed"], "impl_overlaps": core.seed_check()["overlaps"],
                 "namespace_sizes_mine": {k: len(v) for k, v in mine.items()}, "namespace_sizes_impl": {k: len(v) for k, v in impl.items()},
                 "namespaces_equal": {k: (mine["derived"] if k == "derived_init" else mine.get(k)) == impl[k] for k in impl}, "config_files_scanned": files, "seed_key_values": len(seedkeys)}
    # mode refusals
    refusals = {}
    for mode, name in (("calibration", "p10s1-draw-1"), ("rehearsal", "p10s1-draw-3"), ("rehearsal", "p10s1-cal-1"), ("calibration", "p10s1-rehearsal"), ("registered", "p10s1-test-0"), ("registered", "p10s1-cal-2"), ("registered", "p10s1-draw-6")):
        try:
            core.check_seed_set(mode, name)
            refusals[f"{mode}:{name}"] = "ALLOWED"
        except ValueError:
            refusals[f"{mode}:{name}"] = "refused"
    out["check_seed_set"] = refusals
    json.dump(out, sys.stdout, indent=1, default=str)
    print()


if __name__ == "__main__":
    main()
