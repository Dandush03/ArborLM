# ruff: noqa: E501
"""The Part T candidate plan, cells, registry keys and resume policy (ADR-0025 sections 5, 8.6, 10, 11, 19).

Part T's candidate plan (``freeze/partt_plan.json``) is written AFTER calibration, because it holds U, the rates and the read layer; every stage derives its cells and items from that file only. This module
enumerates what the plan holds (cells, stages, the registry keys the analysis needs) from the config and the calibration outcome, decides how a cell may resume, and builds the plan record through the shared
``common.plan``. It trains nothing and scores nothing.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .common import core
from .common import plan as planmod
from .quantities import CELLS, GEN_POSITIONS, NONE, ORDERS, PANEL, REPLICATES, first, second

STAGES = ("gates", "train", "evaluate", "controls", "combined", "analysis", "report")
TWO_STAGE_ARMS = ("M-append", "M-seq", "M-ii", "D-append", "D-seq")
STAGE1_ARMS = ("M1", "D1")
JOINT_ARMS = ("M-joint", "D-joint")
SEPARATE_ARMS = ("M-sep", "D-sep")  # assembled from the two single-teacher modules of a replicate behind the oracle route: no training of their own
LOOKUP_ARMS = ("R-exact", "R-gloss", "R-gloss-icl", "R-nn", "R-icl")
MEMORY_TRAINED = ("M1", "M-append", "M-seq", "M-ii", "M-joint")
CONTROL_KINDS = ("own", "value", "code", "marker", "words")
# Units of U of training, as section 14 counts them (42 store-type and 24 LoRA over three replicates; M-ii is 12 of the 42): READING of the table, listed in the report.
UNITS_OF_U = {"store-type": {"M1": 1, "M-append": 1, "M-seq": 1, "M-ii": 2, "M-joint": 2, "E-table": 1}, "lora": {"D1": 1, "D-append": 1, "D-seq": 1, "D-joint": 2}}
PER_CELL_ARMS = ("M1", "M-append", "M-seq", "M-ii", "D1", "D-append", "D-seq")  # trained once per (replicate, order) cell


def train_cells() -> list[dict[str, Any]]:
    """Every trained cell: per (replicate, order) the stage-1 and stage-2 modules; per replicate the joint arms and E-table (one per capability). M-sep, D-sep and the baselines are assembled or built, not trained."""
    out: list[dict[str, Any]] = []
    for r in REPLICATES:
        for o in ORDERS:
            for arm in PER_CELL_ARMS:
                out.append({"id": f"train|{arm}|{o}|r{r}", "arm": arm, "order": o, "rep": r, "type": "store-type" if arm.startswith("M") else "lora", "stage": 1 if arm in STAGE1_ARMS else 2})
        for arm in JOINT_ARMS:
            out.append({"id": f"train|{arm}|-|r{r}", "arm": arm, "order": NONE, "rep": r, "type": "store-type" if arm.startswith("M") else "lora", "stage": 1})
        for c in core.TASKS:
            out.append({"id": f"train|E-table|{c}|r{r}", "arm": "E-table", "order": NONE, "capability": c, "rep": r, "type": "store-type", "stage": 1})
    ids = [c["id"] for c in out]
    if len(set(ids)) != len(ids):
        raise ValueError("a plan names a cell twice")
    return out


def units_of_training() -> dict[str, int]:
    """Section 14's count: units of U per module type over three replicates, and M-ii's share."""
    out = {"store-type": 0, "lora": 0, "M-ii": 0}
    for c in train_cells():
        w = UNITS_OF_U[c["type"]][c["arm"]]
        out[c["type"]] += w
        if c["arm"] == "M-ii":
            out["M-ii"] += w
    return out


def required_keys() -> set[str]:
    """Every registry key the analysis reads (``quantities`` and ``labels``): missing after the run with no error recorded is INCOMPLETE."""
    from .quantities import key

    ks: set[str] = set()
    for c in core.TASKS:
        p = PANEL[c]
        for arm in ("S0", "TEACHER"):
            ks |= {key(arm, NONE, NONE, f"s:{p}"), key(arm, NONE, NONE, f"sub:own:{p}")}
    for r, o in CELLS:
        for arm in (*STAGE1_ARMS, *TWO_STAGE_ARMS):
            for c in core.TASKS:
                ks.add(key(arm, o, r, f"s:{PANEL[c]}"))
        for arm in ("M1", "M-append", "M-seq", "M-ii"):
            cap = first(o) if arm == "M1" else second(o)
            ks |= {key(arm, o, r, f"sub:{k}:{PANEL[cap]}") for k in CONTROL_KINDS}
        for arm in ("M1", "M-append", "M-seq", "M-ii", "D-seq"):
            ks |= {key(arm, o, r, f"gen:{pos}") for pos in GEN_POSITIONS}
        for c in core.TASKS:
            ks |= {key("M-ii", o, r, f"dcon:{c}"), key("M-append", o, r, f"dcon:{c}")}
        ks.add(key("M-ii", o, r, "modification"))
    for r in REPLICATES:
        for arm in (*JOINT_ARMS, *SEPARATE_ARMS, "E-table", "R-gloss", "R-gloss-icl", "R-nn", "R-icl"):
            for c in core.TASKS:
                ks.add(key(arm, NONE, r, f"s:{PANEL[c]}"))
        for c in core.TASKS:
            ks |= {key("M-joint", NONE, r, f"sub:{k}:{PANEL[c]}") for k in CONTROL_KINDS}
    return ks


def stage_items(ctx: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """The items of every registered stage. ``ctx`` is the calibration outcome: ``U``, ``store_rate``, ``lora_rate``, ``etable_rate``, ``read_layer``."""
    cells = train_cells()
    items: dict[str, list[dict[str, Any]]] = {s: [] for s in STAGES}
    items["gates"] = [{"id": f"gate-{g}", "stage": "gates", "gate": g} for g in ("G1", "G2", "G4", "G5", "G6", "G7", "G8", "G9")]
    for c in cells:
        rate = ctx["store_rate"] if c["type"] == "store-type" and c["arm"] != "E-table" else (ctx["lora_rate"] if c["type"] == "lora" else ctx["etable_rate"])
        items["train"].append({**c, "stage_name": "train", "updates": int(ctx["U"]) * (2 if c["arm"] in JOINT_ARMS else 1), "rate": rate, "read_layer": ctx["read_layer"] if c["type"] == "store-type" else None, "device": "mps", "checkpoint_every": 500})
        items["evaluate"].append({"id": f"evaluate|{c['id']}", "stage": "evaluate", "of": c["id"], "scoring_device": "cpu", "panels": ["E_A", "E_B"], "reads": ["s", "gen", "dcon"]})
        if c["arm"] in MEMORY_TRAINED:
            items["controls"].append({"id": f"controls|{c['id']}", "stage": "controls", "of": c["id"], "subsample": 300, "conditions": list(CONTROL_KINDS)})
    for r in REPLICATES:
        for arm in (*SEPARATE_ARMS, *LOOKUP_ARMS):
            items["evaluate"].append({"id": f"evaluate|{arm}|-|r{r}", "stage": "evaluate", "of": arm, "rep": r, "built_not_trained": True})
        for o in ORDERS:
            for arm in ("M-append", "M-ii", "D-seq", "D-append"):
                items["combined"].append({"id": f"combined|{arm}|{o}|r{r}", "stage": "combined", "arm": arm, "order": o, "rep": r})
        for arm in (*JOINT_ARMS, *SEPARATE_ARMS):
            items["combined"].append({"id": f"combined|{arm}|-|r{r}", "stage": "combined", "arm": arm, "rep": r})
    items["combined"] += [{"id": "combined|S0", "stage": "combined", "arm": "S0"}, {"id": "combined|ensemble", "stage": "combined", "arm": "ensemble"}]
    items["analysis"] = [{"id": "analysis", "stage": "analysis"}]
    items["report"] = [{"id": "report", "stage": "report"}]
    ids = [i["id"] for v in items.values() for i in v]
    if len(set(ids)) != len(ids):
        raise ValueError("a plan names an item twice")
    return items


def combined_arm_cells_per_replicate() -> int:
    """Twelve: the four stage-2 arms in both orders plus the four orderless ones (section 5.5)."""
    return 4 * len(ORDERS) + len(JOINT_ARMS) + len(SEPARATE_ARMS)


def build_candidate(repo: Path, run_dir: Path, cfg: Mapping[str, Any], calibration: Mapping[str, Any], *, mode: str = planmod.REGISTERED, walk: Mapping[str, Any] | None = None, manifests: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The plan record. ``calibration`` holds U (and NOT CONVERGED AT U), the rates, the layer, the calibration records' hashes (refused if stand-in or if their code hashes differ from the frozen files) and the pilot
    outcome. ``manifests`` names the Part Q manifest, the shared panel ledger and the calibration records by path and SHA-256."""
    if calibration.get("pilot", {}).get("passed") is not True:
        raise core.StageRefused("refused: the pilot gate did not pass (NOT STARTED: PILOT): Part T has no plan")
    return planmod.build_plan(
        part="T", mode=mode, cfg=cfg, repo=repo, items=stage_items(calibration), run_dir=run_dir, walk=walk,
        extra={"calibration": dict(calibration), "manifests": dict(manifests or {}), "registry_keys": sorted(required_keys()), "units_of_U": units_of_training(), "seeds": {"replicates": [core.partt_replicate_values(cfg, "registered", r) for r in range(3)]}},
    )  # fmt: skip


# --- resume policy (sections 8.6, 11 item 4; rulings L4, G20) --------------------------------------------------------------------------------------
def resume_decision(record: Mapping[str, Any]) -> dict[str, Any]:
    """What a runner does with a cell record on a new invocation.

    COMPLETE: skip. STOPPED ON A NON-FINITE VALUE: refuse (ENGINEERING STOP — NON-FINITE VALUE; the last finite checkpoint is recorded; MPS training is not bit-reproducible, so resuming until a divergence does
    not recur would be a re-draw chosen on an observed outcome; a second attempt is the human lead's decision). A code or environment error: resume from the last checkpoint once the cause is recorded and the
    fix changes no frozen file; a fix that changes a frozen file ends the attempt (second attempt: the human lead's decision). Otherwise run."""
    status = record.get("status")
    if status == "COMPLETE":
        return {"action": "skip", "delete_checkpoints": True}
    if status == "STOPPED_NONFINITE":
        return {"action": "refuse", "label": "ENGINEERING STOP — NON-FINITE VALUE", "last_finite_checkpoint": record.get("last_finite_checkpoint"), "note": "not resumed; a second attempt is the human lead's decision"}
    if status == "ERROR":
        if not record.get("cause_recorded"):
            return {"action": "refuse", "label": "ENGINEERING STOP", "note": "the cause must be recorded before a resume"}
        if record.get("fix_changes_frozen_file"):
            return {"action": "refuse", "label": "ENGINEERING STOP", "note": "a fix that changes a frozen file ends the attempt; a second attempt is the human lead's decision"}
        return {"action": "resume", "from": record.get("last_checkpoint"), "marked_resumed": True}
    return {"action": "run"}


def checkpoints_to_delete(records: Sequence[Mapping[str, Any]]) -> list[str]:
    """Resume checkpoints of a cell are deleted once its final snapshot is recorded (ruling G20); the durable copy of the data is not counted against the 10 GiB."""
    return [str(r["checkpoint_dir"]) for r in records if r.get("status") == "COMPLETE" and r.get("final_snapshot") and r.get("checkpoint_dir")]


__all__ = ["STAGES", "build_candidate", "checkpoints_to_delete", "required_keys", "resume_decision", "stage_items", "train_cells", "units_of_training"]
