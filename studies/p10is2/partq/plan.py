# ruff: noqa: E501
"""The Part Q candidate plan (ADR-0025 sections 4.3 rule 9, 10, 11 item 5): ``freeze/partq_plan.json`` lists every block, item, label, path and manifest of the registered stages, and the frozen batch layout.

Stages: inputs, partition, qfit, qcheck, generation, regeneration, outputs. Every stage derives its items from this file only. The layout (batch size 32, the order of sources within a block, the order of blocks)
is in it and every teacher run uses it. The per-teacher items name the teacher, the stream, the block indices (Q_check: the reserve's blocks 0..15 in the seeded order; generation: blocks until met, up to the
split pool's end) and the paths of their records.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, write_json

from ..common import core
from ..common import plan as planmod
from ..common.core import StageRefused

STAGES = ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration", "outputs")
REHEARSAL_STAGES = STAGES
PANELS_OUT = ("E_A", "E_B", "E_C", "E_open", "D_cal", "D_con")
FILTER_GRID = "24 settings: tau in {-0.05..-0.60 step 0.05} x length ratio in {[0.5, 2.0], [0.6, 1.6]}"


def layout(cfg: Mapping[str, Any]) -> dict[str, Any]:
    g = cfg["generation"]
    return {
        "batch_size": int(g["batch_size"]), "threads": int(g["threads"]), "deterministic_algorithms": True, "order_of_sources_within_a_block": "the stored order of the block's source list (frozen in the block record)",
        "order_of_blocks": "Q_check: the reserve's seeded order (seed 250903), never skipped or reordered, also across a pause; generation: a seeded order of each capability's own sources (seed 250905), consecutive blocks of generation_block_sources",
        "q_check_block": int(cfg["panels"]["q_check_block"]), "generation_block_sources": int(g["generation_block_sources"]), "digest": {"batches": int(g["digest_batches"]), "seed": 250908, "stream": "Q_fit, the same draw indices for both teachers"},
        "regeneration": {"batches": int(g["regeneration_batches"]), "seed": 250914, "stream": "generation, a fresh generator per teacher"},
    }  # fmt: skip


def registered_items(cfg: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """The items of the registered stages, from the config only."""
    p, g = cfg["panels"], cfg["generation"]
    n_qfit_batches = -(-int(p["q_fit"]) // int(g["batch_size"]))
    items: dict[str, list[dict[str, Any]]] = {
        "inputs": [{"id": "inputs", "stage": "inputs", "what": "hash checks of every input, the applied generation configuration of each teacher against its pinned file, student conversion and equivalence record (G8), tokenizer record, the WikiText-2 path and pins"}],
        "partition": [{"id": "partition", "stage": "partition", "what": "fixed-input counts (step 2), the partition with seed 250901, the pools with the source split (4/5 to B), exact pool sizes", "seeds": [250901, 250902, 250903, 250904]}],
        "qfit": [], "qcheck": [], "generation": [], "regeneration": [], "outputs": [],
    }  # fmt: skip
    for c in core.TASKS:
        items["qfit"].append({"id": f"qfit-{c}", "stage": "qfit", "teacher": c, "sources": int(p["q_fit"]), "batches": n_qfit_batches, "path": f"qfit/teacher_{c}", "never_extended": True, "grid": FILTER_GRID})
        items["qcheck"].append({"id": f"qcheck-{c}", "stage": "qcheck", "teacher": c, "blocks": list(range(int(p["q_check_blocks_max"]))), "block_items": int(p["q_check_block"]), "target_accepted": int(cfg["quality"]["q4_min_accepted"]), "path": f"qcheck/teacher_{c}", "stopping_rules": 3, "runs_after_failed_q1_q2": True})
        items["generation"].append({"id": f"generation-{c}", "stage": "generation", "teacher": c, "block_sources": int(g["generation_block_sources"]), "target_accepted": int(g["accepted_disjoint"]), "minimum_accepted": int(g["accepted_min"]), "path": f"generation/teacher_{c}", "runs_only_if_both_teachers_pass_q1_q4": True})
        items["regeneration"].append({"id": f"regeneration-{c}", "stage": "regeneration", "teacher": c, "batches": int(g["regeneration_batches"]), "seed": 250914, "tolerance_tokens": 0, "tolerance_scores": float(cfg["scoring"]["regeneration_score_tolerance"])})
        for name in PANELS_OUT:
            items["outputs"].append({"id": f"outputs-{c}-{name}", "stage": "outputs", "teacher": c, "panel": name, "path": f"outputs/teacher_{c}/{name}", "scored": False})
    ids = [i["id"] for v in items.values() for i in v]
    if len(set(ids)) != len(ids):
        raise ValueError("a plan names an item twice")
    return items


def build_candidate(repo: Path, run_dir: Path, cfg: Mapping[str, Any], *, inputs: Mapping[str, Any], mode: str = planmod.REGISTERED, walk: Mapping[str, Any] | None = None, ledger_path: str | None = None) -> dict[str, Any]:
    """The plan record. ``inputs`` names every input file with its path and SHA-256 (the downloads, WikiText-2, the package manifest); the panel ledger as it stands at the freeze is hashed into ``manifests``."""
    manifests: dict[str, Any] = {}
    led = ledger_path or cfg["paths"]["panel_ledger"]
    lp = repo / planmod_freeze_dir() / Path(led).name
    if lp.is_file():
        manifests["panel_ledger"] = {"path": str(lp.relative_to(repo)), "sha256": file_sha256(lp)}
    return planmod.build_plan(
        part="Q", mode=mode, cfg=cfg, repo=repo, items=registered_items(cfg), run_dir=run_dir, walk=walk,
        extra={"layout": layout(cfg), "inputs": dict(inputs), "manifests": manifests, "panel_ledger_path": led, "seeds": {k: v for k, v in core.partq_seeds(cfg, "registered").items()}, "thresholds": {k: cfg["quality"][k] for k in cfg["quality"]}},
    )  # fmt: skip


def planmod_freeze_dir() -> Path:
    return core.FREEZE_DIR


NOT_COMPARED = ("adr", "platform")


def scientific_content(data: Mapping[str, Any]) -> dict[str, Any]:
    """The plan without the ADR's hash and the writing process's platform block: what the freeze's re-derivation compares."""
    return {k: v for k, v in data.items() if k not in NOT_COMPARED}


def write_candidate(repo: Path, record: Mapping[str, Any], *, supersede: bool = False) -> Path:
    """Writes ``freeze/partq_plan.json`` ONCE. An existing plan is replaced only with ``supersede``: the old file is moved to ``freeze/superseded/``, never deleted; a frozen plan is never superseded."""
    path = repo / core.PLAN_Q
    if path.exists():
        if not supersede:
            raise StageRefused(f"refused: {path} exists; a candidate plan is replaced only with --supersede (the old file is moved aside, never deleted)")
        if (repo / core.FREEZE_RECORD_Q).exists():
            raise StageRefused("refused: a freeze record exists; a frozen plan is not superseded")
        old = file_sha256(path)
        target = path.parent / "superseded" / f"partq_plan-{old[:12]}.json"
        if target.exists():
            raise StageRefused(f"refused: {target} exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        path.rename(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, core.jsonable(dict(record)))
    return path


from ..common.caps import (  # noqa: E402, F401  (caps by code live in common/ so that both parts share one definition)
    caps_match_config,
    caps_proposal,
    project_stage_seconds,
)
