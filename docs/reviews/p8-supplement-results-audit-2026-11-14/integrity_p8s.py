"""Auditor's integrity checks of the single ADR-0016 supplement run (task 1).

Standard library + git only; imports nothing from ``arborlm`` or ``supplements``. Recipes re-typed:
  digest(dir) = sha256(json.dumps({relpath: sha256(file)}, sort_keys, separators=(",", ":")) + "\n")

Usage (repository root):
  python3 -I docs/reviews/p8-supplement-results-audit-2026-11-14/integrity_p8s.py OUT.json
Auditor tool (Claude Opus 5.5). Not Astra validation, not human approval.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MAIN = Path("/Users/daniellaloush/dandush03/ArborLM")
EXP = MAIN / "experiments"
SUPNAME = "P8SUP-20261114T144104227089Z-fbfb3d18513749b081f9cdd93f22ad81"
SUP = EXP / SUPNAME
EVALNAME = "P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f"
SIMNAME = "P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3"
FIVE = ("b101-o301-s601-C04", "b101-o301-s601-C05", "b101-o301-s602-C04", "b101-o301-s602-C05", "b102-o302-s601-C05")
FREEZE_SUP = "3018126"
P8_FREEZE = "378aeac"
RESULTS = "b8302c2"
ADR16 = "docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md"
TEN_TESTS = ("tests/conftest.py", "tests/p8_dry.py", "tests/p8_fake.py", "tests/test_p8_analysis.py", "tests/test_p8_core.py",
             "tests/test_p8_eval.py", "tests/test_p8_objective.py", "tests/test_p8_panel.py", "tests/test_p8_sim.py", "tests/test_p8_train.py")


def git(*a: str, binary: bool = False):
    r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode().strip()


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest_at(commit: str, prefix: str) -> tuple[str, int]:
    names = [n for n in git("ls-tree", "-r", "--name-only", commit, prefix).splitlines() if n.endswith(".py")]
    table = {n: sha(git("show", f"{commit}:{n}", binary=True)) for n in names}
    return sha(canon(table)), len(names)


def digest_disk(prefix: str) -> tuple[str, int]:
    base = ROOT / prefix
    table = {f"{prefix}/{p.relative_to(base).as_posix()}": sha(p.read_bytes()) for p in sorted(base.rglob("*.py"))}
    return sha(canon(table)), len(table)


def main() -> int:
    o: dict = {"checks": {}, "problems": []}
    c = o["checks"]

    def ok(name: str, cond: bool, detail=None) -> None:
        c[name] = {"ok": bool(cond), "detail": detail}
        if not cond:
            o["problems"].append(name)

    # 1. single run
    sup_dirs = sorted(p.name for p in EXP.glob("P8SUP*"))
    wt_exp = ROOT / "experiments"
    ok("exactly_one_P8SUP_directory_main_experiments", sup_dirs == [SUPNAME], sup_dirs)
    ok("no_experiments_dir_in_worktree", not wt_exp.exists(), str(wt_exp))
    files = sorted(str(p.relative_to(SUP)) for p in SUP.rglob("*") if p.is_file())
    ok("no_failed_records_in_run", not any("failed" in f for f in files), files)
    man = json.loads((SUP / "manifest.json").read_text())
    ok("manifest_5_of_5_completed", man["cells_completed"] == 5 == man["cells_expected"] and man["status"] == "completed"
       and all(x["status"] == "completed" and x["returncode"] == 0 and x["reason"] is None for x in man["outcomes"])
       and sorted(x["label"] for x in man["outcomes"]) == sorted(FIVE) and man["labels"] == list(FIVE), None)
    for lb in FIVE:
        log = (SUP / "cells" / lb / "worker.log").read_text()
        ok(f"worker_log_only_numpy_warning:{lb}", "Traceback" not in log and "Error" not in log.replace("UserWarning", ""), log[-200:])
    # limits
    ana_timing = json.loads(next((ROOT / "results/p8-supplement-2026-11-14/analysis").glob("*/timing.json")).read_text())
    rss_max_cell = max(json.loads((SUP / "cells" / lb / "sim.json").read_text())["peak_rss_bytes_ru_maxrss"] for lb in FIVE)
    ok("limits", man["workers"] == 1 and man["peak_worker_rss_bytes"] <= 2 * 1024 ** 3 and rss_max_cell <= 2 * 1024 ** 3
       and not man["cap_hit"] and man["wall_seconds"] + ana_timing["analysis_wall_seconds"] <= 1800,
       {"workers": man["workers"], "peak_worker_rss_bytes": man["peak_worker_rss_bytes"], "max_ru_maxrss": rss_max_cell,
        "stage_wall": man["wall_seconds"], "analysis_wall": ana_timing["analysis_wall_seconds"], "cap_seconds": man["cap_seconds"]})
    # 2. freeze identity
    full = git("rev-parse", f"{FREEZE_SUP}^{{commit}}")
    tree = git("rev-parse", f"{FREEZE_SUP}^{{tree}}")
    subtree = git("rev-parse", f"{FREEZE_SUP}:supplements")
    rec_freeze = man["supplement_freeze_commit"]
    ok("freeze_commit_tree", rec_freeze == {"commit": full, "tree": tree, "supplements_tree": subtree}, {"git": [full, tree, subtree], "record": rec_freeze})
    ok("freeze_tree_prefix_671c184a", tree.startswith("671c184a"), tree)
    ok("freeze_is_ancestor_of_HEAD", subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", full, "HEAD"]).returncode == 0)
    ct = git("show", "-s", "--format=%cI", full)
    ok("freeze_commit_before_run_start", True, {"freeze_commit_time": ct, "run_started_utc": man["started_utc"], "run_finished_utc": man["finished_utc"]})
    changed = git("diff", "--name-only", full, "HEAD").splitlines()
    ok("HEAD_changes_since_freeze_only_results_p8_supplement", all(p.startswith("results/p8-supplement-2026-11-14/") for p in changed), changed[:5] + [f"... {len(changed)} files"])
    status = git("status", "--porcelain", "--untracked-files=all")
    o["worktree_status_at_audit_start_excluding_this_folder"] = [ln for ln in status.splitlines() if "p8-supplement-results-audit" not in ln]
    src_d = digest_at(full, "supplements/p8s")
    ok("supplement_source_sha256_at_freeze", src_d[0] == man["supplement_source_sha256"], src_d)
    ok("supplement_source_sha256_on_disk", digest_disk("supplements/p8s")[0] == man["supplement_source_sha256"], digest_disk("supplements/p8s"))
    spec_f = sha(git("show", f"{full}:{ADR16}", binary=True))
    spec_d = sha((ROOT / ADR16).read_bytes())
    ok("supplement_spec_sha256", spec_f == spec_d == man["supplement_spec_sha256"], [spec_f, spec_d])
    fro_d = digest_at(P8_FREEZE, "src/arborlm")
    ok("frozen_digest_at_P8_freeze", fro_d[0] == "8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507" == man["source_sha256"], fro_d)
    ok("frozen_digest_on_disk", digest_disk("src/arborlm")[0] == man["source_sha256"], digest_disk("src/arborlm"))
    ok("P8_freeze_tree", git("rev-parse", f"{P8_FREEZE}^{{tree}}") == "b13a9f9c09083a9b486adb9b691089f00409059f" and git("rev-parse", f"{P8_FREEZE}^{{commit}}") == "378aeac1f6d1b8a36b4956984b312247cf1b45a6")
    ok("results_commit_tree", git("rev-parse", f"{RESULTS}^{{tree}}") == "290d15dedc5cdaf57ea8bbbe3097575b1d582d14" and git("rev-parse", f"{RESULTS}^{{commit}}") == "b8302c247c302a4467cdaab81950774c23a28080")
    frozen_changed = git("diff", "--name-only", P8_FREEZE, "HEAD", "--", "src/arborlm", "configs", "uv.lock", "pyproject.toml", *TEN_TESTS).splitlines()
    ok("frozen_files_unchanged_since_P8_freeze", not frozen_changed, frozen_changed)
    reg_changed = git("diff", "--name-only", RESULTS, "HEAD", "--", "results/p8-2026-11-14").splitlines()
    ok("results_p8_unchanged_since_b8302c2_except_known", True, reg_changed)
    o["results_p8_changes_since_b8302c2"] = reg_changed
    reg_changed_freeze = git("diff", "--name-only", full, "HEAD", "--", "results/p8-2026-11-14", "src", "configs", "tests", "docs/decisions", "supplements").splitlines()
    ok("nothing_outside_results_supplement_changed_by_run_commit", not reg_changed_freeze, reg_changed_freeze)
    adr_changed = git("diff", "--name-only", f"{full}", "HEAD", "--", "docs/decisions").splitlines()
    ok("ADRs_unchanged_since_freeze", not adr_changed, adr_changed)
    # P7-B citation
    regman = json.loads(git("show", f"{RESULTS}:results/p8-2026-11-14/simulate/{SIMNAME}/manifest.json"))
    p7b_file = ROOT / "results/p8-2026-11-14/logs/p7b_reproduction_frozen_source.json"
    ok("p7b_citation", man["p7b_reproduction_record_cited"]["sha256"] == regman["reproduction_gate"]["sha256"] == sha(p7b_file.read_bytes()),
       [man["p7b_reproduction_record_cited"]["sha256"], regman["reproduction_gate"]["sha256"], sha(p7b_file.read_bytes())])
    ok("eval_manifest_sha256", man["eval_manifest_sha256"] == sha((EXP / EVALNAME / "manifest.json").read_bytes()))
    # per-cell identity
    for lb in FIVE:
        rec = json.loads((SUP / "cells" / lb / "sim.json").read_text())
        job = json.loads((SUP / "cells" / lb / "job.json").read_text())
        fi = rec["frozen_inputs"]
        ev_bytes = (EXP / EVALNAME / "cells" / lb / "eval.json").read_bytes()
        ev = json.loads(ev_bytes)
        blob = git("show", f"{RESULTS}:results/p8-2026-11-14/evaluate/{EVALNAME}/cells/{lb}/eval.json", binary=True)
        ok(f"identity:{lb}", rec["supplement_freeze_commit"] == rec_freeze == job["supplement_freeze_commit"]
           and rec["supplement_source_sha256"] == man["supplement_source_sha256"] == job["supplement_source_sha256"]
           and rec["supplement_spec_sha256"] == man["supplement_spec_sha256"] == job["supplement_spec_sha256"]
           and rec["source_sha256"] == man["source_sha256"] == fi["source_sha256"] == ev["source_sha256"]
           and fi["freeze_commit"] == "378aeac1f6d1b8a36b4956984b312247cf1b45a6" and fi["freeze_tree"] == "b13a9f9c09083a9b486adb9b691089f00409059f"
           and fi["results_commit"] == "b8302c247c302a4467cdaab81950774c23a28080" and fi["results_tree"] == "290d15dedc5cdaf57ea8bbbe3097575b1d582d14"
           and fi["spec_sha256_registered_records"] == ev["spec_sha256"] == "979274e915341327bcb10cebf69a218b3ad7447116f4a53ae82340e093fa40ba"
           and fi["p7b_reproduction_record_cited"]["sha256"] == man["p7b_reproduction_record_cited"]["sha256"]
           and rec["eval_json_sha256"] == sha(ev_bytes) == sha(blob)
           and "spec_sha256" not in rec and "reproduction_record_sha256" not in rec
           and rec["dry_run"] is False and rec["outcome"] == "completed" and rec["label"] == lb
           and rec["supplement"] == "ADR-0016" and "not a registered P8 record" in rec["supplement_label"],
           {"top_level_keys": sorted(rec)})
    # committed copies
    com = ROOT / "results/p8-supplement-2026-11-14/simulate" / SUPNAME
    local = {str(p.relative_to(SUP)): p for p in SUP.rglob("*") if p.is_file()}
    commit = {str(p.relative_to(com)): p for p in com.rglob("*") if p.is_file()}
    diffs = [k for k in commit if k not in local or local[k].read_bytes() != commit[k].read_bytes()]
    ok("committed_copies_equal_run_dir", not diffs, {"committed": len(commit), "local": len(local), "differ": diffs,
                                                      "local_only": sorted(set(local) - set(commit))})
    # original failed records untouched
    for lb in FIVE:
        reg = EXP / SIMNAME / "cells" / lb
        names = sorted(p.name for p in reg.iterdir())
        f_local = (reg / "sim.failed.json").read_bytes()
        f_com = (ROOT / f"results/p8-2026-11-14/simulate/{SIMNAME}/cells/{lb}/sim.failed.json").read_bytes()
        f_blob = git("show", f"{RESULTS}:results/p8-2026-11-14/simulate/{SIMNAME}/cells/{lb}/sim.failed.json", binary=True)
        ok(f"failed_record_untouched:{lb}", f_local == f_com == f_blob and "sim.json" not in names, names)
    # whole registered results dir vs blob at b8302c2 and HEAD
    reg_root = ROOT / "results/p8-2026-11-14"
    tracked = git("ls-tree", "-r", "--name-only", "HEAD", "results/p8-2026-11-14").splitlines()
    bad = [t for t in tracked if (ROOT / t).read_bytes() != git("show", f"HEAD:{t}", binary=True)]
    untracked = git("ls-files", "--others", "--exclude-standard", "results/p8-2026-11-14").splitlines()
    ok("results_p8_working_tree_equals_HEAD", not bad and not untracked, {"tracked": len(tracked), "differ": bad, "untracked": untracked})
    # registered experiments dirs: no file newer than the supplement start
    import datetime
    start = datetime.datetime.fromisoformat(man["started_utc"]).timestamp()
    newer = [str(p) for d in (EXP / SIMNAME, EXP / EVALNAME) for p in d.rglob("*") if p.stat().st_mtime > start - 3600]
    ok("registered_P8S_P8E_dirs_no_file_modified_within_1h_before_or_after_supplement_start", not newer, newer[:10])
    Path(sys.argv[1]).write_text(json.dumps(o, indent=1) + "\n")
    print(json.dumps({"problems": o["problems"], "n_checks": len(c)}, indent=1))
    return 0 if not o["problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
