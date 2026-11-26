# ruff: noqa: E501
"""P10IS1 sealing of the calibration (ADR-0024 sections 7, 14; the lead's instruction): the calibration's item records (every accuracy on the calibration draws, the readouts, the walk, the U_P detail) are written into a
SEALED directory chosen with an explicit ``--sealed-dir``. The directory is refused when, after resolving symlinks, it lies inside any git working tree or anywhere under the ArborLM checkout directory
(``/Users/daniellaloush/dandush03/ArborLM`` and the repository root of this code). What the lead may see is the public record, built from a WHITELIST (``PUBLIC_KEYS``, also written as a public file): the selected rates,
U_P of each row, U0 of each ladder cell, the registered outcomes and flags (T-OQ PREDICTED NOT FULL, 256 NOT MEASURED, RATE AT EDGE, EDGE BY TIE-WALK, returns to the human lead), H8's annotations and the order of the steps.
No accuracy, readout, walk value or minimum a_use is public. ``assert_public`` refuses a record with a key outside the whitelist."""

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import core

FORBIDDEN_PREFIXES = (Path("/Users/daniellaloush/dandush03/ArborLM"),)
PUBLIC_KEYS = ("rates", "row_u_p", "u0", "sat256", "returns_to_lead", "edge_notes", "order", "complete", "ladder", "h8_annotations", "h8_undertrained_cells", "h8_calibrated_cells", "u_p_returns", "notes")
PUBLIC_LADDER_KEYS = ("cell", "action", "u0", "runs", "note", "returns_to_lead", "toq_predicted_not_full", "foq_length", "toq_length", "ceiling", "options")
SEALED_KEYS_FORBIDDEN_IN_PUBLIC = ("selections", "u_p_detail", "min_a_use", "readout_a_use", "walk", "results")


class SealedRefused(core.StageRefused):
    """The sealed directory is inside a git working tree or under the ArborLM checkout (or does not resolve)."""


def check_sealed_dir(path: Path, extra_forbidden: tuple[Path, ...] = ()) -> Path:
    """Resolve symlinks; refuse a directory under a forbidden prefix (the ArborLM checkout, this repository's root) or inside any git working tree (the nearest existing ancestor is asked). Returns the resolved path."""
    real = path.expanduser().resolve()
    for prefix in (*FORBIDDEN_PREFIXES, core.repo_root(), *extra_forbidden):
        pr = prefix.resolve()
        if real == pr or pr in real.parents:
            raise SealedRefused(f"refused: the sealed directory {real} is under {pr}")
    anc = real
    while not anc.exists():
        anc = anc.parent
    out = subprocess.run(["git", "-C", str(anc), "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True, check=False)  # noqa: S603, S607
    if out.returncode == 0 and out.stdout.strip() == "true":
        raise SealedRefused(f"refused: the sealed directory {real} is inside a git working tree")
    return real


def public_record(full: Mapping[str, Any]) -> dict[str, Any]:
    """The public calibration record, built from the whitelist only (``full`` is ``calibrate.to_record``)."""
    ladder = {n: {k: v for k, v in d.items() if k in PUBLIC_LADDER_KEYS} for n, d in full["ladder"].items()}
    h8 = full.get("h8", {})
    rec = {
        **core.envelope("calibration"), "rates": dict(full["rates"]), "row_u_p": dict(full["row_u_p"]), "u0": dict(full["u0"]), "sat256": full["sat256"], "returns_to_lead": list(full["returns_to_lead"]), "edge_notes": list(full["edge_notes"]),
        "order": list(full["order"]), "complete": full["complete"], "ladder": ladder, "h8_annotations": dict(h8.get("annotations", {})), "h8_undertrained_cells": list(h8.get("undertrained_cells", [])), "h8_calibrated_cells": list(h8.get("calibrated_cells", [])),
        "u_p_returns": {k: v.get("reason") for k, v in full.get("u_p_detail", {}).items() if v.get("u_p") is None}, "notes": "calibration accuracies are sealed; this record holds only what the ADR's whitelist allows",
        "h8": {"undertrained_cells": list(h8.get("undertrained_cells", [])), "calibrated_cells": list(h8.get("calibrated_cells", []))},
    }  # fmt: skip
    assert_public(rec)
    return rec


def assert_public(rec: Mapping[str, Any]) -> None:
    allowed = set(PUBLIC_KEYS) | {"kind", "schema", "study", "h8"}
    extra = set(rec) - allowed
    if extra:
        raise ValueError(f"not public: keys {sorted(extra)} are outside the whitelist")
    text = json.dumps(rec)
    for k in SEALED_KEYS_FORBIDDEN_IN_PUBLIC:
        if f'"{k}"' in text:
            raise ValueError(f"not public: the key {k!r} is sealed")


def write_whitelist(path: Path) -> None:
    """The public whitelist file: what may leave the sealed directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"public_keys": list(PUBLIC_KEYS), "public_ladder_keys": list(PUBLIC_LADDER_KEYS), "sealed": ["every accuracy, readout, walk value, minimum a_use, selection table and U_P detail on the calibration draws"], "rule": "ADR-0024 sections 7 and 14; the lead sees the whitelist only"}, indent=2, sort_keys=True) + "\n")
