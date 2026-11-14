"""P7-B stream B tracing (ADR-0014 section 7a, 'Stream B, exact handling').

For each checkpoint, in one process: (1) replay the recorded P5 NLL on the P5 panel bitwise;
(2) regenerate the calibration and stream-A traces and require them to be byte-identical to the
identity manifest; (3) trace stream B (selected slot IDs and visited branch IDs only); (4) run the
integrity checks; (5) record the identity of the stream-B trace, its per-slot count hash and the
hashes of its three count-preserving null streams (seeds 91321-91323).

**No loss, perplexity or quality number is computed on stream B**: the tracing path is
``p7a_trace.collect_trace``, which calls the model forward on the inputs only and never touches the
targets or ``loss_for``. The only place a loss is computed is the P5-panel replay of step (1).

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

from pathlib import Path
from typing import Any

from torch import Tensor

from . import p7a_core as a_core
from . import p7b_core as core
from .io import file_sha256
from .p5_config import STEPS
from .p6_common import CellSource
from .p7a_trace import GateViolation, bitwise_equal, collect_trace

STREAM_B_PREFIX = "streamB"


def regeneration_check(
    label: str,
    identity: core.Identity,
    eval_selected: Tensor,
    eval_branches: Tensor | None,
    cal_selected: Tensor,
    cal_branches: Tensor | None,
) -> dict[str, Any]:
    """The regenerated calibration and stream-A traces must hash to the identity manifest."""
    got = {
        "evaluation.selected": core.tensor_sha256_int16(eval_selected),
        "calibration.selected": core.tensor_sha256_int16(cal_selected),
    }
    if eval_branches is not None and cal_branches is not None:
        got["evaluation.branches"] = core.tensor_sha256_int8(eval_branches)
        got["calibration.branches"] = core.tensor_sha256_int8(cal_branches)
    differing = []
    for role, digest in got.items():
        if identity.recorded_sha(label, role) != digest:
            differing.append(role)
    expected_roles = {r for r in core.ROLES if identity.recorded_sha(label, r) is not None}
    if differing or set(got) != expected_roles:
        raise GateViolation(
            "regeneration",
            f"{label}: regenerated trace differs from the identity manifest",
            {"differing_roles": differing, "regenerated_roles": sorted(got)},
        )
    return {"byte_identical_to_identity_manifest": True, "sha256": got}


def trace_stream_b(model: Any, panel_b: Tensor) -> tuple[Tensor, Tensor | None]:
    """Stream B's selected IDs (and visited branches): the model forward on the inputs only. No
    target is read and no loss function is called."""
    return collect_trace(model, panel_b)


def trace_checkpoint_b(
    source: CellSource,
    kind: str,
    directory: Path,
    *,
    panel_b: Tensor,
    calibration: Tensor,
    identity: core.Identity,
    recorded_retrieval: dict[str, Any] | None,
    panel_b_sha256: str,
) -> dict[str, Any]:
    """The seven steps for one checkpoint; returns the compact record (no trace content)."""
    from .p5_model import evaluate, state_digest

    model = source.models[kind]
    label = core.cell_label(source.pair, kind)
    index = core.cell_index(source.pair, kind)
    queries = int(panel_b.shape[0]) * core.CONTEXT
    evidence = source.evidence[kind]
    paths = (
        []
        if source.synthetic
        else [Path(evidence["path"]) / "state.pt", Path(evidence["path"]) / "index.json"]
    )
    file_before = {p.name: file_sha256(p) for p in paths}
    digest_before = state_digest(model)
    # (1) bitwise replay of the recorded P5 NLL on the P5 panel (the only loss computed here)
    replay = evaluate(model, source.panel, int(source.panel.shape[0]) * core.CONTEXT)
    recorded_nll = source.recorded[kind]["nll"]
    if not bitwise_equal(replay["nll"], recorded_nll):
        raise GateViolation(
            "nll_replay",
            f"{label}: replayed NLL differs from the recorded P5 NLL",
            {"replayed": replay["nll"], "recorded": recorded_nll},
        )
    # (2) regenerate calibration and stream A; byte-identity with the identity manifest
    eval_selected, eval_branches = collect_trace(model, source.panel)
    cal_selected, cal_branches = collect_trace(model, calibration)
    regenerated = regeneration_check(
        label, identity, eval_selected, eval_branches, cal_selected, cal_branches
    )
    # (3) stream B: selected IDs and branch IDs only
    selected_b, branches_b = trace_stream_b(model, panel_b)
    digest_after = state_digest(model)
    file_after = {p.name: file_sha256(p) for p in paths}
    if digest_after != digest_before or file_after != file_before:
        raise GateViolation("checkpoint_hash", f"{label}: checkpoint changed during tracing")
    if not source.synthetic and any(
        file_before[p.name] != evidence[key]
        for p, key in zip(paths, ("state_sha256", "index_sha256"), strict=True)
    ):
        raise GateViolation("checkpoint_hash", f"{label}: file hash differs from the P5 record")
    # (4) integrity: stream-A regeneration against P5's recorded histogram, then stream B
    try:
        a_core.check_trace(
            eval_selected,
            eval_branches,
            kind,
            recorded=recorded_retrieval,
            queries=int(source.panel.shape[0]) * core.CONTEXT,
        )
        a_core.check_trace(
            cal_selected, cal_branches, kind, queries=int(calibration.shape[0]) * core.CONTEXT
        )
        integrity = a_core.check_trace(selected_b, branches_b, kind, queries=queries)
    except a_core.TraceIntegrityError as exc:
        raise GateViolation("trace_integrity", f"{label}: {exc}") from exc
    files = a_core.write_trace(directory, STREAM_B_PREFIX, selected_b, branches_b, queries)
    # (5) identity of stream B: counts hash and null streams
    counts = a_core.selection_counts(selected_b)
    _, null_info = core.null_streams(counts, core.STREAM_B_NULL_SEEDS, index)
    return {
        "schema": core.SCHEMA_TRACE_B,
        "label": label,
        "kind": kind,
        "pair": list(source.pair),
        "cell_index": index,
        "synthetic": source.synthetic,
        "queries": queries,
        "step": STEPS,
        "trace_dir": directory.name,
        "stream_b": {
            "split": "validation",
            "ranks": list(core.PANEL_B_RANKS) if not source.synthetic else None,
            "panel_sha256": panel_b_sha256,
            "contexts": int(panel_b.shape[0]),
        },
        "files": {"stream_b": files},
        "integrity": integrity,
        "counts_sha256": core.counts_sha256(counts),
        "unique_selected_slots": integrity["unique_selected_slots"],
        "nulls": [
            {
                k: info[k]
                for k in ("replicate_seed", "generator_seed", "stream_sha256", "repair_swaps")
            }
            for info in null_info
        ],
        "regeneration": regenerated,
        "replay": {
            "recorded_nll": recorded_nll,
            "replayed_nll": replay["nll"],
            "bitwise_equal": True,
            "panel": "P5 panel (validation ranks 2048-2559), not stream B",
        },
        "loss_computed_on_stream_b": False,
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
            if kind == "flat"
            else "int8 little-endian [queries, 2], visited branch IDs in rank order",
            "order": "context by context, position 0..63",
        },
    }
