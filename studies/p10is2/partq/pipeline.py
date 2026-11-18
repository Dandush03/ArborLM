# ruff: noqa: E501
"""Part Q's steps over injected interfaces (ADR-0025 section 4.1): partition and fixed-input counts, teachers on Q_fit (Q1, Q2, Q3), Q_check (Q4), generation, the regeneration check, the label.

Everything real (the corpus, the Marian teachers, the student, the tokenizer) is injected through ``QContext``; the tests inject a synthetic corpus, ``FakeTeacher`` and a stub student. Each step writes
its record atomically in the run directory and is skipped when its record exists (resumable). A teacher that fails Q1 or Q2 still has Q3 and Q4 run; a failed Q3 leaves it without Q4 (ruling G15). Step 7
(generation) runs only if BOTH teachers pass Q1-Q4. Nothing here reads a sealed value: in rehearsal mode the values of Q1-Q4 and every per-item score are written to ``sealed/`` and the returned summary holds only
the whitelist (ruling L5).
"""

import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json
from studies.p10s2.data import CorpusLike, Item, TrainItem
from studies.p10s2.filtering import FilterSetting, accepts
from studies.p10s2.text import normalize

from ..common import core
from . import batches as bt
from . import generation as gen
from . import labels, partition, qualify, split
from .teacher import BatchTeacher

# the whitelist of ruling L5: what a sealed (rehearsal) run may show
WHITELIST = ("timings", "memory", "counts", "yields", "filter_setting", "batches", "sources")


@dataclass
class QContext:
    cfg: Mapping[str, Any]
    mode: str  # "test" | "rehearsal" | "registered"
    corpus: CorpusLike
    teachers: Mapping[str, BatchTeacher]
    student_scores: Callable[[Sequence[Item], Any], Mapping[str, float]]  # (Q_fit items, the partition): the untrained student's mean chrF-norm on the Q_fit items, per capability
    run_dir: Path
    sizes: Mapping[str, int] | None = None  # panel size overrides (tests only)
    batch_size: int | None = None
    block_sources: int | None = None
    check_target: int | None = None
    accepted_min: int | None = None
    accepted_disjoint: int | None = None
    per_replicate: int | None = None
    regeneration_batches: int | None = None
    digest_batches: int | None = None
    max_generation_blocks: int | None = None  # rehearsals: limited blocks per capability
    max_check_blocks: int | None = None  # rehearsals: one Q_check block
    seal: bool | None = None  # None: sealed exactly in rehearsal mode; tests set it to exercise the sealing on test-range seeds
    deadline: Callable[[], bool] | None = None
    ordinary_windows_left: int | None = None
    marker_like_windows: int | None = None
    force_generation: bool = False  # REHEARSALS ONLY: run qcheck, generation, regeneration and the outputs whatever Q1-Q4 give (a fallback filter setting if Q3 gives none), so that the sealed outcome is not revealed by which stages ran
    engineering_failures: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)  # seconds spent in this invocation by stage (the measuring rehearsal's rates)

    @property
    def seeds(self) -> dict[str, int]:
        return core.partq_seeds(self.cfg, self.mode)

    @property
    def allowed(self) -> frozenset[int]:
        s = self.seeds
        return frozenset(s.values()) | (core.test_range(self.cfg) if self.mode == "test" else frozenset())

    @property
    def size(self) -> int:
        return self.batch_size or int(self.cfg["generation"]["batch_size"])

    def d(self, p: str) -> Path:
        return self.run_dir / p

    @property
    def sealed(self) -> bool:
        return self.mode == "rehearsal" if self.seal is None else self.seal


def loc(ctx: QContext, name: str) -> str:
    """The path of a record. In a sealed (rehearsal) run every record that holds a quality value, a pass or a fail, or the label goes under ``sealed/`` (ruling L5); the others keep their place."""
    if not ctx.sealed:
        return name
    if name == "qfit/record.json":
        return "sealed/qfit_record.json"
    if name == "qualification.json":
        return "sealed/qualification.json"
    m = re.fullmatch(r"qcheck/teacher_([AB])/result\.json", name)
    if m:
        return f"sealed/qcheck_{m[1]}_result.json"
    return name


def _rec(ctx: QContext, name: str, what: str, body: Mapping[str, Any]) -> dict[str, Any]:
    rec = {**core.envelope("sealed" if (ctx.sealed and what == "values") else "block_record", "Q"), "what": what, **body}
    path = ctx.d(loc(ctx, name))
    if not path.exists():
        core.write_record(path, rec)
    return read_json(path)  # type: ignore[no-any-return]


def fail(ctx: QContext, message: str) -> None:
    """A failure on study-produced data (a gate, a digest or regeneration difference, a tokenization test): kept in memory and in ``engineering_failures.json`` so a resume still sees it."""
    ctx.engineering_failures.append(message)
    core.write_record(ctx.d("engineering_failures.json"), {**core.envelope("block_record", "Q"), "what": "engineering_failures", "failures": list(ctx.engineering_failures)}, overwrite=True)


def _have(ctx: QContext, name: str) -> dict[str, Any] | None:
    p = ctx.d(loc(ctx, name))
    return read_json(p) if p.is_file() else None  # type: ignore[no-any-return]


# --- steps 2-4: partition, fixed-input counts, pools -------------------------------------------------------------------------------------------
def step_partition(ctx: QContext) -> partition.QPartition:
    """Steps 2-4. The partition is a pure function of the corpus and the listed seeds, so it is recomputed (not stored) at each resume; the counts record is written once."""
    p = partition.build_partition(ctx.corpus, ctx.cfg, ctx.seeds, ctx.allowed, sizes=ctx.sizes)
    problems = partition.fixed_input_problems(p, ctx.cfg, ordinary_windows_left=ctx.ordinary_windows_left, marker_like_windows=ctx.marker_like_windows, sizes=ctx.sizes)
    _rec(ctx, "partition_counts.json", "counts", {"counts": p.counts, "problems": problems})
    return p


def fixed_input_problems_recorded(ctx: QContext) -> list[str]:
    rec = _have(ctx, "partition_counts.json")
    return list(rec["problems"]) if rec else []


# --- step 5: teachers on Q_fit; Q1, Q2, Q3 -----------------------------------------------------------------------------------------------------
def _refs(it: Item, cap: str) -> list[str]:
    return list(it.refs[cap])


def fallback_setting(ctx: QContext) -> FilterSetting:
    """The most permissive setting of the grid (the smallest tau, the wider range): used ONLY by a rehearsal that must exercise generation whatever Q3 gives. Its use is not a result and is sealed with the rest."""
    q = ctx.cfg["quality"]
    return FilterSetting(round(min(float(t) for t in q["tau_grid"]), 2), float(q["ratio_ranges"][0][0]), float(q["ratio_ranges"][0][1]))


def require_teachers_passed(ctx: QContext) -> None:
    """Generation, regeneration and step 8 run only if BOTH teachers pass Q1-Q4 (section 4.1 step 7). A rehearsal (``force_generation``) is exempt: its outcome is sealed."""
    if ctx.force_generation:
        return
    f = facts_of(ctx)
    for c in core.TASKS:
        st = labels.teacher_status(f["teachers"][c])
        if st["failed"] or st["reserve_exhausted"] or f["teachers"][c]["q4"] is None:
            raise core.StageRefused(f"refused: generation runs only if both teachers pass Q1-Q4 (teacher {c} has not): step 7 of section 4.1")


def item_error_files(ctx: QContext) -> list[str]:
    d = ctx.d("item_errors")
    return sorted(str(p.name) for p in d.glob("*.json")) if d.is_dir() else []


def record_item_error(ctx: QContext, stage: str, message: str) -> None:
    """A code or environment error inside a stage is an ITEM ERROR the analysis refuses on (section 8.6); it is never a scientific label."""
    d = ctx.d("item_errors")
    d.mkdir(parents=True, exist_ok=True)
    core.write_record(d / f"{stage}.json", {**core.envelope("item_error", "Q"), "stage": stage, "message": message[:2000]}, overwrite=True)


def paused_stages(ctx: QContext) -> list[str]:
    d = ctx.d("stages")
    out = []
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        try:
            rec = read_json(p)
        except Exception:  # noqa: BLE001
            continue
        if rec.get("status") == "PAUSED":
            out.append(p.stem)
    return out


def step_qfit(ctx: QContext, p: partition.QPartition) -> dict[str, Any]:
    """Both teachers on the whole Q_fit in the frozen layout; the digest batches; Q1, Q2 (needs both), Q3. Every per-item input is stored (rule 8). A resume re-asserts each teacher's digest by regeneration."""
    done = _have(ctx, "qfit/record.json")
    items = p.panels["Q_fit"]
    keys, srcs = [i.key for i in items], [i.en for i in items]
    src_of = dict(zip(keys, srcs, strict=True))
    runs: dict[str, list[bt.StoredBatch]] = {}
    for c in core.TASKS:
        runs[c] = bt.run_stream(ctx.teachers[c], ctx.d(f"qfit/teacher_{c}"), keys, srcs, size=ctx.size, deadline=ctx.deadline)
    n_batches = len(runs["A"])
    idx = bt.draw_batch_indices(n_batches, ctx.digest_batches or int(ctx.cfg["generation"]["digest_batches"]), ctx.seeds["teacher_tokenizer_sentences_and_digest"], ctx.allowed, "digest batches")
    digests = {c: {"indices": idx, "sha256": bt.digest_of([runs[c][i] for i in idx])} for c in core.TASKS}
    if done is not None:  # a resume: the recorded digest is asserted by regeneration
        for c in core.TASKS:
            bt.resume_digest_check(ctx.teachers[c], {b.index: b for b in runs[c]}, done["digests"][c]["indices"], src_of, done["digests"][c])
        return done
    outs = {c: gen.outputs_of(runs[c], src_of) for c in core.TASKS}
    scores: dict[str, dict[str, list[float]]] = {t: {} for t in core.TASKS}  # teacher -> capability -> per-item chrF
    for t in core.TASKS:
        for c in core.TASKS:
            scores[t][c] = qualify.item_scores(outs[t], [_refs(i, c) for i in items])
    mean = {t: {c: (sum(v) / len(v) if v else 0.0) for c, v in scores[t].items()} for t in core.TASKS}
    student = dict(ctx.student_scores(items, p))
    q1 = qualify.q1({c: mean[c][c] for c in core.TASKS}, ctx.cfg)
    q2 = qualify.q2(mean, student, ctx.cfg)
    grids, q3 = {}, {}
    for c in core.TASKS:
        table = qualify.grid_table(outs[c], scores[c][c], ctx.cfg)  # teacher c on capability c's references
        grids[c], q3[c] = table, qualify.select_filter(table, ctx.cfg)
    per_item = {t: [{"key": k, "text": o.text, "score": o.score, "chrf_own": scores[t][t][n], "accepted": None if q3[t].setting is None else accepts(o, q3[t].setting)} for n, (k, o) in enumerate(zip(keys, outs[t], strict=True))] for t in core.TASKS}
    values = {
        "q1": q1, "q2": q2, "mean_chrf": mean, "student": student, "q3": {c: q3[c].to_json() for c in core.TASKS}, "grid": grids, "per_item": per_item,
    }  # fmt: skip
    _rec(ctx, "qfit/values.json" if not ctx.sealed else "sealed/qfit_values.json", "values", values)
    summary = {
        "digests": digests, "n_batches": n_batches, "q1": q1, "q2": {c: bool(q2[c]["pass"]) for c in core.TASKS}, "q3": {c: q3[c].setting is not None for c in core.TASKS},
        "filter_setting": {c: (fallback_setting(ctx).to_json() if (q3[c].setting is None and ctx.force_generation) else (None if q3[c].setting is None else q3[c].setting.to_json())) for c in core.TASKS}, "accepted_on_qfit": {c: q3[c].accepted for c in core.TASKS},
        "yields_on_qfit": {c: q3[c].accepted / max(1, len(items)) for c in core.TASKS}, "sealed": ctx.sealed,
    }  # fmt: skip
    return _rec(ctx, "qfit/record.json", "qfit", summary)


# --- step 6: Q_check ---------------------------------------------------------------------------------------------------------------------------
def step_qcheck(ctx: QContext, p: partition.QPartition, qfit: Mapping[str, Any]) -> dict[str, Any]:
    """Q_check per teacher by the three stopping rules. Runs for a teacher that failed Q1 or Q2 (G15); a failed Q3 leaves that teacher without Q4."""
    out: dict[str, Any] = {}
    blocks = p.reserve_blocks[: ctx.max_check_blocks] if ctx.max_check_blocks is not None else p.reserve_blocks
    target = ctx.check_target or int(ctx.cfg["quality"]["q4_min_accepted"])
    for c in core.TASKS:
        existing = _have(ctx, f"qcheck/teacher_{c}/result.json")
        if existing is not None:
            out[c] = existing
            continue
        fs = qfit["filter_setting"][c]
        if fs is None:
            out[c] = _rec(ctx, f"qcheck/teacher_{c}/result.json", "qcheck", {"ran": False, "reason": "Q3 failed: no setting to fix (G15: a failed Q3 leaves the teacher without Q4)"})
            continue
        setting = FilterSetting(fs["tau"], fs["rho1"], fs["rho2"])
        d = ctx.d(f"qcheck/teacher_{c}")
        count = gen.count_phase(ctx.teachers[c], blocks, setting, d, target=target, size=ctx.size, deadline=ctx.deadline)
        stop_path = d / "stop.json"
        gen.record_stop(stop_path, count)  # BEFORE any reference is read
        res = gen.finalize(ctx.teachers[c], blocks, count, setting, d, stop_path, lambda it, c=c: it.refs[c], ctx.cfg, size=ctx.size)
        scores = res.pop("items_per_item_scores")
        _rec(ctx, f"sealed/qcheck_{c}_values.json" if ctx.sealed else f"qcheck/teacher_{c}/values.json", "values", {"result": res, "per_item_chrf": scores})
        out[c] = _rec(ctx, f"qcheck/teacher_{c}/result.json", "qcheck", {"ran": True, "stop": count.to_json(), "accepted": res["accepted"], "read_ok": res["read_ok"], "pass": res["pass"], "reserve_exhausted": count.exhausted, "sealed": ctx.sealed})
    return out


# --- step 7: generation ------------------------------------------------------------------------------------------------------------------------
def step_generation(ctx: QContext, p: partition.QPartition, qfit: Mapping[str, Any]) -> dict[str, Any]:
    """Rules 4-6. Runs only when both teachers pass Q1-Q4 (the caller checks). The split, the seeded block order, generate until met, then the draws rule."""
    done = _have(ctx, "generation/result.json")
    if done is not None:
        return done
    require_teachers_passed(ctx)
    sp = split.split_sources(p.source_pool["A"], p.source_pool["B"], partition.source_unit_key, ctx.seeds["source_split"], ctx.allowed, float(ctx.cfg["generation"]["split_share_b"]))
    orders = gen.source_orders(len(sp["A"]), len(sp["B"]), ctx.seeds["source_block_order"], ctx.allowed)
    eval_norm = {normalize(r) for name in ("E_A", "E_B", "E_C", "E_open") for it in p.panels[name] for refs in it.refs.values() for r in refs}
    g = ctx.cfg["generation"]
    results: dict[str, gen.GenerationResult] = {}
    for c in core.TASKS:
        fs = qfit["filter_setting"][c]
        results[c] = gen.generate_until_met(
            ctx.teachers[c], c, sp[c], orders[c], FilterSetting(fs["tau"], fs["rho1"], fs["rho2"]), ctx.d(f"generation/teacher_{c}"), eval_norm, target=ctx.accepted_disjoint or int(g["accepted_disjoint"]),
            block_sources=ctx.block_sources or int(g["generation_block_sources"]), size=ctx.size, max_blocks=ctx.max_generation_blocks, deadline=ctx.deadline,
        )  # fmt: skip
    counts = {c: len(results[c].accepted) for c in core.TASKS}
    cfg2 = _with_targets(ctx)
    label = split.draws_label(counts, cfg2)
    body: dict[str, Any] = {"split": sp["counts"], "counts": counts, "per_capability": {c: results[c].counts() for c in core.TASKS}, "draws_label": label, "yields": {c: len(results[c].accepted) / max(1, results[c].sources) for c in core.TASKS}}
    pools = {c: [{"key": x.key, "en": x.en, "target": x.target, "group": x.group} for x in results[c].accepted] for c in core.TASKS}
    _rec(ctx, "generation/pools.json", "pools", {"pools": pools})
    if label == split.DISJOINT and ctx.mode == "rehearsal":
        body["draws"] = None
        body["draws_note"] = "the permutation seeds 250916 and 250917 are registered-mode seeds; the rehearsal range has none, so no draw is made in a rehearsal"
    elif label == split.DISJOINT:  # the permutations belong to Part Q (seeds 250916, 250917); OVERLAPPING draws use Part T's training-draw seeds and are made by Part T from the stored pools
        body["draws"] = split.make_draws(counts, cfg2, ctx.seeds, [], ctx.allowed).to_json()
    elif label == split.OVERLAPPING:
        body["draws"] = None
        body["draws_note"] = "each replicate draws 8,000 with its own training-draw seed (base + 1) from the whole pool; Part T makes the draws from the stored pools and prints the shared share beside every line that says every cell"
    return _rec(ctx, "generation/result.json", "generation", body)


def _with_targets(ctx: QContext) -> dict[str, Any]:
    cfg = {k: dict(v) if isinstance(v, Mapping) else v for k, v in ctx.cfg.items()}
    if ctx.accepted_min is not None:
        cfg["generation"]["accepted_min"] = ctx.accepted_min
    if ctx.accepted_disjoint is not None:
        cfg["generation"]["accepted_disjoint"] = ctx.accepted_disjoint
    if ctx.per_replicate is not None:
        cfg["generation"]["per_replicate"] = ctx.per_replicate
    return cfg


def accepted_pool(ctx: QContext, capability: str) -> list[TrainItem]:
    rec = read_json(ctx.d("generation/pools.json"))
    return [TrainItem(x["key"], x["en"], x["target"], int(x["group"])) for x in rec["pools"][capability]]


# --- step 7b: regeneration check ----------------------------------------------------------------------------------------------------------------
def step_regeneration(ctx: QContext, p: partition.QPartition) -> dict[str, Any]:
    """After generation has ended: 32 whole generation batches per teacher, a fresh generator seeded 250914 for each teacher, regenerated in the stored composition and order; zero tolerance on tokens."""
    done = _have(ctx, "regeneration.json")
    if done is not None:
        return done
    require_teachers_passed(ctx)
    gres = _have(ctx, "generation/result.json") or {}
    if gres.get("draws_label") == split.EXHAUSTED and not ctx.force_generation:
        raise core.StageRefused("refused: no regeneration check: a pool ended below the minimum (DATA-EXHAUSTED); generation did not complete")
    report: dict[str, Any] = {}
    n_regen = ctx.regeneration_batches or int(ctx.cfg["generation"]["regeneration_batches"])
    src_of = {it.key: it.en for pool in p.source_pool.values() for it in pool}
    for c in core.TASKS:
        order: list[tuple[Path, int]] = []  # (block directory, batch index), by file name only: no batch is read yet
        for blockdir in sorted(ctx.d(f"generation/teacher_{c}").glob("block_*")):
            order += [(blockdir, i) for i in bt.stored_indices(blockdir)]
        idx = bt.draw_batch_indices(len(order), n_regen, ctx.seeds["regeneration_subsample"], ctx.allowed, f"regeneration subsample, teacher {c}")  # a FRESH generator per teacher, same seed
        stored = {i: bt.read_batch(order[i][0], order[i][1]) for i in idx}  # only the drawn batches are read
        rep = bt.regeneration_check(ctx.teachers[c], stored, idx, src_of, score_tolerance=float(ctx.cfg["scoring"]["regeneration_score_tolerance"]), threads=int(ctx.cfg["generation"]["threads"]))
        report[c] = rep.to_json()
        if not rep.ok:
            fail(ctx, f"regeneration difference, teacher {c}: batch {rep.token_mismatches[0]['batch']} item {rep.token_mismatches[0]['item']}")
    return _rec(ctx, "regeneration.json", "regeneration", {"teachers": report, "ok": all(report[c]["ok"] for c in core.TASKS)})


# --- the label ---------------------------------------------------------------------------------------------------------------------------------
def facts_of(ctx: QContext) -> dict[str, Any]:
    """The facts ``labels.part_q_label`` reads, from the records on disk."""
    qf = _have(ctx, "qfit/record.json")
    teachers: dict[str, Any] = {}
    for c in core.TASKS:
        q4 = _have(ctx, f"qcheck/teacher_{c}/result.json")
        teachers[c] = {
            "q1": None if qf is None else qf["q1"][c], "q2": None if qf is None else qf["q2"][c], "q3": None if qf is None else qf["q3"][c],
            "q4": None if not q4 or not q4.get("ran") else {"read_ok": q4["read_ok"], "pass": q4["pass"]}, "reserve_exhausted": bool(q4 and q4.get("reserve_exhausted")),
        }  # fmt: skip
    g = _have(ctx, "generation/result.json")
    reg = _have(ctx, "regeneration.json")
    stored = _have(ctx, "engineering_failures.json")
    failures = list(dict.fromkeys([*(stored["failures"] if stored else []), *ctx.engineering_failures]))
    if reg is not None and not reg["ok"]:
        failures.append("regeneration difference")
    return {
        "engineering_failure": failures, "data_insufficient": fixed_input_problems_recorded(ctx), "teachers": teachers, "pools": None if g is None else g["counts"], "draws": None if g is None else g["draws_label"],
        "item_errors": item_error_files(ctx), "paused": paused_stages(ctx),
    }  # fmt: skip


def timed(ctx: QContext, stage: str, fn: Callable[[], Any]) -> Any:
    """Runs one step and adds its wall time (also when it stops on a cap) to ``ctx.timings[stage]``."""
    t0 = time.monotonic()
    try:
        return fn()
    finally:
        ctx.timings[stage] = ctx.timings.get(stage, 0.0) + (time.monotonic() - t0)


def run_all(ctx: QContext) -> dict[str, Any]:
    """Steps 2-7 in order, each complete before the next starts. Returns the label result. A teacher that failed Q1 or Q2 still has Q3 and Q4 run; generation runs only if both pass everything. A digest mismatch at a
    resume is QUALIFICATION-ENGINEERING-FAILURE (recorded, then the label is derived); a stop on the cap propagates (PAUSED)."""
    try:
        return _run_all(ctx)
    except bt.DigestMismatch as e:
        fail(ctx, f"digest mismatch at a resume: {e}")
        return labels.part_q_label(facts_of(ctx))


def _run_all(ctx: QContext) -> dict[str, Any]:
    p = timed(ctx, "partition", lambda: step_partition(ctx))
    if fixed_input_problems_recorded(ctx):
        return labels.part_q_label(facts_of(ctx))
    qf = timed(ctx, "qfit", lambda: step_qfit(ctx, p))
    timed(ctx, "qcheck", lambda: step_qcheck(ctx, p, qf))
    f = facts_of(ctx)
    both = ctx.force_generation or all(not labels.teacher_status(f["teachers"][c])["failed"] and not labels.teacher_status(f["teachers"][c])["reserve_exhausted"] and f["teachers"][c]["q4"] is not None for c in core.TASKS)
    if both:
        timed(ctx, "generation", lambda: step_generation(ctx, p, qf))
        if (_have(ctx, "generation/result.json") or {}).get("draws_label") != split.EXHAUSTED:
            timed(ctx, "regeneration", lambda: step_regeneration(ctx, p))
    result = labels.part_q_label(facts_of(ctx))
    core.write_record(ctx.d(loc(ctx, "qualification.json")), {**core.envelope("qualification", "Q"), **{k: v for k, v in result.items() if k != "oracle_line"}}, overwrite=True)
    return result


def summary_for_display(ctx: QContext) -> dict[str, Any]:
    """Ruling L5: through a whitelist, the summary a sealed (rehearsal) run may print: filter setting, yields, batches, counts. No value of Q1-Q4 and no per-item score."""
    qf = _have(ctx, "qfit/record.json") or {}
    g = _have(ctx, "generation/result.json") or {}
    pc = _have(ctx, "partition_counts.json") or {}
    return {"filter_setting": qf.get("filter_setting"), "yields": {"qfit": qf.get("yields_on_qfit"), "generation": g.get("yields")}, "counts": {"partition": pc.get("counts"), "pools": g.get("counts")}, "batches": qf.get("n_batches")}


def hashes_of(ctx: QContext) -> dict[str, str]:
    """SHA-256 of every file of the run directory except sealed ones, for the Part Q manifest (every output is listed with its hash)."""
    return {str(f.relative_to(ctx.run_dir)): file_sha256(f) for f in sorted(ctx.run_dir.rglob("*")) if f.is_file() and "sealed" not in f.parts}


__all__ = ["QContext", "WHITELIST", "run_all", "step_generation", "step_partition", "step_qcheck", "step_qfit", "step_regeneration", "summary_for_display"]
