# ruff: noqa: E501
"""What differs between a Part T rehearsal and a registered run, and nothing else (ADR-0025 section 10; audit B1, B2).

A rehearsal runs through the SAME entry point (``partt_registered.sh <stage> <run-dir> - --rehearsal``), the same task runner, the same worker, the same stage bodies as a registered run. The documented overrides:

* ``--rehearsal``: the candidate plan (``freeze/partt_plan.json`` or ``--plan-file``), no freeze commit (``-``), no Decision 2; mode ``rehearsal``; one run directory of its own, claimed as ``rehearsal``.
* The world holds NO evaluation panel: ``rehearsal_bundle`` splits D_cal by identity group into four disjoint parts, three of which stand in for E_A, E_B and E_C (the fourth stays D_cal), empties E_open and replaces the
  evaluation panels' stored teacher outputs by those of the parts. Every scoring function therefore runs unchanged and scores D_cal only; a rehearsal can never read an evaluation item. Training is on the rehearsal draw (seed 252002) only.
* The plan-derived SUBSET (``subset_items``): replicate 0, one cell of each of the ten trained types at the plan's full U (order AB; E-table on capability A), one scoring task, one combined task, and the
  references; the cells a rehearsal did not train are read from the trained cell of the same arm (``AliasMap``: order BA from AB, E-table B from A), recorded, so every scoring path runs.
* ONE forced pause (a worker stops its cell after ``--pause-after-updates`` and exits ``74``; the same command resumes from the checkpoint) and ONE forced PAUSED — IDENTITY (the stage launched with a plan
  copy whose frozen hash is altered exits 75 and writes nothing; the real plan then runs).
"""

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Any

from studies.p10s2.combined import pair_list, pairs_digest
from studies.p10s2.worldio import DataBundle

from .common import core

SUBSET_REP = 0
SUBSET_ORDER = "AB"
FORCED_PAUSE_EXIT = 74


def tree_bytes(path: Any) -> int:
    """Bytes under a directory (the disk a stage writes is the growth of its run directory)."""
    import os

    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def stats_begin(run_dir: Any) -> dict[str, Any]:
    import os
    import time

    return {"t": time.monotonic(), "load": os.getloadavg(), "disk": tree_bytes(run_dir)}


def stats_end(begin: Mapping[str, Any], run_dir: Any) -> dict[str, Any]:
    """Peak resident set of this process, the MPS memory it holds, the disk its run directory grew by, and the one-minute load at its start and end (every one MEASURED, never a label)."""
    import os
    import resource
    import sys

    import torch

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    mps: dict[str, int | None] = {"current_allocated_bytes": None, "driver_allocated_bytes": None}
    try:
        if torch.backends.mps.is_available():
            mps = {"current_allocated_bytes": int(torch.mps.current_allocated_memory()), "driver_allocated_bytes": int(torch.mps.driver_allocated_memory())}
    except Exception:  # noqa: BLE001 - a missing MPS counter is recorded as missing, never guessed
        pass
    return {"peak_rss_bytes": int(rss if sys.platform == "darwin" else rss * 1024), "mps": mps, "disk_written_bytes": tree_bytes(run_dir) - int(begin["disk"]), "load_start": begin["load"][0], "load_end": os.getloadavg()[0]}


def split_by_group(items: Sequence[Any], parts: int) -> list[list[Any]]:
    """``parts`` disjoint lists of the items, split by identity group (all items of a group go together, groups dealt round-robin in id order); an item with no group (-1) is dealt on its own by position."""
    out: list[list[Any]] = [[] for _ in range(parts)]
    rank = {g: n for n, g in enumerate(sorted({int(i.group) for i in items if int(i.group) >= 0}))}
    for pos, it in enumerate(items):
        out[(rank[int(it.group)] if int(it.group) >= 0 else pos) % parts].append(it)
    return out


def rehearsal_bundle(b: DataBundle, cfg: Mapping[str, Any], q_check_keys: Sequence[str] = ()) -> DataBundle:
    """The bundle a rehearsal world is built from: D_cal is split by identity group into four disjoint parts; the first three are E_A, E_B and E_C of the rehearsal world and the fourth is D_cal; E_open is empty.
    Every scoring function and gate G1 therefore run unchanged on training-side items only; a rehearsal world holds no evaluation item. The control subsample is the first ``control_subsample`` items of E_A."""
    d_cal = list(b.panels["D_cal"])
    a, bb, c, rest = split_by_group(d_cal, 4)
    if min(len(a), len(bb), len(c), len(rest)) < 2:
        raise core.StageRefused(f"refused: D_cal ({len(d_cal)} items) is too small to split into four disjoint parts of at least two items: a rehearsal has nothing to score")
    forbidden = {i.key for n in ("E_A", "E_B", "E_C", "E_open", "Q_check") for i in b.panels.get(n, [])} | set(q_check_keys)
    hit = sorted(i.key for part in (a, bb, c, rest) for i in part if i.key in forbidden)
    if hit:  # ruling 16: no evaluation item and no Q_check item may be in any rehearsal
        raise core.StageRefused(f"refused: {len(hit)} rehearsal item(s) are evaluation or Q_check items (ruling 16): {hit[:3]}")
    sub = int(cfg["data"]["control_subsample"])
    panels = dict(b.panels)
    panels["E_A"], panels["E_B"], panels["E_C"], panels["D_cal"], panels["E_open"] = a, bb, c, rest, []
    abl = dict(b.ablation_keys)
    abl["E_A"], abl["E_B"] = [i.key for i in a[:sub]], [i.key for i in bb[:sub]]
    sigma = list(range(len(c)))
    extra = {**b.extra, "c1_pairing": {"sigma": sigma, "pairs_sha256": pairs_digest(pair_list(len(c), sigma))}, "rehearsal_panels": "E_A, E_B, E_C are disjoint parts of D_cal; D_cal is the fourth part"}
    outs = {cap: dict(v) for cap, v in b.teacher_outputs.items()}
    by_key = {cap: dict(zip((i.key for i in d_cal), outs[cap]["D_cal"], strict=True)) for cap in outs}
    for cap in outs:
        for name, part in (("E_A", a), ("E_B", bb), ("E_C", c), ("D_cal", rest)):
            outs[cap][name] = [by_key[cap][i.key] for i in part]
        outs[cap].pop("E_open", None)
    return dataclasses.replace(b, panels=panels, ablation_keys=abl, teacher_outputs=outs, extra=extra)


class AliasMap(dict[str, str]):
    """Snapshot labels the rehearsal reads from another trained cell: ``rN/<arm>/BA`` from ``AB`` (and the ``@append`` snapshot), ``rN/E-table/B`` from ``A``. A label that is not aliased is returned as it is."""

    def get(self, name: str, default: Any = None) -> Any:  # type: ignore[override]
        parts = name.split("/")
        if len(parts) == 3:
            tail = parts[2]
            base, sep, at = tail.partition("@")
            if parts[1] == "E-table" and base == "B":
                return "/".join([parts[0], parts[1], "A" + sep + at])
            if base == "BA":
                return "/".join([parts[0], parts[1], "AB" + sep + at])
        return name if default is None else default


def subset_items(stage: str, items: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The plan's items a rehearsal runs: replicate 0; training: order AB cells and the joint arms and E-table on capability A, i.e. one cell of each of the ten trained types. Every other stage keeps its replicate-0
    and reference items (one scoring task, one combined task) and the stages that run once."""
    out: list[Mapping[str, Any]] = []
    for i in items:
        rep = i.get("rep")
        if rep is None and "of" in i and "|r" in str(i["of"]):
            rep = int(str(i["of"]).rsplit("|r", 1)[1])
        if rep is not None and int(rep) != SUBSET_REP:
            continue
        if stage == "train":
            if i["arm"] == "E-table" and i.get("capability") != core.TASKS[0]:
                continue
            if i["order"] not in (SUBSET_ORDER, "-"):
                continue
        out.append(i)
    return out


def fill_registry(values: Mapping[str, float], replicates: Sequence[int] = (1, 2)) -> tuple[dict[str, float], list[str]]:
    """The rehearsal's analysis input: the registry of the one replicate it scored, with every key of replicate 0 copied to replicates 1 and 2 (listed). A rehearsal registry is plumbing for the analysis and the
    report and is never a result."""
    out = dict(values)
    filled: list[str] = []
    for k in sorted(values):
        arm, order, rep, read = k.split("|", 3)
        if rep != str(SUBSET_REP):
            continue
        for r in replicates:
            new = f"{arm}|{order}|{r}|{read}"
            if new not in out:
                out[new] = values[k]
                filled.append(new)
    return out, filled
