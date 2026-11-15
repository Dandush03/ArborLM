# ruff: noqa: E501
"""P10S1 evaluation at a snapshot (ADR-0021 sections 7.1 to 7.4): accuracy and useful retention on Panels A and B, the held-out template panels H1 and H2, the unseen-fact
control, the ablations (memory disabled, value shuffle, address swap), slot dropout and value noise (robustness), minimal supports, utilization and separability, the counted
work per query, F-OQ-IVF (F-OQ's trained keys read through the index), and the baselines that need no training (KNN-W, KNN-W-IVF, DICT).

A fact is usefully retained when (1) the model with its memory gives the fact's answer and (2) when the fact's read is replaced by the read of another fact pi(f) (a seeded
derangement of the cell's facts with a different answer symbol) it no longer gives that answer. The address swap replaces the identifier bytes the oracle reads (positions 8r + 1
to 8r + 4 of the record) by those of pi(f); the backbone still sees the original tokens. ``a_use`` is the share of usefully retained facts; the records hold counts, from which
``classes`` computes i, i*, I_use and the dependence gate.

Every record is a count (correct, n): nothing here applies a threshold. A rule never reads a raw accuracy except through ``classes``.
"""

import contextlib
import copy
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import torch
from torch.nn import functional as F

from arborlm.io import file_sha256
from studies.p9 import controls
from studies.p9 import core as p9core
from studies.p9.data import Stream, StudyData, restrict_stream
from studies.p9.evaluate import build_cache, logits_with, minimal_supports, score_cache

from . import core, index
from .model import P10S1Model, build_model, derangement, g5_check, swapped_tokens
from .train import fact_lut_for, load_model_state

if TYPE_CHECKING:
    from torch import Tensor

    from arborlm.p4_model import Backbone

SITES = torch.tensor(core.ANSWER_SITE_POSITIONS, dtype=torch.int64)
BATCH_CONTEXTS = 64
EVAL_CHUNK_ELEMENTS = 1 << 20  # score elements of one block of queries during evaluation (P9's default is 1 << 24): bounds the evaluation peak at 65,536 slots
NEXT_BYTE_ROWS = 128
SECONDARY = core.SECONDARY_STREAMS


@contextlib.contextmanager
def eval_chunking(model: P10S1Model, chunk_elements: int = EVAL_CHUNK_ELEMENTS) -> Iterator[None]:
    """Evaluate the memory in smaller blocks of queries (the result is the same: P9's selection already works in row blocks)."""
    memory = model.addition
    old = getattr(memory, "chunk_elements", None)
    if old is not None:
        memory.chunk_elements = min(int(old), chunk_elements)
    try:
        yield
    finally:
        if old is not None:
            memory.chunk_elements = old


def stream_for(data: StudyData, facts: int, name: str) -> Stream:
    """Stream ``name`` restricted to a cell's ``facts`` trained facts (contexts of unseen controls kept)."""
    return restrict_stream(data.streams[name], data.facts, facts)


def site_logits(model: P10S1Model, h_pre: "Tensor", delta: "Tensor") -> "Tensor":
    """``[B, 8, 256]`` answer-site logits of ``P9Model.finish`` (the same operations; the output projection applied to the eight answer sites only)."""
    bb = model.backbone
    t = h_pre.shape[1]
    h = cast("Tensor", bb.blocks[1](h_pre + delta, bb.mask[:t, :t]))
    return F.linear(bb.final_norm(h[:, SITES]), bb.token.weight)


# --- perturbed value tables (sections 5.2 item 3, 7.1) ------------------------------------------------------------------------------
def shuffled_values(model: P10S1Model, seed: int) -> "Tensor":
    """The value table permuted over slots by a seeded cyclic derangement (P9's ``permute_values``): no slot keeps its own row."""
    from studies.p9.evaluate import permute_values

    return permute_values(model, seed)


def dropped_values(table: "Tensor", fraction: float, seed: int) -> "Tensor":
    """The value table with a seeded random ``fraction`` of rows zeroed (the same uniform draw for every fraction, so the masks are nested)."""
    gen = torch.Generator().manual_seed(seed)
    drop = torch.rand(table.shape[0], generator=gen) < fraction
    out = table.detach().clone()
    out[drop] = 0.0
    return out


def noisy_values(table: "Tensor", level: float, seed: int) -> "Tensor":
    """The value table plus Gaussian noise of ``level`` times each row's RMS (the same normal draw for every level)."""
    gen = torch.Generator().manual_seed(seed)
    noise = torch.randn(table.shape, generator=gen)
    rms = table.detach().pow(2).mean(dim=1, keepdim=True).sqrt()
    return table.detach() + level * rms * noise


def robustness_tables(model: P10S1Model, seeds: p9core.SeedSet) -> "dict[str, Tensor]":
    """Name -> value table: zeroed 5% and 20% of rows and noise 0.1 and 0.5 of the row RMS, each under three seeded masks (seeds base + 52 .. 54 for the masks, base + 55 .. 57
    for the noise)."""
    table = cast("Tensor", model.addition.values)
    out: dict[str, Tensor] = {}
    for k in range(core.ROBUSTNESS_MASKS):
        for f in core.ROBUSTNESS_DROPOUT:
            out[f"drop{int(round(100 * f))}_{k}"] = dropped_values(table, f, core.mask_seed(seeds, 2 + k))
        for lv in core.ROBUSTNESS_NOISE:
            out[f"noise{lv:g}_{k}"] = noisy_values(table, lv, core.mask_seed(seeds, 5 + k))
    return out


# --- one panel ------------------------------------------------------------------------------------------------------------------
@torch.no_grad()
def panel_counts(
    model: P10S1Model,
    data: StudyData,
    facts: int,
    stream: Stream,
    *,
    pi: "Tensor | None",
    tables: "dict[str, Tensor] | None" = None,
    ablate: bool = True,
    batch_contexts: int = BATCH_CONTEXTS,
) -> dict[str, Any]:
    """Counts over one stream: ``n`` trained answer sites, ``correct`` (the model with its memory), ``disabled_correct``, ``swap_correct`` and ``useful`` (correct and wrong
    under the swap) where ``ablate``; ``tables_correct[name]`` for every perturbed value table in ``tables`` (the value shuffle among them); the unseen-control counts."""
    answers = stream.answer_targets()
    ids_all = stream.fact_ids
    trained_total = data.facts.trained
    out: dict[str, Any] = {"n": 0, "correct": 0, "unseen_n": 0, "unseen_correct": 0}
    if ablate:
        out.update(disabled_correct=0, swap_correct=0, useful=0)
    if tables:
        out["tables_correct"] = dict.fromkeys(tables, 0)
    was = model.training
    model.eval()
    try:
        for start in range(0, stream.tokens.shape[0], batch_contexts):
            tok = stream.tokens[start : start + batch_contexts, : core.INPUT_LENGTH].contiguous()
            ids = ids_all[start : start + batch_contexts]
            answer = answers[start : start + batch_contexts].reshape(-1)
            trained = (ids < facts).reshape(-1)
            unseen = (ids >= trained_total).reshape(-1)
            h = model.embed_block0(tok)
            read = model.select(h, tok)
            main = p9core.score_answer_sites(site_logits(model, h, model.memory_delta(h, read)).reshape(-1, 256), answer).correct
            out["n"] += int(trained.sum())
            out["correct"] += int(main[trained].sum())
            out["unseen_n"] += int(unseen.sum())
            out["unseen_correct"] += int(main[unseen].sum())
            if ablate:
                off = p9core.score_answer_sites(site_logits(model, h, model.memory_delta(h, None, disabled=True)).reshape(-1, 256), answer).correct
                out["disabled_correct"] += int(off[trained].sum())
                if pi is None:
                    raise ValueError("the address swap needs the derangement")
                tok_sw = swapped_tokens(tok, ids, pi, data.facts.ident, facts)
                read_sw = model.select(h, tok_sw)
                sw = p9core.score_answer_sites(site_logits(model, h, model.memory_delta(h, read_sw)).reshape(-1, 256), answer).correct
                out["swap_correct"] += int(sw[trained].sum())
                out["useful"] += int((main & ~sw)[trained].sum())
            for name, table in (tables or {}).items():
                c = p9core.score_answer_sites(site_logits(model, h, model.memory_delta(h, read, values=table)).reshape(-1, 256), answer).correct
                out["tables_correct"][name] += int(c[trained].sum())
    finally:
        model.train(was)
    return out


def _deranged(data: StudyData, facts: int, seed: int) -> "Tensor":
    return derangement(data.facts.answer[:facts], seed)


# --- supports, utilization, separability (section 7.3) --------------------------------------------------------------------------------
def fact_codes(model: P10S1Model, data: StudyData, facts: int) -> "Tensor":
    """``[facts, 16]`` the oracle codes of the cell's facts (F-OQ, T-OQ, D-OQ: the query tensor)."""
    from studies.p9.data import encode_identifiers

    ident = encode_identifiers(data.facts.ident[:facts])
    codes = model.addition.codes if hasattr(model.addition, "codes") else None
    if codes is not None:
        return cast("Tensor", codes.of_codes(ident))
    from .model import OracleCodes

    return OracleCodes(model.r1_seed).of_codes(ident)


def fact_slots(model: P10S1Model, data: StudyData, facts: int, codes: "Tensor | None") -> "Tensor":
    """``[facts, 8]`` (R2: ``[facts, 1]``) the slots a fact reads, by fact id: top-8 of the oracle query (F-OQ, T-OQ), the hashed slots (H8) or the dedicated slot (R2)."""
    from studies.p9.data import encode_identifiers

    ident = encode_identifiers(data.facts.ident[:facts])
    mem = model.addition
    if model.arm == "H8":
        return cast("Tensor", mem.slot_table(ident))
    if model.arm == "R2":
        return cast("Tensor", mem.fact_lut[ident][:, None])
    assert codes is not None
    parts = [mem.select_codes(codes[s : s + 2048])[0] for s in range(0, facts, 2048)]
    return torch.cat(parts)


def tree_recall(model: P10S1Model, codes: "Tensor") -> float:
    """T-OQ: the share of the exhaustive top-8 (all N keys, the same query) whose branch the router visited."""
    mem = model.addition
    keys = F.normalize(mem.keys, dim=-1)
    hit = total = 0
    for s in range(0, codes.shape[0], 1024):
        q = codes[s : s + 1024]
        _, _, branches, _ = mem._top_tree(q)
        exhaustive = (q @ keys.T).topk(core.TOP, dim=-1).indices
        in_visited = (exhaustive[:, :, None] // mem.spec.per_branch == branches[:, None, :]).any(-1)
        hit += int(in_visited.sum())
        total += int(in_visited.numel())
    return hit / max(1, total)


def separability(model: P10S1Model, data: StudyData, facts: int, slots_of_fact: "Tensor", codes: "Tensor | None") -> dict[str, Any]:
    """Nearest-neighbour cosine between oracle codes and the share above 0.8, the overlap of the top-8 sets of a fact and its nearest neighbour, the share of facts with a private
    slot, and (T-OQ) the share of the exhaustive top-8 among the visited branches."""
    out: dict[str, Any] = {}
    n = int(slots_of_fact.shape[0])
    counts = torch.bincount(slots_of_fact.reshape(-1), minlength=model.slots)
    private = (counts[slots_of_fact] == 1).any(dim=1)
    out["share_with_private_slot"] = float(private.float().mean())
    if codes is not None and n >= 2:
        nn_idx = torch.empty(n, dtype=torch.int64)
        nn_cos = torch.empty(n)
        for s in range(0, n, 2048):
            sims = codes[s : s + 2048] @ codes.T
            rows = torch.arange(sims.shape[0])
            sims[rows, s + rows] = -2.0
            best = sims.max(1)
            nn_idx[s : s + 2048], nn_cos[s : s + 2048] = best.indices, best.values
        out["nn_cosine_mean"] = float(nn_cos.mean())
        out["share_neighbour_above_0_8"] = float((nn_cos > 0.8).float().mean())
        other = slots_of_fact[nn_idx]
        overlap = (slots_of_fact[:, :, None] == other[:, None, :]).any(-1).float().sum(1) / slots_of_fact.shape[1]
        out["top8_overlap_with_nearest"] = float(overlap.mean())
        if model.arm == "T-OQ":
            out["tree_recall_of_exhaustive_top8"] = tree_recall(model, codes)
    return out


def deep_measures(model: P10S1Model, data: StudyData, facts: int, seeds: p9core.SeedSet, stream: Stream) -> dict[str, Any]:
    """Minimal supports on a seeded sample of 2,048 facts of Panel A, utilization and separability (section 7.3), at U_P."""
    out: dict[str, Any] = {}
    if model.arm == "D-OQ":
        return out
    cache = build_cache(model, stream)
    answer = stream.answer_targets().reshape(-1)
    scores = score_cache(cache, answer)
    off = score_cache(_disabled_cache(model, cache), answer)
    ids = stream.fact_ids.reshape(-1)
    trained = ids < facts
    gen = torch.Generator().manual_seed(seeds.facts + core.SUPPORT_SAMPLE_OFFSET)
    sample_ids = torch.randperm(facts, generator=gen)[: min(core.SUPPORT_SAMPLE, facts)]
    in_sample = torch.zeros(data.facts.size, dtype=torch.bool)
    in_sample[sample_ids] = True
    mask = trained & in_sample[ids.clamp_max(data.facts.size - 1)]
    result = minimal_supports(model, cache, off, scores, facts=mask)
    right = scores.correct & mask
    has = result.has_support & right
    out["support"] = {
        "sample_facts": int(mask.sum()), "correct_facts": int(right.sum()), "with_support": int(has.sum()),
        "share_with_support": float(has.sum()) / max(1, int(right.sum())),
        "mean_length": float(result.length[has].float().mean()) if bool(has.any()) else 0.0, "useful_slots_ustar": len(result.useful),
    }  # fmt: skip
    chosen = cast(Any, cache.selection).selected[:, :, :].reshape(-1)
    chosen = chosen[chosen >= 0]
    distinct = int(torch.unique(chosen).numel())
    codes = fact_codes(model, data, facts) if model.arm in ("F-OQ", "T-OQ") else None
    slots_of_fact = fact_slots(model, data, facts, codes)
    out["utilization"] = {"distinct_selected_slots": distinct, "dead_slots": model.slots - distinct, "facts_per_slot_load": facts / model.slots, "facts_per_distinct_slot": facts / max(1, distinct)}
    out["separability"] = separability(model, data, facts, slots_of_fact, codes)
    return out


def _disabled_cache(model: P10S1Model, cache: Any) -> Any:
    """A cache whose answer-site logits are those of the memory disabled (so ``score_cache`` scores the no-memory read)."""
    clone = copy.copy(cache)
    clone.logits_answer = logits_with(model, cache, disabled=True)
    return clone


# --- IVF read of a trained F-OQ (section 5.5) ------------------------------------------------------------------------------------------
def ivf_model(model: P10S1Model, seeds: p9core.SeedSet) -> "tuple[P10S1Model, index.IVFIndex]":
    """The trained F-OQ memory read through the inverted-file index: a copy of ``model`` whose addition is ``IVFMemory``; the index is built from the trained unit-normalized keys
    (seed base + 60) and is identical on a rebuild (gate G4)."""
    if model.arm != "F-OQ":
        raise ValueError("F-OQ-IVF is F-OQ's cells read through the index")
    idx = index.build_index(model.addition.keys.detach(), core.index_seed(seeds))
    clone = copy.deepcopy(model)
    clone.addition = index.IVFMemory(model.addition, idx)
    clone.arm = "F-OQ-IVF"
    return clone, idx


# --- one snapshot ------------------------------------------------------------------------------------------------------------------------
def _read_record(model: P10S1Model, data: StudyData, facts: int, seeds: p9core.SeedSet, *, deep: bool, robustness: bool) -> dict[str, Any]:
    """The counts of one read of a trained model: Panels A and B with the ablations, H1 and H2, the work counters, and (at U_P) robustness and the deep measures."""
    pi = _deranged(data, facts, core.mask_seed(seeds, 0))
    table = getattr(model.addition, "values", None)
    tables: dict[str, Tensor] = {}
    if table is not None:
        tables["shuffle"] = shuffled_values(model, core.mask_seed(seeds, 1))
    rec: dict[str, Any] = {"panels": {}, "secondary": {}}
    for panel in core.PANELS:
        stream = stream_for(data, facts, core.PANEL_STREAM[panel])
        model.counters.reset()
        if isinstance(model.addition, index.IVFMemory):
            model.addition.reset_measures()
        extra = dict(tables)
        if robustness and panel == "A" and table is not None:
            extra.update(robustness_tables(model, seeds))
        counts = panel_counts(model, data, facts, stream, pi=pi, tables=extra)
        tc = counts.pop("tables_correct", {})
        counts["shuffled_correct"] = tc.pop("shuffle", None)
        if robustness and panel == "A" and table is not None:
            counts["robustness_correct"] = tc
        rec["panels"][panel] = counts
        if panel == "A":
            rec["work"] = model.counters.per_query()
            if isinstance(model.addition, index.IVFMemory):
                rec["ivf_measured"] = model.addition.measured()
    for name, stream_name in SECONDARY.items():
        counts = panel_counts(model, data, facts, stream_for(data, facts, stream_name), pi=None, ablate=False)
        rec["secondary"][name] = {"n": counts["n"], "correct": counts["correct"]}
    if deep:
        rec["deep"] = deep_measures(model, data, facts, seeds, stream_for(data, facts, core.PANEL_STREAM["A"]))
    return rec


def evaluate_readout(
    cell: core.Cell,
    model: P10S1Model,
    data: StudyData,
    update: int,
    *,
    frozen_backbone: "Backbone",
    rows: "Tensor | None",
    deep: bool,
    robustness: bool,
    with_ivf: bool = True,
    check_backbone: bool = False,
) -> dict[str, Any]:
    """The eval record of one cell at one snapshot (``model`` already holds the snapshot). ``deep`` and ``robustness`` are set at the cell's U_P snapshot only (section 7.3,
    section 5.2 item 3). F-OQ cells also get the IVF read (``reads['ivf']``). Records are counts; the chunked evaluation gives the same record as an unchunked one."""
    facts = int(cell.facts)
    seeds = data.seeds
    was = model.training
    model.eval()
    try:
        record: dict[str, Any] = {
            **core.envelope("eval"), "label": cell.label, "arm": cell.arm, "kind_of_cell": cell.kind, "facts": facts, "slots": cell.slots, "draw": cell.draw, "update": update,
            "identity": core.code_identity(), "environment": core.environment(), "reads": {},
        }  # fmt: skip
        with eval_chunking(model):
            record["reads"]["main"] = _read_record(model, data, facts, seeds, deep=deep, robustness=robustness)
            if cell.arm == "F-OQ" and with_ivf:
                ivf, idx = ivf_model(model, seeds)
                ivf.eval()
                with eval_chunking(ivf):
                    record["reads"]["ivf"] = _read_record(ivf, data, facts, seeds, deep=False, robustness=False)
                record["reads"]["ivf"]["index_sha256"] = idx.sha256()
                record["reads"]["ivf"]["index_lists"] = idx.lists
        if check_backbone and rows is not None:
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
    readouts: list[int],
    deep_at: int | None,
    r1_seed: int,
    hash_seed: int,
    rows: "Tensor | None" = None,
    out_dir: Path | None = None,
    extra: dict[str, Any] | None = None,
    require_train_record: bool = False,
    with_ivf: bool = True,
) -> list[Path]:
    """Evaluate the snapshots at ``readouts`` of a trained cell and write one ``eval`` record each (never over an existing one). The snapshot's model file must hash to the value
    recorded in ``train.json`` (required when ``require_train_record``). ``deep_at`` is the update (U_P) at which the deep measures and the robustness runs are made."""
    written: list[Path] = []
    folder = out_dir or core.cell_dir(run_dir, cell.label)
    train_json = folder / "train.json"
    recorded: dict[str, str] | None = None
    if train_json.is_file():
        recorded = core.read_record(train_json, "train")["snapshot_sha256"]
    elif require_train_record:
        raise ValueError(f"no train record at {train_json}: the snapshot hash cannot be verified")
    lut = fact_lut_for(data, cell.facts) if cell.arm == "R2" else None
    for update in readouts:
        snap = folder / "snapshots" / core.snapshot_stem(update)
        if recorded is not None and file_sha256(snap / "model.pt") != recorded.get(str(update)):
            raise ValueError(f"snapshot {snap / 'model.pt'} does not match the hash recorded in train.json")
        model = build_model(cell.arm, cell.slots, cell.init_seed, backbone, fact_lut=lut, r1_seed=r1_seed, hash_seed=hash_seed, seed_rng=False)
        load_model_state(snap, model)
        last = update == max(readouts)
        record = evaluate_readout(cell, model, data, update, frozen_backbone=backbone, rows=rows, deep=deep_at == update, robustness=deep_at == update, with_ivf=with_ivf, check_backbone=last)
        record.update(extra or {})
        path = folder / "eval" / core.snapshot_stem(update) / "eval.json"
        if path.exists():
            raise FileExistsError(path)
        core.write_record(path, core.jsonable(record))
        written.append(path)
    return written


# --- baselines that need no training (section 5.5) -----------------------------------------------------------------------------------------
def baseline_record(data: StudyData, backbone: "Backbone", facts: int, draw: int, stream_batches: "list[tuple[Tensor, Tensor]]", seeds: p9core.SeedSet) -> dict[str, Any]:
    """DICT, KNN-W and KNN-W-IVF on both panels and the no-memory baseline on the trained and unseen sets of the draw's fact set of ``facts`` facts. Evaluation only."""
    keys, mean = index.knn_keys(backbone, data, facts, stream_batches)
    idx = index.build_index(keys, core.index_seed(seeds))
    out: dict[str, Any] = {**core.envelope("baseline"), "draw": draw, "facts": facts, "seed_set": seeds.name, "index_sha256": idx.sha256(), "index_lists": idx.lists, "panels": {}}
    for panel in core.PANELS:
        knn = index.knn_panel(backbone, data, facts, keys, mean, panel, None)
        knn_ivf = index.knn_panel(backbone, data, facts, keys, mean, panel, idx)
        stream = stream_for(data, facts, core.PANEL_STREAM[panel])
        nm = controls.evaluate_no_memory(backbone, data.facts, stream)
        ids = stream.fact_ids.reshape(-1)
        trained, unseen = ids < facts, ids >= data.facts.trained
        out["panels"][panel] = {
            "KNN-W": {**knn, **index.knn_costs(facts, None, float(knn["keys_scored_per_query"]))},
            "KNN-W-IVF": {**knn_ivf, **index.knn_costs(facts, idx, float(knn_ivf["keys_scored_per_query"]))},
            "DICT": index.exact_dictionary(data, facts, panel),
            "NO-MEMORY": {"n": int(trained.sum()), "correct": int(nm.correct[trained].sum()), "unseen_n": int(unseen.sum()), "unseen_correct": int(nm.correct[unseen].sum())},
        }
    return out
