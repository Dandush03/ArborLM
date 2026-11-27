"""Builds run_plan_r2.json (units R2a and R2b) deterministically. Standard library only. It reads: the survivor list of record, the seed file (part A of
addendum1_rev6_fresh_run.out.txt, to assert every seed integer against the formula of stage 1S point 4), and the four copies (hashes).
It is not a runner: it executes nothing. Usage from the worktree root:
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python studies/m0/fresh_run/r2/build_r2_plan.py <attemptN> <out.json>
`<attemptN>` only fixes the scratch directory of the dry-run entries (experiments/_scratch/m0_fr_dry_r2_20261126/<attemptN>/...). Self-check, not independent review."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/agent-a0c9d741ea96ce52f"
SEEDFILE = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1/docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev6_fresh_run.out.txt"
RUN_DIR = ROOT + "/experiments/m0_fresh_run_20261126"
DRY_DIR = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_fr_dry_r2_20261126"
COPY_DIR = "studies/m0/fresh_run/r2"
BASES = {"1": "400002|fresh-shortcut|1", "2": "400002|fresh-shortcut|2", "3": "400002|fresh-shortcut|3", "dry": "400002|fresh-shortcut-dry-run"}
ITEMS = {"1": 4000, "2": 4000, "3": 4000, "dry": 20}
LEVELS = [0, 1, 2, 3, 4, 5, 6]
UV = ["uv", "run", "--locked", "python"]


def h8(s: str) -> int:
    return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8], "big")


def sha_file(p: str) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def seeds_from_file() -> dict[str, dict[str, int]]:
    """part A: {seed index label: {'<unit> <role>': integer}}, base integers under 'base'."""
    out: dict[str, dict[str, int]] = {}
    cur = None
    for ln in Path(SEEDFILE).read_text().splitlines():
        if ln.startswith("PART B"):
            break
        m = re.match(r"\s+seed index (\w+) \(base (\d+)\):", ln)
        if m:
            cur = m.group(1)
            out[cur] = {"base": int(m.group(2))}
            continue
        m = re.match(r"\s+(R2a|R2b)\s+(tag)\s+'([^']+)' -> (\d+)", ln)
        if m and cur:
            out[cur][f"{m.group(1)} {m.group(2)}"] = int(m.group(4))
    return out


def main() -> None:
    attempt, outp = sys.argv[1], sys.argv[2]
    sv = json.loads(Path("studies/m0/manifests/survivor_list_of_record.json").read_text())
    surv = sv["evaluations"]["R2"]
    assert len(surv) == 17 and "R2.to_base_wide" in surv and surv == sorted(surv)
    names = [s.split(".", 1)[1] for s in surv]
    # the 13 survivor lineages that the copy of f_new_heur.py keeps (read from the copy's own source, nothing executed)
    src = Path(COPY_DIR + "/f_new_heur.py").read_text()
    new_keys = sorted(set(re.findall(r'^@rule\("([a-z_0-9]+)"', src, re.M)))
    assert not (set(new_keys) - set(names)), set(new_keys) - set(names)
    assert len(new_keys) == 13 and not {"digit_root", "interval_scheduling"} & set(new_keys)
    new_ids = ["R2." + k for k in new_keys]
    fromfile = seeds_from_file()
    seeds: dict[str, dict[str, int]] = {}
    for idx, base_txt in BASES.items():
        base = h8(base_txt)
        assert fromfile[idx]["base"] == base, idx
        seeds[idx] = {}
        for u in ("R2a", "R2b"):
            v = h8(f"{base}|{u}|tag")
            assert fromfile[idx][f"{u} tag"] == v, (idx, u)
            seeds[idx][u] = v
    copies = {}
    for n in ("r2_fix4_battery.py", "f_rules.py", "f_rules_new.py", "f_new_heur.py"):
        copies[f"{COPY_DIR}/{n}"] = sha_file(f"{ROOT}/{COPY_DIR}/{n}")

    def env(tag: int) -> dict[str, str]:
        return {"M0_FR_TAG": str(tag), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "PYTHONPATH": ROOT}

    def odir(unit: str, idx: str) -> str:
        return f"{DRY_DIR}/{attempt}/{unit.lower()}/dry" if idx == "dry" else f"{RUN_DIR}/{unit}/seed{idx}"

    units: dict[str, dict[str, object]] = {}
    for unit in ("R2a", "R2b"):
        runs: dict[str, object] = {}
        for idx in ("dry", "1", "2", "3"):
            d, n, tag = odir(unit, idx), ITEMS[idx], seeds[idx][unit]
            if unit == "R2a":
                cmds = [{
                    "name": "r2_fix4_battery",
                    "argv": UV + ["-m", "studies.m0.fresh_run.r2.r2_fix4_battery", "run", "--n", str(n), "--seeds", "f4", "--out", f"{d}/r2a.json",
                                  "--only", ",".join(surv), "--procs", "8"],
                    "stdout_file": f"{d}/r2a.stdout.txt", "stderr_file": f"{d}/r2a.stderr.txt",
                    "writes": [f"{d}/r2a.json"],
                    "lineage_ids_in_output": surv, "must_contain": surv,
                }]
            else:
                cmds = [{
                    "name": "f_rules",
                    "argv": UV + [f"{COPY_DIR}/f_rules.py", str(n), f"{d}/f_rules.json", ",".join(names)],
                    "stdout_file": f"{d}/f_rules.stdout.txt", "stderr_file": f"{d}/f_rules.stderr.txt",
                    "writes": [f"{d}/f_rules.json"],
                    "lineage_ids_in_output": surv, "must_contain": surv,
                }, {
                    "name": "f_rules_new",
                    "argv": UV + [f"{COPY_DIR}/f_rules_new.py", str(n), f"{d}/f_rules_new.json"],
                    "stdout_file": f"{d}/f_rules_new.stdout.txt", "stderr_file": f"{d}/f_rules_new.stderr.txt",
                    "writes": [f"{d}/f_rules_new.json"],
                    "lineage_ids_in_output": new_ids, "must_contain": new_ids,
                }]
            runs[idx] = {
                "seed_label": "fresh-shortcut-dry-run" if idx == "dry" else f"fresh-shortcut|{idx}",
                "base_integer": fromfile[idx]["base"],
                "seeds": [{"role": "tag", "integer": tag, "formula": f"int.from_bytes(sha256('{fromfile[idx]['base']}|{unit}|tag')[:8], 'big')",
                           "used_as": "decimal text of the integer, in env M0_FR_TAG; string seed '<tag>|<lid>|<level>|5' (train) and '|6' (test)" + ("; the f_rules_new copy uses |6 only" if unit == "R2b" else "")}],
                "items_per_level": n,
                "levels": LEVELS,
                "working_directory": ROOT,
                "environment": env(tag),
                "environment_note": "only these variables are set by the plan; PATH and HOME are inherited; the runner makes the output directory (mkdir -p) before the first command; commands run in the order listed, each to its end; stdout and stderr of each command go to the files named",
                "output_directory": d,
                "commands": cmds,
            }
        units[unit] = {"runs": runs}
    lid_map = {s: s for s in surv}
    plan = {
        "plan_for": "ADR-0033 addendum 1, stage 1S points 3, 4, 9 and 10; units R2a and R2b only (a fragment of the run plan)",
        "scripts_commit": "b78e58b1f47619f070dfc6c0a88999d345b1a34b",
        "survivor_list_of_record": {"path": "studies/m0/manifests/survivor_list_of_record.json", "sha256": sha_file(f"{ROOT}/studies/m0/manifests/survivor_list_of_record.json"), "R2": surv},
        "seed_file": {"path": SEEDFILE, "sha256": sha_file(SEEDFILE)},
        "copies_sha256": copies,
        "copies_record": f"{COPY_DIR}/COPIES.md",
        "dry_run_scratch_attempt": attempt,
        "lineage_id_map": {
            "R2a:r2a.json": {"rule": "the output writes the id as the script's fix4_set() key, which is the survivor-list id; identity", "map": lid_map},
            "R2b:f_rules.json": {"rule": "the output writes 'R2.' + the name given on the command line; identity", "map": lid_map},
            "R2b:f_rules_new.json": {"rule": "the output writes 'R2.' + a key of NEW of the copy of f_new_heur.py (13 survivors; digit_root and interval_scheduling entries removed by S2b); identity", "map": {s: s for s in new_ids}},
            "alias_tables": "none: the R2 scripts have no RULE_ALIAS, ALIAS, A3_ALIAS or A3_OLD; no file name carries a lineage id",
        },
        "survivors_without_entry_in_NEW": sorted(set(surv) - set(new_ids)),
        "dry_run_exclusions": [],
        "dry_run_exclusions_note": "empty until the dry run of point 10 (all of stage 1S points 9 (i) to (v) existing) is made by the lead",
        "units": units,
        "output_formats": {
            "r2a.json": {
                "top": ["n", "seeds", "lineages"],
                "seeds_field": "the literal 'f4'; not the seed. The seed is the tag in the plan",
                "lineages": "{lid: {level '0'..'6': {shape: {n, answer_type, distinct_answers, [yes_share when answer_type == 'yn'], rules: {name: {k, napp, nerr, acc_all, acc_app}}}}}}",
                "rule_names": "'[mine] ...' (audit 4), '[a3] ...' (audit 3), '[impl] ...' (fix-3 implementer), and 'most frequent answer (train draw)'; a rule with napp = 0 is not written",
                "cond_rules": "k / napp = acc_app (napp is the item count of that figure); k / n_all = acc_all, n_all = the shape's `n`; both recoverable from k, napp and the shape's n",
                "stderr": "'wrote <path>'",
            },
            "f_rules.json": {
                "top": ["n", "seeds", "lineages"],
                "seeds_field": "the literal text 'finalr2|<lid>|<level>|5 train, |6 test'; not the seed. The seed is the tag in the plan",
                "lineages": "{lid: {level '0'..'6': {shape: {n, answer_type, distinct_answers, rules: {name: {k, napp, nerr}}}}}}",
                "rule_names": "'[mine] ...', '[a3] ...', '[impl] ...' and 'most frequent answer (train draw)'; every rule is written, napp = 0 included",
                "cond_rules": "k / napp from k and napp; k / n_all from k and the shape's `n`",
                "stdout": "one line '<lid> <seconds>s' per lineage",
            },
            "f_rules_new.json": {
                "top": ["n", "lineages"],
                "lineages": "{lid: {level '0'..'6': {shape: {n, answer_type, rules: {'[NEW] <name>': {k, napp, nerr}}}}}}",
                "cond_rules": "k / napp from k and napp; k / n_all from k and the shape's `n` (the script's own printed figure for an open answer is k / n)",
                "stdout": "lines '<lid> L<level> [<shape>] <eff> nerr=<nerr> <name>' for effect above 0.05 or nerr > 0 (not complete; read the json)",
            },
        },
    }
    Path(outp).write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
