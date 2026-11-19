# ruff: noqa: E501
"""The freeze-time checks of a plan that reuses completed stages: the confined-diff rule against the earlier freeze, the ledger pin, the seeds, the caps of attempt 3 and the reuse block's byte check. Self-check only."""

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10is2_partq_commands import measuring_record  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.common import plan as planmod  # noqa: E402
from studies.p10is2.partq import freeze, reuse, reusecheck, stages  # noqa: E402
from studies.p10is2.partq import plan as qplan  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RS = "studies/p10is2/partq/real_stages.py"

OLD_RS = '''"""doc"""
import os

STAGE_ORDER = ("a", "b")


class Guard:
    def __call__(self):
        return False


def build_world(x):
    return x


def run_stage(stage):
    return stage


def stage_outputs(w):
    return w
'''


def git(r: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(r), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *a], capture_output=True, text=True, check=True).stdout.strip()  # noqa: S603, S607


def mini_repo(tmp: Path) -> tuple[Path, str]:
    r = tmp / "repo"
    files = {RS: OLD_RS, "studies/p10is2/partq/gloss.py": "X = 1\n", "studies/p10is2/common/core.py": "Y = 1\n", "uv.lock": "lock\n", "pyproject.toml": "p\n", "studies/p10s2/requirements-datagen.txt": "r\n", "configs/p10is2_partq.toml": (ROOT / core.CONFIG_Q).read_text(), "studies/p10is2/launch/partq_registered.sh": "echo a\n", "studies/p10is2/launch/partq_ledger.sh": "echo l\n"}
    for rel, text in files.items():
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_text(text)
    git(r, "init", "-q") if (r / ".git").exists() is False else None
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "freeze")
    return r, git(r, "rev-parse", "HEAD")


def edit(r: Path, rel: str, old: str, new: str) -> None:
    p = r / rel
    assert old in p.read_text()
    p.write_text(p.read_text().replace(old, new))


# --- the confined diff ----------------------------------------------------------------------------------------------------------------------------
def test_an_identical_tree_and_an_allowed_edit_pass_and_the_mixed_function_is_listed_for_the_auditor(tmp_path: Path) -> None:
    r, c = mini_repo(tmp_path)
    assert reusecheck.confined_diff(r, c)["identical"] == 9
    edit(r, RS, "def stage_outputs(w):\n    return w", "def stage_outputs(w):\n    return w + 1")  # the outputs stage: allowed
    edit(r, RS, "def run_stage(stage):\n    return stage", "def run_stage(stage):\n    return (stage, 1)")  # the cap check: allowed by name, MIXED
    edit(r, RS, "import os\n", "import os\nimport sys\n")  # an added import
    (r / "studies/p10is2/partq/reuse.py").write_text("Z = 1\n")  # a new file
    edit(r, "studies/p10is2/partq/gloss.py", "X = 1", "X = 2")  # the segment rule: a whole allowed file
    rec = reusecheck.confined_diff(r, c)
    assert f"{RS}::run_stage" in rec["requires_auditor_certification"] and f"{RS}::stage_outputs" not in rec["requires_auditor_certification"]
    assert rec["changed"][RS] == ["run_stage", "stage_outputs"] and "studies/p10is2/partq/reuse.py" in rec["new_files"]


@pytest.mark.parametrize(
    ("rel", "old", "new", "match"),
    [
        (RS, "def __call__(self):\n        return False", "def __call__(self):\n        return True", "Guard"),  # a class the reused stages executed
        (RS, "STAGE_ORDER = (\"a\", \"b\")", "STAGE_ORDER = (\"b\", \"a\")", "STAGE_ORDER"),  # a constant
        (RS, "import os\n", "import sys\n", "import statement"),  # a changed import
        ("studies/p10is2/common/core.py", "Y = 1", "Y = 2", "core.py"),  # common/ is not allowed
        ("uv.lock", "lock", "lock2", "uv.lock"),
        ("studies/p10is2/launch/partq_ledger.sh", "echo l", "echo m", "partq_ledger.sh"),  # a launch script that is not listed
    ],
)
def test_a_difference_outside_the_confined_set_is_refused(tmp_path: Path, rel: str, old: str, new: str, match: str) -> None:
    r, c = mini_repo(tmp_path)
    edit(r, rel, old, new)
    with pytest.raises(core.StageRefused, match=match):
        reusecheck.confined_diff(r, c)


def test_a_removed_definition_is_refused_and_comments_and_formatting_do_not_count(tmp_path: Path) -> None:
    r, c = mini_repo(tmp_path)
    edit(r, RS, "def build_world(x):\n    return x\n", "def build_world( x ):  # a comment\n    return   x\n")
    assert reusecheck.confined_diff(r, c)["changed"] == {RS: []}  # the syntax tree is the same: no definition changed
    edit(r, RS, "class Guard:\n    def __call__(self):\n        return False\n\n\n", "")
    with pytest.raises(core.StageRefused, match="Guard"):
        reusecheck.confined_diff(r, c)


def test_the_config_may_differ_only_in_the_caps_and_the_ledger_path(tmp_path: Path) -> None:
    r, c = mini_repo(tmp_path)
    cfg = r / core.CONFIG_Q
    text = cfg.read_text()
    text = re.sub(r"(?m)^total_hours = [0-9.]+", "total_hours = 99.0", text).replace("provisional = true", "provisional = false")
    text = re.sub(r'(?m)^panel_ledger = "[^"]*"', 'panel_ledger = "/elsewhere/preserved_copy.json"', text)
    cfg.write_text(text)
    assert reusecheck.confined_diff(r, c)["changed"][core.CONFIG_Q.as_posix()]
    cfg.write_text(re.sub(r"(?m)^batch_size = [0-9]+", "batch_size = 16", cfg.read_text()))
    with pytest.raises(core.StageRefused, match="batch_size"):
        reusecheck.confined_diff(r, c)


# --- the ledger pin and the seeds ----------------------------------------------------------------------------------------------------------------------
def make_plan(sha: str, seeds: dict) -> planmod.Plan:  # type: ignore[type-arg]
    return planmod.Plan({"kind": "freeze_plan", "study": core.STUDY, "schema": core.SCHEMA, "part": "Q", "manifests": {"panel_ledger": {"path": "/x/preserved.json", "sha256": sha}}, "seeds": seeds}, "Q")


def test_the_new_plan_must_pin_a_ledger_with_the_hash_the_reused_stages_ran_against(tmp_path: Path) -> None:
    r, _c = mini_repo(tmp_path)
    old_plan = {"manifests": {"panel_ledger": {"path": "/shared/live.json", "sha256": "62f81116" + "0" * 56}}, "seeds": {"source_split": 250904}}
    (r / core.FREEZE_DIR).mkdir(parents=True, exist_ok=True)
    write_json(r / core.PLAN_Q, old_plan)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "plan")
    c = git(r, "rev-parse", "HEAD")
    ok = reusecheck.check_ledger_pin(r, c, make_plan("62f81116" + "0" * 56, {}))
    assert ok["same_as_earlier_plan"] and ok["path"] == "/x/preserved.json"
    with pytest.raises(core.StageRefused, match="preserved copy"):
        reusecheck.check_ledger_pin(r, c, make_plan("ba14c714" + "0" * 56, {}))  # the live, since-extended ledger
    assert reusecheck.check_seeds(r, c, make_plan("x", {"source_split": 250904}))["seeds_equal"]
    with pytest.raises(core.StageRefused, match="seeds"):
        reusecheck.check_seeds(r, c, make_plan("x", {"source_split": 1}))


# --- caps of attempt 3 ---------------------------------------------------------------------------------------------------------------------------
def test_the_caps_of_attempt_3_come_from_the_charge_so_far_and_the_remaining_stages_only(tmp_path: Path) -> None:
    rec = core.read_record(measuring_record(tmp_path), "rehearsal")
    charge = 42_636.8
    caps = freeze.proposal_attempt3(rec, charge)
    full = freeze.projection_from_record(rec)
    remaining = {s: full[s] for s in ("regeneration", "outputs", "analysis")} | {"reuse": rec["overhead_seconds"]["inputs"]}
    assert set(caps) == {"reuse_hours", "regeneration_hours", "outputs_hours", "analysis_hours", "total_hours"}  # the stages attempt 3 does not run get no cap
    assert caps == qplan.caps_proposal(charge, remaining)  # by the one shared function
    assert caps["total_hours"] * 3600 >= charge + 2 * sum(remaining.values()) - 36 and caps["total_hours"] * 3600 < charge + 2 * sum(full.values())  # not the whole eight-stage projection


def test_the_reuse_rehearsal_gate_needs_every_stage_the_plan_hash_and_the_identity_stop_on_a_reused_file() -> None:
    good = {"kind_of_rehearsal": "counting", "caps_provisional": False, "plan_file_sha256": "a" * 64, "stages": {s: {"status": "COMPLETE"} for s in reuse.ORDER}, "forced": {"identity_on_reused_file": True}}
    assert freeze.reuse_rehearsal_gate(good, "a" * 64)["passed"]
    assert not freeze.reuse_rehearsal_gate({**good, "forced": {}}, "a" * 64)["passed"]
    assert not freeze.reuse_rehearsal_gate(good, "b" * 64)["passed"]
    assert not freeze.reuse_rehearsal_gate({**good, "stages": {"reuse": {"status": "COMPLETE"}}}, "a" * 64)["passed"]


# --- the reuse block --------------------------------------------------------------------------------------------------------------------------------------
def fake_attempt(tmp: Path) -> Path:
    d = tmp / "attempt"
    for top in ("inputs", "partition", "qfit", "qcheck", "generation", "regeneration"):
        (d / top).mkdir(parents=True)
        (d / top / "a.json").write_text(f'{{"x": "{top}"}}')
    (d / "partition_counts.json").write_text("{}")
    (d / "regeneration.json").write_text("{}")
    (d / "stages").mkdir()
    for s in reuse.SOURCE_STAGES:
        (d / "stages" / f"{s}.complete.json").write_text(json.dumps({"stage": s, "status": "COMPLETE", "mode": "registered"}))
    (d / "outputs").mkdir()
    (d / "outputs" / "partial.json").write_text("{}")  # not a reused stage's file
    (d / "engineering_failures.json").write_text("{}")
    return d


def test_the_reuse_block_hashes_exactly_the_six_stages_files_and_detects_any_change(tmp_path: Path) -> None:
    d = fake_attempt(tmp_path)
    block = reuse.build_block(d, "c" * 40)
    assert "outputs/partial.json" not in block["files"] and "engineering_failures.json" not in block["files"] and "stages/regeneration.complete.json" in block["files"] and block["file_count"] == 6 + 1 + 1 + 6 + 0
    reuse.verify_block(block)
    (d / "qfit" / "a.json").write_text('{"x": "changed"}')
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        reuse.verify_block(block)
    (d / "qfit" / "a.json").write_text('{"x": "qfit"}')
    reuse.verify_block(block)  # restored
    (d / "generation" / "new.json").write_text("{}")  # a file ADDED to a hashed directory
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        reuse.verify_block(block)


def test_the_reuse_stage_links_the_reused_directories_and_never_writes_the_source(tmp_path: Path) -> None:
    d = fake_attempt(tmp_path)
    before = reuse.hash_files(d)
    block = reuse.build_block(d, "c" * 40)
    run = tmp_path / "run3"
    out = reuse.link_and_record(block, run, "registered")
    assert (run / "qfit").is_symlink() and (run / "partition_counts.json").is_symlink() and not (run / "regeneration").exists() and out["reused_stages"] == list(reuse.RECORDED)
    assert json.loads((run / "stages/qfit.complete.json").read_text())["reused_from"] == str(d) and not (run / "stages/regeneration.complete.json").exists()
    assert reuse.hash_files(d) == before
    reuse.link_and_record(block, run, "registered")  # idempotent
    with pytest.raises(core.StageRefused, match="mode"):
        reuse.link_and_record(block, tmp_path / "run4", "rehearsal")


def test_the_reuse_file_command_adds_the_block_to_a_copy_of_the_inputs_and_refuses_a_short_commit(tmp_path: Path) -> None:
    d = fake_attempt(tmp_path)
    base = tmp_path / "inputs.json"
    write_json(base, {"requirements": {"path": "r", "sha256": "0" * 64}})
    head = git(ROOT, "rev-parse", "HEAD")
    out = tmp_path / "inputs3.json"
    assert stages.main(["reuse-file", "--source-run-dir", str(d), "--freeze-commit", head, "--base-inputs", str(base), "--out", str(out)]) == 0
    got = json.loads(out.read_text())
    assert got["requirements"] and got[reuse.KEY]["file_count"] == 14 and got[reuse.KEY]["freeze_commit"] == head
    assert stages.main(["reuse-file", "--source-run-dir", str(d), "--freeze-commit", head[:8], "--base-inputs", str(base), "--out", str(tmp_path / "x.json")]) == 2
    assert stages.main(["reuse-file", "--source-run-dir", str(d), "--freeze-commit", head, "--base-inputs", str(base), "--out", str(out)]) == 2  # written once


def test_the_plan_builder_records_the_charge_before_the_freeze(tmp_path: Path) -> None:
    rec = qplan.build_candidate(ROOT, tmp_path / "run", core.load_config("Q"), inputs={}, walk={"python_files": [], "files_opened": [], "outside_study_python": [], "outside_study_data": []}, test_mode=True, charge_before_freeze={"seconds": 42636.8, "ledgers": {"/x/charged_ledger.json": 42636.8}})
    assert rec["charge_before_freeze"]["seconds"] == 42636.8
