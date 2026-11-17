# ruff: noqa
"""Programme-wide seed registry check for the P10-I drafts (ADR-0023 to ADR-0028).

Written by the arbor-auditor subagent (model: Claude Opus 5.5) on 2026-11-17. Standard library only.
It rebuilds, from the repository (configs, studies, src, tests), the inventory of every seed that P1
to P10 used or reserved, literal and derived, and asserts that every P10-I allocation of
SEED_REGISTRY.md, with every value the known derivation rules produce from it, is disjoint from that
inventory (also expanded) and from every other P10-I allocation.

The inventory is reconstructed independently: module-level constants are read with ``ast`` (no
import), rules are cited by file and line. A second, optional pass imports the studies' own seed
functions (needs the locked environment: ``uv run --locked python``) and asserts that every seed they
declare is inside the reconstruction. The script edits nothing.

Usage (from the worktree root):
    uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check.py [--tables]

Exit status 0 when every binding check passes, 1 otherwise.
"""

from __future__ import annotations

import ast
import bisect
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
K_MAX = 10  # seed + 1000*k, k = 1..K_MAX (code uses k <= 5, P9-I k <= 8; 10 is the registry's margin)
INDEX_SPAN = 1000  # s*1000 + index, index in [0, 999] (widest bound that keeps the rule injective)
SMALL_LITERAL = 100_000  # P1-P8 and small constants: +1000k applied conservatively to every literal below this

# ---------------------------------------------------------------------------------------------------
# helpers


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def line_of(rel: str, pattern: str) -> str:
    rx = re.compile(pattern)
    for i, line in enumerate(text(rel).splitlines(), 1):
        if rx.search(line):
            return f"{rel}:{i}"
    raise SystemExit(f"CHECKER ERROR: pattern {pattern!r} not found in {rel}")


_SAFE = {"__builtins__": {}, "range": range, "tuple": tuple, "list": list, "dict": dict}


def const(rel: str, name: str):
    """Module-level constant ``name`` of ``rel`` (literal or a range/tuple expression) and its line."""
    tree = ast.parse(text(rel))
    for node in tree.body:
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets, value = [node.target], node.value
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name:
                return _eval(value), f"{rel}:{node.lineno}"
            if isinstance(t, ast.Tuple) and isinstance(value, ast.Tuple):
                for el, v in zip(t.elts, value.elts):
                    if isinstance(el, ast.Name) and el.id == name:
                        return _eval(v), f"{rel}:{node.lineno}"
    raise SystemExit(f"CHECKER ERROR: constant {name} not found in {rel}")


def _eval(node):
    try:
        return ast.literal_eval(node)
    except ValueError:
        return eval(compile(ast.Expression(node), "<const>", "eval"), dict(_SAFE))


def intervals(values) -> list[tuple[int, int]]:
    """Merge an iterable of ints and/or (lo, hi) pairs into sorted disjoint inclusive intervals."""
    pts: list[tuple[int, int]] = []
    for v in values:
        if isinstance(v, tuple):
            pts.append(v)
        else:
            pts.append((v, v))
    pts.sort()
    out: list[tuple[int, int]] = []
    for lo, hi in pts:
        if out and lo <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out


def fmt(ivs: list[tuple[int, int]], limit: int = 6) -> str:
    parts = [f"{a}" if a == b else f"{a}–{b}" for a, b in ivs]
    n = sum(b - a + 1 for a, b in ivs)
    if len(parts) > limit:
        parts = parts[: limit - 2] + ["…"] + parts[-2:]
    return ", ".join(parts) + (f" ({n} values)" if n > 1 else "")


# ---------------------------------------------------------------------------------------------------
# Part 1: inventory


INV: list[dict] = []


def add(study: str, role: str, values, rule: str, source: str, init: bool = False, primary: bool = True) -> None:
    """``primary`` False marks the conservative catch-all entries (config walk, literal scan), which
    duplicate specific entries; the draft report lists collisions with primary entries only."""
    ivs = intervals(values)
    INV.append({"study": study, "role": role, "ivs": ivs, "rule": rule, "source": source, "init": init, "primary": primary})


def p9_layout(base: int, nulls=(20, 30), templates_plus_one: bool = True) -> list[int]:
    """P9's rehearsal layout: 14 data seeds at base+0..13, null seeds at base+20..22 and base+30..32;
    random.Random(templates_seed + 1) makes base+2 (inside the set)."""
    vals = [base + i for i in range(14)] + [base + nulls[0] + i for i in range(3)] + [base + nulls[1] + i for i in range(3)]
    if templates_plus_one:
        vals.append(base + 1 + 1)
    return vals


def build_inventory() -> None:
    # --- configs: every integer under a key path containing "seed" (conservative: strides and offsets included)
    for path in sorted((ROOT / "configs").glob("*.toml")):
        rel = f"configs/{path.name}"
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        found: set[int] = set()

        def walk(node, under: bool) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, under or "seed" in str(k).lower())
            elif isinstance(node, list):
                for v in node:
                    walk(v, under)
            elif isinstance(node, int) and not isinstance(node, bool) and under:
                found.add(node)

        walk(data, False)
        if found:
            add(rel.split("/")[1].split("_")[0].upper(), "config literal", found,
                "every integer under a key containing 'seed' (strides and offsets included, conservative)", rel,
                init=False, primary=False)

    # --- E0 / P1 (pilot) ---------------------------------------------------------------------
    seeds, src = const("src/arborlm/pilot_config.py", "SEEDS")
    add("P1", "initialization", seeds, "torch/python seed; Memory(variant, seed) draws seed+1000..+5000", src, init=True)
    add("P1", "initialization (derived)", [s + 1000 * k for s in seeds for k in range(1, 6)],
        "seed + 1000k, k=1..5 (keys, values, wq, wo, router)", line_of("src/arborlm/pilot_model.py", r"seed \+ 1000\)"))
    add("P1 diagnostic", "permutation", [9001 + s for s in seeds] + [10001 + s for s in seeds],
        "9001 + seed, 10001 + seed", line_of("src/arborlm/diagnose_memory.py", r"9001 \+ seed"))
    add("E0", "initialization", [42], "torch.manual_seed(42) (engine.py); E0 torch/python seed 42",
        line_of("src/arborlm/engine.py", r"manual_seed\(42\)"), init=True)
    add("misc", "literal", [0, 1, 12], "Random(0) state restore, Random(1) (p7b_budget), Generator(0), Generator(12) (p10s0 synthetic)",
        line_of("studies/p10s0/synthetic.py", r"manual_seed\(12\)"))

    # --- P2 / P3 --------------------------------------------------------------------------------
    p2 = tomllib.loads(text("configs/p2_optimization_followup.toml"))
    add("P2/P3", "initialization", p2["backbone_seeds"] + p2["memory_seeds"],
        "backbone (default generator) and memory seeds; Memory draws seed+1000..+5000",
        "configs/p2_optimization_followup.toml:5", init=True)
    add("P2/P3", "data (order)", p2["order_seeds"], "batch-order seeds", "configs/p2_optimization_followup.toml:7")
    add("P2/P3", "permutation", [20000 + i for i in range(27)] + [30000 + i for i in range(27)],
        "20000 + cell index, 30000 + cell index; index = 9(b-101)+3(o-301)+(m-201) in 0..26",
        line_of("src/arborlm/p2_model.py", r"20000 \+ cell.index"))

    # --- P4 / P5 --------------------------------------------------------------------------------
    s4, src4 = const("src/arborlm/p4_config.py", "SEEDS")
    s5, src5 = const("src/arborlm/p5_config.py", "SEEDS")
    add("P4", "initialization", list(s4) + [0], "Memory seed+1000..+5000; DenseAdapter seed+3000, +4000; baseline 0", src4, init=True)
    add("P4", "permutation", [40000 + i for i in range(27)] + [50000 + i for i in range(27)],
        "40000 + index, 50000 + index (index 0..26)", line_of("src/arborlm/p4_model.py", r"40000 \+ model"))
    add("P5", "initialization", list(s5) + [0], "as P4", src5, init=True)
    add("P5", "permutation", [60000 + i for i in range(27)] + [70000 + i for i in range(27)],
        "60000 + index, 70000 + index (index 0..26)", line_of("src/arborlm/p5_model.py", r"60000 \+ model"))

    # --- P6 -------------------------------------------------------------------------------------
    fx, srcfx = const("src/arborlm/p6_equivalence.py", "FIXTURE_SEED")
    add("P6", "permutation", [9000 + i for i in range(27)], "9000 + pair_index (P5 cell index 0..26)",
        line_of("src/arborlm/p6_common.py", r"9000 \+ pair_index"))
    add("P6", "test", [fx], "constructed-tie fixture seed", srcfx)

    # --- P7-A / P7-B -----------------------------------------------------------------------------------
    a = "src/arborlm/p7a_core.py"
    vals = []
    for name in ("RAND_SEEDS", "FM_SEEDS"):
        v, _ = const(a, name)
        vals += list(v)
    for name in ("ORDER_SHUFFLE_SEED", "CONTEXT_SHUFFLE_SEED", "BOOTSTRAP_SEED", "INDEPENDENT_SELECTION_SEED"):
        v, _ = const(a, name)
        vals.append(v)
    add("P7-A", "permutation/panel", vals, "named constants; null generator replicate_seed*1000 + cell index (rule R3)",
        const(a, "RAND_SEEDS")[1])
    b = "src/arborlm/p7b_core.py"
    vals = list(const(b, "CAL_NULL_SEEDS")[0]) + list(const(b, "STREAM_B_NULL_SEEDS")[0]) + list(const(b, "PARTITION_SEEDS")[0])
    add("P7-B", "permutation/panel", vals, "named constants; null generator s*1000 + cell index (rule R3)", const(b, "CAL_NULL_SEEDS")[1])
    add("P7-A/P7-B", "test (budget)", [7001, 7002, 8001, 8002], "synthetic_trace seeds 7001, 7002 and seed + 1000",
        line_of("src/arborlm/p7a_study.py", r"seed \+ 1000\)") + "; " + line_of("src/arborlm/p7b_budget.py", r"seed \+ 1000\)"))

    # --- P8 / P8 supplement ---------------------------------------------------------------------------
    c = "src/arborlm/p8_core.py"
    s8, src8 = const(c, "SEEDS")
    add("P8", "initialization", s8, "Memory(variant, seed) via P5 Model: seed+1000..+5000", src8, init=True)
    vals = list(const(c, "PARTITION_SEEDS")[0]) + list(const(c, "PANEL_A_NULL_SEEDS")[0]) + list(const(c, "PANEL_B_NULL_SEEDS")[0]) + [const(c, "ORDER_SHUFFLE_SEED")[0]]
    add("P8", "panel/permutation", vals, "partition, panel null (s*1000 + cell index, rule R3) and order-shuffle seeds", const(c, "PARTITION_SEEDS")[1])
    off, srcoff = const(c, "PERMUTE_SEED_OFFSET")
    add("P8", "permutation", [off + i for i in range(60)] + [7000 + i for i in range(60)]
        + [8000 + bb * 10 + oo for bb in (101, 102, 103) for oo in (301, 302, 303)],
        "80000 + index; 7000 + index (index 0..59); 8000 + 10*backbone + order",
        f"{srcoff}; " + line_of("src/arborlm/p8_eval.py", r"7000 \+ cell.index") + "; " + line_of(c, r"8000 \+ cell.backbone"))

    # --- P9 ---------------------------------------------------------------------------------------
    p = "studies/p9/core.py"
    ds, srcds = const(p, "DATA_SEEDS")
    na, _ = const(p, "NULL_SEEDS_A")
    nb, _ = const(p, "NULL_SEEDS_B")
    ini, srcini = const(p, "INIT_SEEDS")
    rb, srcrb = const(p, "REHEARSAL_SEED_BASE")
    stride, _ = const(p, "REHEARSAL_STRIDE")
    dry, srcdry = const("studies/p9/stages.py", "DRY_DRAW")
    add("P9", "data (registered)", list(ds.values()) + [ds["templates"] + 1] + list(na) + list(nb),
        "named data seeds; templates_seed + 1; null seeds", srcds)
    add("P9", "initialization", ini, "studies/p9/model.py: seed+1000..+5000", srcini, init=True)
    draws = list(range(10)) + [dry]
    reh = [v for k in draws for v in p9_layout(rb + stride * k)]
    add("P9 (+P9-I, P9-II)", "rehearsal/calibration/DRY", reh,
        f"draw k: {rb} + {stride}k + (0..13, 20..22, 30..32); k = 0..9 and DRY draw {dry}; code bound: any k >= 0 (see unknowns)",
        f"{srcrb}; {srcdry}")
    add("P9 rehearsal (as reserved by P9-II)", "rehearsal (target, stream)", [rb + stride * k + o + j for k in range(10) for o in (40, 60) for j in (0, 1)],
        "P9-II seed_values adds target +40/+41 and stream +60/+61 to every P9 rehearsal draw 0..9",
        line_of("studies/p9ii/core.py", r"P9_REHEARSAL_DRAWS = "))
    reh_init = [rb + stride * k + j for k in draws for j in (0, 1)]
    add("P9 (+P9-I)", "initialization (rehearsal-derived)", reh_init,
        "rehearsal init = rehearsal facts seed + (cell seed - first init seed), j = 0, 1; then +1000k",
        line_of("studies/p9i/core.py", r"return seeds.facts \+ \(cell.seed"), init=True)

    # --- P9-I -------------------------------------------------------------------------------------
    q = "studies/p9i/core.py"
    base, srcb = const(q, "REGISTERED_DATA_SEED_BASE")
    add("P9-I", "data (registered)", [base + i for i in range(20)], "base + 0..13 data, +14..16 / +17..19 nulls", srcb)
    ini1, s1 = const(q, "INIT_SEEDS")
    cal1, s2 = const(q, "CALIBRATION_INIT_SEEDS")
    add("P9-I", "initialization", list(ini1) + list(cal1),
        "studies/p9i/model.py: seed+1000..+8000 (attention arms use +6000..+8000)", f"{s1}; {s2}", init=True)
    tb, srct = const(q, "TEST_SEED_BASE")
    tests = [v for k in range(3) for v in p9_layout(tb + 100 * k)]
    add("P9-I", "test", tests, "base + 100k, k = 0..2, P9 rehearsal layout", srct)
    add("P9-I", "initialization (test-derived)", [tb + 100 * k + j for k in range(3) for j in (0, 1)],
        "test sets may run in rehearsal mode: init = facts + j; then +1000..+8000", srct, init=True)

    # --- P9-II ------------------------------------------------------------------------------------
    r = "studies/p9ii/core.py"
    reg, srcr = const(r, "REGISTERED_BASE")
    st, _ = const(r, "DRAW_STRIDE")
    res, _ = const(r, "RESERVE_BASES")
    to, _ = const(r, "TARGET_OFFSET")
    so, _ = const(r, "STREAM_OFFSET")
    sets = [reg + st * (d - 1) for d in range(1, 15)] + list(res.values())
    vals = [bb + i for bb in sets for i in range(20)] + [bb + o + j for bb in sets for o in (to, so) for j in (0, 1)]
    add("P9-II", "data (registered + reserve)", vals, f"draws 1..14 at {reg} + {st}(d-1), reserves {list(res.values())}; +0..19, +{to}/{to+1}, +{so}/{so+1}", srcr)
    cal_sets = [rb + stride * k for k in (3, 4, 5)]
    add("P9-II", "calibration/rehearsal (target, stream)", [bb + o + j for bb in cal_sets for o in (to, so) for j in (0, 1)],
        "P9 rehearsal sets 3, 4, 5 plus target/stream offsets", srcr)
    i2, s3 = const(r, "INIT_SEEDS")
    c2, s4_ = const(r, "CALIBRATION_INIT_SEED")
    add("P9-II", "initialization", list(i2) + [c2, c2 + 1], "1901 + j; calibration 1891 + j; P9 model +1000..+5000", f"{s3}; {s4_}", init=True)
    tlo, srctl = const(r, "TEST_SEED_BASE")
    thi, _ = const(r, "TEST_SEED_TOP")
    add("P9-II", "test", [(tlo, thi)], "declared test range (whole)", srctl)

    # --- P10-S0 -----------------------------------------------------------------------------------
    z = "studies/p10s0/core.py"
    reg, srcz = const(z, "REGISTERED_BASE")
    st, _ = const(z, "DRAW_STRIDE")
    nd, _ = const(z, "N_DRAWS")
    res, _ = const(z, "RESERVE_BASES")
    cb, _ = const(z, "CHECK_BASE")
    rhb, _ = const(z, "REHEARSAL_BASE")
    fso, _ = const(z, "FACT_SET_OFFSET")
    tgo, _ = const(z, "TARGET_OFFSET")
    swo, _ = const(z, "SWAP_OFFSET")
    sets = [reg + st * (d - 1) for d in range(1, nd + 1)] + list(res.values()) + [cb, rhb]
    vals = [bb + f + i for bb in sets for f in fso.values() for i in range(20)]
    vals += [bb + o + j for bb in sets for o in tgo.values() for j in (0, 1)] + [bb + o for bb in sets for o in swo.values()]
    add("P10-S0", "data (registered, reserve, check, rehearsal)", vals,
        f"set base + fact-set offset {sorted(fso.values())} + 0..19; target +{sorted(set(tgo.values()))}+j; swap +{sorted(swo.values())}", srcz)
    lo_, _ = const(z, "S0_RANGE")
    add("P10-S0", "declared namespace", [tuple(lo_)], "S0_RANGE (whole, reserved)", const(z, "S0_RANGE")[1])
    i0, si0 = const(z, "INIT_SEEDS")
    ci, sci = const(z, "CHECK_INIT")
    ri, _ = const(z, "REHEARSAL_INIT")
    add("P10-S0", "initialization", list(i0) + [ci, ri], "P9 model via P9-II: seed+1000..+5000", f"{si0}; {sci}", init=True)
    t0, st0 = const(z, "TEST_SEED_BASE")
    t1, _ = const(z, "TEST_SEED_TOP")
    add("P10-S0", "test", [(t0, t1)], "declared test range (whole)", st0)

    # --- P10-S1 -----------------------------------------------------------------------------------
    y = "studies/p10s1/core.py"
    reg, sry = const(y, "REGISTERED_BASE")
    st, _ = const(y, "DRAW_STRIDE")
    reps, _ = const(y, "REPLICATES")
    cbs, _ = const(y, "CALIBRATION_BASES")
    rhb, _ = const(y, "REHEARSAL_BASE")
    h8, _ = const(y, "H8_OFFSET")
    mo, _ = const(y, "MASK_OFFSETS")
    io, _ = const(y, "INDEX_OFFSET")
    sets = [reg + st * (r_ - 1) for r_ in range(1, reps + 1)] + list(cbs) + [rhb]
    vals = [v for bb in sets for v in p9_layout(bb, templates_plus_one=False)] + [bb + o for bb in sets for o in (h8, *mo, io)]
    add("P10-S1", "data (registered, calibration, rehearsal)", vals,
        f"set base + 0..13, +20..22, +30..32, +{h8}, +{mo[0]}..{mo[-1]}, +{io}", sry)
    rng, srng = const(y, "SEED_RANGE")
    add("P10-S1", "declared namespace", [tuple(rng)], "SEED_RANGE (whole, reserved)", srng)
    sbi, ssb = const(y, "SEED_BLOCK_INITS")
    inits = [2100 + r_ for r_ in range(1, reps + 1)] + list(sbi.values()) + [const(y, n)[0] for n in ("CALIBRATION_INIT_SEED", "REHEARSAL_INIT_SEED", "CALIBRATION_INIT_SEED_DRAW2")]
    add("P10-S1", "initialization", inits, "2100 + r; seed block 21<extra><draw>; 2191-2193; DERIVED_INIT_OFFSETS +1000..+5000",
        line_of(y, r"return 2100 \+ replicate") + "; " + ssb, init=True)
    t0, st1 = const(y, "TEST_SEED_BASE")
    t1, _ = const(y, "TEST_SEED_TOP")
    add("P10-S1", "test", [(t0, t1)], "declared test range (whole)", st1)

    # --- P10-S2 -----------------------------------------------------------------------------------
    cfg = tomllib.loads(text("configs/p10s2_transfer.toml"))["seeds"]
    srcs2 = line_of("configs/p10s2_transfer.toml", r"^\[seeds\]")
    offs = cfg["offsets"]
    vals = [bb + o for bb in cfg["replicate_bases"] for o in offs] + [cfg["partition"]] + cfg["partition_streams"]
    add("P10-S2", "data (registered + partition side)", vals, "replicate base + offsets 0..10; partition 220901 and streams 220902..220912", srcs2)
    cal = [cfg["calibration_base"] + cfg["draw_stride"] * i + o for i in range(cfg["draw_count"]) for o in offs]
    reh2 = [cfg["rehearsal_base"] + cfg["draw_stride"] * i + o for i in range(cfg["draw_count"]) for o in offs]
    add("P10-S2", "calibration", cal, "221001 + 100i + offset, i < draw_count", srcs2)
    add("P10-S2", "rehearsal", reh2, "222001 + 100i + offset, i < draw_count", srcs2)
    add("P10-S2", "declared namespace", [(cfg["registered_low"], cfg["registered_high"]), (cfg["calibration_low"], cfg["calibration_high"]),
        (cfg["rehearsal_low"], cfg["rehearsal_high"]), (cfg["test_low"], cfg["test_high"])], "registered, calibration, rehearsal, test ranges (whole)", srcs2)
    add("P10-S2", "test (stand-ins)", [1, 2, 3, 4, 5, 6], "standins data_seed_offset (default 0) + 1..6",
        line_of("studies/p10s2/standins.py", r"data_seed_offset \+ 1"), init=False)

    # --- review diagnostics listed by the P10 G9 gates ----------------------------------------------
    add("Review diagnostics", "initialization", [(500001, 500004)], "init seeds of the ADR-0019 design review scripts (c7 uses +1000..+4000)",
        line_of("studies/p10s1/core.py", r'"review diagnostics"'), init=True)
    add("Review diagnostics", "unknown role", [941001], "listed by P10-S1/P10-S2 G9; origin not found in the repository",
        line_of("studies/p10s1/core.py", r'"review diagnostics"'), init=True)

    # --- ranges listed by later studies' G9 for earlier ones (kept as reserved, conservative) ------------
    add("P9/P9-I/P9-II (as listed by P10 G9)", "declared namespace",
        [(170001, 171343), (179001, 179933), (182001, 182020), (180101, 181900), (900001, 900233), (190001, 191599)],
        "OTHER_STUDY_RANGES of P10-S1", line_of("studies/p10s1/core.py", r"^OTHER_STUDY_RANGES"))

    # --- literal scan of code and tests for seed-like integer literals ------------------------------------
    rx = re.compile(r"(?:manual_seed\(|Random\(|\bseed\w*\s*[=:]\s*|\bseeds?\s*=\s*[\(\[])\s*(\d{1,7})\b")
    found: dict[int, str] = {}
    for d in ("src/arborlm", "studies", "tests"):
        for path in sorted((ROOT / d).rglob("*.py")):
            rel = str(path.relative_to(ROOT))
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for m in rx.finditer(line):
                    found.setdefault(int(m.group(1)), f"{rel}:{i}")
    add("All code and tests", "literal scan", list(found), "integer literal right after manual_seed(, Random(, seed=, seeds=( (regex)",
        f"{len(found)} literals in src/arborlm, studies, tests", init=False, primary=False)


# ---------------------------------------------------------------------------------------------------
# Part 2: P10-I allocation (must equal SEED_REGISTRY.md section 4; drafts as read at commit fd86a0b)

ALLOC: list[tuple[str, str, int, int]] = [
    # study, role, lo, hi (inclusive). Roles containing "init" are initialization seeds.
    ("P10-I-S0 ADR-0023", "data: registered (10) + reserve (4) draw sets", 300001, 306999),
    ("P10-I-S0 ADR-0023", "auxiliary: permutation / controls / bootstrap", 307001, 308999),
    ("P10-I-S0 ADR-0023", "calibration draw sets (2)", 309001, 309199),
    ("P10-I-S0 ADR-0023", "rehearsal draw set (1)", 309201, 309299),
    ("P10-I-S0 ADR-0023", "pipeline-check set (1)", 309301, 309399),
    ("P10-I-S0 ADR-0023", "spare", 309401, 309999),
    ("P10-I-S0 ADR-0023", "init sub-row", 330001, 330099),
    ("P10-I-S0 ADR-0023", "test", 932001, 932999),
    ("P10-I-S1 ADR-0024", "data: registered draw sets (5)", 240001, 246999),
    ("P10-I-S1 ADR-0024", "lane L data sets (5)", 247001, 247999),
    ("P10-I-S1 ADR-0024", "auxiliary: spare", 248001, 248999),
    ("P10-I-S1 ADR-0024", "calibration draw sets (2)", 249001, 249199),
    ("P10-I-S1 ADR-0024", "rehearsal draw set (1)", 249201, 249299),
    ("P10-I-S1 ADR-0024", "spare", 249301, 249999),
    ("P10-I-S1 ADR-0024", "init sub-row", 330101, 330199),
    ("P10-I-S1 ADR-0024", "test", 933001, 933999),
    ("P10-I-S2 ADR-0025", "data: registered replicate sets (3)", 250001, 250899),
    ("P10-I-S2 ADR-0025", "partition side and analysis", 250901, 250999),
    ("P10-I-S2 ADR-0025", "calibration", 251001, 251999),
    ("P10-I-S2 ADR-0025", "rehearsal", 252001, 252999),
    ("P10-I-S2 ADR-0025", "spare", 253001, 259999),
    ("P10-I-S2 ADR-0025", "init sub-row", 330201, 330299),
    ("P10-I-S2 ADR-0025", "test", 934001, 934999),
    ("P10-I-S3 ADR-0026", "registered streams and permutations", 260001, 266999),
    ("P10-I-S3 ADR-0026", "auxiliary: spare", 267001, 268999),
    ("P10-I-S3 ADR-0026", "calibration streams and permutations", 269001, 269199),
    ("P10-I-S3 ADR-0026", "dry-rehearsal streams and permutations", 269201, 269299),
    ("P10-I-S3 ADR-0026", "spare", 269301, 269999),
    ("P10-I-S3 ADR-0026", "init sub-row", 330301, 330399),
    ("P10-I-S3 ADR-0026", "test", 935001, 935999),
    ("P10-I-S4 ADR-0027", "data: registered draw sets (5)", 270001, 276999),
    ("P10-I-S4 ADR-0027", "auxiliary", 277001, 278999),
    ("P10-I-S4 ADR-0027", "calibration draw sets (2)", 279001, 279199),
    ("P10-I-S4 ADR-0027", "rehearsal draw set (1)", 279201, 279299),
    ("P10-I-S4 ADR-0027", "spare", 279301, 279999),
    ("P10-I-S4 ADR-0027", "init sub-row", 330401, 330499),
    ("P10-I-S4 ADR-0027", "test", 936001, 936999),
    ("P10-I-S5 ADR-0028", "data: registered workloads / stores / orders", 280001, 286999),
    ("P10-I-S5 ADR-0028", "auxiliary", 287001, 288999),
    ("P10-I-S5 ADR-0028", "calibration (R1)", 289001, 289199),
    ("P10-I-S5 ADR-0028", "rehearsal", 289201, 289299),
    ("P10-I-S5 ADR-0028", "spare", 289301, 289999),
    ("P10-I-S5 ADR-0028", "init sub-row", 330501, 330599),
    ("P10-I-S5 ADR-0028", "test", 937001, 937999),
    ("P10-I-R ADR-0029", "data: bridge draw sets (5)", 290001, 296999),
    ("P10-I-R ADR-0029", "auxiliary: spare", 297001, 297999),
    ("P10-I-R ADR-0029", "I64 index seeds (3)", 298001, 298999),
    ("P10-I-R ADR-0029", "calibration (held; none needed)", 299001, 299199),
    ("P10-I-R ADR-0029", "rehearsal draw set (1)", 299201, 299299),
    ("P10-I-R ADR-0029", "spare", 299301, 299999),
    ("P10-I-R ADR-0029", "init sub-row", 330601, 330699),
    ("P10-I-R ADR-0029", "test", 938001, 938999),
    ("P10-I spare", "init sub-rows for supplements", 330701, 330999),
]

# Named seeds inside the init sub-rows (SEED_REGISTRY.md section 4.2); each must lie in its study's sub-row.
NAMED_INIT = {
    "P10-I-S0 ADR-0023": {"registered": [330001, 330002], "calibration": [330091, 330093], "rehearsal + pipeline check": [330092], "test mode": [330098, 330099]},
    "P10-I-S1 ADR-0024": {"registered": [330101, 330102, 330103, 330104, 330105], "lane L (if separate)": [330111, 330112, 330113, 330114, 330115],
                          "calibration": [330191, 330193], "rehearsal": [330192], "test mode": [330198, 330199]},
    "P10-I-S2 ADR-0025": {"registered r=0..2 x 8 roles": [330201 + 10 * r + j for r in range(3) for j in range(8)],
                          "calibration i=0,1 x 8 roles": [330231 + 10 * i + j for i in range(2) for j in range(8)],
                          "rehearsal i=0 x 8 roles": [330251 + j for j in range(8)], "test mode": [330298, 330299]},
    "P10-I-S3 ADR-0026": {"registered": [330301, 330302, 330303], "calibration": [330391], "dry rehearsal": [330392], "test mode": [330398, 330399]},
    "P10-I-S4 ADR-0027": {"registered": [330401, 330402, 330403, 330404, 330405], "calibration": [330491, 330492], "rehearsal": [330495], "test mode": [330498, 330499]},
    "P10-I-S5 ADR-0028": {"registered": [330501, 330502, 330503, 330504, 330505], "calibration": [330591], "rehearsal": [330592], "test mode": [330598, 330599]},
    "P10-I-R ADR-0029": {"bridge": [330601, 330602, 330603, 330604, 330605], "rehearsal": [330692], "test mode": [330698, 330699]},
}

# The drafts' own proposals as read on 2026-11-17 (for the report of collisions; not allocations).
DRAFTS: list[tuple[str, str, int, int]] = [
    ("ADR-0023 draft 1", "init", 3001, 3002), ("ADR-0023 draft 1", "init", 3091, 3092),
    ("ADR-0023 draft 1", "data", 300001, 309999),
    ("ADR-0024 draft 1", "init", 2401, 2405), ("ADR-0024 draft 1", "init", 2491, 2493),
    ("ADR-0024 draft 1", "data", 240001, 249999), ("ADR-0024 draft 1", "test", 924001, 924999),
    ("ADR-0025 draft 1", "data", 250001, 259999), ("ADR-0025 draft 1", "test", 259001, 259999),
    ("ADR-0026", "init", 2601, 2699), ("ADR-0026", "data", 260001, 269999), ("ADR-0026", "test", 926001, 926999),
    ("ADR-0027", "init", 2701, 2799), ("ADR-0027", "data", 270001, 279999),
    ("ADR-0028", "data", 280001, 289999),
]


# ---------------------------------------------------------------------------------------------------
# expansion rules


def expand(ivs, init: bool, small_init: bool, all_shift: bool = False, small_r3: bool = False):
    """(label, lo, hi) intervals: identity; R2 = +1000k (k=1..K_MAX) for init seeds (and for every value
    < SMALL_LITERAL when small_init, or for every value when all_shift); R3 = s*1000 + [0, 999] for every
    value >= 1000 (every value when small_r3)."""
    out = []
    for lo, hi in ivs:
        out.append(("id", lo, hi))
        shift_iv = []
        if init or all_shift:
            shift_iv.append((lo, hi))
        elif small_init and lo < SMALL_LITERAL:
            shift_iv.append((lo, min(hi, SMALL_LITERAL - 1)))
        for a, b in shift_iv:
            for k in range(1, K_MAX + 1):
                out.append((f"+{1000 * k}", a + 1000 * k, b + 1000 * k))
        a = lo if small_r3 else max(lo, 1000)
        if a <= hi:
            out.append(("x1000+i", a * 1000, hi * 1000 + INDEX_SPAN - 1))
    return out


class Index:
    def __init__(self, items):  # items: (lo, hi, tag)
        self.items = sorted(items)
        self.los = [it[0] for it in self.items]
        self.maxspan = max((it[1] - it[0] for it in self.items), default=0)

    def hits(self, lo, hi):
        j = bisect.bisect_right(self.los, hi)
        i = bisect.bisect_left(self.los, lo - self.maxspan)
        return [it for it in self.items[i:j] if it[1] >= lo and it[0] <= hi]


def inventory_index(all_shift=False, small_r3=False) -> Index:
    items = []
    for n, e in enumerate(INV):
        for tag, lo, hi in expand(e["ivs"], e["init"], True, all_shift, small_r3):
            items.append((lo, hi, (n, tag)))
    return Index(items)


def is_init(role: str) -> bool:
    return "init" in role


def draft_hits(inv_idx: Index, d):
    study, role, lo, hi = d
    actual, conservative = {}, 0
    for tag, x, y in expand([(lo, hi)], is_init(role), False):
        for ilo, ihi, (n, itag) in inv_idx.hits(x, y):
            e = INV[n]
            ov = (max(x, ilo), min(y, ihi))
            if e["primary"] and (itag == "id" or e["init"] or itag == "x1000+i"):
                key = f"{study} {role} [{tag}] {ov[0]}..{ov[1]} = {e['study']} / {e['role']} [{itag}] ({e['source']})"
                actual[key] = 1
            else:
                conservative += 1
    return list(actual), conservative


def check_allocations(inv_idx: Index, allocs, all_shift=False, small_r3=False):
    return [h[-1] for h in check_structured(inv_idx, allocs, all_shift, small_r3)]


def check_structured(inv_idx: Index, allocs, all_shift=False, small_r3=False):
    """Hits as (alloc study, alloc role, other study, other role, message)."""
    problems = []
    exp = []
    for a, (study, role, lo, hi) in enumerate(allocs):
        for tag, x, y in expand([(lo, hi)], is_init(role), False, all_shift, small_r3):
            exp.append((x, y, a, tag))
            for ilo, ihi, (n, itag) in inv_idx.hits(x, y):
                e = INV[n]
                ov = (max(x, ilo), min(y, ihi))
                problems.append((study, role, e["study"], e["role"], f"{study} / {role} [{tag}] {ov[0]}..{ov[1]} hits inventory: {e['study']} / {e['role']} [{itag}] ({e['source']})"))
    # pairwise between allocations
    idx = Index([(x, y, (a, tag)) for x, y, a, tag in exp])
    seen = set()
    for x, y, a, tag in exp:
        for ilo, ihi, (b, btag) in idx.hits(x, y):
            if b == a:
                continue
            key = (min(a, b), max(a, b), tag, btag) if a < b else (b, a, btag, tag)
            if key in seen:
                continue
            seen.add(key)
            ov = (max(x, ilo), min(y, ihi))
            problems.append((allocs[a][0], allocs[a][1], allocs[b][0], allocs[b][1], f"{allocs[a][0]} / {allocs[a][1]} [{tag}] and {allocs[b][0]} / {allocs[b][1]} [{btag}] share {ov[0]}..{ov[1]}"))
    return problems


# ---------------------------------------------------------------------------------------------------
# optional cross-check against the studies' own seed functions (import; needs the locked environment)


def import_crosscheck():
    sys.path.insert(0, str(ROOT))
    ident = intervals([iv for e in INV for iv in e["ivs"]])
    los = [a for a, _ in ident]

    def inside(v):
        i = bisect.bisect_right(los, v) - 1
        return i >= 0 and ident[i][0] <= v <= ident[i][1]

    report, missing = [], []
    try:
        import importlib

        p9 = importlib.import_module("studies.p9.core")
        p9i = importlib.import_module("studies.p9i.core")
        p9ii = importlib.import_module("studies.p9ii.core")
        s0 = importlib.import_module("studies.p10s0.core")
        s1 = importlib.import_module("studies.p10s1.core")
        s2 = importlib.import_module("studies.p10s2.core")
    except Exception as exc:  # torch missing outside the locked environment
        return [f"SKIPPED (import failed: {type(exc).__name__}: {exc})"], []
    groups = {"P9 registered_seed_values": set(p9.registered_seed_values())}
    for name, vals in p9i.seed_namespaces().items():
        groups[f"P9-I {name}"] = set(vals)
    for name, vals in p9ii.seed_namespaces().items():
        groups[f"P9-II {name}"] = set(vals)
    for name, vals in s0.seed_namespaces().items():
        groups[f"P10-S0 {name}"] = set(vals)
    for name, vals in s1.seed_namespaces().items():
        groups[f"P10-S1 {name}"] = set(vals)
    for mode in ("registered-run", "calibration", "rehearsal", "test", "registered-data", "registered-analysis"):
        try:
            groups[f"P10-S2 allowed_seeds({mode})"] = set(s2.allowed_seeds(mode))
        except Exception as exc:
            report.append(f"P10-S2 allowed_seeds({mode}): {type(exc).__name__}")
    groups["P10-S2 listed_partition_seeds"] = set(s2.listed_partition_seeds().values())
    # S1's derived_init uses k = 1..5 from DERIVED_INIT_OFFSETS: compare with R2 of the reconstructed init seeds
    init_seeds = {v for e in INV if e["init"] for lo, hi in e["ivs"] for v in range(lo, hi + 1) if hi - lo < 100000}
    r2 = {v + 1000 * k for v in init_seeds for k in range(1, K_MAX + 1)}
    for name, vals in sorted(groups.items()):
        if "derived" in name:
            miss = sorted(v for v in vals if v not in r2 and not inside(v))
        else:
            miss = sorted(v for v in vals if not inside(v))
        report.append(f"{name}: {len(vals)} seeds, {len(miss)} outside the reconstruction")
        if miss:
            missing.append(f"{name}: {miss[:10]}")
    return report, missing


# ---------------------------------------------------------------------------------------------------
# literal scan of the repository for integers inside the P10-I allocations (informational)


def literal_scan(allocs):
    rx = re.compile(r"(?<![\w.])(\d{6})(?![\w.])")
    skip = {"docs/decisions/ADR-0023", "docs/decisions/ADR-0024", "docs/decisions/ADR-0025", "docs/decisions/ADR-0026",
            "docs/decisions/ADR-0027", "docs/decisions/ADR-0028", "docs/reviews/p10-i-"}
    idx = Index([(lo, hi, (study, role)) for study, role, lo, hi in allocs])
    hits = []
    for d in ("configs", "src", "studies", "tests", "docs/decisions", "docs/reviews"):
        for path in sorted((ROOT / d).rglob("*")):
            if not path.is_file() or path.suffix not in ((".md",) if d == "docs/decisions" else (".py",) if d == "docs/reviews" else (".py", ".toml")):
                continue
            rel = str(path.relative_to(ROOT))
            if any(rel.startswith(s) for s in skip):
                continue
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                for m in rx.finditer(line):
                    v = int(m.group(1))
                    for _, _, (study, role) in idx.hits(v, v):
                        hits.append(f"{rel}:{i}: {v} in {study} / {role}")
    return hits


# ---------------------------------------------------------------------------------------------------


def main() -> int:
    tables = "--tables" in sys.argv
    build_inventory()
    print("SEED REGISTRY CHECK (P10-I) — arbor-auditor, standard library only")
    print(f"root: {ROOT}")
    print(f"rules: R1 identity; R2 s+1000k, k=1..{K_MAX}, on initialization seeds and on every inventory literal < {SMALL_LITERAL};"
          f" R3 s*1000+i, i in [0,{INDEX_SPAN - 1}], on every value >= 1000; in-set offsets enumerated per study")
    print(f"inventory: {len(INV)} entries, {sum(b - a + 1 for e in INV for a, b in e['ivs'])} identity values (with overlaps)")
    if tables:
        print("\n| # | Study | Role | Literal values / range | Rule (in-set derivation) | R2 applies | Source |")
        print("|---|---|---|---|---|---|---|")
        for n, e in enumerate(INV, 1):
            r2 = "yes" if e["init"] else ("yes (< 100000)" if e["ivs"][0][0] < SMALL_LITERAL else "no")
            print(f"| {n} | {e['study']} | {e['role']} | {fmt(e['ivs'])} | {e['rule']} | {r2} | {e['source']} |")
    ok = True

    # structural checks of the allocation
    for study, named in NAMED_INIT.items():
        rows = [(lo, hi) for s, role, lo, hi in ALLOC if s == study and is_init(role)]
        for what, vals in named.items():
            for v in vals:
                if not any(lo <= v <= hi for lo, hi in rows):
                    print(f"FAIL: named init seed {v} ({study} {what}) is outside the study's init sub-row")
                    ok = False
        flat = [v for vals in named.values() for v in vals]
        if len(flat) != len(set(flat)):
            print(f"FAIL: repeated named init seed in {study}")
            ok = False
    if tables:
        print("\n| Study | Role | Range | Size |")
        print("|---|---|---|---|")
        for study, role, lo, hi in ALLOC:
            print(f"| {study} | {role} | {lo}–{hi} | {hi - lo + 1} |")

    inv_idx = inventory_index()
    print("\n[1] binding: P10-I allocations (R1-R3 expanded) against the inventory (R1-R3 expanded) and against each other")
    problems = check_allocations(inv_idx, ALLOC)
    print(f"    allocations: {len(ALLOC)}; problems: {len(problems)}")
    for p_ in problems[:40]:
        print("    FAIL:", p_)
    ok &= not problems

    print("\n[2] the drafts' own proposals (as read 2026-11-17) under the same rules, against the inventory only")
    print("    (listed: collisions with a seed the code itself uses or derives; 'conservative' counts hits that exist only through")
    print("     the catch-all entries or the +1000k applied to small literals that are not initialization seeds)")
    for d in DRAFTS:
        actual, conservative = draft_hits(inv_idx, d)
        print(f"    {d[0]} {d[1]} {d[2]}–{d[3]}: {len(actual)} actual collisions, {conservative} conservative-only")
        for p_ in actual[:14]:
            print("      ", p_)
        if len(actual) > 14:
            print(f"       … {len(actual) - 14} more")
    cross = [h[-1] for h in check_structured(inv_idx, DRAFTS) if "share" in h[-1] and h[0].split()[0] != h[2].split()[0]]
    print(f"    between drafts: {len(cross)}")
    for p_ in cross[:10]:
        print("      ", p_)

    print("\n[3] informational (not binding): worst case, +1000k applied to EVERY value of every role, both sides")
    w1 = check_structured(inventory_index(all_shift=True), ALLOC, all_shift=True)
    same = sum(1 for h in w1 if h[0] == h[2])
    print(f"    hits: {len(w1)}; {same} inside one study's own block (not listed); the rest grouped by study pair (roles merged):")
    groups: dict[str, int] = {}
    for a_s, a_r, o_s, o_r, _ in w1:
        if a_s == o_s:
            continue
        key = f"{a_s}  <->  {o_s}" + ("" if o_s.startswith("P10-I") else f" / {o_r}")
        groups[key] = groups.get(key, 0) + 1
    for g, n in sorted(groups.items()):
        print(f"       {n:5d}  {g}")
    print("\n[4] informational (not binding): R3 also applied to values < 1000, both sides")
    w2 = check_allocations(inventory_index(small_r3=True), ALLOC, small_r3=True)
    w2 = [p_ for p_ in w2 if p_ not in problems]
    print(f"    hits: {len(w2)}")
    for p_ in w2[:10]:
        print("      ", p_)

    print("\n[5] informational: six-digit literals inside a P10-I allocation, in configs/*.toml, src, studies, tests (*.py),")
    print("    docs/decisions/*.md (ADR-0023..0028 excluded) and docs/reviews/**/*.py (P10-I review folders excluded); sizes are not seeds")
    lit = literal_scan(ALLOC)
    by_value: dict[str, list[str]] = {}
    for h in lit:
        loc, _, rest = h.partition(": ")
        by_value.setdefault(rest, []).append(loc)
    print(f"    hits: {len(lit)} occurrences of {len(by_value)} distinct values")
    for rest, locs in sorted(by_value.items()):
        print(f"       {rest}: {len(locs)} occurrences, first {locs[0]}")

    print("\n[6] cross-check: every seed the studies' own functions declare lies inside the reconstruction")
    report, missing = import_crosscheck()
    for r_ in report:
        print("    ", r_)
    for m_ in missing:
        print("     MISSING:", m_)
    ok &= not missing

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
