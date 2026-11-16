# ruff: noqa: E501
"""The frozen data files and the loader (ADR-0022 sections 2, 5, 14.2): ``DataBundle`` is what the data-generation and partition steps produce; ``write_bundle`` and ``read_bundle`` store it as plain files with
SHA-256 values (gate G7, checked at every load); ``build_world`` turns a bundle into the ``World`` every later step consumes.

This is the seam through which the real data enters: the real data-generation step fills a ``DataBundle`` (student weights converted to a plain torch file, token records, partitions, teacher outputs,
windows) and every later step is the same code that the synthetic stand-ins exercise. The registered path never encodes text and never imports a package outside the lock.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, write_json

from . import core
from .combined import Sentence, combined_set, pairs_digest
from .data import Item, Partition, Sizes, TrainItem, draw_streams
from .evaluate import EvalContext, GeneralWindow, PanelData
from .model import StudentConfig, build_student, load_plain_state
from .routing import RouterSpec
from .tokenization import ByteDecoder
from .train import select_device
from .world import ExampleBank, World


@dataclass
class DataBundle:
    cfg: StudentConfig
    student_state: dict[str, torch.Tensor]
    token_bytes: list[bytes]
    newline_ids: tuple[int, ...]
    sizes: Sizes
    vocab: list[str]
    panels: dict[str, list[Item]]  # E_A, E_B, E_C, E_open, Q_fit, Q_check, D_cal, D_con
    gold_pool: dict[str, list[Item]]
    accepted: dict[str, list[TrainItem]]
    seen_order: dict[str, list[str]]  # keys of the accepted pool in the order of the 220907 permutation (drawn once, in the partition step)
    ablation_keys: dict[str, list[str]]  # panel -> keys of the 300-item subsample (220904)
    bank_records: list[dict[str, Any]]
    windows: list[GeneralWindow]
    wiki_train_ids: list[int]
    teacher_outputs: dict[str, dict[str, list[str]]]
    max_new: int
    extra: dict[str, Any] = field(default_factory=dict)  # tokenization conventions, filter fits, qualification, counts: records, not inputs


def _item_json(i: Item) -> dict[str, Any]:
    return i.to_json()


def _item_from(d: Mapping[str, Any]) -> Item:
    return Item(str(d["key"]), str(d["en"]), {c: tuple(v) for c, v in d["refs"].items()}, int(d["group"]))


TENSOR_KEYS = ("reference_logits", "reference_injection_logits")
TENSOR_PREFIX = "@tensor:"


def _strip_equivalence_tensors(extra: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, torch.Tensor]]:
    """Move the stored reference logits of the equivalence records out of ``extra`` into tensors (keyed by layer, so the record of the first layer that appears twice is stored once); the records keep a
    ``@tensor:`` reference in their place. The caller's mapping is not changed."""
    tensors: dict[str, torch.Tensor] = {}

    def strip(rec: Mapping[str, Any]) -> dict[str, Any]:
        out = dict(rec)
        for k in TENSOR_KEYS:
            v = out.get(k)
            if v is not None and not (isinstance(v, str) and v.startswith(TENSOR_PREFIX)):
                name = f"L{out['layer']}/{k}"
                tensors[name] = torch.as_tensor(v, dtype=torch.float32).clone()
                out[k] = TENSOR_PREFIX + name
        return out

    new = dict(extra)
    if isinstance(new.get("equivalence"), Mapping):
        new["equivalence"] = strip(new["equivalence"])
    if isinstance(new.get("equivalence_layers"), Mapping):
        new["equivalence_layers"] = {k: strip(v) for k, v in new["equivalence_layers"].items()}
    return new, tensors


def _restore_equivalence_tensors(extra: dict[str, Any], tensors: Mapping[str, torch.Tensor]) -> None:
    def fix(rec: dict[str, Any]) -> None:
        for k in TENSOR_KEYS:
            v = rec.get(k)
            if isinstance(v, str) and v.startswith(TENSOR_PREFIX):
                rec[k] = tensors[v[len(TENSOR_PREFIX) :]]

    if isinstance(extra.get("equivalence"), dict):
        fix(extra["equivalence"])
    for rec in (extra.get("equivalence_layers") or {}).values():
        fix(rec)


def write_bundle(b: DataBundle, directory: Path) -> dict[str, Any]:
    """Write the bundle as plain files and a manifest of SHA-256 values (frozen at creation)."""
    directory.mkdir(parents=True, exist_ok=True)
    torch.save({"cfg": b.cfg.__dict__, "state": b.student_state}, directory / "student.pt")
    write_json(directory / "tokenizer_table.json", {"token_bytes_hex": [t.hex() for t in b.token_bytes], "newline_ids": list(b.newline_ids)})
    write_json(directory / "bank.json", b.bank_records)
    write_json(directory / "partition.json", {"sizes": b.sizes.__dict__, "vocab": b.vocab, "panels": {k: [_item_json(i) for i in v] for k, v in b.panels.items()}, "gold_pool": {k: [_item_json(i) for i in v] for k, v in b.gold_pool.items()}, "ablation_keys": b.ablation_keys, "seen_order": b.seen_order})
    write_json(directory / "accepted.json", {c: [x.__dict__ for x in v] for c, v in b.accepted.items()})
    write_json(directory / "windows.json", {"windows": [{"ids": list(w.ids), "reads": [list(r) for r in w.reads], "stratum": w.stratum, "marker_end": w.marker_end} for w in b.windows], "wiki_train_ids": b.wiki_train_ids})
    write_json(directory / "teacher_outputs.json", b.teacher_outputs)
    extra, tensors = _strip_equivalence_tensors(b.extra)
    if tensors:
        torch.save(tensors, directory / "equivalence_tensors.pt")  # 256 x 49,152 logits per layer: as float32 tensors in a hashed file, never as JSON lists (a gigabyte of text, read again by every registered stage)
    write_json(directory / "extra.json", {"max_new": b.max_new, **extra})
    files = sorted(p.name for p in directory.iterdir() if p.is_file() and p.name != "manifest.json")
    manifest = {"schema": core.SCHEMA, "files": {n: {"algo": "sha256", "digest": file_sha256(directory / n)} for n in files}}
    write_json(directory / "manifest.json", manifest)
    return manifest


def read_bundle(directory: Path) -> DataBundle:
    """Read a bundle, verifying every file against the manifest first (gate G7: checked at every load; any difference stops the run)."""
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, spec in manifest["files"].items():
        if file_sha256(directory / name) != spec["digest"]:
            raise ValueError(f"refused: {name} does not hash to the frozen SHA-256 in the manifest")
    st = torch.load(directory / "student.pt", weights_only=True)
    tt = json.loads((directory / "tokenizer_table.json").read_text())
    part = json.loads((directory / "partition.json").read_text())
    win = json.loads((directory / "windows.json").read_text())
    extra = json.loads((directory / "extra.json").read_text())
    if (directory / "equivalence_tensors.pt").exists():
        _restore_equivalence_tensors(extra, torch.load(directory / "equivalence_tensors.pt", weights_only=True))
    return DataBundle(
        StudentConfig(**st["cfg"]), st["state"], [bytes.fromhex(h) for h in tt["token_bytes_hex"]], tuple(tt["newline_ids"]), Sizes(**part["sizes"]), part["vocab"],
        {k: [_item_from(i) for i in v] for k, v in part["panels"].items()}, {k: [_item_from(i) for i in v] for k, v in part["gold_pool"].items()},
        {c: [TrainItem(**x) for x in v] for c, v in json.loads((directory / "accepted.json").read_text()).items()}, part["seen_order"], part["ablation_keys"],
        json.loads((directory / "bank.json").read_text()), [GeneralWindow(tuple(w["ids"]), tuple((a, b) for a, b in w["reads"]), w["stratum"], w["marker_end"]) for w in win["windows"]], win["wiki_train_ids"],
        json.loads((directory / "teacher_outputs.json").read_text()), int(extra.pop("max_new")), extra,
    )  # fmt: skip


@dataclass(frozen=True)
class RunConfig:
    """What the freeze fixes for a run: the calibrated read layer and learning rates, the design (U), the device and the router recipe."""

    layer: int
    updates: int
    batch: int
    replay_rows: int
    rows_per_stage: int
    store_lr: float
    lora_lr: float
    rank_single: int
    rank_joint: int
    router: RouterSpec
    decision_token: int
    window_tokens: int
    device: str = "cpu"

    @staticmethod
    def registered(layer: int, updates: int, store_lr: float, lora_lr: float, device: str) -> "RunConfig":
        t, d = core.CFG["training"], core.CFG["data"]
        return RunConfig(layer, updates, t["batch"], t["replay_rows"], core.ROWS_PER_STAGE, store_lr, lora_lr, t["lora_rank_single"], t["lora_rank_joint"], RouterSpec.registered(), d["router_decision_token"], d["general_window_tokens"], device)

    @staticmethod
    def dry(updates: int | None = None) -> "RunConfig":
        d, t = core.CFG["dry"], core.CFG["training"]
        return RunConfig(d["read_layer"], updates if updates is not None else d["updates"], d["batch"], d["replay_rows"], d["rows_per_stage"], t["store_learning_rate"], t["lora_learning_rates"][1], 2, 4, RouterSpec.dry(), d["router_decision_token"], d["window_tokens"], "cpu")


def build_world(b: DataBundle, mode: str, replicates: int, run: RunConfig) -> World:
    """The world of a run from frozen data: the student (loaded strictly from the plain state), the example bank (rebuilt from stored segment ids, no tokenizer), the panels, the replicate draws (+1 and +5
    generators of the mode's seed plan), the evaluation context."""
    student = build_student(b.cfg)
    load_plain_state(student, b.student_state)
    decoder = ByteDecoder(b.token_bytes)
    vocab_index = {w: i for i, w in enumerate(b.vocab)}
    bank = ExampleBank.from_records(b.bank_records, vocab_index)
    nv = len(b.vocab)
    streams = [draw_streams(core.SeedPlan(mode, r), b.accepted, b.gold_pool, b.sizes) for r in range(replicates)]

    def panel(name: str, cap: str) -> PanelData:
        items = b.panels[name]
        return PanelData("E_" + cap, cap, [bank.prompt(cap, i.en) for i in items], [list(i.refs[cap]) for i in items])

    pa, pb = panel("E_A", "A"), panel("E_B", "B")
    sub = {}
    for name, key in (("E_A", "E_A"), ("E_B", "E_B")):
        keys = set(b.ablation_keys[key])
        sub[name] = [k for k, it in enumerate(b.panels[key]) if it.key in keys]
    sentences = [Sentence(it.key, {c: bank.prompt(c, it.en) for c in core.TASKS}, {c: tuple(it.refs[c]) for c in core.TASKS}) for it in b.panels["E_C"]]
    sigma = b.extra.get("c1_pairing", {}).get("sigma")
    if sigma is None:
        raise ValueError("the data manifest has no C1 pairing (the listed seed 220911 is drawn once, in the partition step)")
    ec = combined_set(sentences, sigma)
    if pairs_digest(ec.pairs) != b.extra["c1_pairing"]["pairs_sha256"]:
        raise ValueError("the C1 pair list does not match its hash in the data manifest")
    panels_all = {"E_A": pa, "E_B": pb}
    for c in core.TASKS:  # E_open (section 6.1, 10): items with at least one out-of-vocabulary word; one panel per capability, the items that carry a reference in that language; descriptive only, oracle route only
        idx = tuple(i for i, it in enumerate(b.panels.get("E_open", [])) if it.refs.get(c))
        if idx:
            panels_all["E_open_" + c] = PanelData("E_open_" + c, c, [bank.prompt(c, b.panels["E_open"][i].en) for i in idx], [list(b.panels["E_open"][i].refs[c]) for i in idx], idx)
    ctx = EvalContext(student, decoder, nv, b.max_new, run.layer, b.newline_ids, panels_all, sub, list(b.windows), decision_index=run.decision_token - 1, first_nll_index=run.decision_token, vocabulary=nv, ec=ec)
    d_con = {c: PanelData("D_con_" + c, c, [bank.prompt(c, i.en) for i in b.panels["D_con"]], [list(i.refs[c]) for i in b.panels["D_con"]]) for c in core.TASKS}
    n_seen = core.CFG["data"]["seen_items"] if mode != "test" else core.CFG["dry"]["seen_items"]
    seen = []
    for s in streams:
        d: dict[str, list[TrainItem]] = {}
        for c in core.TASKS:
            inT = {x.key: x for x in s.t[c]}
            d[c] = [inT[k] for k in b.seen_order[c] if k in inT][:n_seen]
        seen.append(d)
    d_cal = {c: PanelData("D_cal_" + c, c, [bank.prompt(c, i.en) for i in b.panels["D_cal"]], [list(i.refs[c]) for i in b.panels["D_cal"]]) for c in core.TASKS}
    part = Partition(b.sizes, {}, {}, [], b.vocab, vocab_index, b.panels, b.gold_pool, {}, frozenset(), {}, {})
    return World(
        b.cfg, student, decoder, mode, replicates, b.sizes, run.layer, run.updates, run.batch, run.replay_rows, run.rows_per_stage, run.store_lr, run.lora_lr, run.rank_single, run.rank_joint, nv, bank, part,
        streams, ctx, d_con, d_cal, list(b.wiki_train_ids), run.router, seen, b.teacher_outputs, select_device(run.device), mode,
        timing_items={k: list(v) for k, v in b.extra.get("timing_items", {}).items()},
    )  # fmt: skip


def seen_order(accepted: Mapping[str, Sequence[TrainItem]], mode: str) -> dict[str, list[str]]:
    """The 300 seen-item training items (listed seed 220907): a permutation of each capability's accepted pool, drawn once in the partition step and stored; a replicate's seen items are the first 300 of
    its own training draw in that order (capability A, then B; reading: the ADR draws 'the 300 seen-item training items' once but the training draws differ per replicate)."""
    gen = core.partition_gen(mode, "seen_items", "seen items")
    out: dict[str, list[str]] = {}
    for c in core.TASKS:
        keys = sorted({x.key for x in accepted[c]})
        out[c] = [keys[i] for i in torch.randperm(len(keys), generator=gen).tolist()]
    return out
