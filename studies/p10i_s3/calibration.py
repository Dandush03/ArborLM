# ruff: noqa: E501
"""P10IS3 rate search, edge rule, convergence tags and the sealed calibration (ADR-0026 sections 5.1 to 5.3, 16 rulings 5 and 18). Pure functions, no torch.

``curves[rate][cell][duration]`` is the calibration-panel NLL of a run at ``rate`` on calibration cell ``cell`` at ``duration`` updates, or None when the run had a non-finite event through that duration or a
non-finite NLL there (ruling 5; K1: a diverging rate is a failed cell of that rate and is handled here, never an item error).

The public file carries the whitelist of section 5.3 and nothing else; the sealed file carries every loss. ``check_public_against_sealed`` prints only agree / disagree and the names of the disagreeing fields.
"""

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import core, labels
from .core import EngineeringStop

Curves = Mapping[float, Mapping[int, Mapping[int, float | None]]]
ARM_REGIMES = [(a, g) for g in core.REGIMES for a in core.REGIME_ARMS[g]]


def _finite_rates(curves: Curves, duration: int) -> list[float]:
    return sorted(r for r, cells in curves.items() if cells and all(v.get(duration) is not None and math.isfinite(float(v[duration])) for v in cells.values()))  # type: ignore[arg-type]


def _means(curves: Curves, duration: int) -> dict[float, float]:
    return {r: sum(float(v[duration]) for v in curves[r].values()) / len(curves[r]) for r in _finite_rates(curves, duration)}  # type: ignore[arg-type]


def selection(curves: Curves, duration: int, tol: float) -> dict[str, Any]:
    """Section 5.1: m = the lowest mean among the rates finite in all calibration cells; selected = the smallest rate whose mean is within ``tol`` of m (inclusive); minimiser = the rate attaining m (exact tie: the smaller)."""
    means = _means(curves, duration)
    if not means:
        raise EngineeringStop(f"ENGINEERING STOP — no rate is finite in all calibration cells at {duration} updates; no rate can be chosen (before Decision 2)")
    m = min(means.values())
    minimiser = min(r for r, v in means.items() if v == m)
    selected = min(r for r, v in means.items() if v - m <= tol)
    run = sorted(curves)
    edge = "low" if minimiser == run[0] else "high" if minimiser == run[-1] else None
    return {"m": m, "minimiser": minimiser, "selected": selected, "edge": edge}


def extension_needed(curves: Curves, durations: Sequence[int], base_grid: Sequence[float], up: Sequence[float], down: Sequence[float], tol: float, max_per_side: int) -> dict[str, float | None]:
    """The next rate to run on each side, if at some duration the minimiser is the lowest or highest rate run and fewer than ``max_per_side`` steps were added on that side. The edge is read from the minimiser, not from the tie-selected rate (C4)."""
    run = sorted(curves)
    n_up = sum(1 for r in run if r > max(base_grid))
    n_down = sum(1 for r in run if r < min(base_grid))
    edges = {selection(curves, d, tol)["edge"] for d in durations}
    nxt_up = up[n_up] if "high" in edges and n_up < max_per_side and n_up < len(up) else None
    nxt_down = down[n_down] if "low" in edges and n_down < max_per_side and n_down < len(down) else None
    return {"up": nxt_up, "down": nxt_down}


def rate_table(curves_by: Mapping[tuple[str, str], Curves], durations: Sequence[int], u_star: int, tol: float) -> dict[str, Any]:
    """The rate table (arm-regimes x durations) and the RATE-AT-EDGE flags for U* (the minimiser for U* is still the lowest or highest rate run after the extensions)."""
    rates: dict[str, dict[str, float]] = {}
    edge: dict[str, bool] = {}
    for (arm, regime), curves in curves_by.items():
        key = f"{arm}|{regime}"
        sel = {d: selection(curves, d, tol) for d in durations}
        rates[key] = {str(d): sel[d]["selected"] for d in durations}
        edge[key] = sel[u_star]["edge"] is not None
    return {"rates": rates, "edge": edge}


def means_at_selected(curves_by: Mapping[tuple[str, str], Curves], rt: Mapping[str, Any], durations: Sequence[int], u_star: int) -> dict[tuple[str, str], dict[int, float | None]]:
    """M(arm, regime, c): the mean calibration NLL at c of the runs at the rate selected for U*."""
    out: dict[tuple[str, str], dict[int, float | None]] = {}
    for (arm, regime), curves in curves_by.items():
        r = float(rt["rates"][f"{arm}|{regime}"][str(u_star)])
        cells = curves[r]
        out[(arm, regime)] = {d: (None if any(v.get(d) is None for v in cells.values()) else sum(float(v[d]) for v in cells.values()) / len(cells)) for d in durations}  # type: ignore[arg-type]
    return out


def tags(curves_by: Mapping[tuple[str, str], Curves], rt: Mapping[str, Any], durations: Sequence[int], u_star: int, eps: float, margin: float) -> dict[str, Any]:
    m = means_at_selected(curves_by, rt, durations, u_star)
    out: dict[str, Any] = {}
    for (arm, regime), curve in m.items():
        failed = any(v is None for v in curve.values())
        conv = labels.convergence_tag(curve.get(8192), curve.get(u_star), eps, failed=failed)
        entry: dict[str, Any] = {"delta": conv["delta"], "tag": conv["tag"]}
        if regime in (core.REP, core.REPU):
            entry["past_best"] = labels.past_best(curve, u_star, margin, failed=failed)["tag"]
        out[f"{arm}|{regime}"] = entry
    return out


def public_summary(curves_by: Mapping[tuple[str, str], Curves], cfg: Mapping[str, Any], *, gates: Mapping[str, Any], timing: Mapping[str, Any], storage: Mapping[str, Any], sealed_sha256: str) -> dict[str, Any]:
    """``rehearsal_public.json``: the whitelist of section 5.3 and nothing else. No loss value."""
    durations = [int(x) for x in cfg["duration"]["checkpoints"]]
    u = int(cfg["duration"]["u_star"])
    rt = rate_table(curves_by, durations, u, float(cfg["rates"]["tie_tolerance"]))
    return {**core.envelope("rehearsal_public"), "rate_table": rt, "convergence": tags(curves_by, rt, durations, u, float(cfg["duration"]["epsilon"]), float(cfg["duration"]["past_best_margin"])), "gates": dict(gates), "timing": dict(timing), "storage": dict(storage), "sealed_sha256": sealed_sha256, "whitelist_note": "no loss value is in this file (section 5.3)"}  # fmt: skip


# --- the sealed archive ------------------------------------------------------------------------------------------------
def sealed_bytes(curves_by: Mapping[tuple[str, str], Curves], extra: Mapping[str, Any]) -> bytes:
    """One canonical JSON archive: every per-run loss curve and every calibration statistic (``extra``)."""
    body = {"curves": {f"{a}|{g}": {core.rate_label(r): {str(c): {str(d): v for d, v in cells[c].items()} for c in cells} for r, cells in cs.items()} for (a, g), cs in curves_by.items()}, "extra": core.jsonable(dict(extra))}
    return json.dumps(core.jsonable(body), sort_keys=True, separators=(",", ":")).encode()


def require_outside_repo(path: Path, repo: Path, *, allow_inside_repo: bool = False, forbidden_roots: Sequence[str] | None = None) -> None:
    """The sealed archive and the sealed item records (about 1.4-2.6 GB of R1 snapshots) are refused (N2): inside this repository; anywhere under a forbidden root (the main checkout and so every worktree of it; config
    ``[seal]``); inside ANY git working tree (the nearest existing parent answers ``git rev-parse --show-toplevel``). Symlinks are resolved first. The synthetic rehearsal's test device may sit inside."""
    import subprocess

    if allow_inside_repo:
        return
    p = path.resolve()
    roots = [Path(r).resolve() for r in (forbidden_roots if forbidden_roots is not None else core.load_config()["seal"]["forbidden_roots"])]
    for root in [repo.resolve(), *roots]:
        if p == root or root in p.parents:
            raise core.EngineeringStop(f"refused: the sealed folder {p} is inside {root}: it must be outside the repository, outside the lead's checkout and worktrees, and outside every git working tree (section 5.3)")
    probe = p
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    top = subprocess.run(["git", "-C", str(probe), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)  # noqa: S603, S607
    if top.returncode == 0:
        raise core.EngineeringStop(f"refused: the sealed folder {p} is inside the git working tree {top.stdout.strip()} (section 5.3)")


def write_sealed(path: Path, repo: Path, data: bytes, *, allow_inside_repo: bool = False) -> str:
    """Written once, outside the repository (the seal works by procedure; the path is logged in NOTES.md by the lead)."""
    require_outside_repo(path, repo, allow_inside_repo=allow_inside_repo)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def curves_from_sealed(data: bytes) -> dict[tuple[str, str], dict[float, dict[int, dict[int, float | None]]]]:
    body = json.loads(data)
    out: dict[tuple[str, str], dict[float, dict[int, dict[int, float | None]]]] = {}
    for key, rates in body["curves"].items():
        a, g = key.split("|")
        out[(a, g)] = {float(r): {int(c): {int(d): v for d, v in ds.items()} for c, ds in cells.items()} for r, cells in rates.items()}
    return out


def check_public_against_sealed(public: Mapping[str, Any], sealed: bytes, cfg: Mapping[str, Any]) -> dict[str, Any]:
    """The auditor's role in code: recompute the rate table, the tags and the sealed hash from the sealed archive and report only ``agree`` or ``disagree`` and the NAMES of disagreeing fields."""
    curves = curves_from_sealed(sealed)
    mine = public_summary(curves, cfg, gates=public.get("gates", {}), timing=public.get("timing", {}), storage=public.get("storage", {}), sealed_sha256=hashlib.sha256(sealed).hexdigest())
    bad = [k for k in ("rate_table", "convergence", "sealed_sha256") if mine[k] != public.get(k)]
    return {"result": "agree" if not bad else "disagree", "fields": bad}
