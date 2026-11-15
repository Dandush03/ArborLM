# ruff: noqa: E501
"""Synthetic eval/sim records for the P8 analysis tests (hand-controlled m, null, N_eff and NLL)."""

import math
from dataclasses import dataclass
from typing import Any

from arborlm import p7b_core as b
from arborlm import p8_core as core
from arborlm.p8_analysis import CellData

QUERIES = 32768
COUNTED = QUERIES - QUERIES // 2


@dataclass(frozen=True)
class Spec:
    """Multipliers against the baseline values of the synthetic study."""

    m: float = 1.0  # L-COAX m
    nf: float = 1.0  # null mean under L-FREQ
    neff: float = 1.0
    gain: float = 1.0
    m_desc: float = 1.0  # extra multiplier on m under the descending tie rule


BASE_M, BASE_NF, BASE_NEFF, BASE_GAIN = 2.0, 1.0, 400.0, 0.02
DISABLED = 2.32


def _counts(m: float) -> dict[str, Any]:
    warm = round(m * COUNTED)
    return {
        "misses_all": warm * 2,
        "first_touch_all": 0,
        "misses_warm": warm,
        "first_touch_warm": 0,
        "ctx_q": [0] * 7,
    }


def _group(m_asc: float, m_desc: float) -> dict[str, Any]:
    return {"stats": {}, "by_c": {"32": {"asc": _counts(m_asc), "desc": _counts(m_desc)},
                                  "8": {"asc": _counts(m_asc), "desc": _counts(m_desc)}}}  # fmt: skip


def make_cell(cell: core.Cell, specs: dict[str, Spec]) -> CellData:
    tree = cell.variant != "flat"
    eval_rec: dict[str, Any] = {"nll": {"step0": {"enabled": {}}, "step512": {}}, "traces": {}}
    panels: dict[str, Any] = {}
    for panel, shift in (("A", 0), ("B", 1)):
        spec = specs.get((cell.case, panel), specs.get((cell.case, "*"), Spec()))
        jitter_e = 1.0 + 0.02 * ((cell.index * 7 + shift * 3) % 6)  # independent of N_eff
        jitter_x = 0.5 + 0.2 * (((cell.index // 10) * 2 + cell.seed - 601 + shift) % 6)
        neff = BASE_NEFF * spec.neff * jitter_x
        eval_rec["traces"][panel] = {
            "utilization": {
                "n_eff": neff,
                "entropy_nats": math.log(neff),
                "distinct_slots": 300,
                "hot64_share": 0.5,
                "context_breadth_mean": 100.0,
                **(
                    {"branches": {"distinct_visited": 8, "n_eff": 6.0, "top_branch_share": 0.3}}
                    if tree
                    else {}
                ),
            }
        }
        nll = DISABLED - BASE_GAIN * spec.gain
        eval_rec["nll"]["step0"]["enabled"][panel] = 2.34
        for cond, value in (
            ("enabled", nll),
            ("disabled", DISABLED),
            ("values_permuted", nll + 0.01 * spec.gain),
        ):
            eval_rec["nll"]["step512"].setdefault(cond, {})[panel] = value
        m_coax = BASE_M * spec.m * jitter_e
        nf = BASE_NF * spec.nf
        streams: dict[str, Any] = {s: {} for s in b.STREAMS_ALL}
        layouts = {
            b.L_ID: 2.0,
            b.L_FREQ: 1.5,
            b.L_COAX: 1.0,
            **{n: 1.2 for n in b.L_PCOAX},
            **({b.L_BCOAX: 0.9} if tree else {}),
        }
        for rows in (2, 8):
            for name, f in layouts.items():
                m = m_coax * f
                streams["actual"][b.layout_key(name, rows)] = _group(m, m * spec.m_desc * 0.9)
            for s in b.STREAMS_NULL:
                streams[s][b.layout_key(b.L_FREQ, rows)] = _group(nf, nf * 0.9)
                streams[s][b.layout_key(b.L_COAX, rows)] = _group(nf * 0.9, nf * 0.8)
            for name in (b.L_FREQ, b.L_COAX):
                streams["order_shuffled"][b.layout_key(name, rows)] = _group(nf, nf)
        reuse = {s: {"value": 0.3} for s in ("actual", "order_shuffled", *b.STREAMS_NULL)}
        panels[panel] = {
            "queries": QUERIES,
            "streams": streams,
            "temporal_reuse": reuse,
            "branch_persistence": (
                {
                    "actual": {"top_fraction": 0.5, "pair_fraction": 0.6},
                    "order_shuffled": {"top_fraction": 0.1, "pair_fraction": 0.2},
                }  # fmt: skip
                if tree
                else None
            ),
        }
    return CellData(cell, eval_rec, {"panels": panels})


def make_cells(specs: dict[str, Spec]) -> dict[str, CellData]:
    return {c.label: make_cell(c, specs) for c in core.cells()}
