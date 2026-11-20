# ruff: noqa: E501
"""Scoring on CPU and the step from scored snapshots to the registry (ADR-0025 sections 5.2, 5.5, 8.1; ruling L5, G6).

Re-uses P10-S2's scoring unedited: ``evaluate.score_panel`` (greedy decoding, one item at a time, a fixed composition), ``memory_ablations`` (memory off, values permuted, word codes permuted, marker-only,
words-only on the 300-item subsample, each permutation from a fresh +4 generator), ``general_quality`` (the keyword router, both decision positions), the router and the retrieval baselines, and
``combined.score_combined_cell`` (C1 and C2). New: the reads this study's registry keys name (``quantities``), the lookup baseline R-gloss-icl, the sub-sample baselines, the modification measure and the
registry builder. Every read runs under ``torch.no_grad()`` and on CPU. The frozen scoring is repeated bit-identically (gate G2).
"""

import contextlib
import time
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import torch

from studies.p10s2 import retrieval
from studies.p10s2.evaluate import PanelData, general_quality, memory_ablations, score_panel
from studies.p10s2.memory import Arm, MemoryArm, NullArm
from studies.p10s2.routing import Router, train_router
from studies.p10s2.text import chrf_item, mean, normalize

from .common import core
from .engine import AppendLoRAArm, WorldT
from .quantities import NONE, PANEL, Registry, key

COND = {"unablated": "own", "value_perm": "value", "code_perm": "code", "marker_only": "marker", "words_only": "words"}
CONTROL_STAGES = {"M1": [0], "M-append": [1], "M-seq": [0], "M-ii": [0, 1], "M-joint": [0]}
GEN_ARMS = ("M1", "M-append", "M-seq", "M-ii", "D-seq")
TWO = core.TASKS


EVALUATION_FORBIDDEN_MODES = ("rehearsal", "calibration")  # section 4.1: E_A, E_B, E_C and E_open are NEVER scored before the registered run of Part T (rulings 1 and 2)


def require_evaluation_allowed(world: WorldT) -> None:
    """The code REFUSES to score an evaluation panel (E_A, E_B, E_C, E_open) outside a registered stage: a rehearsal and a calibration score D_cal only (audit B2, ruling 1)."""
    if getattr(world, "evaluation_is_d_cal", False):  # a rehearsal world built by ``partt_rehearsal.rehearsal_bundle`` holds no evaluation item: its E_A, E_B and E_C ARE D_cal
        return
    if getattr(world, "plan_mode", "registered") in EVALUATION_FORBIDDEN_MODES:
        raise core.StageRefused(f"refused: a {world.plan_mode} never scores E_A, E_B, E_C or E_open (section 4.1: not before the registered run of Part T); it scores D_cal only")


ITEMS: dict[str, dict[str, Any]] = {}  # registry key (without the read's own scalar) -> per-item records of the read, written by the scoring functions (audit R5, ruling 8)
_AT: list[str] = []


@contextlib.contextmanager
def at(prefix: str) -> Iterator[None]:
    """The registry-key prefix (``arm|order|rep``) the scoring calls inside this block belong to: a per-item record is stored under ``prefix|read``."""
    _AT.append(prefix)
    try:
        yield
    finally:
        _AT.pop()


def log_items(prefix: str, read: str, items: Sequence[float], *, exact: Sequence[bool] | None = None, sequences: Sequence[Sequence[int]] | None = None, texts: Sequence[str] | None = None) -> None:
    """Store one read's per-item scores (and, where the scoring made them, its exact-match flags, greedy token sequences and answer texts) under the registry key of the read."""
    rec: dict[str, Any] = {"items": [float(x) for x in items]}
    if exact is not None:
        rec["exact"] = [bool(x) for x in exact]
    if sequences is not None:
        rec["sequences"] = [[int(t) for t in s] for s in sequences]
    if texts is not None:
        rec["texts"] = [str(t) for t in texts]
    ITEMS[f"{prefix}|{read}"] = rec


def log_panel(read: str, sc: Any) -> None:
    if _AT:
        log_items(_AT[-1], read, sc.items, exact=sc.exact, sequences=sc.sequences)


def log_json(read: str, js: Mapping[str, Any]) -> None:
    if _AT:
        log_items(_AT[-1], read, js["items"], exact=js["exact"], sequences=js["sequences"])


def take_items() -> dict[str, dict[str, Any]]:
    out = dict(ITEMS)
    ITEMS.clear()
    return out


KIND_SECONDS: dict[str, float] = {}
KIND_CALLS: dict[str, int] = {}


@contextlib.contextmanager
def timed(kind: str) -> Iterator[None]:
    """Seconds spent per kind of work in this process (the measuring rehearsal's per-kind rates; nothing else reads them)."""
    t0 = time.perf_counter()
    try:
        yield
    finally:
        KIND_SECONDS[kind] = KIND_SECONDS.get(kind, 0.0) + (time.perf_counter() - t0)
        KIND_CALLS[kind] = KIND_CALLS.get(kind, 0) + 1


def _cap(order: str, which: int) -> str:
    return order[which]


@torch.no_grad()
def panel_means(world: WorldT, arm: Arm, log: bool = True) -> dict[str, float]:
    """s:E_A and s:E_B: the mean chrF-norm of the arm on each full panel under the oracle route."""
    require_evaluation_allowed(world)
    ctx = world.ctx
    out: dict[str, float] = {}
    for n in ("E_A", "E_B"):
        with timed("score:plain"):
            sc = score_panel(ctx, arm, ctx.panels[n])
        if log:
            log_panel(f"s:{n}", sc)
        out[f"s:{n}"], out[f"em:{n}"] = sc.mean, mean([float(x) for x in sc.exact])  # em: exact-match rate (EXACT-MATCH WEAK)
    return out


@torch.no_grad()
def control_reads(world: WorldT, rep: int, arm: MemoryArm, name: str, order: str) -> dict[str, float]:
    """sub:{own,value,code,marker,words}:E_x on the 300-item subsample of the capabilities the arm's controls act on (section 5.2): M1 the first; the stage-2 arms the second; M-joint both on their own panels."""
    ctx = world.ctx
    ctx.seed_plan = world.plan(rep)  # type: ignore[assignment]
    caps = list(TWO) if name == "M-joint" else [_cap(order, 0 if name == "M1" else 1)]
    with timed("score:control"):
        res = memory_ablations(ctx, arm, [PANEL[c] for c in caps], CONTROL_STAGES[name], caps)
    out: dict[str, float] = {}
    for c in caps:
        for kind, cond in COND.items():
            out[f"sub:{cond}:{PANEL[c]}"] = float(res[PANEL[c]][kind]["mean"])
            log_json(f"sub:{cond}:{PANEL[c]}", res[PANEL[c]][kind])
    return out


@torch.no_grad()
def reference_reads(world: WorldT) -> dict[str, float]:
    """S0 (the frozen student, no arm) and the teachers' stored outputs on the full panels and the subsample: the floor and the ceiling of every gap."""
    ctx = world.ctx
    out: dict[str, float] = {}
    for c in TWO:
        n = PANEL[c]
        panel = ctx.panels[n]
        sub = ctx.subsample[n]
        s0_full = score_panel(ctx, NullArm(), panel)
        log_items("S0|-|-", f"s:{n}", s0_full.items, exact=s0_full.exact, sequences=s0_full.sequences)
        log_items("S0|-|-", f"sub:own:{n}", [s0_full.items[i] for i in sub])
        out[f"S0|s:{n}"] = s0_full.mean
        out[f"S0|sub:own:{n}"] = mean([s0_full.items[i] for i in sub])
        texts = world.teacher_outputs[c][n]
        items = [chrf_item(t, r) for t, r in zip(texts, panel.refs, strict=True)]
        t_exact = [normalize(t) in {normalize(x) for x in r} for t, r in zip(texts, panel.refs, strict=True)]
        log_items("TEACHER|-|-", f"s:{n}", items, exact=t_exact, texts=texts)
        log_items("TEACHER|-|-", f"sub:own:{n}", [items[i] for i in sub])
        out[f"TEACHER|s:{n}"] = mean(items)
        out[f"TEACHER|em:{n}"] = mean([float(normalize(t) in {normalize(x) for x in r}) for t, r in zip(texts, panel.refs, strict=True)])
        out[f"S0|em:{n}"] = mean([float(x) for x in s0_full.exact])
        out[f"TEACHER|sub:own:{n}"] = mean([items[i] for i in sub])
        op = ctx.panels.get(f"E_open_{c}")
        if op is not None:  # the descriptive E_open reference reads: S0 and the teacher's stored answers on the panel's items (their positions in the stored panel)
            s0o = score_panel(ctx, NullArm(), op)
            log_items("S0|-|-", f"open:{c}", s0o.items, exact=s0o.exact, sequences=s0o.sequences)
            out[f"S0|open:{c}"] = s0o.mean
            t_texts = [world.teacher_outputs[c]["E_open"][j] for j in (op.source_index or range(len(op.refs)))]
            t_items = [chrf_item(t, r) for t, r in zip(t_texts, op.refs, strict=True)]
            log_items("TEACHER|-|-", f"open:{c}", t_items, texts=t_texts)
            out[f"TEACHER|open:{c}"] = mean(t_items)
    return out


def build_routers_t(world: WorldT, rep: int) -> dict[tuple[str, ...], tuple[Router, dict[str, Any]]]:
    """One router per (replicate, set of tasks): {A}, {B}, {A, B}, from the +13 stream (initialization: role 7), as P10-S2's ``build_routers`` with this study's seeds."""
    out: dict[tuple[str, ...], tuple[Router, dict[str, Any]]] = {}
    for tasks in (("A",), ("B",), TWO):
        prompts = {t: [world.bank.prompt(t, x.en) for x in world.streams[rep].t[t]] for t in tasks}
        with torch.enable_grad(), timed("router:train"):  # the router trains: scoring's no_grad does not apply to it
            out[tasks] = train_router(world.student, world.layer, tasks, prompts, world.wiki_train_ids, world.plan(rep), world.router_spec)  # type: ignore[arg-type]
    return out


def save_routers(routers: Mapping[tuple[str, ...], tuple[Router, dict[str, Any]]], directory: Path) -> dict[str, Any]:
    """Snapshot every router of a replicate with its hashes (audit R5, ruling 11): one file and one manifest per task set; written once, never overwritten."""
    import json

    from arborlm.io import atomic_write, file_sha256

    directory.mkdir(parents=True, exist_ok=True)
    out: dict[str, Any] = {}
    for tasks, (router, diag) in routers.items():
        name = "_".join(tasks)
        data, manifest = directory / f"{name}.pt", directory / f"{name}.manifest.json"
        if data.exists():
            raise FileExistsError(f"router snapshot {name!r} exists and is immutable")
        torch.save({"tasks": list(tasks), "width": int(router.proj.shape[1]), "state": {k: v.detach().clone() for k, v in router.state_dict().items()}}, data)
        m = {"tasks": list(tasks), "file": data.name, "file_sha256": file_sha256(data), "state_hash": router.state_hash(), "diagnostics": diag}
        atomic_write(manifest, (json.dumps(core.jsonable(m), sort_keys=True) + "\n").encode())
        out[name] = m
    return out


def load_routers(directory: Path) -> dict[tuple[str, ...], tuple[Router, dict[str, Any]]]:
    """The routers of a replicate from their snapshots, each file re-hashed against its manifest and each state against its recorded state hash (the recomputation uses THESE routers, never new ones)."""
    import json

    from arborlm.io import file_sha256

    out: dict[tuple[str, ...], tuple[Router, dict[str, Any]]] = {}
    manifests = sorted(directory.glob("*.manifest.json")) if directory.is_dir() else []
    if not manifests:
        raise core.StageRefused(f"refused: no router snapshot under {directory}: the recomputation re-reads the routers the evaluation used")
    for mf in manifests:
        m = json.loads(mf.read_text())
        data = directory / m["file"]
        if file_sha256(data) != m["file_sha256"]:
            raise core.StageRefused(f"refused: {data} does not hash to its router manifest (PAUSED — IDENTITY)")
        st = torch.load(data, weights_only=True)
        router = Router(st["tasks"], int(st["width"]), torch.Generator())  # the initial values are replaced by the stored state
        router.load_state_dict(st["state"])
        if router.state_hash() != m["state_hash"]:
            raise core.StageRefused(f"refused: the router in {data} does not match its recorded state hash")
        out[tuple(m["tasks"])] = (router, m["diagnostics"])
    return out


def _gen_panel(values: Sequence[float], strata: Sequence[str]) -> float:
    from .partt_items import panel_mean

    return panel_mean(values, strata)


@torch.no_grad()
def gen_windows(ctx: Any, arm: Arm, router: Router | None) -> dict[str, Any]:
    """The per-window quantities ``general_quality`` reduces (it returns only the panel figures): for every GEN window the unmodified student's mean NLL, the arm's under the router's decision at token 64 and at
    the first marker-like string, the stratum and both decisions. The same forward passes as ``general_quality``; the caller checks that they reproduce its figures."""
    import torch.nn.functional as F

    from studies.p10s2.evaluate import _window_logits
    from studies.p10s2.routing import hidden_at_ends

    null = NullArm()
    preds: list[str] = []
    preds_m: list[str] = []
    if router is not None and ctx.windows:
        preds = router.predict(hidden_at_ends(ctx.student, ctx.router_layer, [w.ids for w in ctx.windows], [ctx.decision_index] * len(ctx.windows)))
        second = [w.marker_end if w.stratum == "marker" and w.marker_end >= 0 else ctx.decision_index for w in ctx.windows]
        preds_m = router.predict(hidden_at_ends(ctx.student, ctx.router_layer, [w.ids for w in ctx.windows], second))
    nll_base: list[float] = []
    nll_a: list[float] = []
    nll_m: list[float] = []
    for k, w in enumerate(ctx.windows):
        tgt = torch.tensor(list(w.ids[ctx.first_nll_index :]))
        pred = preds[k] if router is not None else "none"
        pred_m = preds_m[k] if router is not None else "none"
        tasks = [] if pred == "none" else [pred]
        tasks_m = [] if pred_m == "none" else [pred_m]
        base = _window_logits(ctx, null, w, [])[ctx.first_nll_index - 1 : -1]
        nll_base.append(float(-F.log_softmax(base, dim=-1).gather(1, tgt[:, None]).mean()))
        a = _window_logits(ctx, arm, w, tasks)[ctx.first_nll_index - 1 : -1]
        nll_a.append(float(-F.log_softmax(a, dim=-1).gather(1, tgt[:, None]).mean()))
        if tasks_m == tasks:
            nll_m.append(nll_a[-1])
        else:
            m = _window_logits(ctx, arm, w, tasks_m)[ctx.first_nll_index - 1 : -1]
            nll_m.append(float(-F.log_softmax(m, dim=-1).gather(1, tgt[:, None]).mean()))
    return {"nll_base": nll_base, "nll_a": nll_a, "nll_m": nll_m, "strata": [w.stratum for w in ctx.windows], "preds": preds or ["none"] * len(ctx.windows), "preds_m": preds_m or ["none"] * len(ctx.windows)}


@torch.no_grad()
def gen_reads(world: WorldT, rep: int, arm: Arm, name: str, order: str, routers: Mapping[tuple[str, ...], tuple[Router, dict[str, Any]]]) -> tuple[dict[str, float], dict[str, Any]]:
    """gen:token64 and gen:first_marker: the loss increase over the unmodified student under the learned router, at the two decision positions (``general_quality``). M1 is read with the router of its first
    task; a stage-2 snapshot with the router of both tasks."""
    tasks = (_cap(order, 0),) if name == "M1" else TWO
    router = routers[tasks][0]
    with timed("score:gen"):
        res = general_quality(world.ctx, arm, router)
        ww = gen_windows(world.ctx, arm, router)
    for read, field, preds in (("gen:token64", "nll_a", "preds"), ("gen:first_marker", "nll_m", "preds_m")):
        rec = {"nll_base": ww["nll_base"], "nll_arm": ww[field], "strata": ww["strata"], "preds": ww[preds]}
        value = _gen_panel(rec["nll_arm"], rec["strata"]) - _gen_panel(rec["nll_base"], rec["strata"])
        reported = float(res["loss_increase" if read == "gen:token64" else "loss_increase_first_marker"])
        if abs(value - reported) > 1e-9:  # the stored per-window losses must reproduce what general_quality reported
            raise core.StageRefused(f"refused: the per-window GEN losses give {value} and general_quality {reported} for {read}: an engineering stop")
        if _AT:
            ITEMS[f"{_AT[-1]}|{read}"] = {"gen": rec}
    return {"gen:token64": float(res["loss_increase"]), "gen:first_marker": float(res["loss_increase_first_marker"])}, {k: res[k] for k in ("false_trigger_count", "false_trigger_count_first_marker", "stratum_sizes", "stratum_means", "passes")}


@torch.no_grad()
def dcon_reads(world: WorldT, arm: Arm) -> dict[str, float]:
    out: dict[str, float] = {}
    with timed("score:dcon"):
        for c in TWO:
            sc = score_panel(world.ctx, arm, world.d_con[c])
            log_panel(f"dcon:{c}", sc)
            out[f"dcon:{c}"] = sc.mean
    return out


@torch.no_grad()
def seen_reads(world: WorldT, rep: int, arm: Arm) -> dict[str, float]:
    """The seen-item scores (ADR-0022 section on seen items, ADR-0025 sections 5.3 and 8.5): the arm's chrF-norm on the replicate's 300 seen training items of each capability (Part Q's seen order, not the first 300 of the
    draw), oracle route. Reported, entering no label."""
    out: dict[str, float] = {}
    for c in TWO:
        seen = list(world.seen_items[rep][c])
        if not seen:
            continue
        panel = PanelData(f"seen_{c}", c, [world.bank.prompt(c, x.en) for x in seen], [[x.target] for x in seen])
        sc = score_panel(world.ctx, arm, panel)
        log_panel(f"seen:{c}", sc)
        out[f"seen:{c}"] = sc.mean
    return out


@torch.no_grad()
def open_reads(world: WorldT, arm: Arm) -> dict[str, float]:
    """The E_open scores (sections 4.1 and 8.5): the arm on the descriptive panel of each capability (``E_open_<c>``: evaluation sentences with an out-of-vocabulary word), oracle route only. Reported, entering no label."""
    out: dict[str, float] = {}
    for c in TWO:
        panel = world.ctx.panels.get(f"E_open_{c}")
        if panel is None:
            continue
        sc = score_panel(world.ctx, arm, panel)
        log_panel(f"open:{c}", sc)
        out[f"open:{c}"] = sc.mean
    return out


def log_edit1_flags(world: WorldT, rep: int) -> None:
    """For E_A and E_B: each item's flag, a training source of this replicate's draw at word-level edit distance 1 (section 5.3), stored as a per-item record next to the scores it is applied to."""
    from .partt_items import edit1_flags

    train_keys = [x.key for c in TWO for x in world.streams[rep].t[c]]
    for c in TWO:
        n = PANEL[c]
        flags = edit1_flags([i.key for i in world.partition.panels[n]], train_keys)
        ITEMS[f"edit1|-|{rep}|edit1:{n}"] = {"flags": flags}


def modification(m_ii: MemoryArm, m1: MemoryArm) -> dict[str, float]:
    """‖V1(after) − V1(before)‖_F / ‖V1(before)‖_F over the first-stage value rows (ADR-0022 section 6.3) and the share of first-stage rows that changed at all."""
    before, after = m1.store.values[0].detach(), m_ii.store.values[0].detach()
    rel = float((after - before).norm() / before.norm().clamp_min(1e-30))
    changed = float(((after - before).abs().sum(dim=1) > 0).float().mean())
    return {"modification": rel, "modification_rows_changed_share": changed}


def put(reg: Registry, arm: str, order: str, rep: int | str, reads: Mapping[str, float]) -> None:
    for k, v in reads.items():
        reg.put(arm, order, rep, k, v)


def cell_reads(world: WorldT, rep: int, name: str, order: str, arm: Arm, routers: Mapping[tuple[str, ...], tuple[Router, dict[str, Any]]] | None, *, m1: Arm | None = None, m_append: Arm | None = None) -> tuple[dict[str, float], dict[str, Any]]:
    """Every registry read of one trained cell, and the side records (router diagnostics). Reads exist exactly where section 5.2 and ``partt_plan.required_keys`` say."""
    reads = panel_means(world, arm)
    extra: dict[str, Any] = {}
    if name in CONTROL_STAGES and isinstance(arm, MemoryArm):
        reads |= control_reads(world, rep, arm, name, order)
    if name in GEN_ARMS and routers is not None:
        g, diag = gen_reads(world, rep, arm, name, order, routers)
        reads |= g
        extra["router_diagnostics"] = diag
    if name in ("M-append", "M-ii"):
        reads |= dcon_reads(world, arm)
    if name in ("M1", "M-append"):  # the arms the ADR names for the seen-item scores; E_open is read on the same
        reads |= seen_reads(world, rep, arm)
        reads |= open_reads(world, arm)
    if name == "M-ii" and isinstance(arm, MemoryArm) and isinstance(m1, MemoryArm):
        mod = modification(arm, m1)
        reads["modification"] = mod["modification"]
        extra["modification_rows_changed_share"] = mod["modification_rows_changed_share"]
    return reads, extra


# --- lookup baselines ---------------------------------------------------------------------------------------------------------------------------
def gloss_icl_ids(source: str, query: Any, lexicon: Mapping[str, str], vocab: set[str], bank: Mapping[str, Any], cap: str, bos_len: int) -> list[int]:
    """R-gloss-icl (section 5.2): before the task prompt S0 receives, unchanged, one line per in-vocabulary source word with a lexicon entry, in source order, repeats included: the source word's stored
    segment, the separator segment, the gloss word's stored segment, the newline segment; no tokenizer is called. A BOS token, if the prompt starts with one, stays once at the start (reading, as ``icl_ids``)."""
    pairs = [(w, lexicon[w]) for w in normalize(source).split() if w in vocab and w in lexicon]
    ids = list(query.prompt_ids)
    if not pairs:
        return ids
    lines: list[int] = []
    for i, (w, g) in enumerate(pairs):  # the amended segment rule (addendum section 3): a later line's source-word segment carries the newline before it
        lines += [*(bank["source_words"][w] if i == 0 else bank["source_words_after_newline"][w]), *bank["separator"], *bank["words"][cap][g]]
    ln = bank["last_newline"]
    if ln["rule"] == "own-segment":
        return ids[:bos_len] + lines + list(bank["newline"]) + ids[bos_len:]
    drop = len(ln["first_task_piece_ids"])  # the last newline is stored together with the task prompt's first piece
    if ids[bos_len : bos_len + drop] != ln["first_task_piece_ids"]:
        raise ValueError("the task prompt does not begin with the piece the bank's last-newline rule names")
    return ids[:bos_len] + lines + list(ln["fused_ids"]) + ids[bos_len + drop :]


@torch.no_grad()
def baseline_reads(world: WorldT, rep: int, gloss_bank: Mapping[str, Any]) -> dict[str, float]:
    """The lookup baselines of a replicate on E_A and E_B from its training draw: R-gloss, R-gloss-icl, R-nn and R-icl (E-table is a trained arm), plus R-exact's hit count (gate G1)."""
    from studies.p10s2.cells import icl_ids

    ctx, out = world.ctx, {}
    vocab = set(world.partition.vocab)
    for c in TWO:
        train = world.streams[rep].t[c]
        items = world.partition.panels[PANEL[c]]
        n = PANEL[c]
        idx = retrieval.TfidfIndex(train)
        r_ex, r_nn, r_gl = retrieval.r_exact(train, items, c), retrieval.r_nn(train, items, c, idx), retrieval.r_gloss(train, items, c)
        for arm_name, rr in (("R-exact", r_ex), ("R-nn", r_nn), ("R-gloss", r_gl)):
            log_items(f"{arm_name}|-|{rep}", f"s:{n}", rr["items"])
        out[f"R-exact|s:{n}"] = r_ex["mean"]
        out[f"R-exact|hits:{n}"] = float(r_ex["hits"])
        out[f"R-nn|s:{n}"] = r_nn["mean"]
        out[f"R-gloss|s:{n}"] = r_gl["mean"]
        lex = retrieval.gloss_lexicon(train)
        icl, gicl, icl_seq, gicl_seq = [], [], [], []
        for it, ex, refs in zip(items, ctx.panels[n].examples, ctx.panels[n].refs, strict=True):
            demos = retrieval.r_icl_prompt_items(train, it.en, 4, idx)
            seq = ctx.student.greedy(torch.tensor([icl_ids([world.bank.train(c, d) for d in demos], ex)]), add=None, adapter=None, max_new=ctx.max_new, stop_bytes=ctx.decoder.table)
            icl.append(chrf_item(ctx.decoder.answer_text(seq), refs))
            icl_seq.append(seq)
            bos = len(ex.segments[0].ids) if ex.segments and ex.segments[0].text == "<bos>" else 0
            seq2 = ctx.student.greedy(torch.tensor([gloss_icl_ids(it.en, ex, lex, vocab, gloss_bank, c, bos)]), add=None, adapter=None, max_new=ctx.max_new, stop_bytes=ctx.decoder.table)
            gicl.append(chrf_item(ctx.decoder.answer_text(seq2), refs))
            gicl_seq.append(seq2)
        log_items(f"R-icl|-|{rep}", f"s:{n}", icl, sequences=icl_seq)
        log_items(f"R-gloss-icl|-|{rep}", f"s:{n}", gicl, sequences=gicl_seq)
        out[f"R-icl|s:{n}"], out[f"R-gloss-icl|s:{n}"] = mean(icl), mean(gicl)
    return out


# --- the registry ---------------------------------------------------------------------------------------------------------------------------
def registry_from_reads(records: Mapping[str, Mapping[str, float]]) -> Registry:
    """The registry from scored reads. ``records`` maps ``"{arm}|{order}|{rep}"`` to its reads; reference reads are keyed ``"S0|-|-"`` and ``"TEACHER|-|-"``. Two records can never share a key."""
    reg = Registry()
    for k, reads in records.items():
        arm, order, rep = k.split("|")
        put(reg, arm, order, rep if rep == NONE else int(rep), reads)
    return reg


def reference_records(world: WorldT) -> dict[str, dict[str, float]]:
    with timed("score:reference"):
        ref = reference_reads(world)
    out: dict[str, dict[str, float]] = {"S0|-|-": {}, "TEACHER|-|-": {}}
    for k, v in ref.items():
        who, read = k.split("|", 1)
        out[f"{who}|-|-"][read] = v
    return out


def key_of(arm: str, order: str, rep: int | str, read: str) -> str:
    return key(arm, order, rep, read)


def panels_of(world: WorldT) -> dict[str, PanelData]:
    return world.ctx.panels


def is_append(arm: Arm) -> bool:
    return isinstance(arm, AppendLoRAArm)


@torch.no_grad()
def route_reads(world: WorldT, rep: int, arm: Arm, routers: Mapping[tuple[str, ...], tuple[Router, dict[str, Any]]]) -> tuple[dict[str, float], dict[str, Any]]:
    """The learned-route scores of a stage-2 snapshot on E_A and E_B (``lr:E_x``) and the router's route accuracy on the task panels and on 200 general pieces of the WikiText-2 train file the router never saw
    (pieces drawn with seed 250918 in a registered run)."""
    from studies.p10s2.routing import none_pieces, route_accuracy

    router = routers[TWO][0]
    ctx = world.ctx
    reads: dict[str, float] = {}
    with timed("score:route"):
        for n in ("E_A", "E_B"):
            sc = score_panel(ctx, arm, ctx.panels[n], route="learned", router=router)
            log_panel(f"lr:{n}", sc)
            reads[f"lr:{n}"] = sc.mean
    plan = world.plan(rep)
    pieces = none_pieces(world.wiki_train_ids, world.router_spec.prefix_tokens)
    picked = set(torch.randperm(len(pieces), generator=plan.gen(3, "router sampling")).tolist()[: world.router_spec.none_prefixes])
    order = [i for i in torch.randperm(len(pieces), generator=plan.route_pieces_gen()).tolist() if i not in picked][: world.router_spec.general_prefix_count]
    acc = route_accuracy(router, world.student, world.layer, {c: [world.bank.prompt(c, x.en) for x in world.partition.panels[PANEL[c]]] for c in TWO}, [pieces[i] for i in order])
    return reads, {"route_accuracy": acc, "general_pieces": len(order)}
