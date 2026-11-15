"""Auditor's own applier: parse CHANGES.md (Old/New, Anchor/Inserted blocks) and apply to rev4; compare to rev5.
Usage: python3 -I apply_changes.py CHANGES.md rev4.md rev5.md out.md"""
import re, sys, difflib
ch, r4, r5, out = sys.argv[1:5]
T = open(ch, encoding="utf-8").read()
body = T.split("\n## Open for the lead\n")[0]
secs = re.split(r"\n### (C\d\d) — ", body)
changes = []
for i in range(1, len(secs), 2):
    cid, s = secs[i], secs[i + 1]
    mode = re.search(r"- \*\*Mode:\*\* (.+)\n", s).group(1)
    blocks = re.findall(r"```text\n(.*?)\n```\n", s, re.S)
    changes.append((cid, mode, blocks))
text = open(r4, encoding="utf-8").read()
target = open(r5, encoding="utf-8").read()
log = []
for cid, mode, blocks in changes:
    if len(blocks) != 2:
        log.append(f"{cid}: {len(blocks)} code blocks (parse issue)"); continue
    a, b = blocks
    n = text.count(a)
    if n != 1:
        log.append(f"{cid}: anchor count {n}"); continue
    if mode == "replace":
        text = text.replace(a, b)
    elif mode == "insert after":
        # CHANGES.md strips leading newlines of inserted text; choose the variant whose result is a substring
        # pattern found in the target (anchor+ins prefix), recording which was needed.
        cands = [b, "\n" + b, "\n\n" + b, " " + b]
        ok = [c for c in cands if (a + c) in target]
        if not ok:
            log.append(f"{cid}: insert not found in rev5 in any variant"); text = text.replace(a, a + b); continue
        c = ok[0]
        if c != b: log.append(f"{cid}: insert needed leading {c[:len(c)-len(b)]!r} (lost in CHANGES.md strip)")
        text = text.replace(a, a + c)
    elif mode == "insert before":
        cands = [b, b + "\n", b + "\n\n"]
        ok = [c for c in cands if (c + a) in target]
        c = ok[0] if ok else b
        if not ok: log.append(f"{cid}: insert-before not found")
        elif c != b: log.append(f"{cid}: insert-before needed trailing {c[len(b):]!r}")
        text = text.replace(a, c + a)
    else:
        log.append(f"{cid}: unknown mode {mode}")
open(out, "w", encoding="utf-8").write(text)
print(f"{len(changes)} changes parsed")
print("\n".join(log))
print("IDENTICAL" if text == target else "DIFFERENT")
if text != target:
    for l in difflib.unified_diff(text.splitlines(), target.splitlines(), "applied", "rev5", lineterm="", n=0):
        print(l[:300])
