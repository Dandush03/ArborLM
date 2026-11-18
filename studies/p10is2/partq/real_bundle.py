# ruff: noqa: E501
"""Step 8 of Part Q on real data: the token-id bank, the tokenization tests, the C1 pairing, the timing items, the stored GEN windows and the bundle Part T reads (ADR-0025 section 4.1 step 8).

Part T reads this bundle (``studies.p10s2.worldio.write_bundle`` / ``read_bundle``: the same container P10-S2's training and scoring code already consumes), so it encodes no text and needs no tokenizer. Every
function calls P10-S2's own code (``ExampleBank`` / ``SpillBank``, ``prefreeze.tokenization_checks`` and ``check_combined_whole_string``, ``combined.pair_list``) with this study's seeds and pools.
Needs the packages only through the tokenizer object it is handed; never imported by the unit tests.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import torch

from studies.p10s2 import prefreeze
from studies.p10s2.combined import pair_list, pairs_digest
from studies.p10s2.data import Item, Sizes, TrainItem
from studies.p10s2.evaluate import GeneralWindow
from studies.p10s2.spill import SpillBank
from studies.p10s2.tokenization import ByteDecoder, tokenize_segment
from studies.p10s2.world import ExampleBank
from studies.p10s2.worldio import DataBundle

from ..common import core
from . import pipeline


def seeded_permutation(n: int, seed_name: str, ctx: pipeline.QContext) -> list[int]:
    return torch.randperm(n, generator=core.seeded_generator(ctx.seeds[seed_name], seed_name, ctx.allowed)).tolist()


def subsample(items: Sequence[Item], n: int, ctx: pipeline.QContext, name: str = "control_subsample") -> list[Item]:
    """The 300-item subsample of a panel (seed 250906): the first ``n`` of a seeded permutation, in panel order. One generator drawn for E_A then E_B by the caller's order (as P10-S2's ``fixed_subsample``)."""
    order = sorted(seeded_permutation(len(items), name, ctx)[:n])
    return [items[i] for i in order]


def timing_indices(sizes: Mapping[str, int], count: int, ctx: pipeline.QContext) -> dict[str, list[int]]:
    g = core.seeded_generator(ctx.seeds["timing_items"], "timing benchmark items", ctx.allowed)
    return {name: sorted(torch.randperm(n, generator=g).tolist()[: min(count, n)]) if n else [] for name, n in sizes.items()}


def seen_order(accepted: Mapping[str, Sequence[TrainItem]], ctx: pipeline.QContext) -> dict[str, list[str]]:
    g = core.seeded_generator(ctx.seeds["seen_items"], "seen items", ctx.allowed)
    out: dict[str, list[str]] = {}
    for c in core.TASKS:
        keys = sorted({x.key for x in accepted[c]})
        out[c] = [keys[i] for i in torch.randperm(len(keys), generator=g).tolist()]
    return out


def build_bank(tok: Any, vocab_index: Mapping[str, int], p: Any, accepted: Mapping[str, Sequence[TrainItem]], spill: Path | None) -> ExampleBank:
    """Segment ids of every training row (pool item with its target), every pool prompt and every panel prompt, as P10-S2's data step stored them (SpillBank when a path is given)."""
    bank: ExampleBank = SpillBank(vocab_index, spill) if spill is not None else ExampleBank()
    if isinstance(bank, SpillBank):
        bank.spilling = True
    for c in core.TASKS:
        for x in accepted[c]:
            bank.build_from_tokenizer(tok, vocab_index, c, x.en, x.target)
            bank.build_from_tokenizer(tok, vocab_index, c, x.en, None)
    if isinstance(bank, SpillBank):
        bank.spilling = False
    for name, items in p.panels.items():
        for it in items:
            for c in core.TASKS:
                if c in it.refs:
                    bank.build_from_tokenizer(tok, vocab_index, c, it.en, None)
    return bank


def c1_pairing(p: Any, ctx: pipeline.QContext, tok: Any) -> dict[str, Any]:
    """The pairing of the combined task C1 (seed 250911): a seeded permutation of the E_C positions, the pair list and its digest, and the whole-string extension of test (a)."""
    n = len(p.panels["E_C"])
    sigma = torch.randperm(n, generator=core.seeded_generator(ctx.seeds["c1_pairing"], "C1 pairing", ctx.allowed)).tolist()
    pairs = pair_list(n, sigma)
    return {"sigma": sigma, "pairs_sha256": pairs_digest(pairs), "n": n, "whole_string": prefreeze.check_combined_whole_string(tok, p.panels["E_C"], pairs)}


def make_bundle(
    ctx: pipeline.QContext, p: Any, tok: Any, student: Any, accepted: Mapping[str, Sequence[TrainItem]], windows: Sequence[GeneralWindow], train_text: str, teacher_outputs: Mapping[str, Mapping[str, list[str]]], max_new: int, spill: Path | None,
    provenance: Mapping[str, Any], extra: Mapping[str, Any] | None = None,
) -> tuple[DataBundle, dict[str, Any]]:  # fmt: skip
    """The bundle and the record of the tests. The panels are the partition's (E_A, E_B, E_C, E_open, Q_fit, D_cal, D_con); the gold pool is empty (this design is teacher-only); the ablation subsample
    (seed 250906) is E_A then E_B; the timing items (seed 250913) are 200 per panel."""
    vocab_index = {w: i for i, w in enumerate(p.vocab)}
    decoder = ByteDecoder(tok.token_bytes())
    nl = tuple(tokenize_segment(tok, "\n").ids)
    bank = build_bank(tok, vocab_index, p, accepted, spill)
    gold_items: dict[str, list[TrainItem]] = {c: [] for c in core.TASKS}
    rec: dict[str, Any] = {"tokenization": prefreeze.tokenization_checks(tok, decoder, bank, accepted, gold_items, p, teacher_outputs)}
    rec["c1_pairing"] = c1_pairing(p, ctx, tok)
    ctrl = core.seeded_generator(ctx.seeds["control_subsample"], "control subsample", ctx.allowed)
    ablation: dict[str, list[str]] = {}
    for name in ("E_A", "E_B"):
        items = p.panels[name]
        order = sorted(torch.randperm(len(items), generator=ctrl).tolist()[:300])
        ablation[name] = [items[i].key for i in order]
    timing = timing_indices({n: len(p.panels[n]) for n in ("E_A", "E_B")}, 200, ctx)
    sizes = replace(Sizes.registered(), panel_q_fit=int(ctx.cfg["panels"]["q_fit"]), panel_q_check=int(ctx.cfg["panels"]["q_check_block"]))
    panels = {k: v for k, v in p.panels.items()}
    bundle = DataBundle(
        student.cfg, {k: v.detach().clone() for k, v in student.state_dict().items()}, tok.token_bytes(), nl, sizes, p.vocab, panels, {c: [] for c in core.TASKS}, {c: list(accepted[c]) for c in core.TASKS}, seen_order(accepted, ctx), ablation,
        bank.records_stream() if isinstance(bank, SpillBank) else bank.to_records(), list(windows), tok.encode(train_text), {c: {k: list(v) for k, v in per.items()} for c, per in teacher_outputs.items()}, max_new,
        {"conventions": {"bos": tok.bos_id}, "c1_pairing": {"sigma": rec["c1_pairing"]["sigma"], "pairs_sha256": rec["c1_pairing"]["pairs_sha256"]}, "timing_items": timing, "provenance": dict(provenance), "study": "P10IS2", **dict(extra or {})},
    )  # fmt: skip
    rec["required_ok"] = bool(rec["tokenization"]["required_ok"] and rec["c1_pairing"]["whole_string"]["ok"])
    return bundle, rec
