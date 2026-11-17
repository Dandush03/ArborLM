# ruff: noqa: E501
"""P10S0 evaluation at a readout. The readout of ADR-0019 section 8.2 is ``studies.p9ii.evaluate.evaluate_readout`` itself (accuracy on Panels A and B, held-out template
panels, value permutation, memory disabled, the unseen-fact control and LEAKAGE, address stability, the probe, LM capability with cost, G5), called and not copied; its record
is re-stamped with S0's envelope and identity. What S0 adds is the read swap and a_use (ADR-0020 section 8.1, ADR-0021 section 7.1):

* pi is a seeded derangement of the cell's facts with answer(pi(f)) != answer(f).
* For fact f on a panel, the swapped prediction is the model's prediction at f's answer site when the memory's read vector THERE is replaced by the read vector the model computes at
  pi(f)'s answer site in pi(f)'s own panel context. Only that site is replaced (the second block attends over earlier positions, so the other sites keep their own reads).
* The swapped prediction counts as f's answer if that answer is among the arg-max symbols of the 32-symbol alphabet scoring (ties on the conservative side).
* a_use = (facts answered correctly whose swapped prediction is not their answer) / (facts) = a share of all facts, comparable with accuracy. ``a_use_of_correct`` (the same count
  over the correct facts) is recorded beside it; condition 6, a_use >= 0.95 x accuracy, is the same statement in both. i = 5 - h2(e) - e log2(31) bits per fact with e = 1 - a_use,
  and 0 when the count is at or below the upper end of the chance interval (G2).
"""

import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch

from arborlm.io import file_sha256
from studies.p9 import core as p9core
from studies.p9.data import StudyData
from studies.p9i.evaluate import next_byte_loss, stream_for
from studies.p9ii import evaluate as p9iieval
from studies.p9ii.model import SITES
from studies.p9ii.train import load_model_state

from . import core
from .model import build_model, derangement

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

corpus_rows = p9iieval.corpus_rows
controls_record = p9iieval.controls_record
ALPHABET_INDEX = torch.tensor(p9core.ALPHABET, dtype=torch.int64)
SWAP_CHUNK = 64


def has_read(arm: str) -> bool:
    """The read swap needs a memory read vector: every learned arm and WX. A6 reads an oracle code (its swap is not defined as a measure of a learned address) and A7 has no memory."""
    return arm in core.LEARNED_ARMS


def fact_answers(data: StudyData, facts: int, panel: str = "A") -> "Tensor":
    """``[facts]`` answer symbol (0..31) of each trained fact, from the panel's stream (every trained fact once)."""
    stream = stream_for(data, facts, core.PANEL_STREAM[panel])
    keep = (stream.fact_ids < facts).all(dim=1)
    ids, ans = stream.fact_ids[keep], stream.answer_targets()[keep]
    out = torch.full((facts,), -1, dtype=torch.int64)
    out[ids.reshape(-1)] = ans.reshape(-1)
    if bool((out < 0).any()):
        raise ValueError("a trained fact is missing from the panel")
    return out


def swap_permutation(data: StudyData, facts: int, seed: int) -> "Tensor":
    """The derangement pi of the cell's facts, seeded (base + 50 / 51 / 52 for the 2,048 / 8,192 / 32,768-fact sets)."""
    return derangement(fact_answers(data, facts), seed)


def binary_entropy(p: float) -> float:
    return 0.0 if p <= 0.0 or p >= 1.0 else float(-(p * math.log2(p) + (1 - p) * math.log2(1 - p)))


def information_bits(a_use_count: int, facts: int) -> float:
    """i = 5 - h2(e) - e log2(31), e = 1 - a_use; 0 when the count is at or below the upper end of the chance interval (G2)."""
    if a_use_count <= p9core.chance_interval(facts, p9core.G2_TESTS_PRIMARY).high:
        return 0.0
    e = 1.0 - a_use_count / facts
    return 5.0 - binary_entropy(e) - e * math.log2(31)


@torch.no_grad()
def read_swap(model: Any, data: StudyData, facts: int, panel: str, perm: "Tensor") -> dict[str, Any]:
    """The read swap of one panel (see the module docstring). ``perm`` is the cell's derangement of its facts."""
    stream = stream_for(data, facts, core.PANEL_STREAM[panel])
    keep = (stream.fact_ids < facts).all(dim=1)
    tokens = stream.tokens[keep][:, : core.INPUT_LENGTH].contiguous()
    ids = stream.fact_ids[keep]
    answers = stream.answer_targets()[keep]
    was = model.training
    model.eval()
    try:
        hs: list[Tensor] = []
        deltas: list[Tensor] = []
        own: list[Tensor] = []
        table = torch.zeros(facts, core.HIDDEN_WIDTH)
        for start in range(0, tokens.shape[0], SWAP_CHUNK):
            tok = tokens[start : start + SWAP_CHUNK]
            h = model.embed_block0(tok)
            delta = model.memory_delta(h, model.select(h, tok))
            own.append(model.finish(h, delta)[:, SITES])
            table[ids[start : start + SWAP_CHUNK].reshape(-1)] = delta[:, SITES].reshape(-1, core.HIDDEN_WIDTH)
            hs.append(h)
            deltas.append(delta)
        swapped_table = table[perm]
        swapped_logits: list[Tensor] = []
        for chunk, (h, delta) in enumerate(zip(hs, deltas, strict=True)):
            rows = ids[chunk * SWAP_CHUNK : chunk * SWAP_CHUNK + h.shape[0]]
            out = torch.zeros(h.shape[0], SITES.numel(), 256)
            for r in range(SITES.numel()):
                replaced = delta.clone()
                replaced[:, SITES[r]] = swapped_table[rows[:, r]]
                out[:, r] = model.finish(h, replaced)[:, SITES[r]]
            swapped_logits.append(out)
    finally:
        model.train(was)
    own_logits = torch.cat(own).reshape(-1, 256)
    swapped = torch.cat(swapped_logits).reshape(-1, 256)
    target = answers.reshape(-1)
    correct = p9core.score_answer_sites(own_logits, target).correct
    inside = swapped.float()[:, ALPHABET_INDEX]
    rows_index = torch.arange(inside.shape[0])
    still_answer = inside[rows_index, target] >= inside.max(dim=-1).values  # the answer is among the arg-max symbols (ties on the conservative side)
    used = correct & ~still_answer
    n, n_correct, n_used = int(target.numel()), int(correct.sum()), int(used.sum())
    return {
        "facts": n, "correct": n_correct, "a_use_count": n_used, "swapped_still_answer": int(still_answer.sum()),
        "accuracy": n_correct / n, "a_use": n_used / n, "a_use_of_correct": (n_used / n_correct) if n_correct else math.nan, "information_bits": information_bits(n_used, n),
    }  # fmt: skip


def check_swap_accuracy(record: dict[str, Any]) -> None:
    """Condition 6 compares a_use with the panel accuracy of a separate evaluation pass: the read swap's own accuracy must equal it on both panels (a defect otherwise; the audit's m7)."""
    for p in core.PANELS:
        if abs(float(record["read_swap"][p]["accuracy"]) - float(record["panels"][p]["accuracy"])) > 1e-9:
            raise ValueError(f"read-swap accuracy differs from the panel accuracy on Panel {p}: the two evaluation passes disagree")


@torch.no_grad()
def answer_site_auc(model: Any, data: StudyData, facts: int, max_contexts: int = 512, chunk: int = 16) -> dict[str, Any]:
    """Descriptive only (ADR-0020 section 5.2, last bullet; no training, no rule): the area under the ROC curve of max_s a_s (the largest cosine between the position's unit query and any key) for separating
    the answer sites (8 per context) from the other 55 positions, on the first ``max_contexts`` Panel A contexts, with the WX query evaluated at every position. Ties count one half."""
    stream = stream_for(data, facts, core.PANEL_STREAM["A"])
    keep = (stream.fact_ids < facts).all(dim=1)
    tokens = stream.tokens[keep][:max_contexts, : core.INPUT_LENGTH].contiguous()
    positions = torch.arange(core.INPUT_LENGTH)
    is_site = torch.zeros(core.INPUT_LENGTH, dtype=torch.bool)
    is_site[SITES] = True
    was = model.training
    model.eval()
    sites: list[Tensor] = []
    others: list[Tensor] = []
    try:
        keys = torch.nn.functional.normalize(model.addition.keys, dim=-1)
        for start in range(0, tokens.shape[0], chunk):
            tok = tokens[start : start + chunk]
            h = model.embed_block0(tok)
            q = torch.nn.functional.normalize(model.addition.window_z(h, positions), dim=-1).reshape(-1, core.KEY_WIDTH)
            top = (q @ keys.T).max(dim=-1).values.reshape(tok.shape[0], -1)
            sites.append(top[:, is_site].reshape(-1))
            others.append(top[:, ~is_site].reshape(-1))
    finally:
        model.train(was)
    pos, neg = torch.cat(sites), torch.cat(others)
    order = neg.sort().values
    lt = torch.searchsorted(order, pos, right=False).double()
    le = torch.searchsorted(order, pos, right=True).double()
    auc = float(((lt + le) / 2).sum() / (pos.numel() * neg.numel()))
    return {"auc": auc, "answer_sites": int(pos.numel()), "other_positions": int(neg.numel()), "contexts": int(tokens.shape[0]), "note": "descriptive only: the memory is told the answer position; no label says an interface finds where to read"}


def evaluate_readout(cell: core.Cell, model: Any, data: StudyData, facts: int, update: int, *, frozen_backbone: "Backbone", rows: "Tensor", target_seed: int, swap_seed: int, frozen_loss: float | None = None, chunked: bool = True) -> dict[str, Any]:
    """The eval record of one cell at one readout (``model`` already holds the snapshot): ``studies.p9ii``'s record with S0's envelope, plus the read swap of both panels for a
    cell with a memory read."""
    record = p9iieval.evaluate_readout(cell.p9ii_cell(), model, data, facts, update, frozen_backbone=frozen_backbone, rows=rows, target_seed=target_seed, frozen_loss=frozen_loss, chunked=chunked)
    record.update(core.envelope("eval"))
    record.update({"label": cell.label, "arm": cell.arm, "block": cell.block, "celltype": cell.celltype, "draw": cell.draw, "seed_index": cell.seed_index, "identity": core.code_identity(), "environment": core.environment()})
    record.pop("stage", None)
    if has_read(cell.arm):
        perm = swap_permutation(data, facts, swap_seed)
        with p9iieval.eval_chunking(model, p9iieval.EVAL_CHUNK_ELEMENTS if chunked else 1 << 40):  # the swap's memory is bounded as the evaluation's is (audit M2: the 65,536-slot evaluation peak)
            record["read_swap"] = {p: read_swap(model, data, facts, p, perm) for p in core.PANELS}
        check_swap_accuracy(record)
        record["read_swap"]["note"] = "a_use = facts answered correctly whose swapped prediction is not their answer, over all facts; condition 6 compares it with 0.95 x accuracy (ADR-0020 section 8.2)"
    if core.is_wx(cell.arm):
        record["answer_site_auc"] = answer_site_auc(model, data, facts)
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
    target_seed: int,
    swap_seed: int,
    out_dir: Path | None = None,
    extra: dict[str, Any] | None = None,
    require_train_record: bool = False,
) -> list[Path]:
    """Evaluate the snapshots at ``readouts`` of a trained cell and write one ``eval`` record each (never over an existing one). The snapshot's model file must hash to the value
    recorded in ``train.json`` (required when ``require_train_record``)."""
    written: list[Path] = []
    folder = out_dir or core.cell_dir(run_dir, cell.label)
    train_json = folder / "train.json"
    recorded: dict[str, str] | None = None
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
        record = evaluate_readout(cell, model, data, facts, update, frozen_backbone=backbone, rows=rows, target_seed=target_seed, swap_seed=swap_seed, frozen_loss=frozen_loss)
        record.update(extra or {})
        path = folder / "eval" / core.snapshot_stem(update) / "eval.json"
        if path.exists():
            raise FileExistsError(path)
        core.write_record(path, core.jsonable(record))
        written.append(path)
    return written
