# ruff: noqa: E501
"""Step 8 of Part Q (ADR-0025 section 4.1): teacher outputs on the six panels, the GEN window entries of the shared panel ledger, the gloss bank and tokenization test (a). Over injected interfaces like ``pipeline``."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from arborlm.io import read_json
from studies.p10s2.data import Item

from ..common import core
from ..common.panel_ledger import LEDGER_FORMAT, PanelLedger, RowMap, Span, write_ledger
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


def step_ledger(ctx: QContext, ledger_path: Path, marker_windows: Sequence[Span], ordinary_candidates: Sequence[Span], owner: str = "P10IS2-partq", row_map: RowMap | None = None) -> dict[str, Any]:
    """Records the 44 marker-like windows and 100 sampled ordinary windows in the shared panel ledger (byte spans, end exclusive). ``marker_windows`` and ``ordinary_candidates`` are the spans the caller built
    from the tokenized WikiText-2 validation text (the real path) or synthetic spans (tests). The ordinary sample (seed 250907) takes only candidates that overlap no span already in the ledger."""
    led = PanelLedger(Span.from_json(r) for r in (read_json(ledger_path)["windows"] if ledger_path.is_file() else []))
    pn = dict(ctx.cfg["panels"])
    if ctx.sizes:
        pn.update(ctx.sizes)
    if len(marker_windows) != int(pn["gen_marker_like"]):
        raise core.PendingLeadReview(f"{len(marker_windows)} marker-like windows on the fixed grid, the rule needs exactly {pn['gen_marker_like']}")
    for m in marker_windows:
        led.add(replace(m, kind="marker", owner=owner))
    g = core.seeded_generator(ctx.seeds["gen_ordinary_windows"], "GEN ordinary windows", ctx.allowed)
    eligible = len(led.eligible_ordinary(ordinary_candidates))
    for s in led.sample_ordinary(ordinary_candidates, int(pn["gen_ordinary"]), g):
        led.add(replace(s, kind="ordinary", owner=owner))
    check = led.check_own_panel(owner, int(pn["gen_marker_like"]), int(pn["gen_ordinary"]))
    if not check["ok"]:
        fail(ctx, f"the panel ledger check failed: {check}")
    write_ledger(ledger_path, led, owner, check, eligible, row_map)
    return {"eligible_ordinary": eligible, **check}


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
