# ruff: noqa: E501
"""P10IS0: F1 (the guard keeps the substring test; only exact opaque shapes are exempt, only in a hashes map) and F2 (a committed, pinned ruling; one rebind; the record is a frozen input)."""

import random
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from arborlm.io import write_json  # noqa: E402
from studies.p10is0 import core, drivers, ladder, runner, sealed  # noqa: E402
from studies.p10is0 import plan as planmod  # noqa: E402

CFG = core.load_config()
H = "a" * 64
AUDITOR_NAMES = ["acc12345678", "accdeadbeef", "acc0ffee", "Acc12345678", "acc_12345678", "trainloss", "meanacc", "valacc", "testacc", "panelaccuracy", "probecorrect", "hloss", "Xacc", "m_p", "recall_at_1", "plateau_value", "lossy", "glossary", "accept", "access", "bitsy", "correction", "curves2", "entropy0", "margin1", "nll", "mean_acc", "accuracy"]


def old_rule(key: str) -> bool:
    return any(w in key.lower() for w in sealed.FORBIDDEN_WORDS)


@pytest.mark.parametrize("name", AUDITOR_NAMES)
def test_every_auditor_name_is_refused_everywhere(name: str) -> None:
    assert sealed.names_a_measure(name) and sealed.names_a_measure(name, hashes_key=True) and sealed.names_a_measure(f"cal/{name}.json", hashes_key=True)
    with pytest.raises(sealed.PublicOutputError):
        sealed.validate_public({"hashes": {f"tasks/s/{name}.log": H}})
    with pytest.raises(sealed.PublicOutputError):
        sealed.validate_public({"cell_types": {name: 1}})


def test_everything_the_old_rule_refused_is_still_refused_except_exact_task_files() -> None:
    rng = random.Random(7)
    words = ["a", "c", "acc", "x", "loss", "t", "d", "bits", "correct", "m_p", "e", "f", "0", "1", "recall"]
    for _ in range(4000):
        key = "".join(rng.choice(words) for _ in range(rng.randint(1, 4)))
        assert sealed.names_a_measure(key) == (old_rule(key) or "recall" in key.lower())  # outside a hashes map the rule IS the old rule
        assert sealed.names_a_measure(key, hashes_key=True) == (old_rule(key) or "recall" in key.lower()) or sealed.OPAQUE_TASK_FILE.match(key)


def test_the_exemption_is_exactly_the_shape_the_generator_makes(tmp_path: Path) -> None:
    key = "tasks/stage_r_a0_base_i4/t1af0a449caccd5.log"
    assert sealed.OPAQUE_TASK_FILE.match("t1af0a449caccd5.log") and not sealed.names_a_measure(key, hashes_key=True)
    sealed.validate_public({"hashes": {key: H}})
    for near in ("t1af0a449caccd.log", "t1af0a449caccd55.log", "T1af0a449caccd5.log", "acc12345678.log", "t1af0a449caccd5.txt", "t1af0a449caccd5.log.bak"):
        assert near == "t1af0a449caccd5.log.bak" or not sealed.OPAQUE_TASK_FILE.match(near)
    assert sealed.names_a_measure("tasks/s/t1af0a449caccd5.log.bak", hashes_key=True)  # not an exact shape: tested, and it contains acc
    assert sealed.names_a_measure(key)  # outside a hashes map the same key is refused (an int or a string under it is refused too)
    for v in (5, "x", 0.5):
        with pytest.raises(sealed.PublicOutputError):
            sealed.validate_public({"cell_types": {"t1af0a449caccd5.log": v}})
        with pytest.raises(sealed.PublicOutputError):
            sealed.validate_public({"hashes": {key: v}})  # in a hashes map the value must be 64-hex
    # the real generator: task ids and the files the runner gives them
    ctx = drivers.Ctx(REPO, tmp_path / "run", registered=False, sealed_dir=tmp_path / "store")
    rng = random.Random(11)
    for _ in range(4000):
        label = drivers.opaque_label(tmp_path / "store", rng.randint(0, 3), f"{rng.choice(['2K', '8K'])}/{rng.choice(['512', '16K', '4K'])}", rng.choice(["A5-D", "A6"]), rng.randint(1, 2), rng.randint(1, 10**6))
        assert sealed.OPAQUE_TASK_FILE.match(f"{label}.log") and sealed.OPAQUE_TASK_FILE.match(f"{label}.result.json") and sealed.OPAQUE_TASK_FILE.match(f"{label}.failed.json")
        sealed.validate_public({"hashes": {f"tasks/stage_r_a0_base_i{rng.randint(0, 9)}/{label}.log": H, f"tasks/s/{label}.result.json": H}})  # never raises
    t = ctx.task("stage_r_a0_base_i0", label, "stage-r-run", sealed_tasks=True)
    assert all(sealed.OPAQUE_TASK_FILE.match(p.name) for p in (t.log_path, t.result_path, t.failed_path))  # the runner's file names are the shapes the guard exempts
    assert isinstance(runner.Task, type)


# --- F2 ------------------------------------------------------------------------------------------------------------------------------------------------
def gitc(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@e.invalid", "-c", "commit.gpgsign=false", *args], cwd=repo, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def make_repo(tmp: Path) -> tuple[Path, str]:
    repo = tmp / "repo"
    shutil.copytree(REPO / "studies", repo / "studies", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "freeze"))
    shutil.copytree(REPO / "configs", repo / "configs")
    (repo / "studies/p10is0/freeze").mkdir(parents=True, exist_ok=True)
    (repo / ".gitignore").write_text("/experiments/\n")
    gitc(repo, "init", "-q")
    write_json(repo / core.DURATIONS, ladder.durations_record({}, drivers.code_identity(repo)))
    (repo / "studies/p10is0/freeze/.gitignore").write_text("*\n")  # durations.json stays untracked, as in the real run
    gitc(repo, "add", "-A")
    gitc(repo, "commit", "-q", "-m", "stage r")
    return repo, gitc(repo, "rev-parse", "HEAD")


def edit(repo: Path, rel: str, text: str = "\n# fix\n") -> None:
    f = repo / rel
    f.write_text(f.read_text() + text)


def ruling(repo: Path, stage_r: str, new: str, name: str = "RULING.md", mutate: str | None = None) -> Path:
    pins = drivers.rebind_pins(repo, stage_r, new, "the lead")
    if mutate:
        pins = pins.replace(mutate, "0" * len(mutate), 1)
    p = repo / "results" / "p10is0-freeze-x" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("RULING of the lead\n" + pins)
    return p


def test_rebind_needs_a_committed_ruling_that_pins_what_changed(tmp_path: Path) -> None:
    repo, stage_r = make_repo(tmp_path)
    ctx = drivers.Ctx(repo, tmp_path / "run", registered=False)
    edit(repo, "studies/p10is0/sealed.py")
    gitc(repo, "commit", "-qam", "fix")
    new = gitc(repo, "rev-parse", "HEAD")
    pins = drivers.rebind_pins(repo, stage_r, new, "the lead")
    assert pins.startswith(f"PIN stage_r_commit {stage_r}\nPIN new_commit {new}\nPIN file studies/p10is0/sealed.py old ") and pins.rstrip().endswith("PIN ruler the lead")
    # the ruling file is not committed
    r = ruling(repo, stage_r, new)
    with pytest.raises(drivers.StageRefused, match="committed"):
        drivers.cmd_rebind_identity(ctx, r)
    gitc(repo, "add", "-A")
    gitc(repo, "commit", "-qm", "ruling")
    # an uncommitted edit anywhere in the tree
    edit(repo, "studies/p10is0/stages.py")
    with pytest.raises(drivers.StageRefused, match="uncommitted"):
        drivers.cmd_rebind_identity(ctx, r)
    gitc(repo, "checkout", "--", "studies/p10is0/stages.py")
    # a wrong pinned hash, a missing ruler, a ruling pinning a different file set
    old_hash = pins.split(" old ")[1].split()[0]
    bad = ruling(repo, stage_r, new, "BAD.md", mutate=old_hash)
    gitc(repo, "add", "-A")
    gitc(repo, "commit", "-qm", "bad ruling")
    with pytest.raises(drivers.StageRefused, match="pinned hashes"):
        drivers.cmd_rebind_identity(ctx, bad)
    ok = ruling(repo, stage_r, new, "OK.md")
    ok.write_text(ok.read_text().replace("PIN ruler the lead\n", ""))
    gitc(repo, "add", "-A")
    gitc(repo, "commit", "-qm", "no ruler")
    with pytest.raises(drivers.StageRefused, match="no ruler"):
        drivers.cmd_rebind_identity(ctx, ok)
    good = ruling(repo, stage_r, new, "GOOD.md")
    gitc(repo, "add", "-A")
    gitc(repo, "commit", "-qm", "good ruling")
    # a change after the ruling's pins (the laundering the audit showed) is not covered by it
    edit(repo, "studies/p10is0/drivers.py", "\n# a later edit\n")
    gitc(repo, "commit", "-qam", "later edit")
    with pytest.raises(drivers.StageRefused, match="not the files the ruling pins|pinned hashes"):
        drivers.cmd_rebind_identity(ctx, good)
    gitc(repo, "reset", "-q", "--hard", "HEAD~1")
    out = drivers.cmd_rebind_identity(ctx, good)
    assert out["changed_files"] == ["studies/p10is0/sealed.py"]
    drivers.check_code_identity(repo)
    rec = core.read_record(repo / drivers.REBIND_RECORD, "event")
    assert rec["stage_r_commit"] == stage_r and rec["new_commit"] == new and rec["ruler"] == "the lead" and rec["files"][0]["old_sha256"] != rec["files"][0]["new_sha256"] and rec["ruling_sha256"]
    # one rebind only, and the record is a frozen input
    with pytest.raises(drivers.StageRefused, match="already made"):
        drivers.cmd_rebind_identity(ctx, good)
    assert "studies/p10is0/freeze/durations_identity_rebind.json" in planmod.frozen_paths(repo)


def test_rebind_refuses_a_change_outside_the_three_files_and_after_the_plan(tmp_path: Path) -> None:
    repo, stage_r = make_repo(tmp_path)
    ctx = drivers.Ctx(repo, tmp_path / "run", registered=False)
    edit(repo, "studies/p10is0/items.py")
    gitc(repo, "commit", "-qam", "science")
    new = gitc(repo, "rev-parse", "HEAD")
    with pytest.raises(drivers.StageRefused):
        drivers.cmd_rebind_identity(ctx, ruling(repo, stage_r, new))  # the pin helper itself works on any file; the scope check refuses
    gitc(repo, "add", "-A")
    gitc(repo, "commit", "-qm", "ruling")
    with pytest.raises(drivers.StageRefused, match="outside the ruling's scope"):
        drivers.cmd_rebind_identity(ctx, repo / "results/p10is0-freeze-x/RULING.md")
    gitc(repo, "reset", "-q", "--hard", stage_r)
    edit(repo, "studies/p10is0/sealed.py")
    gitc(repo, "commit", "-qam", "fix")
    new2 = gitc(repo, "rev-parse", "HEAD")
    r2 = ruling(repo, stage_r, new2, "R2.md")
    gitc(repo, "add", "-A")
    gitc(repo, "commit", "-qm", "ruling 2")
    (repo / core.PLAN).write_text("{}")
    with pytest.raises(drivers.StageRefused, match="plan exists"):
        drivers.cmd_rebind_identity(ctx, r2)


def test_the_event_template_is_shared(tmp_path: Path) -> None:
    ev = ["(a) anchor 8K/16K: NOT SHOWN"]
    dur = {"cell_types": {"8K/16K": {"convergence": "x"}}}
    drivers.write_events(tmp_path / "a", ev, dur)
    drivers.write_events_numbered(tmp_path / "b", [(1, ev[0])], dur)
    assert (tmp_path / "a" / "EVENT_1.md").read_text() == (tmp_path / "b" / "EVENT_1.md").read_text()
    with pytest.raises(FileExistsError):
        drivers.write_events(tmp_path / "a", ev, dur)
