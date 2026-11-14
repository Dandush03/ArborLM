# ruff: noqa: E501
"""P9I evaluation (ADR-0017 Part I, section I.5): accuracy on Panels A and B (primary) and the H1, H2 and
mixed-cluster streams (secondary), interface efficiency inputs, I_acc, the Sigma-renormalized log-loss gain
and the 256-way loss (descriptive), query diagnostics, value permutation and disabling, minimal supports
restricted to the answer-site read, the unseen-fact control with the LEAKAGE flag, the no-memory baseline,
exact retrieval, gate G2, and, for the BB arms, the backbone's next-byte loss on its own corpus rows
before and after training.

Everything that is a rule input uses accuracy: the most probable alphabet symbol, ties wrong
(``studies.p9.core.score_answer_sites``). Interface efficiency eta = accuracy(arm) / accuracy(R1) is a
ratio of two records and is formed in ``classes``, not here.

P9's cached evaluation (``build_cache``, ``logits_with``, ``permute_values``, ``minimal_supports``) is
imported and called on ``P9IModel`` (a subclass of ``P9Model``). Definitions fixed here (reported):

* "Mean cosine between queries of different facts" = the mean over all ordered pairs of distinct trained
  facts of Panel A (one query per fact); for unit queries this equals ``(|sum q|^2 - n) / (n (n - 1))``.
* "Share of facts whose nearest other query is closer than 0.9" is read as: the largest cosine to any
  other fact's query exceeds 0.9 (cosine, not distance); settled by ADR-0017 section 15.4 item 4.
* Attention weight on the five identifier positions: for A4, A4E the interface layer's weights, for the
  BB arms block 0 of the (trained) backbone; per head, mean over trained facts of the answer sites'
  weight on positions 8r+1..8r+5 of their own record (``identifier_mass``), plus the same mass for the
  uniform attention a head would give (``uniform_mass`` = 5 / (8 r + 7)) averaged over the same sites.
* The no-memory probability used by the minimal-support threshold is the arm's own memory-disabled
  probability (identical to the frozen baseline for every arm that trains no backbone parameter).
* The backbone's next-byte loss is measured with nothing added, on the rows of the corpus the backbones
  were trained on (first 2,048 rows of 65 bytes: inputs 0..63, targets 1..64), as 256-way cross-entropy
  averaged over all 64 targets of each row.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import torch
from torch.nn import functional as F

from arborlm.io import file_sha256
from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9.core import AnswerScores
from studies.p9.data import Stream, StudyData, neighbour_flags, restrict_stream
from studies.p9.evaluate import (
    ReadCache,
    build_cache,
    leakage_flag,
    logits_with,
    minimal_supports,
    permute_values,
    score_cache,
)

from . import core
from .model import P9IModel, build_model, identifier_attention_mass
from .train import load_snapshot

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

VOCAB = 256
STREAM_OF = {"A": "panel_a", "B": "panel_b", "H1": "h1", "H2": "h2", "MIXED": "mixed"}
SECONDARY = ("H1", "H2", "MIXED")
NEXT_BYTE_BATCH = 256
QUERY_CHUNK = 2048


def stream_for(data: StudyData, facts: int, name: str) -> Stream:
    """Stream ``name`` restricted to a cell's ``facts`` trained facts (contexts of unseen controls kept)."""
    return restrict_stream(data.streams[name], data.facts, facts)


def _inside(correct: int, n: int) -> bool:
    """Inside the G2 interval for ``n`` facts: what every rule means by "chance"."""
    interval = p9core.chance_interval(n, p9core.G2_TESTS_PRIMARY)
    return interval.low <= correct <= interval.high


def _accuracy(scores: AnswerScores, mask: "Tensor") -> float:
    return float(scores.correct[mask].float().mean()) if bool(mask.any()) else float("nan")


def _score_logits(logits: "Tensor", answer: "Tensor") -> AnswerScores:
    return p9core.score_answer_sites(logits.reshape(-1, VOCAB), answer)


def _finite(value: Any) -> Any:
    """Records are JSON without NaN: every non-finite float (an empty class, one fact) becomes None."""
    if isinstance(value, float):
        return value if value == value and value not in (float("inf"), float("-inf")) else None
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_finite(v) for v in value]
    return value


# --- descriptive measures of one scored stream ---------------------------------------------------------------------
def descriptive(scores: AnswerScores, logits: "Tensor", mask: "Tensor") -> dict[str, float]:
    """Sigma-renormalized log-loss gain (sum over facts of 5 + log2 p_f, can be negative), mean 256-way
    cross-entropy at the answer sites (nats), mean probability mass inside the alphabet."""
    p = scores.p_correct[mask].clamp_min(1e-30)
    gain = float((p9core.BITS_PER_FACT + torch.log2(p)).sum())
    target = core.ALPHABET_BASE + scores.answer[mask]
    flat = logits.reshape(-1, VOCAB)[mask]
    loss256 = float(F.cross_entropy(flat, target)) if bool(mask.any()) else float("nan")
    return {
        "logloss_gain_bits": gain,
        "loss_256_nats": loss256,
        "mass_in_alphabet": float(scores.mass_sigma[mask].mean()) if bool(mask.any()) else float("nan"),
    }


def information(correct: int, facts: int) -> dict[str, float]:
    """I_acc in bits (Fano bound, floored at chance by the G2 interval) and per fact."""
    bits = p9core.information_bits(correct, facts) if facts > 0 else 0.0
    return {"i_acc_bits": bits, "i_acc_bits_per_fact": bits / facts if facts else 0.0}


# --- query diagnostics --------------------------------------------------------------------------------------------------
def query_statistics(queries: "Tensor") -> dict[str, float]:
    """``queries [n, d]`` unit vectors, one per fact. Mean cosine between different facts (exact, from the
    sum) and the share of facts whose largest cosine to another fact's query exceeds 0.9 (chunked; the
    diagonal is excluded)."""
    n = int(queries.shape[0])
    if n < 2:
        return {"facts": n, "mean_cosine_different": float("nan"), "share_nearest_above_0_9": float("nan")}
    total = queries.to(torch.float64).sum(0)
    mean_cos = float((total @ total - n) / (n * (n - 1)))
    near = 0
    for start in range(0, n, QUERY_CHUNK):
        block = queries[start : start + QUERY_CHUNK]
        sims = block @ queries.T
        rows = torch.arange(block.shape[0])
        sims[rows, start + rows] = -2.0
        near += int((sims.max(dim=1).values > core.NEAREST_QUERY_COSINE).sum())
    return {"facts": n, "mean_cosine_different": mean_cos, "share_nearest_above_0_9": near / n}


def _queries_and_attention(
    model: P9IModel, cache: ReadCache, trained: "Tensor"
) -> tuple["Tensor | None", dict[str, Any] | None]:
    """Unit queries of the trained facts (answer-site order) and the identifier attention mass."""
    tokens, h_pre = cache.tokens[:, : core.INPUT_LENGTH], cache.h_pre
    q_parts: list[Tensor] = []
    mass_parts: list[Tensor] = []
    have_q = have_a = False
    with torch.no_grad():
        for start in range(0, tokens.shape[0], 256):
            tok, h = tokens[start : start + 256].contiguous(), h_pre[start : start + 256]
            q = model.answer_queries(h, tok)
            if q is not None:
                have_q = True
                q_parts.append(q.reshape(-1, q.shape[-1]))
            w = model.answer_attention(h, tok)
            if w is not None:
                have_a = True
                mass_parts.append(identifier_attention_mass(w))  # [b, 4, 8]
    queries = torch.cat(q_parts)[trained] if have_q else None
    attention: dict[str, Any] | None = None
    if have_a:
        mass = torch.cat(mass_parts)  # [C, 4, 8]
        per_site = mass.permute(0, 2, 1).reshape(-1, mass.shape[1])[trained]  # [facts, 4]
        sites = torch.tensor(core.ANSWER_SITE_POSITIONS, dtype=torch.float64)
        uniform = float((5.0 / (sites + 1.0)).mean())  # a uniform head over the causal prefix of 8r+7 positions
        attention = {
            "identifier_mass_per_head": [float(x) for x in per_site.mean(0)],
            "identifier_mass_mean": float(per_site.mean()),
            "uniform_mass": uniform,
        }
    return queries, attention


# --- one stream ----------------------------------------------------------------------------------------------------------------
def evaluate_stream(
    model: P9IModel,
    data: StudyData,
    facts: int,
    name: str,
    *,
    primary: bool,
    supports: bool = True,
    batch_contexts: int = 64,
) -> dict[str, Any]:
    """Accuracy and, for the primary panels, every other measurement of one stream (trained facts)."""
    stream = stream_for(data, facts, name)
    cache = build_cache(model, stream, batch_contexts=batch_contexts)
    answer = stream.answer_targets().reshape(-1)
    scores = score_cache(cache, answer)
    ids = stream.fact_ids.reshape(-1)
    trained = ids < facts
    unseen = ids >= data.facts.trained
    n = int(trained.sum())
    correct = int(scores.correct[trained].sum())
    record: dict[str, Any] = {
        "stream": name,
        "sha256": stream.sha256,
        "facts": n,
        "correct": correct,
        "accuracy": correct / n if n else float("nan"),
        "chance_interval": list(p9core.chance_interval(n, p9core.G2_TESTS_PRIMARY)[2:4]) if n else None,
    }
    if bool(unseen.any()):
        uc, un = int(scores.correct[unseen].sum()), int(unseen.sum())
        record.update(unseen_correct=uc, unseen_facts=un, unseen_accuracy=uc / un, leakage=leakage_flag(uc, un))
    if not primary:
        return record
    record.update(information(correct, n))
    record.update(descriptive(scores, cache.logits_answer, trained))
    flags = neighbour_flags(data.facts, among=facts)[ids.clamp_max(data.facts.size - 1)] & trained
    record["accuracy_with_neighbour"] = _accuracy(scores, flags & trained)
    record["accuracy_without_neighbour"] = _accuracy(scores, ~flags & trained)
    # memory dependence: value permutation and disabling
    off_logits = logits_with(model, cache, disabled=True, batch_contexts=batch_contexts)
    off = _score_logits(off_logits, answer)
    record["disabled_correct"] = int(off.correct[trained].sum())
    record["disabled_accuracy"] = _accuracy(off, trained)
    record["disabled_at_chance"] = _inside(record["disabled_correct"], n)
    table = getattr(model.addition, "values", None)
    if table is not None:
        permuted = permute_values(model, 977)
        perm_scores = _score_logits(logits_with(model, cache, values=permuted, batch_contexts=batch_contexts), answer)
        record["permuted_correct"] = int(perm_scores.correct[trained].sum())
        record["permuted_accuracy"] = _accuracy(perm_scores, trained)
        record["permuted_at_chance"] = _inside(record["permuted_correct"], n)
        record["memory_dependence_chance"] = bool(record["permuted_at_chance"] and record["disabled_at_chance"])
    else:
        record["permuted_accuracy"] = None
        record["memory_dependence_chance"] = bool(record["disabled_at_chance"])
    if model.arm in core.MEMORY_ARMS or model.arm in core.BB_ARMS:
        queries, attention = _queries_and_attention(model, cache, trained)
        if queries is not None:
            record["query"] = query_statistics(queries)
        if attention is not None:
            record["attention"] = attention
    if supports and cache.selection is not None and model.arm in core.MEMORY_ARMS:
        result = minimal_supports(model, cache, off, scores, facts=trained)
        right = scores.correct & trained
        has = result.has_support & right
        record["support"] = {
            "correct_facts": int(right.sum()),
            "with_support": int(has.sum()),
            "share_with_support": float(has.sum()) / max(1, int(right.sum())),
            "mean_length": float(result.length[has].float().mean()) if bool(has.any()) else 0.0,
            "useful_slots": len(result.useful),
            "site_read_removed_stays_correct_share": float(result.removing_site_read_stays_correct[right].float().mean()) if bool(right.any()) else 0.0,
        }
    if cache.selection is not None:
        chosen = cache.selection.selected[:, :, :].reshape(-1)
        chosen = chosen[chosen >= 0]
        record["distinct_selected_slots"] = int(torch.unique(chosen).numel())
    return record


# --- the backbone's next-byte loss (BB arms) ------------------------------------------------------------------------------------
def next_byte_loss(backbone: "Backbone", rows: "Tensor") -> float:
    """Mean 256-way cross-entropy of ``backbone`` with nothing added on ``rows [R, 65] int64`` (inputs 0..63,
    targets 1..64), averaged over all targets."""
    total, count = 0.0, 0
    with torch.no_grad():
        for start in range(0, rows.shape[0], NEXT_BYTE_BATCH):
            chunk = rows[start : start + NEXT_BYTE_BATCH]
            tokens = chunk[:, : core.CONTEXT_BYTES].contiguous()
            logits = controls.logits_from_hidden(backbone, controls.insertion_hidden(backbone, tokens))
            target = chunk[:, 1 : core.CONTEXT_BYTES + 1]
            total += float(F.cross_entropy(logits.reshape(-1, VOCAB), target.reshape(-1), reduction="sum"))
            count += int(target.numel())
    return total / count


def corpus_rows(corpus: bytes) -> "Tensor":
    """``[R, 65] int64`` rows of the backbone's training corpus (``p9core.load_trained_corpus``)."""
    raw = torch.frombuffer(bytearray(corpus), dtype=torch.uint8).to(torch.int64)
    return raw.reshape(-1, p9core.CORPUS_ROW_BYTES)


def language_modelling(model: P9IModel, frozen: "Backbone", rows: "Tensor") -> dict[str, float | bool]:
    """Next-byte loss before (the frozen backbone) and after (the model's own backbone), and the section
    I.8.2 flag input: the relative rise."""
    before = next_byte_loss(frozen, rows)
    after = next_byte_loss(model.backbone, rows)
    rise = (after - before) / before
    return {"before_nats": before, "after_nats": after, "relative_rise": rise, "degraded": bool(rise > core.LM_DEGRADED_RELATIVE)}


# --- one snapshot ---------------------------------------------------------------------------------------------------------------
def evaluate_snapshot(
    cell: core.Cell,
    model: P9IModel,
    data: StudyData,
    facts: int,
    update: int,
    *,
    frozen_backbone: "Backbone | None" = None,
    rows: "Tensor | None" = None,
    secondary: bool = True,
    supports: bool = True,
) -> dict[str, Any]:
    """The eval record of one cell at one snapshot (``model`` already holds the snapshot)."""
    was_training = model.training
    model.eval()
    try:
        record: dict[str, Any] = {
            **core.envelope("eval"),
            "label": cell.label,
            "arm": cell.arm,
            "slots": cell.slots,
            "parent": list(cell.parent),
            "seed": cell.seed,
            "update": update,
            "facts": facts,
            "identity": dict(core.code_identity()),
            "panels": {},
            "secondary": {},
        }
        for panel in core.PANELS:
            record["panels"][panel] = evaluate_stream(model, data, facts, core.PANEL_STREAM[panel], primary=True, supports=supports)
        if secondary:
            for name in SECONDARY:
                record["secondary"][name] = evaluate_stream(model, data, facts, STREAM_OF[name], primary=False)
        if cell.arm in core.BB_ARMS and frozen_backbone is not None and rows is not None:
            record["language_modelling"] = language_modelling(model, frozen_backbone, rows)
    finally:
        model.train(was_training)
    return _finite(record)  # type: ignore[no-any-return]


def evaluate_cell(
    cell: core.Cell,
    run_dir: Path,
    data: StudyData,
    backbone: "Backbone",
    *,
    facts: int,
    updates: list[int],
    init_seed: int,
    r1_seed: int,
    fact_lut: "Tensor | None" = None,
    rows: "Tensor | None" = None,
    secondary: bool = True,
    supports: bool = True,
    out_dir: Path | None = None,
    extra: dict[str, Any] | None = None,
    require_train_record: bool = False,
) -> list[Path]:
    """Evaluate the snapshots ``updates`` of a trained cell and write one ``eval`` record each (never over
    an existing one). Returns the written paths. The snapshot's model file must hash to the value recorded
    in ``train.json`` (required when ``require_train_record``); ``extra`` is added to the record."""
    written: list[Path] = []
    cell_dir = out_dir or core.cell_dir(run_dir, cell.label)
    train_json = cell_dir / "train.json"
    if train_json.is_file():
        recorded = core.read_record(train_json, "train")["snapshot_sha256"]
    elif require_train_record:
        raise ValueError(f"no train record at {train_json}: the snapshot hash cannot be verified")
    else:
        recorded = None
    for update in updates:
        model_file = cell_dir / "snapshots" / core.snapshot_stem(update) / "model.pt"
        if recorded is not None and file_sha256(model_file) != recorded.get(str(update)):
            raise ValueError(f"snapshot {model_file} does not match the hash recorded in train.json")
        model = build_model(cell.arm, cell.slots, init_seed, backbone, fact_lut=fact_lut, r1_seed=r1_seed, seed_rng=False)
        load_snapshot(cell_dir / "snapshots" / core.snapshot_stem(update), model)
        record = evaluate_snapshot(cell, model, data, facts, update, frozen_backbone=backbone, rows=rows, secondary=secondary, supports=supports)
        record.update(extra or {})
        path = cell_dir / "eval" / core.snapshot_stem(update) / "eval.json"
        if path.exists():
            raise FileExistsError(path)
        core.write_record(path, record)
        written.append(path)
    return written


# --- controls: no-memory baseline, exact retrieval, G2 -------------------------------------------------------------------------
def no_memory_counts(backbone: "Backbone", data: StudyData, panel_stream: str, fact_counts: list[int]) -> dict[str, dict[str, int]]:
    """``{"<F>": {correct, facts}, ..., "unseen": ...}`` for one primary panel: the no-memory baseline on
    the F-fact sets and the unseen set (ADR section 8.1 G2)."""
    out: dict[str, dict[str, int]] = {}
    full = data.streams[panel_stream]
    for facts in fact_counts:
        stream = restrict_stream(full, data.facts, facts)
        scores = controls.evaluate_no_memory(backbone, data.facts, stream)
        ids = stream.fact_ids.reshape(-1)
        mask = ids < facts
        out[str(facts)] = {"correct": int(scores.correct[mask].sum()), "facts": int(mask.sum())}
        if facts == fact_counts[-1]:
            unseen = ids >= data.facts.trained
            out["unseen"] = {"correct": int(scores.correct[unseen].sum()), "facts": int(unseen.sum())}
    return out


def exact_retrieval_accuracy(data: StudyData, fact_counts: list[int]) -> dict[str, float]:
    """Exact retrieval (dictionary of the trained facts) on Panel A restricted to each fact count."""
    out: dict[str, float] = {}
    for facts in fact_counts:
        stream = restrict_stream(data.streams["panel_a"], data.facts, facts)
        scores = controls.exact_retrieval(data.facts, stream, torch.arange(data.facts.trained))
        trained = stream.fact_ids.reshape(-1) < facts
        out[str(facts)] = float(scores.correct[trained].float().mean())
    return out


def controls_record(data: StudyData, backbones: dict[tuple[int, int], "Backbone"], fact_counts: list[int]) -> dict[str, Any]:
    """The no-memory baseline per parent and panel, exact retrieval, and the G2 family on the primary
    parent (8 tests: three fact counts and the unseen set, per panel, as ADR section 8.1)."""
    primary = backbones[core.PRIMARY_PARENT]
    no_memory = {p: no_memory_counts(primary, data, s, fact_counts) for p, s in core.PANEL_STREAM.items()}
    counts = {f"{p}/{name}": (v["correct"], v["facts"]) for p, per in no_memory.items() for name, v in per.items()}
    g2 = controls.g2_report(counts, p9core.G2_TESTS_PRIMARY)
    replicate = backbones.get(core.REPLICATE_PARENT)
    return {
        "fact_counts": list(fact_counts),
        "no_memory": no_memory,
        "no_memory_replicate": None if replicate is None else {p: no_memory_counts(replicate, data, s, fact_counts) for p, s in core.PANEL_STREAM.items()},
        "exact_accuracy": exact_retrieval_accuracy(data, fact_counts),
        "g2": dict(g2),
    }

