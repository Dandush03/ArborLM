# ruff: noqa: E501
"""P9II evaluation at a readout (ADR-0019 section 8.2): accuracy on Panels A and B, on the held-out template panels H1 and H2, negative
log-likelihood over the alphabet, accuracy with the memory disabled and with values permuted, the unseen-fact control with the LEAKAGE flag,
address stability across the two panels, same-fact consistency, target-slot recall, the probe set once more (success condition 3), the LM-capability
loss with the memory active (every learned arm, A6 and A7), and G5 (backbone identity).

Imported from P9 and P9-I and called, not copied: ``studies.p9i.evaluate.evaluate_stream`` (cached read, scoring, G2 intervals, value permutation,
disabling, unseen control, LEAKAGE; it runs on a ``P9IIModel`` because that subclasses P9-I's model, and with ``supports=False`` no minimal-support
search is run: ADR-0019 does not use it), ``next_byte_loss``, ``corpus_rows``, ``controls_record``.

LM capability. The next-byte loss of the system with the addition active reading at its fixed answer sites (positions 8r + 6), 256-way cross-entropy
averaged over all 64 targets of each of the backbone's 2,048 corpus rows (inputs 0..63, targets 1..64), against the frozen backbone's. ``relative_rise``
r = (system - frozen) / frozen; ``absolute_rise`` = the same as a percentage is printed beside it (section 8.4 (c)). A non-finite loss keeps its raw
value as ``"+inf"``, ``"-inf"`` or ``"nan"`` and counts as a rise above any A6 + 0.05 (``flag_input`` reads it with ``core.number``).
"""

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch
from torch.nn import functional as F

from arborlm.io import file_sha256
from studies.p9.data import StudyData
from studies.p9i.evaluate import (
    controls_record,
    corpus_rows,
    evaluate_stream,
    next_byte_loss,
    stream_for,
)

from . import core
from .diagnostics import build_probe, probe_measures, probe_reads
from .model import P9IIModel, build_model, g5_check, target_injection
from .train import load_model_state

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

__all__ = ["controls_record", "corpus_rows"]
SECONDARY = {"H1": "h1", "H2": "h2"}
NEXT_BYTE_BATCH = 128


def _marker(value: float) -> float | str:
    return value if math.isfinite(value) else core.nonfinite_str(value)


# --- LM capability ----------------------------------------------------------------------------------------------------------
@torch.no_grad()
def system_next_byte_loss(model: P9IIModel, rows: "Tensor") -> float:
    """256-way next-byte loss of ``model`` with its addition active on ``rows [R, 65] int64``."""
    was = model.training
    model.eval()
    total, count = 0.0, 0
    try:
        for start in range(0, rows.shape[0], NEXT_BYTE_BATCH):
            chunk = rows[start : start + NEXT_BYTE_BATCH]
            logits, _ = model(chunk[:, : core.CONTEXT_BYTES].contiguous())
            target = chunk[:, 1 : core.CONTEXT_BYTES + 1]
            total += float(F.cross_entropy(logits.reshape(-1, 256), target.reshape(-1), reduction="sum"))
            count += int(target.numel())
    finally:
        model.train(was)
    return total / count


def language_modelling(model: P9IIModel, frozen: "Backbone", rows: "Tensor", frozen_loss: float | None = None) -> dict[str, float | str]:
    before = next_byte_loss(frozen, rows) if frozen_loss is None else frozen_loss
    after = system_next_byte_loss(model, rows)
    rise = (after - before) / before
    return {"before_nats": _marker(before), "after_nats": _marker(after), "relative_rise": _marker(rise), "absolute_rise_percent": _marker(100.0 * rise)}


def lm_flagged(rise: float, a6_rise: float) -> bool:
    """Section 8.4 (b): a cell is flagged if r > r(A6, same draw and size) + 0.05. A non-finite r is flagged; a non-finite A6 rise flags
    nothing it cannot measure against (the comparison is then NOT_INTERPRETED by the analysis, not decided here)."""
    if not math.isfinite(rise):
        return True
    if not math.isfinite(a6_rise):
        return False
    return rise > a6_rise + core.LM_MARGIN


# --- per-fact reads of a panel -----------------------------------------------------------------------------------------------
@torch.no_grad()
def panel_reads(model: P9IIModel, data: StudyData, facts: int, name: str) -> dict[str, "Tensor | None"]:
    """Per trained fact (index = fact id; the panel holds each once): the top-1 slot, the top 8 and the unit query (None where the arm has none)."""
    stream = stream_for(data, facts, name)
    top1 = torch.full((facts,), -1, dtype=torch.int64)
    top8 = torch.full((facts, core.TOP), -1, dtype=torch.int64)
    query = torch.zeros(facts, core.KEY_WIDTH)
    have_q = have_top = False
    was = model.training
    model.eval()
    try:
        for start in range(0, stream.tokens.shape[0], 64):
            tok = stream.tokens[start : start + 64, : core.INPUT_LENGTH].contiguous()
            ids = stream.fact_ids[start : start + 64]
            keep = ids < facts
            h = model.embed_block0(tok)
            sel = model.select(h, tok)
            q = model.answer_queries(h, tok)
            if sel is not None:
                have_top = True
                top1[ids[keep]] = sel.selected[:, :, 0][keep]
                top8[ids[keep]] = sel.selected[:, :, : core.TOP][keep]
            if q is not None:
                have_q = True
                query[ids[keep]] = q[keep]
    finally:
        model.train(was)
    return {"top1": top1 if have_top else None, "top8": top8 if have_top else None, "query": query if have_q else None}


def panel_statistics(a: dict[str, "Tensor | None"], b: dict[str, "Tensor | None"], injection: "Tensor | None") -> dict[str, Any]:
    """Address stability (share of facts whose top-1 slot is the same on Panels A and B), same-fact consistency (mean cosine of the two queries
    of the same fact) and, for an arm with a target slot (A1-S: the cell's injection, which it never trains on, a chance-level reference),
    the top-1 and top-8 recall of s(f) on each panel."""
    out: dict[str, Any] = {}
    if a["top1"] is not None and b["top1"] is not None:
        out["address_stability"] = float((a["top1"] == b["top1"]).float().mean())
    if a["query"] is not None and b["query"] is not None:
        out["same_fact_consistency"] = float(F.cosine_similarity(a["query"], b["query"], dim=-1).mean())
    if injection is not None:
        for panel, reads in (("A", a), ("B", b)):
            if reads["top1"] is not None:
                top1, top8 = reads["top1"], reads["top8"]
                assert top1 is not None and top8 is not None
                out[f"target_top1_recall_{panel}"] = float((top1 == injection).float().mean())
                out[f"target_top8_recall_{panel}"] = float((top8 == injection[:, None]).any(-1).float().mean())
    return out


# --- one readout ----------------------------------------------------------------------------------------------------------
def evaluate_readout(
    cell: core.Cell,
    model: P9IIModel,
    data: StudyData,
    facts: int,
    update: int,
    *,
    frozen_backbone: "Backbone",
    rows: "Tensor",
    target_seed: int,
    frozen_loss: float | None = None,
) -> dict[str, Any]:
    """The eval record of one cell at one readout (``model`` already holds the snapshot)."""
    was = model.training
    model.eval()
    try:
        record: dict[str, Any] = {
            **core.envelope("eval"),
            "label": cell.label,
            "arm": cell.arm,
            "stage": cell.stage,
            "slots": cell.slots,
            "draw": cell.draw,
            "seed_index": cell.seed_index,
            "update": update,
            "facts": facts,
            "identity": core.code_identity(),
            "environment": core.environment(),
            "panels": {},
            "secondary": {},
        }
        for panel in core.PANELS:
            record["panels"][panel] = evaluate_stream(model, data, facts, core.PANEL_STREAM[panel], primary=True, supports=False)
        for name, stream in SECONDARY.items():
            record["secondary"][name] = evaluate_stream(model, data, facts, stream, primary=False)
        injection = target_injection(facts, cell.slots, target_seed) if cell.arm in core.TARGET_ARMS else None
        reads = {p: panel_reads(model, data, facts, core.PANEL_STREAM[p]) for p in core.PANELS}
        record["panel_statistics"] = panel_statistics(reads["A"], reads["B"], injection)
        probe = build_probe(data, facts)
        keys = getattr(model.addition, "keys", None)
        targets = None if injection is None else injection[probe.fact]
        record["probe"] = probe_measures(probe_reads(model, probe), probe, keys=None if keys is None else keys.detach(), targets=targets, centred_arm=cell.arm == "A5-C")
        record["language_modelling"] = language_modelling(model, frozen_backbone, rows, frozen_loss)
        record["g5"] = g5_check(model, frozen_backbone, rows[:, : core.CONTEXT_BYTES].contiguous())
    finally:
        model.train(was)
    return record


def evaluate_cell(
    cell: core.Cell,
    run_dir: Path,
    data: StudyData,
    backbone: "Backbone",
    *,
    facts: int,
    readouts: list[int],
    init_seed: int,
    r1_seed: int,
    rows: "Tensor",
    out_dir: Path | None = None,
    extra: dict[str, Any] | None = None,
    require_train_record: bool = False,
) -> list[Path]:
    """Evaluate the snapshots at ``readouts`` of a trained cell and write one ``eval`` record each (never over an existing one). The snapshot's
    model file must hash to the value recorded in ``train.json`` (required when ``require_train_record``)."""
    written: list[Path] = []
    folder = out_dir or core.cell_dir(run_dir, cell.label)
    train_json = folder / "train.json"
    recorded: dict[str, str] | None = None
    target_seed = core.target_seed(data.seeds, cell.seed_index)
    if train_json.is_file():
        train_record = core.read_record(train_json, "train")
        recorded, target_seed = train_record["snapshot_sha256"], int(train_record["target_seed"])
    elif require_train_record:
        raise ValueError(f"no train record at {train_json}: the snapshot hash cannot be verified")
    frozen_loss = next_byte_loss(backbone, rows)
    for update in readouts:
        snap = folder / "snapshots" / core.snapshot_stem(update)
        if recorded is not None and file_sha256(snap / "model.pt") != recorded.get(str(update)):
            raise ValueError(f"snapshot {snap / 'model.pt'} does not match the hash recorded in train.json")
        model = build_model(cell.arm, cell.slots, init_seed, backbone, r1_seed=r1_seed, seed_rng=False)
        load_model_state(snap, model)
        record = evaluate_readout(cell, model, data, facts, update, frozen_backbone=backbone, rows=rows, target_seed=target_seed, frozen_loss=frozen_loss)
        record.update(extra or {})
        path = folder / "eval" / core.snapshot_stem(update) / "eval.json"
        if path.exists():
            raise FileExistsError(path)
        core.write_record(path, core.jsonable(record))
        written.append(path)
    return written


def calibration_accuracy(model: P9IIModel, data: StudyData, facts: int) -> float:
    """Accuracy on the draw's calibration stream restricted to the cell's trained facts (section 6: the calibration rule measures accuracy there)."""
    return float(evaluate_stream(model, data, facts, "calibration", primary=False, supports=False)["accuracy"])
