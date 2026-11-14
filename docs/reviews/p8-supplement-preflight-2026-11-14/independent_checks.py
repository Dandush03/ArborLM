"""Auditor's independent reproduction of the ADR-0016 preflight claims.

Usage (from the repository root):

    uv run --locked python docs/reviews/p8-supplement-preflight-2026-11-14/independent_checks.py \
        <experiments root> <scratch dir> [all|four] [allow-supplement-key]

Does NOT reuse ``supplements.p8s.frozen`` / ``preflight`` / ``analysis`` comparison code and does not
import any ``arborlm.*_analysis`` module. It imports ``supplements.p8s.sim.build_record`` and
``supplements.p8s.null`` only as the objects under test. It never simulates the five collapsed
cells' panel traces: for those it reads only the calibration trace (layout build) and counts.

Checks:
  A. blobs: every file under src/arborlm at 378aeac + the 13 extra frozen files, by
     ``git hash-object`` versus ``git rev-parse <commit>:<path>``; 60 eval.json + 55 sim.json
     versus b8302c2; ADR-0015 versus 2d10338.
  B. layouts of the five cells rebuilt (frozen builders, calibration only) versus the bytes in the
     failed directory.
  C. replay: the supplement wrapper (default provider: precondition evaluated, false) and the
     frozen ``p8_sim.simulate_cell`` on registered cells, each compared type-strictly with the
     registered sim.json, excluding exactly the W6 list.
  D. the identity-null stream hash recomputed with ``struct`` directly.
"""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from arborlm import p7b_layout as layout_mod  # noqa: E402
from arborlm import p8_core as core  # noqa: E402
from arborlm import p8_sim  # noqa: E402
from arborlm.p7a_trace import configure_deterministic_cpu  # noqa: E402

FREEZE = "378aeac"
RESULTS = "b8302c2"
EVAL = "P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f"
SIM = "P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3"
FIVE = (
    "b101-o301-s601-C04",
    "b101-o301-s601-C05",
    "b101-o301-s602-C04",
    "b101-o301-s602-C05",
    "b102-o302-s601-C05",
)
EXTRA = (
    "configs/p8_locality_training.toml",
    "uv.lock",
    "pyproject.toml",
    "tests/conftest.py",
    "tests/p8_dry.py",
    "tests/p8_fake.py",
    "tests/test_p8_analysis.py",
    "tests/test_p8_core.py",
    "tests/test_p8_eval.py",
    "tests/test_p8_objective.py",
    "tests/test_p8_panel.py",
    "tests/test_p8_sim.py",
    "tests/test_p8_train.py",
)
W6_TOP = {
    "seconds",
    "worker_seconds",
    "peak_rss_bytes_ru_maxrss",
    "source_sha256",
    "spec_sha256",
    "reproduction_record_sha256",
    "frozen_inputs",
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, check=True, text=True
    ).stdout.strip()


def blob_of(spec: str) -> str | None:
    done = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--verify", "--quiet", spec],
        capture_output=True,
        text=True,
    )
    return done.stdout.strip() or None


def hash_object(path: Path) -> str:
    return git("hash-object", "--no-filters", str(path))


def check_blobs(experiments: Path) -> dict[str, Any]:
    src = [p for p in git("ls-tree", "-r", "--name-only", FREEZE, "--", "src/arborlm").splitlines()]
    work_src = sorted(
        p.relative_to(ROOT).as_posix()
        for p in (ROOT / "src/arborlm").rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    )
    bad = []
    for path in [*src, *EXTRA]:
        if blob_of(f"{FREEZE}:{path}") != hash_object(ROOT / path):
            bad.append(path)
    eval_ok = sim_ok = 0
    bad_results = []
    for label in core.all_labels():
        for run, name, stage in ((EVAL, "eval.json", "evaluate"), (SIM, "sim.json", "simulate")):
            local = experiments / run / "cells" / label / name
            spec = f"{RESULTS}:results/p8-2026-11-14/{stage}/{run}/cells/{label}/{name}"
            ref = blob_of(spec)
            if not local.exists():
                if not (name == "sim.json" and label in FIVE and ref is None):
                    bad_results.append(f"{label} {name} missing")
                continue
            if ref == hash_object(local):
                if name == "eval.json":
                    eval_ok += 1
                else:
                    sim_ok += 1
            else:
                bad_results.append(f"{label} {name} differs")
    adr = "docs/decisions/ADR-0015-p8-locality-aware-memory-training.md"
    return {
        "src_files_at_freeze": len(src),
        "extra_files": len(EXTRA),
        "files_compared": len(src) + len(EXTRA),
        "files_differing": bad,
        "working_src_not_in_freeze": sorted(set(work_src) - set(src)),
        "eval_json_equal": eval_ok,
        "sim_json_equal": sim_ok,
        "results_problems": bad_results,
        "adr0015_working_blob": hash_object(ROOT / adr),
        "adr0015_blob_at_2d10338": blob_of(f"2d10338:{adr}"),
        "freeze_tree": git("rev-parse", f"{FREEZE}^{{tree}}"),
        "results_tree": git("rev-parse", f"{RESULTS}^{{tree}}"),
        "source_digest": core.source_digest(),
    }


def build_layout_bytes(cell_dir: Path, label: str, target: Path) -> bytes:
    cell = core.parse_label(label)
    record = json.loads((cell_dir / "eval.json").read_text())
    selected, branches = p8_sim.load_trace(cell_dir, record, "calibration")
    cal = layout_mod.CalibrationTrace.declared(selected, branches, cell.variant, label)
    orders, _ = p8_sim.build_p8_layouts(cal)
    layout_mod.write_layout_file(
        target,
        [
            layout_mod.BuiltLayout(
                k.partition("|R")[0], int(k.partition("|R")[2]) if "|R" in k else None, o
            )
            for k, o in orders.items()
        ],
    )
    return target.read_bytes()


def check_layouts(experiments: Path, scratch: Path) -> dict[str, Any]:
    out = {}
    for label in FIVE:
        target = scratch / "layouts" / label / "layouts.int16.bin"
        target.parent.mkdir(parents=True, exist_ok=True)
        mine = build_layout_bytes(experiments / EVAL / "cells" / label, label, target)
        theirs = (experiments / SIM / "cells" / label / "layouts.int16.bin").read_bytes()
        out[label] = {
            "equal": mine == theirs,
            "bytes": len(mine),
            "sha256": hashlib.sha256(mine).hexdigest(),
        }
    return out


def strict_diff(a: Any, b: Any, path: str = "") -> list[str]:
    if type(a) is not type(b):
        return [f"{path}: type {type(a).__name__} vs {type(b).__name__}"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: only in second")
            elif k not in b:
                out.append(f"{path}.{k}: only in first")
            else:
                out += strict_diff(a[k], b[k], f"{path}.{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}: list length {len(a)} vs {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            out += strict_diff(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [f"{path}: {a!r} vs {b!r}"]


def strip_w6(record: dict[str, Any], registered: dict[str, Any]) -> tuple[dict[str, Any], list]:
    rec = json.loads(json.dumps(record))
    removed = []
    for k in list(rec):
        if k in W6_TOP or k.startswith("supplement_"):
            removed.append(k)
            del rec[k]
        elif k == "supplement" and len(sys.argv) > 4 and sys.argv[4] == "allow-supplement-key":
            # run 1 found this key outside the literal W6 pattern "supplement_*"; run 2 onward
            # excludes it explicitly and reports it under a separate name.
            removed.append("supplement (NOT literally supplement_*)")
            del rec[k]
    for panel, p in rec.get("panels", {}).items():
        reg_entries = registered["panels"][panel]["null_streams"]
        for entry, reg in zip(p["null_streams"], reg_entries, strict=True):
            for key in ("method", "precondition"):
                if key in entry and key not in reg:
                    removed.append(f"panels.{panel}.null_streams[].{key}={entry[key]!r}")
                    del entry[key]
    return rec, removed


def check_replay(experiments: Path, scratch: Path, labels: list[str]) -> dict[str, Any]:
    from supplements.p8s import sim as supplement_sim

    out = {}
    for label in labels:
        cell = core.parse_label(label)
        cell_dir = experiments / EVAL / "cells" / label
        registered = json.loads((experiments / SIM / "cells" / label / "sim.json").read_text())
        reg = {k: v for k, v in registered.items() if k not in W6_TOP}
        d1 = scratch / "replay_supplement" / label
        d1.mkdir(parents=True, exist_ok=True)
        mine = supplement_sim.build_record(cell, cell_dir, d1, freeze=None, deadline=None)
        mine_s, removed = strip_w6(mine, registered)
        entry: dict[str, Any] = {
            "supplement_wrapper_diffs": strict_diff(reg, mine_s)[:20],
            "removed_from_supplement_record": sorted(set(removed)),
            "supplement_layout_file_equal": hashlib.sha256(
                (d1 / "layouts.int16.bin").read_bytes()
            ).hexdigest()
            == registered["layouts"]["file_sha256"],
            "preconditions": {
                p: v["holds"] for p, v in mine["supplement_null_preconditions"].items()
            },
            "unique_selected_slots": mine["layouts"]["meta"]["unique_selected_slots"],
            "variant": cell.variant,
        }
        if label in ("b102-o302-s601-C04", "b102-o302-s602-C05"):
            d2 = scratch / "replay_frozen" / label
            d2.mkdir(parents=True, exist_ok=True)
            frozen = p8_sim.simulate_cell(cell, cell_dir, d2)
            fz = {k: v for k, v in json.loads(json.dumps(frozen)).items() if k not in W6_TOP}
            entry["frozen_simulate_cell_diffs_vs_registered"] = strict_diff(
                {k: v for k, v in reg.items() if k in fz}, fz
            )[:20]
            entry["frozen_keys_missing_vs_registered"] = sorted(set(reg) - set(fz))
        out[label] = entry
    return out


def check_identity_hash() -> dict[str, Any]:
    from supplements.p8s import null

    s = (3, 17, 200, 999, 1000, 2048, 4000, 4095)
    q = 32768
    stream = null.identity_stream(s, q)
    expected = hashlib.sha256(struct.pack(f"<{8 * q}h", *(list(s) * q))).hexdigest()
    return {"equal": null.stream_sha256(stream) == expected, "expected": expected}


def main() -> None:
    configure_deterministic_cpu()
    experiments, scratch = Path(sys.argv[1]), Path(sys.argv[2])
    replay_all = len(sys.argv) > 3 and sys.argv[3] == "all"
    labels = (
        [x for x in core.all_labels() if x not in FIVE]
        if replay_all
        else [
            "b102-o302-s601-C04",
            "b102-o302-s602-C05",
            "b103-o303-s601-C01",
            "b101-o301-s601-C07",
        ]
    )
    result = {
        "blobs": check_blobs(experiments),
        "layouts_five": check_layouts(experiments, scratch),
        "identity_hash": check_identity_hash(),
        "replay": check_replay(experiments, scratch, labels),
    }
    bad_replay = [
        k
        for k, v in result["replay"].items()
        if v["supplement_wrapper_diffs"]
        or not v["supplement_layout_file_equal"]
        or any(v["preconditions"].values())
        or v.get("frozen_simulate_cell_diffs_vs_registered")
    ]
    result["summary"] = {
        "files_compared": result["blobs"]["files_compared"],
        "files_differing": len(result["blobs"]["files_differing"]),
        "eval_json_equal": result["blobs"]["eval_json_equal"],
        "sim_json_equal": result["blobs"]["sim_json_equal"],
        "layouts_five_equal": sum(v["equal"] for v in result["layouts_five"].values()),
        "replayed": len(result["replay"]),
        "replay_failures": bad_replay,
        "identity_hash_equal": result["identity_hash"]["equal"],
    }
    print(json.dumps(result, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
