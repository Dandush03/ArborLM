"""M0 fresh run, evaluation M1 (units M1a, M1b, M1c): writes run_plan_m1.json (deterministic). Standard library only.

Seeds are recomputed by the formula of ADR-0033 addendum 1 section 4A stage 1S point 4 and asserted equal to the
integers of part A of addendum1_rev6_fresh_run.out.txt. Writes a new file; refuses to overwrite.

Run from the worktree root:
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python studies/m0/fresh_run/m1/make_run_plan_m1.py <dry_attempt_number> <out_json>
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

COMMIT = "b78e58b1f47619f070dfc6c0a88999d345b1a34b"
WORKTREE = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
MAIN = "/Users/daniellaloush/dandush03/ArborLM"
SPEC_WT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1"
PART_A = f"{SPEC_WT}/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev6_fresh_run.out.txt"
RUN_ROOT = f"{MAIN}/experiments/m0_fresh_run_20261126"
DRY_ROOT = f"{MAIN}/experiments/_scratch/m0_fr_dry_m1_20261126"
AUD = "docs/reviews/m0-lineage-decision-2026-11-25"
COPY_DIR = "studies/m0/fresh_run/m1"
PKG = "studies.m0.fresh_run.m1"

STUDY_SEED = "400002"
BASES = {
    "1": f"{STUDY_SEED}|fresh-shortcut|1",
    "2": f"{STUDY_SEED}|fresh-shortcut|2",
    "3": f"{STUDY_SEED}|fresh-shortcut|3",
    "dry": f"{STUDY_SEED}|fresh-shortcut-dry-run",
}
ROLES = {"M1a": ["own", "a4", "a3"], "M1b": ["seed"], "M1c": ["seed"]}
ENV_NAMES = {"own": "M1A_SEED_OWN", "a4": "M1A_SEED_A4", "a3": "M1A_SEED_A3"}
N_RUN, N_DRY = 4000, 20
WORKERS_M1A = 6  # the script's own default (m1_fix4_battery.py main)
DRY_TIMEOUT_S = {"M1a": 600, "M1b": 600, "M1c": 600}


def h(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def orig_sha(path: str) -> str:
    return sha_bytes(subprocess.run(["git", "show", f"{COMMIT}:{path}"], check=True, capture_output=True).stdout)


def main() -> None:
    attempt = int(sys.argv[1])
    out_path = Path(sys.argv[2])
    if out_path.exists():
        sys.exit(f"refusing to overwrite {out_path}")

    # bases, and the part A integers of the seed file
    base_int = {k: h(v) for k, v in BASES.items()}
    assert base_int["1"] == 16103270370041696293 and base_int["2"] == 10773834973117025986
    assert base_int["3"] == 619660634241804713 and base_int["dry"] == 3342082268851962967
    part_a = Path(PART_A).read_text()
    found: dict[tuple[str, str, str], int] = {}
    for m in re.finditer(r"^\s+(M1[abc])\s+(\w+)\s+'(\d+)\|(M1[abc])\|(\w+)'\s+->\s+(\d+)\s*$", part_a, re.M):
        unit, role, base_txt, unit2, role2, val = m.groups()
        assert unit == unit2 and role == role2
        found[(base_txt, unit, role)] = int(val)
    seeds: dict[str, dict[str, dict[str, int]]] = {}
    for idx in BASES:
        seeds[idx] = {}
        for unit, roles in ROLES.items():
            seeds[idx][unit] = {}
            for role in roles:
                text = f"{base_int[idx]}|{unit}|{role}"
                v = h(text)
                assert found[(str(base_int[idx]), unit, role)] == v, (idx, unit, role)
                seeds[idx][unit][role] = v

    survivors = json.loads(Path("studies/m0/manifests/survivor_list_of_record.json").read_text())["evaluations"]["M1"]
    assert len(survivors) == 29 and survivors == sorted(survivors)
    id_map = {i: i for i in survivors}  # identity: the M1 scripts write survivor-list ids unchanged

    copies = {n: sha_bytes(Path(f"{COPY_DIR}/{n}").read_bytes()) for n in
              ("m1_fix4_battery.py", "m1_fix3_shortcuts.py", "shortcuts_a4.py", "shortcuts_a3.py")}
    rules_a5 = f"{AUD}/final_m1/rules_a5.py"
    rules_a5_1 = f"{AUD}/final_m1/rules_a5_attempt1.py"
    scripts = {
        "M1a": [{"path": f"{COPY_DIR}/{n}", "sha256": s, "kind": "run copy (see COPIES.md)"} for n, s in sorted(copies.items())],
        "M1b": [{"path": rules_a5, "sha256": orig_sha(rules_a5), "kind": "as committed at b78e58b1"}],
        "M1c": [{"path": rules_a5_1, "sha256": orig_sha(rules_a5_1), "kind": "as committed at b78e58b1"}],
    }

    base_env = {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": WORKTREE}
    uvpy = ["uv", "run", "--locked", "python"]
    plan: dict = {
        "plan": "M0 fresh run, evaluation M1: units M1a, M1b, M1c",
        "status": "FRAGMENT: self-check by the implementer, not reviewed; not hashed; nothing here was run on any run seed",
        "specification": "ADR-0033 addendum 1 (approved 2026-11-26), section 4A stage 1S, at 2c944302 on claude/m0-spec",
        "rule_scripts_commit": COMMIT,
        "worktree_and_cwd": WORKTREE,
        "environment_note": "the variables listed per command are set in addition to the inherited environment (PATH, HOME); nothing else is set; the process must start with cwd = worktree_and_cwd",
        "bases": {k: {"text": BASES[k], "integer": base_int[k]} for k in BASES},
        "seed_formula": "int.from_bytes(sha256('<base integer as decimal text>|<unit>|<role>')[:8], 'big'); asserted equal to part A of addendum1_rev6_fresh_run.out.txt",
        "survivor_list": {"source": "studies/m0/manifests/survivor_list_of_record.json, evaluations.M1", "ids": survivors},
        "id_map_to_survivor_id": {
            "M1a": id_map,
            "M1b": id_map,
            "M1c": id_map,
            "note": "identity for every unit: m1_fix4_battery.py, rules_a5.py and rules_a5_attempt1.py write ids as lineages_m1_fix4 names them, which are the survivor-list ids; no alias table is involved. Other keys in the outputs are not lineage ids: M1a 'exclusions' keys are lineage stems, 'seeds' holds the original's literals.",
        },
        "units": {},
    }

    def out_dir(unit: str, idx: str) -> str:
        return f"{DRY_ROOT}/attempt{attempt}/{unit}/dry" if idx == "dry" else f"{RUN_ROOT}/{unit}/seed{idx}"

    for unit in ("M1a", "M1b", "M1c"):
        entry: dict = {"scripts": scripts[unit], "runs": {}}
        for idx in ("dry", "1", "2", "3"):
            n = N_DRY if idx == "dry" else N_RUN
            od = out_dir(unit, idx)
            env = dict(base_env)
            seed_list = []
            if unit == "M1a":
                for role in ROLES[unit]:
                    env[ENV_NAMES[role]] = str(seeds[idx][unit][role])
                    seed_list.append({"role": role, "integer": seeds[idx][unit][role], "enters_as": f"environment variable {ENV_NAMES[role]}"})
                out_file = f"{od}/battery.json"
                argv = uvpy + ["-m", f"{PKG}.m1_fix4_battery", "--n", str(n), "--workers", str(WORKERS_M1A), "--out", out_file, "--only", ",".join(survivors)]
                fmt = "JSON object: n, seeds (the ORIGINAL's literals {own 410302, a4 17, a3 5}, not the true seeds), exclusions, raw.own.<lineage>.<level 0..6>.{N, base, mode_insample, halfwidth95, rates, minus_base, answer_echoed_anywhere}; raw.a4.<lineage>.<level>.{N, base, best_echo, answer_echoed_anywhere, rates, minus_base, within_applicable}; raw.a3.<lineage>.<level>.{N, base, rates, minus_base} and raw.a3.<lineage>.a3_skipped_items; summary.<lineage>.<level>.{max_abs_excess, signed, rule, base_by_source, excluded_procedure_max_signed, excluded_procedure_rule}"
                must = {
                    "file": out_file,
                    "json_paths": ["raw.own", "raw.a4", "raw.a3"],
                    "each_holds": "every survivor lineage id, each with level keys '0'..'6'",
                    "expected_row_N": n,
                }
            else:
                script = rules_a5 if unit == "M1b" else rules_a5_1
                seed_int = seeds[idx][unit]["seed"]
                seed_list.append({"role": "seed", "integer": seed_int, "enters_as": "command-line argument 4 (python <script> fresh N SEED out.json)"})
                out_file = f"{od}/out.json"
                argv = uvpy + [script, "fresh", str(n), str(seed_int), out_file]
                fmt = "JSON object: mode, N, seed, label, results.<lineage>.<level 0..6>.{N, base, rates, minus_base, within_applicable, a3_skipped_items, [one_op_best], [asked_is_largest_observed_vs_uniform]}"
                must = {
                    "file": out_file,
                    "json_paths": ["results"],
                    "each_holds": "every survivor lineage id, each with level keys '0'..'6'",
                    "expected_row_N": n,
                }
            if unit == "M1a":
                seed_check = "stored seed of the original is written into output.seeds and is NOT the true seed"
            else:
                seed_check = "the true seed is written to output.seed"
            run = {
                "argv": argv,
                "cwd": WORKTREE,
                "env": dict(sorted(env.items())),
                "items_per_level": n,
                "levels": [0, 1, 2, 3, 4, 5, 6],
                "seeds": seed_list,
                "seed_note": seed_check,
                "output_directory_created_by_runner_before_start": od,
                "stdout_redirected_to": f"{od}/stdout.txt",
                "stderr_redirected_to": f"{od}/stderr.txt",
                "output_files_written_by_the_command": [out_file],
                "output_format": fmt,
                "must_contain": must,
                "survivor_lineages_the_output_must_contain": survivors,
            }
            if idx == "dry":
                run["timeout_seconds"] = DRY_TIMEOUT_S[unit]
                run["dry_attempt"] = attempt
            entry["runs"]["dry" if idx == "dry" else f"seed{idx}"] = run
        plan["units"][unit] = entry
    out_path.write_text(json.dumps(plan, indent=1, sort_keys=True) + "\n")
    print("wrote", out_path)


if __name__ == "__main__":
    main()
