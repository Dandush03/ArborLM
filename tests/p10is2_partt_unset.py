"""Test helper (P10-I-S2 Part T).

The Part T tests build synthetic repositories from a copy of ``configs/p10is2_partt.toml`` and then
text-replace the UNSET values (``study_budget_hours = 0.0``, ``calibration_hours = 0.0``,
``remote_url = ""``, ``remote_branch = ""``). Ruling 41 and the pre-calibration setup set those
values in the real config, so each synthetic copy first gets them back to unset here, derived from
the current config (not a frozen copy); each test then applies its own replacements as before.
Only these four values are touched; comments are kept.
"""

from __future__ import annotations

import re
from pathlib import Path

_UNSET = (
    (r"(?m)^(study_budget_hours = )[0-9.]+", r"\g<1>0.0"),
    (r"(?m)^(calibration_hours = )[0-9.]+", r"\g<1>0.0"),
    (r'(?m)^(remote_url = )".*"', r'\g<1>""'),
    (r'(?m)^(remote_branch = )".*"', r'\g<1>""'),
)


def unset_text(text: str) -> str:
    for pattern, repl in _UNSET:
        text = re.sub(pattern, repl, text)
    return text


def unset_config(repo: Path, rel: str = "configs/p10is2_partt.toml") -> None:
    """Rewrite the synthetic repository's Part T config with the four values unset."""
    p = repo / rel
    p.write_text(unset_text(p.read_text()))
