"""P7-A trace generation (the only step that runs a model) and synthetic traces for the budget run.

Real traces are taken from the unmodified frozen P5 ``Model`` after a bitwise replay of the
recorded P5 final NLL. Nothing here changes weights, routing, scoring or RNG state. The synthetic
generator makes concentrated, heavy-tailed fake traces for timing and tests only; it never touches
a checkpoint.

Status: implementation self-checked only.
"""

import struct
from pathlib import Path
from typing import Any

import torch
from torch import Tensor

from . import p7a_core as core
from .io import file_sha256
from .p5_config import BATCH, FLAT, STEPS
from .p6_common import CellSource


class GateViolation(Exception):
    """A registered stop: NLL replay mismatch, checkpoint hash change or trace-integrity failure."""

    def __init__(self, gate: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(f"{gate}: {message}")
        self.gate, self.message, self.details = gate, message, details or {}


def configure_deterministic_cpu() -> None:
    """The registered environment: CPU float32, deterministic algorithms, single thread (P5's own
    ``configure_cpu``). A second call in one process cannot set the inter-op threads again; that
    case keeps the remaining settings."""
    from .engine import configure_cpu

    try:
        configure_cpu()
    except RuntimeError:
        torch.set_default_device("cpu")
        torch.set_default_dtype(torch.float32)
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True, warn_only=False)


def bitwise_equal(first: float, second: float) -> bool:
    return struct.pack("!d", first) == struct.pack("!d", second)


def collect_trace(model: Any, data: Tensor) -> tuple[Tensor, Tensor | None]:
    """Selected slot IDs (and visited branch IDs for trees) per query in registered stream order:
    context by context, position 0 to 63. The model sees P5's batching (8 contexts per batch);
    the row order of its lookup output is context-major, which is the registered order."""
    from .longer_training import _isolated_rng

    was_training = model.training
    model.eval()
    selected: list[Tensor] = []
    branches: list[Tensor] = []
    try:
        with _isolated_rng(), torch.no_grad():
            for start in range(0, data.shape[0], BATCH):
                batch = data[start : start + BATCH]
                _, lookup = model(batch[:, :-1])
                if lookup is None:
                    raise GateViolation("trace", "model returned no retrieval")
                selected.append(lookup.selected.to(torch.int64))
                if lookup.branch_ids is not None:
                    branches.append(lookup.branch_ids.to(torch.int64))
    finally:
        model.train(was_training)
    return torch.cat(selected), (torch.cat(branches) if branches else None)


def trace_checkpoint(
    source: CellSource,
    kind: str,
    directory: Path,
    *,
    contexts: int,
    calibration: Tensor,
    recorded_retrieval: dict[str, Any] | None,
) -> dict[str, Any]:
    """Integrity replay, then the evaluation and calibration traces of one checkpoint.

    ``recorded_retrieval`` is P5's ``final.retrieval`` for the cell. On the synthetic fixture the
    caller supplies the fixture's own replay-derived record.
    """
    from .p5_model import evaluate, state_digest

    model = source.models[kind]
    label = core.cell_label(source.pair, kind)
    queries = contexts * core.CONTEXT
    evidence = source.evidence[kind]
    paths = (
        []
        if source.synthetic
        else [Path(evidence["path"]) / "state.pt", Path(evidence["path"]) / "index.json"]
    )
    file_before = {p.name: file_sha256(p) for p in paths}
    digest_before = state_digest(model)
    replay = evaluate(model, source.panel, queries)
    recorded_nll = source.recorded[kind]["nll"]
    if not bitwise_equal(replay["nll"], recorded_nll):
        raise GateViolation(
            "nll_replay",
            f"{label}: replayed NLL differs from the recorded P5 NLL",
            {"replayed": replay["nll"], "recorded": recorded_nll},
        )
    eval_selected, eval_branches = collect_trace(model, source.panel)
    cal_selected, cal_branches = collect_trace(model, calibration)
    digest_after = state_digest(model)
    file_after = {p.name: file_sha256(p) for p in paths}
    if digest_after != digest_before or file_after != file_before:
        raise GateViolation("checkpoint_hash", f"{label}: checkpoint changed during tracing")
    if not source.synthetic and any(
        file_before[p.name] != evidence[key]
        for p, key in zip(paths, ("state_sha256", "index_sha256"), strict=True)
    ):
        raise GateViolation("checkpoint_hash", f"{label}: file hash differs from the P5 record")
    try:
        integrity = core.check_trace(
            eval_selected, eval_branches, kind, recorded=recorded_retrieval, queries=queries
        )
        core.check_trace(cal_selected, cal_branches, kind, queries=queries)
    except core.TraceIntegrityError as exc:
        raise GateViolation("trace_integrity", f"{label}: {exc}") from exc
    files = {
        "evaluation": core.write_trace(directory, "eval", eval_selected, eval_branches, queries),
        "calibration": core.write_trace(directory, "calib", cal_selected, cal_branches, queries),
    }
    return {
        "schema": core.SCHEMA_TRACE,
        "label": label,
        "kind": kind,
        "pair": list(source.pair),
        "cell_index": core.cell_index(source.pair, kind),
        "synthetic": source.synthetic,
        "queries": queries,
        "step": STEPS,
        "evaluation_stream": {
            "split": "validation",
            "ranks": list(core.EVAL_RANKS) if not source.synthetic else None,
            "contexts": contexts,
        },
        "calibration_stream": {
            "split": "training pool",
            "ranks": [core.CAL_START, core.CAL_END] if not source.synthetic else None,
            "contexts": contexts,
        },
        "context_bytes": core.CONTEXT,
        "trace_dir": directory.name,
        "files": files,
        "integrity": integrity,
        "replay": {
            "recorded_nll": recorded_nll,
            "replayed_nll": replay["nll"],
            "bitwise_equal": True,
        },
        "checkpoint": {
            "files_sha256_before": file_before,
            "files_sha256_after": file_after,
            "files_unchanged": True,
            "state_digest_before": digest_before,
            "state_digest_after": digest_after,
            "recorded_state_sha256": source.recorded[kind]["state_sha256"],
        },
        "format": {
            "selected": "int16 little-endian [queries, 8], slot IDs in returned order",
            "branches": None
            if kind == FLAT
            else "int8 little-endian [queries, 2], visited branch IDs in rank order",
            "order": "context by context, position 0..63",
        },
    }


# --- synthetic traces (budget and tests only) -----------------------------------------------------
def synthetic_trace(
    kind: str,
    seed: int,
    *,
    queries: int = core.QUERIES,
    hot_slots: int = 400,
    exponent: float = 1.1,
) -> tuple[Tensor, Tensor | None]:
    """A concentrated fake trace: slot weights are a Zipf law over a few hundred hot slots.

    Flat: eight distinct slots per query drawn without replacement from the hot slots. Tree: each
    query picks two branches (weights favour a few branches, with persistence inside a context)
    and draws eight distinct slots from the hot slots lying in those two branches; the hot slots
    are spread so that every branch holds at least ``hot_slots / 32`` of them, enough for eight
    distinct selections.
    """
    generator = torch.Generator().manual_seed(seed)
    hot = torch.randperm(core.SLOTS, generator=generator)[:hot_slots]
    if kind != FLAT:
        per_branch = hot_slots // core.BRANCHES
        hot = torch.cat(
            [
                b * core.PER_BRANCH
                + torch.randperm(core.PER_BRANCH, generator=generator)[:per_branch]
                for b in range(core.BRANCHES)
            ]
        )
    ranks = torch.arange(1, hot.numel() + 1, dtype=torch.float64)
    weights = torch.zeros(core.SLOTS, dtype=torch.float32)
    shuffled = hot[torch.randperm(hot.numel(), generator=generator)]
    weights[shuffled] = (ranks**-exponent).float()
    if kind == FLAT:
        selected = torch.multinomial(
            weights.expand(queries, core.SLOTS), core.TOP, replacement=False, generator=generator
        )
        return selected, None
    branch_weights = torch.zeros(core.BRANCHES, dtype=torch.float32)
    branch_weights += weights.reshape(core.BRANCHES, core.PER_BRANCH).sum(dim=1)
    branch_weights = branch_weights**1.5
    picks = torch.multinomial(
        branch_weights.expand(queries, core.BRANCHES), 2, replacement=False, generator=generator
    )
    # Persistence: within a context, half of the queries repeat the previous branch pair.
    again = torch.rand(queries, generator=generator) < 0.5
    again[:: core.CONTEXT] = False
    for i in range(1, queries):
        if bool(again[i]):
            picks[i] = picks[i - 1]
    selected_rows = torch.empty((queries, core.TOP), dtype=torch.int64)
    slot_weights = weights.reshape(core.BRANCHES, core.PER_BRANCH)
    for pair in {tuple(row) for row in picks.tolist()}:
        rows = ((picks[:, 0] == pair[0]) & (picks[:, 1] == pair[1])).nonzero().flatten()
        local = torch.cat([slot_weights[pair[0]], slot_weights[pair[1]]])
        draw = torch.multinomial(
            local.expand(rows.numel(), local.numel()),
            core.TOP,
            replacement=False,
            generator=generator,
        )
        ids = torch.cat(
            [
                torch.arange(pair[0] * core.PER_BRANCH, (pair[0] + 1) * core.PER_BRANCH),
                torch.arange(pair[1] * core.PER_BRANCH, (pair[1] + 1) * core.PER_BRANCH),
            ]
        )
        selected_rows[rows] = ids[draw]
    return selected_rows, picks
