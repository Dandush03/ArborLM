# ruff: noqa
"""Programme-wide seed registry check for P10-I. REVISION 4 (2026-11-19): a new file, as SEED_REGISTRY.md section 4.5
item 5 requires; seed_registry_check.py (revision 2) and seed_registry_check_r3.py (revision 3) are kept unchanged.

Written by the arbor-auditor subagent (model: Claude Opus 5.5) on 2026-11-19. Standard library only (section [6] and
the import half of section [8] import the studies' own seed functions and need the locked environment; without it
they print SKIPPED).

What revision 4 adds to revision 3 (whose rules, inventory and checks are reproduced unchanged):
  * P10-I-S6 (ADR-0031) allocation rows, named initialisation and data values, and its declared re-uses;
  * corrections of record for P10-I-S3 (ADR-0026: the joint-permutation seeds) and P10-I-S5 (ADR-0028: the values its
    revision-4 seed table and frozen config actually use), with section [8] reconstructing the values each executed
    study used from its frozen config / seed plan and asserting they equal the record and lie in that study's rows;
  * the own-files case (ADR-0029 ruling 6) handled inside the checker instead of by text substitution: every inventory
    entry built from a file carries an owner (the P10-I study whose config, code or tests the file is). A hit between a
    study's allocation and an inventory entry owned by that SAME study is the known own-files case and is listed, not
    failed. A hit against an entry owned by a DIFFERENT study, or against an unowned entry, fails as before. Built-in
    owners: P10-I-S3, P10-I-S5, P10-I-R (executed, on main). A later study adds its own files without editing this file:
        --own "P10-I-S6 ADR-0031=configs/p10i_s6_*,studies/p10i_s6/*,tests/test_p10i_s6_*"
    (repeatable; the study label must be an ALLOC study; globs are fnmatch patterns on repository-relative paths, where
    '*' also matches '/').

Usage (from the worktree root):
    uv run --locked python docs/reviews/p10-i-direction-2026-11-17/seed_registry_check_r4.py [--tables] [--own STUDY=GLOBS]... [--root PATH] [--selftest]

--selftest plants three faults (an S6 row on a value P10-I-S3's own files use; an S6 named initialisation value outside
its sub-row; a declared re-use inside an allocation) and must print RESULT: FAIL.

Exit status 0 when every binding check passes, 1 otherwise.
"""

from __future__ import annotations

import ast
import bisect
import fnmatch
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
K_MAX = 10  # seed + 1000*k, k = 1..K_MAX (code uses k <= 5, P9-I k <= 8; 10 is the registry's margin)
INDEX_SPAN = 1000  # s*1000 + index, index in [0, 999] (widest bound that keeps the rule injective)
SMALL_LITERAL = 100_000  # P1-P8 and small constants: +1000k applied conservatively to every literal below this

# Own files of executed P10-I studies on main (ADR-0029 ruling 6). Extended at run time by --own.
OWN_FILES: dict[str, tuple[str, ...]] = {
    "P10-I-S3 ADR-0026": ("configs/p10i_s3_*", "studies/p10i_s3/*", "tests/test_p10is3_*"),
    "P10-I-S5 ADR-0028": ("configs/p10is5_*", "studies/p10is5/*", "tests/test_p10is5_*"),
    "P10-I-R ADR-0029": ("configs/p10ir_*", "studies/p10ir/*", "tests/test_p10ir_*"),
}

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


def owner_of(rel: str) -> str | None:
    owners = [s for s, globs in OWN_FILES.items() if any(fnmatch.fnmatchcase(rel, g) for g in globs)]
    if len(owners) > 1:
        raise SystemExit(f"CHECKER ERROR: {rel} matches the own-file globs of two studies: {owners}")
    return owners[0] if owners else None


# ---------------------------------------------------------------------------------------------------
# Part 1: inventory (revision 3's, with an owner on every entry built from a file)


INV: list[dict] = []


def add(study: str, role: str, values, rule: str, source: str, init: bool = False, primary: bool = True, owner: str | None = None) -> None:
    """``primary`` False marks the conservative catch-all entries (config walk, literal scan), which duplicate specific
    entries; the draft report lists collisions with primary entries only. ``owner``: the P10-I study whose own file the
    entry was read from (ADR-0029 ruling 6), else None."""
    ivs = intervals(values)
    INV.append({"study": study, "role": role, "ivs": ivs, "rule": rule, "source": source, "init": init, "primary": primary, "owner": owner})


def p9_layout(base: int, nulls=(20, 30), templates_plus_one: bool = True) -> list[int]:
    """P9's rehearsal layout: 14 data seeds at base+0..13, null seeds at base+20..22 and base+30..32;
    random.Random(templates_seed + 1) makes base+2 (inside the set)."""
    vals = [base + i for i in range(14)] + [base + nulls[0] + i for i in range(3)] + [base + nulls[1] + i for i in range(3)]
    if templates_plus_one:
        vals.append(base + 1 + 1)
    return vals


LITERAL_RX = re.compile(r"(?:manual_seed\(|Random\(|\bseed\w*\s*[=:]\s*|\bseeds?\s*=\s*[\(\[])\s*(\d{1,7})\b")


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
                init=False, primary=False, owner=owner_of(rel))

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
    # Revision 4: split by owner. Values from files no P10-I study owns form the general entry (as in revision 3);
    # values from a study's own files form one entry per owner (a value in both kinds of file is in both entries).
    general: dict[int, str] = {}
    owned: dict[str, dict[int, str]] = {}
    for d in ("src/arborlm", "studies", "tests"):
        for path in sorted((ROOT / d).rglob("*.py")):
            rel = str(path.relative_to(ROOT))
            own = owner_of(rel)
            target = owned.setdefault(own, {}) if own else general
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for m in LITERAL_RX.finditer(line):
                    target.setdefault(int(m.group(1)), f"{rel}:{i}")
    add("All code and tests", "literal scan", list(general), "integer literal right after manual_seed(, Random(, seed=, seeds=( (regex)",
        f"{len(general)} literals in src/arborlm, studies, tests (files no P10-I study owns)", init=False, primary=False)
    for own, found in sorted(owned.items()):
        if found:
            add(f"{own} own files", "literal scan", list(found), "as above, in the study's own files only",
                f"{len(found)} literals; first {sorted(found.values())[0]}", init=False, primary=False, owner=own)


# ---------------------------------------------------------------------------------------------------
# Part 2: P10-I allocation (SEED_REGISTRY.md section 4 and SEED_REGISTRY_R4.md)

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
    ("P10-I-S1 ADR-0024", "data: block M registered draw sets (5)", 240001, 240499),
    ("P10-I-S1 ADR-0024", "data: block X fresh draw sets (5)", 240501, 240999),
    ("P10-I-S1 ADR-0024", "data: spare draw sets", 241001, 246999),
    ("P10-I-S1 ADR-0024", "lane L data sets (PENDING: decided in the lane L revision)", 247001, 247999),
    ("P10-I-S1 ADR-0024", "auxiliary: spare", 248001, 248999),
    ("P10-I-S1 ADR-0024", "calibration draw sets (2)", 249001, 249199),
    ("P10-I-S1 ADR-0024", "rehearsal draw set (1)", 249201, 249299),
    ("P10-I-S1 ADR-0024", "spare", 249301, 249999),
    ("P10-I-S1 ADR-0024", "init sub-row", 330101, 330199),
    ("P10-I-S1 ADR-0024", "test", 933001, 933999),
    ("P10-I-S2 ADR-0025", "data: registered replicate sets (3)", 250001, 250899),
    ("P10-I-S2 ADR-0025", "partition side, analysis, disjoint-draw permutations", 250901, 250999),
    ("P10-I-S2 ADR-0025", "calibration", 251001, 251999),
    ("P10-I-S2 ADR-0025", "Part T rehearsal sets (i = 0..8)", 252001, 252899),
    ("P10-I-S2 ADR-0025", "Part Q rehearsal partition side", 252901, 252999),
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
    # --- revision 4: P10-I-S6 (ADR-0031); block 320001-329999, first supplement sub-row of the P10-I spare, test 952001-952999
    ("P10-I-S6 ADR-0031", "data: registered streams (27)", 320001, 320099),
    ("P10-I-S6 ADR-0031", "data: OA streams (27)", 320101, 320199),
    ("P10-I-S6 ADR-0031", "data: registered P_used (108)", 320201, 320399),
    ("P10-I-S6 ADR-0031", "spare (R-KNN left out; 320401-320427 not allocated to it)", 320401, 320999),
    ("P10-I-S6 ADR-0031", "data: parent order seeds (9 + 3)", 321001, 321999),
    ("P10-I-S6 ADR-0031", "spare", 322001, 328999),
    ("P10-I-S6 ADR-0031", "calibration streams and P_used", 329001, 329199),
    ("P10-I-S6 ADR-0031", "dry-rehearsal streams, P_used and held DRY values", 329201, 329299),
    ("P10-I-S6 ADR-0031", "spare (R-KNN left out; 329301-329303 not allocated to it)", 329301, 329999),
    ("P10-I-S6 ADR-0031", "init sub-row", 330701, 330799),
    ("P10-I-S6 ADR-0031", "test", 952001, 952999),
    ("P10-I spare", "init sub-rows for supplements", 330801, 330999),
]

# Named seeds inside the init sub-rows; each must lie in its study's sub-row.
NAMED_INIT = {
    "P10-I-S0 ADR-0023": {"registered": [330001, 330002], "calibration": [330091, 330093], "rehearsal + pipeline check": [330092], "test mode": [330098, 330099]},
    "P10-I-S1 ADR-0024": {"registered": [330101, 330102, 330103, 330104, 330105], "lane L (PENDING)": [330111, 330112, 330113, 330114, 330115],
                          "block X fresh draws": [330121, 330122, 330123, 330124, 330125],
                          "calibration": [330191, 330193], "rehearsal": [330192], "test mode": [330198, 330199]},
    "P10-I-S2 ADR-0025": {"registered r=0..2 x 8 roles": [330201 + 10 * r + j for r in range(3) for j in range(8)],
                          "calibration i=0,1 x 8 roles": [330231 + 10 * i + j for i in range(2) for j in range(8)],
                          "rehearsal i=0 x 8 roles": [330251 + j for j in range(8)], "test mode": [330298, 330299]},
    "P10-I-S3 ADR-0026": {"registered": [330301, 330302, 330303], "calibration": [330391], "dry rehearsal": [330392], "test mode": [330398, 330399]},
    "P10-I-S4 ADR-0027": {"registered (Route B: 330401-330405; Route A: 330401-330403, same values, one route per entry)": [330401, 330402, 330403, 330404, 330405],
                          "calibration (both routes)": [330491, 330492], "rehearsal (both routes)": [330495], "test mode": [330498, 330499],
                          "held: Route A if both routes are ever entered (registered, calibration, rehearsal)": [330411, 330412, 330413, 330481, 330482, 330485]},
    "P10-I-S5 ADR-0028": {"scientific part only (not laid out; unused)": [330501, 330502, 330503, 330504, 330505], "calibration (scientific part)": [330591], "rehearsal (scientific part)": [330592], "test mode": [330598, 330599]},
    "P10-I-R ADR-0029": {"bridge": [330601, 330602, 330603, 330604, 330605], "rehearsal": [330692], "test mode": [330698, 330699]},
    # revision 4
    "P10-I-S6 ADR-0031": {
        "addition, registered cell c = 3p + s (one per cell, both arms)": [330701 + c for c in range(27)],
        "addition, OA seed position s (shared by the old nine parents)": [330731, 330732, 330733],
        "backbone, registered new parents p = 0..8": list(range(330741, 330750)),
        "backbone, calibration new parents q = 0..2": [330751, 330752, 330753],
        "addition, calibration (all three calibration cells, every rate)": [330791],
        "addition, dry rehearsal; read-equality gate": [330792],
        "planted-positive toy model (gate) [added by revision 4]": [330793],
        "held: DRY-profile parent backbone, only if the DRY profile trains a parent [added by revision 4]": [330794],
        "test mode": [330798, 330799],
    },
}

# Named data seeds (revision 3 for S4 and S5; revision 4 adds S6 and corrects the record of S3 and S5).
NAMED_DATA = {
    "P10-I-S4 ADR-0027": {
        "Route B registered draw sets d=1..5 (set bases)": [270001 + 100 * (d - 1) for d in range(1, 6)],
        "Route A registered stream seeds, set d = parent 1..9, offset s-1 (s = 1..3)": [270001 + 100 * (d - 1) + o for d in range(1, 10) for o in range(3)],
        "calibration sets / Route A calibration stream seeds": [279001, 279101],
        "rehearsal set / Route A rehearsal stream seed": [279201],
        "held: Route A data if both routes are ever entered (sets 271001 + 100(p-1), offsets 0..2)": [271001 + 100 * (d - 1) + o for d in range(1, 10) for o in range(3)],
        "held: Route A calibration and rehearsal streams if both routes are entered": [279301, 279401, 279501],
    },
    # revision 4, correction of record: the values P10-I-S5 used (ADR-0028 revision 6 section 10; configs/p10is5_ssd.toml [seeds])
    "P10-I-S5 ADR-0028": {
        "registered request orders, repeats 1..5 and spare (280006)": list(range(280001, 280007)),
        "registered file contents": [280101],
        "registered pass orders, repeats 1..5 and spare (280206)": list(range(280201, 280207)),
        "auxiliary: registered tile assignment": [287001],
        "R1: rehearsal file contents, control file contents (also the harness request order's source)": [289001, 289013],
        "R1: request order, pass order, re-read offsets": [289011, 289021, 289051],
        "rehearsal M request orders, K request orders": list(range(289211, 289221)),
        "rehearsal M pass orders, K pass orders": list(range(289221, 289231)),
        "rehearsal M and K tile assignments": [289241, 289242],
    },
    # revision 4, correction of record: every value P10-I-S3 used (ADR-0026 section 9 table; studies/p10i_s3/freeze/seed_plan.json)
    "P10-I-S3 ADR-0026": {
        "registered streams 260001 + 3c + g": list(range(260001, 260082)),
        "registered P_all 260101 + c": list(range(260101, 260128)),
        "registered joint 260131 + c [missing from revision 3]": list(range(260131, 260158)),
        "registered P_used 260201 + 4c + j": list(range(260201, 260309)),
        "registered X 260401 + 4c + j": list(range(260401, 260509)),
        "calibration streams, P_all, joint [joint missing from revision 3], P_used, X": list(range(269001, 269010)) + list(range(269021, 269027)) + list(range(269031, 269043)) + list(range(269051, 269063)),
        "dry streams, P_all, joint [joint missing from revision 3], P_used, X": [269201, 269202, 269203, 269221, 269222, 269231, 269232, 269233, 269234, 269251, 269252, 269253, 269254],
    },
    "P10-I-S6 ADR-0031": {
        "registered streams 320001 + c (c = 3p + s)": [320001 + c for c in range(27)],
        "OA streams 320101 + c (c = 3p + s over the old nine parents)": [320101 + c for c in range(27)],
        "registered P_used 320201 + 4c + j (reused across rungs)": [320201 + 4 * c + j for c in range(27) for j in range(4)],
        "order seeds, registered new parents p = 0..8": list(range(321001, 321010)),
        "order seeds, calibration new parents q = 0..2": [321091, 321092, 321093],
        "calibration streams 329001 + q": [329001, 329002, 329003],
        "calibration P_used 329031 + 4q + j (also NEG-REF on calibration checkpoints)": [329031 + 4 * q + j for q in range(3) for j in range(4)],
        "dry stream": [329201],
        "dry P_used (also the planted-positive gate's draws)": [329231, 329232, 329233, 329234],
        "held: DRY OA stream, only if the DRY profile runs OA as a separate item [added by revision 4]": [329202],
        "held: DRY-profile parent order seed, only if the DRY profile trains a parent [added by revision 4]": [329211],
    },
}

# P10-I-S5 values assigned by revision 3 and never used (they stay in S5's block; nothing else may take them).
S5_ASSIGNED_UNUSED = [280007, 280008, 280009, 280010, 280102, 280103, 280301, 280302, 280303, 289012, 289031, 289201, 289231]

# ADR-0031 section 14 as approved (R-KNN rows excluded: open choice 14 was left OUT at Decision 1).
S6_PROPOSAL_DATA = sorted(
    [320001 + c for c in range(27)] + [320101 + c for c in range(27)] + [320201 + 4 * c + j for c in range(27) for j in range(4)]
    + list(range(321001, 321010)) + [321091, 321092, 321093] + [329001 + c for c in range(3)] + [329031 + 4 * c + j for c in range(3) for j in range(4)]
    + [329201, 329231, 329232, 329233, 329234])
S6_PROPOSAL_INIT = sorted([330701 + c for c in range(27)] + [330731, 330732, 330733] + list(range(330741, 330750)) + [330751, 330752, 330753] + [330791, 330792, 330798, 330799])
S6_PROPOSAL_TEST = (952001, 952999)
S6_RKNN_NOT_ALLOCATED = [320401 + c for c in range(27)] + [329301 + c for c in range(3)]


# Declared re-uses: seeds of a completed study that a P10-I study reads on purpose (not allocations, not
# collisions). The checker asserts each value is in the inventory (so it is a re-use of an existing seed, not
# a new one) and lies in no P10-I allocation, and lists it separately.
def _p10s0_set_values(base):
    fso = (0, 20, 60)
    return [base + f + i for f in fso for i in range(20)] + [base + o + j for o in (40, 44, 48) for j in (0, 1)] + [base + o for o in (50, 51, 52)]


def _p10s1_set_values(base):
    return [base + i for i in range(14)] + [base + 20 + i for i in range(3)] + [base + 30 + i for i in range(3)] + [base + 40] + [base + o for o in range(50, 61)]


DECLARED_REUSE: list[tuple[str, str, list, str]] = [
    ("P10-I-S0 ADR-0023", "identity gate part (a): P10-S0 rehearsal data set (base 209101), read-only, bit-identity at 4,096 and 16,384 slots",
     _p10s0_set_values(209101), "studies/p10s0/core.py:424 (REHEARSAL_BASE), :489 (REHEARSAL_SET), :541 (check_seed_set)"),
    ("P10-I-S0 ADR-0023", "identity gate part (a): P10-S0 rehearsal initialization seed 2092 and its +1000k component seeds",
     [2092] + [2092 + 1000 * k for k in range(1, 6)], "studies/p10s0/core.py:145 (REHEARSAL_INIT); studies/p9/model.py:272-279"),
    ("P10-I-R ADR-0029", "stage A1 reproduction reads: P10-S1 registered draws 1..5 incl. index seed (base + 60)",
     [v for r in range(5) for v in _p10s1_set_values(210001 + 100 * r)], "studies/p10s1/core.py:812-877"),
    ("P10-I-R ADR-0029", "adapter identity gate (section 10): P10-S1 cells F-OQ and T-OQ at 8K/4K, draw 1 (set 210001) with initialization seed 2101 and its component seeds",
     _p10s1_set_values(210001) + [2101] + [2101 + 1000 * k for k in range(1, 6)], "studies/p10s1/core.py:486 (2100 + r), :812 (REGISTERED_BASE), :820 (SEED_RANGE whitelist)"),
    # revision 4
    ("P10-I-S6 ADR-0031", "OA anchor (old nine parents, read-only by hash) and adapter identity gate (reproduce them bitwise): the P2/P3 control lineage seeds the old parents (also P10-I-S3's parents) were built from, backbone 101-103 and order 301-303",
     [101, 102, 103, 301, 302, 303], "src/arborlm/p2_config.py:34-36; src/arborlm/p2_model.py:20-22; src/arborlm/p2_data.py:151-156; ADR-0031 sections 7, 16a G9-G10"),
    ("P10-I-S6 ADR-0031", "adapter identity gate, only if it needs the frozen control memory (ADR-0031 G9): control memory seed 201 and its component seeds",
     [201] + [201 + 1000 * k for k in range(1, 6)], "src/arborlm/p2_config.py:48 (control_memory_seed); src/arborlm/pilot_model.py:110-124"),
    ("P10-I-S6 ADR-0031", "process default generators set by engine.configure_cpu (random.seed(42), torch.manual_seed(42)), part of the P2/P3 lineage and of every P10-I study's process set-up",
     [42], "src/arborlm/engine.py:26-27"),
]


def check_reuse(inv_idx: "Index"):
    problems, report = [], []
    alloc_idx = Index([(lo, hi, (st, ro)) for st, ro, lo, hi in ALLOC])
    for study, purpose, vals, src in DECLARED_REUSE:
        not_inv = sorted(v for v in vals if not any(INV[n]["primary"] for _, _, (n, _t) in inv_idx.hits(v, v)))
        in_alloc = sorted(v for v in vals if alloc_idx.hits(v, v))
        report.append(f"{study}: {purpose}: {len(vals)} values, {fmt(intervals(vals), 4)}; source {src}; "
                      f"not in inventory: {len(not_inv)}; inside a P10-I allocation: {len(in_alloc)}")
        if not_inv:
            problems.append(f"{study}: declared re-use values not found in the inventory: {not_inv[:8]}")
        if in_alloc:
            problems.append(f"{study}: declared re-use values inside a P10-I allocation: {in_alloc[:8]}")
    return report, problems


# The drafts' own proposals as read on 2026-11-17 (for the report of collisions; not allocations), plus ADR-0031's.
DRAFTS: list[tuple[str, str, int, int]] = [
    ("ADR-0023 draft 1", "init", 3001, 3002), ("ADR-0023 draft 1", "init", 3091, 3092),
    ("ADR-0023 draft 1", "data", 300001, 309999),
    ("ADR-0024 draft 1", "init", 2401, 2405), ("ADR-0024 draft 1", "init", 2491, 2493),
    ("ADR-0024 draft 1", "data", 240001, 249999), ("ADR-0024 draft 1", "test", 924001, 924999),
    ("ADR-0025 draft 1", "data", 250001, 259999), ("ADR-0025 draft 1", "test", 259001, 259999),
    ("ADR-0026", "init", 2601, 2699), ("ADR-0026", "data", 260001, 269999), ("ADR-0026", "test", 926001, 926999),
    ("ADR-0027", "init", 2701, 2799), ("ADR-0027", "data", 270001, 279999),
    ("ADR-0028", "data", 280001, 289999),
    ("ADR-0024 draft 3 (block X)", "data", 240501, 240901), ("ADR-0024 draft 3 (block X)", "init", 330121, 330125),
    ("ADR-0025 draft 3", "data (disjoint draws)", 250916, 250917), ("ADR-0025 draft 3", "data (Part Q rehearsal)", 252901, 252914),
    ("ADR-0027 draft 3 Route A", "data (streams d=6..9)", 270501, 270803), ("ADR-0027 draft 3", "init", 330401, 330405),
    ("ADR-0028 draft 3", "data (registered)", 280001, 280303),
    ("ADR-0031 section 14", "data", 320001, 329999), ("ADR-0031 section 14", "init", 330701, 330799), ("ADR-0031 section 14", "test", 952001, 952999),
]


# ---------------------------------------------------------------------------------------------------
# expansion rules (revision 3's, unchanged)


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


def is_test(role: str) -> bool:
    return role == "test"


def draft_hits(inv_idx: Index, d):
    study, role, lo, hi = d
    actual, conservative, own = {}, 0, 0
    for tag, x, y in expand([(lo, hi)], is_init(role), False):
        for ilo, ihi, (n, itag) in inv_idx.hits(x, y):
            e = INV[n]
            ov = (max(x, ilo), min(y, ihi))
            if e["owner"] is not None:
                own += 1  # an executed study's own files (reported in [1] against the allocation, not here)
            elif e["primary"] and (itag == "id" or e["init"] or itag == "x1000+i"):
                key = f"{study} {role} [{tag}] {ov[0]}..{ov[1]} = {e['study']} / {e['role']} [{itag}] ({e['source']})"
                actual[key] = 1
            else:
                conservative += 1
    return list(actual), conservative, own


def check_structured(inv_idx: Index, allocs, all_shift=False, small_r3=False):
    """Hits as (alloc study, alloc role, other study, other role, message, owner); owner is the inventory entry's owner
    (None for an unowned entry), or the string "<allocation>" for a hit between two allocations."""
    problems = []
    exp = []
    for a, (study, role, lo, hi) in enumerate(allocs):
        for tag, x, y in expand([(lo, hi)], is_init(role), False, all_shift, small_r3):
            exp.append((x, y, a, tag))
            for ilo, ihi, (n, itag) in inv_idx.hits(x, y):
                e = INV[n]
                ov = (max(x, ilo), min(y, ihi))
                problems.append((study, role, e["study"], e["role"], f"{study} / {role} [{tag}] {ov[0]}..{ov[1]} hits inventory: {e['study']} / {e['role']} [{itag}] ({e['source']})", e["owner"]))
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
            problems.append((allocs[a][0], allocs[a][1], allocs[b][0], allocs[b][1], f"{allocs[a][0]} / {allocs[a][1]} [{tag}] and {allocs[b][0]} / {allocs[b][1]} [{btag}] share {ov[0]}..{ov[1]}", "<allocation>"))
    return problems


def split_own(hits):
    """(failures, known own-files cases). A hit is the known own-files case iff it is a hit against the inventory and
    the inventory entry's owner is the allocation's own study (ADR-0029 ruling 6). Everything else fails."""
    fails, own = [], []
    for h in hits:
        (own if h[5] not in (None, "<allocation>") and h[5] == h[0] else fails).append(h)
    return fails, own


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
# [8] executed P10-I studies: the values they used, from their frozen configs and seed plans (revision 4)


def rows_of(study: str, kind: str) -> list[tuple[int, int]]:
    """kind: 'data' (neither init nor test), 'init' or 'test'."""
    out = []
    for s, role, lo, hi in ALLOC:
        if s != study:
            continue
        k = "init" if is_init(role) else "test" if is_test(role) else "data"
        if k == kind:
            out.append((lo, hi))
    return out


def outside(values, rows) -> list[int]:
    return sorted(v for v in values if not any(lo <= v <= hi for lo, hi in rows))


def s3_used() -> dict[str, set[int]]:
    """P10-I-S3's values by the formulas of studies/p10i_s3/core.py Seeds (re-implemented here), from its frozen config."""
    s = tomllib.loads(text("configs/p10i_s3_longer_training.toml"))["seeds"]
    used: dict[str, set[int]] = {}
    used["registered_streams"] = {s["stream_base"] + 3 * c + g for c in range(27) for g in range(3)}
    used["registered_p_all"] = {s["p_all_base"] + c for c in range(27)}
    used["registered_joint"] = {s["joint_base"] + c for c in range(27)}
    used["registered_p_used"] = {s["p_used_base"] + 4 * c + j for c in range(27) for j in range(4)}
    used["registered_x"] = {s["x_base"] + 4 * c + j for c in range(27) for j in range(4)}
    used["calibration"] = ({s["cal_stream_base"] + 3 * c + g for c in range(3) for g in range(3)} | {s["cal_p_all_base"] + c for c in range(3)}
                           | {s["cal_joint_base"] + c for c in range(3)} | {s["cal_p_used_base"] + 4 * c + j for c in range(3) for j in range(4)}
                           | {s["cal_x_base"] + 4 * c + j for c in range(3) for j in range(4)})
    used["dry"] = {s["dry_stream_base"] + g for g in range(3)} | {s["dry_p_all"], s["dry_joint"]} | {s["dry_p_used_base"] + j for j in range(4)} | {s["dry_x_base"] + j for j in range(4)}
    used["init"] = set(s["init_registered"]) | {s["init_calibration"], s["init_dry"]}
    used["test_init"] = set(s["init_test"])
    t = s["test_range"][0]
    used["test_profile"] = ({t + 3 * c + g for c in range(27) for g in range(3)} | {t + 100 + c for c in range(27)} | {t + 200 + c for c in range(27)}
                            | {t + 300 + 4 * c + j for c in range(27) for j in range(4)} | {t + 500 + 4 * c + j for c in range(27) for j in range(4)})
    return used


def s5_used() -> dict[str, set[int]]:
    s = tomllib.loads(text("configs/p10is5_ssd.toml"))["seeds"]
    reg = {s["store_contents"], *s["request_order"], s["spare_request_order"], *s["pass_order"], s["spare_pass_order"]}
    aux = {s["tile_assignment"]}
    r1 = {s["r1_rehearsal_file_contents"], s["r1_control_file_contents"], s["r1_request_order"], s["r1_pass_order"], s["r1_reread_offsets"]}
    reh = {*s["m_request_order"], *s["k_request_order"], *s["m_pass_order"], *s["k_pass_order"], s["m_tile_assignment"], s["k_tile_assignment"]}
    t = "studies/p10is5/testing.py"
    test = {const(t, "TEST_SEED_CONTENTS")[0], const(t, "TEST_SEED_ASSIGN")[0], *const(t, "TEST_SEED_REQUEST")[0], *const(t, "TEST_SEED_ORDER")[0]}
    return {"registered": reg, "auxiliary": aux, "r1": r1, "rehearsal": reh, "test": test}


def r_used() -> dict[str, set[int]]:
    s = tomllib.loads(text("configs/p10ir_routing.toml"))["seeds"]
    bridge = {v for d in range(1, s["bridge_draws"] + 1) for v in _p10s1_set_values(s["bridge_base"] + s["bridge_stride"] * (d - 1))}
    inits = {s["bridge_init_base"] + d for d in range(1, s["bridge_draws"] + 1)} | {s["rehearsal_init"]} | set(s["test_init"])
    return {"bridge_sets": bridge, "i64_index_seeds": set(s["index_seeds"]), "test_index_seeds": set(s["test_index_seeds"]),
            "rehearsal_set": set(_p10s1_set_values(s["rehearsal_base"])), "initialisation": inits}


def executed_check():
    report, problems = [], []
    # --- P10-I-S3
    st = "P10-I-S3 ADR-0026"
    u = s3_used()
    plan = json.loads(text("studies/p10i_s3/freeze/seed_plan.json"))["roles"]
    for role in ("registered_streams", "registered_p_all", "registered_joint", "registered_p_used", "registered_x", "calibration", "dry", "init", "test_init"):
        if set(plan[role]) != u[role]:
            problems.append(f"{st}: role {role}: the frozen seed plan and the config formula differ")
    data = set().union(*(u[k] for k in ("registered_streams", "registered_p_all", "registered_joint", "registered_p_used", "registered_x", "calibration", "dry")))
    named = {v for vals in NAMED_DATA[st].values() for v in vals}
    report.append(f"{st}: frozen seed plan = config formula for 9 roles; data values used {len(data)} (registered {sum(len(u[k]) for k in u if k.startswith('registered'))}, "
                  f"calibration {len(u['calibration'])}, dry {len(u['dry'])}); joint 260131–260157, 269024–269026, 269222 among them")
    if data != named:
        problems.append(f"{st}: values used and the revision-4 record differ: used-not-recorded {sorted(data - named)[:6]}, recorded-not-used {sorted(named - data)[:6]}")
    for kind, vals in (("data", data), ("init", u["init"] | u["test_init"]), ("test", u["test_profile"])):
        bad = outside(vals, rows_of(st, kind))
        report.append(f"{st}: {kind} values {fmt(intervals(vals), 4)}; outside the study's {kind} rows: {len(bad)}")
        if bad:
            problems.append(f"{st}: {kind} values outside its rows: {bad[:6]}")
    ninit = {v for vals in NAMED_INIT[st].values() for v in vals}
    if u["init"] | u["test_init"] != ninit:
        problems.append(f"{st}: initialisation used {sorted(u['init'] | u['test_init'])} differs from the record {sorted(ninit)}")
    # synthetic-only literals of S3's code that are not registry values (facts of the record, not failures)
    pl = ast.parse(text("studies/p10i_s3/planted.py"))
    toy = [fn.args.defaults[-1].value for fn in pl.body if isinstance(fn, ast.FunctionDef) and fn.name == "plant"]
    loc_plant = line_of("studies/p10i_s3/planted.py", r"def plant")
    loc_synth = line_of("studies/p10i_s3/stages.py", r"test_seed\(900 \+ seed\)")
    report.append(f"{st}: note (not a failure): the planted-positive toy model is built with seed {toy} ({loc_plant}); "
                  f"synthetic resources use test seed 935901 + seed and backbones PilotModel('dense_small', 42 + parent % 3) "
                  f"({loc_synth}): undeclared re-uses of inventory literals 1 and 42-44 on synthetic paths only")
    # --- P10-I-S5
    st = "P10-I-S5 ADR-0028"
    u5 = s5_used()
    used5 = u5["registered"] | u5["auxiliary"] | u5["r1"] | u5["rehearsal"]
    named5 = {v for vals in NAMED_DATA[st].values() for v in vals}
    report.append(f"{st}: values used {len(used5)} (registered {len(u5['registered'])}, auxiliary {len(u5['auxiliary'])}, R1 {len(u5['r1'])}, rehearsal {len(u5['rehearsal'])}); "
                  f"test {sorted(u5['test'])}; revision-3 values never used: {fmt(intervals(S5_ASSIGNED_UNUSED), 8)}")
    if used5 != named5:
        problems.append(f"{st}: values used and the revision-4 record differ: used-not-recorded {sorted(used5 - named5)[:6]}, recorded-not-used {sorted(named5 - used5)[:6]}")
    if set(S5_ASSIGNED_UNUSED) & used5:
        problems.append(f"{st}: a value listed as never used is used: {sorted(set(S5_ASSIGNED_UNUSED) & used5)}")
    for kind, vals in (("data", used5 | set(S5_ASSIGNED_UNUSED)), ("test", u5["test"])):
        bad = outside(vals, rows_of(st, kind))
        report.append(f"{st}: {kind} values outside the study's {kind} rows: {len(bad)}")
        if bad:
            problems.append(f"{st}: {kind} values outside its rows: {bad[:6]}")
    # --- P10-I-R
    st = "P10-I-R ADR-0029"
    ur = r_used()
    for kind, vals in (("data", ur["bridge_sets"] | ur["i64_index_seeds"] | ur["rehearsal_set"]), ("init", ur["initialisation"]), ("test", ur["test_index_seeds"])):
        bad = outside(vals, rows_of(st, kind))
        report.append(f"{st}: {kind} values {fmt(intervals(vals), 4)}; outside the study's {kind} rows: {len(bad)}")
        if bad:
            problems.append(f"{st}: {kind} values outside its rows: {bad[:6]}")
    if ur["initialisation"] != {v for vals in NAMED_INIT[st].values() for v in vals}:
        problems.append(f"{st}: initialisation used differs from the record")
    # --- import half: the studies' own planned_seed_values against the reconstruction above
    try:
        import importlib

        sys.path.insert(0, str(ROOT))
        g3 = importlib.import_module("studies.p10i_s3.gates")
        g5 = importlib.import_module("studies.p10is5.gates")
        c5 = importlib.import_module("studies.p10is5.core")
        gr = importlib.import_module("studies.p10ir.gates")
    except Exception as exc:
        report.append(f"import cross-check SKIPPED ({type(exc).__name__}: {exc})")
        return report, problems
    p3 = g3.planned_seed_values()
    for role, vals in sorted(p3.items()):
        mine = u.get(role)
        if role == "init_components":
            mine = {i + k for i in u["init"] | u["test_init"] for k in (1000, 2000, 3000, 4000, 5000)}
        same = mine is not None and set(vals) == mine
        report.append(f"import P10-I-S3 gates.planned_seed_values[{role}]: {len(vals)} values; equal to the reconstruction: {same}")
        if not same:
            problems.append(f"P10-I-S3 {role}: the study's own function and the reconstruction differ")
    p5 = g5.planned_seed_values(c5.load_config())
    for role, vals in sorted(p5.items()):
        same = set(vals) == u5[role]
        report.append(f"import P10-I-S5 gates.planned_seed_values[{role}]: {len(vals)} values; equal to the reconstruction: {same}")
        if not same:
            problems.append(f"P10-I-S5 {role}: the study's own function and the reconstruction differ")
    pr = gr.planned_seed_values()
    for role, vals in sorted(pr.items()):
        if role in ur:
            same = set(vals) == ur[role]
            report.append(f"import P10-I-R gates.planned_seed_values[{role}]: {len(vals)} values; equal to the reconstruction: {same}")
            if not same:
                problems.append(f"P10-I-R {role}: the study's own function and the reconstruction differ")
        else:
            rows = rows_of(st, "test") if role == "test_sets" else None
            if role == "test_sets":
                bad = outside(vals, rows)
                report.append(f"import P10-I-R gates.planned_seed_values[test_sets]: {len(vals)} values, {fmt(intervals(vals), 4)}; outside the test row: {len(bad)}")
                if bad:
                    problems.append(f"P10-I-R test_sets outside its test row: {bad[:6]}")
            else:
                report.append(f"import P10-I-R gates.planned_seed_values[{role}]: {len(vals)} values (R2 images of the initialisation seeds; not compared)")
    return report, problems


# ---------------------------------------------------------------------------------------------------
# [9] P10-I-S6: ADR-0031 section 14's proposal against the revision-4 allocation


def s6_check():
    report, problems = [], []
    st = "P10-I-S6 ADR-0031"
    data = [v for vals in NAMED_DATA[st].values() for v in vals]
    init = [v for vals in NAMED_INIT[st].values() for v in vals]
    if len(data) != len(set(data)) or len(init) != len(set(init)) or set(data) & set(init):
        problems.append(f"{st}: a named value is repeated across roles")
    add_d = sorted(set(data) - set(S6_PROPOSAL_DATA))
    add_i = sorted(set(init) - set(S6_PROPOSAL_INIT))
    drop_d = sorted(set(S6_PROPOSAL_DATA) - set(data))
    drop_i = sorted(set(S6_PROPOSAL_INIT) - set(init))
    report.append(f"{st}: named data {len(data)}, named initialisation {len(init)}; test row 952001–952999 (proposal {S6_PROPOSAL_TEST[0]}–{S6_PROPOSAL_TEST[1]})")
    report.append(f"{st}: proposal values kept: data {len(set(data) & set(S6_PROPOSAL_DATA))} of {len(S6_PROPOSAL_DATA)}, initialisation {len(set(init) & set(S6_PROPOSAL_INIT))} of {len(S6_PROPOSAL_INIT)}")
    report.append(f"{st}: proposal values moved or dropped: data {drop_d}, initialisation {drop_i}")
    report.append(f"{st}: values added by revision 4 (roles the proposal left without a value): data {add_d}, initialisation {add_i}")
    rk = sorted(set(S6_RKNN_NOT_ALLOCATED) & (set(data) | set(init)))
    report.append(f"{st}: R-KNN values of the ADR text (320401–320427, 329301–329303) named in the allocation: {rk} (open choice 14 left OUT)")
    if rk:
        problems.append(f"{st}: R-KNN values are named although R-KNN was left out")
    for kind, vals in (("data", data), ("init", init)):
        bad = outside(vals, rows_of(st, kind))
        if bad:
            problems.append(f"{st}: {kind} named values outside its {kind} rows: {bad[:6]}")
    # informational: W1 reach of S6's data block into the initialisation row (why no data seed may be expanded by +1000k)
    named_init_all = {v: s for s, roles in NAMED_INIT.items() for vals in roles.values() for v in vals}
    w1 = sorted({(d, d + 1000 * k, named_init_all[d + 1000 * k]) for d in data for k in range(1, K_MAX + 1) if d + 1000 * k in named_init_all})
    report.append(f"{st}: informational (W1, not binding): S6 named data values d with d + 1000k equal to a named P10-I initialisation value: {len(w1)}; "
                  f"e.g. {', '.join(f'{d}+{x - d}={x} ({s})' for d, x, s in w1[:4])}")
    return report, problems


# ---------------------------------------------------------------------------------------------------
# literal scan of the repository for integers inside the P10-I allocations (informational)


def literal_scan(allocs):
    rx = re.compile(r"(?<![\w.])(\d{6})(?![\w.])")
    skip = tuple(f"docs/decisions/ADR-00{n}" for n in range(23, 32)) + ("docs/reviews/p10-i-",)
    idx = Index([(lo, hi, (study, role)) for study, role, lo, hi in allocs])
    hits = []
    for d in ("configs", "src", "studies", "tests", "docs/decisions", "docs/reviews"):
        for path in sorted((ROOT / d).rglob("*")):
            if not path.is_file() or path.suffix not in ((".md",) if d == "docs/decisions" else (".py",) if d == "docs/reviews" else (".py", ".toml")):
                continue
            rel = str(path.relative_to(ROOT))
            if rel.startswith(skip):
                continue
            own = owner_of(rel)
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                for m in rx.finditer(line):
                    v = int(m.group(1))
                    for _, _, (study, role) in idx.hits(v, v):
                        hits.append((f"{rel}:{i}", v, study, role, own == study))
    return hits


# ---------------------------------------------------------------------------------------------------


def parse_args(argv):
    opts = {"tables": False, "selftest": False}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--tables":
            opts["tables"] = True
        elif a == "--selftest":
            opts["selftest"] = True
        elif a in ("--own", "--root"):
            if i + 1 >= len(argv):
                raise SystemExit(f"CHECKER ERROR: {a} needs a value")
            val = argv[i + 1]
            i += 1
            if a == "--root":
                global ROOT
                ROOT = Path(val)
            else:
                study, sep, globs = val.partition("=")
                if not sep or not globs:
                    raise SystemExit("CHECKER ERROR: --own takes STUDY=GLOB[,GLOB...]")
                if study not in {s for s, *_ in ALLOC}:
                    raise SystemExit(f"CHECKER ERROR: --own names {study!r}, which is not an ALLOC study")
                OWN_FILES[study] = OWN_FILES.get(study, ()) + tuple(g.strip() for g in globs.split(",") if g.strip())
        else:
            raise SystemExit(f"CHECKER ERROR: unknown argument {a!r}")
        i += 1
    return opts


def plant_faults() -> None:
    ALLOC.append(("P10-I-S6 ADR-0031", "PLANTED: a data row on P10-I-S3's joint seed 260131", 260131, 260131))
    NAMED_INIT["P10-I-S6 ADR-0031"]["PLANTED: outside the sub-row"] = [330801]
    DECLARED_REUSE.append(("P10-I-S6 ADR-0031", "PLANTED: a re-use inside an allocation", [320001], "selftest"))


def main() -> int:
    opts = parse_args(sys.argv)
    tables = opts["tables"]
    if opts["selftest"]:
        plant_faults()
    build_inventory()
    print("SEED REGISTRY CHECK (P10-I) revision 4 — arbor-auditor, standard library only" + ("  [SELFTEST: three planted faults]" if opts["selftest"] else ""))
    print(f"root: {ROOT}")
    print(f"rules: R1 identity; R2 s+1000k, k=1..{K_MAX}, on initialization seeds and on every inventory literal < {SMALL_LITERAL};"
          f" R3 s*1000+i, i in [0,{INDEX_SPAN - 1}], on every value >= 1000; in-set offsets enumerated per study")
    print("own files (ADR-0029 ruling 6): " + "; ".join(f"{s} = {', '.join(g)}" for s, g in OWN_FILES.items()))
    print(f"inventory: {len(INV)} entries, {sum(b - a + 1 for e in INV for a, b in e['ivs'])} identity values (with overlaps); "
          f"entries owned by a P10-I study: {sum(1 for e in INV if e['owner'])}")
    if tables:
        print("\n| # | Study | Role | Literal values / range | Rule (in-set derivation) | R2 applies | Owner | Source |")
        print("|---|---|---|---|---|---|---|---|")
        for n, e in enumerate(INV, 1):
            r2 = "yes" if e["init"] else ("yes (< 100000)" if e["ivs"][0][0] < SMALL_LITERAL else "no")
            print(f"| {n} | {e['study']} | {e['role']} | {fmt(e['ivs'])} | {e['rule']} | {r2} | {e['owner'] or '—'} | {e['source']} |")
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
    for study, named in NAMED_DATA.items():
        rows = [(lo, hi) for s_, role, lo, hi in ALLOC if s_ == study and not is_init(role) and not is_test(role)]
        for what, vals in named.items():
            for v in vals:
                if not any(lo <= v <= hi for lo, hi in rows):
                    print(f"FAIL: named data seed {v} ({study} {what}) is outside the study's data allocations")
                    ok = False
        flat = [v for vals in named.values() for v in vals]
        # revision 4's no-repeat check applies to the studies it adds or corrects; P10-I-S4's Route A and Route B share
        # values by design (SEED_REGISTRY.md section 4.7: one route per entry)
        if study in ("P10-I-S3 ADR-0026", "P10-I-S5 ADR-0028", "P10-I-S6 ADR-0031") and len(flat) != len(set(flat)):
            print(f"FAIL: repeated named data seed in {study}")
            ok = False
    print(f"named values checked: {sum(len(v) for n in NAMED_INIT.values() for v in n.values())} initialization, "
          f"{sum(len(v) for n in NAMED_DATA.values() for v in n.values())} data (revision 4)")
    if tables:
        print("\n| Study | Role | Range | Size |")
        print("|---|---|---|---|")
        for study, role, lo, hi in ALLOC:
            print(f"| {study} | {role} | {lo}–{hi} | {hi - lo + 1} |")

    inv_idx = inventory_index()
    print("\n[1] binding: P10-I allocations (R1-R3 expanded) against the inventory (R1-R3 expanded) and against each other")
    raw = check_structured(inv_idx, ALLOC)
    fails, own = split_own(raw)
    print(f"    allocations: {len(ALLOC)}; problems: {len(fails)}; known own-files cases (not failures): {len(own)}; "
          f"revision-3-equivalent count (own files not separated): {len(raw)}")
    by_owner: dict[str, int] = {}
    for h in own:
        by_owner[h[0]] = by_owner.get(h[0], 0) + 1
    for s_, n_ in sorted(by_owner.items()):
        print(f"    known own-files case: {s_}: {n_} hits of its own allocation against its own files")
    for h in fails[:60]:
        print("    FAIL:", h[4] + (f"  [entry owned by {h[5]}]" if h[5] not in (None, "<allocation>") else ""))
    if len(fails) > 60:
        print(f"    … {len(fails) - 60} more")
    ok &= not fails

    print("\n[2] the drafts' own proposals under the same rules, against the inventory only")
    print("    (listed: collisions with a seed the code itself uses or derives; 'conservative' counts hits that exist only through")
    print("     the catch-all entries or the +1000k applied to small literals that are not initialization seeds; 'own-files' counts")
    print("     hits on an executed study's own files, which [1] classifies against the allocation)")
    for d in DRAFTS:
        actual, conservative, ownc = draft_hits(inv_idx, d)
        print(f"    {d[0]} {d[1]} {d[2]}–{d[3]}: {len(actual)} actual collisions, {conservative} conservative-only, {ownc} own-files")
        for p_ in actual[:14]:
            print("      ", p_)
        if len(actual) > 14:
            print(f"       … {len(actual) - 14} more")
    cross = [h[4] for h in check_structured(inv_idx, DRAFTS) if h[5] == "<allocation>" and h[0].split()[0] != h[2].split()[0]]
    print(f"    between drafts: {len(cross)}")
    for p_ in cross[:10]:
        print("      ", p_)

    print("\n[3] informational (not binding): worst case, +1000k applied to EVERY value of every role, both sides")
    w1 = check_structured(inventory_index(all_shift=True), ALLOC, all_shift=True)
    same = sum(1 for h in w1 if h[0] == h[2] or h[5] == h[0])
    print(f"    hits: {len(w1)}; {same} inside one study's own block or own files (not listed); the rest grouped by study pair (roles merged):")
    groups: dict[str, int] = {}
    for a_s, a_r, o_s, o_r, _, ow in w1:
        if a_s == o_s or ow == a_s:
            continue
        key = f"{a_s}  <->  {o_s}" + ("" if o_s.startswith("P10-I") else f" / {o_r}")
        groups[key] = groups.get(key, 0) + 1
    for g, n in sorted(groups.items()):
        print(f"       {n:5d}  {g}")
    print("\n[4] informational (not binding): R3 also applied to values < 1000, both sides")
    w2 = [h[4] for h in check_structured(inventory_index(small_r3=True), ALLOC, small_r3=True)]
    w2 = [p_ for p_ in w2 if p_ not in {h[4] for h in raw}]
    print(f"    hits: {len(w2)}")
    for p_ in w2[:10]:
        print("      ", p_)

    print("\n[5] informational: six-digit literals inside a P10-I allocation, in configs/*.toml, src, studies, tests (*.py),")
    print("    docs/decisions/*.md (ADR-0023..0031 excluded) and docs/reviews/**/*.py (P10-I review folders excluded); sizes are not seeds")
    lit = literal_scan(ALLOC)
    own_lit: dict[str, int] = {}
    for loc, v, study, role, is_own in lit:
        if is_own:
            own_lit[study] = own_lit.get(study, 0) + 1
    foreign: dict[str, list[str]] = {}
    for loc, v, study, role, is_own in lit:
        if not is_own:
            foreign.setdefault(f"{v} in {study} / {role}", []).append(loc)
    print(f"    hits: {len(lit)} occurrences; in the allocation's own study's files: {sum(own_lit.values())} ({', '.join(f'{k} {n}' for k, n in sorted(own_lit.items()))}); "
          f"elsewhere: {sum(len(x) for x in foreign.values())} occurrences of {len(foreign)} distinct values")
    for rest, locs in sorted(foreign.items())[:80]:
        print(f"       {rest}: {len(locs)} occurrences, first {locs[0]}")
    if len(foreign) > 80:
        print(f"       … {len(foreign) - 80} more distinct values")

    print("\n[6] cross-check: every seed the studies' own functions declare lies inside the reconstruction")
    report, missing = import_crosscheck()
    for r_ in report:
        print("    ", r_)
    for m_ in missing:
        print("     MISSING:", m_)
    ok &= not missing

    print("\n[7] declared re-uses (read-only use of a completed study's seeds; not allocations, not collisions)")
    rreport, rproblems = check_reuse(inv_idx)
    for r_ in rreport:
        print("    ", r_)
    for p_ in rproblems:
        print("     FAIL:", p_)
    ok &= not rproblems

    print("\n[8] executed P10-I studies (revision 4): values used, from frozen configs and seed plans, against the record and their rows")
    ereport, eproblems = executed_check()
    for r_ in ereport:
        print("    ", r_)
    for p_ in eproblems:
        print("     FAIL:", p_)
    ok &= not eproblems

    print("\n[9] P10-I-S6 (ADR-0031 section 14) against the revision-4 allocation")
    sreport, sproblems = s6_check()
    for r_ in sreport:
        print("    ", r_)
    for p_ in sproblems:
        print("     FAIL:", p_)
    ok &= not sproblems

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
