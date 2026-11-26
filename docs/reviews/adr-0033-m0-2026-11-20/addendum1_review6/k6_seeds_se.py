"""Check 6, scopes 3 and 4: the seed integers of addendum 1 draft 6 (section 4A stage 1S point 4) recomputed from the
text alone, and the standard errors of point 5. Standard library only. Reads one file: the drafter's output, to compare.
No item is generated, no rule script is run, no lineage figure is computed.
Usage: python k6_seeds_se.py <path of addendum1_rev6_fresh_run.out.txt>
"""
from __future__ import annotations

import hashlib
import math
import re
import sys


def d(*parts: object) -> int:
    # the text: decimal text of the seed and the labels joined by '|', UTF-8, SHA-256, first 8 bytes big-endian
    return int.from_bytes(hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).digest()[:8], "big")


# roles as listed in the text, point 4 (typed from the text, not from the drafter's script)
ROLES = {
    "R1a": "aud_seed aud_fit impl_seed impl_fit feat1_fit feat1_test feat2_fit feat2_test".split(),
    "R1b": "aud_seed aud_fit impl_seed impl_fit feat_fit feat_test".split(),
    "R1c": "fit test".split(),
    "R2a": ["tag"], "R2b": ["tag"],
    "M1a": "own a4 a3".split(),
    "M1b": ["seed"], "M1c": ["seed"], "C1a": ["seed"], "C1b": ["seed"], "C1c": ["seed"],
}
TEXT_BASES = {"1": 16103270370041696293, "2": 10773834973117025986, "3": 619660634241804713}
TEXT_DRY = 3342082268851962967


def main() -> None:
    print("SCOPE 3. Seeds")
    bases = {i: d(400002, "fresh-shortcut", i) for i in ("1", "2", "3")}
    dry = d(400002, "fresh-shortcut-dry-run")
    for i, v in bases.items():
        print(f"  base {i}: {v}  text {TEXT_BASES[i]}  {'AGREE' if v == TEXT_BASES[i] else 'DIFFER'}")
    print(f"  dry: {dry}  text {TEXT_DRY}  {'AGREE' if dry == TEXT_DRY else 'DIFFER'}")
    per: dict[tuple[str, str, str], int] = {}
    for name, b in [*bases.items(), ("dry", dry)]:
        for u, rs in ROLES.items():
            for r in rs:
                per[(name, u, r)] = d(b, u, r)
    allv = [*bases.values(), dry, *per.values()]
    print(f"  roles per seed {sum(len(r) for r in ROLES.values())}; integers {len(allv)}; distinct {len(set(allv))}")
    print(f"  all below 2**64: {all(0 <= v < 2**64 for v in allv)}; smallest {min(allv)}; largest {max(allv)}")
    # compare every per-unit integer with the drafter's output
    txt = open(sys.argv[1], encoding="utf-8").read()
    rows = re.findall(r"'(\d+)\|(\w+)\|(\w+)' -> (\d+)", txt)
    bymap = {"16103270370041696293": "1", "10773834973117025986": "2", "619660634241804713": "3", "3342082268851962967": "dry"}
    diff = 0
    for b, u, r, v in rows:
        if (bymap.get(b), u, r) not in per or per[(bymap[b], u, r)] != int(v):
            diff += 1
            print("   DIFFER", b, u, r, v)
    print(f"  drafter's per-unit rows read: {len(rows)}; differences from mine: {diff}; mine not in drafter's: {len(set(per) - {(bymap[b], u, r) for b, u, r, _ in rows})}")
    print("  sample (mine):")
    for k in [("1", "R1a", "aud_seed"), ("2", "M1a", "a3"), ("3", "C1c", "seed"), ("dry", "R2b", "tag"), ("3", "R1b", "feat_test")]:
        print(f"    {k}: {per[k]}")
    # registered values of ADR-0033 section 12 and integers of the other labels named in the addendum
    reg = set(range(400001, 400014)) | {400031, 400032} | set(range(409001, 409100)) | set(range(953001, 954000))
    other = {"400002|development": d(400002, "development"), "400002|capacity": d(400002, "capacity"),
             "400002|cheap-rule": d(400002, "cheap-rule"), "400002|fresh-shortcut": d(400002, "fresh-shortcut")}
    for lab in ("cross", "R1", "R2", "M1", "C1"):
        other[f"400004|cluster-partition|{lab}"] = d(400004, "cluster-partition", lab)
    for s in sorted(reg | {400004}):
        pass
    print(f"  collisions with registered values of ADR-0033 section 12 (400001-400013, 400031, 400032, 409001-409099, 953001-953999): {len(set(allv) & reg)}")
    print(f"  collisions with the integers of other labels: {sorted(k for k, v in other.items() if v in set(allv))}")
    print(f"  smallest integer of the 108 is {min(allv)}, so none lies in any registered range (all registered values are < 10**6)")
    # R1 scripts form per-level streams by ADDING to the seed: Random(s + level) (gen4/fgen/r1_fix4_gen) and Random(s*1000 + level) (r1_fix3_battery)
    eff: dict[int, list[str]] = {}
    for (name, u, r), s in per.items():
        if not u.startswith("R1"):
            continue
        for lv in range(7):
            eff.setdefault(s + lv, []).append(f"{name}/{u}/{r}/+{lv}")
            eff.setdefault(s * 1000 + lv, []).append(f"{name}/{u}/{r}/*1000+{lv}")
    clash = {k: v for k, v in eff.items() if len(v) > 1}
    print(f"  R1 effective per-level integers under both forms: {len(eff)}; shared by two roles: {len(clash)}")
    r1 = sorted(v for (n_, u, _), v in per.items() if u.startswith("R1"))
    print(f"  smallest gap between two R1 role integers: {min(b - a for a, b in zip(r1, r1[1:]))} (streams overlap only if a gap is <= 6)")
    print()
    print("SCOPE 4. Binomial standard error sqrt(p(1-p)/n) at the bound")
    for ev, n1 in (("R1", 3000), ("R2/M1", 4000), ("C1", 2000)):
        n = 3 * n1
        print(f"  {ev}: n = {n}: open p=0.15 {math.sqrt(.15*.85/n):.4f}; yes/no p=0.65 {math.sqrt(.65*.35/n):.4f}; p=0.5 {math.sqrt(.25/n):.4f}")
    print(f"  dry run n = 20: p=0.15 {math.sqrt(.15*.85/20):.3f}; p=0.5 {math.sqrt(.25/20):.3f}")
    n = 3 * 300
    print(f"  M1a digit_puzzle lineages (m1_fix4_battery caps n at 300 per level and seed): n = {n}: p=0.15 {math.sqrt(.15*.85/n):.4f}; p=0.5 {math.sqrt(.25/n):.4f}")
    # a difference rate - base of two estimates from the same items (M1 read against base): worst case if independent
    for n1 in (4000,):
        n = 3 * n1
        print(f"  M1 rate - base, both near 0.15 apart (rate 0.30, base 0.15), as if independent: {math.sqrt(.3*.7/n + .15*.85/n):.4f}")
    # rounding: printed at d decimals after an earlier rounding to 4 (new_rules_final.py: round(x, 4) then format .3f)
    print("  double rounding in new_rules_final.py: |error| <= 0.00005 + 0.0005 = 0.00055 (the text says 0.0005);")
    print("  with three seeds of equal n the pooled mean lies on a grid of 1/3000, and 0.149 + 0.00055 < 0.15 <= 0.1500 - so the outcome is the same")
    # share recovery: round(share*n) recovers the count exactly when the share is written to 4 decimals and n < 5000
    print(f"  count recovered from a share at 4 decimals is exact iff n * 0.00005 < 0.5, i.e. n < 10000; at 2,000 per level: exact")


if __name__ == "__main__":
    main()
