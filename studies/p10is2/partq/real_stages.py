# ruff: noqa: E501
"""The real Part Q stage bodies (ADR-0025 sections 4.1, 4.3, 10): ``inputs``, ``partition``, ``qfit``, ``qcheck``, ``generation``, ``regeneration``, ``outputs``, ``analysis``.

Each stage builds the real world (``real_world``: P10-S2's own loaders), the real ``QContext`` and calls the SAME ``pipeline`` / ``step8`` functions the unit tests drive with fakes, so the real path adds no
scientific code. One process, teachers one after the other inside it (the ADR allows one teacher per worker and at most two workers; this body runs one process: reading, listed). Charged time is the wall time of
the process (ruling L2). A stop on the cap is PAUSED (``StageCapExceeded``); a registered test of the data step (a tokenization test, the equivalence test, the chrF cross-check) stops the stage and returns to
the lead (ruling L3). Needs the packages; never imported by the unit tests.
"""

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json
from studies.p10s2 import datagen, fetch_guard
from studies.p10s2.datagen import RegisteredTestStop
from studies.p10s2.tokenization import ByteDecoder, tokenize_segment

from ..common import core
from ..common.core import PendingLeadReview, StageRefused
from ..common.panel_ledger import RowMap
from . import generation as gen
from . import labels, pipeline, real, real_bundle, real_world, step8
from .batches import StageCapExceeded
from .teacher import marian_batch_teacher


def downloads_dir(cfg: Any) -> Path:
    return Path(cfg["paths"]["durable_downloads"]) / "downloads"


def ledger_path(cfg: Any, repo: Path, run_dir: Path, mode: str) -> Path:
    """Registered: the shared ledger in the freeze directory (the plan names it); a rehearsal writes a candidate in its own run directory, which the lead copies into the freeze directory."""
    name = Path(cfg["paths"]["panel_ledger"]).name
    return repo / core.FREEZE_DIR / name if mode == "registered" else run_dir / name


def build_world(cfg: Any, repo: Path, run_dir: Path, mode: str, *, load_teachers: bool, tick: Callable[[str], None] = lambda s: None) -> real_world.RealWorld:
    real_world.assert_process_environment(cfg)
    w = real_world.RealWorld(cfg, repo, run_dir, downloads_dir(cfg))
    w.record["packages"] = real_world.check_packages(cfg, repo)
    w.record["hashes"] = datagen.verify_downloads(w.downloads, repo / real_world.TATOEBA_RECORD, root=repo)
    pins = real.wikitext_pins(repo)
    w.record["wikitext"] = real.check_wikitext(Path(cfg["paths"]["wikitext_dir"]), pins)
    w.record["wikitext"]["adr_0004_sha256"] = file_sha256(repo / real.ADR_0004)
    w.wikitext_rows = real_world.read_wikitext_rows(Path(cfg["paths"]["wikitext_dir"]), pins)
    w.texts = {k: "".join(v) for k, v in w.wikitext_rows.items()}
    tick("hash checks")
    w.student, hf_state, w.record["student"] = real_world.load_student(w.downloads, run_dir / "inputs")
    w.tok = datagen.HFTokenizer(w.downloads)
    w.decoder = ByteDecoder(w.tok.token_bytes())
    w.record["tokenizer_conventions"] = w.tok.conventions
    w._hf_state = hf_state  # type: ignore[attr-defined]
    corpus, corpus_rec = datagen.load_corpus(w.downloads, w.record["hashes"]["tatoeba"])
    w.corpus, w.record["corpus"] = corpus, corpus_rec
    tick("corpus loaded")
    if load_teachers:
        for c, (name, rev, folder) in real_world.TEACHER_FOLDERS.items():
            w.teachers[c] = marian_batch_teacher(w.downloads, folder, name, rev, tick)
        tick("teachers loaded")
    return w


def make_ctx(w: real_world.RealWorld, mode: str, *, limits: dict[str, Any] | None = None) -> pipeline.QContext:
    nl = tuple(tokenize_segment(w.tok, "\n").ids)
    inputs = (read_json(w.run_dir / "inputs/record.json") if (w.run_dir / "inputs/record.json").is_file() else {})
    ctx = pipeline.QContext(
        cfg=w.cfg, mode=mode, corpus=w.corpus, teachers=w.teachers, student_scores=real_world.student_scorer(w.student, w.tok, w.decoder, nl), run_dir=w.run_dir,
        ordinary_windows_left=inputs.get("ordinary_windows_left"), marker_like_windows=inputs.get("marker_like_windows"),
    )  # fmt: skip
    for k, v in (limits or {}).items():
        setattr(ctx, k, v)
    return ctx


# --- stage bodies ----------------------------------------------------------------------------------------------------------------------------
def stage_inputs(w: real_world.RealWorld, ctx: pipeline.QContext, mode: str) -> dict[str, Any]:
    """Step 1: hash checks (done by ``build_world``), the applied generation configuration of each teacher against its pinned file, student conversion and the equivalence record at each read layer (gate G8),
    test (c) of the tokenizer, and the GEN windows: the 44 marker-like and 100 ordinary windows as byte spans in the shared panel ledger (end exclusive, per-row conversion)."""
    cfg = w.cfg
    get = real_world.seed_getter(cfg, mode)
    for c, t in w.teachers.items():
        datagen.check_generation_config(t.model.generation_config, t.generation_config)  # the applied configuration equals the pinned file, else RegisteredTestStop
    w.record["generation_config"] = {c: {"pinned": t.generation_config, "applied": t.applied_generation_config} for c, t in w.teachers.items()}
    layers = (4, 12)
    eq = real_world.equivalence_records(w.student, w._hf_state, w.downloads, w.tok, w.texts["train"], get, layers)  # type: ignore[attr-defined]
    w.record["equivalence"] = {k: v["at_creation"] for k, v in eq.items()}
    if not all(v["at_creation"]["logits"]["ok"] and v["at_creation"]["injection"]["ok"] for v in eq.values()):
        raise RegisteredTestStop("the student equivalence test failed at a read layer (gate G8)")
    w.record["check_c"] = real_world.check_decoder_test_c(w.tok, get)
    window, decision = int(cfg["panels"]["general_window_tokens"]), 64
    grid = real_world.window_grid(w.tok, w.texts["validation"], window, decision)
    spans = real_world.window_spans(grid, w.texts["validation"], w.wikitext_rows["validation"])
    marker = [s for s in spans if s.kind == "marker"]
    ordinary = [s for s in spans if s.kind == "ordinary"]
    lp = ledger_path(cfg, w.repo, w.run_dir, mode)
    ctx_for_ledger = ctx
    ctx_for_ledger.mode = mode
    res = step8.step_ledger(ctx_for_ledger, lp, marker, ordinary, row_map=RowMap.from_rows(w.wikitext_rows["validation"]))
    w.record["gen_windows"] = {"grid_windows": len(grid), "marker_like": len(marker), "ordinary_candidates": len(ordinary), "ledger": str(lp), "ledger_sha256": file_sha256(lp), **res}
    rec = {**core.envelope("block_record", "Q"), "what": "inputs", "ordinary_windows_left": res["eligible_ordinary"], "marker_like_windows": len(marker), **{k: v for k, v in w.record.items() if k not in ("corpus",)}}
    core.write_record(w.run_dir / "inputs/record.json", rec, overwrite=True)
    return rec


def tokenizer_record(w: real_world.RealWorld, ctx: pipeline.QContext, p: Any) -> dict[str, Any]:
    """The token ids of 100 fixed sentences per teacher (seed 250908, drawn from that capability's own generation sources) and the teacher's own translation of them (P10-S2's ``tokenizer_record``)."""
    path = w.run_dir / "inputs/tokenizer_record.json"
    if path.is_file():
        return read_json(path)  # type: ignore[no-any-return]
    from . import split

    sp = split.split_sources(p.source_pool["A"], p.source_pool["B"], pipeline.partition.source_unit_key, ctx.seeds["source_split"], ctx.allowed, float(ctx.cfg["generation"]["split_share_b"]))
    g = core.seeded_generator(ctx.seeds["teacher_tokenizer_sentences_and_digest"], "teacher tokenizer sentences", ctx.allowed)
    out: dict[str, Any] = {}
    import torch

    for c in core.TASKS:
        pool = sorted(sp[c], key=lambda i: i.key)
        pick = torch.randperm(len(pool), generator=g).tolist()[:100]
        out[c] = w.teachers[c].tokenizer_record([pool[i].en for i in pick])
    write_json(path, core.jsonable(out))
    return out


def stage_outputs(w: real_world.RealWorld, ctx: pipeline.QContext, p: Any, mode: str) -> dict[str, Any]:
    """Step 8: teacher outputs on the six panels (stored, not scored); the chrF cross-check against sacrebleu; the token-id bank, tests (a) and (b), the C1 pairing; the gloss word ids for R-gloss-icl; the bundle."""
    from studies.p10s2.worldio import write_bundle

    from . import batches as bt

    step8.step_outputs(ctx, p)
    qf = ctx.d(pipeline.loc(ctx, "qfit/record.json"))
    items = p.panels["Q_fit"]
    a_batches = [bt.read_batch(ctx.d("qfit/teacher_A"), i) for i in bt.stored_indices(ctx.d("qfit/teacher_A"))]
    src_of = {it.key: it.en for it in items}
    outs_a = gen.outputs_of(a_batches, src_of)[:1000]
    cross = datagen.crosscheck_chrf([(o.text, list(i.refs["A"])) for o, i in zip(outs_a, items[:1000], strict=True)])
    if not cross["ok"]:
        raise RegisteredTestStop(f"the chrF cross-check differs by {cross['max_abs_difference']} (0.001 allowed)")
    accepted = {c: pipeline.accepted_pool(ctx, c) for c in core.TASKS}
    teacher_outputs = {c: {name: [t for b in sorted_batches(ctx, c, name) for t in b.texts] for name in step8.PANEL_OUTPUT_PANELS} for c in core.TASKS}
    max_new = real_world.max_new_from_dcal(w.tok, p, tuple(tokenize_segment(w.tok, "\n").ids))
    windows = _stored_windows(w, ctx, mode)
    spill = w.run_dir / "outputs/bank_spill.tmp"
    try:
        bundle, rec = real_bundle.make_bundle(ctx, p, w.tok, w.student, accepted, windows, w.texts["train"], teacher_outputs, max_new, spill, {"wikitext": w.record["wikitext"], "tatoeba": w.record["hashes"]["tatoeba"]})
        if not rec["required_ok"]:
            raise RegisteredTestStop(f"tokenization test (a) or the combined whole-string test failed: {json.dumps(rec['tokenization'])[:400]}")
        from . import gloss

        gb = gloss.gloss_bank(w.tok, accepted, p.vocab)
        write_bundle(bundle, w.run_dir / "outputs/bundle")
        write_json(w.run_dir / "outputs/gloss_bank.json", gb)
    finally:
        spill.unlink(missing_ok=True)
    out = {"chrf_crosscheck": cross, "tokenization": rec["tokenization"], "c1_pairing": {k: v for k, v in rec["c1_pairing"].items() if k != "sigma"}, "bundle": str(w.run_dir / "outputs/bundle"), "qfit_record": str(qf)}
    core.write_record(w.run_dir / "outputs/step8_record.json", {**core.envelope("block_record", "Q"), "what": "step8", **core.jsonable(out)}, overwrite=True)
    return out


def sorted_batches(ctx: pipeline.QContext, c: str, name: str) -> list[Any]:
    from . import batches as bt

    d = ctx.d(f"outputs/teacher_{c}/{name}")
    return [bt.read_batch(d, i) for i in bt.stored_indices(d)]


def _stored_windows(w: real_world.RealWorld, ctx: pipeline.QContext, mode: str) -> list[Any]:
    """The 144 stored GEN windows as ``GeneralWindow`` records: every marker-like window and the 100 ordinary windows the ledger recorded (the ledger is the source of which windows)."""
    led = read_json(ledger_path(w.cfg, w.repo, w.run_dir, mode))["windows"]
    mine = {(x["start"], x["end"]) for x in led if x.get("owner") == "P10IS2-partq"}
    vocab_index = {x: i for i, x in enumerate(pipeline.partition.build_partition(w.corpus, w.cfg, ctx.seeds, ctx.allowed, sizes=ctx.sizes).vocab)}
    cut = real_world.cut_general_windows(w.tok, w.texts["validation"], vocab_index, int(w.cfg["panels"]["general_window_tokens"]), 64)
    grid = real_world.window_grid(w.tok, w.texts["validation"], int(w.cfg["panels"]["general_window_tokens"]), 64)
    spans = real_world.window_spans(grid, w.texts["validation"], w.wikitext_rows["validation"])
    if len(cut) != len(spans):
        raise RegisteredTestStop("the window grid and P10-S2's window cut disagree in count")
    return [win for win, s in zip(cut, spans, strict=True) if (s.start, s.end) in mine]


def run_stage(stage: str, repo: Path, run_dir: Path, mode: str, *, limits: dict[str, Any] | None = None) -> dict[str, Any]:
    """One stage, in this process. Returns a small record; a cap stop raises ``StageCapExceeded`` (the caller records PAUSED)."""
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    started = time.monotonic()
    w = build_world(cfg, repo, run_dir, mode, load_teachers=stage != "analysis")
    ctx = make_ctx(w, mode, limits=limits)
    if stage == "inputs":
        out = stage_inputs(w, ctx, mode)
    else:
        p = pipeline.step_partition(ctx)
        if stage == "partition":
            out = {"counts": p.counts, "tokenizer_record": bool(tokenizer_record(w, ctx, p))}
        elif stage == "qfit":
            out = pipeline.step_qfit(ctx, p)
        elif stage == "qcheck":
            out = pipeline.step_qcheck(ctx, p, pipeline.step_qfit(ctx, p))
        elif stage == "generation":
            out = pipeline.step_generation(ctx, p, pipeline.step_qfit(ctx, p))
        elif stage == "regeneration":
            out = pipeline.step_regeneration(ctx, p)
        elif stage == "outputs":
            out = stage_outputs(w, ctx, p, mode)
        elif stage == "analysis":
            res = labels.part_q_label(pipeline.facts_of(ctx))
            core.write_record(run_dir / pipeline.loc(ctx, "qualification.json"), {**core.envelope("qualification", "Q"), **{k: v for k, v in res.items() if k != "oracle_line"}}, overwrite=True)
            out = {"label": res["label"], "part_t": res["part_t"]} if mode == "registered" else pipeline.summary_for_display(ctx)
        else:
            raise StageRefused(f"refused: {stage!r} is not a Part Q stage")
    total = float(cfg["stage_caps"].get("total_hours", 0.0)) * 3600.0
    led = core.Ledger(run_dir / "charged_ledger.json", "Q", total if total > 0 else 1e12)  # the ledger lives in the run directory (git-ignored or outside the repository), never in the tree
    led.charge_process(stage, mode, "main", time.monotonic() - started)
    return out


__all__ = ["PendingLeadReview", "StageCapExceeded", "fetch_guard", "run_stage"]
