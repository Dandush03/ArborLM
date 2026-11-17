# Re-run of the re-check's demonstrations against the fixed code, in a throwaway frozen clone (argv[1]) on test seeds only.
# Every command is a subprocess of the clone's code with the worktree's interpreter; outputs are exit codes and stderr tails.
import json, os, subprocess, sys, tempfile, shutil
from pathlib import Path
CLONE = Path(sys.argv[1]); PY = sys.argv[2]; OUT = Path(sys.argv[3])
env0 = {k: v for k, v in os.environ.items() if k not in ("PYTEST_CURRENT_TEST", "P10S0_STAGE_TOKEN", "P10S0_E2E_CLONE")}
env0["PYTHONPATH"] = str(CLONE)
def run(argv, env=None, cwd=CLONE):
    p = subprocess.run([PY, "-m", "studies.p10s0.stages", *argv], cwd=cwd, env={**env0, **(env or {})}, capture_output=True, text=True, timeout=600)
    err = [l for l in p.stderr.splitlines() if "Warning" not in l and "_conversion_method" not in l]
    return {"argv": argv, "rc": p.returncode, "stderr_tail": err[-3:], "stdout_tail": p.stdout.splitlines()[-2:]}
freeze = subprocess.run(["git", "rev-parse", "HEAD"], cwd=CLONE, capture_output=True, text=True).stdout.strip()
tmp = Path(tempfile.mkdtemp(prefix="p10s0-demo-", dir=str(OUT.parent.parent / "tmp")))
res = {"freeze_commit_of_clone": freeze}
R = tmp / "run"; R.mkdir()
# a. typed registered worker, no token
res["a_typed_train_worker_no_token"] = run(["work", "train", "--mode", "registered", "--run-dir", str(R), "--freeze-commit", freeze, "--labels", "WX-WX-A1-2K4K-d01-j0"])
# b. forged running stage: label not among its tasks; label among tasks but not in the frozen matrix; token for another stage kind
st = R / "train-q1"; st.mkdir()
(st / "RUNNING.json").write_text(json.dumps({"stage": "train-q1", "nonce": "n0nce", "task_labels": ["x"], "cells": ["Q1-A0-2K4K-d01-j0", "Q1-A0-2K4K-d99-j0"], "started_utc": "t"}))
tok = {"P10S0_STAGE_TOKEN": "train-q1:n0nce"}
res["b1_label_not_in_stage"] = run(["work", "train", "--mode", "registered", "--run-dir", str(R), "--freeze-commit", freeze, "--labels", "WX-WX-A1-2K4K-d01-j0"], tok)
res["b2_label_in_stage_not_in_matrix"] = run(["work", "train", "--mode", "registered", "--run-dir", str(R), "--freeze-commit", freeze, "--labels", "Q1-A0-2K4K-d99-j0"], tok)
res["b3_token_wrong_kind"] = run(["work", "evaluate", "--mode", "registered", "--run-dir", str(R), "--freeze-commit", freeze, "--labels", "Q1-A0-2K4K-d01-j0"], tok)
res["b4_wrong_nonce"] = run(["work", "train", "--mode", "registered", "--run-dir", str(R), "--freeze-commit", freeze, "--labels", "Q1-A0-2K4K-d01-j0"], {"P10S0_STAGE_TOKEN": "train-q1:other"})
res["b5_valid_forged_token_in_matrix_reaches_registered_state"] = run(["work", "train", "--mode", "registered", "--run-dir", str(R), "--freeze-commit", freeze, "--labels", "Q1-A0-2K4K-d01-j0"], tok)
# generation worker without token
res["b6_generate_worker_no_token"] = run(["work", "generate", "--mode", "registered", "--draw", "1", "--run-dir", str(R)])
# f. typed caps / overrides in registered mode
res["f1_generate_typed_cap"] = run(["generate", "--mode", "registered", "--draw", "1", "--run-dir", str(tmp / "g"), "--generation-cap-from-config", "--i-understand-freeze-time", "--stage-cap-seconds", "5"])
res["f2_registered_q1_typed_cap"] = run(["registered", "q1", "--run-dir", str(R), "--freeze-commit", freeze, "--caps", "studies/p10s0/freeze/stage_caps.json", "--stage-cap-seconds", "5"])
res["f3_train_mode_registered"] = run(["train", "--block", "q1", "--mode", "registered", "--run-dir", str(R)])
# d. set-generation-cap with DRY / check / wrong-stage manifests (on a scratch copy of the config: --repo points at a temporary repo copy)
repo = tmp / "repo"; (repo / "configs").mkdir(parents=True); shutil.copy(CLONE / "configs/p10s0_qualification.toml", repo / "configs/p10s0_qualification.toml")
base = {"study": "P10S0", "schema": 1, "kind": "stage_manifest", "status": "COMPLETE", "tasks": [{"seconds": 40.0}]}
for name, extra in {"dry": {"stage": "generate-p10s0-rehearsal", "mode": "dry"}, "check_mode": {"stage": "generate-p10s0-check", "mode": "check"}, "rehearsal_mode_wrong_stage": {"stage": "generate-p10s0-check", "mode": "rehearsal"}, "ok_rehearsal": {"stage": "generate-p10s0-rehearsal", "mode": "rehearsal"}}.items():
    m = tmp / f"m_{name}.json"; m.write_text(json.dumps({**base, **extra}))
    res[f"d_set_generation_cap_{name}"] = run(["set-generation-cap", "--repo", str(repo), "--generate-manifest", str(m)])
res["d_config_after_ok"] = (repo / "configs/p10s0_qualification.toml").read_text().split("[generation]")[1].split("[resources]")[0].strip().splitlines()
res["d_cap_hours_after_ok"] = [l for l in (repo / "configs/p10s0_qualification.toml").read_text().splitlines() if l.startswith("cap_hours")]
# h. freeze-plan --test-profile without the e2e environment
res["h_freeze_plan_test_profile_without_e2e_env"] = run(["freeze-plan", "--run-dir", str(R), "--arm-selection", "studies/p10s0/freeze/arm_selection.json", "--projection", "/nonexistent.json", "--out", str(tmp / "plan.json"), "--test-profile"])
# g. NEW: rehearse-cell worker typed with --mode registered (no guard) on a TEST-PROFILE run dir with a stand-in draw plan naming test sets
T = tmp / "trun"; T.mkdir(); (T / "TEST_PROFILE").write_text("test\n")
sys.path.insert(0, str(CLONE)); from studies.p10s0 import core  # only to write stand-in envelope records into my temp dir
names = core.set_names("test"); draws = core.draw_names("test")
core.write_record(T / "draw_plan.json", {**core.envelope("draw_plan"), "ok": True, "seed_set_of": {str(k): draws[k - 1] for k in range(1, core.N_DRAWS + 1)}, "replacements": {}, "labels": {}, "reason": None, "g1": {}})
for n in names:
    (T / "draws" / n).mkdir(parents=True)
    core.write_record(T / "draws" / n / "data_manifest.json", {**core.envelope("data_manifest"), "seed_set": n, "g1_passed": True, "sha256s": {}})
res["g_rehearse_cell_mode_registered_test_profile"] = run(["work", "rehearse-cell", "--mode", "registered", "--draw", "1", "--run-dir", str(T), "--item", "A0,2K/4K,main"])
res["g_written"] = sorted(str(p.relative_to(T)) for p in T.rglob("*.json") if "rehearsal" in str(p))
if res["g_written"]:
    rec = json.loads((T / res["g_written"][0]).read_text()); res["g_record_seed_set"] = rec.get("seed_set"); res["g_record_mode"] = rec.get("mode")
res["tmpdir"] = str(tmp)
json.dump(res, sys.stdout, indent=1)
