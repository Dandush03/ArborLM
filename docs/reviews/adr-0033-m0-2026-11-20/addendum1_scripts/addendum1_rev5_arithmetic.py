"""ADR-0033 addendum 1, draft 5: arithmetic for the two things draft 5 states anew.

Standard library only. Reads no cluster map, no lineage, no run output and no model.

Part A (check 4, H6): the slack k * D_lin(G, k) - D(G) of section 4A stage 4, for
G = 1..19 and k = 2..8: where it is zero, and its maximum.
  D(G)        = 10 * (ceil(4000 / G) + ceil(20000 / G) + 100)
  D_lin(G, k) = 10 * (ceil(ceil(4000 / G) / k) + ceil(ceil(20000 / G) / k) + ceil(100 / k))

Part B (check 4, H2): the derived seed of section 4A stage 0 for a cheap-rule script on
record without a seed, on a MADE-UP base name that names no script on record. It shows
that the base name and a repository path give two different integers, which is why the
text fixes the base name.

Run: uv run --locked python -I -B addendum1_rev5_arithmetic.py > addendum1_rev5_arithmetic.out.txt
"""

import hashlib
from math import ceil


def demand(g: int) -> int:
    return 10 * (ceil(4000 / g) + ceil(20000 / g) + 100)


def demand_lin(g: int, k: int) -> int:
    return 10 * (ceil(ceil(4000 / g) / k) + ceil(ceil(20000 / g) / k) + ceil(100 / k))


def derived(*labels: str) -> int:
    text = "|".join(labels)
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def main() -> None:
    print("PART A. slack(G, k) = k * D_lin(G, k) - D(G), G = 1..19, k = 2..8")
    worst = (-1, 0, 0)
    negative = 0
    for k in range(2, 9):
        zeros = []
        row = []
        for g in range(1, 20):
            s = k * demand_lin(g, k) - demand(g)
            if s < 0:
                negative += 1
            if s == 0:
                zeros.append(g)
            if s > worst[0]:
                worst = (s, g, k)
            row.append(s)
        print(f"k = {k}: zero slack at G = {zeros if zeros else 'none'}")
        print(f"        slack for G = 1..19: {row}")
    print(f"cells with negative slack: {negative}")
    print(f"maximum slack: {worst[0]} keys, first reached at G = {worst[1]}, k = {worst[2]}")
    at_max = [(g, k) for k in range(2, 9) for g in range(1, 20) if k * demand_lin(g, k) - demand(g) == worst[0]]
    print(f"cells at the maximum (G, k): {at_max}")
    print()
    print("slack as a share of D(G), largest over the same cells:")
    share = max(((k * demand_lin(g, k) - demand(g)) / demand(g), g, k) for k in range(2, 9) for g in range(1, 20))
    print(f"  {share[0]:.5f} at G = {share[1]}, k = {share[2]} (D = {demand(share[1])})")
    print()
    print("PART B. derived seed for an unseeded cheap-rule script (made-up name)")
    base = "example_rules.py"
    path = "docs/reviews/some_folder/example_rules.py"
    a = derived("400002", "cheap-rule", base)
    b = derived("400002", "cheap-rule", path)
    print(f"  '400002|cheap-rule|{base}' -> {a}")
    print(f"  '400002|cheap-rule|{path}' -> {b}")
    print(f"  equal: {a == b}")


if __name__ == "__main__":
    main()
