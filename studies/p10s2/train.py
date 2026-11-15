# ruff: noqa: E501
"""Training of one cell (ADR-0022 section 6): U updates of batch 32 with AdamW (no weight decay, clip 1.0, constant learning rate) and a fresh optimizer state; sequence-level cross-entropy on
the target tokens (prompt positions masked). The student is never trained: only the arm's parameters have gradients. The device comes from the call (config), never from the code path.

Batch order is a fresh +2 generator per use (section 9): concatenated epoch permutations of the stream, cut into batches. A replayed row stream (M-ii) uses its own fresh +2 generator.
Training on MPS is not bit-reproducible; snapshots are the object and every score is recomputed on CPU (sections 13.3, 15).

Failures (audit B M10): any exception inside the update loop (an unsupported MPS operation, a device error, an out-of-memory, a stage stop) ends the cell with a ``failed`` record carrying the error text,
never an exception out of ``train_arm``; the arm and the student are moved back to CPU in a ``finally``. ``STOP`` is the stage guard's request to end the running work (a reached stage cap or memory
limit): every cell started after it, and the cell running when it is set, ends ``failed`` with the reason, so a replicate's other records survive.
"""

import math
import os
import resource
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

import torch
from torch import Tensor
from torch.nn import functional as F

from . import core
from .memory import Arm, Read, run_student
from .model import Student
from .tokenization import Example


class StopRequest:
    """The stage guard's request to stop running work (a stage cap or memory limit reached). ``reason`` is None while nothing is requested; hooks (a ``Deadline``) are asked on every read, so a stage cap
    stops the cell running at the next update without a helper thread."""

    def __init__(self) -> None:
        self._reason: str | None = None
        self.hooks: list[Callable[[], str | None]] = []

    @property
    def reason(self) -> str | None:
        if self._reason is not None:
            return self._reason
        for h in self.hooks:
            r = h()
            if r is not None:
                return r
        return None

    def set(self, reason: str) -> None:
        if self._reason is None:
            self._reason = reason

    def clear(self) -> None:
        self._reason = None
        self.hooks.clear()


STOP = StopRequest()
MPS_IN_USE = False  # set once a cell has been trained on MPS: only then is the MPS driver asked for its memory (asking initializes the device)


def process_memory_bytes() -> dict[str, int]:
    """Peak resident set of this process, and the MPS driver's and the allocator's current memory when MPS was used. ``max`` is the figure the memory rule reads: ``ru_maxrss`` does not see MPS memory (a
    2 GiB MPS tensor raised it by 0.024 GiB in audit B4), so the driver's number counts as well."""
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss = int(r if sys.platform == "darwin" else r * 1024)
    out = {"rss_peak": rss, "mps_driver": 0, "mps_allocated": 0}
    if MPS_IN_USE and torch.backends.mps.is_available():
        out["mps_driver"] = int(torch.mps.driver_allocated_memory())
        out["mps_allocated"] = int(torch.mps.current_allocated_memory())
    out["max"] = max(out["rss_peak"], out["mps_driver"], out["mps_allocated"])
    return out


class NonFiniteLoss(RuntimeError):
    """A cell whose loss became non-finite is recorded as failed and never silently scored."""


def select_device(name: str) -> torch.device:
    """``cpu``, ``mps`` or ``auto`` (mps when available, else cpu). An unavailable device is an error; ``PYTORCH_ENABLE_MPS_FALLBACK`` must be unset so any fallback is an error (G4)."""
    if name == "cpu":
        return torch.device("cpu")
    if os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK"):
        raise RuntimeError("PYTORCH_ENABLE_MPS_FALLBACK is set: an MPS fallback must be an error (gate G4)")
    avail = bool(torch.backends.mps.is_available())
    if name == "mps":
        if not avail:
            raise RuntimeError("device mps requested but unavailable")
        return torch.device("mps")
    if name == "auto":
        return torch.device("mps" if avail else "cpu")
    raise ValueError(f"unknown device {name!r}")


def reads_of(ex: Example, tasks: Sequence[str], marker_index: int) -> list[Read]:
    """The reads of one example under a route: every in-vocabulary source word and the task marker, once per routed task. An empty task list is route "none"."""
    out: list[Read] = []
    for t in tasks:
        out += [(pos, t, j) for pos, j in ex.reads]
        out.append((ex.marker, t, marker_index))
    return out


def collate(examples: Sequence[Example], marker_index: int, device: torch.device | None = None) -> tuple[Tensor, Tensor, list[list[Read]]]:
    """Right-padded ids, labels (-100 except on target tokens: the label of position t is ids[t+1]) and the read lists, each example read under its own task."""
    width = max(len(e.ids) for e in examples)
    ids = torch.zeros(len(examples), width, dtype=torch.long)
    labels = torch.full((len(examples), width), -100, dtype=torch.long)
    reads: list[list[Read]] = []
    for b, e in enumerate(examples):
        ids[b, : len(e.ids)] = torch.tensor(list(e.ids), dtype=torch.long)
        if e.target_len:
            labels[b, e.prompt_len - 1 : len(e.ids) - 1] = torch.tensor(list(e.ids[e.prompt_len :]), dtype=torch.long)
        reads.append(reads_of(e, [e.task], marker_index))
    if device is not None:
        ids, labels = ids.to(device), labels.to(device)
    return ids, labels, reads


def batch_plan(n: int, updates: int, batch: int, generator: torch.Generator) -> list[list[int]]:
    """Batches of indices: epoch permutations of ``range(n)`` concatenated (a fresh generator per use), cut into ``updates`` batches of ``batch``. An epoch's tail carries into the next."""
    stream: list[int] = []
    while len(stream) < updates * batch:
        stream += torch.randperm(n, generator=generator).tolist()
    return [stream[u * batch : (u + 1) * batch] for u in range(updates)]


def loss_of(student: Student, arm: Arm, examples: Sequence[Example], marker_index: int, device: torch.device) -> Tensor:
    ids, labels, reads = collate(examples, marker_index, device)
    logits = run_student(student, arm, ids, reads)
    return F.cross_entropy(logits.reshape(-1, logits.shape[-1]), labels.reshape(-1), ignore_index=-100)


@dataclass
class TrainRecord:
    status: str  # "completed" | "failed"
    updates: int
    batch: int
    replay_rows: int
    rows_per_update: int
    device: str
    wall_seconds: float
    seconds_per_update: float
    trainable_parameters: int
    first_loss: float
    last_loss: float
    losses: list[float] = field(default_factory=list)
    error: str = ""

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = core.jsonable({k: getattr(self, k) for k in self.__dataclass_fields__})
        return out


def train_arm(
    student: Student,
    arm: Arm,
    examples: Sequence[Example],
    updates: int,
    batch: int,
    lr: float,
    order_generator: torch.Generator,
    marker_index: int,
    *,
    device: torch.device | None = None,
    clip: float | None = None,
    replay: Sequence[Example] | None = None,
    replay_rows: int = 0,
    replay_generator: torch.Generator | None = None,
    on_update: Callable[[int], None] | None = None,
) -> TrainRecord:
    """Train the arm's trainable parameters for ``updates`` updates. ``replay`` rows (M-ii) are added to every batch: ``replay_rows`` of them, ordered by ``replay_generator``. A non-finite loss stops
    the cell and returns a failed record (kept, never retried with changed settings)."""
    global MPS_IN_USE
    dev = device if device is not None else torch.device("cpu")
    params = arm.trainable()
    if not params:
        raise ValueError("the arm has no trainable parameter")
    clip_norm = clip if clip is not None else core.CFG["training"]["clip_norm"]
    wd = core.CFG["training"]["weight_decay"]
    previous_deterministic = torch.are_deterministic_algorithms_enabled()
    if dev.type == "mps":
        MPS_IN_USE = True
        if previous_deterministic:
            torch.use_deterministic_algorithms(False)  # MPS training is not bit-reproducible by design (snapshots are the object); a deterministic-mode error must not end a cell
    losses: list[float] = []
    status, err = "completed", ""
    plan: list[list[int]] = []
    rplan: list[list[int]] | None = None
    t0 = time.perf_counter()
    try:
        student.to(dev)
        arm.to(dev)
        opt = torch.optim.AdamW(params, lr=lr, weight_decay=wd)  # a fresh optimizer state
        plan = batch_plan(len(examples), updates, batch, order_generator)
        rplan = batch_plan(len(replay), updates, replay_rows, replay_generator) if replay is not None and replay_rows and replay_generator is not None else None
        t0 = time.perf_counter()
        for u in range(updates):
            if STOP.reason is not None:
                status, err = "failed", f"stopped before update {u}: {STOP.reason}"
                break
            rows = [examples[i] for i in plan[u]]
            if rplan is not None and replay is not None:
                rows += [replay[i] for i in rplan[u]]
            loss = loss_of(student, arm, rows, marker_index, dev)
            if not torch.isfinite(loss):
                status, err = "failed", f"non-finite loss at update {u}"
                losses.append(float("nan"))
                break
            opt.zero_grad(set_to_none=True)
            loss.backward()  # type: ignore[no-untyped-call]
            torch.nn.utils.clip_grad_norm_(params, clip_norm)
            opt.step()
            losses.append(float(loss.item()))
            if on_update is not None:
                on_update(u + 1)
    except KeyboardInterrupt:
        if STOP.reason is None:
            raise
        status, err = "failed", f"stopped at update {len(losses)}: {STOP.reason}"
    except Exception as e:  # noqa: BLE001 (any device or operation error ends the cell as a kept failed record, audit B M10)
        status, err = "failed", f"{type(e).__name__}: {e} (at update {len(losses)})"
    finally:
        wall = time.perf_counter() - t0
        if previous_deterministic and not torch.are_deterministic_algorithms_enabled():
            torch.use_deterministic_algorithms(True)
        try:
            arm.to(torch.device("cpu"))  # snapshots and every score live on CPU
            student.to(torch.device("cpu"))
        except Exception as e:  # noqa: BLE001
            status, err = "failed", (err + "; " if err else "") + f"could not move back to CPU: {type(e).__name__}: {e}"
    done = len(losses)
    return TrainRecord(
        status, done, batch, replay_rows if rplan is not None else 0, batch + (replay_rows if rplan is not None else 0), str(dev), wall, wall / max(1, done), sum(p.numel() for p in params),
        losses[0] if losses else math.nan, losses[-1] if losses else math.nan, losses, err,
    )  # fmt: skip


def gradient_reach(student: Student, arm: Arm, examples: Sequence[Example], marker_index: int) -> dict[str, Any]:
    """Gate G4, gradient reach: after one backward pass every trainable parameter of the arm has a gradient and no student parameter does. For M-append-frozen the caller checks, in addition,
    that no first-stage row, key or gate has a gradient (they are not trainable)."""
    for p in [*arm.trainable(), *student.parameters()]:
        p.grad = None
    loss = loss_of(student, arm, examples, marker_index, torch.device("cpu"))
    loss.backward()  # type: ignore[no-untyped-call]
    arm_reach = [p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in arm.trainable()]
    student_reach = [p.grad is not None for p in student.parameters()]
    return {"loss": float(loss.item()), "arm_parameters": len(arm_reach), "arm_with_gradient": sum(arm_reach), "student_with_gradient": sum(student_reach)}


def update_agreement(loss_a: Sequence[float], loss_b: Sequence[float], params_a: Sequence[Tensor], params_b: Sequence[Tensor]) -> dict[str, Any]:
    """Gate G4, MPS against CPU: the losses of the same 20 updates agree within 1e-3 and the parameters within a relative norm difference of 1e-4 (tolerances from the config)."""
    g = core.CFG["gates"]
    dl = max((abs(a - b) for a, b in zip(loss_a, loss_b, strict=True)), default=math.inf)
    rel = max(
        ((pa.detach().cpu() - pb.detach().cpu()).norm() / pa.detach().cpu().norm().clamp_min(1e-30)).item() for pa, pb in zip(params_a, params_b, strict=True)
    ) if params_a else math.inf  # fmt: skip
    return {"max_loss_difference": dl, "max_relative_parameter_difference": rel, "ok": dl <= g["mps_loss_tolerance"] and rel <= g["mps_parameter_relative_tolerance"]}
