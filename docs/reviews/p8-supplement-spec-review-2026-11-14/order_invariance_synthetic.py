"""ADR-0016 spec review, proof item 2, empirical companion (SYNTHETIC DATA ONLY).

Checks on synthetic streams that the frozen consumers of a null-stream tensor in the P8 path
(``p7b_sim.page_sets`` -> ``p7b_sim.simulate_group`` and ``p8_sim.temporal_reuse``) give identical
output when the slots inside each row are permuted, and that the only order-dependent quantity is
the stream hash (``sha256`` of the int16 pack, as ``p7a_core.frequency_matched_detail``).

Also checks, on a synthetic single-set stream, the analytic predictions of ADR-0016 section 2:
m = 0 at both settings and both tie rules for any layout, temporal reuse = 1.

No real trace, no P8 cell and no registered null is touched. Not Astra validation.

Run: uv run --locked python -I docs/reviews/p8-supplement-spec-review-2026-11-14/order_invariance_synthetic.py
"""

import array
import hashlib
import json
import random
import sys

import torch

from arborlm import p7b_sim as sim
from arborlm import p8_sim

SLOTS = 4096
TOP = 8
CONTEXT = 64
SETTINGS = ((2, 32), (8, 8))


def pack_hash(t: torch.Tensor) -> str:
    # little-endian int16, C order (platform is little-endian arm64; asserted)
    assert sys.byteorder == "little"
    flat = array.array("h", t.flatten().tolist())
    return hashlib.sha256(flat.tobytes()).hexdigest()


def random_stream(rng: random.Random, queries: int, pool: int) -> torch.Tensor:
    slots = rng.sample(range(SLOTS), pool)
    return torch.tensor([rng.sample(slots, TOP) for _ in range(queries)], dtype=torch.int64)


def shuffle_rows(rng: random.Random, t: torch.Tensor) -> torch.Tensor:
    rows = t.tolist()
    for r in rows:
        rng.shuffle(r)
    return torch.tensor(rows, dtype=torch.int64)


def run_sim(stream: torch.Tensor, order: list[int]) -> dict[str, object]:
    positions = sim.positions_tensor(order)
    out: dict[str, object] = {}
    for rows, cap in SETTINGS:
        q = sim.page_sets(positions, rows, stream)
        out[f"R{rows}"] = sim.simulate_group(q, (cap,), (cap,), f"syn|R{rows}")
    out["reuse"] = p8_sim.temporal_reuse(stream)
    return out


def m_values(res: dict[str, object]) -> dict[str, int]:
    vals: dict[str, int] = {}
    for rows, cap in SETTINGS:
        group = res[f"R{rows}"]
        assert isinstance(group, dict)
        for tie in ("asc", "desc"):
            c = group["by_c"][str(cap)][tie]
            vals[f"R{rows}|{tie}"] = c["misses_warm"] - c["first_touch_warm"]
    return vals


def main() -> int:
    rng = random.Random(20261114)
    report: dict[str, object] = {"label": "synthetic only; not Astra validation"}
    queries = CONTEXT * 16  # 1,024 queries: an even number of whole contexts
    invariance = []
    for trial in range(6):
        pool = (12, 40, 90, 200, 600, 2000)[trial]
        stream = random_stream(rng, queries, pool)
        perm = shuffle_rows(rng, stream)
        assert sorted(map(sorted, stream.tolist())) == sorted(map(sorted, perm.tolist()))
        for layout_seed in range(3):
            order = list(range(SLOTS))
            random.Random(1000 + layout_seed).shuffle(order)
            a, b = run_sim(stream, order), run_sim(perm, order)
            invariance.append(
                {
                    "pool": pool,
                    "layout_seed": layout_seed,
                    "sim_and_reuse_equal": a == b,
                    "stream_hash_equal": pack_hash(stream) == pack_hash(perm),
                    "m": m_values(a),
                    "reuse": a["reuse"]["value"],  # type: ignore[index]
                }
            )
    report["within_row_order_invariance"] = invariance

    # single-set synthetic stream: precondition of ADR-0016 section 3
    s = sorted(rng.sample(range(SLOTS), TOP))
    trace_like = torch.tensor(
        [rng.sample(s, TOP) for _ in range(queries)], dtype=torch.int64
    )  # rows in varying order, as the real collapsed traces
    identity = torch.tensor([s] * queries, dtype=torch.int64)
    single = []
    for layout_seed in range(5):
        order = list(range(SLOTS))
        random.Random(2000 + layout_seed).shuffle(order)
        a, b = run_sim(trace_like, order), run_sim(identity, order)
        single.append(
            {
                "layout_seed": layout_seed,
                "actual_equals_identity_null": a == b,
                "m_actual": m_values(a),
                "m_identity": m_values(b),
                "reuse_actual": a["reuse"]["value"],  # type: ignore[index]
                "reuse_identity": b["reuse"]["value"],  # type: ignore[index]
            }
        )
    report["single_set"] = single
    ok = all(r["sim_and_reuse_equal"] for r in invariance) and all(
        r["actual_equals_identity_null"]
        and set(r["m_actual"].values()) == {0}
        and r["reuse_actual"] == 1.0
        for r in single
    )
    hash_differs = all(not r["stream_hash_equal"] for r in invariance)
    report["verdict"] = {"all_invariant_and_predictions_hold": ok, "hash_order_dependent": hash_differs}
    json.dump(report, sys.stdout, indent=1, sort_keys=True)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
