"""P8 report generator (analysis-only).

Reads the JSON/CSV records written by the P8 stages (analysis, evaluation, simulation, training) and
renders figures, a self-contained HTML report, a compact JSON and a figures index. It does not import
``arborlm`` and recomputes no registered quantity: every ratio, class and flag comes from
``analysis.json`` / ``scorecard.csv``; the per-cell points come from ``cells.csv`` / ``pairs.csv``.

Run (matplotlib 3.10.8 is the version present in the local uv cache; 3.10.6 needs a download)::

    uv run --locked --extra pilot --with matplotlib==3.10.8 python \
        results/p8-2026-11-14/report/make_report.py \
        --analysis-run DIR --eval-run DIR --sim-run DIR [--train-run DIR] \
        --out results/p8-2026-11-14/report [--summary-md FILE]

Honesty rules built in: records with ``dry_run`` true are stamped "SYNTHETIC DRY RUN - NOT A RESULT" on
every figure and in the HTML; the study denominator is always 60 cells; undefined values are drawn
hatched and labelled "undef", never as zero; no interpretation is generated (captions only say what
is plotted). Simulated misses are value-page misses of a model, not physical I/O. Astra review:
NOT_PERFORMED.
"""

import argparse
import base64
import csv
import hashlib
import html
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

NAN = float("nan")
CASES = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10"]
PANELS = ["A", "B"]
FLAT = {"C01", "C04", "C06", "C08"}
BASELINE = {"C04": "C01", "C05": "C03", "C06": "C01", "C07": "C03", "C08": "C01", "C09": "C03", "C10": "C03"}
REGULARIZED = list(BASELINE)
NAMES = {
    "C01": "flat, L",
    "C02": "fixed tree, L",
    "C03": "learned tree, L",
    "C04": "flat, +R_conc",
    "C05": "learned tree, +R_conc",
    "C06": "flat, +R_co",
    "C07": "learned tree, +R_co",
    "C08": "flat, +R_temp",
    "C09": "learned tree, +R_temp",
    "C10": "learned tree, +R_co+R_temp",
}
# Okabe-Ito based: flat cases in blues, tree cases in oranges/browns (colour-blind safe), plus marker per objective.
COLOUR = {
    "C01": "#08306B", "C04": "#0072B2", "C06": "#56B4E9", "C08": "#8FC8EE",
    "C02": "#5C2A00", "C03": "#A63F00", "C05": "#D55E00", "C07": "#E69F00", "C09": "#F0C27B", "C10": "#8C6D1F",
}  # fmt: skip
MARKER = {"C01": "o", "C02": "o", "C03": "o", "C04": "s", "C05": "s", "C06": "^", "C07": "^", "C08": "D", "C09": "D", "C10": "P"}
PRIMARY, CONFIRM = "R2|C32|asc", "R8|C8|asc"
SETTINGS = {"R2|C32": "R=2 (hypothetical) rows/page, C=32 pages", "R8|C8": "R=8 (hypothetical) rows/page, C=8 pages"}
TIES = ["asc", "desc"]
LAYOUTS = ["L-ID", "L-FREQ", "L-COAX", "L-BCOAX", *[f"L-PCOAX-{i}" for i in range(1, 6)]]
MISS_NOTE = "simulated value-page misses per query (not physical I/O)"
BANNER = "SYNTHETIC DRY RUN — NOT A RESULT"
CAPS = {"train": 5400.0, "eval": 1800.0, "sim": 5400.0, "analysis": 600.0}
DENOMINATOR = 60
PARENT_COLOUR = {101: "#009E73", 102: "#332288", 103: "#AA4499"}
DPI = 150
plt.rcParams.update(
    {"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "legend.fontsize": 8, "axes.grid": True,
     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 100}
)  # fmt: skip


# --------------------------------------------------------------------------------------------- loading
def num(x: Any) -> float:
    """float from a JSON value: {"value": v, "exact": s} Fractions, plain numbers, None/''."""
    if isinstance(x, dict):
        x = x.get("value")
    if x is None or x == "":
        return NAN
    try:
        return float(x)
    except (TypeError, ValueError):
        return NAN


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_csv(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open(newline="") as stream:
        for row in csv.DictReader(stream):
            out.append({k: (v if k in TEXT_COLUMNS else num(v)) for k, v in row.items()})
    return out


TEXT_COLUMNS = {
    "label", "case", "architecture", "panel", "tie", "tag", "layout_case", "layout_reference",
    "reference_name", "reference", "objective", "baseline", "study_status", "class_A", "class_B",
    "study_class", "beats_optimized_flat", "architecture_advantage",
}  # fmt: skip


def mean(values: list[float]) -> float:
    ok = [v for v in values if not math.isnan(v)]
    return sum(ok) / len(ok) if len(ok) == len(values) and ok else NAN


class Data:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        a = Path(args.analysis_run)
        self.analysis_dir = a
        self.analysis: dict[str, Any] = read_json(a / "analysis.json")
        self.analysis_manifest: dict[str, Any] = (
            read_json(a / "manifest.json") if (a / "manifest.json").is_file() else {}
        )
        self.cells = read_csv(a / "cells.csv")
        self.pairs = read_csv(a / "pairs.csv")
        self.scorecard = read_csv(a / "scorecard.csv")
        self.eval_dir, self.sim_dir = Path(args.eval_run), Path(args.sim_run)
        self.eval_manifest = self._opt(self.eval_dir / "manifest.json")
        self.sim_manifest = self._opt(self.sim_dir / "manifest.json")
        self.train_dir = Path(args.train_run) if args.train_run else None
        self.train_manifest = self._opt(self.train_dir / "manifest.json") if self.train_dir else {}
        self.train_cells: dict[str, dict[str, Any]] = {}
        self.steps: dict[str, list[dict[str, Any]]] = {}
        if self.train_dir is not None:
            self._load_train()
        self.sims: dict[str, dict[str, Any]] = {}
        for label in self.labels():
            p = self.sim_dir / "cells" / label / "sim.json"
            if p.is_file():
                try:
                    self.sims[label] = read_json(p)
                except json.JSONDecodeError:
                    pass
        self.dry = bool(
            self.analysis.get("dry_run")
            or any(t.get("dry_run") for t in self.train_cells.values())
            or self.train_manifest.get("dry_run")
            or self.eval_manifest.get("dry_run")
            or self.sim_manifest.get("dry_run")
        )

    @staticmethod
    def _opt(path: Path) -> dict[str, Any]:
        return read_json(path) if path.is_file() else {}

    def labels(self) -> list[str]:
        out = []
        for backbone, order in ((101, 301), (102, 302), (103, 303)):
            for seed in (601, 602):
                for case in CASES:
                    out.append(f"b{backbone}-o{order}-s{seed}-{case}")
        return out

    def _load_train(self) -> None:
        assert self.train_dir is not None
        for label in self.labels():
            folder = self.train_dir / "cells" / label
            if (folder / "train.json").is_file():
                try:
                    rec = read_json(folder / "train.json")
                except json.JSONDecodeError:
                    continue
                if rec.get("status") != "completed":
                    continue
                self.train_cells[label] = rec
                steps = []
                if (folder / "steps.jsonl").is_file():
                    for line in (folder / "steps.jsonl").read_text().splitlines():
                        if line.strip():
                            try:
                                steps.append(json.loads(line))
                            except json.JSONDecodeError:
                                break
                self.steps[label] = steps

    # status ---------------------------------------------------------------------------------------
    @property
    def n_records(self) -> int:
        return int(self.analysis.get("cells_with_complete_records", 0))

    @property
    def n_train(self) -> int | None:
        return None if self.train_dir is None else len(self.train_cells)

    @property
    def complete(self) -> bool:
        return (
            self.analysis.get("study_status") == "COMPLETE"
            and self.n_records == DENOMINATOR
            and (self.n_train is None or self.n_train == DENOMINATOR)
        )

    @property
    def n_complete(self) -> int:
        return self.n_records if self.n_train is None else min(self.n_records, self.n_train)

    def status_text(self) -> str:
        if self.complete and self.n_train is not None:
            return f"COMPLETE: {DENOMINATOR} of {DENOMINATOR}"
        if self.n_train is None:
            return (f"INCOMPLETE: no training run supplied; {self.n_records} of {DENOMINATOR} cells "
                    "have complete evaluation and simulation records")
        return (f"INCOMPLETE: {self.n_complete} of {DENOMINATOR} cells; {self.n_records} of {DENOMINATOR} with complete "
                f"evaluation and simulation records; {self.n_train} of {DENOMINATOR} with training records")

    # accessors ------------------------------------------------------------------------------------
    def case(self, c: str) -> dict[str, Any]:
        return self.analysis["cases"][c]

    def means(self, c: str, p: str) -> dict[str, Any]:
        return self.case(c)["panels"][p].get("means", {})

    def cond_rows(self, rows: list[dict[str, Any]], p: str, cond: str) -> list[dict[str, Any]]:
        r, cap, tie = cond.split("|")
        return [
            x for x in rows
            if x["panel"] == p and x["R"] == float(r[1:]) and x["C"] == float(cap[1:]) and x["tie"] == tie
        ]  # fmt: skip

    def cell_rows(self, case: str, p: str, cond: str = PRIMARY) -> list[dict[str, Any]]:
        return [x for x in self.cond_rows(self.cells, p, cond) if x["case"] == case]

    def tag_cond(self, c: str, p: str, cond: str, ref: str = "vs_baseline", tag: str = "L-COAX") -> dict[str, Any]:
        e = self.case(c)["panels"][p]
        block = e.get(ref) if ref == "vs_baseline" else e.get("vs_other", {}).get(ref)
        if not block or block.get("status") != "complete":
            return {}
        return block.get("tags", {}).get(tag, {}).get(cond, {})

    def quality(self, c: str, p: str) -> dict[str, Any]:
        block = self.case(c)["panels"][p].get("vs_baseline")
        if not block or block.get("status") != "complete":
            return {}
        return block.get("quality", {})


# ------------------------------------------------------------------------------------------- plotting
def finish(fig: Any, data: Data, path: Path, title: str, foot: str | None = None, legend: bool = False) -> None:
    fig.suptitle(title, fontsize=11, fontweight="bold", y=0.995, va="top")
    top = 0.955
    if data.dry:
        fig.text(0.5, 0.962, BANNER, ha="center", va="top", color="white", fontsize=11, fontweight="bold",
                 bbox={"facecolor": "#B00020", "edgecolor": "none", "pad": 3})  # fmt: skip
        top = 0.925
    if not data.complete:
        fig.text(0.01, 0.004, data.status_text(), color="#B00020", fontsize=8, fontweight="bold", va="bottom")
    if foot:
        fig.text(0.99, 0.004, foot, fontsize=7, ha="right", va="bottom", color="#333333")
    fig.tight_layout(rect=(0, 0.075 if legend else 0.03, 1, top))
    fig.savefig(path, dpi=DPI, metadata={"Software": None})
    plt.close(fig)


def case_label(c: str) -> str:
    return c


def legend_cases(fig: Any, cases: list[str], loc: str = "lower center") -> None:
    handles = [plt.Line2D([], [], marker=MARKER[c], color=COLOUR[c], linestyle="", markersize=7,
                          label=f"{c} {NAMES[c]}") for c in cases]  # fmt: skip
    fig.legend(handles=handles, loc=loc, ncol=5, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, 0.022))


def hatch_undef(ax: Any, x: float, width: float, ymax: float) -> None:
    ax.add_patch(Rectangle((x - width / 2, 0), width, ymax, facecolor="none", edgecolor="#777777", hatch="////", linewidth=0.6))
    ax.text(x, ymax * 0.5, "undef", rotation=90, ha="center", va="center", fontsize=7, color="#555555",
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5})  # fmt: skip


def bars_with_dots(ax: Any, data: Data, values: dict[str, float], dots: dict[str, list[float]], ylabel: str, title: str,
                   cases: list[str] | None = None, log: bool = False) -> None:  # fmt: skip
    cases = cases or CASES
    finite = [v for v in values.values() if not math.isnan(v)]
    ymax = max([*finite, *[d for ds in dots.values() for d in ds if not math.isnan(d)], 1e-9]) * 1.15
    for i, c in enumerate(cases):
        v = values.get(c, NAN)
        if math.isnan(v):
            hatch_undef(ax, i, 0.7, ymax)
            continue
        ax.bar(i, v, color=COLOUR[c], width=0.7, edgecolor="black", linewidth=0.4)
        ds = [d for d in dots.get(c, []) if not math.isnan(d)]
        if ds:
            ax.scatter([i] * len(ds), ds, s=9, color="white", edgecolor="black", linewidth=0.5, zorder=3)
    ax.set_xticks(range(len(cases)), [case_label(c) for c in cases], fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if log:
        ax.set_yscale("log")
    else:
        ax.set_ylim(0, ymax)


def per_case(data: Data, p: str, fn: Any, cond: str = PRIMARY) -> tuple[dict[str, float], dict[str, list[float]]]:
    vals: dict[str, float] = {}
    dots: dict[str, list[float]] = {}
    for c in CASES:
        rows = data.cell_rows(c, p, cond)
        d = [fn(r) for r in rows]
        dots[c] = d
        vals[c] = mean(d) if rows else NAN
    return vals, dots


# --------------------------------------------------------------------------------------- figure 1
def fmt(x: float, digits: int = 3, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "undef"
    return f"{x:+.{digits}f}" if signed else f"{x:.{digits}f}"


def fig01(data: Data, out: Path) -> str:
    header = ["Case", "Architecture /\nobjective", "NLL\nPanel A", "NLL\nPanel B", "ΔNLL\nPanel A", "ΔNLL\nPanel B", "M-ratio\nPanel A", "M-ratio\nPanel B",
              "E-ratio\nPanel A", "E-ratio\nPanel B", "adj. E-ratio\nPanel A", "adj. E-ratio\nPanel B", "U-ratio\nPanel A", "U-ratio\nPanel B", "Class\nPanel A", "Class\nPanel B"]  # fmt: skip
    widths = [0.55, 2.7, 0.95, 0.95, 1.0, 1.0, 0.95, 0.95, 0.95, 0.95, 1.1, 1.1, 0.95, 0.95, 2.1, 2.1]
    fig, ax = plt.subplots(figsize=(sum(widths) * 0.74 + 0.4, 7.0))
    ax.axis("off")
    ax.grid(False)
    total = sum(widths)
    row_h = 1.0
    x0 = [sum(widths[:i]) for i in range(len(widths))]

    def cell(ri: int, ci: int, text: str, undef: bool = False, bold: bool = False, face: str | None = None) -> None:
        y = -(ri + 1) * row_h
        ax.add_patch(Rectangle((x0[ci], y), widths[ci], row_h, facecolor=face or "white", edgecolor="#999999",
                               linewidth=0.5, hatch="////" if undef else None))  # fmt: skip
        ax.text(x0[ci] + widths[ci] / 2, y + row_h / 2, text, ha="center", va="center", fontsize=7.5 if ci < 14 else 6.8,
                fontweight="bold" if bold else "normal",
                bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.4} if undef else None)  # fmt: skip

    for ci, h in enumerate(header):
        cell(0, ci, h, bold=True, face="#E6E6E6")
    for ri, c in enumerate(CASES, start=1):
        cell(ri, 0, c, bold=True, face=COLOUR[c])
        ax.texts[-1].set_color("white" if c in {"C01", "C02", "C03", "C04", "C05", "C10"} else "black")
        cell(ri, 1, NAMES[c])
        for pi, p in enumerate(PANELS):
            cell(ri, 2 + pi, fmt(num(data.means(c, p).get("nll")), 4), undef=math.isnan(num(data.means(c, p).get("nll"))))
            q = data.quality(c, p)
            if c in BASELINE:
                v = num(q.get("delta_nll_mean"))
                cell(ri, 4 + pi, fmt(v, 5, True), undef=math.isnan(v))
                t = data.tag_cond(c, p, PRIMARY)
                for k, key in enumerate(("m_ratio", "e_ratio", "rho_adj")):
                    vv = num(t.get(key))
                    cell(ri, 6 + 2 * k + pi, fmt(vv), undef=math.isnan(vv))
                u = num(q.get("u_ratio"))
                cell(ri, 12 + pi, fmt(u), undef=math.isnan(u))
            else:
                for col in (4 + pi, 6 + pi, 8 + pi, 10 + pi, 12 + pi):
                    cell(ri, col, "baseline" if col == 4 + pi else "—")
            cls = data.case(c)["panels"][p].get("classification", "— (not regularized)")
            cell(ri, 14 + pi, wrap(cls, 22), undef=cls == "INCOMPLETE")
    ax.set_xlim(-0.05, total + 0.05)
    ax.set_ylim(-(len(CASES) + 1) * row_h - 1.4, 0.1)
    ax.text(0, -(len(CASES) + 1) * row_h - 0.25,
            wrap("Ratios: regularized case vs its baseline (C04/C06/C08 vs C01; C05/C07/C09/C10 vs C03); L-COAX, primary setting "
                 "R=2 (hypothetical), C=32, ascending tie rule. Hatched \"undef\": undefined by the registered rule. "
                 "NLL in nats/byte; ΔNLL = case minus baseline.", 190), fontsize=7.5, va="top", color="#333333")  # fmt: skip
    name = "fig01_scorecard.png"
    finish(fig, data, out / name, "Scorecard: ten cases, Panels A and B")
    return name


def wrap(text: str, width: int) -> str:
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return "\n".join(lines)


# --------------------------------------------------------------------------------------- figure 2
def pareto(points: dict[str, tuple[float, float]]) -> list[str]:
    names = [c for c, (x, y) in points.items() if not (math.isnan(x) or math.isnan(y))]
    front = []
    for c in names:
        x, y = points[c]
        if not any((points[o][0] <= x and points[o][1] <= y) and (points[o][0] < x or points[o][1] < y) for o in names if o != c):
            front.append(c)
    return sorted(front, key=lambda c: points[c][0])


OFFSETS = [(6, 6), (6, -11), (-30, 6), (-30, -11), (10, 14), (10, -18), (-34, 14), (-34, -18), (18, 0), (-40, 0)]


def fig02(data: Data, out: Path) -> str:
    fig, axes = plt.subplots(2, 2, figsize=(13, 9.5))
    for row, (metric, ylab) in enumerate((
        ("m_L-COAX", f"mean m under L-COAX, R=2 (hypothetical), C=32\n{MISS_NOTE}"),
        ("E_L-COAX", "mean E under L-COAX, R=2 (hypothetical), C=32\n(m ÷ count-preserving null under L-FREQ; not physical I/O)"),
    )):
        for col, p in enumerate(PANELS):
            ax = axes[row][col]
            pts: dict[str, tuple[float, float]] = {}
            for c in CASES:
                rows = data.cell_rows(c, p)
                xs, ys = [r["nll"] for r in rows], [r[metric] for r in rows]
                ax.scatter(xs, ys, s=14, color=COLOUR[c], marker=MARKER[c], alpha=0.28, linewidths=0)
                pts[c] = (mean(xs) if rows else NAN, mean(ys) if rows else NAN)
            for i, c in enumerate(CASES):
                x, y = pts[c]
                if math.isnan(x) or math.isnan(y):
                    continue
                ax.scatter([x], [y], s=70, color=COLOUR[c], marker=MARKER[c], edgecolor="black", linewidth=0.8, zorder=4)
                ax.annotate(c, (x, y), textcoords="offset points", xytext=OFFSETS[i % len(OFFSETS)], fontsize=7.5, zorder=5)
            front = pareto(pts)
            if len(front) > 1:
                ax.step([pts[c][0] for c in front], [pts[c][1] for c in front], where="post", color="black",
                        linewidth=1, linestyle="-", alpha=0.6, zorder=2, label="Pareto frontier (case means, lower-left)")  # fmt: skip
            elif front:
                ax.scatter([pts[front[0]][0]], [pts[front[0]][1]], s=170, facecolor="none", edgecolor="black", zorder=3,
                           label="Pareto frontier (case means, lower-left)")  # fmt: skip
            for base, colour, lab in (("C01", COLOUR["C04"], "flat guard: C01 + 0.005"), ("C03", COLOUR["C05"], "tree guard: C03 + 0.005")):
                b = pts.get(base, (NAN, NAN))[0]
                if not math.isnan(b):
                    ax.axvline(b + 0.005, color=colour, linestyle="--", linewidth=1.2, label=lab)
            ax.set_xlabel("mean final NLL (nats/byte)")
            ax.set_ylabel(ylab)
            ax.set_title(f"Panel {p}: " + ("m" if row == 0 else "E"))
            ax.margins(x=0.08, y=0.12)
            if row == 0 and col == 0:
                ax.legend(loc="best", frameon=True, fontsize=7)
    legend_cases(fig, CASES)
    name = "fig02_quality_vs_locality.png"
    finish(fig, data, out / name, "Quality versus locality (faint = cells, bold = case means; dashed = baseline + 0.005 nats/byte)", legend=True)
    return name


# --------------------------------------------------------------------------------------- figure 3
def fig03(data: Data, out: Path) -> str:
    metrics = [("n_eff", "entropy-effective slots N_eff", False), ("distinct_slots", "distinct slots selected", False),
               ("hot64_share", "share of selections on 64 most-selected slots", False),
               ("context_breadth", "mean distinct slots per 64-query context", False)]  # fmt: skip
    fig, axes = plt.subplots(2, 4, figsize=(17, 7.5))
    for r, p in enumerate(PANELS):
        for k, (key, lab, log) in enumerate(metrics):
            vals, dots = per_case(data, p, lambda row, key=key: row[key])
            bars_with_dots(axes[r][k], data, vals, dots, lab, f"Panel {p}", log=log)
    legend_cases(fig, CASES)
    name = "fig03_utilization.png"
    finish(fig, data, out / name, "Utilization on the hard evaluation trace (bars = case mean, dots = cells)", legend=True)
    return name


# --------------------------------------------------------------------------------------- figure 4
def case_tie_means(data: Data, c: str, p: str, setting: str, column: str) -> list[float]:
    out = []
    for tie in TIES:
        rows = data.cell_rows(c, p, f"{setting}|{tie}")
        out.append(mean([r[column] for r in rows]) if rows else NAN)
    return out


def fig04(data: Data, out: Path) -> str:
    series = [("m actual, L-FREQ", "m_L-FREQ", "#999999"), ("m actual, L-COAX", "m_L-COAX", "#0072B2"),
              ("count-preserving null (mean of 3), L-FREQ", "null_L-FREQ_mean", "#E69F00")]  # fmt: skip
    fig, axes = plt.subplots(2, 2, figsize=(17, 8.5))
    w = 0.26
    for r, p in enumerate(PANELS):
        for k, setting in enumerate(SETTINGS):
            ax = axes[r][k]
            ymax = 1e-9
            for si, (lab, col, colour) in enumerate(series):
                for i, c in enumerate(CASES):
                    lo_hi = case_tie_means(data, c, p, setting, col)
                    x = i + (si - 1) * w
                    if any(math.isnan(v) for v in lo_hi):
                        continue
                    mid = sum(lo_hi) / 2
                    ymax = max(ymax, max(lo_hi))
                    ax.bar(x, mid, width=w, color=colour, edgecolor="black", linewidth=0.3, label=lab if i == 0 else None)
                    ax.errorbar(x, mid, yerr=[[mid - min(lo_hi)], [max(lo_hi) - mid]], color="black", capsize=2, linewidth=0.8)
            ax.set_xticks(range(len(CASES)), CASES)
            ax.set_ylim(0, ymax * 1.4)
            ax.set_ylabel("mean m: simulated value-page misses\nper query (not physical I/O)", fontsize=8)
            ax.set_title(f"Panel {p}, {SETTINGS[setting]}")
            if r == 0 and k == 0:
                ax.legend(loc="upper left", frameon=True)
    name = "fig04_null_vs_actual.png"
    finish(fig, data, out / name, "Actual versus count-preserving null (bar = mean of the two tie rules, whisker = tie-rule range)")
    return name


# --------------------------------------------------------------------------------------- figure 5
PAIRS = [("C03", "C01"), ("C02", "C01"), ("C05", "C04"), ("C07", "C06"), ("C09", "C08")]


def fig05(data: Data, out: Path) -> str:
    metrics = [("m", "m_case", "m_reference", "m under L-COAX"), ("E", "E_case", "E_reference", "E under L-COAX"),
               ("NLL", "nll_case", "nll_reference", "final NLL (nats/byte)")]  # fmt: skip
    fig, axes = plt.subplots(len(PAIRS), 3, figsize=(14, 3.0 * len(PAIRS)), squeeze=False)
    for i, (child, parent) in enumerate(PAIRS):
        for k, (_, ck, rk, lab) in enumerate(metrics):
            ax = axes[i][k]
            for pi, p in enumerate(PANELS):
                rows = [x for x in data.cond_rows(data.pairs, p, PRIMARY)
                        if x["case"] == child and x["reference"] == parent and x["tag"] == "L-COAX"]  # fmt: skip
                seen = set()
                for x in rows:
                    key = (x["backbone"], x["seed"])
                    if key in seen:
                        continue
                    seen.add(key)
                    xs = [pi * 2.6, pi * 2.6 + 1]
                    ax.plot(xs, [x[rk], x[ck]], color=PARENT_COLOUR.get(int(x["backbone"]), "#555555"),
                            linestyle="-" if x["seed"] == 601 else ":", linewidth=1.2, alpha=0.9)  # fmt: skip
                    ax.scatter([xs[0]], [x[rk]], s=22, color=COLOUR[parent], marker=MARKER[parent], zorder=3, edgecolor="black", linewidth=0.3)
                    ax.scatter([xs[1]], [x[ck]], s=22, color=COLOUR[child], marker=MARKER[child], zorder=3, edgecolor="black", linewidth=0.3)
            ax.set_xticks([0, 1, 2.6, 3.6], [parent, child, parent, child])
            ax.set_xlim(-0.5, 4.1)
            ax.set_ylabel(lab, fontsize=8)
            ax.set_title(f"{child} vs {parent}", fontsize=9, pad=14)
            ax.text(0.5, 1.0, "Panel A", transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=7, color="#555555")
            ax.text(3.1, 1.0, "Panel B", transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=7, color="#555555")
            if k < 2:
                ax.set_ylim(bottom=0)
    handles = [plt.Line2D([], [], color=PARENT_COLOUR[b], label=f"parent B{b}") for b in PARENT_COLOUR] + [
        plt.Line2D([], [], color="black", linestyle="-", label="seed 601"), plt.Line2D([], [], color="black", linestyle=":", label="seed 602")]
    fig.legend(handles=handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 0.022))
    name = "fig05_flat_vs_tree_pairs.png"
    finish(fig, data, out / name, "Paired effects per (parent, seed) pair (left point = reference case, right point = tree case)",
           foot=f"m axes: {MISS_NOTE}; R=2 (hypothetical), C=32, ascending tie", legend=True)
    return name


# --------------------------------------------------------------------------------------- figure 6
def fig06(data: Data, out: Path) -> str:
    fig, axes = plt.subplots(2, 3, figsize=(17, 8))
    trees = [c for c in CASES if c not in FLAT]
    for r, p in enumerate(PANELS):
        ax = axes[r][0]
        w = 0.38
        for i, c in enumerate(CASES):
            recs = [s["panels"][p]["temporal_reuse"] for lab, s in data.sims.items() if s.get("case") == c and p in s.get("panels", {})]
            if not recs:
                hatch_undef(ax, i, 0.7, 1.0)
                continue
            act = mean([t["actual"]["value"] for t in recs])
            nul = mean([mean([t[f"null_{j}"]["value"] for j in (1, 2, 3)]) for t in recs])
            ax.bar(i - w / 2, act, w, color=COLOUR[c], edgecolor="black", linewidth=0.4, label="actual" if i == 0 else None)
            ax.bar(i + w / 2, nul, w, color="white", edgecolor=COLOUR[c], hatch="..", linewidth=1.0, label="count-preserving null (mean of 3)" if i == 0 else None)
        ax.set_xticks(range(len(CASES)), CASES)
        ax.set_ylabel("fraction of selections seen\nin previous 8 queries", fontsize=8)
        ax.set_ylim(0, 0.8)
        ax.set_title(f"Panel {p}: temporal reuse")
        if r == 0:
            ax.legend(loc="best", fontsize=7)
        for k, (key, lab) in enumerate((("top_fraction", "same top branch"), ("pair_fraction", "same visited pair"))):
            ax = axes[r][1 + k]
            for i, c in enumerate(trees):
                recs = [s["panels"][p].get("branch_persistence") for _, s in data.sims.items() if s.get("case") == c and p in s.get("panels", {})]
                recs = [t for t in recs if t]
                if not recs:
                    hatch_undef(ax, i, 0.7, 1.0)
                    continue
                act = mean([t["actual"][key] for t in recs])
                shuf = mean([t["order_shuffled"][key] for t in recs])
                ax.bar(i - w / 2, act, w, color=COLOUR[c], edgecolor="black", linewidth=0.4, label="actual" if i == 0 else None)
                ax.bar(i + w / 2, shuf, w, color="white", edgecolor=COLOUR[c], hatch="//", linewidth=1.0, label="order-shuffled" if i == 0 else None)
            ax.set_xticks(range(len(trees)), trees)
            ax.set_ylabel(f"fraction of consecutive pairs\n({lab})", fontsize=8)
            ax.set_title(f"Panel {p}: branch persistence ({lab})")
            ax.set_ylim(0, 1.0)
            if r == 0:
                ax.legend(loc="best", fontsize=7)
    name = "fig06_temporal_branch.png"
    finish(fig, data, out / name, "Temporal reuse (actual vs null) and branch persistence (actual vs order-shuffled), hard trace")
    return name


# --------------------------------------------------------------------------------------- figure 7
def fig07(data: Data, out: Path) -> str:
    cols = [(f"b{b}", b, s) for b in (101, 102, 103) for s in (601, 602)]
    metrics = [("m ratio (L-COAX)", lambda x: x["m_case"] / x["m_reference"] if x["m_reference"] else NAN, 1.0, ".2f"),
               ("E ratio (L-COAX)", lambda x: x["E_case"] / x["E_reference"] if x["E_reference"] else NAN, 1.0, ".2f"),
               ("ΔNLL vs baseline (nats/byte)", lambda x: x["delta_nll"], 0.0, "+.4f")]  # fmt: skip
    fig, axes = plt.subplots(2, 3, figsize=(17, 8.2))
    for r, p in enumerate(PANELS):
        rows = [x for x in data.cond_rows(data.pairs, p, PRIMARY) if x["reference_name"] == "baseline" and x["tag"] == "L-COAX"]
        for k, (lab, fn, centre, f) in enumerate(metrics):
            ax = axes[r][k]
            ax.grid(False)
            grid = np.full((len(REGULARIZED), len(cols)), np.nan)
            for i, c in enumerate(REGULARIZED):
                for j, (_, b, s) in enumerate(cols):
                    hit = [x for x in rows if x["case"] == c and x["backbone"] == b and x["seed"] == s]
                    if hit:
                        grid[i, j] = fn(hit[0])
            finite = grid[np.isfinite(grid)]
            spread = max(float(np.max(np.abs(finite - centre))) if finite.size else 0.1, 1e-6)
            norm = TwoSlopeNorm(vcenter=centre, vmin=centre - spread, vmax=centre + spread)
            cmap = matplotlib.colormaps["PuOr"].copy()
            cmap.set_bad("white")
            ax.imshow(np.ma.masked_invalid(grid), cmap=cmap, norm=norm, aspect="auto")
            for i in range(len(REGULARIZED)):
                for j in range(len(cols)):
                    v = grid[i, j]
                    if math.isnan(v):
                        ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, hatch="////", edgecolor="#777777", linewidth=0))
                        ax.text(j, i, "undef", ha="center", va="center", fontsize=7, bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5})
                    else:
                        rgba = cmap(norm(v))
                        dark = (0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]) < 0.45
                        ax.text(j, i, format(v, f), ha="center", va="center", fontsize=7, color="white" if dark else "black")
            ax.set_xticks(range(len(cols)), [f"{n}\ns{s}" for n, _, s in cols], fontsize=7)
            ax.set_yticks(range(len(REGULARIZED)), [f"{c} v {BASELINE[c]}" for c in REGULARIZED], fontsize=7)
            ax.set_title(f"Panel {p}: {lab}", fontsize=9)
    name = "fig07_heatmaps.png"
    finish(fig, data, out / name, "Per-pair effects: seven regularized cases × six (parent, seed) pairs",
           foot=f"Diverging scale centred at 1 (0 for ΔNLL). m: {MISS_NOTE}; R=2 (hypothetical), C=32, ascending tie.")
    return name


# --------------------------------------------------------------------------------------- figure 8
def series_by_case(data: Data, getter: Any) -> dict[str, list[list[tuple[int, float]]]]:
    out: dict[str, list[list[tuple[int, float]]]] = {c: [] for c in CASES}
    for label, steps in data.steps.items():
        case = label.rsplit("-", 1)[1]
        pts = []
        for s in steps:
            v = getter(s)
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                pts.append((int(s["step"]), float(v)))
        if pts:
            out[case].append(pts)
    return out


def draw_curves(ax: Any, ser: dict[str, list[list[tuple[int, float]]]], cases: list[str], title: str, ylabel: str,
                log: bool = False, style: str = "-", markers: bool = False) -> None:  # fmt: skip
    drew = False
    for c in cases:
        runs = ser.get(c, [])
        if not runs:
            continue
        drew = True
        for run in runs:
            ax.plot(*zip(*run, strict=True), color=COLOUR[c], alpha=0.18, linewidth=0.7, linestyle=style)
        steps = sorted({s for run in runs for s, _ in run})
        mean_y = [sum(v for run in runs for st, v in run if st == s) / sum(1 for run in runs for st, _ in run if st == s) for s in steps]
        ax.plot(steps, mean_y, color=COLOUR[c], linewidth=1.8, linestyle=style, marker="o" if markers else None, markersize=4, label=c)
    ax.set_title(title)
    ax.set_xlabel("update")
    ax.set_ylabel(ylabel)
    if log:
        ax.set_yscale("log")
    if drew:
        ax.legend(fontsize=7, ncol=2)
    else:
        ax.text(0.5, 0.5, "no records", transform=ax.transAxes, ha="center", va="center", color="#777777")


def fig08(data: Data, out: Path) -> str | None:
    if data.train_dir is None:
        return None
    fig, axes = plt.subplots(4, 3, figsize=(16, 18))
    ax = axes[0][0]
    wall = {c: NAN for c in CASES}
    wdots: dict[str, list[float]] = {c: [] for c in CASES}
    rss = {c: NAN for c in CASES}
    rdots: dict[str, list[float]] = {c: [] for c in CASES}
    for label, rec in data.train_cells.items():
        c = label.rsplit("-", 1)[1]
        wdots[c].append(num(rec.get("wall_seconds")))
        rdots[c].append(num(rec.get("peak_rss_bytes")) / 2**20)
    for c in CASES:
        wall[c] = mean(wdots[c]) if wdots[c] else NAN
        rss[c] = mean(rdots[c]) if rdots[c] else NAN
    bars_with_dots(ax, data, wall, wdots, "wall seconds per cell (measured)", f"Training wall time ({len(data.train_cells)} of {DENOMINATOR} cells)")
    bars_with_dots(axes[0][1], data, rss, rdots, "peak RSS per cell (MiB, measured)", "Training peak RSS (limit 2048 MiB per worker)")
    draw_curves(axes[0][2], series_by_case(data, lambda s: s.get("loss")), CASES, "Language-model loss (mean over cells; faint = cells)", "mean next-byte loss (nats/byte)")
    for k, (name, lab) in enumerate((("conc", "R_conc"), ("co", "R_co"), ("temp", "R_temp"))):
        ser = series_by_case(data, lambda s, name=name: (s.get("regularizer") or {}).get(name))
        cases = [c for c in REGULARIZED if any(name in obj for obj in [data_obj(c)])]
        draw_curves(axes[1][k], ser, cases, f"{lab} on the training batch", lab)
    lam_conc = series_by_case(data, lambda s: (s.get("lam") or {}).get("conc"))
    lam_co = series_by_case(data, lambda s: (s.get("lam") or {}).get("co"))
    lam_temp = series_by_case(data, lambda s: (s.get("lam") or {}).get("temp"))
    ax = axes[2][0]
    for ser, style, lab in ((lam_conc, "-", "λ_conc"), (lam_co, "--", "λ_co"), (lam_temp, ":", "λ_temp")):
        draw_lambda(ax, ser, style, lab)
    ax.set_yscale("log")
    ax.set_title("λ (matched-pressure coefficient; line style = regularizer)")
    ax.set_xlabel("update")
    ax.set_ylabel("λ (log scale)")
    handles = [plt.Line2D([], [], color="black", linestyle=s, label=lab) for s, lab in (("-", "λ_conc"), ("--", "λ_co"), (":", "λ_temp"))]
    ax.legend(handles=handles, fontsize=7)
    gap = series_by_case(data, lambda s: (s.get("diagnostics") or {}).get("mean_gap_8_9"))
    draw_curves(axes[2][1], gap, CASES, "Mean 8th–9th score gap (logged updates)", "score gap", markers=True)
    pi = series_by_case(data, lambda s: (s.get("diagnostics") or {}).get("mean_pi_mass_outside_top8"))
    draw_curves(axes[2][2], pi, CASES, "π mass outside the top 8 (logged updates)", "sum of π outside top 8 per query", markers=True)
    for k, key in enumerate(("theta_r", "other")):
        ser = series_by_case(data, lambda s, key=key: (s.get("param_change_l2") or {}).get(key))
        draw_curves(axes[3][k], ser, CASES, f"Norm of per-update parameter change: {'Θ_r (keys, wq, router)' if key == 'theta_r' else 'remaining parameters'}",
                    "L2 norm of change", log=True)
    axes[3][2].axis("off")
    axes[3][2].text(0.0, 0.8, "Curves: bold = mean over the cells present for the case,\nfaint = individual cells.\n"
                    "λ and R appear only for the case's own regularizers.\nGap and π mass are logged at updates 1, 128, 256, 384, 512.",
                    fontsize=8, va="top")  # fmt: skip
    name = "fig08_training_resources.png"
    finish(fig, data, out / name, f"Training resources and curves ({len(data.train_cells)} of {DENOMINATOR} cells present)")
    return name


def data_obj(case: str) -> list[str]:
    return {"C04": ["conc"], "C05": ["conc"], "C06": ["co"], "C07": ["co"], "C08": ["temp"], "C09": ["temp"], "C10": ["co", "temp"]}.get(case, [])


def draw_lambda(ax: Any, ser: dict[str, list[list[tuple[int, float]]]], style: str, lab: str) -> None:
    for c, runs in ser.items():
        if not runs:
            continue
        for run in runs:
            pos = [(s, v) for s, v in run if v > 0]
            if pos:
                ax.plot(*zip(*pos, strict=True), color=COLOUR[c], alpha=0.15, linewidth=0.6, linestyle=style)
        steps = sorted({s for run in runs for s, _ in run})
        ys = []
        for s in steps:
            vals = [v for run in runs for st, v in run if st == s]
            ys.append(sum(vals) / len(vals) if vals else NAN)
        pairs = [(s, y) for s, y in zip(steps, ys, strict=True) if y > 0]
        if pairs:
            ax.plot(*zip(*pairs, strict=True), color=COLOUR[c], linewidth=1.5, linestyle=style)


# --------------------------------------------------------------------------------------- figure 9
def fig09(data: Data, out: Path) -> str:
    fig, axes = plt.subplots(2, 3, figsize=(17, 8))
    titles = ["arbitrary-partition control: mean L-PCOAX ÷ L-COAX", "L-BCOAX ÷ L-COAX (tree cases)", "trained-in layout: L-ID ÷ L-COAX"]
    for r, p in enumerate(PANELS):
        for k in range(3):
            ax = axes[r][k]
            cases = CASES if k != 1 else [c for c in CASES if c not in FLAT]
            vals: dict[str, float] = {}
            vals2: dict[str, float] = {}
            for c in cases:
                for cond, store in ((PRIMARY, vals), (CONFIRM, vals2)):
                    ctrl = data.case(c)["panels"][p].get("controls", {}).get(cond, {})
                    if k == 0:
                        store[c] = num(ctrl.get("partition_over_coax"))
                    elif k == 2:
                        store[c] = num(ctrl.get("id_over_coax"))
                    else:
                        lay = data.means(c, p).get("layouts", {}).get(cond, {})
                        den = num((lay.get("L-COAX") or {}).get("m_mean")) if lay else NAN
                        # zero misses under L-COAX: the ratio is undefined, never a number (fixed after
                        # the registered run; the first real render raised ZeroDivisionError here)
                        store[c] = num((lay.get("L-BCOAX") or {}).get("m_mean")) / den if lay and den > 0 else NAN
            allv = [v for v in [*vals.values(), *vals2.values()] if not math.isnan(v)]
            hi = max([1.1, *allv])
            lo = min([0.9, *allv])
            for i, c in enumerate(cases):
                v = vals.get(c, NAN)
                if math.isnan(v):
                    ax.add_patch(Rectangle((i - 0.35, 0.95), 0.7, 0.1, facecolor="none", edgecolor="#777777", hatch="////", linewidth=0.6))
                    ax.text(i, 1.0, "undef", ha="center", va="center", fontsize=7, bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.5})
                    continue
                edge = "black"
                trained = k == 2 and c in ("C06", "C07", "C10")
                ax.bar(i, v - 1.0, bottom=1.0, color=COLOUR[c], edgecolor=edge, linewidth=2.2 if trained else 0.4, width=0.7,
                       hatch="xx" if (k == 2 and not trained) else None, label=None)  # fmt: skip
                v2 = vals2.get(c, NAN)
                if not math.isnan(v2):
                    ax.scatter([i], [v2], marker="D", s=26, facecolor="white", edgecolor="black", zorder=4, label="R=8 (hypothetical), C=8" if i == 0 else None)
            ax.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
            ax.set_xticks(range(len(cases)), cases)
            ax.set_ylim(lo - 0.05, hi + 0.08)
            ax.set_ylabel("ratio of mean simulated misses\n(not physical I/O); bars drawn from 1", fontsize=8)
            ax.set_title(f"Panel {p}: {titles[k]}", fontsize=9)
            if k == 2 and r == 0:
                ax.text(0.01, 0.98, "thick outline: objective refers to slot-ID groups (C06, C07, C10);\nhatched: reported for reference only", transform=ax.transAxes, va="top", fontsize=7, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    name = "fig09_layout_controls.png"
    finish(fig, data, out / name, "Layout controls (reported, not part of any classification)",
           foot="Bars: R=2 (hypothetical), C=32, ascending tie. Diamonds: R=8 (hypothetical), C=8, ascending tie. Dashed line = 1.")
    return name


FIGURES: list[tuple[str, Any, str]] = [
    ("fig01_scorecard.png", fig01, "Ten-case table of final NLL, change in NLL against baseline, M-ratio, E-ratio, utilization-adjusted E-ratio, U-ratio and class, per panel (L-COAX, R=2 hypothetical rows/page, C=32 pages, ascending tie rule)."),
    ("fig02_quality_vs_locality.png", fig02, "Mean final NLL against mean simulated value-page misses (m) and against E under L-COAX at the primary setting, per panel, with cell points, case means, the lower-left Pareto set of case means and the baseline + 0.005 nats/byte lines."),
    ("fig03_utilization.png", fig03, "Entropy-effective slots, distinct slots, share of selections on the 64 most-selected slots and mean distinct slots per 64-query context, per case and panel."),
    ("fig04_null_vs_actual.png", fig04, "Mean simulated misses of the actual trace under L-FREQ and L-COAX and of the count-preserving null under L-FREQ, per case, panel and cache setting, with the tie-rule range as whiskers."),
    ("fig05_flat_vs_tree_pairs.png", fig05, "Per (parent, seed) pair values of m under L-COAX, E under L-COAX and final NLL for C03 vs C01, C02 vs C01, C05 vs C04, C07 vs C06 and C09 vs C08, both panels."),
    ("fig06_temporal_branch.png", fig06, "Temporal reuse of the actual trace and of the count-preserving null per case, and branch persistence of the actual and order-shuffled trace for tree cases, per panel."),
    ("fig07_heatmaps.png", fig07, "Per (parent, seed) pair m ratio, E ratio (both under L-COAX) and change in NLL against baseline for the seven regularized cases, per panel."),
    ("fig08_training_resources.png", fig08, "Per-case wall seconds and peak RSS of the training cells and training curves (loss, regularizer values, lambda, 8th-9th score gap, pi mass outside the top 8, parameter-change norms)."),
    ("fig09_layout_controls.png", fig09, "Mean L-PCOAX over L-COAX, L-BCOAX over L-COAX (trees) and L-ID over L-COAX simulated misses per case and panel at both cache settings."),
]


# --------------------------------------------------------------------------------------- html helpers
def esc(x: Any) -> str:
    return html.escape(str(x))


def inline_md(text: str) -> str:
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", text)


def markdown(md: str) -> str:
    lines, out, i = md.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            i += 1
        elif s.startswith("#"):
            level = min(len(s) - len(s.lstrip("#")), 4)
            out.append(f"<h{level + 2}>{inline_md(s.lstrip('#').strip())}</h{level + 2}>")
            i += 1
        elif s.startswith(("- ", "* ")):
            items = []
            while i < len(lines) and lines[i].strip().startswith(("- ", "* ")):
                items.append(f"<li>{inline_md(lines[i].strip()[2:])}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
        elif s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                head = "".join(f"<th>{inline_md(c)}</th>" for c in rows[0])
                body = "".join("<tr>" + "".join(f"<td>{inline_md(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
                out.append(f"<div class='scroll'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>")
        else:
            para = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("#", "- ", "* ", "|")):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline_md(' '.join(para))}</p>")
    return "\n".join(out)


def rng(values: list[float], digits: int = 3) -> str:
    ok = [v for v in values if not math.isnan(v)]
    if len(ok) < len(values):
        return "undef"
    lo, hi = min(ok), max(ok)
    return f"{lo:.{digits}f}" if f"{lo:.{digits}f}" == f"{hi:.{digits}f}" else f"{lo:.{digits}f}–{hi:.{digits}f}"


def ratio_cell(data: Data, c: str, p: str, setting: str, key: str) -> str:
    vals = [num(data.tag_cond(c, p, f"{setting}|{t}").get(key)) for t in TIES]
    if c not in BASELINE:
        return "—"
    return "<span class='undef'>undef</span>" if any(math.isnan(v) for v in vals) else rng(vals)


def scorecard_html(data: Data) -> str:
    head = ["Case", "Architecture / objective", "Panel", "NLL", "ΔNLL", "Gain retention", "M R2/C32", "E R2/C32", "adj. E R2/C32",
            "M R8/C8", "E R8/C8", "adj. E R8/C8", "U-ratio", "pairs E<base (of 6)", "parents E<base (of 3)", "Class", "Study class", "Beats optimized flat", "Architecture advantage"]  # fmt: skip
    rows = []
    for c in CASES:
        e = data.case(c)
        study = e.get("study_classification", {})
        for pi, p in enumerate(PANELS):
            q = data.quality(c, p)
            t = data.tag_cond(c, p, PRIMARY)
            cells = [f"<td rowspan='2'>{esc(c)}</td><td rowspan='2'>{esc(NAMES[c])}</td>" if pi == 0 else "", f"<td>{p}</td>",
                     f"<td>{fmt(num(data.means(c, p).get('nll')), 4)}</td>"]  # fmt: skip
            if c in BASELINE:
                cells += [f"<td>{fmt(num(q.get('delta_nll_mean')), 5, True)}</td>", f"<td>{fmt(num(q.get('gain_retention')), 3)}</td>"]
                for s in ("R2|C32", "R8|C8"):
                    cells += [f"<td>{ratio_cell(data, c, p, s, k)}</td>" for k in ("m_ratio", "e_ratio", "rho_adj")]
                cells += [f"<td>{fmt(num(q.get('u_ratio')), 3)}</td>", f"<td>{int(num(t.get('pairs_e_lower'))) if not math.isnan(num(t.get('pairs_e_lower'))) else 'undef'}</td>",
                          f"<td>{int(num(t.get('parents_e_below_one'))) if not math.isnan(num(t.get('parents_e_below_one'))) else 'undef'}</td>"]  # fmt: skip
            else:
                cells += ["<td>baseline</td>"] + ["<td>—</td>"] * 10
            cells.append(f"<td>{esc(e['panels'][p].get('classification', '—'))}</td>")
            if pi == 0:
                beats = e.get("beats_optimized_flat", {})
                arch = e.get("architecture_advantage", {})
                cells.append(f"<td rowspan='2'>{esc(study.get('class', '—'))}</td>")
                cells.append(f"<td rowspan='2'>{yn(beats, c in BASELINE)}</td><td rowspan='2'>{yn(arch, c in BASELINE)}</td>")
            rows.append(f"<tr class='{'tree' if c not in FLAT else 'flat'}'>{''.join(cells)}</tr>")
    thead = "".join(f"<th>{esc(h)}</th>" for h in head)
    return f"<div class='scroll'><table class='score'><thead><tr>{thead}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def yn(block: dict[str, Any], applicable: bool) -> str:
    if not applicable:
        return "—"
    if block.get("status") == "INCOMPLETE":
        return "INCOMPLETE"
    if "reason" in block:
        return "n/a (no flat counterpart)"
    return "yes" if block.get("holds") else "no"


def resource_rows(data: Data) -> list[dict[str, Any]]:
    tm, em, sm = data.train_manifest, data.eval_manifest, data.sim_manifest
    am = data.analysis_manifest
    rows = []
    if data.train_dir is not None:
        walls = [num(r.get("wall_seconds")) for r in data.train_cells.values()]
        rss = [num(r.get("peak_rss_bytes")) for r in data.train_cells.values()]
        rows.append({"stage": "Training (cells present)", "wall_s_total": sum(w for w in walls if not math.isnan(w)),
                     "wall_s_basis": "sum of per-cell wall seconds (cells ran up to 4 in parallel)", "stage_wall_s": num(tm.get("stage_wall_seconds")),
                     "cap_s": CAPS["train"], "max_cell_s": max([w for w in walls if not math.isnan(w)], default=NAN), "cell_cap_s": 600.0,
                     "peak_worker_rss_mib": max([r for r in rss if not math.isnan(r)], default=NAN) / 2**20,
                     "peak_aggregate_rss_mib": num(tm.get("peak_aggregate_rss_bytes")) / 2**20, "records": f"{len(data.train_cells)} of {DENOMINATOR}"})  # fmt: skip
    for name, m, cap in (("Evaluation, interventions, traces", em, CAPS["eval"]), ("Layouts and simulation", sm, CAPS["sim"])):
        rows.append({"stage": name, "stage_wall_s": num(m.get("wall_seconds")), "cap_s": cap,
                     "peak_worker_rss_mib": num(m.get("peak_worker_rss_bytes")) / 2**20,
                     "peak_aggregate_rss_mib": num(m.get("peak_aggregate_rss_bytes")) / 2**20,
                     "records": f"{m.get('cells_completed', 'n/a')} of {m.get('cells_expected', DENOMINATOR)}"})  # fmt: skip
    rows.append({"stage": "Analysis", "stage_wall_s": num(am.get("wall_seconds")), "cap_s": CAPS["analysis"], "records": f"{data.n_records} of {DENOMINATOR}"})
    return rows


def resource_html(rows: list[dict[str, Any]]) -> str:
    head = ["Stage", "Stage wall seconds (measured)", "Cap (s)", "Largest cell wall (s)", "Peak worker RSS (MiB)", "Peak aggregate RSS (MiB)", "Cells with records"]
    body = []
    for r in rows:
        cells = [esc(r["stage"]), fmt(r.get("stage_wall_s", NAN), 1), f"{r['cap_s']:.0f}", fmt(r.get("max_cell_s", NAN), 1),
                 fmt(r.get("peak_worker_rss_mib", NAN), 0), fmt(r.get("peak_aggregate_rss_mib", NAN), 0), esc(r["records"])]  # fmt: skip
        body.append("<tr>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")
    total = sum(r["stage_wall_s"] for r in rows if not math.isnan(r.get("stage_wall_s", NAN)))
    return (f"<div class='scroll'><table><thead><tr>{''.join(f'<th>{h}</th>' for h in head)}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
            f"<p class='note'>Sum of the stage wall times listed above: {total:.1f} s (measured; the human-set ceiling for the whole study is 8 h of active wall time). "
            "Training cells with regularizers run two backward passes per update: equal updates, not equal compute.</p>")  # fmt: skip


CSS = """
:root{--bg:#fff;--fg:#1b1b1b;--muted:#555;--line:#c9c9c9;--card:#f6f6f6;--warn:#b00020;--accent:#0072B2}
@media (prefers-color-scheme: dark){:root{--bg:#15171a;--fg:#e8e8e8;--muted:#a8a8a8;--line:#444;--card:#202328;--warn:#ff6b81;--accent:#56B4E9}
img{background:#fff}}
*{box-sizing:border-box}body{margin:0;padding:0 1rem 3rem;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;max-width:1200px;margin-inline:auto}
h1{font-size:1.5rem;margin:1rem 0 .3rem}h2{font-size:1.2rem;margin-top:2rem;border-bottom:1px solid var(--line);padding-bottom:.2rem}
.banner{border:2px solid var(--warn);border-radius:6px;padding:.6rem .8rem;margin:.8rem 0;background:var(--card)}
.banner strong.red,.red{color:var(--warn)}.dry{background:var(--warn);color:#fff;padding:.5rem .8rem;border-radius:6px;font-weight:700;text-align:center;margin:.8rem 0;font-size:1.05rem}
.scroll{overflow-x:auto;margin:.6rem 0}table{border-collapse:collapse;font-size:.78rem}th,td{border:1px solid var(--line);padding:.2rem .4rem;text-align:center;white-space:nowrap}
th{background:var(--card)}td:nth-child(2){text-align:left}tr.flat td:first-child{border-left:5px solid #0072B2}tr.tree td:first-child{border-left:5px solid #D55E00}
.undef{background:repeating-linear-gradient(45deg,transparent 0 3px,var(--line) 3px 4px);padding:0 .3rem}
figure{margin:1.2rem 0;padding:.5rem;background:var(--card);border-radius:6px}figure img{max-width:100%;height:auto;display:block}
figcaption{font-size:.85rem;color:var(--muted);margin-top:.4rem}.note,.small{font-size:.82rem;color:var(--muted)}code{font-size:.85em}
ul{padding-left:1.3rem}a{color:var(--accent)}
@media (max-width:600px){body{font-size:14px;padding:0 .5rem 2rem}h1{font-size:1.25rem}}
"""


def build_html(data: Data, out: Path, figs: list[tuple[str, str]], rows: list[dict[str, Any]], summary: str | None, hashes: dict[str, str]) -> str:
    banner_dry = f"<div class='dry'>{BANNER}</div>" if data.dry else ""
    status = data.status_text()
    status_cls = "" if data.complete else "red"
    missing = data.analysis.get("missing_cells", [])
    miss_html = ""
    if missing:
        items = "".join(f"<li><code>{esc(m.get('label'))}</code>: {esc('; '.join(m.get('reasons', [])))}</li>" for m in missing)
        miss_html = f"<details><summary>{len(missing)} cells without complete records</summary><ul>{items}</ul></details>"
    di = data.analysis.get("decision_inputs", {})
    flags = (f"<ul><li>Concentration controls bind (C04 or C05 LOCALITY-POSITIVE on either panel): <strong>{esc(data.analysis.get('concentration_controls_bind'))}</strong></li>"
             f"<li>Section 8 mechanical map indicates option: <strong>{esc(di.get('section_8_option_indicated'))}</strong> ({esc(di.get('section_8_reason'))}). {esc(di.get('note', ''))}</li>"
             f"<li>Cases LOCALITY-POSITIVE on both panels: {esc(', '.join(di.get('locality_positive_cases_both_panels', [])) or 'none')}</li>"
             f"<li>Architecture advantage cases: {esc(', '.join(di.get('architecture_advantage_cases', [])) or 'none')}</li></ul>")  # fmt: skip
    parts = [f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>P8 report</title><style>{CSS}</style></head><body>",
             "<h1>P8: locality-aware memory training pilot</h1>", banner_dry]
    parts.append(f"<div class='banner'><div><strong class='{status_cls}'>Study status: {esc(status)}</strong></div>"
                 "<div><strong>Astra review: NOT_PERFORMED.</strong> Self-checks by the Claude workflow are not independent review, not Astra validation and not human approval.</div>"
                 "<div><strong>Simulation, not physical I/O.</strong> Misses are simulated value-page misses of a page model at hypothetical row sizes (R=2 and R=8 rows/page). No latency, throughput or SSD claim can be drawn.</div>"
                 f"<div class='small'>Denominator is {DENOMINATOR} training cells (10 cases × 3 parents × 2 seeds) and is never reduced. Pilot of three correlated parents and two seeds: no significance claim.</div>{miss_html}</div>")  # fmt: skip
    if summary:
        parts.append(f"<h2>Lead's summary</h2><div class='summary'>{markdown(summary)}</div>")
    parts.append("<h2>Scorecard</h2>")
    parts.append("<p class='small'>Ratios compare each regularized case with its registered baseline (C04, C06, C08 against C01; C05, C07, C09, C10 against C03) under L-COAX. "
                 "Ratio cells show the range across the two tie rules (ascending, descending). \"undef\": undefined by the registered rule. Values are measured simulation outputs and analytical ratios of them; classes are the registered mechanical rules, not interpretation.</p>")  # fmt: skip
    parts.append(scorecard_html(data))
    parts.append("<h2>Study-level flags</h2>" + flags)
    parts.append("<h2>Figures</h2>")
    for name, cap in figs:
        b64 = base64.b64encode((out / name).read_bytes()).decode()
        parts.append(f"<figure id='{name[:5]}'><img alt='{esc(cap)}' src='data:image/png;base64,{b64}'><figcaption><strong>{esc(name)}</strong>. {esc(cap)}</figcaption></figure>")
    parts.append("<h2>Resource accounting</h2>" + resource_html(rows))
    parts.append("<h2>Files</h2><ul>" + "".join(
        f"<li><a href='{n}'>{n}</a> <span class='small'>sha256 {h[:16]}…</span></li>" for n, h in hashes.items()) + "</ul>")
    parts.append("<p class='small'>Generated by <code>results/p8-2026-11-14/report/make_report.py</code> (analysis-only; reads records, recomputes nothing registered).</p></body></html>")
    return "\n".join(parts)


# --------------------------------------------------------------------------------------- compact json
def compact(data: Data, rows: list[dict[str, Any]], inputs: dict[str, str]) -> dict[str, Any]:
    sc: dict[str, Any] = {}
    for c in CASES:
        e = data.case(c)
        entry: dict[str, Any] = {"architecture": e["architecture"], "objective": e["objective"], "baseline": e.get("baseline"),
                                 "study_classification": e.get("study_classification"),
                                 "beats_optimized_flat": e.get("beats_optimized_flat", {}).get("holds"),
                                 "architecture_advantage": e.get("architecture_advantage", {}).get("holds"), "panels": {}}  # fmt: skip
        for p in PANELS:
            q = data.quality(c, p)
            pe: dict[str, Any] = {"classification": e["panels"][p].get("classification"),
                                  "nll": num(data.means(c, p).get("nll")), "n_eff": num(data.means(c, p).get("n_eff")),
                                  "delta_nll": num(q.get("delta_nll_mean")), "gain_retention": num(q.get("gain_retention")),
                                  "association_retention": num(q.get("association_retention")), "u_ratio": num(q.get("u_ratio")), "conditions": {}}  # fmt: skip
            if c in BASELINE:
                for cond in data.analysis.get("conditions", []):
                    t = data.tag_cond(c, p, cond)
                    pe["conditions"][cond] = {k: (None if math.isnan(num(t.get(k))) else num(t.get(k))) for k in ("m_ratio", "e_ratio", "rho_adj", "pairs_e_lower", "parents_e_below_one")}
            entry["panels"][p] = pe
        sc[c] = entry
    return {
        "schema": "P8-report-compact-v1",
        "dry_run": data.dry,
        "synthetic_banner": BANNER if data.dry else None,
        "astra_review": "NOT_PERFORMED",
        "note": "simulation, not physical I/O; self-check output, not independent review",
        "study_status": "COMPLETE" if data.complete else "INCOMPLETE",
        "status_text": data.status_text(),
        "cells_expected": DENOMINATOR,
        "cells_with_complete_eval_sim_records": data.n_records,
        "training_records_found": data.n_train,
        "missing_cells": data.analysis.get("missing_cells", []),
        "concentration_controls_bind": data.analysis.get("concentration_controls_bind"),
        "decision_inputs": data.analysis.get("decision_inputs"),
        "scorecard": sc,
        "resource_totals": rows,
        "input_sha256": inputs,
    }


def clean(x: Any) -> Any:
    if isinstance(x, float) and math.isnan(x):
        return None
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, list):
        return [clean(v) for v in x]
    return x


# --------------------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysis-run", required=True, type=Path)
    ap.add_argument("--eval-run", required=True, type=Path)
    ap.add_argument("--sim-run", required=True, type=Path)
    ap.add_argument("--train-run", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--summary-md", type=Path, default=None)
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    data = Data(args)
    made: list[tuple[str, str]] = []
    for name, fn, cap in FIGURES:
        result = fn(data, out)
        if result:
            made.append((result, cap))
        else:
            print(f"skipped {name}: no --train-run")
    for name in ("scorecard.csv", "pairs.csv", "cells.csv", "analysis.json"):
        shutil.copyfile(data.analysis_dir / name, out / name)
    rows = resource_rows(data)
    inputs = {f"analysis/{n}": sha256(data.analysis_dir / n) for n in ("analysis.json", "scorecard.csv", "cells.csv", "pairs.csv")}
    (out / "p8_results_compact.json").write_text(json.dumps(clean(compact(data, rows, inputs)), indent=2, sort_keys=True) + "\n")
    (out / "figures_index.md").write_text(
        "# P8 figures\n\n"
        + (f"**{BANNER}**\n\n" if data.dry else "")
        + f"Study status: {data.status_text()}. Astra review: NOT_PERFORMED. Simulated misses are not physical I/O.\n\n"
        + "".join(f"- `{n}`: {c}\n" for n, c in made)
    )
    summary = args.summary_md.read_text() if args.summary_md else None
    files = {n: sha256(out / n) for n in ("scorecard.csv", "pairs.csv", "cells.csv", "analysis.json", "p8_results_compact.json", "figures_index.md")}
    (out / "report.html").write_text(build_html(data, out, made, rows, summary, files))
    print(f"report written to {out} ({len(made)} figures; {data.status_text()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
