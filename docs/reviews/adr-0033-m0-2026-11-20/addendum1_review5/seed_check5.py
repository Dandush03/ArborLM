# ruff: noqa
"""Check 5, scope 5: derive the seed for an unseeded cheap-rule script from the text of draft 5, section 4A stage 0 point 7,
and section 4's definition of stream(). Own code, standard library only; does not import the drafter's script.

Text (point 7): int.from_bytes(sha256("400002|cheap-rule|" + base name)[:8], "big"); base name = file name with extension,
without any directory. Section 4: the decimal seed and the labels joined by '|', UTF-8, SHA-256, first 8 bytes big-endian.
"""
import hashlib
import random


def derive(seed, *labels):
    s = "|".join([str(seed), *labels])
    return int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8], "big")


def derive_point7_literal(base):
    # the literal form written in point 7
    return int.from_bytes(hashlib.sha256(("400002|cheap-rule|" + base).encode("utf-8")).digest()[:8], "big")


cases = [
    ("drafter's made-up example, base name", "example_rules.py"),
    ("drafter's made-up example, path (not the rule)", "docs/reviews/some_folder/example_rules.py"),
    ("named script of the record (M1 fix-3 battery; it is seeded, 410302, so point 7 does not apply to it)", "m1_fix3_shortcuts.py"),
    ("same script, without extension (not the rule)", "m1_fix3_shortcuts"),
]
print("PART 1. derived integers")
for what, name in cases:
    a = derive(400002, "cheap-rule", name)
    b = derive_point7_literal(name)
    assert a == b, (name, a, b)
    print(f"  {what}\n    '400002|cheap-rule|{name}' -> {a}")

print()
print("PART 2. agreement with the drafter's printed part B (addendum1_rev5_arithmetic.out.txt)")
printed = {"example_rules.py": 1035349750409085599, "docs/reviews/some_folder/example_rules.py": 15176297000423028348}
for k, v in printed.items():
    print(f"  {k}: mine {derive(400002, 'cheap-rule', k)} printed {v} equal {derive(400002, 'cheap-rule', k) == v}")

print()
print("PART 3. the integer seeds random.Random; first three draws of random() for m1_fix3_shortcuts.py, for the record")
r = random.Random(derive(400002, "cheap-rule", "m1_fix3_shortcuts.py"))
print("  ", [round(r.random(), 12) for _ in range(3)])

print()
print("PART 4. label collision check: the new first labels against the one existing stream on 400002 (check 4 scope 4)")
for lab in ("cheap-rule", "capacity"):
    print(f"  '{lab}' == 'development': {lab == 'development'}; contains '|': {'|' in lab}")
