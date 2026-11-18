# ruff: noqa: E501
"""P10IS5 freeze commands (ADR-0028 section 12; the pattern of ADR-0029 section 13): ``config-proposal`` (prints m_t and the quiet figures from R1's and M's records for the lead to write into the config), ``caps-proposal``,
``candidate-plan`` (writes ``freeze/plan.json`` first; refuses to overwrite without ``--supersede``, which moves the old file aside), ``freeze`` (writes ``freeze/freeze_record.json`` only if the committed plan has the SHA-256 in K's record),
``seed-gate``.

``candidate-plan`` refuses while the figures or the caps are provisional (m_t, the quiet figures and the caps are fixed BEFORE the candidate plan exists) and refuses unless the config's figures equal the ones R1's and M's records
give. ``freeze`` re-derives the plan's scientific content from the current code and config and refuses any difference, refuses a rehearsal made on provisional caps, requires K's candidate section to name this exact plan file,
and does not compare the ADR's hash. It writes only the freeze record; the freeze commit is the lead's act.
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any

from arborlm.io import file_sha256, read_json, write_json

from . import core, gates
from . import plan as planmod
from .core import StageRefused

REHEARSAL_STAGES = ("prediction", "harness_figure", "blocks", "analysis", "report", "registered_enumeration")
FIGURE_KEYS = ("load_p95", "read_bytes_per_s_p95", "write_bytes_per_s_p95", "read_ops_per_s_p95", "write_ops_per_s_p95")


def add_commands(sub: Any) -> None:
    cp = sub.add_parser("candidate-plan", help="write the candidate freeze/plan.json once (K runs against it)")
    cp.add_argument("--run-dir", required=True)
    cp.add_argument("--data-dir", required=True, help="the .noindex directory of the files, outside every worktree")
    cp.add_argument("--r1-record", required=True)
    cp.add_argument("--m-record", required=True)
    cp.add_argument("--supersede", action="store_true", help="replace an existing candidate plan: the old file is moved to freeze/superseded/plan-<sha12>.json, never deleted")
    cp.add_argument("--repo")
    f = sub.add_parser("freeze", help="write freeze/freeze_record.json for the committed candidate plan")
    f.add_argument("--rehearsal", required=True, help="K's rehearsal record, whose candidate section names the plan file's SHA-256")
    f.add_argument("--repo")
    c = sub.add_parser("caps-proposal", help="print the cap section 8 proposes: charged + 2 x projected remaining")
    c.add_argument("--charged-hours", type=float, required=True)
    c.add_argument("--projected-remaining-hours", type=float, required=True)
    p = sub.add_parser("config-proposal", help="print m_t and the quiet figures to write into the config, from R1's and M's records")
    p.add_argument("--r1-record", required=True)
    p.add_argument("--m-record", required=True)
    sub.add_parser("seed-gate", help="run the seed gate and print its result")


def figures_from_records(r1_record: dict[str, Any], m_record: dict[str, Any]) -> dict[str, Any]:
    """The figures the config's ``[fixed_after_r1_and_m]`` must hold: R1's idle 95th percentiles and M's margin."""
    fig = r1_record.get("idle_figures")
    margin = (m_record.get("summary") or {}).get("margin")
    if not r1_record.get("passed") or not fig:
        raise StageRefused("refused: R1's record is not a passed R1 with idle figures")
    if margin is None:
        raise StageRefused("refused: M's record has no margin (CV_R could not be computed)")
    return {**{k: float(fig[k]) for k in FIGURE_KEYS}, "m_t": float(margin["m_t"]), "timing_spread": bool(margin["timing_spread"])}


def figures_problems(cfg: Any, derived: dict[str, Any]) -> list[str]:
    f = cfg["fixed_after_r1_and_m"]
    out = []
    for k in (*FIGURE_KEYS, "m_t"):
        a, b = float(f[k]), float(derived[k])
        if not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12):
            out.append(f"{k}: the config has {a!r}, the records give {b!r}")
    if bool(f["timing_spread"]) != bool(derived["timing_spread"]):
        out.append(f"timing_spread: the config has {f['timing_spread']!r}, the records give {derived['timing_spread']!r}")
    return out


def dispatch(args: argparse.Namespace) -> int:
    if args.command == "candidate-plan":
        return cmd_candidate_plan(args)
    if args.command == "freeze":
        return cmd_freeze(args)
    if args.command == "caps-proposal":
        print(json.dumps({"proposed_cap_hours": core.propose_cap_hours(args.charged_hours, args.projected_remaining_hours), "rule": "section 8: charged + 2 x projected remaining; the lead sets it in the config and clears caps.provisional"}))
        return 0
    if args.command == "config-proposal":
        d = figures_from_records(core.read_record(Path(args.r1_record), "r1"), core.read_record(Path(args.m_record), "rehearsal"))
        print("[fixed_after_r1_and_m]\nprovisional = false")
        for k, v in d.items():
            print(f"{k} = {json.dumps(v)}")
        return 0
    if args.command == "seed-gate":
        res = gates.seed_gate()
        print(json.dumps(res, indent=1, default=str))
        return 0 if res["passed"] else 1
    raise ValueError(args.command)


def cmd_candidate_plan(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.repo_root()
    cfg = core.load_config(repo / core.CONFIG)
    if core.provisional_figures(cfg):
        raise StageRefused("refused: [fixed_after_r1_and_m] is provisional: m_t and the quiet figures come from R1's and M's records and are written into the config before the candidate plan exists")
    if core.caps_provisional(cfg):
        raise StageRefused("refused: the caps are provisional: the lead sets them after M (charged + 2 x projected remaining) before the candidate plan, so that K runs on them")
    r1_path, m_path = Path(args.r1_record), Path(args.m_record)
    r1_rec, m_rec = core.read_record(r1_path, "r1"), core.read_record(m_path, "rehearsal")
    problems = figures_problems(cfg, figures_from_records(r1_rec, m_rec))
    if problems:
        raise StageRefused("refused: the config's fixed figures differ from R1's and M's records: " + "; ".join(problems))
    data_dir = Path(args.data_dir)
    planmod.require_data_dir_outside(repo, data_dir, str(cfg["device"]["directory_suffix"]))
    plan_path = repo / core.PLAN
    if plan_path.exists():
        if not args.supersede:
            raise StageRefused(f"refused: {plan_path} exists; a candidate plan is replaced only with --supersede (the old file is moved aside, never deleted)")
        if (repo / planmod.FREEZE_RECORD).exists():
            raise StageRefused("refused: a freeze record exists; a frozen plan is not superseded")
        old = file_sha256(plan_path)
        target = plan_path.parent / "superseded" / f"plan-{old[:12]}.json"
        if target.exists():
            raise StageRefused(f"refused: {target} exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        plan_path.rename(target)
        print(json.dumps({"superseded": str(target), "sha256": old}))
    record = planmod.build_plan(cfg, repo, data_dir, Path(args.run_dir), {"r1": r1_path, "m": m_path})
    core.write_record(plan_path, record)
    print(json.dumps({"candidate_plan": str(plan_path), "plan_file_sha256": file_sha256(plan_path), "caps_provisional": record["caps_provisional"]}))
    return 0


def cmd_freeze(args: argparse.Namespace) -> int:
    repo = Path(args.repo) if args.repo else core.repo_root()
    cfg = core.load_config(repo / core.CONFIG)
    plan_path, record_path = repo / core.PLAN, repo / planmod.FREEZE_RECORD
    if record_path.exists():
        raise StageRefused(f"refused: {record_path} exists; a freeze is written once")
    if not plan_path.is_file():
        raise StageRefused("refused: no candidate plan: write it first (candidate-plan), rehearse against it (K), then freeze")
    plan = planmod.Plan.load(plan_path)
    if core.caps_provisional(cfg) or plan.data.get("caps_provisional") or core.provisional_figures(cfg) or plan.data.get("figures_provisional"):
        raise StageRefused("refused: the caps or the fixed figures are provisional")
    plan_sha = file_sha256(plan_path)
    data_dir = Path(plan.content["paths"]["data_dir"])
    records = {name: Path(ref["path"]) for name, ref in plan.data["records"].items()}
    rederived = planmod.build_plan(cfg, repo, data_dir, Path(plan.data["run_dir"]), records)
    if planmod.scientific_content(json.loads(json.dumps(rederived))) != planmod.scientific_content(plan.data):
        raise StageRefused("refused: the candidate plan differs from a re-derivation from the current code and config (the code or the config changed after the plan was written): supersede it and rehearse again")
    rehearsal_path = Path(args.rehearsal)
    k = core.read_record(rehearsal_path, "rehearsal")
    if k.get("caps_provisional") is not False or k.get("figures_provisional") is not False:
        raise StageRefused("refused: the rehearsal record was made on provisional caps or figures (or does not say): the counting rehearsal runs against the plan with the caps set")
    cand = k.get("candidate") or {}
    stages_ok = all(((k.get("stages") or {}).get(s) or {}).get("status") == "COMPLETE" for s in REHEARSAL_STAGES)
    if k.get("stage") != "K" or cand.get("status") != "COMPLETE" or cand.get("plan_file_sha256") != plan_sha or not stages_ok:
        raise StageRefused(f"refused: the rehearsal record does not show K complete on every stage against the candidate plan of SHA-256 {plan_sha}")
    seed = gates.seed_gate(cfg, root=repo)
    if not seed["passed"]:
        raise StageRefused(f"refused: the seed gate did not pass: {seed['problems']}")
    rec = {
        **core.envelope("freeze_record"), "plan_file_sha256": plan_sha, "rehearsal": {"path": str(rehearsal_path.resolve()), "sha256": file_sha256(rehearsal_path)}, "seed_gate": {k_: seed[k_] for k_ in ("passed", "roles", "checker")},
        "note": "the ADR's hash is provenance only and is not compared; the freeze commit is the lead's act",
    }  # fmt: skip
    record_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(record_path, rec)
    print(json.dumps({"freeze_record": str(record_path), "sha256": file_sha256(record_path), "plan_file_sha256": plan_sha}))
    return 0


def read_plan(path: Path) -> dict[str, Any]:
    return read_json(path)
