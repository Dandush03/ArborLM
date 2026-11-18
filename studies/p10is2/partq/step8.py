# ruff: noqa: E501
"""Step 8 of Part Q (ADR-0025 section 4.1): teacher outputs on the six panels, the GEN window entries of the shared panel ledger, the gloss bank and tokenization test (a). Over injected interfaces like ``pipeline``."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from studies.p10s2.data import Item

from ..common import core
from ..common.panel_ledger import (
    LEDGER_FORMAT,
    PanelLedger,
    RowMap,
    Span,
    read_shared,
    write_ledger,
)
from . import batches as bt
from . import gloss, partition
from .pipeline import QContext, _rec, accepted_pool, fail

__all__ = ["LEDGER_FORMAT"]
PANEL_OUTPUT_PANELS = ("E_A", "E_B", "E_C", "E_open", "D_cal", "D_con")


def step_outputs(ctx: QContext, p: partition.QPartition) -> dict[str, Any]:
    """Teacher outputs on E_A, E_B, E_C, E_open, D_cal and D_con in the frozen layout, stored and hashed and NOT scored. READING (listed): every teacher runs on every one of the six panels, so the ensemble
    ceiling of each capability, the combined tasks and the descriptive scores all find their outputs; the ADR does not say which teacher runs on which panel."""
    out: dict[str, Any] = {}
    for c in core.TASKS:
        for name in PANEL_OUTPUT_PANELS:
            items = p.panels[name]
            b = bt.run_stream(ctx.teachers[c], ctx.d(f"outputs/teacher_{c}/{name}"), [i.key for i in items], [i.en for i in items], size=ctx.size, deadline=ctx.deadline)
            out[f"{c}/{name}"] = {"batches": len(b), "sources": len(items), "sha256": bt.digest_of(b)}
    return _rec(ctx, "outputs/record.json", "outputs", {"outputs": out, "scored": False})


def write_study_ledger(cfg: Mapping[str, Any], mode: str, ledger_path: Path, marker_windows: Sequence[Span], ordinary_candidates: Sequence[Span], owner: str = "P10IS2-partq", row_map: RowMap | None = None, sizes: Mapping[str, int] | None = None) -> dict[str, Any]:
    """The ONE pre-freeze ledger step: records the 44 marker-like windows and 100 ordinary windows sampled with seed 250907 (252907 in a rehearsal) from the candidates that overlap no span already in the shared ledger.
    ``marker_windows`` and ``ordinary_candidates`` are byte spans from the tokenized WikiText-2 validation text. Refuses if this study's windows are already in the ledger (written once)."""
    seeds = core.partq_seeds(cfg, mode)
    allowed = frozenset(seeds.values()) | (core.test_range(cfg) if mode == "test" else frozenset())
    shared = read_shared(ledger_path)
    if any(w.get("owner") == owner for w in shared.get("windows", [])):
        raise core.StageRefused(f"refused: {ledger_path} already holds this study's windows; the ledger is written once, before the freeze")
    led = PanelLedger(Span.from_json(r) for r in shared.get("windows", []))
    pn = dict(cfg["panels"])
    if sizes:
        pn.update(sizes)
    if len(marker_windows) != int(pn["gen_marker_like"]):
        raise core.PendingLeadReview(f"{len(marker_windows)} marker-like windows on the fixed grid, the rule needs exactly {pn['gen_marker_like']}")
    for m in marker_windows:
        led.add(replace(m, kind="marker", owner=owner))
    g = core.seeded_generator(seeds["gen_ordinary_windows"], "GEN ordinary windows", allowed)
    eligible = len(led.eligible_ordinary(ordinary_candidates))
    for s in led.sample_ordinary(ordinary_candidates, int(pn["gen_ordinary"]), g):
        led.add(replace(s, kind="ordinary", owner=owner))
    check = led.check_own_panel(owner, int(pn["gen_marker_like"]), int(pn["gen_ordinary"]))
    if not check["ok"]:
        raise core.StageRefused(f"refused: the panel ledger's own check failed: {check}")
    write_ledger(ledger_path, led, owner, check, eligible, row_map)
    return {"eligible_ordinary": eligible, **check}


def verify_study_ledger(cfg: Mapping[str, Any], ledger_path: Path, marker_windows: Sequence[Span], ordinary_candidates: Sequence[Span], owner: str = "P10IS2-partq", sizes: Mapping[str, int] | None = None) -> dict[str, Any]:
    """What the registered ``inputs`` stage does with the ledger: it VERIFIES and never writes. The ledger must hold this study's 44 marker-like windows equal to the grid's, and 100 ordinary windows that are
    candidates of the grid, overlap no other owner's span and no other window of this study. (The sample itself was drawn once, before the freeze, with seed 250907.)"""
    pn = dict(cfg["panels"])
    if sizes:
        pn.update(sizes)
    shared = read_shared(ledger_path)
    mine = [Span.from_json(w) for w in shared.get("windows", []) if w.get("owner") == owner]
    problems: list[str] = []
    want_m = sorted((m.start, m.end) for m in marker_windows)
    have_m = sorted((s.start, s.end) for s in mine if s.kind == "marker")
    if have_m != want_m:
        problems.append(f"the ledger's marker-like windows ({len(have_m)}) are not the grid's {len(want_m)}")
    cand = {(c.start, c.end) for c in ordinary_candidates}
    ordn = [s for s in mine if s.kind == "ordinary"]
    if len(ordn) != int(pn["gen_ordinary"]):
        problems.append(f"the ledger holds {len(ordn)} ordinary windows of this study, needs {pn['gen_ordinary']}")
    problems += [f"ordinary window {s.start}-{s.end} is not a candidate of the grid" for s in ordn if (s.start, s.end) not in cand]
    led = PanelLedger(Span.from_json(w) for w in shared.get("windows", []))
    chk = led.check_own_panel(owner, int(pn["gen_marker_like"]), int(pn["gen_ordinary"]))
    if not chk["ok"]:
        problems.append(f"the ledger's own check fails: {chk}")
    if problems:
        raise core.StageRefused("refused: the shared panel ledger does not verify: " + "; ".join(problems))
    return {"verified": True, "marker_like": len(have_m), "ordinary": len(ordn), "check": chk}


def step_ledger(ctx: QContext, ledger_path: Path, marker_windows: Sequence[Span], ordinary_candidates: Sequence[Span], owner: str = "P10IS2-partq", row_map: RowMap | None = None) -> dict[str, Any]:
    """Test and rehearsal wrapper of ``write_study_ledger`` with a context (its mode, its panel-size overrides)."""
    return write_study_ledger(ctx.cfg, ctx.mode, ledger_path, marker_windows, ordinary_candidates, owner, row_map, ctx.sizes)


def step_gloss(ctx: QContext, tok: Any, items_for_test: Mapping[str, Sequence[Item]], in_vocab: set[str]) -> dict[str, Any]:
    """The gloss bank (token ids of every target-language word type of each accepted pool, the separator and newline segments) and tokenization test (a) on the R-gloss-icl prompts of every E_A, E_B and
    D_cal item with a lexicon built from the whole accepted pool. Zero mismatches are required; a mismatch is a failed gate on study-produced data."""
    pools = {c: accepted_pool(ctx, c) for c in core.TASKS}
    bank = gloss.gloss_bank(tok, pools)
    tests: dict[str, Any] = {}
    for name, cap in (("E_A", "A"), ("E_B", "B"), ("D_cal", "A"), ("D_cal", "B")):
        lex = gloss.gloss_lexicon(pools[cap])
        tests[f"{name}/{cap}"] = gloss.tokenization_test_a(tok, items_for_test[name], lex, in_vocab, cap, bank)
    bad = sum(t["mismatches"] for t in tests.values())
    if bad:
        fail(ctx, f"tokenization test (a) on R-gloss-icl prompts: {bad} mismatches (zero required)")
    _rec(ctx, "outputs/gloss_bank.json", "gloss_bank", {"bank": bank})
    return _rec(ctx, "outputs/gloss_test.json", "gloss_test", {"tests": tests, "mismatches": bad})
