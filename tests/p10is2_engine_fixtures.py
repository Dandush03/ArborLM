# ruff: noqa: E501
"""A tiny Part T world for tests: P10-S2's synthetic data bundle (a made-up word-for-word translation pair, a tiny random student, lexicon teachers; its own test seeds 229001-229999 inside its functions) with this
study's seed plan, training draws and test-mode seeds (934001-934999, 330298-330299). CPU only. Nothing here is a result."""

import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from studies.p10is2 import engine  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10s2.routing import RouterSpec  # noqa: E402
from studies.p10s2.standins import build_synthetic_bundle  # noqa: E402

CFG_T = core.load_config("T")


@lru_cache(maxsize=1)
def bundle():  # type: ignore[no-untyped-def]
    b, _ = build_synthetic_bundle(2)
    return b


def draws(n_reps: int = 3, n: int = 20):  # type: ignore[no-untyped-def]
    """Training draws with disjoint sources between the capabilities (the registered split is made before generation): capability A from its pool, B from its pool minus every source of A's pool."""
    b = bundle()
    a_keys = {x.key for x in b.accepted["A"]}
    pool_b = [x for x in b.accepted["B"] if x.key not in a_keys]
    out = []
    for r in range(n_reps):
        out.append({"A": list(b.accepted["A"])[r * 2 : r * 2 + n], "B": pool_b[r * 2 : r * 2 + n] or pool_b[:n]})
    return out


def world(updates: int = 4, n_reps: int = 3):  # type: ignore[no-untyped-def]
    run = engine.run_config(CFG_T, layer=1, updates=updates, store_rate=0.003, lora_rate=0.001, device="cpu", batch=4, rows=16, router=RouterSpec.dry(), decision_token=8, window_tokens=24, ranks=(2, 4), replay=4)
    w = engine.build_world_t(bundle(), CFG_T, draws(n_reps), run, plan_mode="test")
    w.etable_lr = 0.003  # type: ignore[attr-defined]
    return w
