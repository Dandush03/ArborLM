# ruff: noqa
"""Test vectors for the cluster-partition mechanics of ADR-0033 addendum 1, draft 2, section 4.

This is NOT the partition code of record and it reads NO cluster map. Every identity below is made up. It exists so
that a third party who implements section 4 from the text alone can check the derivation byte for byte:
the derived integers, a shuffle of a made-up list, and the whole procedure on a made-up map.
Standard library only; imports nothing from studies/. CPython 3.12 (random.Random is the Mersenne Twister;
shuffle is the Fisher-Yates loop of Lib/random.py).

Run:  uv run --locked python -I docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/partition_vector.py
"""

from __future__ import annotations

import hashlib
import random
import sys

SEED = 400004
EVALS = ("R1", "R2", "M1", "C1")


def derive(seed: int, *labels: str) -> int:
    text = "|".join([str(seed), *labels])
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def stream(seed: int, *labels: str) -> random.Random:
    return random.Random(derive(seed, *labels))


def shuffled(ids: list[str], rng: random.Random) -> list[str]:
    out = sorted(ids)  # Python str order = Unicode code-point order
    rng.shuffle(out)
    return out


# made-up map: lineage id -> registered?; links = pairs the (made-up) auditor judged one procedure
LINEAGES = {
    "R1.alpha": True, "R1.beta": True, "R1.gamma": True, "R1.delta": False, "R1.epsilon": True, "R1.zeta": True,
    "R2.alpha": True, "R2.beta": True, "R2.gamma": True, "R2.delta": True, "R2.epsilon": True,
    "M1.alpha": True, "M1.beta": True, "M1.gamma": True, "M1.delta": True,
    "C1.alpha": True, "C1.beta": True, "C1.gamma": True, "C1.delta": True, "C1.epsilon": False,
}
LINKS = [
    ("R1.alpha", "R1.beta"),      # two lineages of one evaluation: one cluster
    ("C1.alpha", "R2.alpha"),     # cross-evaluation
    ("C1.beta", "R2.beta"),       # cross-evaluation
    ("M1.alpha", "R2.gamma"),     # cross-evaluation
    ("C1.gamma", "M1.beta"),      # cross-evaluation
    ("R1.gamma", "R1.delta"),     # a registered and an unregistered lineage
    ("C1.epsilon", "R1.epsilon"), # cross-evaluation only through an unregistered lineage: not in X
]


def components() -> dict[str, list[str]]:
    parent = {x: x for x in LINEAGES}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in LINKS:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    comp: dict[str, list[str]] = {}
    for x in LINEAGES:
        comp.setdefault(find(x), []).append(x)
    return {min(v): sorted(v) for v in comp.values()}


def partition() -> tuple[dict[str, str], dict[str, tuple[int, int, int]], list[str]]:
    comps = components()
    reg = {cid: sorted({x.split(".", 1)[0] for x in mem if LINEAGES[x]}) for cid, mem in comps.items()}
    assigned = {cid: ev for cid, ev in reg.items() if ev}  # step 1
    cross = [cid for cid, ev in assigned.items() if len(ev) >= 2]
    part: dict[str, str] = {}
    order_x = shuffled(cross, stream(SEED, "cluster-partition", "cross"))  # step 2
    for i, cid in enumerate(order_x):
        part[cid] = "A" if i % 2 == 0 else "B"
    report = {}
    for e in EVALS:  # step 3, in this order
        total = [cid for cid, ev in assigned.items() if e in ev]
        target = len(total) // 2
        x_a = sum(1 for cid in total if cid in cross and part[cid] == "A")
        local = [cid for cid in total if assigned[cid] == [e]]
        k = min(len(local), max(0, target - x_a))
        for i, cid in enumerate(shuffled(local, stream(SEED, "cluster-partition", e))):
            part[cid] = "A" if i < k else "B"
        a = sum(1 for cid in total if part[cid] == "A")
        report[e] = (len(total), a, len(total) - a)
    return part, report, order_x


def main() -> None:
    print("python", sys.version.split()[0])
    print("== 1. derived integers (first 8 bytes of SHA-256, big-endian)")
    for labels in (("cluster-partition", "cross"), *[("cluster-partition", e) for e in EVALS]):
        text = "|".join([str(SEED), *labels])
        print(f"  {text!r}: sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()}  ->  {derive(SEED, *labels)}")
    print("== 2. shuffle of the made-up list ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'] (sorted first) on each stream")
    for labels in (("cluster-partition", "cross"), *[("cluster-partition", e) for e in EVALS]):
        print(f"  {labels[1]:>5}: {shuffled(list('hgfedcba'), stream(SEED, *labels))}")
    print("== 3. the whole of section 4 on the made-up map in this file")
    comps = components()
    for cid, mem in sorted(comps.items()):
        if len(mem) > 1:
            print(f"  component {cid}: {mem}")
    part, report, order_x = partition()
    print("  cross-evaluation clusters in shuffled order:", order_x)
    print("  part A:", sorted(c for c, p in part.items() if p == "A"))
    print("  part B:", sorted(c for c, p in part.items() if p == "B"))
    print("  unassigned (no registered lineage):", sorted(c for c in comps if c not in part))
    print("  per evaluation (clusters, in A, in B):", report)
    members = {x: cid for cid, mem in comps.items() for x in mem}
    for e in EVALS:
        a = {members[x] for x in LINEAGES if x.startswith(e + ".") and LINEAGES[x] and part[members[x]] == "A"}
        b = {members[x] for x in LINEAGES if x.startswith(e + ".") and LINEAGES[x] and part[members[x]] == "B"}
        assert not (a & b)
    print("  no cluster in both parts: asserted")


if __name__ == "__main__":
    main()
