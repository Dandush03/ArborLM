# ruff: noqa: E501
"""The real Part Q stage bodies (ADR-0025 sections 4.1, 4.3, 9, 10): ``ledger`` (the one pre-freeze command), ``inputs``, ``partition``, ``qfit``, ``qcheck``, ``generation``, ``regeneration``, ``outputs``, ``analysis``.

Each stage builds the real world (``real_world``: P10-S2's own loaders), the real ``QContext`` and calls the SAME ``pipeline`` / ``step8`` functions the unit tests drive with fakes, so the real path adds no
scientific code. What this module adds is the stage machinery the ADR asks for:

* every registered stage takes its parameters from the FROZEN PLAN (``plan.items(stage)``, ``plan.data["layout"]``), not from the config;
* stage ORDER is enforced (a stage runs only after its predecessor's completion record; generation, regeneration and the outputs only if both teachers passed Q1-Q4);
* a CUMULATIVE ledger of charged seconds in the run directory (the wall time of each process, ruling L2): a stage may use the smaller of its cap less what it used and what is left of the part's total; a cap stop
  or a memory-guard stop (12 GiB) is PAUSED and the stage resumes at the next batch; the stage manifest says so;
* a code or environment error is an ITEM ERROR (``item_errors/``) the analysis refuses on; a digest mismatch, a failed G8 or any registered test of the data step leaves a record (``engineering_failures.json``)
  and stops the stage (ruling L3); a worker's refusal on identity exits 75 (PAUSED — IDENTITY) before anything is written;
* the process is configured (six threads, deterministic algorithms) first.

The shared panel ledger is written ONLY by the ``ledger`` command, before the freeze (seed 250907; rehearsal 252907, into the run directory); ``inputs`` VERIFIES it and never writes. One process per stage, the
teachers one after the other inside it (the ADR allows one teacher per worker and two workers; a worker split is an optimisation the lead's launch can add). Needs the packages (except ``analysis``, which reads
records only); never imported by the unit tests.
"""

import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json
from studies.p10s2 import datagen
from studies.p10s2.datagen import RegisteredTestStop
from studies.p10s2.tokenization import ByteDecoder, tokenize_segment

from ..common import core, gates, procs, runner
from ..common import plan as planmod
from ..common.core import StageRefused
from . import batches as bt
from . import generation as gen
from . import labels, partition, pipeline, pkgmanifest, real, real_bundle, real_world, reuse, step8
from .batches import DigestMismatch, StageCapExceeded
from .teacher import marian_batch_teacher

STAGE_ORDER = ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration", "outputs", "analysis")
TEACHER_GATED = ("generation", "regeneration", "outputs")


def downloads_dir(cfg: Any) -> Path:
    return Path(cfg["paths"]["durable_downloads"]) / "downloads"


def ledger_path(cfg: Any, repo: Path, run_dir: Path, mode: str) -> Path:
    """Registered: the SHARED ledger (``paths.panel_ledger``, outside the repository); a rehearsal writes a candidate in its own run directory, which the lead may use as the registered one only by copying it."""
    return Path(cfg["paths"]["panel_ledger"]) if mode == "registered" else run_dir / "panel_ledger_candidate.json"


def build_world(cfg: Any, repo: Path, run_dir: Path, mode: str, *, load_teachers: bool, light: bool = False, plan: planmod.Plan | None = None, tick: Callable[[str], None] = lambda s: None) -> real_world.RealWorld:
    """The real world. ``light`` loads only the tokenizer and WikiText-2 (the ``ledger`` command); otherwise also the student and the corpus (and the teachers if asked)."""
    gates.apply_platform_settings(cfg)
    if plan is not None:  # R7: the plan's inputs and the durable package copy are what the freeze recorded, checked at the start of every stage that uses them
        pkgmanifest.verify_inputs(plan.data["inputs"], uses_packages=True, repo=repo)
    real_world.assert_process_environment(cfg)
    w = real_world.RealWorld(cfg, repo, run_dir, downloads_dir(cfg))
    w.record["packages"] = real_world.check_packages(cfg, repo)
    pins = real.wikitext_pins(repo)
    w.record["wikitext"] = real.check_wikitext(Path(cfg["paths"]["wikitext_dir"]), pins)
    w.record["wikitext"]["adr_0004_sha256"] = file_sha256(repo / real.ADR_0004)
    w.wikitext_rows = real_world.read_wikitext_rows(Path(cfg["paths"]["wikitext_dir"]), pins)
    w.texts = {k: "".join(v) for k, v in w.wikitext_rows.items()}
    if light:
        w.tok = datagen.HFTokenizer(w.downloads)
        return w
    w.record["hashes"] = datagen.verify_downloads(w.downloads, repo / real_world.TATOEBA_RECORD, root=repo)
    tick("hash checks")
    save_to = None if (run_dir / "inputs/student_plain.pt").is_file() else run_dir / "inputs"  # the 538 MB converted state is written ONCE (the inputs stage), never rewritten by later stages
    w.student, hf_state, w.record["student"] = real_world.load_student(w.downloads, save_to)
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


def make_ctx(w: real_world.RealWorld, mode: str, *, plan: planmod.Plan | None = None, limits: dict[str, Any] | None = None, deadline: Callable[[], bool] | None = None, inputs_stage: bool = False) -> pipeline.QContext:
    """The context. In a registered stage every parameter comes from the plan: the layout (batch size, block size, digest and regeneration batches), the Q_check target and the generation targets of its items,
    and only the teachers its items name."""
    nl = tuple(tokenize_segment(w.tok, "\n").ids) if w.tok is not None and w.student is not None else ()
    inputs = read_json(w.run_dir / "inputs/record.json") if (w.run_dir / "inputs/record.json").is_file() else {}
    if plan is not None and not inputs and not inputs_stage:  # the inputs stage WRITES this record; every later stage needs it
        raise StageRefused("refused: the inputs record is missing: the fixed-input counts (windows) cannot be skipped")
    scorer = real_world.student_scorer(w.student, w.tok, w.decoder, nl) if w.student is not None else (lambda items, p: {})
    ctx = pipeline.QContext(cfg=w.cfg, mode=mode, corpus=w.corpus, teachers=w.teachers, student_scores=scorer, run_dir=w.run_dir, ordinary_windows_left=inputs.get("ordinary_windows_left"), marker_like_windows=inputs.get("marker_like_windows"), deadline=deadline)
    if plan is not None:
        lay = plan.data["layout"]
        ctx.batch_size, ctx.block_sources = int(lay["batch_size"]), int(lay["generation_block_sources"])
        ctx.digest_batches, ctx.regeneration_batches = int(lay["digest"]["batches"]), int(lay["regeneration"]["batches"])
        qc = plan.items("qcheck")
        ctx.check_target = int(qc[0]["target_accepted"])
        gi = plan.items("generation")
        ctx.accepted_min, ctx.accepted_disjoint = int(gi[0]["minimum_accepted"]), int(gi[0]["target_accepted"])
        named = {i["teacher"] for i in plan.items("qfit")}
        ctx.teachers = {c: t for c, t in w.teachers.items() if c in named}
    for k, v in (limits or {}).items():
        setattr(ctx, k, v)
    return ctx


# --- the ledger command (before the freeze) and the inputs stage -------------------------------------------------------------------------------------
def window_candidates(w: real_world.RealWorld, cfg: Any) -> tuple[list[Any], list[Any], list[Any]]:
    """(grid, marker spans, ordinary spans) of the validation text, the spans from BYTES (each window's token bytes found exactly once in the concatenated text)."""
    window, decision = int(cfg["panels"]["general_window_tokens"]), 64
    grid = real_world.window_grid(w.tok, w.texts["validation"], window, decision)
    spans = real_world.window_spans(grid, w.tok.token_bytes(), w.wikitext_rows["validation"])
    return grid, [s for s in spans if s.kind == "marker"], [s for s in spans if s.kind == "ordinary"]


def command_ledger(repo: Path, run_dir: Path | None, mode: str) -> dict[str, Any]:
    """THE pre-freeze ledger step: the 44 marker-like windows and the 100 ordinary windows (seed 250907; 252907 in a rehearsal) into the shared ledger (a candidate file in a rehearsal's run directory)."""
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    rd = run_dir or Path(".")
    w = build_world(cfg, repo, rd, mode, load_teachers=False, light=True)
    _grid, marker, ordinary = window_candidates(w, cfg)
    lp = ledger_path(cfg, repo, rd, mode)
    res = step8.write_study_ledger(cfg, mode, lp, marker, ordinary, row_map=real_world.RowMap.from_rows(w.wikitext_rows["validation"]))
    return {"ledger": str(lp), "sha256": file_sha256(lp), "marker_like": len(marker), "ordinary_candidates": len(ordinary), **res}


def stage_inputs(w: real_world.RealWorld, ctx: pipeline.QContext, mode: str) -> dict[str, Any]:
    """Step 1: hash checks (``build_world``), the applied generation configuration of each teacher against its pinned file, the student's conversion and the equivalence record at each read layer (gate G8), test (c) of
    the tokenizer, the corpus-level supply counts, and the shared panel ledger VERIFIED (never written here)."""
    cfg = w.cfg
    get = real_world.seed_getter(cfg, mode)
    for c, t in w.teachers.items():
        datagen.check_generation_config(t.model.generation_config, t.generation_config)  # the applied configuration equals the pinned file, else RegisteredTestStop
    w.record["generation_config"] = {c: {"pinned": t.generation_config, "applied": t.applied_generation_config} for c, t in w.teachers.items()}
    layers = tuple(int(x) for x in (4, 12))
    eq = real_world.equivalence_records(w.student, w._hf_state, w.downloads, w.tok, w.texts["train"], get, layers)  # type: ignore[attr-defined]
    w.record["equivalence"] = {k: v["at_creation"] for k, v in eq.items()}
    if not all(v["at_creation"]["logits"]["ok"] and v["at_creation"]["injection"]["ok"] for v in eq.values()):
        pipeline.fail(ctx, "gate G8: the student equivalence test failed at a read layer")
        raise RegisteredTestStop("the student equivalence test failed at a read layer (gate G8)")
    w.record["check_c"] = real_world.check_decoder_test_c(w.tok, get)
    w.record["corpus_supply"] = partition.corpus_supply(w.corpus, cfg)
    _grid, marker, ordinary = window_candidates(w, cfg)
    lp = ledger_path(cfg, w.repo, w.run_dir, mode)
    verified = step8.verify_study_ledger(cfg, lp, marker, ordinary)
    w.record["gen_windows"] = {"ledger": str(lp), "ledger_sha256": file_sha256(lp), "marker_like": len(marker), "ordinary_candidates": len(ordinary), **verified}
    rec = {**core.envelope("block_record", "Q"), "what": "inputs", "ordinary_windows_left": len(ordinary), "marker_like_windows": len(marker), **{k: v for k, v in w.record.items() if k not in ("corpus",)}}
    core.write_record(w.run_dir / "inputs/record.json", rec, overwrite=True)
    return rec


def tokenizer_record(w: real_world.RealWorld, ctx: pipeline.QContext, p: Any) -> dict[str, Any]:
    """The token ids of 100 fixed sentences per teacher (seed 250908, drawn from that capability's own generation sources) and the teacher's own translation of them (P10-S2's ``tokenizer_record``)."""
    import torch

    from . import split

    path = w.run_dir / "inputs/tokenizer_record.json"
    if path.is_file():
        return read_json(path)  # type: ignore[no-any-return]
    sp = split.split_sources(p.source_pool["A"], p.source_pool["B"], partition.source_unit_key, ctx.seeds["source_split"], ctx.allowed, float(ctx.cfg["generation"]["split_share_b"]))
    g = core.seeded_generator(ctx.seeds["teacher_tokenizer_sentences_and_digest"], "teacher tokenizer sentences", ctx.allowed)
    out: dict[str, Any] = {}
    for c in core.TASKS:
        pool = sorted(sp[c], key=lambda i: i.key)
        pick = torch.randperm(len(pool), generator=g).tolist()[:100]
        out[c] = w.teachers[c].tokenizer_record([pool[i].en for i in pick])
    write_json(path, core.jsonable(out))
    return out


def stage_outputs(w: real_world.RealWorld, ctx: pipeline.QContext, p: Any, mode: str) -> dict[str, Any]:
    """Step 8: teacher outputs on the six panels (stored, not scored); the chrF cross-check against sacrebleu; the token-id bank, tests (a) and (b), the C1 pairing; the gloss word ids for R-gloss-icl and
    tokenization test (a) on the R-gloss-icl prompts of every E_A, E_B and D_cal item; the bundle; the Part Q manifest (every output with its hash)."""
    from studies.p10s2.worldio import write_bundle

    from . import gloss

    pipeline.require_teachers_passed(ctx)
    step8.step_outputs(ctx, p)
    items = p.panels["Q_fit"]
    a_batches = [bt.read_batch(ctx.d("qfit/teacher_A"), i) for i in bt.stored_indices(ctx.d("qfit/teacher_A"))]
    outs_a = gen.outputs_of(a_batches, {it.key: it.en for it in items})[:1000]
    cross = datagen.crosscheck_chrf([(o.text, list(i.refs["A"])) for o, i in zip(outs_a, items[:1000], strict=True)])
    if not cross["ok"]:
        pipeline.fail(ctx, f"the chrF cross-check against sacrebleu differs by {cross['max_abs_difference']} (0.001 allowed)")
        raise RegisteredTestStop(f"the chrF cross-check differs by {cross['max_abs_difference']} (0.001 allowed)")
    accepted = {c: pipeline.accepted_pool(ctx, c) for c in core.TASKS}
    teacher_outputs = {c: {name: [t for b in sorted_batches(ctx, c, name) for t in b.texts] for name in step8.PANEL_OUTPUT_PANELS} for c in core.TASKS}
    max_new = real_world.max_new_from_dcal(w.tok, p, tuple(tokenize_segment(w.tok, "\n").ids))
    windows = _stored_windows(w, ctx, mode)
    spill = w.run_dir / "outputs/bank_spill.tmp"
    try:
        bundle, rec = real_bundle.make_bundle(ctx, p, w.tok, w.student, accepted, windows, w.texts["train"], teacher_outputs, max_new, spill, {"wikitext": w.record["wikitext"], "tatoeba": w.record["hashes"]["tatoeba"]})
        if not rec["required_ok"]:
            pipeline.fail(ctx, "tokenization test (a) or the combined whole-string test failed")
            raise RegisteredTestStop(f"tokenization test (a) or the combined whole-string test failed: {json.dumps(rec['tokenization'])[:400]}")
        pieces = gloss.first_task_pieces(w.tok, {"A": [*p.panels["E_A"], *p.panels["D_cal"]], "B": [*p.panels["E_B"], *p.panels["D_cal"]]})
        gb = gloss.gloss_bank(w.tok, accepted, p.vocab, pieces)  # the amended segment rule (addendum section 3); the last newline's rule is decided here from the tokenizer and the items alone and recorded in the bank
        gtest = step8.step_gloss(ctx, w.tok, {n: p.panels[n] for n in ("E_A", "E_B", "D_cal")}, set(p.vocab), bank=gb)
        if gtest["mismatches"]:
            raise RegisteredTestStop(f"tokenization test (a) on the R-gloss-icl prompts: {gtest['mismatches']} mismatches (zero required)")
        write_bundle(bundle, w.run_dir / "outputs/bundle")
        write_json(w.run_dir / "outputs/gloss_bank.json", gb)
    finally:
        spill.unlink(missing_ok=True)
    out = {"chrf_crosscheck": cross, "tokenization": rec["tokenization"], "c1_pairing": {k: v for k, v in rec["c1_pairing"].items() if k != "sigma"}, "gloss_test_mismatches": gtest["mismatches"], "bundle": str(w.run_dir / "outputs/bundle")}
    core.write_record(w.run_dir / "outputs/step8_record.json", {**core.envelope("block_record", "Q"), "what": "step8", **core.jsonable(out)}, overwrite=True)
    write_manifest(ctx)
    return out


def write_manifest(ctx: pipeline.QContext, reused: dict[str, Any] | None = None) -> dict[str, str]:
    """The Part Q manifest: every output file of the run (sealed files excluded) with its SHA-256 (section 4.1: every output is listed with its hash). Part T reads these files by hash and nothing else."""
    files = pipeline.hashes_of(ctx)
    core.write_record(ctx.d("manifest.json"), {**core.envelope("block_record", "Q"), "what": "partq_manifest", "files": files, "excluded": list(pipeline.MANIFEST_EXCLUDES), "bundle_dir": "outputs/bundle", **({"reused": {k: reused[k] for k in ("source_run_dir", "freeze_commit", "stages", "file_count", "tree_sha256")}} if reused else {})}, overwrite=True)
    if pipeline.hashes_of(ctx) != files:  # the manifest is written LAST of the outputs: nothing it lists may have changed while it was written
        raise RegisteredTestStop("the Part Q manifest does not describe the run directory it was written in (a listed file changed or a result file was written after it)")
    return files


def sorted_batches(ctx: pipeline.QContext, c: str, name: str) -> list[Any]:
    d = ctx.d(f"outputs/teacher_{c}/{name}")
    return [bt.read_batch(d, i) for i in bt.stored_indices(d)]


def _stored_windows(w: real_world.RealWorld, ctx: pipeline.QContext, mode: str) -> list[Any]:
    """The 144 stored GEN windows as ``GeneralWindow`` records: the windows the ledger recorded for this study (the ledger is the source of which windows), cut by P10-S2's own ``cut_windows``."""
    led = read_json(ledger_path(w.cfg, w.repo, w.run_dir, mode))["windows"]
    mine = {(x["start"], x["end"]) for x in led if x.get("owner") == "P10IS2-partq"}
    vocab_index = {x: i for i, x in enumerate(pipeline.partition.build_partition(w.corpus, w.cfg, ctx.seeds, ctx.allowed, sizes=ctx.sizes).vocab)}
    cut = real_world.cut_general_windows(w.tok, w.texts["validation"], vocab_index, int(w.cfg["panels"]["general_window_tokens"]), 64)
    grid, _m, _o = window_candidates(w, w.cfg)
    spans = real_world.window_spans(grid, w.tok.token_bytes(), w.wikitext_rows["validation"])
    if len(cut) != len(spans):
        raise RegisteredTestStop("the window grid and P10-S2's window cut disagree in count")
    return [win for win, s in zip(cut, spans, strict=True) if (s.start, s.end) in mine]


# --- the stage machinery ---------------------------------------------------------------------------------------------------------------------------
class Guard:
    """The deadline the pipeline asks between batches: the cumulative cap (the stage's own cap less what it used, never more than what is left of the part's total) and the memory guard (12 GiB per worker).
    ``reason`` says which tripped; True means stop (PAUSED)."""

    def __init__(self, cap_seconds: float, rss_gib_limit: float, clock: Callable[[], float] = time.monotonic, rss: Callable[[], float] = procs.rss_gib) -> None:
        self.cap, self.limit, self.clock, self.rss = cap_seconds, rss_gib_limit, clock, rss
        self.t0 = clock()
        self.reason: str | None = None

    def __call__(self) -> bool:
        if self.clock() - self.t0 >= self.cap:
            self.reason = f"cap: {self.cap:.0f} s of this stage's remaining hours used"
        elif self.rss() > self.limit:
            self.reason = f"memory: resident set above the guard of {self.limit} GiB"
        return self.reason is not None


CAP_SENTENCE = "Caps are frozen: a batch stage whose cap is spent stays PAUSED, and the only way on is a recorded new freeze by the lead; no code path extends a cap."


def require_one_mode(run_dir: Path, mode: str, led: core.Ledger) -> None:
    """A run directory belongs to ONE mode: every stage record (completion, paused, refused, running) and every ledger entry must carry the mode of the stage that now runs. A registered stage therefore refuses a
    run directory that holds any rehearsal record, a rehearsal stage one that holds a registered record, and a stage refuses a predecessor of another mode (a record without a mode counts as another mode)."""
    d = run_dir / "stages"
    for f in sorted(d.glob("*.json")) if d.is_dir() else []:
        rec = read_json(f)
        if rec.get("mode") != mode:
            raise StageRefused(f"refused: {f.name} in {run_dir} is a record of mode {rec.get('mode')!r}, and this stage runs in mode {mode!r}: a run directory holds the records of one mode only")
    other = sorted({str(e.get("run")) for e in led.entries() if e.get("run") != mode})
    if other:
        raise StageRefused(f"refused: the charged ledger of {run_dir} holds entries of mode {other}, and this stage runs in mode {mode!r}: a run directory holds one mode only")


def running_path(run_dir: Path, stage: str) -> Path:
    return run_dir / "stages" / f"{stage}.running.json"


def process_start(pid: int) -> str | None:
    """The start time of a process as ``ps`` prints it (``lstart``), or None if there is no such process. A reused process ID has another start time."""
    import subprocess

    out = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True, text=True, check=False).stdout.strip()  # noqa: S603, S607
    return out or None


def process_is_the_same(pid: int, recorded_start: str | None) -> bool:
    """True if ``pid`` is alive AND (when the marker recorded a start time) started at that time: a dead process whose ID was reused does not count as running."""
    now = process_start(pid)
    if now is None:
        return False
    return recorded_start is None or now == recorded_start


def settle_killed(run_dir: Path, stage: str, mode: str, led: core.Ledger) -> float:
    """A stage process that was killed (SIGKILL, power loss) never reached its charge. Its start marker (written at stage start, its modification time refreshed by a heartbeat every few seconds) is still there: the
    time from the start to the last heartbeat is charged now, honestly as a LOWER bound within one heartbeat interval of the true time. If the process that wrote the marker is still alive the stage is refused."""
    path = running_path(run_dir, stage)
    if not path.is_file():
        return 0.0
    rec = read_json(path)
    pid = int(rec.get("pid", 0))
    if pid and pid != os.getpid() and process_is_the_same(pid, rec.get("pid_start")):
        raise StageRefused(f"refused: process {pid} that started stage {stage!r} is still running")
    seconds = max(0.0, path.stat().st_mtime - float(rec["start_epoch"]))
    led.charge_process(stage, mode, "killed-process-lower-bound", seconds)
    path.unlink()
    return seconds


class Heartbeat:
    """Writes the start marker of a stage and refreshes its modification time every ``interval`` seconds until ``stop`` (which removes it)."""

    def __init__(self, path: Path, stage: str, mode: str, interval: float = 10.0) -> None:
        import threading

        self.path, self.interval = path, interval
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, {"stage": stage, "mode": mode, "pid": os.getpid(), "pid_start": process_start(os.getpid()), "start_utc": core.utc_stamp(), "start_epoch": time.time()})
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                os.utime(self.path)
            except OSError:
                return

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=self.interval + 1.0)
        self.path.unlink(missing_ok=True)


class PauseGuard:
    """The counting rehearsal's forced pause: the stage's own guard, which also trips once after ``after`` calls (between batches). The stop is then exactly a cap stop: PAUSED, exit 4, resumable by running the same command."""

    def __init__(self, inner: Callable[[], bool], after: int) -> None:
        self.inner, self.after, self.calls = inner, after, 0
        self.reason: str | None = None

    def __call__(self) -> bool:
        self.calls += 1
        if self.calls > self.after:
            self.reason = f"forced pause of the counting rehearsal after {self.after} guard checks"
            return True
        stop = self.inner()
        self.reason = getattr(self.inner, "reason", None)
        return stop


def completion_path(run_dir: Path, stage: str) -> Path:
    return run_dir / "stages" / f"{stage}.complete.json"


def order_of(plan: planmod.Plan | None) -> tuple[str, ...]:
    """The stages of a plan in order: the eight of a first attempt, or ``reuse.ORDER`` for a plan that reuses the completed stages of an earlier attempt."""
    return reuse.ORDER if plan is not None and (plan.data.get("inputs") or {}).get(reuse.KEY) else STAGE_ORDER


def require_prerequisites(run_dir: Path, stage: str, order: tuple[str, ...] = STAGE_ORDER) -> None:
    """Stage order is enforced: each stage runs only after its predecessor's completion record. The ``analysis`` also runs after a RECORDED ENGINEERING FAILURE (``engineering_failures.json``): a registered test of
    the data step that stopped a stage leaves no completion record, and ADR-0025 section 4.4 row 1 derives its label from the records (QUALIFICATION-ENGINEERING-FAILURE, no line derived)."""
    i = order.index(stage)
    if stage == "analysis" and (run_dir / "engineering_failures.json").is_file():
        return
    if i and not completion_path(run_dir, order[i - 1]).is_file():
        raise StageRefused(f"refused: stage {stage!r} needs {order[i - 1]!r} to be complete first (no completion record)")


def run_stage(stage: str, repo: Path, run_dir: Path, mode: str, *, plan: planmod.Plan | None = None, limits: dict[str, Any] | None = None, other_alive: Callable[[], list[str]] = procs.other_studies_alive, pause_after_batches: int | None = None) -> dict[str, Any]:
    """One stage, in this process. ``mode`` is registered or rehearsal (the counting rehearsal runs THIS function, in a fresh process per stage, with the candidate plan; its overrides are ``limits`` and ``pause_after_batches``). Returns a small record. A cap or memory stop leaves the stage PAUSED (manifest; exit 4 from the command); an error is an item error; a registered test of the data step or a
    digest mismatch leaves an engineering-failure record and stops (ruling L3)."""
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    gates.apply_platform_settings(cfg)
    order = order_of(plan)
    if stage not in order:
        raise StageRefused(f"refused: {stage!r} is not a stage of this plan ({', '.join(order)})")
    if mode in ("registered", "rehearsal") and plan is None:
        raise StageRefused("refused: a registered stage takes its parameters from the frozen plan")
    if mode in ("registered", "rehearsal"):
        require_prerequisites(run_dir, stage, order)
    total = float(plan.total_cap_seconds()) if plan is not None else 0.0
    before = float((plan.data.get("charge_before_freeze") or {}).get("seconds", 0.0)) if plan is not None else 0.0  # everything charged before the freeze counts against the total cap
    led = core.Ledger(run_dir / "charged_ledger.json", "Q", total if total > 0 else 1e12)  # in the run directory, never in the tree
    left_in_total = (total - before - led.charged()) if total > 0 else led.remaining()  # the total cap less EVERYTHING charged: before the freeze (attempts, rehearsals) and in this run directory
    if mode in ("registered", "rehearsal"):
        require_one_mode(run_dir, mode, led)
        settle_killed(run_dir, stage, mode, led)  # the time of a killed earlier process of this stage, charged now (a lower bound)
    cap = 1e12
    stage_cap_total: float | None = None
    if plan is not None:
        own = float(plan.data["stage_caps"].get(f"{stage}_hours", 0.0)) * 3600.0
        stage_cap = own if own > 0 else 1e12
        stage_cap_total = own if own > 0 else None
        cap = min(stage_cap - led.charged(stage), left_in_total)
        if cap <= 0:
            reason = "the cumulative hour cap is spent. " + CAP_SENTENCE
            man = runner.write_manifest(run_dir, "Q", stage, mode, {stage: {"status": runner.KILLED_CAP, "seconds": 0.0, "reason": reason, "peak_rss_bytes": 0}}, 0.0, identity={}, started=core.utc_stamp(), caps={"stage_seconds_left": cap})
            _mark(run_dir, stage, "PAUSED", mode=mode)
            return {"status": "PAUSED", "reason": reason, "manifest": man["status"]}
    if stage in TEACHER_GATED and mode != "rehearsal":  # a rehearsal runs every stage whatever Q1-Q4 gave (its outcome is sealed)
        why = gate_outcome(cfg, run_dir, mode, stage)
        if why is not None:  # the negative-outcome path: an explicit, recorded NOT RUN BY RULE (section 4.1 step 7), never a mis-recorded COMPLETE
            _mark(run_dir, stage, "NOT RUN BY RULE", why, mode=mode)
            return {"status": "NOT RUN BY RULE", "reason": why}
    guard: Callable[[], bool] = Guard(cap, float(cfg["caps"]["memory_per_worker_gib"]))
    if pause_after_batches is not None:
        if mode != "rehearsal":
            raise StageRefused("refused: a forced pause exists in a rehearsal only")
        guard = PauseGuard(guard, pause_after_batches)
    holder: dict[str, Any] = {"ctx": None}

    reuse_block = (plan.data.get("inputs") or {}).get(reuse.KEY) if plan is not None else None

    def body() -> dict[str, Any]:
        out = body_inner()
        if reuse_block:
            reuse.verify_block(reuse_block)  # the reused files are still, byte for byte, what the plan listed: no stage of this attempt wrote into them
        return out

    def body_inner() -> dict[str, Any]:
        if stage == "reuse":
            if not reuse_block:
                raise StageRefused("refused: this plan reuses no earlier stage")
            return reuse.link_and_record(reuse_block, run_dir, mode)
        if stage == "analysis":
            if plan is not None:
                pkgmanifest.verify_inputs(plan.data["inputs"], uses_packages=False, repo=repo)
            ctx = holder["ctx"] = _light_ctx(cfg, run_dir, mode)
            res = labels.part_q_label(pipeline.facts_of(ctx))
            core.write_record(run_dir / pipeline.loc(ctx, "qualification.json"), {**core.envelope("qualification", "Q"), **{k: v for k, v in res.items() if k != "oracle_line"}}, overwrite=True)
            write_manifest(ctx, reuse_block)
            return {"label": res["label"], "part_t": res["part_t"]} if mode == "registered" else pipeline.summary_for_display(ctx)
        t_world = time.monotonic()
        w = build_world(cfg, repo, run_dir, mode, load_teachers=True, plan=plan)
        ctx = holder["ctx"] = make_ctx(w, mode, plan=plan, limits=limits, deadline=guard, inputs_stage=stage == "inputs")
        holder["overhead"] = time.monotonic() - t_world  # the fixed per-process cost of every stage that needs the world (checks, hashing, corpus, student, teachers): the caps rule keeps it apart from the per-unit rate
        if guard():  # the phases before the first batch are not guarded between batches: check the resident set and the cap once the world stands
            raise StageCapExceeded(guard.reason or "guard")
        if stage == "inputs":
            return stage_inputs(w, ctx, mode)
        p = pipeline.step_partition(ctx)
        if stage == "partition":
            return {"counts": p.counts, "tokenizer_record": bool(tokenizer_record(w, ctx, p))}
        if stage == "qfit":
            return pipeline.step_qfit(ctx, p)
        if stage == "qcheck":
            return pipeline.step_qcheck(ctx, p, pipeline.step_qfit(ctx, p))
        if stage == "generation":
            return pipeline.step_generation(ctx, p, pipeline.step_qfit(ctx, p))
        if stage == "regeneration":
            return pipeline.step_regeneration(ctx, p)
        return stage_outputs(w, ctx, p, mode)

    return execute(stage, run_dir, mode, led, guard, cap, body, holder, other_alive, stage_cap_total=stage_cap_total, prior_charged=led.charged(stage))


def execute(stage: str, run_dir: Path, mode: str, led: core.Ledger, guard: Callable[[], bool], cap: float, body: Callable[[], dict[str, Any]], holder: dict[str, Any], other_alive: Callable[[], list[str]] = procs.other_studies_alive, *, stage_cap_total: float | None = None, prior_charged: float = 0.0, heartbeat_seconds: float = 10.0) -> dict[str, Any]:
    """Runs a stage body and records how it ended, each ending its own way:
    * COMPLETE: the completion record and a COMPLETE manifest;
    * PAUSED (a cap or memory stop): a PAUSED manifest, no completion record, resumable;
    * a REFUSAL (``StageRefused``: an environment, pin, ledger or precondition refusal): NO completion record and NO COMPLETE manifest: the stage can be run again once the cause is fixed;
    * an engineering failure (digest mismatch, registered test of the data step): ``engineering_failures.json`` and no completion record;
    * any other error: an item error and no completion record.
    The wall time of this process is charged in every case (ruling L2); a process that is killed is charged by the next one from its start marker. A COMPLETE record carries ``within_cap``: false (and a warning on
    stderr) when the stage's whole charge ended above its cap, which the stages without a guard between batches (partition, regeneration, analysis) can do: never silent."""
    t0 = time.monotonic()
    started = core.utc_stamp()
    status, out = "COMPLETE", {}
    reason = None
    beat = Heartbeat(running_path(run_dir, stage), stage, mode, heartbeat_seconds) if mode in ("registered", "rehearsal") else None
    try:
        out = body()
    except StageCapExceeded:
        status = "PAUSED"
        why = getattr(guard, "reason", None) or "the cap was reached"
        out = {"reason": why + (". " + CAP_SENTENCE if why.startswith("cap") else "")}
    except (DigestMismatch, RegisteredTestStop) as e:
        if holder.get("ctx") is not None and not holder["ctx"].engineering_failures:
            pipeline.fail(holder["ctx"], f"{type(e).__name__}: {e}")
        status = "ENGINEERING-FAILURE"
        raise
    except StageRefused as e:
        status, reason = "REFUSED", str(e)
        raise
    except Exception as e:  # noqa: BLE001 - a code or environment error is an item error, never a scientific label
        if holder.get("ctx") is not None:
            pipeline.record_item_error(holder["ctx"], stage, f"{type(e).__name__}: {e}")
        status = "ITEM-ERROR"
        raise
    finally:
        seconds = time.monotonic() - t0
        led.charge_process(stage, mode, "main", seconds)  # the wall time of this process (ruling L2), also when it stopped
        if beat is not None:
            beat.stop()  # the charge above is written: the start marker is no longer needed
        extra: dict[str, Any] = {}
        if status == "COMPLETE":
            total_seconds = prior_charged + seconds
            within = None if stage_cap_total is None else total_seconds <= stage_cap_total
            extra = {"stage_seconds": total_seconds, "stage_cap_seconds": stage_cap_total, "within_cap": within, "overhead_seconds": float(holder.get("overhead", 0.0)), "process_seconds": seconds}
            if within is False:
                print(f"WARNING: stage {stage} took {total_seconds:.0f} s in all, above its cap of {stage_cap_total:.0f} s: within_cap false is recorded", file=sys.stderr)
        if status != "REFUSED":
            greason = getattr(guard, "reason", None)
            key = runner.COMPLETED if status == "COMPLETE" else (runner.KILLED_RSS if greason and greason.startswith("memory") else (runner.KILLED_CAP if status == "PAUSED" else runner.FAILED))
            runner.write_manifest(run_dir, "Q", stage, mode, {stage: {"status": key, "seconds": seconds, "reason": greason or status, "peak_rss_bytes": int(procs.rss_gib() * 2**30)}}, seconds, identity={}, started=started, caps={"stage_seconds_left": cap}, extra={"other_studies_alive": other_alive()})
            _mark(run_dir, stage, status, mode=mode, extra=extra)
        else:
            _mark(run_dir, stage, "REFUSED", reason, mode=mode)
    return {"status": status, **({"result": out} if status == "COMPLETE" else out)}


def gate_outcome(cfg: Any, run_dir: Path, mode: str, stage: str) -> str | None:
    """Section 4.1 step 7 and section 4.4: generation, regeneration and the outputs run only if BOTH teachers pass Q1-Q4 (and the regeneration and the outputs only if generation reached a draws label). Returns the
    reason a stage is NOT RUN BY RULE, or None if it runs. Decided from the records alone (no world is built); it is the registered path to a negative Part Q label."""
    ctx = _light_ctx(cfg, run_dir, mode)
    if not completion_path(run_dir, "qcheck").is_file():
        return None  # the prerequisite check says what is missing
    f = pipeline.facts_of(ctx)
    for c in core.TASKS:
        st = labels.teacher_status(f["teachers"][c])
        if st["failed"] or st["reserve_exhausted"] or f["teachers"][c]["q4"] is None:
            return f"teacher {c} did not pass Q1-Q4 or its Q_check did not reach 150 accepted items: generation and what follows do not run (section 4.1 step 7); the Part Q label is derived from the records by the analysis"
    if stage in ("regeneration", "outputs"):
        gres = pipeline._have(ctx, "generation/result.json") or {}
        if gres.get("draws_label") == "DATA-EXHAUSTED":
            return "a pool ended below 10,000 accepted sources (DATA-EXHAUSTED): no regeneration check and no outputs (section 4.3 rule 6)"
    return None


def _mark(run_dir: Path, stage: str, status: str, reason: str | None = None, mode: str = "registered", extra: dict[str, Any] | None = None) -> None:
    """The stage's state for the order check and for ``pipeline.paused_stages``. COMPLETE and NOT RUN BY RULE both complete the stage for the order check (the second says why nothing ran); PAUSED is a state, not
    an outcome; a REFUSED or failed stage leaves NO completion record."""
    d = run_dir / "stages"
    d.mkdir(parents=True, exist_ok=True)
    if status in ("COMPLETE", "NOT RUN BY RULE"):
        write_json(completion_path(run_dir, stage), {"stage": stage, "status": status, "mode": mode, "reason": reason, "utc": core.utc_stamp(), **(extra or {})})
        (d / f"{stage}.json").unlink(missing_ok=True)
    elif status == "PAUSED":
        write_json(d / f"{stage}.json", {"stage": stage, "status": "PAUSED", "mode": mode, "utc": core.utc_stamp()})
    else:
        (d / f"{stage}.json").unlink(missing_ok=True)
        if status == "REFUSED":
            write_json(d / f"{stage}.refused.json", {"stage": stage, "status": "REFUSED", "mode": mode, "reason": reason, "utc": core.utc_stamp()})  # a record of the refusal; it blocks nothing


def _light_ctx(cfg: Any, run_dir: Path, mode: str) -> pipeline.QContext:
    """The context of the analysis: records only, no corpus, no model, no package."""
    return pipeline.QContext(cfg=cfg, mode=mode, corpus=None, teachers={}, student_scores=lambda items, p: {}, run_dir=run_dir)  # type: ignore[arg-type]


__all__ = ["planmod", "run_stage", "write_manifest"]
