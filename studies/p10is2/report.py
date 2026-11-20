# ruff: noqa: E501
"""The Part T report: a pure function of the derived lines and the run context (ADR-0025 sections 1, 5.4, 8.3-8.6; ruling L8).

Every label, line, table and summary carries directly above it the fixed oracle-assisted line, and every line prints "(3 replicates, U = ...)" and NOT CONVERGED AT U where section 7.1 says so; the shared share
of the training draws is printed beside every line that says "every cell" when the draws overlap. The renderer REFUSES to write a line without them (``ReportRefused``). Under an engineering status no line is
printed. Nothing here claims a success: ArborLM is unproven research and ``Astra review: NOT_PERFORMED``.
"""

from collections.abc import Mapping
from typing import Any

from .common import core

QUALIFIER = "the memory receives the task identity by rule in its address; the dense arm receives it only through the prompt"
LINES_WITH_EVERY_CELL = ("ACQUISITION", "RETENTION", "GENERAL-QUALITY", "AGAINST-DENSE", "AGAINST-LOOKUP", "MILESTONE")


class ReportRefused(ValueError):
    """The report would print a line without the fixed line, the replicate count and U (or NOT CONVERGED AT U)."""


def suffix(ctx: Mapping[str, Any], name: str) -> str:
    s = f" (3 replicates, U = {ctx['U']})"
    if not ctx.get("converged", True):
        s += " NOT CONVERGED AT U"
    if name.startswith(LINES_WITH_EVERY_CELL) and ctx.get("draws") == "OVERLAPPING DRAWS":
        share = ctx.get("shared_share") or {}
        s += " [OVERLAPPING DRAWS; shared share of training items between replicates: " + ", ".join(f"{c} {share.get(c, float('nan')):.3f}" for c in core.TASKS) + "]"
    return s


def line(name: str, text: str, ctx: Mapping[str, Any]) -> str:
    """One printed line: the fixed line directly above, then the text with the replicate count and U."""
    if "U" not in ctx or ctx["U"] is None:
        raise ReportRefused("refused: a line without U")
    return core.under_line(f"{name}: {text}{suffix(ctx, name)}")


def compact(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.3f}"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {compact(x)}" for k, x in v.items()) + "}"
    if isinstance(v, list | tuple):
        return "[" + ", ".join(compact(x) for x in v) + "]"
    return str(v)


def companion_blocks(derived: Mapping[str, Any], ctx: Mapping[str, Any]) -> list[str]:
    """What the ADR prints with each line (audit R14): the per-cell tables behind ACQUISITION and RETENTION (with the evaluable cells and those in the negative zone, the passing cells per order, CONTROLS UNDEFINED
    and the cells behind NOT EVALUABLE), AGAINST-DENSE's per-cell differences, GENERAL-QUALITY's per-cell loss increases, AGAINST-LOOKUP's per-cell values, every annotation (NO ADVANTAGE OVER SEPARATE ADAPTERS, the
    M-sep and D-sep reading, ROUTER with its false-trigger counts, COMPOSES, ...) and the cost lines. Each is its own block under the fixed line; nothing here enters a label."""
    out: list[str] = []
    for name in ("ACQUISITION", "RETENTION"):
        d = derived.get(name) or {}
        for k, v in (d.get("table") or {}).items():
            out.append(line(f"COMPANION {name} table, {k}", compact(v), ctx))
        for key in ("passing_cells_per_order", "why"):
            if d.get(key):
                out.append(line(f"COMPANION {name} {key.replace('_', ' ')}", compact(d[key]), ctx))
    for name in ("AGAINST-DENSE", "AGAINST-DENSE (M-seq vs D-seq)"):
        d = derived.get(name) or {}
        for key in ("delta_G", "delta_rho"):
            if key in d:
                out.append(line(f"COMPANION {name} per-cell {key}", compact(d[key]), ctx))
    g = derived.get("GENERAL-QUALITY") or {}
    if g.get("readings"):
        out.append(line("COMPANION GENERAL-QUALITY per-cell loss increases (token64 and first marker)", compact(g["readings"]), ctx))
    lk = derived.get("AGAINST-LOOKUP") or {}
    if lk.get("per_cell"):
        out.append(line("COMPANION AGAINST-LOOKUP per cell", compact(lk["per_cell"]), ctx))
    for aname, a in sorted((ctx.get("annotations") or {}).items()):
        out.append(line(f"ANNOTATION {aname}", f"holds {a.get('holds')}; {compact(a.get('detail'))}", ctx))
    for text in ctx.get("cost_lines") or []:
        out.append(line("COST", text, ctx))
    return out


def render(status: Mapping[str, Any], derived: Mapping[str, Any] | None, ctx: Mapping[str, Any]) -> str:
    """The report text. ``status`` is ``labels.study_status``; ``derived`` is ``labels.derive_all`` (None when the status does not derive)."""
    if not status["derive"] or derived is None:
        return core.under_line(f"{status['status']}: {status['why']}", "No line is derived.", core.FIXED_NOTE)
    blocks: list[str] = []
    m = derived["MILESTONE"]
    blocks.append(line("MILESTONE (sequential acquisition with retention)", m["label"] + m.get("line_tail", ""), ctx))
    d = derived["AGAINST-DENSE"]
    blocks.append(line("AGAINST-DENSE", d["value"] + f". Reading: at matched updates; {QUALIFIER}.", ctx))
    ds = derived["AGAINST-DENSE (M-seq vs D-seq)"]
    blocks.append(line("AGAINST-DENSE (M-seq against D-seq)", ds["value"], ctx))
    lk = derived["AGAINST-LOOKUP"]
    blocks.append(line("AGAINST-LOOKUP", f"{lk['label']} (best baseline by frequency: {lk['baseline']})", ctx))
    blocks.append(line("ACQUISITION", derived["ACQUISITION"]["label"], ctx))
    blocks.append(line("RETENTION", derived["RETENTION"]["label"], ctx))
    g = derived["GENERAL-QUALITY"]
    blocks.append(line("GENERAL-QUALITY", g["label"] + (f" ({g['note']})" if g.get("note") else ""), ctx))
    blocks.append(line("MODIFICATION (M-ii, descriptive)", derived["MODIFICATION"]["label"], ctx))
    blocks += companion_blocks(derived, ctx)
    blocks.append(line("DISCLOSED LIMITATION (ruling 19)", "gate G1 tests Q_check against the training streams by English key only: Part Q stored no Q_check identity groups, so a paraphrase that shares an identity group with a training item is not detected", ctx))
    blocks.append(core.under_line(core.FIXED_NOTE))
    text = "\n\n".join(blocks)
    return check(text)


def check(text: str) -> str:
    """Refuses a report in which any block lacks the fixed line directly above it, or a printed line lacks the replicate count and U."""
    for block in text.split("\n\n"):
        lines = block.split("\n")
        if lines[0] != core.ORACLE_LINE:
            raise ReportRefused(f"refused: a block does not start with the fixed oracle-assisted line: {lines[0][:60]!r}")
        for ln in lines[1:]:
            if ln != core.FIXED_NOTE and "(3 replicates, U = " not in ln:
                raise ReportRefused(f"refused: the line {ln[:60]!r} carries no replicate count and U")
    return text
