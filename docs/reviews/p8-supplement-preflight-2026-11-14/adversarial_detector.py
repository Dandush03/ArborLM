"""Auditor's adversarial inputs for ``supplements.p8s.null`` (the object under test).

Usage: uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/adversarial_detector.py

Each case states what ADR-0016 section 3 requires (holds or not) and what the detector returned.
An independent reference predicate (written here from the section 3 text, not from the code) is
also evaluated: precondition = exactly eight slots with non-zero count, each count == Q; the
redundant assertion = every row, as a set, equals S.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import torch  # noqa: E402

from supplements.p8s import null  # noqa: E402

S = [5, 40, 41, 900, 1023, 2047, 3000, 4095]


def reference(rows: list[list[int]]) -> bool:
    q = len(rows)
    counts: dict[int, int] = {}
    for r in rows:
        for s in r:
            counts[s] = counts.get(s, 0) + 1
    pre = q > 0 and len(counts) == 8 and all(c == q for c in counts.values())
    if not pre:
        return False
    sset = set(counts)
    return all(len(r) == 8 and set(r) == sset for r in rows)


def run(name: str, rows: list[list[int]], dtype: torch.dtype = torch.int64) -> bool:
    t = torch.tensor(rows, dtype=dtype)
    try:
        got = null.detect_single_set(t)
        holds: object = got.holds
        extra = f"slots={got.slots} reasons={got.reasons}"
    except Exception as exc:  # noqa: BLE001 - recorded
        holds = f"EXCEPTION {type(exc).__name__}"
        extra = str(exc)[:100]
    ref = reference(rows)
    agree = holds == ref
    print(f"{'OK ' if agree else 'BAD'} {name}: detector={holds} reference={ref} {extra}")
    return agree


def main() -> None:
    q = 64
    base = [list(S) for _ in range(q)]
    cases: list[tuple[str, list[list[int]]]] = []
    cases.append(("all rows S ascending", [list(S) for _ in range(q)]))
    cases.append(
        ("all rows S, each a different permutation", [S[i % 8 :] + S[: i % 8] for i in range(q)])
    )
    # counts pass, rows fail: row 0 has a twice and lacks h; row 1 has h twice and lacks a
    r = [list(S) for _ in range(q)]
    r[0] = [S[0], S[0], *S[1:7]]
    r[1] = [S[7], S[7], *S[1:7]]
    cases.append(("duplicates that preserve every count (only the direct check can catch it)", r))
    # nine slots, all counts not Q
    r = [list(S) for _ in range(q)]
    r[3][2] = 7
    cases.append(("one query differs (nine slots)", r))
    # eight slots, one count Q-1, total 8Q-1 impossible with 8 per row -> use duplicate
    r = [list(S) for _ in range(q)]
    r[0][0] = S[1]
    cases.append(("eight slots, one count below Q, another above Q", r))
    cases.append(("Q = 1", [list(S)]))
    cases.append(("Q = 3 (not a multiple of 64)", [list(S)] * 3))
    cases.append(
        ("seven distinct slots per row padded with a repeat", [S[:7] + [S[0]] for _ in range(q)])
    )
    cases.append(("slot 0 included", [[0, *S[1:]] for _ in range(q)]))
    cases.append(
        (
            "two disjoint sets alternating",
            [S if i % 2 else [s + 1 for s in S[:7]] + [6] for i in range(q)],
        )
    )
    ok = all(run(n, rr) for n, rr in cases)
    ok &= run("int16 dtype", [list(S) for _ in range(q)], torch.int16)
    ok &= run("int32 dtype", [list(S) for _ in range(q)], torch.int32)
    # outside the trace domain (load_trace would reject these first): record behaviour only
    for name, rows in (
        ("negative slot id", [[-1, *S[1:]] for _ in range(q)]),
        ("slot id 4096", [[*S[:7], 4096] for _ in range(q)]),
    ):
        run(name + " [domain excluded by load_trace]", rows)
    # empty trace
    try:
        got = null.detect_single_set(torch.zeros((0, 8), dtype=torch.int64))
        print(f"OK  empty trace: holds={got.holds} reasons={got.reasons}")
    except Exception as exc:  # noqa: BLE001
        print(f"BAD empty trace raised {type(exc).__name__}: {exc}")
        ok = False
    # precondition-false branch: identical to the registered generator for a near-collapsed trace
    rows = [list(S) for _ in range(q)]
    for i in range(0, q, 2):
        rows[i][7] = 77  # nine slots, counts Q/2 for two of them
    t = torch.tensor(rows, dtype=torch.int64)
    from arborlm import p7a_core as a_core
    from arborlm import p7b_core as b_core

    seeds = (91331, 91332, 91333)

    def both(tt: torch.Tensor, name: str) -> bool:
        # run 1 of this script crashed here: the registered generator itself raises on the
        # near-collapsed 9-slot trace. Run 2 compares outcomes, including the exception.
        def attempt(fn):  # type: ignore[no-untyped-def]
            try:
                return ("ok", fn())
            except Exception as exc:  # noqa: BLE001
                return ("raised", f"{type(exc).__name__}: {exc}")

        a = attempt(lambda: null.supplement_null_provider(tt, seeds, 12))
        b = attempt(lambda: b_core.null_streams(a_core.selection_counts(tt), seeds, 12))
        if a[0] != b[0]:
            same = False
        elif a[0] == "raised":
            same = a[1] == b[1]
        else:
            mine, info = a[1]
            reg, reg_info = b[1]
            same = (
                all(torch.equal(x, y) for x, y in zip(mine, reg, strict=True))
                and [{k: v for k, v in d.items() if k != "precondition"} for d in info] == reg_info
            )
        print(
            f"{'OK ' if same else 'BAD'} precondition-false ({name}): supplement={a[0]} registered={b[0]} {a[1] if a[0] == 'raised' else ''}"
        )
        return same

    ok &= both(t, "9-slot near-collapse, generator raises")
    from arborlm.p7a_trace import synthetic_trace

    sel, _ = synthetic_trace("flat", 11, queries=256, hot_slots=32)
    ok &= both(sel.to(torch.int64), "synthetic 32-hot-slot trace")
    # identity branch: ascending rows, counts, hash identical across replicates, seeds recorded
    streams, info = null.supplement_null_provider(torch.tensor(base[::-1]), seeds, 12)
    asc = all(r == sorted(S) for r in streams[0].tolist())
    hashes = {d["stream_sha256"] for d in info}
    gens = [d["generator_seed"] for d in info]
    good = asc and len(hashes) == 1 and gens == [s * 1000 + 12 for s in seeds]
    print(
        f"{'OK ' if good else 'BAD'} identity branch: ascending={asc} hashes={len(hashes)} gens={gens}"
    )
    ok &= good
    print("ALL AGREE" if ok else "DISAGREEMENT FOUND")


if __name__ == "__main__":
    main()
