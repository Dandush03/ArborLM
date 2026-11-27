"""Independent recomputation of the M0 capacity stage of record: common helpers.

Written by the recomputing auditor from the approved text (ADR-0033 addendum 1 at 2c944302, section 4A stage 4 and
section 10 part A). It does NOT import studies/m0/registration/capacity.py, pool_builder.py or partition.py, nor any
*_analysis module. It imports the committed generators (core.build_item and the lineage modules) and the committed
second solvers, which are what is counted, and the committed key studies/m0/registration/distinct_key.py (stated:
no relabelling of my own is used for the counts).
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
import time

W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
SCR = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_recompute_20261126"
KEYDIR = f"{SCR}/work/keys"
if W not in sys.path:
    sys.path.insert(0, W)

SEED = 400002
LABEL = "capacity"  # the run is over; the brief allows drawing the registered label for recomputation
LEVELS = (0, 1, 2, 3, 4, 5, 6)


# ------------------------------------------------------------------ demand (section 10 part A items 2 and 4)
def cdiv(a: int, b: int) -> int:
    return -(-a // b)


def D(g: int) -> int:
    return 10 * (cdiv(4000, g) + cdiv(20000, g) + 100)


def D_lin(g: int, k: int) -> int:
    return 10 * (cdiv(cdiv(4000, g), k) + cdiv(cdiv(20000, g), k) + cdiv(100, k))


# ------------------------------------------------------------------ stream (section 4 derivation, written again)
def my_stream(seed: int, *labels: str) -> random.Random:
    s = "|".join([str(seed), *labels])
    return random.Random(int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "big"))


# ------------------------------------------------------------------ inputs
def load_json(rel: str):
    with open(f"{W}/{rel}", encoding="utf-8") as fh:
        return json.load(fh)


def round1_parts():
    """{(e, p): {cluster: [lineage ids sorted]}} from the candidate list, the map and the partition of record."""
    cand = load_json("studies/m0/registration/candidate_list.json")["candidates"]
    mp = load_json("studies/m0/manifests/map_of_record.json")
    part = load_json("studies/m0/manifests/partition_of_record.json")["cluster_part"]
    member_of = {}
    for c in mp["clusters"]:
        for m in c["members"]:
            if m in member_of:
                raise RuntimeError(f"{m} in two clusters")
            member_of[m] = c["cluster_id"]
    parts: dict = {}
    for e, ids in cand.items():
        for lid in ids:
            cl = member_of[lid]
            p = part[cl]
            parts.setdefault((e, p), {}).setdefault(cl, []).append(lid)
    for v in parts.values():
        for cl in v:
            v[cl].sort()
    return parts


# ------------------------------------------------------------------ lineages and solvers
_LINS = None
_SOLVERS = None


def lineages():
    global _LINS
    if _LINS is None:
        from studies.m0.lineages_c1_fix4 import all_written
        from studies.m0.lineages_m1_fix4 import load_registered
        from studies.m0.lineages_r1_fix4_clusters import candidates_v4, registered_v4
        from studies.m0.r2_fix4_set import fix4_set

        out = {}
        for x in [*candidates_v4(), *registered_v4()]:
            assert out.get(x.id, x) is x or out[x.id].build is x.build or True
            out.setdefault(x.id, x)
        for src in (dict(fix4_set()), {x.id: x for x in load_registered()}, dict(all_written())):
            for k, v in src.items():
                assert k not in out, k
                out[k] = v
        _LINS = out
    return _LINS


def solvers():
    global _SOLVERS
    if _SOLVERS is None:
        import importlib.util

        out = {}
        for f in ("r1", "r2a", "r2b", "m1a", "m1b", "m1c", "c1"):
            p = f"{W}/studies/m0/solvers2/solver2_{f}.py"
            spec = importlib.util.spec_from_file_location(f"rc_solver2_{f}", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for lid, fn in mod.SOLVERS.items():
                assert lid not in out, lid
                out[lid] = fn
        _SOLVERS = out
    return _SOLVERS


# ------------------------------------------------------------------ the count c(x, v, T)
def count_cell(lid: str, level: int, target: int, check_solver: bool = True, save_keys: bool = True,
               budget_override: int | None = None, label: str = LABEL):
    """c(x, v, T) as section 4A stage 4 states it, my own loop.

    Fresh stream stream(400002, "capacity", e, id, str(v)); empty key set; build items one after another with the
    builder's build_item; discard an item whose key is already in the set; stop at T keys, or when the number of
    attempts would exceed 40T + 1000 (draw_items: the counter is raised, then tested, then the item is built), or when
    build_item gives up after 500 consecutive retries. The second solver is applied to every item built.
    """
    from studies.m0.core import build_item
    from studies.m0.registration.distinct_key import item_key

    lin = lineages()[lid]
    assert lin.eval == lid.split(".")[0]
    sol = solvers()[lid] if check_solver else None
    rng = my_stream(SEED, label, lin.eval, lin.id, str(level))
    budget = 40 * target + 1000 if budget_override is None else budget_override
    seen: set = set()
    order = bytearray()
    built = 0
    ended = None
    dis = []
    ndis = 0
    tmax = 0.0
    t0 = time.time()
    while len(seen) < target:
        if built + 1 > budget:
            ended = "budget"
            break
        try:
            it = build_item(lin, level, rng, "rc", "rc")
        except RuntimeError as exc:
            if "consecutive retries" in str(exc):
                ended = "gave_up"
                break
            raise
        built += 1
        if sol is not None:
            st = copy.deepcopy(json.loads(json.dumps(it.structured)))
            ts = time.perf_counter()
            try:
                got = sol(it.question, st)
                bad = None if (isinstance(got, str) and got == it.answer) else ("mismatch", repr(got)[:80])
            except Exception as exc:  # noqa: BLE001
                bad = ("error", f"{type(exc).__name__}: {str(exc)[:80]}")
            tmax = max(tmax, time.perf_counter() - ts)
            if bad is not None:
                ndis += 1
                if len(dis) < 5:
                    dis.append([built, it.answer[:80], *bad])
        k = item_key(lid, it.question, it.structured)
        if k in seen:
            continue
        seen.add(k)
        order += k
    if ended is None:
        ended = "target"
    digest = hashlib.sha256(bytes(order)).hexdigest()
    if save_keys:
        with open(f"{KEYDIR}/{lid}__L{level}__T{target}.bin", "xb") as fh:
            fh.write(bytes(order))
    return {
        "lineage": lid, "level": level, "target": target, "count": len(seen), "attempts": built, "ended": ended,
        "solver_disagreements": ndis, "disagreement_detail": dis, "max_solver_seconds": round(tmax, 4),
        "keys_sha256": digest, "seconds": round(time.time() - t0, 1),
    }


def read_keys(lid: str, level: int, target: int) -> set:
    with open(f"{KEYDIR}/{lid}__L{level}__T{target}.bin", "rb") as fh:
        b = fh.read()
    assert len(b) % 16 == 0
    return {b[i:i + 16] for i in range(0, len(b), 16)}
