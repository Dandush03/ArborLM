# ruff: noqa: E501
"""The world exactly as Part T's evaluate stage read it (ADR-0035 section 3): Part T's frozen configuration, Part Q's directory and the calibration plan, through ``partt_real.build_world_real``. CPU, six threads,
deterministic algorithms. Nothing is written by building it (``driver`` records the file lists and hashes of the Part T run directory and Part Q's directory before and after)."""

import hashlib
import json
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256
from studies.p10is2 import partt_real
from studies.p10is2.common import core
from studies.p10is2.common.plan import Plan

PART_T_RUN = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P10IS2-T-registered-20261121")
ITEM_RECORDS_SHA256_PREFIX, ITEM_RECORDS_SHA256_SUFFIX = "54589c9f", "af938"  # OUTCOME.md, as ADR-0035 section 3 quotes it
THREADS = 6


def configure_platform() -> None:
    torch.set_num_threads(THREADS)
    torch.use_deterministic_algorithms(True)


def world_inputs(repo: Path) -> dict[str, Any]:
    """SHA-256 of what the world is built from, recorded before use: the configuration, the plan file, the calibration plan block, Part Q's manifest, plan and the calibration record the plan names."""
    plan = Plan.load(repo / core.PLAN_T, "T")
    calib = plan.data["calibration"]
    pq = plan.data["part_q"]
    rec_path = Path(calib["record"]["path"])
    return {
        "config": {"path": str(core.CONFIG_T), "sha256": file_sha256(repo / core.CONFIG_T)},
        "plan": {"path": str(core.PLAN_T), "sha256": file_sha256(repo / core.PLAN_T)},
        "calibration_plan_block": {"sha256": hashlib.sha256(json.dumps(calib, sort_keys=True, default=str).encode()).hexdigest(), "U": calib["U"], "read_layer": calib["read_layer"], "store_rate": calib["store_rate"]},
        "calibration_record": {"path": str(rec_path), "sha256": file_sha256(rec_path), "sha256_in_plan": calib["record"]["sha256"]},
        "part_q": {"run_dir": pq["run_dir"], "manifest": {"path": pq["manifest"]["path"], "sha256": file_sha256(Path(pq["manifest"]["path"])), "sha256_in_plan": pq["manifest"]["sha256"]}, "plan": {"path": pq["plan"]["path"], "sha256": file_sha256(Path(pq["plan"]["path"])), "sha256_in_plan": pq["plan"]["sha256"]}},
        "part_t_run_dir": str(PART_T_RUN),
        "item_records": {"sha256": file_sha256(PART_T_RUN / "item_records.json")},
        "registry": {"sha256": file_sha256(PART_T_RUN / "registry.json")},
    }


def build_world(repo: Path) -> tuple[Any, dict[str, Any]]:
    """(world, cfg). The Part Q door re-hashes every Part Q file it reads against Part Q's manifest."""
    configure_platform()
    cfg = core.load_config("T", repo / core.CONFIG_T)
    plan = Plan.load(repo / core.PLAN_T, "T")
    qdir = partt_real.qdir_of(plan, Path(plan.data["part_q"]["run_dir"]))
    calib = partt_real.calibration_of(cfg, plan, "registered")
    world, _gloss, _qres = partt_real.build_world_real(repo, cfg, qdir, calib, "registered", partt_real.door_of(plan, qdir))
    world.device = torch.device("cpu")
    bad = [n for n, p in world.student.named_parameters() if p.device.type != "cpu"]
    if bad:
        raise RuntimeError(f"the student is not on CPU: {bad[:3]}")
    return world, cfg
