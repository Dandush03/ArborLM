"""Auditor's common helpers (M0 stage-4 capacity audit, 2026-11-26). Written from the approved text only.

Nothing here imports capacity.py, distinct_key.py or pool_builder.py; scripts that compare against them import them
themselves. The audit stream label is AUDIT_LABEL, never the registered "capacity".
"""
from __future__ import annotations

import hashlib
import json
import random
import sys

W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
SCR = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_capacity_audit_20261126"
if W not in sys.path:
    sys.path.insert(0, W)

AUDIT_LABEL = "capacity-audit"
REGISTERED_LABEL = "capacity"


def my_stream(seed: int, *labels: str) -> random.Random:
    """Section 4 derivation, written from the text."""
    if labels and labels[0] == REGISTERED_LABEL:
        raise RuntimeError("the auditor never draws from the registered label")
    s = "|".join([str(seed), *labels])
    return random.Random(int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "big"))


def load_lineages() -> dict:
    """Lineage objects as gen_fresh.py of the pair audit loads them (written here again, not taken from capacity.py)."""
    from studies.m0.lineages_c1_fix4 import all_written
    from studies.m0.lineages_m1_fix4 import load_registered
    from studies.m0.lineages_r1_fix4_clusters import candidates_v4, registered_v4
    from studies.m0.r2_fix4_set import fix4_set

    out = {}
    r1 = {x.id: x for x in candidates_v4()}
    r1.update({x.id: x for x in registered_v4()})
    out.update(r1)
    out.update(dict(fix4_set()))
    out.update({x.id: x for x in load_registered()})
    out.update(dict(all_written()))
    return out


def load_solvers() -> dict:
    import importlib.util

    out = {}
    for f in ["r1", "r2a", "r2b", "m1a", "m1b", "m1c", "c1"]:
        p = f"{W}/studies/m0/solvers2/solver2_{f}.py"
        spec = importlib.util.spec_from_file_location(f"audit_solver2_{f}", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for lid, fn in mod.SOLVERS.items():
            assert lid not in out
            out[lid] = fn
    return out


def candidates() -> dict:
    return json.load(open(f"{W}/studies/m0/registration/candidate_list.json"))["candidates"]


def my_count(lin, level, target, key_fn, label=AUDIT_LABEL, seed=400002):
    """c(x, v, T), from section 4A stage 4 only. Returns (keys in first-occurrence order, ended, attempts begun).

    Fresh stream stream(400002, label, e, id, str(v)); key set empty; build_item as draw_items calls it (attempt counter
    incremented before the budget test, budget 40T+1000, test before building); discard repeated key; stop at T keys,
    when attempts exceed the budget, or when build_item gives up (RuntimeError after 500 consecutive Retry)."""
    from studies.m0.core import build_item

    rng = my_stream(seed, label, lin.eval, lin.id, str(level))
    seen = set()
    order = []
    attempts = 0
    while len(order) < target:
        attempts += 1
        if attempts > 40 * target + 1000:
            return order, "budget", attempts - 1
        try:
            it = build_item(lin, level, rng, "x", "y")
        except RuntimeError as exc:
            if "500 consecutive retries" in str(exc):
                return order, "gave_up", attempts
            raise
        k = key_fn(lin.id, it.question, it.structured)
        if k in seen:
            continue
        seen.add(k)
        order.append(k)
    return order, "target", attempts
