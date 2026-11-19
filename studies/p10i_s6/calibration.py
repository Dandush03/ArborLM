# ruff: noqa: E501
"""P10IS6 rate search, interior rule, calibration convergence states and the sealed archive (ADR-0031 section 8; ADR-0026 section 5.1 unchanged). Pure functions, no torch.

``curves[rate][cell][updates]`` is the calibration-panel NLL of the run at ``rate`` on calibration cell ``cell`` at ``updates`` updates, or None when the run had a non-finite event through that count or a non-finite
NLL there (ruling 5). Frozen import (section 15): ``studies.p10i_s3.calibration.selection`` (it reads no P10-I-S3 value); everything else is this study's own.

The public file carries the whitelist of section 8 and nothing else (no loss, no delta, no convergence state); the sealed archive carries every curve and the calibration convergence states.
"""

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from studies.p10i_s3.calibration import require_outside_repo, selection  # frozen imports: both read no P10-I-S3 value (require_outside_repo is given ``forbidden_roots`` explicitly)

from . import core, labels
from .core import EngineeringStop

Curves = Mapping[float, Mapping[int, Mapping[int, float | None]]]
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def durations_of(cfg: Mapping[str, Any], k_max: int) -> list[int]:
    return [core.rung_updates(cfg, k) for k in core.rung_range(k_max)]


def arm_selection(curves: Curves, durations: Sequence[int], tol: float) -> dict[int, dict[str, Any]]:
    return {d: selection(curves, d, tol) for d in durations}


def extension_decision(curves: Curves, durations: Sequence[int], cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Section 8 and ruling G14, per arm and across all durations -1..k_max: the next rate to run on each side if at some duration the minimiser is the lowest or highest rate run; ``stop`` names ENGINEERING STOP — CALIBRATION NOT INTERIOR
    if an edge persists with no extension left (at most four steps down and two up per arm). A rate whose neighbour on a side is non-finite in a calibration cell is not at an edge on that side: the lowest and highest rates RUN are
    compared, and a rate that diverged is a rate run."""
    r = cfg["rates"]
    grid = [float(x) for x in r["grid"]]
    up, down = [float(x) for x in r["extension_up"]], [float(x) for x in r["extension_down"]]
    run = sorted(curves)
    n_up = sum(1 for x in run if x > max(grid))
    n_down = sum(1 for x in run if x < min(grid))
    edges = {s["edge"] for s in arm_selection(curves, durations, float(r["tie_tolerance"])).values()}
    out: dict[str, Any] = {"up": None, "down": None, "stop": None}
    if "high" in edges:
        if n_up < int(r["max_extensions_up"]) and n_up < len(up):
            out["up"] = up[n_up]
        else:
            out["stop"] = "ENGINEERING STOP — CALIBRATION NOT INTERIOR: the minimiser is the highest rate run and the grid cannot be extended further (the grid is amended with a recorded approval and the calibration re-run on the same calibration seeds)"
    if "low" in edges:
        if n_down < int(r["max_extensions_down"]) and n_down < len(down):
            out["down"] = down[n_down]
        else:
            out["stop"] = "ENGINEERING STOP — CALIBRATION NOT INTERIOR: the minimiser is the lowest rate run and the grid cannot be extended further (the grid is amended with a recorded approval and the calibration re-run on the same calibration seeds)"
    return out


def rate_table(curves_by_arm: Mapping[str, Curves], cfg: Mapping[str, Any], k_max: int) -> dict[str, Any]:
    """r(arm, k) for k = -1..k_max; ``interior[arm][k]`` is True if the minimiser is neither the lowest nor the highest rate run (always True in a table that reached the freeze). Raises ``EngineeringStop`` if the edge persists."""
    tol = float(cfg["rates"]["tie_tolerance"])
    rates: dict[str, dict[str, float]] = {}
    interior: dict[str, dict[str, bool]] = {}
    for arm in core.ARMS:
        curves = curves_by_arm[arm]
        rates[arm], interior[arm] = {}, {}
        for k in core.rung_range(k_max):
            sel = selection(curves, core.rung_updates(cfg, k), tol)
            rates[arm][str(k)] = float(sel["selected"])
            interior[arm][str(k)] = sel["edge"] is None
    return {"rates": rates, "interior": interior}


def calibration_states(curves_by_arm: Mapping[str, Curves], rt: Mapping[str, Any], cfg: Mapping[str, Any], k_max: int) -> dict[str, Any]:
    """F2: delta, deltarun and the convergence state of each arm on the calibration cells at the selected rates, 3-cell means. SEALED ONLY: no decision before the registered run uses them."""
    eps = float(cfg["convergence"]["epsilon"])
    out: dict[str, Any] = {}
    for arm in core.ARMS:
        curves = curves_by_arm[arm]

        def m(rate: float, k: int, curves: Curves = curves) -> float | None:
            vals = [curves[rate][c].get(core.rung_updates(cfg, k)) for c in sorted(curves[rate])]
            return None if any(v is None for v in vals) else sum(float(v) for v in vals if v is not None) / len(vals)

        L = {k: m(float(rt["rates"][arm][str(k)]), k) for k in core.rung_range(k_max)}
        entry: dict[str, Any] = {"L": {str(k): v for k, v in L.items()}}
        for k in range(0, k_max + 1):
            d = None if L[k - 1] is None or L[k] is None else float(L[k - 1]) - float(L[k])  # type: ignore[arg-type]
            rate = float(rt["rates"][arm][str(k)])
            prev, cur = m(rate, k - 1), m(rate, k)
            dr = None if prev is None or cur is None else float(prev) - float(cur)
            entry[str(k)] = {"delta": d, "delta_run": dr, "state": labels.convergence_state(d, dr, eps)}
        out[arm] = entry
    return out


# --- the public whitelist guard (requirement 5) -------------------------------------------------------------------------------------------------
FORBIDDEN = ("nll", "loss", "delta", "converg", "gain", "persist", "bpb", "nats", "held", "lead")


def public_guard(obj: Any, *, path: str = "", opaque: bool = False) -> list[str]:
    """Forbidden measure names match as plain substrings (the old rule) in every key and every string value, except an exact opaque 64-hex digest, and except everything inside a mapping called ``hashes`` (file names to digests)."""
    bad: list[str] = []
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            ks = str(k)
            if not opaque and not HEX64.match(ks) and any(w in ks.lower() for w in FORBIDDEN):
                bad.append(f"{path}{ks}")
            bad += public_guard(v, path=f"{path}{ks}.", opaque=opaque or ks == "hashes")
    elif isinstance(obj, list | tuple):
        for i, v in enumerate(obj):
            bad += public_guard(v, path=f"{path}{i}.", opaque=opaque)
    elif isinstance(obj, str) and not opaque and not HEX64.match(obj) and any(w in obj.lower() for w in FORBIDDEN):
        bad.append(f"{path}='{obj[:40]}'")
    return bad


def public_summary(curves_by_arm: Mapping[str, Curves], cfg: Mapping[str, Any], k_max: int, *, gates: Mapping[str, Any], seconds: Mapping[str, Any], storage: Mapping[str, Any], sealed_sha256: str, rule_hashes: Mapping[str, Any]) -> dict[str, Any]:
    """``rehearsal_public.json`` (R1's part): the rate table, the interior flags, gate results, seconds, storage and the sealed archive's SHA-256. No loss value, no delta, no convergence state."""
    rt = rate_table(curves_by_arm, cfg, k_max)
    rec = {**core.envelope("rehearsal_public"), "rate_table": rt, "gates": dict(gates), "seconds": dict(seconds), "storage": dict(storage), "sealed_sha256": sealed_sha256, "rule_hashes": dict(rule_hashes), "k_max": k_max, "whitelist_note": "no value of any measured quantity is in this file (section 8)"}
    problems = public_guard({k: v for k, v in rec.items() if k not in ("whitelist_note",)})
    if problems:
        raise EngineeringStop(f"ENGINEERING STOP — the public calibration file would carry forbidden names: {problems[:5]}")
    return rec


# --- the sealed archive -------------------------------------------------------------------------------------------------------------------------
def sealed_bytes(curves_by_arm: Mapping[str, Curves], states: Mapping[str, Any], extra: Mapping[str, Any]) -> bytes:
    body = {"curves": {arm: {core.rate_label(r): {str(c): {str(d): v for d, v in cells[c].items()} for c in cells} for r, cells in cs.items()} for arm, cs in curves_by_arm.items()}, "states": core.jsonable(dict(states)), "extra": core.jsonable(dict(extra))}
    return json.dumps(core.jsonable(body), sort_keys=True, separators=(",", ":")).encode()


def curves_from_sealed(data: bytes) -> dict[str, dict[float, dict[int, dict[int, float | None]]]]:
    body = json.loads(data)
    return {arm: {float(r): {int(c): {int(d): v for d, v in ds.items()} for c, ds in cells.items()} for r, cells in rates.items()} for arm, rates in body["curves"].items()}


def write_sealed(path: Path, repo: Path, data: bytes, cfg: Mapping[str, Any], *, allow_inside_repo: bool = False) -> str:
    """Written once, outside every git working tree and outside the roots the config forbids (symlinks resolved). The explicit ``forbidden_roots`` argument is this study's own (section 15)."""
    require_outside_repo(path, repo, allow_inside_repo=allow_inside_repo, forbidden_roots=[str(x) for x in cfg["seal"]["forbidden_roots"]])
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def check_public_against_sealed(public: Mapping[str, Any], sealed: bytes, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The auditor's role in code: recompute the rate table and the sealed hash from the sealed archive; report only ``agree`` or ``disagree`` and the NAMES of disagreeing fields."""
    curves = curves_from_sealed(sealed)
    k_max = int(public["k_max"])
    rt = rate_table(curves, cfg, k_max)
    bad = [k for k, ok in (("rate_table", rt == public.get("rate_table")), ("sealed_sha256", hashlib.sha256(sealed).hexdigest() == public.get("sealed_sha256"))) if not ok]
    return {"result": "agree" if not bad else "disagree", "fields": bad}


def finite(x: Any) -> bool:
    return isinstance(x, int | float) and math.isfinite(x)
