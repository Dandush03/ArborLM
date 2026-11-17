# ruff: noqa: E501
"""P10S1 estimated storage traffic (ADR-0021 section 7.5): arithmetic and simulation only, no device. The estimate assumes keys in RAM and values on storage.

For a memory cell at its U_P snapshot (replicate 1): value bytes read per query; distinct pages touched per query at 8 and 32 rows per page under the identity layout; page misses
from ``studies/p9/sim.py`` at ONE setting with three count-preserving nulls, the ratio to the null (``e_ratio``) and the working set; a null miss rate below 0.05 is DEGENERATE.
Key bytes scored per query if keys were on storage is printed as an identity from section 7.4 (K x 16 x 4 bytes), not an estimate.

The ADR says 'at one setting' without naming it: the setting here is 8 rows per page, a cache of rho = 1/4 of the working set, tie rule ascending (READING / PENDING LEAD REVIEW,
printed with every record). No simulated traffic is ever called locality, and none is reported without the working set beside it.
"""

from typing import TYPE_CHECKING, Any

import torch

from studies.p9 import core as p9core
from studies.p9 import layout, sim
from studies.p9.data import StudyData

from . import core
from .evaluate import stream_for
from .model import P10S1Model

if TYPE_CHECKING:
    from torch import Tensor

SETTING_ROWS, SETTING_RHO, SETTING_TIE = 8, 0.25, "asc"
SETTING = {"rows_per_page": SETTING_ROWS, "cache_fraction": SETTING_RHO, "tie": SETTING_TIE}
PAGE_ROWS = (8, 32)
DISCLAIMER = "arithmetic and simulation, no device: not a storage measurement; value pages only, keys assumed in RAM; no reduction is called locality"


@torch.no_grad()
def answer_site_trace(model: P10S1Model, data: StudyData, facts: int, stream_name: str, label: str, update: int) -> p9core.Trace:
    """The answer-site reads of ``model`` on a stream restricted to ``facts``: one row per query (a trained fact's answer site), the 8 selected slots, in (context, position) order."""
    stream = stream_for(data, facts, stream_name)
    model.eval()
    selected: list[Tensor] = []
    context: list[Tensor] = []
    position: list[Tensor] = []
    fact: list[Tensor] = []
    for start in range(0, stream.tokens.shape[0], 64):
        tok = stream.tokens[start : start + 64, : core.INPUT_LENGTH].contiguous()
        ids = stream.fact_ids[start : start + 64]
        sel = model.select(model.embed_block0(tok), tok)
        keep = ids < facts
        rows, recs = keep.nonzero(as_tuple=True)
        selected.append(sel.selected[rows, recs].to(torch.int64))  # type: ignore[union-attr]
        context.append(start + rows)
        position.append(torch.tensor(core.ANSWER_SITE_POSITIONS)[recs])
        fact.append(ids[rows, recs])
    facts_t = torch.cat(fact)
    sel_t = torch.cat(selected)
    if sel_t.shape[1] != core.TOP:
        sel_t = sel_t[:, : core.TOP]
    return p9core.Trace(label, update, stream_name, "answer", model.slots, sel_t, None, torch.cat(context), torch.cat(position), facts_t, data.facts.cluster[facts_t])


def traffic_record(model: P10S1Model, data: StudyData, facts: int, label: str, update: int, seeds: p9core.SeedSet) -> dict[str, Any]:
    """The estimated traffic of one cell at its U_P snapshot: value bytes, pages per query at 8 and 32 rows per page (identity layout), page misses at the one setting with three
    count-preserving nulls, the working set and the DEGENERATE flag; key bytes as an identity from section 7.4."""
    if model.arm not in ("F-OQ", "T-OQ", "H8"):
        raise ValueError("traffic is estimated for the memory arms F-OQ, T-OQ and H8")
    trace = answer_site_trace(model, data, facts, "panel_a", label, update)
    calibration = answer_site_trace(model, data, facts, "calibration", label, update)
    identity = layout.identity_layout(model.slots)
    pages = {str(r): sim.pages_per_query(sim.page_sequence(trace, identity, r)) for r in PAGE_ROWS}
    rec = sim.simulate_setting(trace, calibration, identity, rows=SETTING_ROWS, rho=SETTING_RHO, tie=SETTING_TIE, null_seeds=seeds.null_seeds_a, label=label, update=update, stream="panel_a", index=0)
    work = core.work_formula(model.arm, model.slots)
    return {
        **core.envelope("simulation"), "label": label, "arm": model.arm, "facts": facts, "slots": model.slots, "update": update, "disclaimer": DISCLAIMER,
        "setting": dict(SETTING), "setting_note": "READING / PENDING LEAD REVIEW: the ADR says 'at one setting' without naming it", "value_bytes_per_query": 4 * core.HIDDEN_WIDTH * core.TOP,
        "pages_per_query_identity_layout": pages, "queries": int(trace.selected.shape[0]), "working_set_slots": int(rec["working_set"]), "actual_capacity_misses": int(rec["actual_misses"]),
        "null_capacity_misses": [int(x) for x in rec["null_misses"]], "e_ratio": rec["e_ratio"], "null_miss_rate": float(rec["null_miss_rate"]), "degenerate": bool(rec["degenerate"]),
        "key_bytes_scored_per_query_if_keys_on_storage": 4 * core.KEY_WIDTH * work["K"], "key_bytes_label": "identity from section 7.4 (K x 16 x 4), not an estimate",
    }  # fmt: skip
