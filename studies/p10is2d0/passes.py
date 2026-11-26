# ruff: noqa: E501
"""The task list of D0 (ADR-0035 sections 4, 5.2, 8), the charged-time ledger, the per-pass and per-cell records and the worker body.

A task is one reproduction pass (``G``), one cell's read statistics (``S``) or one scoring pass (``P``). Passes per cell: sixteen (nine on E_first, seven on E_second), 96 in all. Every pass is greedy decoding under
the ORACLE route (the example's own task), by ``studies.p10s2.evaluate.score_panel``, with an ``Arm`` whose ``prepare`` substitutes the condition's read. A record is written once, atomically, after the pass
completes; a worker skips a task whose record exists (section 8.3: a resume from completed records is the same run)."""

import json
import os
import time
from pathlib import Path
from typing import Any

import torch

from arborlm.io import atomic_write
from studies.p10is2.common import core
from studies.p10s2.evaluate import score_panel
from studies.p10s2.text import mean
from studies.p10s2.train import reads_of

from . import reads as R
from . import run, stats

REPLICATES = (0, 1, 2)
ORDERS = ("AB", "BA")
PANEL = {"A": "E_A", "B": "E_B"}
CAP_SECONDS = 8 * 3600.0
CHUNK = 100
WORKERS = 3

FIRST_PASSES = (("M1", "a"), ("append", "a"), ("append", "d1"), ("final", "a"), ("final", "b1"), ("final", "c"), ("final", "d1"), ("final", "e1"), ("final", "g1"))
SECOND_PASSES = (("final", "a"), ("final", "b2"), ("final", "c"), ("final", "d2"), ("final", "e2"), ("final", "g2"), ("final", "e1"))
GATE_PASSES = (("M1", "first"), ("append", "first"), ("final", "first"), ("final", "second"))
REGISTERED_ARM = {"M1": "M1", "append": "M-append@append", "final": "M-append"}


class CapReached(RuntimeError):
    pass


def cells() -> list[tuple[int, str]]:
    return [(r, o) for r in REPLICATES for o in ORDERS]


def panel_of(order: str, role: str) -> str:
    return PANEL[order[0] if role == "first" else order[1]]


def gate_tasks() -> list[dict[str, Any]]:
    return [{"id": f"G|{r}|{o}|{s}|{role}", "kind": "gate", "rep": r, "order": o, "store": s, "role": role} for r, o in cells() for s, role in GATE_PASSES]


def main_tasks() -> list[dict[str, Any]]:
    """Read statistics first (section 8.3), then the 96 passes cell by cell."""
    out = [{"id": f"S|{r}|{o}", "kind": "stats", "rep": r, "order": o} for r, o in cells()]
    for r, o in cells():
        for role, plist in (("first", FIRST_PASSES), ("second", SECOND_PASSES)):
            out += [{"id": f"P|{r}|{o}|{s}|{c}|{role}", "kind": "pass", "rep": r, "order": o, "store": s, "cond": c, "role": role} for s, c in plist]
    return out


def record_path(out: Path, task_id: str) -> Path:
    sub = {"G": "gate_passes", "S": "stats", "P": "passes"}[task_id[0]]
    return out / sub / (task_id.replace("|", "__") + ".json")


class Ledger:
    """Worker-seconds: the wall time of each computing process, one file per process, rewritten atomically at every chunk. The charged total is the sum over all files (and the orchestrator's own)."""

    def __init__(self, out: Path, name: str) -> None:
        self.dir = out / "cost"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / f"ledger_{name}.json"
        self.t0 = time.monotonic()
        self.start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.note: dict[str, Any] = {}
        self._acc = 0.0  # seconds of earlier running spans (the orchestrator pauses its clock while it only waits for workers)
        self._since: float | None = self.t0

    def elapsed(self) -> float:
        return self._acc + (0.0 if self._since is None else time.monotonic() - self._since)

    def pause(self) -> None:
        if self._since is not None:
            self._acc += time.monotonic() - self._since
            self._since = None
            self.tick()

    def unpause(self) -> None:
        if self._since is None:
            self._since = time.monotonic()

    def tick(self) -> None:
        atomic_write(self.path, (json.dumps({"pid": os.getpid(), "start_utc": self.start, "elapsed_seconds": self.elapsed(), **self.note}, sort_keys=True) + "\n").encode())

    def total(self) -> float:
        return charged_total(self.dir)


def charged_total(cost_dir: Path) -> float:
    tot = 0.0
    for f in cost_dir.glob("ledger_*.json"):
        try:
            tot += float(json.loads(f.read_text())["elapsed_seconds"])
        except (OSError, ValueError, KeyError):
            continue
    return tot


def make_arm(arms: dict[str, Any], store: str, cond: str) -> Any:
    """The unmodified registered arm for the M1 pass and for the reproduction passes; otherwise a ``DiagArm`` with the condition's read."""
    base = arms[store]
    if store == "M1" or cond in ("first", "second"):
        return base
    return R.DiagArm(base.store, base.layer, base.codes, cond)


@torch.no_grad()
def run_panel(world: Any, arm: Any, panel_name: str, ledger: Ledger, cap: float) -> dict[str, Any]:
    panel = world.ctx.panels[panel_name]
    n = len(panel.examples)
    items: list[float] = []
    exact: list[bool] = []
    seqs: list[list[int]] = []
    for lo in range(0, n, CHUNK):
        ledger.tick()
        if ledger.total() > cap:
            raise CapReached(f"charged {ledger.total():.0f} s above the cap of {cap:.0f} s")
        sc = score_panel(world.ctx, arm, panel, indices=range(lo, min(n, lo + CHUNK)))
        items += sc.items
        exact += sc.exact
        seqs += sc.sequences
    return {"items": items, "exact": exact, "sequences": seqs, "mean": mean(items), "n": n}


def panel_reads(world: Any, panel_name: str, codes: Any) -> tuple[torch.Tensor, torch.Tensor]:
    """The queries of every read of every item of a panel under the oracle route, in order, and a mask that is True for marker reads."""
    q: list[torch.Tensor] = []
    marker: list[bool] = []
    for ex in world.ctx.panels[panel_name].examples:
        for _pos, task, j in reads_of(ex, [ex.task], world.ctx.marker_index):
            q.append(codes.get(task, j))
            marker.append(j == world.ctx.marker_index)
    return torch.stack(q), torch.tensor(marker)


def cell_statistics(world: Any, arms: dict[str, Any], rep: int, order: str) -> dict[str, Any]:
    """Section 5.2: E_first at the append point and at the final store (protected stage 1), E_second at the final store (protected stage 2); word reads and marker reads separately."""
    out: dict[str, Any] = {"rep": rep, "order": order}
    for store, role, p in (("append", "first", 0), ("final", "first", 0), ("final", "second", 1)):
        panel = panel_of(order, role)
        arm = arms[store]
        q, is_marker = panel_reads(world, panel, arm.codes)
        parts: dict[str, list[torch.Tensor]] = {}
        for lo in range(0, q.shape[0], 1500):
            for k, v in stats.per_read_quantities(arm.store, q[lo : lo + 1500], p).items():
                parts.setdefault(k, []).append(v)
        qty = {k: torch.cat(v) for k, v in parts.items()}
        out[f"{store}|{role}"] = {
            "panel": panel, "protected_stage": p + 1, "reads": int(q.shape[0]), "marker_reads": int(is_marker.sum()), "gates": [float(g) for g in arm.store.gates],
            "words": stats.summarise_all(qty, ~is_marker), "markers": stats.summarise_all(qty, is_marker),
        }  # fmt: skip
    return out


def distinct_queries(world: Any, order: str, codes: Any) -> torch.Tensor:
    """Every distinct query (task, j) that either panel's items read under the oracle route: what the identity gates are checked on."""
    seen: dict[tuple[str, int], torch.Tensor] = {}
    for name in ("E_A", "E_B"):
        for ex in world.ctx.panels[name].examples:
            for _pos, task, j in reads_of(ex, [ex.task], world.ctx.marker_index):
                seen.setdefault((task, j), codes.get(task, j))
    return torch.stack([seen[k] for k in sorted(seen)])


def worker_main(out: Path, stage: str, index: int, count: int, repo: Path, cap: float = CAP_SECONDS) -> int:
    """One worker process: build the world once, take every ``count``-th task of the stage's list that has no record yet. Exit 0 if its share is done, 9 at the cap."""
    from .world import PART_T_RUN, build_world

    ledger = Ledger(out, f"{stage}_w{index}_{os.getpid()}")
    ledger.note = {"stage": stage, "worker": index}
    ledger.tick()
    tasks = gate_tasks() if stage == "gate" else main_tasks()
    todo = [t for i, t in enumerate(tasks) if i % count == index and not record_path(out, t["id"]).is_file()]
    if not todo:
        return 0
    world, _cfg = build_world(repo)
    ledger.note["world_build_seconds"] = ledger.elapsed()
    ledger.tick()
    cache: dict[tuple[int, str], dict[str, Any]] = {}
    for t in todo:
        key = (t["rep"], t["order"])
        if key not in cache:
            cache.clear()
            cache[key] = run.load_cell(world, t["rep"], t["order"], PART_T_RUN / "snapshots")
        if not execute_task(world, cache[key], t, out, ledger, cap, index):
            return 9
    return 0


def execute_task(world: Any, arms: dict[str, Any], t: dict[str, Any], out: Path, ledger: Ledger, cap: float, worker: int = 0) -> bool:
    """Run one task and write its record once, atomically. False if the cap stopped it (nothing is written for the task)."""
    t0 = time.monotonic()
    try:
        if t["kind"] == "stats":
            rec = cell_statistics(world, arms, t["rep"], t["order"])
        else:
            role = t["role"]
            arm = make_arm(arms, t["store"], t.get("cond", role))
            rec = {**run_panel(world, arm, panel_of(t["order"], role), ledger, cap), "store": t["store"], "cond": t.get("cond", "registered-read"), "role": role}
    except CapReached as e:
        atomic_write(out / f"cap_reached_{worker}.json", (json.dumps({"task": t["id"], "why": str(e)}) + "\n").encode())
        ledger.tick()
        return False
    rec.update({"id": t["id"], "oracle_line": core.ORACLE_LINE, "label": "POST-HOC EXPLORATORY DIAGNOSTIC OF AN OBSERVED RUN; NOT A REGISTERED LABEL", "task_seconds": time.monotonic() - t0, "worker": worker, "pid": os.getpid()})
    p = record_path(out, t["id"])
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(p, (json.dumps(rec, sort_keys=True) + "\n").encode())
    ledger.tick()
    return True


def reference_for(role: str) -> tuple[str, str]:
    """The reference pass of the share of items whose greedy output differs: M1 on E_first; ``a`` on E_second (final store)."""
    return ("M1", "a") if role == "first" else ("final", "a")

