"""Independent accounting check: apply CHANGES.md's Old/New and Inserted-after blocks
to ADR-0020 rev3 and compare with rev4. Written by the auditor; does not use build.py.
Usage: python3 -I check_changes.py <worktree>
"""
import re
import sys
import hashlib
from pathlib import Path

wt = Path(sys.argv[1])
rev3 = (wt / "docs/reviews/p10-design-2026-11-15/revisions/ADR-0020-rev3.md").read_text()
rev4 = (wt / "docs/decisions/ADR-0020-p10-s0-addressing-qualification.md").read_text()
changes = (wt / "docs/reviews/p10-design-2026-11-15/adr-0020-review/rev4-draft/CHANGES.md").read_text()

for name, t in (("rev3", rev3), ("rev4", rev4), ("CHANGES", changes)):
    print(name, hashlib.sha256(t.encode()).hexdigest()[:8], len(t.splitlines()), "lines")

body = changes.split("## Every changed passage", 1)[1].split("## Open for the lead", 1)[0]
sections = re.split(r"^### (C\d\d) — (.*)$", body, flags=re.M)[1:]


def quote(block: str) -> str:
    """Join a run of '> ' lines (first quote block) into text."""
    lines = []
    started = False
    for ln in block.splitlines():
        if ln.startswith(">"):
            started = True
            s = ln[1:]
            if s.startswith(" "):
                s = s[1:]
            lines.append(s)
        elif started:
            break
    return "\n".join(lines)


ops = []
for i in range(0, len(sections), 3):
    cid, title, text = sections[i], sections[i + 1], sections[i + 2]
    if "**Old:**" in text:
        old = quote(text.split("**Old:**", 1)[1])
        new = quote(text.split("**New:**", 1)[1])
        ops.append((cid, "replace", old, new))
    elif "**Inserted after this passage" in text:
        anchor = quote(text.split("**Inserted after this passage", 1)[1].split("\n", 1)[1])
        new = quote(text.split("**New text:**", 1)[1])
        ops.append((cid, "insert", anchor, new))
    else:
        ops.append((cid, "unknown", "", ""))

doc = rev3
for cid, kind, a, b in ops:
    n = doc.count(a)
    if n != 1:
        print(f"{cid}: anchor occurs {n} times ({kind})")
        continue
    if kind == "replace":
        doc = doc.replace(a, b)
    else:
        # inserted text: if it starts with a space it continues the line, else new paragraph(s)
        if b.startswith(" "):
            doc = doc.replace(a, a + b)
        else:
            # try both: same line, new line, blank line
            doc = doc.replace(a, a + "\n" + b) if (a + "\n" + b) in rev4 else (
                doc.replace(a, a + "\n\n" + b) if (a + "\n\n" + b) in rev4 else doc.replace(a, a + "\n" + b))
print(len(ops), "change entries parsed:", [o[0] for o in ops if o[1] != "unknown"][-1])

if doc == rev4:
    print("RESULT: rev3 + CHANGES == rev4 (byte identical)")
else:
    import difflib
    d = list(difflib.unified_diff(doc.splitlines(), rev4.splitlines(), "rev3+CHANGES", "rev4", n=0, lineterm=""))
    print("RESULT: differs;", len(d), "diff lines")
    print("\n".join(d[:80]))
