"""Re-audit check (stdlib only, synthetic): does the ADR item 8 step-3 wording pin a unique stream?
"While query q holds a duplicated slot x, take the later position of x in q" does not say which x when a
dealt query holds two different duplicated slots, or which later position when x appears three times.
This counts how often such queries occur after the step-2 deal on a heavy synthetic histogram, and
shows that an alternative literal reading (the LAST occurrence of the smallest duplicated slot) gives a
different stream than the reading implemented by the study and by independent_sim.fm_stream (the
later position of the first repeated entry met reading left to right).

Run: python3 -I docs/reviews/p7a-preflight-2026-11-13/reaudit/check_item8_wording.py
"""

import hashlib
import random
import sys
from array import array
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import independent_sim as indep  # noqa: E402

Q, TOP = 32768, 8


def heavy() -> list[int]:
    rng = random.Random(3)
    counts = [0] * 4096
    slots = rng.sample(range(4096), 700)
    w = [1 / (r + 1) for r in range(700)]
    scale = TOP * Q / sum(w)
    for s, x in zip(slots, w):
        counts[s] = min(Q, int(x * scale))
    counts[slots[0]] = 18460
    i = 0
    while sum(counts) != TOP * Q:
        s = slots[1 + i % 699]
        if sum(counts) < TOP * Q:
            counts[s] += 1
        elif counts[s] > 1:
            counts[s] -= 1
        i += 1
    return counts


def alt_stream(counts: list[int], s: int, idx: int) -> list[list[int]]:
    g = random.Random(s * 1000 + idx)
    pool = [slot for slot, c in enumerate(counts) for _ in range(c)]
    g.shuffle(pool)
    rows = [pool[TOP * i : TOP * (i + 1)] for i in range(Q)]
    for i in range(Q):
        row = rows[i]
        while len(set(row)) < TOP:
            x = min(v for v in row if row.count(v) > 1)
            later = max(j for j in range(TOP) if row[j] == x)
            present = set(row)
            for d in range(1, Q):
                other = rows[(i + d) % Q]
                if x in other:
                    continue
                k = next((k for k in range(TOP) if other[k] not in present), None)
                if k is not None:
                    row[later], other[k] = other[k], x
                    break
            else:
                raise RuntimeError("no partner")
    order = list(range(Q))
    g.shuffle(order)
    return [rows[i] for i in order]


def main() -> int:
    counts = heavy()
    g = random.Random(91301 * 1000 + 0)
    pool = [slot for slot, c in enumerate(counts) for _ in range(c)]
    g.shuffle(pool)
    rows = [pool[TOP * i : TOP * (i + 1)] for i in range(Q)]
    multi = sum(1 for r in rows if sum(1 for v in set(r) if r.count(v) > 1) >= 2)
    triple = sum(1 for r in rows if any(r.count(v) >= 3 for v in set(r)))
    dup = sum(1 for r in rows if len(set(r)) < TOP)
    registered, _ = indep.fm_stream(counts, 91301, 0, Q)
    alt = alt_stream(counts, 91301, 0)
    sha = lambda rows: hashlib.sha256(array("h", [v for r in rows for v in r]).tobytes()).hexdigest()  # noqa: E731
    lines = [
        f"dealt queries with any duplicate: {dup}; with two or more different duplicated slots: {multi}; "
        f"with a slot three or more times: {triple} (of {Q})",
        f"registered reading sha256 {sha(registered)}",
        f"alternative reading sha256 {sha(alt)}",
        f"streams identical: {registered == alt}",
    ]
    (HERE / "outputs" / "item8_wording.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
