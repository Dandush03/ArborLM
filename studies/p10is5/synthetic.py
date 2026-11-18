# ruff: noqa: E501
"""Synthetic registries for the P10IS5 analysis tests (module of the package so that pytest does not collect it). Latencies are explicit, so every label has a known answer computed by hand in the tests, not by the
analysis's own helpers. Nothing here touches a device, a file of the study or a registered seed. Self-check only."""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import core

SIZES = (1, 3, 8, 64)
DEPTHS = (1, 2, 4, 8, 16, 32)
N_OF = {1: 400, 3: 400, 8: 160, 64: 64}
GRID = [(k, s) for k in DEPTHS for s in SIZES]
PAGE = 16384
QUIET_OK = {"ok": True}
QUIET_BAD = {"ok": False, "failed": ["load"]}


def default_thresholds(m_t: float = 0.10, timing_spread: bool = False) -> dict[str, Any]:
    return {
        "m_t": m_t, "timing_spread": timing_spread, "label_min_repeats": 4, "valid_min_repeats": 4, "harness_limited_fraction": 0.25, "sizes": list(SIZES), "depths": list(DEPTHS), "grid": [list(c) for c in GRID],
    }  # fmt: skip


def lat_list(median_ns: int, n: int) -> list[int]:
    """n - 1 requests at ``median_ns`` and one at ten times: the median is ``median_ns`` and so is p90 and p99 (for n >= 100); the maximum is ten times."""
    return [median_ns] * (n - 1) + [10 * median_ns]


def make_pass(stage: str, repeat: int, k: int, s: int, block: str, role: str, seq: int, median_ns: int, *, status: str = "OK", counter_delta: int = 0, pps: float = 1000.0, attempt: int = 1, parity: bool | None = True) -> dict[str, Any]:
    n = N_OF[s]
    predicted = PAGE * s * n
    counter = predicted + counter_delta if status == "OK" else (predicted - PAGE if status == core.STORE_PAGES_CACHED else predicted + PAGE)
    counter = predicted + counter_delta if status == "OK" else counter
    return {
        "key": core.pass_key(stage, repeat, k, s, attempt), "stage": stage, "repeat": repeat, "k": k, "s": s, "attempt": attempt, "block": block, "role": role, "seq": seq, "predicted_bytes": predicted, "counter_bytes": counter, "written_bytes": 0,
        "counter_status": status, "latency_ns": lat_list(median_ns, n), "pages_per_second": pps, "parity_ok": parity, "requests": n,
    }  # fmt: skip


def make_registry(
    *,
    median_of: Callable[[int, int, int], int] | None = None,
    repeats: int = 5,
    spare: bool = False,
    quiet: Mapping[int, tuple[Mapping[str, Any], Mapping[str, Any]]] | None = None,
    bad_cells: Mapping[tuple[int, int, int], str] | None = None,
    spare_bad_cells: Mapping[tuple[int, int], str] | None = None,
    spare_quiet: tuple[Mapping[str, Any], Mapping[str, Any]] = (QUIET_OK, QUIET_OK),
    harness_ns: Mapping[int, int] | None = None,
    r1_reasons: Sequence[str] = (),
    cold_outcomes: Sequence[str] = (),
    manifest: Mapping[str, Any] | None = None,
    stops: Sequence[Mapping[str, Any]] = (),
    thresholds: Mapping[str, Any] | None = None,
    stage: str = "E2",
) -> dict[str, Any]:
    """A registry of ``repeats`` regular blocks (and a spare if ``spare``), 24 passes each. ``median_of(repeat, k, s)`` gives the per-pass median latency in ns (default: 50,000 + 20,000 (s - 1) / (1 + 0.1 (k - 1))
    rounded to integer ns, the same in every repeat). ``quiet`` overrides (start, end) readings by repeat; ``bad_cells`` maps (repeat, k, s) to a counter status that fails the rule."""
    median_of = median_of or (lambda r, k, s: round(50_000 + 20_000 * (s - 1) / (1 + 0.1 * (k - 1))))
    passes: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    seq = 0
    all_reps = list(range(1, repeats + 1)) + ([repeats + 1] if spare else [])
    for r in all_reps:
        role = "spare" if spare and r == repeats + 1 else "regular"
        bkey = core.block_key(stage, r)
        keys = []
        for k, s in GRID:
            seq += 1
            st = (bad_cells or {}).get((r, k, s)) if role == "regular" else (spare_bad_cells or {}).get((k, s))
            p = make_pass(stage, r, k, s, bkey, role, seq, median_of(r, k, s), status=st or "OK")
            passes.append(p)
            keys.append(p["key"])
        q = spare_quiet if role == "spare" else (quiet or {}).get(r, (QUIET_OK, QUIET_OK))
        blocks.append({"key": bkey, "stage": stage, "repeat": r, "role": role, "quiet_start": dict(q[0]), "quiet_end": dict(q[1]), "pass_keys": keys, "complete": True})
    harness = {k: {"status": "MEASURED", "median_ns": (harness_ns or {}).get(k, 1_000)} for k in DEPTHS}
    return {
        "passes": passes, "blocks": blocks, "harness": harness, "r1": {"not_evaluable_reasons": list(r1_reasons)}, "cold_checks": [{"outcome": o} for o in cold_outcomes], "manifest": dict(manifest or {}), "stops": [dict(s) for s in stops],
        "thresholds": dict(thresholds or default_thresholds()),
    }  # fmt: skip
