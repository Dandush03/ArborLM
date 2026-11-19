# ruff: noqa: E501
"""P10IS6 training with resume, the streams over the memory-mapped uint8 chunk table, and this study's read set (ADR-0031 sections 5, 6.4 rule 7, 11, 16 and 16a G2, G12, G15, G16).

Frozen imports from ``studies.p10i_s3.model`` (section 15; none reads a P10-I-S3 config value, seed, path or arm list): ``Ctl``, ``Collector``, ``S3Model``, ``build_model``, ``evaluate``, ``train_step``, ``make_optimizer``,
``seeded``, ``p_used_values``, ``neg_ref_values``, ``state_digest``, ``trainable_count``. This study's own: the pool stream, the resume-capable ``train_run``, ``evaluate_reads`` (M-FLAT: enabled, replay by the caller, disabled,
P_used x 4, X_mean, V_mean; D-ADAPT: enabled, replay, disabled, X_mean_dense), the NEG-REF check with V_mean and the planted positive.
Reads and evaluations run under ``torch.no_grad()`` (inside ``evaluate``). Self-check only.
"""

import copy
import hashlib
import math
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import torch
from torch import Tensor
from torch.optim import AdamW

from arborlm.io import canonical_json, read_json, sha256, write_json
from studies.p10i_s3.model import Collector, Ctl, S3Model, build_model, evaluate, make_optimizer, neg_ref_values, p_used_values, seeded, state_digest, train_step, trainable_count
from studies.p10i_s3.planted import plant, toy_panel

from . import core
from .core import DENSE, FLAT, FailedCell

__all__ = ["Collector", "Ctl", "S3Model", "build_model", "evaluate", "make_optimizer", "neg_ref_values", "p_used_values", "seeded", "state_digest", "trainable_count", "plant", "toy_panel"]

CHUNK = 65


# --- the chunk table and the streams (section 6.4 rules 5 and 7; G16) ---------------------------------------------------------------------
def map_table(path: Path, rows: int) -> Tensor:
    """The uint8 chunk table, memory-mapped (``torch.from_file``, private mapping): [rows * 65] uint8. The file's size must be exactly rows * 65."""
    if path.stat().st_size != rows * CHUNK:
        raise core.EngineeringStop(f"ENGINEERING STOP — {path} has {path.stat().st_size} bytes, expected {rows * CHUNK}")
    return torch.from_file(str(path), shared=False, size=rows * CHUNK, dtype=torch.uint8).reshape(rows, CHUNK)


class PoolStream:
    """One CPU generator seeded with the stream seed; ``randperm(pool size)`` over the pool in rank order; update u takes entries 8u to 8u + 7 (ruling 3); a batch is ``table[row].long()`` (G16). No chunk is used twice in a stream. The pool is the
    contiguous slice ``[start, start + size)`` of the table (this study's table holds the registered pool first and the calibration pool after it)."""

    def __init__(self, table: Tensor, start: int, size: int, seed: int, batch: int = 8) -> None:
        if start < 0 or start + size > table.shape[0]:
            raise ValueError("the pool lies outside the table")
        self.table, self.start, self.size, self.batch = table, start, size, batch
        self.perm = torch.randperm(size, generator=seeded(seed), device="cpu")

    def max_updates(self) -> int:
        return self.size // self.batch

    def indices(self, k: int) -> Tensor:
        lo = k * self.batch
        if lo + self.batch > self.size:
            raise core.EngineeringStop(f"ENGINEERING STOP — the pool of {self.size} chunks supports {self.size // self.batch} updates, not {k + 1}")
        return self.perm[lo : lo + self.batch]

    def get(self, k: int) -> Tensor:
        return self.table[self.start + self.indices(k)].long()


# --- snapshots with the optimizer state (resume identity) -------------------------------------------------------------------------------------------
def snapshot_dir(root: Path, step: int) -> Path:
    return root / f"snap-u{step:06d}"


def save_snapshot(root: Path, model: S3Model, optimizer: AdamW | None, step: int, identity: Mapping[str, Any]) -> dict[str, Any]:
    d = snapshot_dir(root, step)
    d.mkdir(parents=True, exist_ok=True)
    assert model.addition is not None
    torch.save({"addition": model.addition.state_dict(), "optimizer": optimizer.state_dict() if optimizer else None, "step": step, "identity": dict(identity)}, d / "state.pt")
    with (d / "state.pt").open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    write_json(d / "index.json", {"state_sha256": digest, "step": step, "identity_sha256": sha256(canonical_json(dict(identity))), "bytes": (d / "state.pt").stat().st_size})
    return {"sha256": digest, "bytes": (d / "state.pt").stat().st_size}


def _load_checked(root: Path, step: int, identity: Mapping[str, Any]) -> dict[str, Any]:
    d = snapshot_dir(root, step)
    index = read_json(d / "index.json")
    with (d / "state.pt").open("rb") as f:
        if hashlib.file_digest(f, "sha256").hexdigest() != index["state_sha256"]:
            raise ValueError("snapshot checksum mismatch")
    state = torch.load(d / "state.pt", weights_only=True, map_location="cpu")
    if state["step"] != step or state["identity"] != dict(identity):
        raise ValueError("snapshot step or identity mismatch")
    return state  # type: ignore[no-any-return]


def restore_snapshot(root: Path, model: S3Model, step: int, identity: Mapping[str, Any]) -> None:
    state = _load_checked(root, step, identity)
    assert model.addition is not None
    model.addition.load_state_dict(state["addition"], strict=True)


def restore_for_resume(root: Path, model: S3Model, rate: float, step: int, identity: Mapping[str, Any]) -> AdamW:
    """Model and optimizer state from a snapshot; the stream position is the update index. The rate is written into the group again (it is also in the state)."""
    state = _load_checked(root, step, identity)
    assert model.addition is not None
    model.addition.load_state_dict(state["addition"], strict=True)
    opt = make_optimizer(model, rate)
    opt.load_state_dict(state["optimizer"])
    opt.param_groups[0]["lr"] = float(rate)
    return opt


def snapshots_equal(root_a: Path, step_a: int, root_b: Path, step_b: int) -> bool:
    """Bitwise equality of the CONTENT of two snapshots (addition tensors, optimizer state tensors, param groups, step): the resume-identity and prefix-identity comparison. File hashes are not compared: serialising a restored
    optimizer's state can differ in bytes while every tensor is bit-identical."""
    a = torch.load(snapshot_dir(root_a, step_a) / "state.pt", weights_only=True, map_location="cpu")
    b = torch.load(snapshot_dir(root_b, step_b) / "state.pt", weights_only=True, map_location="cpu")
    if a["step"] != b["step"] or set(a["addition"]) != set(b["addition"]) or not all(torch.equal(a["addition"][k], b["addition"][k]) for k in a["addition"]):
        return False
    oa, ob = a["optimizer"], b["optimizer"]
    if (oa is None) != (ob is None):
        return False
    if oa is None:
        return True
    if oa["param_groups"] != ob["param_groups"] or list(oa["state"]) != list(ob["state"]):
        return False
    return all(set(oa["state"][i]) == set(ob["state"][i]) and all(torch.equal(oa["state"][i][k], ob["state"][i][k]) for k in oa["state"][i]) for i in oa["state"])


def train_run(model: S3Model, stream: PoolStream, rate: float, root: Path, snapshots: Sequence[int], max_update: int, identity: Mapping[str, Any], *, start: int = 0, optimizer: AdamW | None = None, pause_check: Callable[[], str | None] | None = None) -> dict[str, Any]:
    """Train from update ``start`` (0, or a snapshot's step with its optimizer) to ``max_update``, saving a snapshot after each update count in ``snapshots``. A ``FailedCell`` ends the run with status ``failed_cell`` and keeps the snapshots made;
    any other exception propagates (an item error / engineering stop). ``pause_check`` is asked after each snapshot at a rung (item boundary inside a long run, F19): a reason stops the run with status ``paused`` and the snapshot to resume from.
    Section 9.5's continuation rung is NOT implemented: nothing here can extend ``max_update`` beyond what the caller passes, and the caller derives it from the frozen plan."""
    opt = optimizer if optimizer is not None else make_optimizer(model, rate)
    snaps: dict[int, dict[str, Any]] = {}
    status: dict[str, Any] = {"status": "ok"}
    began = time.monotonic()
    model.train()
    if start == 0 and 0 in snapshots:
        snaps[0] = save_snapshot(root, model, opt, 0, identity)
    done = start
    try:
        for k in range(start, max_update):
            train_step(model, opt, stream.get(k), k + 1)
            done = k + 1
            if done in snapshots:
                snaps[done] = save_snapshot(root, model, opt, done, identity)
                if pause_check is not None and done < max_update:
                    reason = pause_check()
                    if reason:
                        status = {"status": "paused", "reason": reason, "resume_from": done}
                        break
    except FailedCell as e:
        status = {"status": "failed_cell", "reason": str(e), "failed_at_update": done + 1}
    return {**status, "snapshots": {str(k): v for k, v in snaps.items()}, "seconds": time.monotonic() - began, "updates_done": done, "bytes": sum(v["bytes"] for v in snaps.values())}


# --- the read set (G12) ----------------------------------------------------------------------------------------------------------------------------
def _fin(v: float) -> float | None:
    return v if math.isfinite(v) else None


def evaluate_reads(m: S3Model, panel: Tensor, seeds: Any, cell: int, mode: str, *, draws: int = 4, expected_targets: int = 32768, keep_usage: bool = False) -> dict[str, Any]:
    """The reads of one snapshot in ``mode`` (``core.read_list``). Keys ``"<read>|<draw>"``; a non-finite intervention value is None; the enabled read raises ``FailedCell`` if non-finite (the caller records it). The replay is made by the
    caller after a fresh restore. ``used_slots`` (and ``usage`` when asked: calibration checkpoints only, ruling 15) are the statistics of the enabled read."""

    def ev(ctl: Ctl | None = None, *, collector: Collector | None = None, nonfinite: str = "value") -> float:
        return evaluate(m, panel, ctl, collector=collector, expected_targets=expected_targets, nonfinite=nonfinite)

    wanted = {r for r, _ in core.read_list(m.arm, mode, draws)}
    out: dict[str, float | None] = {}
    stats: dict[str, Any] = {}
    col = Collector() if m.arm == FLAT else None
    out[f"{core.READ_ENABLED}|0"] = ev(collector=col, nonfinite="raise")
    if col is not None:
        stats["used_slots"] = len(col.selected)
        if keep_usage:
            stats["usage"] = [float(x) for x in col.usage.tolist()]
    if core.READ_DISABLED in wanted:
        m.bypass = True
        try:
            out[f"{core.READ_DISABLED}|0"] = _fin(ev(nonfinite="value"))
        finally:
            m.bypass = False
    if mode == "full":
        if m.arm == FLAT:
            mem = m.addition
            assert mem is not None and col is not None
            used = sorted(col.selected)
            for j in range(draws):
                v = p_used_values(mem.values, used, seeds.p_used(cell, j))  # type: ignore[union-attr]
                out[f"{core.READ_P_USED}|{j}"] = None if v is None else _fin(ev(Ctl("values", values=v)))
            out[f"{core.READ_X_MEAN}|0"] = _fin(ev(Ctl("X_mean")))
            vm = neg_ref_values(mem.values, col.usage)  # type: ignore[union-attr]
            out[f"{core.READ_V_MEAN}|0"] = _fin(ev(Ctl("values", values=vm)))
        else:
            out[f"{core.READ_X_MEAN_DENSE}|0"] = _fin(ev(Ctl("X_mean")))
    return {"reads": out, "stats": stats}


# --- NEG-REF with V_mean, and the planted positive (section 11) --------------------------------------------------------------------------------------
def _effects(m: S3Model, panel: Tensor, seeds: Any, cell: int, draws: int, expected_targets: int) -> dict[str, Any]:
    base = S3Model(m.backbone, core.BASE, None)
    b = evaluate(base, panel, expected_targets=expected_targets, nonfinite="value")
    col = Collector()
    h = evaluate(m, panel, None, collector=col, expected_targets=expected_targets, nonfinite="value")
    mem = m.addition
    assert mem is not None
    pu = []
    for j in range(draws):
        v = p_used_values(mem.values, sorted(col.selected), seeds.p_used(cell, j))  # type: ignore[union-attr]
        pu.append(evaluate(m, panel, Ctl("values", values=v), expected_targets=expected_targets, nonfinite="value") if v is not None else float("nan"))
    xm = evaluate(m, panel, Ctl("X_mean"), expected_targets=expected_targets, nonfinite="value")
    vm = evaluate(m, panel, Ctl("values", values=neg_ref_values(mem.values, col.usage)), expected_targets=expected_targets, nonfinite="value")  # type: ignore[union-attr]
    return {"B": b, "H": h, "C": b - h, "P_used": sum(pu) / draws - h, "X_mean": xm - h, "V_mean": vm - h, "usage": col.usage, "used_slots": len(col.selected)}


def neg_ref_check(m: S3Model, panel: Tensor, seeds: Any, cfg: Mapping[str, Any], *, cell: int = 0, expected_targets: int | None = None) -> dict[str, Any]:
    """NEG-REF of a checkpoint: every value row replaced by the usage-weighted mean value (weights from the enabled read on ``panel``). P_used, X_mean and V_mean of the NEG-REF must be 0 within 1e-6 and no NEG-REF cell may meet F2's or
    F3's per-cell condition (C > 0 and effect >= 0.5 C). The tolerance is ADR-0026's, the only comparison of two different computations in this study (section 11)."""
    n = expected_targets if expected_targets is not None else panel.shape[0] * (panel.shape[1] - 1)
    draws = int(cfg["controls"]["p_used_draws"])
    first = _effects(m, panel, seeds, cell, draws, n)
    ref = copy.deepcopy(m)
    assert ref.addition is not None
    with torch.no_grad():
        ref.addition.values.copy_(neg_ref_values(ref.addition.values, first["usage"]))  # type: ignore[union-attr]
    e = _effects(ref, panel, seeds, cell, draws, n)
    tol, half = float(cfg["thresholds"]["tolerance_neg_ref"]), float(cfg["thresholds"]["half"])
    zero = {k: bool(math.isfinite(e[k]) and abs(e[k]) <= tol) for k in ("P_used", "X_mean", "V_mean")}
    f2 = e["C"] > 0 and e["P_used"] >= half * e["C"]
    f3 = e["C"] > 0 and e["X_mean"] >= half * e["C"]
    return {"passed": all(zero.values()) and not f2 and not f3, "zero_within_tolerance": zero, "meets_f2_cell": bool(f2), "meets_f3_cell": bool(f3)}


def planted_positive(cfg: Mapping[str, Any], seeds: Any) -> dict[str, Any]:
    """On the toy of ``studies.p10i_s3.planted`` (identity blocks, tied embedding, a planted memory): P_used and X_mean are each >= 0.5 C with C > 0, and NEG-REF gives 0. Nothing here touches natural text or a registered seed."""
    panel = toy_panel(32)
    m = plant(FLAT)
    half = float(cfg["thresholds"]["half"])
    n = panel.shape[0] * 64
    e = _effects(m, panel, seeds, 0, int(cfg["controls"]["p_used_draws"]), n)
    neg = neg_ref_check(m, panel, seeds, cfg, cell=0, expected_targets=n)
    ok = e["C"] > 0 and e["P_used"] >= half * e["C"] and e["X_mean"] >= half * e["C"] and neg["passed"]
    return {"passed": bool(ok), "C": e["C"], "P_used": e["P_used"], "X_mean": e["X_mean"], "V_mean": e["V_mean"], "neg_ref": neg}


__all__ += ["PoolStream", "map_table", "train_run", "evaluate_reads", "neg_ref_check", "planted_positive", "save_snapshot", "restore_snapshot", "restore_for_resume", "snapshot_dir", "snapshots_equal", "DENSE", "FLAT"]
