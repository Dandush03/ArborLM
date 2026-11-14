"""Synthetic stand-ins for the dry run and the tests (never used by a registered stage).

Everything here is labelled synthetic: a tiny random fixture model per checkpoint, traces
regenerated from it, an identity manifest in the real schema, a P7-A-style reference record
produced by this study's own simulator (so the reproduction check exercises its machinery but is
**not** independent evidence), and a small text corpus for the panel reconstruction. None of it
touches ``experiments/`` or ``results/``.

Status: implementation self-checked only. Not independent review, not Astra validation.
"""

import random
from pathlib import Path
from typing import Any

from torch import Tensor

from . import p6_common as common
from . import p7a_core as a_core
from . import p7b_core as core
from . import p7b_sim as sim
from .io import write_json
from .p6_common import Pair
from .p7a_trace import collect_trace

SYNTHETIC_CALIBRATION_OFFSET = 16  # train rows 16.. (the fixture holds 32 rows)


def synthetic_calibration(train: Tensor, contexts: int) -> Tensor:
    return train[SYNTHETIC_CALIBRATION_OFFSET : SYNTHETIC_CALIBRATION_OFFSET + contexts]


def synthetic_corpus(seed: int, rows: int, length: int = 320) -> list[str]:
    generator = random.Random(seed)
    alphabet = "abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,;"
    return ["".join(generator.choice(alphabet) for _ in range(length)) for _ in range(rows)]


def build_identity(
    root: Path, pair_list: list[Pair], contexts: int
) -> tuple[core.Identity, dict[str, dict[str, Any]]]:
    """Trace every synthetic checkpoint (stream A on the fixture's panel, calibration on its
    training rows), write the files under ``root`` and an identity manifest in the real schema.
    Returns the identity and, per label, the in-memory traces (for building references)."""
    checkpoints: list[dict[str, Any]] = []
    kept: dict[str, dict[str, Any]] = {}
    queries = contexts * core.CONTEXT
    for pair in pair_list:
        source = common.load_synthetic_cell(pair, rows=contexts)
        calibration = synthetic_calibration(source.train, contexts)
        for kind in core.KINDS:
            label = core.cell_label(pair, kind)
            model = source.models[kind]
            eval_sel, eval_br = collect_trace(model, source.panel)
            cal_sel, cal_br = collect_trace(model, calibration)
            directory = root / "p7a-traces" / label
            files = {
                "evaluation": a_core.write_trace(directory, "eval", eval_sel, eval_br, queries),
                "calibration": a_core.write_trace(directory, "calib", cal_sel, cal_br, queries),
            }
            entries = []
            for part in ("evaluation", "calibration"):
                for name in ("selected", "branches"):
                    f = files[part][name]
                    if f is None:
                        continue
                    entries.append(
                        {
                            "role": f"{part}.{name}",
                            "relpath": str((directory / f["file"]).relative_to(root)),
                            "recorded_sha256": f["sha256"],
                            "shape": f["shape"],
                            "dtype": f["dtype"],
                        }
                    )
            checkpoints.append(
                {
                    "label": label,
                    "kind": kind,
                    "pair": list(pair),
                    "cell_index": core.cell_index(pair, kind),
                    "files": entries,
                }
            )
            kept[label] = {"eval": (eval_sel, eval_br), "cal": (cal_sel, cal_br)}
    data = {
        "schema": "p7b-spec-inputs-identity-manifest-v1",
        "synthetic": True,
        "label": "SYNTHETIC STAND-IN identity manifest (dry run / tests only)",
        "checkpoints": checkpoints,
        "mismatches": [],
        "missing": [],
        "totals": {"trace_files_matching": sum(len(c["files"]) for c in checkpoints)},
    }
    data["overall_hash"] = {"sha256": core.overall_hash(data)}
    path = root / "identity_manifest.json"
    write_json(path, data)
    labels = [c["label"] for c in checkpoints]
    return core.load_identity(root, path, labels), kept


def reference_record(
    kind: str,
    index: int,
    eval_selected: Tensor,
    calibration_selected: Tensor,
) -> dict[str, Any]:
    """A P7-A-format record of the configurations P7-A ran, produced by THIS study's simulator
    (a stand-in; the real reference is P7-A's own published record)."""
    counts_eval = a_core.selection_counts(eval_selected)
    layouts = a_core.build_layouts(kind, a_core.selection_counts(calibration_selected))
    nulls, null_info = core.null_streams(counts_eval, core.STREAM_A_NULL_SEEDS, index)
    queries = int(eval_selected.shape[0])
    order = a_core.query_order(a_core.STREAM_ORDER, queries)
    streams: dict[str, Any] = {"actual": {}, "order_shuffled": {}}
    streams.update({a_core.STREAMS_FM[i]: {} for i in range(3)})
    for name, positions in layouts.items():
        pos = sim.positions_tensor(_order_of(positions))
        for rows in core.RS:
            base = sim.page_sets(pos, rows, eval_selected)
            variants: list[tuple[str, sim.PageSets]] = [("actual", base)]
            if name in (core.L_ID, core.L_FREQ):
                variants.append(("order_shuffled", [base[i] for i in order]))
                variants += [
                    (a_core.STREAMS_FM[i], sim.page_sets(pos, rows, nulls[i])) for i in range(3)
                ]
            for stream, queries_list in variants:
                group = sim.simulate_group(queries_list, core.CS, (), f"{stream}|{name}|R{rows}")
                streams[stream][f"{name}|R{rows}"] = {
                    "stats": group["stats"],
                    "by_c": {c: v["asc"] for c, v in group["by_c"].items()},
                }
    return {
        "complete": True,
        "kind": kind,
        "streams": streams,
        "frequency_matched": {
            a_core.STREAMS_FM[i]: {
                "stream_sha256": null_info[i]["stream_sha256"],
                "generator_seed": null_info[i]["generator_seed"],
            }
            for i in range(3)
        },
        "label": "SYNTHETIC STAND-IN for P7-A's record (this study's own simulator)",
    }


def _order_of(positions: list[int]) -> list[int]:
    order = [0] * core.SLOTS
    for slot, position in enumerate(positions):
        order[position] = slot
    return order


def write_references(root: Path, identity: core.Identity, kept: dict[str, dict[str, Any]]) -> Path:
    """P7-A-style reference records for every synthetic checkpoint (``root/p7a-reference``)."""
    directory = root / "p7a-reference"
    directory.mkdir(parents=True, exist_ok=True)
    for label, traces in kept.items():
        pair, kind = core.parse_label(label)
        record = reference_record(
            kind, core.cell_index(pair, kind), traces["eval"][0], traces["cal"][0]
        )
        write_json(directory / f"{label}.result.json", {"outcome": "completed", "record": record})
    return directory
