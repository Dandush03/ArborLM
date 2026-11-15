"""ADR-0016 stage runner: refusals (dirty tree, missing or wrong freeze commit, earlier run) and the
single-worker, 30-minute, 2 GiB limits. No real cell is simulated here."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from supplements.p8s import common, stage  # noqa: E402

GIT_CONFIG = (
    "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
    "-c", "core.hooksPath=/dev/null",
)  # fmt: skip


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *GIT_CONFIG, *args], capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    (r / "supplements" / "p8s").mkdir(parents=True)
    (r / "tests").mkdir()
    (r / "docs" / "decisions").mkdir(parents=True)
    (r / "supplements" / "p8s" / "x.py").write_text("x = 1\n")
    (r / "tests" / "test_p8s_x.py").write_text("def test_x(): pass\n")
    (r / common.SPEC_PATH).write_text("adr\n")
    _git(r.parent, "init", "-q", str(r))
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "freeze")
    return r


def test_clean_tree_required(repo: Path) -> None:
    stage.require_clean_tree(repo)
    (repo / "untracked.txt").write_text("u\n")
    with pytest.raises(common.SupplementError, match="not clean"):
        stage.require_clean_tree(repo)
    (repo / "untracked.txt").unlink()
    (repo / "supplements" / "p8s" / "x.py").write_text("x = 2\n")
    with pytest.raises(common.SupplementError, match="not clean"):
        stage.require_clean_tree(repo)


def test_freeze_commit_is_required_verified_and_recorded_with_its_tree(repo: Path) -> None:
    with pytest.raises(common.SupplementError, match="--freeze-commit is required"):
        stage.verify_supplement_freeze(repo, None)
    with pytest.raises(common.SupplementError, match="not a commit"):
        stage.verify_supplement_freeze(repo, "deadbeef")
    head = _git(repo, "rev-parse", "HEAD")
    freeze = stage.verify_supplement_freeze(repo, head)
    assert freeze["commit"] == head and freeze["tree"] == _git(repo, "rev-parse", "HEAD^{tree}")
    assert freeze["supplements_tree"] == _git(repo, "rev-parse", "HEAD:supplements")
    # code changed after the freeze commit: refused
    (repo / "supplements" / "p8s" / "x.py").write_text("x = 3\n")
    _git(repo, "commit", "-q", "-am", "later change")
    with pytest.raises(common.SupplementError, match="differs from the freeze commit"):
        stage.verify_supplement_freeze(repo, head)
    # a later commit that touches nothing the supplement owns is accepted
    later = _git(repo, "rev-parse", "HEAD")
    (repo / "notes.txt").write_text("n\n")
    _git(repo, "add", "notes.txt")
    _git(repo, "commit", "-q", "-m", "notes")
    assert stage.verify_supplement_freeze(repo, later)["commit"] == later


def test_unrelated_commit_is_not_an_ancestor(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "side")
    (repo / "side.txt").write_text("s\n")
    _git(repo, "add", "side.txt")
    _git(repo, "commit", "-q", "-m", "side")
    side = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", base)
    with pytest.raises(common.SupplementError, match="not an ancestor"):
        stage.verify_supplement_freeze(repo, side)


def test_runs_once_only(tmp_path: Path) -> None:
    stage.refuse_if_previous_run(tmp_path / "missing")
    stage.refuse_if_previous_run(tmp_path)
    (tmp_path / "P8SUP-20261114T000000000000Z-abc").mkdir()
    with pytest.raises(common.SupplementError, match="runs once"):
        stage.refuse_if_previous_run(tmp_path)


def test_run_stage_refuses_before_writing_anything(repo: Path, tmp_path: Path) -> None:
    out = tmp_path / "experiments"
    (repo / "dirty.txt").write_text("d\n")
    with pytest.raises(common.SupplementError, match="not clean"):
        stage.run_stage(tmp_path / "e", tmp_path / "s", out, freeze_commit="HEAD", repo=repo)
    (repo / "dirty.txt").unlink()
    with pytest.raises(common.SupplementError, match="--freeze-commit is required"):
        stage.run_stage(tmp_path / "e", tmp_path / "s", out, freeze_commit=None, repo=repo)
    assert not out.exists()


def test_cli_requires_the_freeze_commit_argument() -> None:
    with pytest.raises(SystemExit) as excinfo:
        stage.main(["run"])
    assert excinfo.value.code == 2


def test_limits_are_the_adr_limits() -> None:
    assert common.WALL_LIMIT_SECONDS == 1800.0  # 30 minutes
    assert common.RSS_LIMIT_BYTES == 2 * 1024**3  # 2 GiB
    assert common.SUPPLEMENT_CELLS == (
        "b101-o301-s601-C04",
        "b101-o301-s601-C05",
        "b101-o301-s602-C04",
        "b101-o301-s602-C05",
        "b102-o302-s601-C05",
    )


def test_execute_runs_one_worker_keeps_failures_and_records_limits(tmp_path: Path) -> None:
    from arborlm import p8_core as core
    from arborlm.io import read_json, write_json
    from supplements.p8s import synthetic

    if not common.commit_available(common.ROOT, common.FREEZE_COMMIT):
        pytest.skip("freeze commit not available in this clone (shallow checkout)")
    eval_run = tmp_path / "eval"
    good, bad = "b101-o301-s601-C04", "b102-o302-s601-C05"
    synthetic.write_single_set_cell(eval_run, core.parse_label(good))
    write_json(eval_run / "manifest.json", {"synthetic": True})
    # `bad` has no eval record: its worker fails and the failure record is kept
    freeze = {"commit": "a" * 40, "tree": "b" * 40, "supplements_tree": "c" * 40}
    run = stage.execute(
        eval_run, tmp_path / "sim", tmp_path / "experiments",
        freeze=freeze, verification={"ok": True, "problems": []}, repo=common.ROOT,
        cap_seconds=600.0, labels=(good, bad),
    )  # fmt: skip
    assert run.name.startswith("P8SUP-")
    manifest = read_json(run / "manifest.json")
    assert manifest["workers"] == 1 and manifest["cap_seconds"] == 600.0 and not manifest["cap_hit"]
    assert manifest["rss_limit_per_worker_bytes"] == 2 * 1024**3
    assert manifest["peak_worker_rss_bytes"] > 0 and manifest["wall_seconds"] > 0
    assert manifest["supplement_freeze_commit"] == freeze
    assert manifest["supplement_spec_sha256"] == common.supplement_spec_sha256()
    assert manifest["supplement_source_sha256"] == common.supplement_source_digest()
    assert manifest["source_sha256"] == common.FROZEN_SOURCE_DIGEST
    assert manifest["p7b_reproduction_record_cited"] == common.p7b_reproduction_record_cited()
    assert manifest["status"] == "INCOMPLETE" and manifest["cells_completed"] == 1
    assert (run / "cells" / good / "sim.json").is_file()
    failed = read_json(run / "cells" / bad / "sim.failed.json")
    assert failed["status"] == "failed" and "not re-run" in failed["note"]
    record = read_json(run / "cells" / good / "sim.json")
    assert record["supplement_freeze_commit"] == freeze and record["supplement"] == "ADR-0016"
    assert record["frozen_inputs"]["p7b_reproduction_record_cited"] == (
        common.p7b_reproduction_record_cited()
    )
    # the earlier run blocks any second run
    with pytest.raises(common.SupplementError, match="runs once"):
        stage.refuse_if_previous_run(tmp_path / "experiments")


def test_unexpected_exception_after_the_folder_exists_is_recorded_and_reraised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_: object, **__: object) -> None:
        raise RuntimeError("pool exploded")

    monkeypatch.setattr(stage.p8_pool, "run_pool", boom)
    freeze = {"commit": "a" * 40, "tree": "b" * 40, "supplements_tree": "c" * 40}
    experiments = tmp_path / "experiments"
    with pytest.raises(RuntimeError, match="pool exploded"):
        stage.execute(
            tmp_path / "eval", tmp_path / "sim", experiments,
            freeze=freeze, verification={"ok": True, "problems": []}, repo=common.ROOT,
            cap_seconds=60.0, labels=(common.SUPPLEMENT_CELLS[0],),
        )  # fmt: skip
    (run,) = experiments.glob("P8SUP-*")
    from arborlm.io import read_json

    failed = read_json(run / "manifest.json")
    assert failed["status"] == "FAILED" and failed["exception_type"] == "RuntimeError"
    assert failed["exception_message"] == "pool exploded" and "Traceback" in failed["traceback"]
    assert failed["supplement_freeze_commit"] == freeze
    with pytest.raises(common.SupplementError, match="runs once"):  # the folder blocks a re-run
        stage.refuse_if_previous_run(experiments)


def _skip_repo_gates(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI always checks the real repository (dirty while the supplement is uncommitted); skip
    the two git gates so the CLI path reaches the gate under test."""
    monkeypatch.setattr(stage, "require_clean_tree", lambda repo: None)
    monkeypatch.setattr(
        stage,
        "verify_supplement_freeze",
        lambda repo, commit: {"commit": "a" * 40, "tree": "b" * 40},
    )


def test_stage_cli_refuses_an_existing_supplement_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _skip_repo_gates(monkeypatch)
    (tmp_path / "P8SUP-20261114T000000000000Z-abc").mkdir()
    code = stage.main(["run", "--freeze-commit", "HEAD", "--experiments-root", str(tmp_path)])
    assert code == 2
    assert "REFUSED" in capsys.readouterr().err
    assert sorted(p.name for p in tmp_path.iterdir()) == ["P8SUP-20261114T000000000000Z-abc"]


def test_stage_cli_refuses_a_failed_frozen_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _skip_repo_gates(monkeypatch)
    monkeypatch.setattr(
        stage.frozen,
        "verify_frozen_material",
        lambda repo, eval_run, sim_run: {"ok": False, "problems": ["synthetic: blob differs"]},
    )
    code = stage.main(["run", "--freeze-commit", "HEAD", "--experiments-root", str(tmp_path)])
    assert code == 2
    err = capsys.readouterr().err
    assert "frozen material does not verify" in err and "blob differs" in err
    assert list(tmp_path.glob("P8SUP-*")) == []  # nothing written


def test_stage_cli_refuses_a_dirty_tree_and_a_missing_freeze_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def dirty(repo: Path) -> None:
        raise common.SupplementError("refused: the working tree is not clean:\nx")

    monkeypatch.setattr(stage, "require_clean_tree", dirty)
    assert stage.main(["run", "--freeze-commit", "HEAD", "--experiments-root", str(tmp_path)]) == 2
    assert "not clean" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
