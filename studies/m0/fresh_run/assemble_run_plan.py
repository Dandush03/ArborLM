# ruff: noqa: E501
"""Assemble ONE run plan from the four fragments (stage 1S point 9 (vii)). Standard library only; reads the fragments, edits none.

    python3 -I studies/m0/fresh_run/assemble_run_plan.py [--out PATH] [--fragments-dir DIR] [--survivors PATH]

One convention for all eleven units:
  seeds 1-3 : /Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_20261126/<unit>/seed<i>
  dry set   : /Users/daniellaloush/dandush03/ArborLM/experiments/m0_fresh_run_dry_20261126/<unit>
Only the output-directory prefixes in argv / env / stdout / stderr / writes fields are rewritten; the script asserts, for every command,
that putting the old prefix back gives the fragment's command exactly (so nothing else changed), that the multiset of long digit strings
(the seed integers) is unchanged, and that every seed integer is the sha256 derivation of its base, unit and role.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = "/Users/daniellaloush/dandush03/ArborLM/experiments"
RUN_ROOT = EXP + "/m0_fresh_run_20261126"
DRY_ROOT = EXP + "/m0_fresh_run_dry_20261126"
UNIT_ORDER = ["R1a", "R1b", "R1c", "R2a", "R2b", "M1a", "M1b", "M1c", "C1a", "C1b", "C1c"]
SEED_SETS = ["dry", "1", "2", "3"]
BASE_TEXT = {"1": "400002|fresh-shortcut|1", "2": "400002|fresh-shortcut|2", "3": "400002|fresh-shortcut|3", "dry": "400002|fresh-shortcut-dry-run"}
BASE_INT = {"1": 16103270370041696293, "2": 10773834973117025986, "3": 619660634241804713, "dry": 3342082268851962967}
SURVIVORS_REL = "studies/m0/manifests/survivor_list_of_record.json"


def sd(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def new_dir(unit: str, seed_set: str) -> str:
    return f"{DRY_ROOT}/{unit}" if seed_set == "dry" else f"{RUN_ROOT}/{unit}/seed{seed_set}"


def rewrite(obj: Any, old: str, new: str) -> Any:
    if isinstance(obj, str):
        return obj.replace(old, new)
    if isinstance(obj, list):
        return [rewrite(x, old, new) for x in obj]
    if isinstance(obj, dict):
        return {k: rewrite(v, old, new) for k, v in obj.items()}
    return obj


def long_digits(obj: Any) -> list[str]:
    """Every maximal run of 15 or more digits in every string and integer of obj (the seed integers), sorted."""
    out: list[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, str):
            out.extend(re.findall(r"(?<!\d)\d{15,}(?!\d)", x))
        elif isinstance(x, bool):
            return
        elif isinstance(x, int):
            if len(str(abs(x))) >= 15:
                out.append(str(x))
        elif isinstance(x, list):
            for y in x:
                walk(y)
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(k)
                walk(v)

    walk(obj)
    return sorted(out)


def rel(path: str, old_dir: str) -> str:
    assert path == old_dir or path.startswith(old_dir + "/"), (path, old_dir)
    return os.path.relpath(path, old_dir)


def normalise_command(c: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    """One unified command from a fragment's command; the old output directory is replaced by the new one in every string."""
    cmd = {"name": c["name"], "argv": c["argv"], "cwd": c["cwd"], "env": c["env"], "stdout_file": c["stdout_file"],
           "stderr_file": c["stderr_file"], "writes": c["writes"]}
    out = rewrite(cmd, old, new)
    back = rewrite(out, new, old)
    assert back == cmd, "a command changed by more than the output-path prefix: " + c["name"]
    assert long_digits(out) == long_digits(cmd), "a seed integer (long digit string) changed in " + c["name"]
    assert old == new or old not in json.dumps(out), "old output prefix left in " + c["name"]
    return out


def load(path: str) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------- fragments -> neutral form
def r1_runs(frag: dict[str, Any], unit: str) -> dict[str, Any]:
    u = frag["units"][unit]
    runs = {}
    for ss, key in (("dry", "dry"), ("1", "seed1"), ("2", "seed2"), ("3", "seed3")):
        r = u["runs"][key]
        runs[ss] = {"old_dir": r["output_dir"], "items": r["items_per_level"], "seeds": r["seeds"],
                    "commands": [{"name": unit, "argv": r["argv"], "cwd": r["cwd"], "env": r["env"], "stdout_file": r["stdout_file"],
                                  "stderr_file": r["stderr_file"], "writes": r["output_files"]}]}
    return runs


def r2_runs(frag: dict[str, Any], unit: str) -> dict[str, Any]:
    u = frag["units"][unit]
    runs = {}
    for ss in SEED_SETS:
        r = u["runs"][ss]
        cmds = [{"name": c["name"], "argv": c["argv"], "cwd": r["working_directory"], "env": r["environment"], "stdout_file": c["stdout_file"],
                 "stderr_file": c["stderr_file"], "writes": c["writes"]} for c in r["commands"]]
        runs[ss] = {"old_dir": r["output_directory"], "items": r["items_per_level"], "seeds": r["seeds"], "commands": cmds}
    return runs


def m1_key(ss: str) -> str:
    return "dry" if ss == "dry" else "seed" + ss


def m1_runs(frag: dict[str, Any], unit: str) -> dict[str, Any]:
    u = frag["units"][unit]
    runs = {}
    for ss in SEED_SETS:
        r = u["runs"][m1_key(ss)]
        runs[ss] = {"old_dir": r["output_directory_created_by_runner_before_start"], "items": r["items_per_level"], "seeds": r["seeds"],
                    "commands": [{"name": unit, "argv": r["argv"], "cwd": r["cwd"], "env": r["env"], "stdout_file": r["stdout_redirected_to"],
                                  "stderr_file": r["stderr_redirected_to"], "writes": r["output_files_written_by_the_command"]}]}
    return runs


def c1_runs(frag: dict[str, Any], unit: str) -> dict[str, Any]:
    u = frag["units"][unit]
    runs = {}
    for ss in SEED_SETS:
        r = u[ss]
        cmds = []
        for i, st in enumerate(r["chain"]):
            cmds.append({"name": f"{unit}-step{i + 1}", "argv": st["argv"], "cwd": st["cwd"], "env": st["env_set"], "stdout_file": st["stdout"],
                         "stderr_file": st["stderr"], "writes": st["outputs_written"], "what": st["what"]})
        runs[ss] = {"old_dir": r["run_dir"], "items": r["items_per_level"], "seeds": [{"role": r["seed_role"], "integer": r["seed_integer"]}],
                    "commands": cmds}
    return runs


# ---------------------------------------------------------------- the pooling-script view of each unit's outputs
def pool_outputs(unit: str, frags: dict[str, dict[str, Any]], old: str, ss: str) -> list[dict[str, Any]]:
    """The outputs the pooling script reads, with file names relative to the unit's output directory."""
    if unit in ("R1a", "R1b"):
        u = frags["R1"]["units"][unit]
        mc = u["must_contain"]
        assert sorted(mc) == ["aud_and_impl_files_for_every_lineage", "feat_files_empty_by_construction_for", "feat_files_with_rows_for"], sorted(mc)
        return [{"form": "r1_rows", "id_map": u["id_map"]["map"], "kinds": {
            "aud": {"glob": "*.aud.jsonl", "must_contain": mc["aud_and_impl_files_for_every_lineage"]},
            "impl": {"glob": "*.impl.jsonl", "must_contain": mc["aud_and_impl_files_for_every_lineage"]},
            "feat": {"glob": "*.feat.jsonl", "must_contain": mc["feat_files_with_rows_for"], "empty_by_construction_for": mc["feat_files_empty_by_construction_for"]}}}]
    if unit == "R1c":
        u = frags["R1"]["units"][unit]
        return [{"form": "r1c_stdout", "file": "stdout.txt", "id_map": u["id_map"]["map"], "must_contain": u["must_contain"]["stdout_lines_with_lineage_id_for"]}]
    if unit in ("R2a", "R2b"):
        f = frags["R2"]
        outs = []
        for c in f["units"][unit]["runs"][ss]["commands"]:
            for w in c["writes"]:
                base = os.path.basename(w)
                outs.append({"form": "r2_json", "variant": {"r2a.json": "r2a", "f_rules.json": "f_rules", "f_rules_new.json": "f_rules_new"}[base],
                             "file": rel(w, old), "id_map": f["lineage_id_map"][f"{unit}:{base}"]["map"], "must_contain": c["must_contain"]})
        return outs
    if unit in ("M1a", "M1b", "M1c"):
        f = frags["M1"]
        r = f["units"][unit]["runs"][m1_key(ss)]
        return [{"form": "m1_battery" if unit == "M1a" else "m1_results", "file": rel(r["must_contain"]["file"], old),
                 "id_map": f["id_map_to_survivor_id"][unit], "must_contain": r["survivor_lineages_the_output_must_contain"]}]
    if unit in ("C1a", "C1b", "C1c"):
        r = frags["C1"]["units"][unit][ss]
        idm, mcs = r["id_map"], r["must_contain"]
        outs: list[dict[str, Any]] = []
        for path, spec in sorted(mcs.items()):
            name = rel(path, old)
            if name == "s5.json":
                m = idm["s5_json_key_to_survivor_id"]
                outs.append({"form": "c1_s5", "file": name, "id_map": m, "must_contain": sorted({m[k] for k in spec["top_level_keys_are_draw_ids"]})})
            elif name == "a3":
                per = {}
                for sid, d in spec["per_survivor"].items():
                    per[sid] = {"primary_file": rel(d["primary_file"], old), "primary_key": d["primary_key_in_file"],
                                "fallback_file": None if d["fallback_file"] is None else rel(d["fallback_file"], old),
                                "fallback_key": d["fallback_key_in_file"], "run_log_key": d["run_log_key"]}
                outs.append({"form": "c1_a3", "run_log": "a3/run_log.json", "per_survivor": per, "must_contain": sorted(per)})
            elif name in ("f5.json", "f5b.json"):
                m = idm["closed_forms"]["json_key_fid_to_survivor_id"]
                outs.append({"form": "c1_closed", "file": name, "id_map": m, "must_contain": sorted({m[k] for k in spec["top_level_keys_are_survivor_ids"]})})
            elif name == "battery.json":
                m = idm["battery_json_key_to_survivor_id"]
                outs.append({"form": "c1_battery", "file": name, "id_map": m, "must_contain": sorted({m[k] for k in spec["top_level_keys_are_survivor_ids"]})})
            elif name in ("gen", "rules"):
                continue  # intermediate draws and s4 records: not read by the pooling script
            else:
                raise AssertionError(f"unknown must_contain entry {name} in {unit}")
        return outs
    raise AssertionError(unit)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "run_plan.json"))
    ap.add_argument("--fragments-dir", default=HERE, help="the directory that holds r1/ r2/ m1/ c1/")
    ap.add_argument("--survivors", default=os.path.join(HERE, "..", "manifests", "survivor_list_of_record.json"))
    a = ap.parse_args()
    if os.path.exists(a.out):
        print("refusing to overwrite " + a.out, file=sys.stderr)
        return 3
    paths = {e: os.path.join(a.fragments_dir, e.lower(), f"run_plan_{e.lower()}.json") for e in ("R1", "R2", "M1", "C1")}
    frags = {e: load(p) for e, p in paths.items()}
    assert set(frags["R1"]["units"]) == {"R1a", "R1b", "R1c"}
    for e in ("R1", "R2"):
        assert frags[e]["dry_run_exclusions"] == [], e
    surv = load(a.survivors)
    getters = {"R1": r1_runs, "R2": r2_runs, "M1": m1_runs, "C1": c1_runs}
    units: dict[str, Any] = {}
    for unit in UNIT_ORDER:
        ev = unit[:2]
        neutral = getters[ev](frags[ev], unit)
        runs: dict[str, Any] = {}
        views: dict[str, Any] = {}
        for ss in SEED_SETS:
            r = neutral[ss]
            old, new = r["old_dir"], new_dir(unit, ss)
            cmds = [normalise_command(c, old, new) for c in r["commands"]]
            for c0, c1 in zip(r["commands"], cmds, strict=True):
                if "what" in c0:
                    c1["what"] = c0["what"]
            seeds = []
            for s in r["seeds"]:
                role, integer = s["role"], s["integer"]
                assert sd(f"{BASE_INT[ss]}|{unit}|{role}") == integer, (unit, ss, role)
                text = str(integer)
                assert any(text in " ".join(c["argv"]) or text in " ".join(map(str, c["env"].values())) for c in cmds), ("seed not in any command", unit, ss, role)
                seeds.append({"role": role, "integer": integer})
            runs[ss] = {"seed_set": ss, "base_integer": BASE_INT[ss], "base_text": BASE_TEXT[ss], "output_dir": new, "items_per_level": r["items"],
                        "seeds": seeds, "commands": cmds}
            views[ss] = pool_outputs(unit, frags, old, ss)
        for ss in SEED_SETS[1:]:
            assert views[ss] == views["dry"], (unit, ss, "the pooling view differs between seed sets")
        items = {"dry": runs["dry"]["items_per_level"], "run": runs["1"]["items_per_level"]}
        assert runs["2"]["items_per_level"] == runs["3"]["items_per_level"] == items["run"], unit
        units[unit] = {"evaluation": ev, "items_per_level": items, "outputs": views["dry"], "runs": runs}
    plan = {
        "plan_kind": "ONE run plan, assembled from four fragments by studies/m0/fresh_run/assemble_run_plan.py (stage 1S point 9 (vii)); not hashed by this file",
        "script_commit": frags["R1"]["script_commit"],
        "fragments": {e: {"path": f"studies/m0/fresh_run/{e.lower()}/run_plan_{e.lower()}.json", "sha256": sha256_file(p)} for e, p in paths.items()},
        "output_roots": {"run": RUN_ROOT, "dry": DRY_ROOT},
        "convention": {"run": RUN_ROOT + "/<unit>/seed<i>", "dry": DRY_ROOT + "/<unit>",
                       "rewritten": "only the old output-directory prefix in argv, env, stdout_file, stderr_file and writes of every command; checked by reverse substitution"},
        "survivor_list": {"path": SURVIVORS_REL, "sha256": sha256_file(a.survivors),
                          "counts": {k: len(v) for k, v in sorted(surv["evaluations"].items())}},
        "unit_order": UNIT_ORDER,
        "dry_run_exclusions": [],
        "worktree_root": frags["R1"]["worktree_root"],
        "units": units,
    }
    assert plan["survivor_list"]["sha256"] == frags["R1"]["survivor_list"]["sha256"]
    with open(a.out, "x") as f:
        json.dump(plan, f, indent=1, sort_keys=True)
        f.write("\n")
    print("wrote " + a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
