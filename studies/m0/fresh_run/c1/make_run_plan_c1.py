"""M0 fresh run, stage 1S point 9: the run-plan fragment for evaluation C1 (units C1a, C1b, C1c). Standard library only. Runs nothing, generates no item.

Usage (from the worktree root):
  PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1 uv run --locked python studies/m0/fresh_run/c1/make_run_plan_c1.py --out <new json path> --dry-root <scratch attempt dir>

Everything is derived from: the survivor list of record; the alias tables of the scripts at b78e58b1 (read as text with ``ast``; no script is imported or executed);
the seed formula of point 4, asserted against part A of the seed file. Output is deterministic JSON (sorted keys, no timestamps).
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

COMMIT = "b78e58b1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LEAD = Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1")
SEED_FILE = LEAD / "docs/reviews/adr-0033-m0-2026-11-20/addendum1_scripts/addendum1_rev6_fresh_run.out.txt"
RD = "docs/reviews/m0-lineage-decision-2026-11-25/"
S4 = RD + "audit4_c1/s4_rules_v2.py"
S5 = RD + "audit4_c1/s5_analyse_v2.py"
A3 = RD + "audit3_c1/a3_shortcuts.py"
F1 = RD + "final_c1/f1_draw.py"
F3 = RD + "final_c1/f3_a3_run.py"
F5B_ORIG = RD + "final_c1/f5b_closed_forms_v2.py"
F5_ORIG = RD + "final_c1/f5_closed_forms.py"
F5B = "studies/m0/fresh_run/c1/f5b_closed_forms_v2.py"
F5 = "studies/m0/fresh_run/c1/f5_closed_forms.py"
RUN_ROOT_REL = "experiments/m0_fresh_run_20261126"
ITEMS = {"run": 2000, "dry": 20}
SUBPROCESS_TIMEOUT = 3000  # = timeout=3000 of final_c1/f3_a3_run.py:34 (confirmed from the file by the assertion in main())
WORKERS = 6
BASES = {"1": "400002|fresh-shortcut|1", "2": "400002|fresh-shortcut|2", "3": "400002|fresh-shortcut|3", "dry": "400002|fresh-shortcut-dry-run"}
BASE_INT = {"1": 16103270370041696293, "2": 10773834973117025986, "3": 619660634241804713, "dry": 3342082268851962967}


def git_show(path: str) -> str:
    return subprocess.run(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def table(path: str, name: str) -> dict[str, str]:
    """Literal dict assigned to ``name`` at module level of the committed file (read with ast, not executed)."""
    for node in ast.parse(git_show(path)).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name and node.value is not None:
            return ast.literal_eval(node.value)
    raise KeyError((path, name))


def fns_keys(path_text: str) -> list[str]:
    for node in ast.parse(path_text).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "FNS" for t in node.targets):
            assert isinstance(node.value, ast.Dict)
            return [ast.literal_eval(k) for k in node.value.keys if k is not None]
    raise KeyError("FNS")


def seed_int(base: int, unit: str, role: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{base}|{unit}|{role}".encode()).digest()[:8], "big")


def part_a() -> dict[tuple[str, str, str], int]:
    """(set, unit, role) -> integer, parsed from part A of the seed file."""
    res: dict[tuple[str, str, str], int] = {}
    cur = None
    for ln in SEED_FILE.read_text().splitlines():
        if ln.startswith("PART B"):
            break
        m = re.match(r"\s+seed index (\d|dry) \(base", ln)
        if m:
            cur = m.group(1)
        m = re.match(r"\s+(C1[abc])\s+(\w+)\s+'[^']*' -> (\d+)", ln)
        if m and cur:
            res[(cur, m.group(1), m.group(2))] = int(m.group(3))
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-root", required=True, help="new scratch attempt directory; dry outputs go to <dry-root>/<unit>/dry/")
    a = ap.parse_args()
    out_path = Path(a.out)
    assert not out_path.exists(), "refusing to overwrite"
    dry_root = Path(a.dry_root).resolve()

    survivors = json.loads((ROOT / "studies/m0/manifests/survivor_list_of_record.json").read_text())["evaluations"]["C1"]
    assert len(survivors) == 26 and survivors == sorted(survivors)
    surv = set(survivors)

    # --- seeds: formula, asserted against part A of the seed file
    # the bases are int.from_bytes(sha256(<text>)[:8], "big") (section 4 derivation, labels joined by '|')
    for k in ("1", "2", "3", "dry"):
        assert int.from_bytes(hashlib.sha256(BASES[k].encode()).digest()[:8], "big") == BASE_INT[k], k
    pa = part_a()
    seeds: dict[str, dict[str, int]] = {}
    for unit in ("C1a", "C1b", "C1c"):
        seeds[unit] = {}
        for k in ("1", "2", "3", "dry"):
            v = seed_int(BASE_INT[k], unit, "seed")
            assert pa[(k, unit, "seed")] == v, (k, unit, pa.get((k, unit, "seed")), v)
            seeds[unit][k] = v

    # --- alias tables, as committed
    rule_alias = table("studies/m0/c1_fix4_draw.py", "RULE_ALIAS")
    f1_alias = table(F1, "ALIAS")
    assert rule_alias == f1_alias
    a3_alias = table("studies/m0/c1_fix4_a3_run.py", "A3_ALIAS")
    a3_old = table(F3, "A3_OLD")
    f3_src = git_show(F3)
    assert "timeout=3000" in f3_src
    swap = {v: k for k, v in rule_alias.items()}  # c1_fix4_battery.SWAP
    assert "SWAP = {v: k for k, v in RULE_ALIAS.items()}" in git_show("studies/m0/c1_fix4_battery.py")

    draw_id = {s: rule_alias.get(s, s) for s in survivors}  # id written in the draw, in its rows and in s4/s5 output
    to_surv = {v: k for k, v in draw_id.items()}
    assert len(to_surv) == 26
    file_of = {s: draw_id[s].replace("C1.", "") + ".jsonl.gz" for s in survivors}
    # the two a3 wrappers' tables, for the survivors' draw ids
    a3_ids = {}
    for s in survivors:
        d = draw_id[s]
        assert a3_alias.get(d) == a3_old.get(d), (d, a3_alias.get(d), a3_old.get(d))  # same old id in both wrappers for every survivor
        a3_ids[s] = a3_alias.get(d)
    # every id that can occur must map to exactly one survivor id, none to another
    all_ids = [*survivors, *draw_id.values(), *[v for v in a3_ids.values() if v]]
    for i in set(all_ids):
        owners = {s for s in survivors if i in (s, draw_id[s], a3_ids[s])}
        assert len(owners) == 1, (i, owners)
    nonsurv_in_tables = {
        "RULE_ALIAS": sorted(k for k in rule_alias if k not in surv),
        "A3_ALIAS keys (draw ids) not a survivor's draw id": sorted(k for k in a3_alias if k not in to_surv),
        "A3_OLD keys (draw ids) not a survivor's draw id": sorted(k for k in a3_old if k not in to_surv),
    }
    battery_name = {s: (draw_id[s] if s in rule_alias else s) for s in survivors}  # the id the battery knows (fix-3/older name) for the fix-4 five; the id itself otherwise

    # --- closed-form scripts: FNS of the copies, base file names from the committed inline map (read as text)
    copies_fns = {}
    for name, p in (("f5b", F5B), ("f5", F5)):
        keys = fns_keys((ROOT / p).read_text())
        orig_keys = fns_keys(git_show(F5B_ORIG if name == "f5b" else F5_ORIG))
        assert keys == [k for k in orig_keys if k in surv] and len(orig_keys) - len(keys) == 1
        copies_fns[name] = keys
    assert copies_fns["f5b"] == copies_fns["f5"]
    cf_keys = copies_fns["f5"]
    # base names: the inline map of the committed script maps the fix-4 five to the draw name, anything else to its id without "C1."
    cf_base = {s: draw_id[s].replace("C1.", "") for s in cf_keys}

    def tag(s: str) -> str:
        return draw_id[s].replace("C1.", "")

    def maps_draw() -> dict:
        return {"draw_file_name_to_survivor_id": {file_of[s]: s for s in survivors}, "lid_in_rows_to_survivor_id": {draw_id[s]: s for s in survivors}, "fid_in_rows_of_f1_draw_to_survivor_id": {s: s for s in survivors}}

    def a3_outputs(base: str, unit: str) -> dict:
        per = {}
        for s in survivors:
            t = tag(s)
            if a3_ids[s]:
                per[s] = {"primary_file": f"{base}/a3/{t}__alias.json", "primary_key_in_file": a3_ids[s], "fallback_file": f"{base}/a3/{t}__own.json", "fallback_key_in_file": draw_id[s],
                          "fallback_written_only_if": "alias subprocess returned non-zero (run_log.json: alias_rc != 0)", "run_log_key": draw_id[s]}
            else:
                per[s] = {"primary_file": f"{base}/a3/{t}__own.json", "primary_key_in_file": draw_id[s], "fallback_file": None, "fallback_key_in_file": None, "fallback_written_only_if": None, "run_log_key": draw_id[s]}
        return {"per_survivor": per, "other_files": [f"{base}/a3/run_log.json", f"{base}/a3/in/<tag>__alias|__own/<name>.jsonl.gz (relabelled copies of the draw)"]}

    def env() -> dict:
        return {"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"}

    wt = str(ROOT)
    uv = ["uv", "run", "--locked", "python"]
    ids_csv = ",".join(survivors)
    only_csv = ",".join(battery_name[s] for s in survivors)

    def cmd(argv: list[str], stdout: str, outputs: list[str], what: str) -> dict:
        return {"argv": argv, "cwd": wt, "env_set": env(), "env_note": "all other variables are inherited from the runner (PATH and HOME for uv); PYTHONPATH is not needed and not set",
                "stdout": stdout, "stderr": stdout.replace(".stdout.txt", ".stderr.txt"), "outputs_written": outputs, "what": what}

    def build_unit(unit: str, sk: str) -> dict:
        n = ITEMS["dry" if sk == "dry" else "run"]
        base = str(dry_root / unit / "dry") if sk == "dry" else f"{wt}/{RUN_ROOT_REL}/{unit}/seed{sk}"
        seed = seeds[unit][sk]
        draw_outs = [f"{base}/gen/{file_of[s]}" for s in survivors] + [f"{base}/gen/meta.json"]
        rule_outs = [f"{base}/rules/{file_of[s]}" for s in survivors]
        chain: list[dict] = []
        entry: dict = {"unit": unit, "seed_set": sk, "seed_role": "seed", "seed_integer": seed, "items_per_level": n, "run_dir": base, "chain": chain}
        if unit == "C1b":
            chain.append(cmd([*uv, "-m", "studies.m0.c1_fix4_battery", "--per-level", str(n), "--seed", str(seed), "--out", f"{base}/battery.json", "--only", only_csv, "--workers", str(WORKERS)],
                             f"{base}/battery.stdout.txt", [f"{base}/battery.json", f"{base}/battery.stdout.txt (progress lines and the summary table)"],
                             "c1_fix4_battery.py, as committed; --only gives the ids the battery knows (the five fix-4 lineages by RULE_ALIAS name)"))
            entry["must_contain"] = {f"{base}/battery.json": {"top_level_keys_are_survivor_ids": survivors}}
            entry["id_map"] = {"battery_only_name_to_survivor_id": {battery_name[s]: s for s in survivors}, "battery_json_key_to_survivor_id": {s: s for s in survivors},
                               "note": "the output is keyed by SWAP.get(name, name): the fix-4 id for the five, the id itself otherwise"}
            return entry
        if unit == "C1a":
            chain.append(cmd([*uv, "-m", "studies.m0.c1_fix4_draw", "--per-level", str(n), "--seed", str(seed), "--out", f"{base}/gen", "--ids", ids_csv, "--workers", str(WORKERS)],
                             f"{base}/draw.stdout.txt", [*draw_outs, f"{base}/draw.stdout.txt"], "c1_fix4_draw.py, as committed; --ids gives the 26 survivor ids"))
            s4s, s5s = S4, S5
        else:
            chain.append(cmd([*uv, F1, "--seed", str(seed), "--per-level", str(n), "--out", f"{base}/gen", "--ids", ids_csv, "--workers", str(WORKERS)],
                             f"{base}/draw.stdout.txt", [*draw_outs, f"{base}/draw.stdout.txt"], "final_c1/f1_draw.py, as committed; --ids gives the 26 survivor ids"))
            s4s, s5s = S4, S5
        chain.append(cmd([*uv, "-I", s4s, f"{base}/gen", f"{base}/rules"], f"{base}/s4.stdout.txt", [*rule_outs, f"{base}/s4.stdout.txt"], "audit4_c1/s4_rules_v2.py on the draw (no argv[3]: every file of the draw)"))
        chain.append(cmd([*uv, "-I", s5s, f"{base}/rules", f"{base}/s5.json"], f"{base}/s5.stdout.txt", [f"{base}/s5.json", f"{base}/s5.stdout.txt"], "audit4_c1/s5_analyse_v2.py on the rules"))
        a3o = a3_outputs(base, unit)
        if unit == "C1a":
            chain.append(cmd([*uv, "-m", "studies.m0.c1_fix4_a3_run", "--gen", f"{base}/gen", "--a3", A3, "--out", f"{base}/a3", "--timeout", str(SUBPROCESS_TIMEOUT)], f"{base}/a3run.stdout.txt",
                             [f"{base}/a3/", f"{base}/a3run.stdout.txt"], "c1_fix4_a3_run.py, as committed, with --timeout 3000 (the value of f3_a3_run.py:34)"))
        else:
            chain.append(cmd([*uv, F3, f"{base}/gen", A3, f"{base}/a3"], f"{base}/a3run.stdout.txt", [f"{base}/a3/", f"{base}/a3run.stdout.txt"],
                             "final_c1/f3_a3_run.py, as committed (timeout=3000 is a literal in the file)"))
            chain.append(cmd([*uv, "-I", F5B, f"{base}/gen", f"{base}/f5b.json"], f"{base}/f5b.stdout.txt", [f"{base}/f5b.json", f"{base}/f5b.stdout.txt"], "run copy of f5b_closed_forms_v2.py (S2 b)"))
            chain.append(cmd([*uv, "-I", F5, f"{base}/gen", f"{base}/f5.json"], f"{base}/f5.stdout.txt", [f"{base}/f5.json", f"{base}/f5.stdout.txt"], "run copy of f5_closed_forms.py (S2 b)"))
        entry["must_contain"] = {
            f"{base}/gen": {"files": [file_of[s] for s in survivors], "plus": ["meta.json"]},
            f"{base}/rules": {"files": [file_of[s] for s in survivors]},
            f"{base}/s5.json": {"top_level_keys_are_draw_ids": [draw_id[s] for s in survivors], "levels": "0 to 6 under each"},
            f"{base}/a3": {"per_survivor": a3o["per_survivor"], "run_log_keys_are_draw_ids": [draw_id[s] for s in survivors]},
        }
        entry["id_map"] = {"draw": maps_draw(), "s4_rules_file_name_to_survivor_id": {file_of[s]: s for s in survivors}, "s4_record_lid_to_survivor_id": {draw_id[s]: s for s in survivors},
                           "s5_json_key_to_survivor_id": {draw_id[s]: s for s in survivors},
                           "a3_file_name_and_key": {"file_name_pattern": "<draw file base>__alias.json | <draw file base>__own.json", "files_to_survivor_id": {f"{tag(s)}__alias.json": s for s in survivors if a3_ids[s]} | {f"{tag(s)}__own.json": s for s in survivors},
                                                   "key_in_alias_file_to_survivor_id": {a3_ids[s]: s for s in survivors if a3_ids[s]}, "key_in_own_file_to_survivor_id": {draw_id[s]: s for s in survivors},
                                                   "run_log_key_to_survivor_id": {draw_id[s]: s for s in survivors},
                                                   "table_used": "A3_ALIAS of c1_fix4_a3_run.py" if unit == "C1a" else "A3_OLD of final_c1/f3_a3_run.py"},
                           "ids_not_a_survivor_in_the_alias_tables_and_so_never_in_an_output": nonsurv_in_tables}
        if unit == "C1c":
            f5o = {f"{base}/f5b.json": cf_keys, f"{base}/f5.json": cf_keys}
            entry["must_contain"].update({p: {"top_level_keys_are_survivor_ids": k, "per_level_levels": "0 to 6 under per_level"} for p, k in f5o.items()})
            entry["id_map"]["closed_forms"] = {"json_key_fid_to_survivor_id": {s: s for s in cf_keys}, "base_file_name_opened_to_survivor_id": {cf_base[s] + ".jsonl.gz": s for s in cf_keys},
                                               "survivors_of_the_unit_not_in_FNS_so_not_scored_by_these_two_scripts": [s for s in survivors if s not in cf_keys],
                                               "removed_from_FNS_by_the_copies": [k for k in fns_keys(git_show(F5_ORIG)) if k not in cf_keys]}
        return entry

    plan = {"fragment": "C1", "commit_of_scripts": COMMIT, "worktree_root": wt, "survivor_list": survivors, "survivor_count": len(survivors),
            "items_per_level": ITEMS, "workers_flag_value": WORKERS, "subprocess_timeout_s_for_c1_fix4_a3_run": SUBPROCESS_TIMEOUT,
            "seed_source": "int.from_bytes(sha256('<base>|<unit>|seed')[:8], 'big'), asserted equal to part A of addendum1_rev6_fresh_run.out.txt for every set and unit here",
            "run_copies": {"studies/m0/fresh_run/c1/f5_closed_forms.py": "S2 (b)", "studies/m0/fresh_run/c1/f5b_closed_forms_v2.py": "S2 (b)"},
            "units": {}}
    for unit in ("C1a", "C1b", "C1c"):
        plan["units"][unit] = {sk: build_unit(unit, sk) for sk in ("dry", "1", "2", "3")}
    out_path.write_text(json.dumps(plan, indent=1, sort_keys=True) + "\n")
    print("wrote", out_path)


if __name__ == "__main__":
    main()
