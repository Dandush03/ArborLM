"""Writes the run-plan fragment for evaluation R1 (units R1a, R1b, R1c) of the M0 fresh run, stage 1S.

Standard library only. Deterministic: the same arguments give the same bytes.
Usage (worktree root):
    PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python studies/m0/fresh_run/r1/make_run_plan_r1.py <dry_attempt_dir> <out.json>

Every seed integer is recomputed by the formula of stage 1S point 4 and asserted equal to part A of
addendum1_rev6_fresh_run.out.txt. Nothing here chooses a seed, a count or a path at run time.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

WORKTREE = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f")
SPEC_WORKTREE = Path(
    "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1"
)
SEED_FILE = (
    SPEC_WORKTREE
    / "docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev6_fresh_run.out.txt"
)
SURVIVORS = WORKTREE / "studies/m0/manifests/survivor_list_of_record.json"
RUN_ROOT = WORKTREE / "experiments/m0_fresh_run_20261126"
SCRIPT_COMMIT = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
FINAL_R1 = "docs/reviews/m0-lineage-decision-2026-11-25/final_r1"
BASES = {
    "seed1": "16103270370041696293",
    "seed2": "10773834973117025986",
    "seed3": "619660634241804713",
    "dry": "3342082268851962967",
}
N_RUN = 3000
N_DRY = 20
ROLES = {
    "R1a": [
        "aud_seed",
        "aud_fit",
        "impl_seed",
        "impl_fit",
        "feat1_fit",
        "feat1_test",
        "feat2_fit",
        "feat2_test",
    ],
    "R1b": ["aud_seed", "aud_fit", "impl_seed", "impl_fit", "feat_fit", "feat_test"],
    "R1c": ["fit", "test"],
}
FEAT_LINEAGES = [
    "R1.boolean_lights_r4",
    "R1.categories_default_exceptions_r4",
    "R1.conditional_threshold_rule_r4",
    "R1.knights_knaves_r6",
]
SPEC_KEPT = [  # keys of SPEC of the R1c copy that are on the survivor list (the copy removes R1.conditional_decision_tree_r6)
    "R1.boolean_lights_r4",
    "R1.categories_default_exceptions_r4",
    "R1.compass_turns",
    "R1.knights_knaves_r6",
    "R1.temporal_weekday_shift_r6",
]
COMMON_ENV = {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}
UV = ["uv", "run", "--locked", "python"]


def seed_int(base: str, unit: str, role: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{base}|{unit}|{role}".encode()).digest()[:8], "big")


def parse_part_a() -> dict[str, dict[tuple[str, str], int]]:
    text = SEED_FILE.read_text()
    part_a = text.split("PART B.")[0]
    out: dict[str, dict[tuple[str, str], int]] = {}
    cur = None
    for line in part_a.splitlines():
        m = re.match(r"\s+seed index (\w+) \(base (\d+)\):", line)
        if m:
            cur = "seed" + m.group(1) if m.group(1) != "dry" else "dry"
            assert BASES[cur] == m.group(2), (cur, m.group(2))
            out[cur] = {}
            continue
        m = re.match(r"\s+(\w+)\s+(\w+)\s+'(\d+)\|(\w+)\|(\w+)' -> (\d+)$", line)
        if m and cur:
            unit, role, b, u2, r2, val = m.groups()
            assert (u2, r2) == (unit, role) and b == BASES[cur], line
            out[cur][(unit, role)] = int(val)
    return out


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_show_sha(path: str) -> str:
    data = subprocess.run(
        ["git", "-C", str(WORKTREE), "show", f"{SCRIPT_COMMIT}:{path}"],
        check=True,
        capture_output=True,
    ).stdout
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    dry_attempt = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    part_a = parse_part_a()
    survivors = json.loads(SURVIVORS.read_text())["evaluations"]["R1"]
    assert len(survivors) == 10 and survivors == sorted(survivors)
    assert all(s in survivors for s in FEAT_LINEAGES + SPEC_KEPT)
    id_map = {
        s: s for s in survivors
    }  # R1 scripts carry no alias table: every id in an output is its survivor-list id

    plan: dict = {
        "evaluation": "R1",
        "plan_kind": "fragment of the run plan, stage 1S point 9 item (vii); not hashed by this file",
        "script_commit": SCRIPT_COMMIT,
        "worktree_root": str(WORKTREE),
        "survivor_list": {
            "path": "studies/m0/manifests/survivor_list_of_record.json",
            "sha256": sha256_file(SURVIVORS),
            "lineages": survivors,
        },
        "items_per_level": {"run": N_RUN, "dry": N_DRY},
        "bases": {
            k: {"base_integer": v, "kind": "analytical (sha256 of a fixed string)"}
            for k, v in BASES.items()
        },
        "environment_notes": "Variables listed per command are the ones the plan sets. PATH and HOME are inherited from the runner; nothing else is read by the scripts.",
        "dry_run_exclusions": [],
        "units": {},
    }

    def seeds_for(unit: str, key: str) -> list[dict]:
        rows = []
        for role in ROLES[unit]:
            v = seed_int(BASES[key], unit, role)
            assert part_a[key][(unit, role)] == v, (key, unit, role)
            rows.append({"role": role, "integer": v, "derivation": f"{BASES[key]}|{unit}|{role}"})
        return rows

    def outdir(unit: str, key: str) -> Path:
        if key == "dry":
            return dry_attempt / unit / "dry"
        return RUN_ROOT / unit / key

    def run_block(unit: str, key: str) -> dict:
        n = N_DRY if key == "dry" else N_RUN
        seeds = seeds_for(unit, key)
        sv = {s["role"]: str(s["integer"]) for s in seeds}
        od = outdir(unit, key)
        env = dict(COMMON_ENV)
        root = str(WORKTREE)
        blk: dict = {
            "kind": "dry-run seeds" if key == "dry" else f"run seed index {key[-1]}",
            "items_per_level": n,
            "cwd": root,
            "seeds": seeds,
            "output_dir": str(od),
            "stdout_file": str(od / "stdout.txt"),
            "stderr_file": str(od / "stderr.txt"),
        }
        if unit == "R1a":
            env["PYTHONPATH"] = root
            for r, name in (
                ("feat1_fit", "M0FR_R1A_FEAT1_FIT"),
                ("feat1_test", "M0FR_R1A_FEAT1_TEST"),
                ("feat2_fit", "M0FR_R1A_FEAT2_FIT"),
                ("feat2_test", "M0FR_R1A_FEAT2_TEST"),
            ):
                env[name] = sv[r]
            blk["argv"] = [
                *UV,
                "-m",
                "studies.m0.fresh_run.r1.r1_fix4_measure",
                str(n),
                sv["aud_seed"],
                sv["aud_fit"],
                sv["impl_seed"],
                sv["impl_fit"],
                str(od),
                *survivors,
            ]
            blk["fixed_size_draws_in_code"] = (
                "audit fit 400, implementer fit 300, lookup fit 3000 and lookup test 1000 per level (r1_fix4_tells.feature_rows) whatever the item count (lead ruling R-47)"
            )
            blk["output_files"] = sorted(
                [str(od / f"{s}.{k}.jsonl") for s in survivors for k in ("aud", "impl", "feat")]
                + [blk["stdout_file"], blk["stderr_file"]]
            )
        elif unit == "R1b":
            env["PYTHONPATH"] = root
            nf = N_DRY if key == "dry" else N_RUN
            blk["n_feat"] = nf
            blk["argv"] = [
                *UV,
                f"{FINAL_R1}/run_rules_final.py",
                str(n),
                sv["aud_seed"],
                sv["aud_fit"],
                sv["impl_seed"],
                sv["impl_fit"],
                sv["feat_fit"],
                sv["feat_test"],
                str(nf),
                str(od),
                *survivors,
            ]
            blk["fixed_size_draws_in_code"] = (
                "audit fit 400 and implementer fit 300 per level; lookup fit and test draws are n_feat each"
            )
            blk["output_files"] = sorted(
                [str(od / f"{s}.{k}.jsonl") for s in survivors for k in ("aud", "impl", "feat")]
                + [blk["stdout_file"], blk["stderr_file"]]
            )
        else:
            env["PYTHONPATH"] = f"{root}:{root}/{FINAL_R1}"
            blk["argv"] = [
                *UV,
                "studies/m0/fresh_run/r1/new_rules_final.py",
                str(n),
                sv["fit"],
                sv["test"],
            ]
            blk["fixed_size_draws_in_code"] = (
                "fit draw of n items per level for each lookup (lead ruling R-47)"
            )
            blk["output_files"] = [blk["stdout_file"], blk["stderr_file"]]
            blk["note"] = (
                "results go to standard output only; no output directory is created by the script, so the runner creates output_dir before the command"
            )
        blk["env"] = dict(sorted(env.items()))
        return blk

    units = {
        "R1a": {
            "script": "studies/m0/r1_fix4_measure.py",
            "runs_from": "run copy studies/m0/fresh_run/r1/r1_fix4_measure.py (module studies.m0.fresh_run.r1.r1_fix4_measure) which imports the copy of r1_fix4_tells.py",
            "copies": [
                "studies/m0/fresh_run/r1/r1_fix4_measure.py",
                "studies/m0/fresh_run/r1/r1_fix4_tells.py",
            ],
            "must_contain": {
                "aud_and_impl_files_for_every_lineage": survivors,
                "feat_files_with_rows_for": FEAT_LINEAGES,
                "feat_files_empty_by_construction_for": [
                    s for s in survivors if s not in FEAT_LINEAGES
                ],
            },
            "id_map": {
                "rule": "each output file name is <lineage id>.<aud|impl|feat>.jsonl; the id is the survivor-list id",
                "map": id_map,
            },
        },
        "R1b": {
            "script": f"{FINAL_R1}/run_rules_final.py",
            "runs_from": "the original, as committed (all seeds and lineages are on the command line)",
            "copies": [],
            "must_contain": {
                "aud_and_impl_files_for_every_lineage": survivors,
                "feat_files_with_rows_for": FEAT_LINEAGES,
                "feat_files_empty_by_construction_for": [
                    s for s in survivors if s not in FEAT_LINEAGES
                ],
            },
            "id_map": {
                "rule": "each output file name is <lineage id>.<aud|impl|feat>.jsonl; the id is the survivor-list id",
                "map": id_map,
            },
        },
        "R1c": {
            "script": f"{FINAL_R1}/new_rules_final.py",
            "runs_from": "run copy studies/m0/fresh_run/r1/new_rules_final.py (S2b: the entry R1.conditional_decision_tree_r6 of SPEC removed); fgen is imported from the original through PYTHONPATH (lead ruling R-49)",
            "copies": ["studies/m0/fresh_run/r1/new_rules_final.py"],
            "must_contain": {"stdout_lines_with_lineage_id_for": SPEC_KEPT},
            "id_map": {
                "rule": "each stdout line begins with the lineage id padded to 36 characters; the id is the survivor-list id",
                "map": {s: s for s in SPEC_KEPT},
            },
        },
    }
    for unit, u in units.items():
        u["items_per_level"] = {"run": N_RUN, "dry": N_DRY}
        u["seed_roles"] = ROLES[unit]
        u["runs"] = {key: run_block(unit, key) for key in ("dry", "seed1", "seed2", "seed3")}
        plan["units"][unit] = u
    plan["copies"] = {
        p: {
            "original": o,
            "original_sha256_at_b78e58b1": git_show_sha(o),
            "copy_sha256": sha256_file(WORKTREE / p),
        }
        for p, o in (
            ("studies/m0/fresh_run/r1/r1_fix4_tells.py", "studies/m0/r1_fix4_tells.py"),
            ("studies/m0/fresh_run/r1/r1_fix4_measure.py", "studies/m0/r1_fix4_measure.py"),
            ("studies/m0/fresh_run/r1/new_rules_final.py", f"{FINAL_R1}/new_rules_final.py"),
        )
    }
    out_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
