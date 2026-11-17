"""Auditor check A0: which sections of ADR-0021 changed between revision 4 (+s22-s24) and the revision 5 draft,
and whether the sections the draft says are unchanged (s15, s17-s24, Addendum, verbatim quotations) are byte-identical.
Also lists every line of the revision 5 text that still names a revision-4-only cell or size.
Usage: python3 -I a0_sections.py <rev4.md> <rev5.md>"""
import re
import sys

old, new = (open(p, encoding="utf-8").read() for p in sys.argv[1:3])


def sections(text):
    out, key, buf = {}, "header", []
    for line in text.splitlines():
        m = re.match(r"^## (\d+\.?\d*|Addendum)", line)
        if m:
            out[key] = "\n".join(buf)
            key, buf = m.group(1).rstrip("."), []
        buf.append(line)
    out[key] = "\n".join(buf)
    return out


so, sn = sections(old), sections(new)
print("section  rev4_chars rev5_chars identical")
for k in sorted(set(so) | set(sn), key=lambda s: (s == "Addendum", float(s) if s.replace(".", "").isdigit() else -1)):
    a, b = so.get(k), sn.get(k)
    print(f"{k:8s} {len(a or ''):10d} {len(b or ''):10d} {a == b}")

quotes_old = re.findall(r"^> .*$", old, re.M)
quotes_new = re.findall(r"^> .*$", new, re.M)
print("\nverbatim quotations in rev4:", len(quotes_old), "in rev5:", len(quotes_new), "all rev4 quotes present in rev5:", all(q in quotes_new for q in quotes_old))

print("\nrev5 lines (outside s17-s24 and s25.3/25.6, which are historical) naming revision-4-only cells or sizes:")
pat = re.compile(r"65,536 slots|65536|64K|32K/64K|8K/64K|Study A|Study B|overload|A1|A2|B1|\bB3\b|diagonal|12 charged hours|16 charged hours")
cur = "header"
for n, line in enumerate(new.splitlines(), 1):
    m = re.match(r"^## (\d+|Addendum)", line)
    if m:
        cur = m.group(1)
    if cur in {"17", "18", "19", "20", "21", "22", "23", "24", "Addendum", "15"}:
        continue
    for hit in pat.findall(line):
        print(f"  L{n} [s{cur}] {hit!r}: {line.strip()[:150]}")
        break
