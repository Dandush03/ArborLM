"""Check that the RECHECK.md section 4 wording changes appear verbatim in ADR-0016.

Usage: uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/check_w_applied.py
Auditor script; reads two Markdown files, writes nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RECHECK = ROOT / "docs/reviews/p8-supplement-spec-review-2026-11-14/RECHECK.md"
ADR = ROOT / "docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md"


def quoted_blocks(text: str) -> dict[str, list[str]]:
    """Return {"W1": [line, ...], ...}: the '> ' quoted lines under each **Wn** heading."""
    section = text.split("## 4. Required wording changes", 1)[1].split("## 5.", 1)[0]
    out: dict[str, list[str]] = {}
    current = ""
    for line in section.splitlines():
        m = re.match(r"\*\*(W\d) ", line)
        if m:
            current = m.group(1)
            out[current] = []
        elif line.startswith("> ") and current:
            out[current].append(line[2:])
    return out


def main() -> None:
    adr = ADR.read_text(encoding="utf-8")
    adr_lines = adr.splitlines()
    blocks = quoted_blocks(RECHECK.read_text(encoding="utf-8"))
    for name, lines in blocks.items():
        for line in lines:
            body = line
            if name in ("W4", "W8"):
                # Fragments appended to / substituted inside an existing sentence.
                present = body in adr
            elif name in ("W6", "W7"):
                # List items nested under gate 4 / the numbered list may be indented.
                present = body in [x.strip() for x in adr_lines]
            elif name == "W9":
                # W9 prescribes edits described by '→' / 'replace' text; check targets.
                if body.startswith("- Line 3 → "):
                    target = body.split("→ ", 1)[1].strip("`")
                    present = target in adr_lines
                elif body.startswith("- Line 5"):
                    target = body.split(' with "', 1)[1].rsplit('"', 1)[0]
                    present = target in adr
                else:
                    present = "### 9.1" in adr and "W1–W9" in adr
            else:
                present = body in adr_lines
            print(f"{name}: {'VERBATIM' if present else 'NOT FOUND'}: {body[:90]}")


if __name__ == "__main__":
    main()
