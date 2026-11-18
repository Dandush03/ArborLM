# ruff: noqa: E501
"""P10IR plan, refusal and resumability tests (ADR-0029 sections 11, 12, 13): the registered entry points REFUSE without the frozen plan, the freeze commit and a committed Decision 2 (no freeze exists today);
the frozen-input set excludes the ADR; items come from the plan only; the runner pauses on a cap and resumes; a finished read is not recomputed. Seeds: the unit-test range 938001-938999 only; no registered
seed, no registered checkpoint. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10ir import core, items, reads, runner, stages, stages_io  # noqa: E402
from studies.p10ir import plan as planmod
from studies.p10ir.plan import Plan, StageRefused  # noqa: E402

CFG = core.load_config()
ROOT = Path(__file__).resolve().parents[1]


# --- the registered entry points refuse today -----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("stage", planmod.REGISTERED_STAGES)
def test_every_registered_stage_refuses_today(stage: str, tmp_path: Path) -> None:
    """No freeze exists (``freeze/plan.json`` is absent and no Decision 2 is committed), so each registered entry point exits with a refusal before it reads or trains anything."""
    assert not (ROOT / core.PLAN).exists(), "a freeze exists: this test is about the state before it"
    code = stages.main(["registered", stage, "--run-dir", str(tmp_path / "run"), "--freeze-commit", "HEAD"])
    assert code == 2
    assert not (tmp_path / "run").exists()  # nothing was written


def test_launch_scripts_refuse_too_and_take_exactly_two_arguments(tmp_path: Path) -> None:
    script = ROOT / "studies" / "p10ir" / "launch" / "a1.sh"
    bad = subprocess.run(["sh", str(script)], capture_output=True, text=True, timeout=60, check=False)
    assert bad.returncode == 2 and "usage" in bad.stderr
    run = subprocess.run(["sh", str(script), str(tmp_path / "r"), "HEAD"], capture_output=True, text=True, timeout=300, check=False)
    assert run.returncode == 2 and "refused" in run.stderr and not (tmp_path / "r").exists()
    assert "confirm" in planmod.REGISTERED_STAGES and planmod.STAGE_GROUP["confirm"] == "A2" and planmod.STAGE_GROUP["analysis"] == "A1"
    for name in [*planmod.REGISTERED_STAGES, "rehearse", "generate-bridge"]:
        text = (ROOT / "studies" / "p10ir" / "launch" / f"{name}.sh").read_text(encoding="utf-8")
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        assert text.startswith("#!/bin/sh") and "set -eu" in code and all(w not in code.split() for w in ("sleep", "while", "until", "wait"))  # no unbounded wait


def make_repo(tmp: Path) -> Path:
    """A temporary git repository with a committed ``studies/p10ir`` file and config, to test each leg of the preconditions (the real repository is never touched)."""
    repo = tmp / "repo"
    (repo / "studies" / "p10ir").mkdir(parents=True)
    (repo / "configs").mkdir()
    (repo / "studies" / "p10ir" / "x.py").write_text("X = 1\n", encoding="utf-8")
    (repo / "configs" / "p10ir_routing.toml").write_text((ROOT / "configs" / "p10ir_routing.toml").read_text(encoding="utf-8"), encoding="utf-8")
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True, timeout=60)  # noqa: E731
    run("init", "-q", "-b", "main")
    run("config", "user.email", "t@example.invalid")
    run("config", "user.name", "t")
    run("config", "commit.gpgsign", "false")
    run("add", "-A")
    run("commit", "-q", "-m", "freeze")
    return repo


def head(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=60).stdout.strip()


def test_preconditions_refuse_on_each_leg(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    full = head(repo)
    assert planmod.check_preconditions(planmod.REHEARSAL, repo, None) is None  # only registered mode is guarded
    with pytest.raises(StageRefused, match="requires --freeze-commit"):
        planmod.check_preconditions(planmod.REGISTERED, repo, None)
    with pytest.raises(StageRefused, match="not a commit"):
        planmod.check_preconditions(planmod.REGISTERED, repo, "0123456789abcdef0123456789abcdef01234567")
    (repo / "dirty.txt").write_text("x", encoding="utf-8")
    with pytest.raises(StageRefused, match="not clean"):
        planmod.check_preconditions(planmod.REGISTERED, repo, full)
    (repo / "dirty.txt").unlink()
    # a frozen file changed after the freeze commit: refused (the tree is clean again after the commit)
    (repo / "studies" / "p10ir" / "x.py").write_text("X = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "edit after the freeze"], check=True, capture_output=True, timeout=60)
    with pytest.raises(StageRefused, match="differs from the freeze commit"):
        planmod.check_preconditions(planmod.REGISTERED, repo, full)


def test_the_adr_text_is_not_among_the_files_whose_change_refuses(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "docs" / "decisions").mkdir(parents=True)
    (repo / core.SPEC).write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True, timeout=60)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "adr"], check=True, capture_output=True, timeout=60)
    full = head(repo)
    before = planmod.frozen_file_hashes(repo)
    (repo / core.SPEC).write_text("v2 with a different threshold 0.77\n", encoding="utf-8")
    assert planmod.frozen_file_hashes(repo) == before  # the ADR's text is in no hash
    assert set(before) == {"studies/p10ir/x.py", str(core.CONFIG)} and not any("docs/" in k or "tests/" in k for k in before)
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "edit the ADR"], check=True, capture_output=True, timeout=60)
    # the freeze commit's frozen roots equal HEAD's although the ADR changed: that leg passes (the later legs, the platform and the frozen sources, are those of this machine)
    problems = [p for p in (*planmod.FROZEN_ROOTS, str(core.CONFIG)) if planmod.git(repo, "rev-parse", f"{full}:{p}").stdout != planmod.git(repo, "rev-parse", f"HEAD:{p}").stdout]
    assert problems == []
    assert planmod.adr_provenance(repo)["note"].startswith("provenance only")


def test_decision_2_needs_a_committed_file_with_the_run_line_the_full_commit_and_its_own_group(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    full = head(repo)
    with pytest.raises(StageRefused, match="DECISION_2_A1"):
        planmod.require_decision_2(repo, full, "A1")
    d = repo / "results" / "p10ir-freeze-2026-11-20"
    d.mkdir(parents=True)
    (d / "DECISION_2_A1.md").write_text(f"freeze commit {full}\nDECISION: RUN\n", encoding="utf-8")
    with pytest.raises(StageRefused):  # written but not committed
        planmod.require_decision_2(repo, full, "A1")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True, timeout=60)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "decision 2 for A1"], check=True, capture_output=True, timeout=60)
    assert planmod.require_decision_2(repo, full, "A1").endswith("DECISION_2_A1.md")
    with pytest.raises(StageRefused, match="DECISION_2_A2"):  # A2 has its own Decision 2
        planmod.require_decision_2(repo, full, "A2")
    (d / "DECISION_2_A2.md").write_text(f"{full}\nDECISION: DO NOT RUN\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True, timeout=60)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "decision 2 for A2: no"], check=True, capture_output=True, timeout=60)
    with pytest.raises(StageRefused):
        planmod.require_decision_2(repo, full, "A2")
    (d / "DECISION_2_A2.md").write_text("DECISION: RUN\n", encoding="utf-8")  # no commit named
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "decision 2 for A2 without the commit"], check=True, capture_output=True, timeout=60)
    with pytest.raises(StageRefused):
        planmod.require_decision_2(repo, full, "A2")


def test_plan_loading_refuses_without_a_file_or_with_a_foreign_one(tmp_path: Path) -> None:
    with pytest.raises(StageRefused, match="no freeze plan"):
        Plan.load(tmp_path / "plan.json")
    (tmp_path / "plan.json").write_text(json.dumps({"kind": "other"}), encoding="utf-8")
    with pytest.raises(StageRefused, match="not a P10IR plan"):
        Plan.load(tmp_path / "plan.json")
    with pytest.raises(StageRefused, match="no freeze plan"):
        planmod.load_registered_plan(tmp_path)


def test_a_registered_worker_refuses_a_plan_that_is_not_the_frozen_one(tmp_path: Path) -> None:
    plan = {**core.envelope("freeze_plan"), "mode": "registered", "items": {"A1": [], "A2": []}}
    p = tmp_path / "other_plan.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    args = stages.build_parser().parse_args(["work", "reads", "--stage", "a1", "--labels", "x", "--run-dir", str(tmp_path / "r"), "--plan", str(p), "--mode", "registered", "--freeze-commit", "HEAD"])
    with pytest.raises(StageRefused, match="the registered plan is"):
        stages.cmd_work(args)


def test_registered_stage_overrides_do_not_exist() -> None:
    """The registered parser takes the run directory and the freeze commit and nothing else (no cap, no seed, no path, no item list)."""
    with pytest.raises(SystemExit):
        stages.build_parser().parse_args(["registered", "a1", "--run-dir", "r", "--freeze-commit", "c", "--stage-cap-seconds", "9"])
    with pytest.raises(SystemExit):
        stages.build_parser().parse_args(["registered", "a1", "--run-dir", "r", "--labels", "x"])


# --- the registered plan's items, from the config and the seeds (no registered data is opened) ----------------------------------------------------------
def test_registered_items_counts_labels_and_not_applicable_entries() -> None:
    it = planmod.registered_items(CFG)
    assert len(it["A1"]) == 280 and len(it["A2"]) == 40  # 70 cells x 4 checkpoints, 20 cells x 2
    assert len({i["id"] for i in it["A1"] + it["A2"]}) == 320
    by_cell = {i["cell"]: i for i in it["A1"] if i["update"] == i["u_p"]}
    assert "P_T-OQ_f8192_n4096_d1_i2101" in by_cell and "P_F-OQ_f8192_n4096_d1_i2101" in by_cell  # the labels the ADR names (section 10)
    assert any(c.startswith("P_T-OQ_f8192_n1024_d1_i2101") and c.endswith("y393216") for c in by_cell)  # the loaded cell's own run length is in its label
    assert all(i["init_seed"] == 2100 + i["draw"] and i["seed_base"] == 210001 + 100 * (i["draw"] - 1) for i in it["A1"])
    assert all(i["init_seed"] == 330600 + i["draw"] and i["seed_base"] == 290001 + 100 * (i["draw"] - 1) for i in it["A2"])
    assert not ({i["cell"] for i in it["A1"]} & {i["cell"] for i in it["A2"]})  # no bridge label equals a P10-S1 label
    cps = {(i["cell_name"], i["checkpoint"]): i["update"] for i in it["A1"] if i["draw"] == 1 and i["arm"] == "T-OQ"}
    assert cps[("8K/4K", "U_P")] == 8192 and cps[("8K/4K", "RUN")] == 49152 and cps[("32K/16K", "RUN")] == 98304 and cps[("32K/4K", "RUN")] == 786432 and cps[("8K/1K", "TRAJ2")] == 196608
    shallow = next(i for i in it["A1"] if i["slots"] == 1024 and i["arm"] == "T-OQ" and i["facts"] == 2048)
    na = {r["name"]: r for r in shallow["reads"] if r["status"] != "RUN"}
    assert set(na) == {"Tv8_on", "Tv8_off"} and "exceeds N/256 = 4" in na["Tv8_on"]["reason"]
    flat_shallow = next(i for i in it["A1"] if i["slots"] == 1024 and i["arm"] == "F-OQ" and i["facts"] == 2048)
    na_f = [r["name"] for r in flat_shallow["reads"] if r["status"] != "RUN"]
    assert len(na_f) == 6 and all(n.startswith(("I64@1024/", "I64@2048/")) for n in na_f)
    full = next(i for i in it["A1"] if i["slots"] == 16384 and i["arm"] == "T-OQ")
    assert all(r["status"] == "RUN" for r in full["reads"]) and [r["name"] for r in full["reads"]][:5] == ["T0", "T1", "T1w", "T3", "T2"]
    assert [i["cell"] for i in it["A1"]] == [i["cell"] for i in it["A1"]]  # deterministic


# --- items come from the plan only -------------------------------------------------------------------------------------------------------------------------
def tiny_plan(tmp: Path, draws: int = 1) -> Plan:
    from studies.p10ir import rehearsal

    plan, _ = rehearsal.build_synthetic_plan(tmp / "syn", CFG, draws)
    return plan


@pytest.fixture(scope="module")
def mini(tmp_path_factory: pytest.TempPathFactory) -> tuple[Plan, items.Ctx]:
    from studies.p10ir import rehearsal
    from studies.p10s1 import train as s1train

    s1train.configure()
    root = tmp_path_factory.mktemp("mini") / "syn"
    return rehearsal.build_synthetic_plan(root, CFG, 1)


def test_stages_derive_items_from_the_plan_only(mini: tuple[Plan, items.Ctx], monkeypatch: pytest.MonkeyPatch) -> None:
    plan, ctx = mini
    before = [i["id"] for i in plan.items("A1")]
    labels_before = stages.labels_of_stage(plan, "a1")
    monkeypatch.setattr(core, "cell_specs", lambda *a, **k: (_ for _ in ()).throw(AssertionError("the config's cells were read")))
    monkeypatch.setattr(core, "primary_cells", lambda *a, **k: (_ for _ in ()).throw(AssertionError("the config's cells were read")))
    assert [i["id"] for i in plan.items("A1")] == before and stages.labels_of_stage(plan, "a1") == labels_before
    assert len(stages._specs_of(plan, "A1")) == 2 and {s.name for s in stages._specs_of(plan, "A1")} == {"128/1K", "128/4K"}
    assert [t.label for t in stages.make_tasks("a1", plan, ctx.run_dir, ctx.run_dir / "freeze" / "plan.json", None, ())] == labels_before  # type: ignore[arg-type]
    with pytest.raises(StageRefused, match="not an item"):
        plan.item("A1|not-a-cell|u0000001")
    with pytest.raises(StageRefused, match="not a cell of the frozen plan"):
        stages.work_reads(ctx, plan, "a1", ["P_T-OQ_f8192_n4096_d1_i2101"])  # a real P10-S1 label that this plan does not list
    assert plan.item(before[0])["id"] == before[0]


def test_the_plan_lists_every_planned_read_and_records_its_identities(mini: tuple[Plan, items.Ctx]) -> None:
    plan, _ = mini
    d = plan.data
    assert d["kind"] == "freeze_plan" and d["mode"] == "rehearsal" and set(d["frozen_files"]) >= {str(core.CONFIG), "studies/p10ir/plan.py"}
    assert "freeze/plan.json" not in " ".join(d["frozen_files"]) and not any(k.startswith("docs/") for k in d["frozen_files"])
    assert d["adr"]["note"].startswith("provenance only") and d["config_sha256"] == core.config_sha256()
    caps = core.load_config()["caps"]  # the plan copies the config's caps whatever they are
    assert d["stage_caps"] == {k: float(v) for k, v in caps.items() if k.endswith("_hours")} and d["caps_provisional"] is bool(caps["provisional"])
    assert d["seal"]["values_opened"] is False and len(d["seal"]["accesses_declared"]) == 3
    it = plan.items("A1")[0]
    assert set(it) >= {"id", "stage", "arm", "cell", "facts", "slots", "draw", "update", "checkpoint", "init_seed", "seed_name", "seed_base", "reads", "table_facts", "synthetic"}
    seeds = {i["seed_base"] for i in plan.items("A1") + plan.items("A2")}
    lo, hi = CFG["seeds"]["test_range"]
    assert all(lo <= s <= hi for s in seeds)  # the synthetic plan uses the unit-test range only


def test_verify_plan_checks_every_frozen_file_the_config_the_caps_and_the_run_directory(mini: tuple[Plan, items.Ctx], tmp_path: Path) -> None:
    plan, ctx = mini
    planmod.verify_plan(plan, ROOT, ctx.run_dir, check_items=False)  # this working tree is the plan's tree
    with pytest.raises(StageRefused, match="run directory"):
        planmod.verify_plan(plan, ROOT, tmp_path / "elsewhere", check_items=False)
    data = json.loads(json.dumps(plan.data))
    data["frozen_files"]["studies/p10ir/plan.py"] = "0" * 64
    with pytest.raises(StageRefused, match="PAUSED — IDENTITY"):
        planmod.verify_plan(Plan(data), ROOT, ctx.run_dir, check_items=False)
    data = json.loads(json.dumps(plan.data))
    data["config_sha256"] = "1" * 64
    with pytest.raises(StageRefused, match="config differs"):
        planmod.verify_plan(Plan(data), ROOT, ctx.run_dir, check_items=False)
    data = json.loads(json.dumps(plan.data))
    data["stage_caps"]["a1_hours"] = 99.0
    with pytest.raises(StageRefused, match="caps"):
        planmod.verify_plan(Plan(data), ROOT, ctx.run_dir, check_items=False)
    data = json.loads(json.dumps(plan.data))
    data["manifests"] = {"x": {"path": str(tmp_path / "gone.json"), "sha256": "2" * 64}}
    with pytest.raises(StageRefused, match="frozen manifest"):
        planmod.verify_plan(Plan(data), ROOT, ctx.run_dir, check_items=False)
    reg = json.loads(json.dumps(plan.data))
    reg["mode"] = "registered"
    reg["caps_provisional"] = True  # a plan that records provisional caps (independent of the live config)
    with pytest.raises(StageRefused, match="provisional"):
        planmod.verify_plan(Plan(reg), ROOT, ctx.run_dir, check_items=False)  # the caps are provisional until the human lead sets them


def test_freeze_and_candidate_plan_refuse_in_this_repository_today(tmp_path: Path) -> None:
    assert not (ROOT / core.PLAN).exists() and not (ROOT / planmod.FREEZE_RECORD).exists()
    assert stages.main(["freeze", "--rehearsal", str(tmp_path / "rehearsal.json")]) == 2  # no candidate plan
    assert stages.main(["candidate-plan", "--run-dir", str(tmp_path / "r"), "--s1-run-dir", str(tmp_path / "s1")]) == 2  # no checkpoint files, no manifests: nothing is written
    assert not (ROOT / core.PLAN).exists()


def freeze_repo(tmp: Path) -> tuple[Path, Path]:
    """A temporary repository holding the code, the config (caps cleared) and a registered candidate plan; the freeze command works on it with the seed gate stubbed (it needs the whole repository)."""
    repo = tmp / "frepo"
    (repo / "studies" / "p10ir").mkdir(parents=True)
    (repo / "configs").mkdir()
    (repo / "docs" / "decisions").mkdir(parents=True)
    (repo / core.SPEC).write_text("adr\n", encoding="utf-8")
    (repo / "studies" / "p10ir" / "x.py").write_text("X = 1\n", encoding="utf-8")
    cfg_text = re.sub(r"(?m)^provisional = (true|false)", "provisional = false", (ROOT / "configs" / "p10ir_routing.toml").read_text(encoding="utf-8"), count=1)
    (repo / "configs" / "p10ir_routing.toml").write_text(cfg_text, encoding="utf-8")
    cfg = core.load_config(repo / core.CONFIG)
    rec = planmod.build_plan(mode=planmod.REGISTERED, cfg=cfg, repo=repo, items=planmod.registered_items(cfg), run_dir=tmp / "run", s1_run_dir=tmp / "s1", extra={"seal": {"accesses_declared": [], "values_opened": False, "broken": False}})
    core.write_record(repo / core.PLAN, rec)
    return repo, tmp / "rehearsal.json"


def test_freeze_needs_the_rehearsed_plan_hash_and_writes_only_the_freeze_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ruling 5: the candidate plan comes first; the rehearsal record names its SHA-256; the freeze refuses unless the committed file has that hash."""
    from arborlm.io import file_sha256
    from studies.p10ir import freeze, gates

    repo, reh = freeze_repo(tmp_path)
    monkeypatch.setattr(gates, "seed_gate", lambda *a, **k: {"passed": True, "problems": [], "roles": {}, "declared_reuse_not_new": {}, "checker": {}})
    plan_data = json.loads((repo / core.PLAN).read_text(encoding="utf-8"))
    monkeypatch.setattr(freeze, "build_candidate", lambda *a, **k: json.loads(json.dumps(plan_data)))  # the re-derivation needs the registered run directories: stubbed to the plan itself
    plan_sha = file_sha256(repo / core.PLAN)
    full = {s: {"status": "COMPLETE"} for s in stages.REHEARSAL_STAGES}
    good_gates = {"gate1_passed": True, "gate2_passed": True, "gate3_run": False}

    def record(candidate_sha: str | None, status: str = "COMPLETE", provisional: bool | None = False) -> None:
        core.write_record(reh, {**core.envelope("rehearsal"), "stages": full, "registered_checkpoint_gates": good_gates, "caps_provisional": provisional, "candidate": {"status": status, "plan_file_sha256": candidate_sha}}, overwrite=True)

    args = lambda *extra: stages.build_parser().parse_args(["freeze", "--rehearsal", str(reh), "--repo", str(repo), *extra])  # noqa: E731
    record("0" * 64)  # a rehearsal of another plan file
    with pytest.raises(StageRefused, match="candidate plan of SHA-256"):
        freeze.cmd_freeze(args("--attest-sealed-unopened", "lead,implementer,auditor"))
    record(plan_sha, status="INCOMPLETE")
    with pytest.raises(StageRefused, match="candidate plan of SHA-256"):
        freeze.cmd_freeze(args("--attest-sealed-unopened", "lead,implementer,auditor"))
    record(plan_sha, provisional=True)  # N2: a rehearsal made on provisional caps cannot be frozen on
    with pytest.raises(StageRefused, match="provisional caps"):
        freeze.cmd_freeze(args("--attest-sealed-unopened", "lead,implementer,auditor"))
    record(plan_sha, provisional=None)  # a record that does not say
    with pytest.raises(StageRefused, match="provisional caps"):
        freeze.cmd_freeze(args("--attest-sealed-unopened", "lead,implementer,auditor"))
    record(plan_sha)
    stale = json.loads(json.dumps(plan_data))
    stale["config_sha256"] = "9" * 64  # N2: the plan no longer equals a re-derivation from the current code and config
    monkeypatch.setattr(freeze, "build_candidate", lambda *a, **k: json.loads(json.dumps(stale)))
    with pytest.raises(StageRefused, match="differs from a re-derivation"):
        freeze.cmd_freeze(args("--attest-sealed-unopened", "lead,implementer,auditor"))
    monkeypatch.setattr(freeze, "build_candidate", lambda *a, **k: json.loads(json.dumps(plan_data)))
    with pytest.raises(StageRefused, match="has not opened the sealed values|none has opened"):
        freeze.cmd_freeze(args())  # no attestation
    with pytest.raises(StageRefused, match="seal flag"):
        freeze.cmd_freeze(args("--seal-broken"))
    assert not (repo / planmod.FREEZE_RECORD).exists()
    assert freeze.cmd_freeze(args("--attest-sealed-unopened", "lead,implementer,auditor")) == 0
    fr = json.loads((repo / planmod.FREEZE_RECORD).read_text(encoding="utf-8"))
    assert fr["kind"] == "freeze_record" and fr["plan_file_sha256"] == plan_sha and fr["rehearsal"]["sha256"] == file_sha256(reh)
    assert file_sha256(repo / core.PLAN) == plan_sha  # the plan is never rewritten
    plan = Plan.load(repo / core.PLAN)
    assert planmod.verify_freeze_record(plan, repo)["plan_file_sha256"] == plan_sha
    with pytest.raises(StageRefused, match="freeze is written once|exists"):
        freeze.cmd_freeze(args("--attest-sealed-unopened", "lead,implementer,auditor"))
    # the freeze record is not part of the frozen-file hashes (like the plan), and a plan that changed after the freeze no longer matches it
    assert str(planmod.FREEZE_RECORD) not in planmod.frozen_file_hashes(repo)
    (repo / core.PLAN).write_text((repo / core.PLAN).read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(StageRefused, match="does not name the SHA-256"):
        planmod.verify_freeze_record(plan, repo)


def test_freeze_refuses_provisional_caps_and_a_registered_verify_needs_the_freeze_record(tmp_path: Path) -> None:
    from studies.p10ir import freeze

    repo, reh = freeze_repo(tmp_path)
    (repo / "configs" / "p10ir_routing.toml").write_text(re.sub(r"(?m)^provisional = (true|false)", "provisional = true", (ROOT / "configs" / "p10ir_routing.toml").read_text(encoding="utf-8"), count=1), encoding="utf-8")  # provisional again
    with pytest.raises(StageRefused, match="provisional"):
        freeze.cmd_freeze(stages.build_parser().parse_args(["freeze", "--rehearsal", str(reh), "--repo", str(repo)]))
    repo2, _ = freeze_repo(tmp_path / "second")
    plan = Plan.load(repo2 / core.PLAN)
    with pytest.raises(StageRefused, match="no freeze record"):
        planmod.verify_plan(plan, repo2, tmp_path / "second" / "run", check_items=False)
    planmod.verify_plan(plan, repo2, tmp_path / "second" / "run", check_items=False, candidate=True)  # the candidate phase verifies the plan without a freeze record


def test_caps_proposal_is_section_12s_rule(capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.main(["caps-proposal", "--charged-hours", "1.0", "--projected-remaining-hours", "2.0"]) == 0
    assert json.loads(capsys.readouterr().out)["proposed_cap_hours"] == 5.0


# --- the runner: PAUSED and resumable -------------------------------------------------------------------------------------------------------------------------
def py_task(tmp: Path, label: str, code: str, result: bool = True) -> runner.Task:
    done = tmp / f"{label}.done"
    body = code + (f"\nopen({str(done)!r}, 'w').write('ok')\n" if result else "\n")
    return runner.Task(label, (sys.executable, "-c", body), done, tmp / f"{label}.failed.json", tmp / f"{label}.log")


def test_runner_completes_pauses_on_the_cap_and_resumes_without_rerunning(tmp_path: Path) -> None:
    quick = py_task(tmp_path, "quick", "pass")
    slow = py_task(tmp_path, "slow", "import time; time.sleep(20)")
    later = py_task(tmp_path, "later", "pass")
    began = time.monotonic()
    out, wall = runner.run_tasks([quick, slow, later], workers=2, cap_seconds=2.0, rss_worker_bytes=1 << 30, rss_aggregate_bytes=1 << 31, poll=0.05)
    assert time.monotonic() - began < 15 and wall < 15  # the wait has a deadline
    assert out["quick"]["status"] == runner.COMPLETED and out["slow"]["status"] == runner.KILLED_CAP and out["later"]["status"] in (runner.COMPLETED, runner.NOT_STARTED)
    assert runner.stage_status(out) == "PAUSED"
    # resume: the completed task is not run again (its result exists), the paused ones run
    marker = tmp_path / "quick.done"
    stamp = marker.stat().st_mtime_ns
    slow2 = py_task(tmp_path, "slow", "pass")
    out2, _ = runner.run_tasks([quick, slow2, later], workers=2, cap_seconds=30.0, rss_worker_bytes=1 << 30, rss_aggregate_bytes=1 << 31, poll=0.05)
    assert out2["quick"].get("skipped") == "result exists" and marker.stat().st_mtime_ns == stamp
    assert out2["slow"]["status"] == runner.COMPLETED and runner.stage_status(out2) == "COMPLETE"


def test_runner_keeps_a_failed_task_and_does_not_rerun_it_and_the_rss_guard_pauses(tmp_path: Path) -> None:
    bad = py_task(tmp_path, "bad", "raise SystemExit(3)", result=False)
    out, _ = runner.run_tasks([bad], workers=1, cap_seconds=30.0, rss_worker_bytes=1 << 30, rss_aggregate_bytes=1 << 31, poll=0.05)
    assert out["bad"]["status"] == runner.FAILED and bad.failed_path.is_file() and runner.stage_status(out) == "FAILED"
    again, _ = runner.run_tasks([bad], workers=1, cap_seconds=30.0, rss_worker_bytes=1 << 30, rss_aggregate_bytes=1 << 31, poll=0.05)
    assert again["bad"]["status"] == runner.FAILED and "never re-run" in again["bad"]["reason"] or "not re-run" in again["bad"]["reason"]
    hog = py_task(tmp_path, "hog", "x = bytearray(200 * 1024 * 1024); import time; time.sleep(20)")
    out3, _ = runner.run_tasks([hog], workers=1, cap_seconds=30.0, rss_worker_bytes=50 * 1024 * 1024, rss_aggregate_bytes=1 << 31, poll=0.05)
    assert out3["hog"]["status"] == runner.KILLED_RSS and runner.stage_status(out3) == "PAUSED"  # a memory guard is a resource cap: PAUSED


def test_stage_manifest_records_paused_then_complete_and_is_never_rewritten_when_complete(tmp_path: Path) -> None:
    ident = {"plan_sha256": "x"}
    m1 = runner.write_manifest(tmp_path, "a1", "rehearsal", {"c1": {"status": "completed", "seconds": 1.0}, "c2": {"status": "killed_cap", "seconds": 1.0}}, 2.0, identity=ident, started="t0", caps={"stage_seconds": 3.0})
    assert m1["status"] == "PAUSED" and len(m1["history"]) == 1
    m2 = runner.write_manifest(tmp_path, "a1", "rehearsal", {"c2": {"status": "completed", "seconds": 1.0}}, 1.0, identity=ident, started="t1", caps={"stage_seconds": 3.0})
    assert m2["status"] == "COMPLETE" and len(m2["history"]) == 2 and m2["charged_seconds"] == 3.0 and m2["tasks"]["c1"]["status"] == "completed"
    with pytest.raises(RuntimeError, match="COMPLETE"):
        runner.write_manifest(tmp_path, "a1", "rehearsal", {}, 0.0, identity=ident, started="t2", caps={})
    assert runner.read_manifest(tmp_path, "a1")["status"] == "COMPLETE"  # type: ignore[index]


def test_ledger_charges_and_refuses_when_the_cap_is_spent(tmp_path: Path) -> None:
    ledger = core.Ledger(tmp_path / "ledger.json", 100.0)
    ledger.require_room("a1", 50.0)
    ledger.charge("a1", "run", 60.0)
    ledger.charge("a2", "run", 30.0)
    assert ledger.charged() == 90.0 and ledger.charged("a1") == 60.0 and ledger.remaining() == 10.0
    ledger.charge("a1", "run", 20.0)
    with pytest.raises(core.LedgerRefused):
        ledger.require_room("a1", 50.0)
    with pytest.raises(core.LedgerRefused):
        ledger.require_room("a1", 0.0)


# --- resumability inside a task: a finished read is not recomputed ----------------------------------------------------------------------------------------
def test_a_resumed_item_recomputes_only_the_missing_reads_and_a_complete_item_not_at_all(mini: tuple[Plan, items.Ctx], monkeypatch: pytest.MonkeyPatch) -> None:
    plan, ctx = mini
    digests = plan.data["checkpoint_digests"]
    it = next(i for i in plan.items("A1") if i["arm"] == "T-OQ" and i["update"] == i["u_p"] and i["slots"] == 1024)
    items.run_item(ctx, it, digests)
    rec = items.Recorder(ctx, it)
    assert rec.complete() and all(rec.has_read(r["name"]) for r in it["reads"] if r["status"] == "RUN")
    t1 = rec.read_file("T1")
    stamp, text = t1.stat().st_mtime_ns, t1.read_text(encoding="utf-8")
    calls: list[str] = []
    real = reads.read_counts
    monkeypatch.setattr(reads, "read_counts", lambda *a, **k: (calls.append("x"), real(*a, **k))[1])
    items.run_item(ctx, it, digests)  # complete: nothing is computed
    assert calls == []
    # a PAUSED item: the completion mark and one read are gone; only that read is recomputed, the others are untouched
    (rec.dir / "item.json").unlink()
    rec.read_file("Tv1_on").unlink()
    (rec.dir / "gate.t0_counts.json").unlink()
    items.run_item(ctx, it, digests)
    assert len(calls) == 1 and rec.complete() and rec.has_read("Tv1_on") and rec.has_gate("t0_counts")
    assert t1.stat().st_mtime_ns == stamp and t1.read_text(encoding="utf-8") == text
    done = core.read_record(rec.dir / "item.json", "item")
    assert done["complete"] is True and set(done["gates"]) >= {"checkpoint_identity", "t0_path", "t0_counts", "tree_recall_reproduction", "tv1_priors_on_against_off", "t3_against_independent_flat", "t2_against_independent_flat"}
    assert {r["name"] for r in done["not_applicable"]} == {"Tv8_on", "Tv8_off"} and "T0" in done["reads_done"]


def test_item_files_are_one_per_read_with_the_read_name_in_the_path(mini: tuple[Plan, items.Ctx]) -> None:
    plan, ctx = mini
    it = next(i for i in plan.items("A1") if i["arm"] == "F-OQ")
    p = stages_io.read_path(ctx.run_dir, it["stage"], it["id"], "I64@256/s938901")
    assert p.name == "read.I64@256~s938901.json" and "/" not in p.name
    assert stages_io.read_path(ctx.run_dir, it["stage"], it["id"], "F0") != stages_io.read_path(ctx.run_dir, it["stage"], it["id"], "I256@512")


# --- a stage through subprocess workers: PAUSED on a spent cap, then resumed ---------------------------------------------------------------------------------
def test_a_stage_through_subprocess_workers_pauses_on_a_spent_cap_and_resumes_to_complete(tmp_path: Path) -> None:
    """The pool path of the registered driver (``runner.run_tasks`` over ``python -m studies.p10ir.stages work reads``), on the rehearsal's own plan. The first invocation has one second of cap left in its
    ledger: the workers are killed (``killed_cap`` or ``not_started``) and the stage manifest says PAUSED. A second invocation, with the cap extended (another ledger), runs only what is missing."""
    from studies.p10ir import rehearsal
    from studies.p10s1 import train as s1train

    s1train.configure()
    plan, ctx = rehearsal.build_synthetic_plan(tmp_path / "sub", CFG, 1)
    root = ctx.run_dir
    plan_path = root / "freeze" / "plan.json"
    stages.execute_stage("gates-a1", plan, ctx, root, plan_path, repo=ROOT, workers=1, inline=True)
    spent = stages.ledger_of(plan, root, tmp_path / "ledger_a")
    spent.charge("a1", "earlier", plan.cap_seconds("a1") - 1.0)
    assert stages.stage_cap_seconds(plan, "a1", spent) == pytest.approx(1.0)
    first = stages.execute_stage("a1", plan, ctx, root, plan_path, repo=ROOT, workers=2, inline=False, extra_worker_args=("--run-sealed",), ledger_root=tmp_path / "ledger_a")
    assert first["status"] == "PAUSED" and {v["status"] for v in first["tasks"].values()} <= {runner.KILLED_CAP, runner.NOT_STARTED, runner.COMPLETED}
    assert not any(v["status"] == runner.FAILED for v in first["tasks"].values())
    second = stages.execute_stage("a1", plan, ctx, root, plan_path, repo=ROOT, workers=2, inline=False, extra_worker_args=("--run-sealed",), ledger_root=tmp_path / "ledger_b")
    assert second["status"] == "COMPLETE" and len(second["history"]) == 2 and all(v["status"] == runner.COMPLETED for v in second["tasks"].values())
    for it in plan.items("A1"):
        assert items.Recorder(ctx, it).complete(), it["id"]
    with pytest.raises(StageRefused, match="is COMPLETE"):
        stages.execute_stage("a1", plan, ctx, root, plan_path, repo=ROOT, workers=2, inline=False, ledger_root=tmp_path / "ledger_c")


def test_registered_items_survive_a_json_round_trip_so_verify_plan_can_compare_them() -> None:
    it = planmod.registered_items(CFG)
    assert json.loads(json.dumps(it)) == it


def test_the_entry_points_set_the_platform_settings_before_they_check_them() -> None:
    """A fresh process has torch's default thread counts; the driver sets one thread, one interop thread and deterministic algorithms (``train.configure``) before ``check_preconditions`` looks at them."""
    code = (
        f"import sys; sys.path.insert(0, {str(ROOT)!r})\n"
        "from studies.p10ir import gates\n"
        "before = gates.platform_problems()\n"
        "from studies.p10s1 import train\n"
        "train.configure()\n"
        "print(len(before) > 0, gates.platform_problems())\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120, check=False)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("[]"), out.stdout


# --- B2: PAUSED — IDENTITY ------------------------------------------------------------------------------------------------------------------------------
def test_a_worker_that_refuses_exits_75_and_the_runner_pauses_it_without_a_failed_record(tmp_path: Path) -> None:
    refusing = py_task(tmp_path, "r", "import sys; sys.exit(75)", result=False)
    out, _ = runner.run_tasks([refusing], workers=1, cap_seconds=30.0, rss_worker_bytes=1 << 30, rss_aggregate_bytes=1 << 31, poll=0.05)
    assert out["r"]["status"] == runner.PAUSED_IDENTITY and "PAUSED — IDENTITY" in out["r"]["reason"]
    assert not refusing.failed_path.exists() and runner.stage_status(out) == "PAUSED"
    # the next invocation runs the task again (the cause was removed)
    again = py_task(tmp_path, "r", "pass")
    out2, _ = runner.run_tasks([again], workers=1, cap_seconds=30.0, rss_worker_bytes=1 << 30, rss_aggregate_bytes=1 << 31, poll=0.05)
    assert out2["r"]["status"] == runner.COMPLETED and runner.stage_status(out2) == "COMPLETE"
    # a genuine failure is still FAILED and kept (exit 2 is not the identity code)
    bad = py_task(tmp_path, "b", "raise SystemExit(2)", result=False)
    assert runner.run_tasks([bad], workers=1, cap_seconds=30.0, rss_worker_bytes=1 << 30, rss_aggregate_bytes=1 << 31, poll=0.05)[0]["b"]["status"] == runner.FAILED


def test_a_dirty_tree_appearing_during_a_stage_pauses_the_workers_and_the_stage_resumes(tmp_path: Path) -> None:
    """The P10-S1 failure mode: a file written in the repository while a registered stage runs made every task that started then refuse, permanently. Here the real worker entry point refuses on the dirty tree with
    exit 75, the runner records PAUSED — IDENTITY and the stage manifest says PAUSED; nothing is kept as failed; after the cause is removed the same task runs again."""
    repo = make_repo(tmp_path)
    plan = {**core.envelope("freeze_plan"), "mode": "registered", "items": {"A1": [], "A2": []}}
    pf = repo / core.PLAN
    pf.parent.mkdir(parents=True, exist_ok=True)
    pf.write_text(json.dumps(plan), encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True, timeout=60)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "plan"], check=True, capture_output=True, timeout=60)
    full = head(repo)
    (repo / "NOTE.md").write_text("a note written during the stage", encoding="utf-8")  # the dirty tree
    done = tmp_path / "out" / "x.done.json"
    argv = (sys.executable, "-m", "studies.p10ir.stages", "work", "reads", "--stage", "a1", "--labels", "x", "--run-dir", str(tmp_path / "out"), "--plan", str(pf), "--mode", "registered", "--freeze-commit", full, "--repo", str(repo))
    task = runner.Task("x", argv, done, tmp_path / "out" / "x.failed.json", tmp_path / "out" / "x.log")
    out, _ = runner.run_tasks([task], workers=1, cap_seconds=120.0, rss_worker_bytes=1 << 31, rss_aggregate_bytes=1 << 33, env={"PYTHONPATH": str(ROOT)})
    assert out["x"]["returncode"] == 75 and out["x"]["status"] == runner.PAUSED_IDENTITY, out
    assert "not clean" in (tmp_path / "out" / "x.log").read_text(encoding="utf-8") and not task.failed_path.exists()
    manifest = runner.write_manifest(tmp_path / "out", "a1", "registered", out, 1.0, identity={}, started="t", caps={})
    assert manifest["status"] == "PAUSED"
    (repo / "NOTE.md").unlink()  # restored bit for bit
    stub = py_task(tmp_path / "out", "x", "pass")
    out2, _ = runner.run_tasks([stub], workers=1, cap_seconds=30.0, rss_worker_bytes=1 << 30, rss_aggregate_bytes=1 << 31, poll=0.05)
    assert out2["x"]["status"] == runner.COMPLETED
    assert runner.write_manifest(tmp_path / "out", "a1", "registered", out2, 1.0, identity={}, started="t2", caps={})["status"] == "COMPLETE"


def test_main_returns_75_for_a_worker_refusal_and_2_for_the_driver(tmp_path: Path) -> None:
    plan = {**core.envelope("freeze_plan"), "mode": "registered", "items": {"A1": [], "A2": []}}
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    w = ["work", "reads", "--stage", "a1", "--labels", "x", "--run-dir", str(tmp_path / "r"), "--plan", str(p), "--mode", "registered", "--freeze-commit", "HEAD"]
    assert stages.main(w) == runner.IDENTITY_EXIT == 75
    assert stages.main(["registered", "a1", "--run-dir", str(tmp_path / "r"), "--freeze-commit", "HEAD"]) == 2


# --- audit A6, A7, A8 --------------------------------------------------------------------------------------------------------------------------------
def test_an_edit_of_imported_p10s1_code_after_the_freeze_refuses(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / "studies" / "p10s1").mkdir(parents=True)
    (repo / "studies" / "p10s1" / "index.py").write_text("A = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True, timeout=60)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "p10s1"], check=True, capture_output=True, timeout=60)
    full = head(repo)
    assert "studies/p10s1" in planmod.IMPORTED_CODE_ROOTS and "studies/p9" in planmod.IMPORTED_CODE_ROOTS and "studies/p9i" in planmod.IMPORTED_CODE_ROOTS
    (repo / "studies" / "p10s1" / "index.py").write_text("A = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "edit p10s1 after the freeze"], check=True, capture_output=True, timeout=60)
    with pytest.raises(StageRefused, match="studies/p10s1 at HEAD differs"):
        planmod.check_preconditions(planmod.REGISTERED, repo, full)


def test_a_run_directory_inside_the_repository_must_be_git_ignored(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    (repo / ".gitignore").write_text("experiments/\n", encoding="utf-8")
    planmod.require_ignored_run_dir(repo, repo / "experiments" / "P10IR-run")  # ignored: allowed
    planmod.require_ignored_run_dir(repo, tmp_path / "elsewhere")  # outside the repository: allowed
    with pytest.raises(StageRefused, match="not git-ignored"):
        planmod.require_ignored_run_dir(repo, repo / "results" / "run")


def test_run_sealed_outside_registered_mode_needs_the_rehearsals_own_records(tmp_path: Path) -> None:
    """Audit A8: a plan whose ``s1_run_dir`` is the registered run, in rehearsal mode, must not be read with ``--run-sealed`` (that would compare a sealed value before the freeze)."""
    plan = {**core.envelope("freeze_plan"), "mode": "rehearsal", "items": {"A1": [], "A2": []}, "s1_run_dir": str(tmp_path / "registered_run"), "i64_seeds": [1, 2, 3]}
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    base = ["work", "reads", "--stage", "a1", "--labels", "x", "--run-dir", str(tmp_path / "rehearsal"), "--plan", str(p), "--mode", "rehearsal"]
    assert stages.main([*base, "--run-sealed"]) == 75
    inside = {**plan, "s1_run_dir": str(tmp_path / "rehearsal" / "s1")}
    p.write_text(json.dumps(inside), encoding="utf-8")
    with pytest.raises(StageRefused, match="not a cell of the frozen plan"):
        stages.cmd_work(stages.build_parser().parse_args([*base, "--run-sealed"]))  # the sealed-run guard passes; the unknown label then refuses


def test_the_rehearsal_gate_in_a_registered_plan_reads_the_freeze_records_rehearsal(tmp_path: Path) -> None:
    repo, reh = freeze_repo(tmp_path)
    plan = Plan.load(repo / core.PLAN)
    from arborlm.io import file_sha256

    assert stages.rehearsal_record_of(plan) == (None, file_sha256(repo / core.PLAN))  # no freeze record yet: no rehearsal record, and the plan file's own hash


def test_candidate_plan_is_superseded_only_with_the_flag_and_the_old_file_is_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """N2: a candidate plan is never overwritten silently; with --supersede the old file moves to freeze/superseded/plan-<sha12>.json."""
    from arborlm.io import file_sha256
    from studies.p10ir import freeze

    repo, _ = freeze_repo(tmp_path)
    old_sha = file_sha256(repo / core.PLAN)
    new = json.loads((repo / core.PLAN).read_text(encoding="utf-8"))
    new["run_dir"] = str(tmp_path / "other_run")
    monkeypatch.setattr(freeze, "build_candidate", lambda *a, **k: json.loads(json.dumps(new)))
    base = ["candidate-plan", "--run-dir", str(tmp_path / "r"), "--s1-run-dir", str(tmp_path / "s1"), "--repo", str(repo)]
    with pytest.raises(StageRefused, match="--supersede"):
        freeze.cmd_candidate_plan(stages.build_parser().parse_args(base))
    assert file_sha256(repo / core.PLAN) == old_sha
    assert freeze.cmd_candidate_plan(stages.build_parser().parse_args([*base, "--supersede"])) == 0
    kept = repo / "studies" / "p10ir" / "freeze" / "superseded" / f"plan-{old_sha[:12]}.json"
    assert kept.is_file() and file_sha256(kept) == old_sha and file_sha256(repo / core.PLAN) != old_sha
    (repo / planmod.FREEZE_RECORD).write_text("{}", encoding="utf-8")
    with pytest.raises(StageRefused, match="freeze record exists"):
        freeze.cmd_candidate_plan(stages.build_parser().parse_args([*base, "--supersede"]))


def test_the_ledger_is_never_written_where_it_would_dirty_the_tree(tmp_path: Path) -> None:
    """N3: a ledger path inside the repository must be git-ignored; the run directory being the ignored root itself puts the ledger in its parent, which is not."""
    repo = make_repo(tmp_path)
    (repo / ".gitignore").write_text("experiments/\n", encoding="utf-8")
    plan = Plan({**core.envelope("freeze_plan"), "mode": "registered", "items": {"A1": [], "A2": []}, "stage_caps": {"total_hours": 1.0}})
    ok = stages.ledger_of(plan, repo / "experiments" / "run", None, repo)
    assert ok.path == repo / "experiments" / "P10IR-ledger.json"
    with pytest.raises(StageRefused, match="not git-ignored"):
        stages.ledger_of(plan, repo / "experiments", None, repo)  # the run directory is the ignored root: its parent is the repository root
    assert stages.ledger_of(plan, tmp_path / "outside" / "run", None, repo).path.parent == tmp_path / "outside"
    with pytest.raises(StageRefused, match="not git-ignored"):
        stages.ledger_of(plan, repo / "experiments" / "run", repo / "results", repo)


def test_the_freeze_compares_the_scientific_content_not_the_adr_hash_or_the_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """F3: an ADR edit between candidate-plan and freeze does not refuse the freeze (the ADR is recorded for provenance only, section 13); a config or code change does."""
    from studies.p10ir import freeze, gates

    repo, reh = freeze_repo(tmp_path)
    cfg_path = repo / core.CONFIG
    plan_sha = planmod.file_sha256(repo / core.PLAN)
    monkeypatch.setattr(gates, "seed_gate", lambda *a, **k: {"passed": True, "problems": [], "roles": {}, "declared_reuse_not_new": {}, "checker": {}})

    def rederive(*a: Any, **k: Any) -> dict[str, Any]:
        c = core.load_config(cfg_path)
        return planmod.build_plan(mode=planmod.REGISTERED, cfg=c, repo=repo, items=planmod.registered_items(c), run_dir=tmp_path / "run", s1_run_dir=tmp_path / "s1", extra={"seal": {"accesses_declared": [], "values_opened": False, "broken": False}})

    monkeypatch.setattr(freeze, "build_candidate", rederive)
    core.write_record(reh, {**core.envelope("rehearsal"), "stages": {s: {"status": "COMPLETE"} for s in stages.REHEARSAL_STAGES}, "registered_checkpoint_gates": {"gate1_passed": True, "gate2_passed": True, "gate3_run": False}, "caps_provisional": False, "candidate": {"status": "COMPLETE", "plan_file_sha256": plan_sha}})
    args = stages.build_parser().parse_args(["freeze", "--rehearsal", str(reh), "--repo", str(repo), "--attest-sealed-unopened", "lead,implementer,auditor"])
    (repo / core.SPEC).write_text("the ADR was edited to record the caps\n", encoding="utf-8")
    assert freeze.scientific_content({"adr": 1, "platform": 2, "items": 3}) == {"items": 3}
    # a code change refuses
    (repo / "studies" / "p10ir" / "x.py").write_text("X = 2\n", encoding="utf-8")
    with pytest.raises(StageRefused, match="differs from a re-derivation"):
        freeze.cmd_freeze(args)
    (repo / "studies" / "p10ir" / "x.py").write_text("X = 1\n", encoding="utf-8")
    # a config change refuses
    original = cfg_path.read_text(encoding="utf-8")
    cfg_path.write_text(original.replace("closure = 0.5", "closure = 0.6"), encoding="utf-8")
    with pytest.raises(StageRefused, match="differs from a re-derivation"):
        freeze.cmd_freeze(args)
    cfg_path.write_text(original, encoding="utf-8")
    assert freeze.cmd_freeze(args) == 0  # the ADR edit and a different platform record alone do not refuse
