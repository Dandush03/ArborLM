# ruff: noqa: E501
"""P9 package I6: job manager (immutable ids, semaphores, RSS and time caps, kept failures, dependent-cell
stop rule, refusal of a dirty tree or wrong freeze). Fake workers only; nothing is trained.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p9 import core, pool  # noqa: E402

IDENTITY = core.Identity(
    source_sha256="a" * 64,
    spec_sha256="b" * 64,
    config_sha256="c" * 64,
    frozen_source_sha256="d" * 64,
)
PY = sys.executable
WRITE = "import sys; open(sys.argv[1], 'w').write('{}')"


def task(
    tmp_path: Path,
    label: str,
    code: str,
    *,
    depends: tuple[str, ...] = (),
    group: str = "train",
    after: tuple[str, ...] = (),
    stage: str = "train",
) -> pool.Task:
    d = tmp_path / "cells" / label
    return pool.Task(
        task_id=pool.task_id(stage, label, IDENTITY),
        stage=stage,
        label=label,
        argv=(PY, "-c", code, str(d / "train.json")),
        depends_on=depends,
        after=after,
        group=group,
        result_path=d / "train.json",
        failed_path=d / "train.failed.json",
        log_path=d / "train.log",
    )


def run(tasks: list[pool.Task], **kw: object) -> pool.PoolResult:
    args: dict[str, object] = {
        "workers": {"train": 2, "simulate": 4, "evaluate": 2},
        "stage_cap_seconds": 60.0,
        "rss_worker_bytes": 3 * 1024**3,
        "rss_aggregate_bytes": 24 * 1024**3,
        "poll": 0.02,
    }
    args.update(kw)
    return pool.run_stage(tasks, **args)  # type: ignore[arg-type]


def status(result: pool.PoolResult) -> dict[str, str]:
    return {o.label: o.status for o in result.outcomes}


# --- pure functions -------------------------------------------------------------------------------------
def test_task_id_is_a_pure_function_of_stage_label_identity() -> None:
    a = pool.task_id("train", "x", IDENTITY)
    assert a == pool.task_id("train", "x", IDENTITY) and len(a) == 64
    assert a != pool.task_id("evaluate", "x", IDENTITY)
    assert a != pool.task_id("train", "y", IDENTITY)
    changed = core.Identity(**{**IDENTITY, "source_sha256": "e" * 64})
    assert a != pool.task_id("train", "x", changed)


def graph(edges: dict[str, tuple[str, ...]]) -> list[pool.Task]:
    p = Path("/nonexistent")
    return [
        pool.Task("id" + k, "train", k, ("x",), v, (), "train", p, p, p) for k, v in edges.items()
    ]


def test_skipped_for_dependency_is_transitive_and_leaves_independent_labels() -> None:
    tasks = graph({"a": (), "b": ("a",), "c": ("b",), "d": (), "e": ("d",), "f": ("c", "d")})
    assert pool.skipped_for_dependency(tasks, {"a"}) == {"b", "c", "f"}
    assert pool.skipped_for_dependency(tasks, {"d"}) == {"e", "f"}
    assert pool.skipped_for_dependency(tasks, {"b"}) == {"c", "f"}
    assert pool.skipped_for_dependency(tasks, set()) == set()
    assert pool.skipped_for_dependency(tasks, {"f"}) == set()  # a leaf failing skips nothing
    assert (
        pool.skipped_for_dependency(tasks, {"zzz"}) == set()
    )  # unknown label: nothing depends on it


def test_skipped_for_dependency_handles_unknown_dependency_and_cycles_free() -> None:
    tasks = graph({"a": ("outside",), "b": ("a",)})
    assert pool.skipped_for_dependency(tasks, {"outside"}) == {"a", "b"}
    assert pool.skipped_for_dependency(tasks, set()) == set()


def test_registry_lane_d_dependencies_drive_the_rule() -> None:
    d2 = [c for c in core.cells() if c.block == "D2"]
    d1 = [c for c in core.cells() if c.block == "D1"]
    plan = pool.plan_stage(
        "train",
        d1 + d2,
        Path("/r"),
        IDENTITY,
        argv_for={c.label: pool.worker_argv("train", c.label) for c in d1 + d2},
    )
    flat_phase_a = [c.label for c in d1 if c.arch == "flat" and c.seed == 1701][0]
    skipped = pool.skipped_for_dependency(plan, {flat_phase_a})
    expected = {c.label for c in d2 if flat_phase_a in c.depends_on}
    assert (
        skipped == expected and len(expected) == 3
    )  # flat sequential, memory-only, replay at seed 1701
    joint = [c.label for c in d2 if c.lane_d_arm == "joint" and c.seed == 1701][0]
    assert joint not in skipped  # the joint bound is independent in training


def test_plan_stage_restricts_depends_on_and_sets_after() -> None:
    d1 = next(c for c in core.cells() if c.block == "D1" and c.arch == "flat" and c.seed == 1701)
    seq = next(
        c
        for c in core.cells()
        if c.block == "D2" and c.arch == "flat" and c.seed == 1701 and c.lane_d_arm == "sequential"
    )
    argv = {c.label: pool.worker_argv("train", c.label) for c in (d1, seq)}
    both = pool.plan_stage(
        "train",
        [d1, seq],
        Path("/r"),
        IDENTITY,
        argv_for=argv,
        previous_stage_ids={seq.label: "prev-id"},
    )
    by = {t.label: t for t in both}
    assert by[seq.label].depends_on == (d1.label,) and by[d1.label].depends_on == ()
    assert by[seq.label].after == ("prev-id",) and by[d1.label].after == ()
    only = pool.plan_stage("train", [seq], Path("/r"), IDENTITY, argv_for=argv)
    assert only[0].depends_on == ()  # restricted to the cells in the plan
    assert only[0].task_id == pool.task_id("train", seq.label, IDENTITY)
    assert by[seq.label].group == "train"
    assert (
        pool.plan_stage("evaluate", [seq], Path("/r"), IDENTITY, argv_for=argv)[0].group
        == "evaluate"
    )


def test_plan_stage_refuses_non_module_commands_and_unknown_stage() -> None:
    cell = core.cells()[0]
    with pytest.raises(ValueError, match="studies.p9"):
        pool.plan_stage(
            "train", [cell], Path("/r"), IDENTITY, argv_for={cell.label: ["bash", "-c", "echo hi"]}
        )
    with pytest.raises(ValueError, match="no worker command"):
        pool.plan_stage("train", [cell], Path("/r"), IDENTITY, argv_for={})
    with pytest.raises(ValueError, match="unknown"):
        pool.plan_stage(
            "nope", [cell], Path("/r"), IDENTITY, argv_for={cell.label: pool.worker_argv("train")}
        )
    with pytest.raises(ValueError):
        pool.worker_argv("train; rm -rf /")
    assert pool.worker_argv("sim", "cell", python="py")[:3] == ["py", "-m", "studies.p9.sim"]


def test_launcher_has_no_shell_word_splitting(tmp_path: Path) -> None:
    # an argument with spaces and shell metacharacters reaches the worker as ONE argument
    marker = tmp_path / "out.txt"
    code = "import sys; open(sys.argv[1], 'w').write(repr(sys.argv[2:]))"
    t = pool.Task(
        "i",
        "train",
        "x",
        (PY, "-c", code, str(marker), "a b; echo $HOME *"),
        (),
        (),
        "train",
        marker,
        tmp_path / "f.json",
        tmp_path / "l.log",
    )
    result = run([t])
    assert status(result) == {"x": "completed"}
    assert marker.read_text() == repr(["a b; echo $HOME *"])


# --- run_stage end to end with fake workers --------------------------------------------------------------
def test_success_records_outcome_and_log(tmp_path: Path) -> None:
    t = task(tmp_path, "ok", WRITE)
    result = run([t])
    assert result.all_completed and status(result) == {"ok": "completed"}
    o = result.outcomes[0]
    assert o.returncode == 0 and o.seconds >= 0 and o.task_id == t.task_id and o.reason is None
    assert not t.failed_path.exists() and t.result_path.is_file() and t.log_path.is_file()


def test_failure_is_preserved_with_a_failed_record(tmp_path: Path) -> None:
    t = task(tmp_path, "bad", "import sys; sys.exit(3)")
    result = run([t])
    assert status(result) == {"bad": "failed"} and not result.all_completed
    record = json.loads(t.failed_path.read_text())
    assert (
        record["status"] == "failed"
        and record["returncode"] == 3
        and record["task_id"] == t.task_id
    )
    assert "not re-run" in record["note"]


def test_exit_zero_without_result_file_is_a_failure(tmp_path: Path) -> None:
    t = task(tmp_path, "empty", "pass")
    result = run([t])
    assert status(result) == {"empty": "failed"} and "no result file" in str(
        result.outcomes[0].reason
    )


def test_dependency_skip_end_to_end_independent_tasks_continue(tmp_path: Path) -> None:
    mark = tmp_path / "launched"
    mark.mkdir()
    touch = f"import sys, pathlib; pathlib.Path({str(mark)!r}, sys.argv[1].split('/')[-2]).touch(); open(sys.argv[1], 'w').write('{{}}')"
    tasks = [
        task(tmp_path, "a", "import sys; sys.exit(7)"),
        task(tmp_path, "b", touch, depends=("a",)),
        task(tmp_path, "c", touch, depends=("b",)),
        task(tmp_path, "d", touch),
        task(tmp_path, "e", touch, depends=("d",)),
    ]
    result = run(tasks)
    assert status(result) == {
        "a": "failed",
        "b": "skipped_dependency",
        "c": "skipped_dependency",
        "d": "completed",
        "e": "completed",
    }
    assert sorted(p.name for p in mark.iterdir()) == ["d", "e"]  # b and c were never launched
    for label in ("b", "c"):
        rec = json.loads((tmp_path / "cells" / label / "train.failed.json").read_text())
        assert rec["status"] == "skipped_dependency"
    assert "dependency" in str([o.reason for o in result.outcomes if o.label == "b"][0])


def test_dependent_stop_rule_applies_to_every_stage_group(tmp_path: Path) -> None:
    for stage, group in (("evaluate", "evaluate"), ("simulate", "simulate"), ("analyze", "train")):
        d = tmp_path / stage
        tasks = [
            task(d, "a", "import sys; sys.exit(1)", group=group, stage=stage),
            task(d, "b", WRITE, depends=("a",), group=group, stage=stage),
            task(d, "c", WRITE, group=group, stage=stage),
        ]
        result = run(tasks, workers={"train": 1, "evaluate": 1, "simulate": 1})
        assert status(result) == {"a": "failed", "b": "skipped_dependency", "c": "completed"}, stage


def test_killed_dependency_also_stops_dependents(tmp_path: Path) -> None:
    tasks = [
        task(tmp_path, "hog", "import time; time.sleep(30)"),
        task(tmp_path, "after", WRITE, depends=("hog",)),
    ]
    result = run(tasks, stage_cap_seconds=0.7)
    assert status(result) == {
        "hog": "killed_cap",
        "after": "not_started",
    }  # the cap ends everything; nothing launched


def test_after_requires_completed_upstream_ids(tmp_path: Path) -> None:
    t = task(tmp_path, "needs", WRITE, after=("upstream-id",))
    assert status(run([t])) == {"needs": "skipped_dependency"}  # fail closed: no completed id given
    assert status(
        run(
            [task(tmp_path / "x", "needs", WRITE, after=("upstream-id",))],
            completed_ids={"upstream-id"},
        )
    ) == {"needs": "completed"}


def test_rss_breach_kills_the_worker_and_keeps_a_record(tmp_path: Path) -> None:
    hog = "import time; blob = b'x' * 250_000_000; time.sleep(30)"
    result = run([task(tmp_path, "hog", hog)], rss_worker_bytes=120 * 1024**2, stage_cap_seconds=30)
    assert status(result) == {"hog": "killed_rss"}
    assert (
        "per-worker" in str(result.outcomes[0].reason)
        and result.outcomes[0].peak_rss_bytes > 120 * 1024**2
    )
    assert (
        json.loads((tmp_path / "cells" / "hog" / "train.failed.json").read_text())["status"]
        == "killed_rss"
    )


def test_aggregate_rss_kills_the_largest_worker_only(tmp_path: Path) -> None:
    big = "import time; blob = b'x' * 200_000_000; time.sleep(30)"
    small = f"import time; blob = b'x' * 20_000_000; time.sleep(2.5); open({str(tmp_path / 'cells' / 'small' / 'train.json')!r}, 'w').write('{{}}')"
    tasks = [task(tmp_path, "big", big), task(tmp_path, "small", small)]
    result = run(
        tasks, rss_aggregate_bytes=170 * 1024**2, rss_worker_bytes=3 * 1024**3, stage_cap_seconds=60
    )
    assert status(result) == {"big": "killed_rss", "small": "completed"}
    assert "aggregate" in str([o.reason for o in result.outcomes if o.label == "big"][0])
    assert result.peak_aggregate_rss_bytes > 170 * 1024**2


def test_stage_cap_kills_running_and_marks_pending_not_started(tmp_path: Path) -> None:
    tasks = [task(tmp_path, f"t{i}", "import time; time.sleep(30)") for i in range(4)]
    result = run(tasks, workers={"train": 2}, stage_cap_seconds=0.6)
    s = status(result)
    assert (
        sorted(s.values()) == ["killed_cap", "killed_cap", "not_started", "not_started"]
        and result.cap_hit
    )
    assert result.wall_seconds < 10
    assert all((tmp_path / "cells" / f"t{i}" / "train.failed.json").is_file() for i in range(4))


def test_total_budget_caps_the_stage_below_the_stage_cap(tmp_path: Path) -> None:
    t = task(tmp_path, "slow", "import time; time.sleep(30)")
    result = run([t], stage_cap_seconds=60, total_remaining_seconds=0.5)
    assert status(result) == {"slow": "killed_cap"} and "total wall-time cap" in str(
        result.outcomes[0].reason
    )
    budget = pool.WallBudget(total_seconds=10.0)
    budget.charge(4.0)
    assert budget.remaining() == pytest.approx(6.0)
    budget.charge(100.0)
    assert budget.remaining() == 0.0


def test_semaphore_limits_concurrency_per_group(tmp_path: Path) -> None:
    stamps = tmp_path / "stamps"
    stamps.mkdir()
    code = (
        "import sys, time, os, pathlib\n"
        f"d = pathlib.Path({str(stamps)!r}); me = d / str(os.getpid())\n"
        "t0 = time.time(); time.sleep(0.4); t1 = time.time()\n"
        "me.write_text(f'{t0} {t1}'); open(sys.argv[1], 'w').write('{}')\n"
    )
    for limit in (2, 3):
        for p in stamps.iterdir():
            p.unlink()
        d = tmp_path / f"l{limit}"
        result = run([task(d, f"t{i}", code) for i in range(6)], workers={"train": limit})
        assert result.all_completed
        spans = [tuple(map(float, p.read_text().split())) for p in stamps.iterdir()]
        overlap = max(sum(1 for (a, b) in spans if a <= t < b) for (t, _) in spans)
        assert overlap == limit


def test_separate_semaphores_for_training_and_simulation(tmp_path: Path) -> None:
    code = "import sys, time; time.sleep(0.5); open(sys.argv[1], 'w').write('{}')"
    tasks = [task(tmp_path, f"tr{i}", code, group="train") for i in range(2)] + [
        task(tmp_path, f"si{i}", code, group="simulate") for i in range(4)
    ]
    result = run(tasks, workers={"train": 2, "simulate": 4})
    assert result.all_completed
    # six tasks of two groups ran together: total time well below the serial 3 s
    assert result.wall_seconds < 2.0


def test_missing_group_slots_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no worker slots"):
        run([task(tmp_path, "x", WRITE, group="simulate")], workers={"train": 2})
    with pytest.raises(ValueError, match="duplicate"):
        run([task(tmp_path, "x", WRITE), task(tmp_path, "x", WRITE)])


def test_existing_failed_or_result_file_blocks_a_rerun(tmp_path: Path) -> None:
    t = task(tmp_path, "x", "import sys; sys.exit(1)")
    first = run([t])
    assert status(first) == {"x": "failed"}
    kept = t.failed_path.read_text()
    second = run([t])
    assert status(second) == {"x": "failed"} and "never re-run" in str(second.outcomes[0].reason)
    assert t.failed_path.read_text() == kept  # not overwritten
    ok = task(tmp_path / "y", "y", WRITE)
    assert run([ok]).all_completed
    again = run([ok])
    assert status(again) == {"y": "failed"} and "refused" in str(again.outcomes[0].reason)


# --- manifests --------------------------------------------------------------------------------------------
def test_manifest_records_every_task_hash_skips_and_status(tmp_path: Path) -> None:
    tasks = [
        task(tmp_path, "a", "import sys; sys.exit(2)"),
        task(tmp_path, "b", WRITE, depends=("a",)),
        task(tmp_path, "c", WRITE),
    ]
    result = run(tasks)
    m = pool.build_manifest(
        "train",
        tmp_path,
        "registered",
        IDENTITY,
        tasks,
        result,
        started_utc="s",
        finished_utc="f",
        workers=2,
        caps={"stage_seconds": 60.0},
    )
    assert m["status"] == "INCOMPLETE" and m["skipped_for_dependency"] == ["b"]
    by = {t["label"]: t for t in m["tasks"]}
    assert by["a"]["status"] == "failed" and by["a"]["result_sha256"] is None
    assert (
        by["c"]["status"] == "completed"
        and len(str(by["c"]["result_sha256"])) == 64
        and by["c"]["result_path"]
    )
    assert (
        by["b"]["depends_on"] == ["a"] and len(m["tasks"]) == 3
    )  # the denominator is never reduced
    path = pool.write_manifest(tmp_path, m)
    assert core.read_record(path, "stage_manifest")["run_id"] == tmp_path.name


def test_manifest_complete_only_when_every_task_completed(tmp_path: Path) -> None:
    tasks = [task(tmp_path, "a", WRITE), task(tmp_path, "b", WRITE)]
    result = run(tasks)
    m = pool.build_manifest(
        "train",
        tmp_path,
        "rehearsal",
        IDENTITY,
        tasks,
        result,
        started_utc="s",
        finished_utc=None,
        workers=2,
        caps={},
    )
    assert (
        m["status"] == "COMPLETE"
        and m["skipped_for_dependency"] == []
        and m["finished_utc"] is None
    )
    partial = pool.PoolResult(outcomes=result.outcomes[:1])
    m2 = pool.build_manifest(
        "train",
        tmp_path,
        "rehearsal",
        IDENTITY,
        tasks,
        partial,
        started_utc="s",
        finished_utc="f",
        workers=2,
        caps={},
    )
    assert m2["status"] == "INCOMPLETE" and {t["status"] for t in m2["tasks"]} == {
        "completed",
        "not_started",
    }


def test_peak_rss_is_positive() -> None:
    assert pool.peak_rss_bytes() > 1_000_000


def test_completed_ids_from_manifests() -> None:
    m = {"tasks": [{"task_id": "x", "status": "completed"}, {"task_id": "y", "status": "failed"}]}
    assert pool.completed_ids_from([m]) == {"x"}


# --- registered preconditions ------------------------------------------------------------------------------
def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def make_repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    (repo / "studies" / "p9").mkdir(parents=True)
    (repo / "configs").mkdir()
    (repo / core.SPEC).parent.mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "studies" / "p9" / "a.py").write_text("x = 1\n")
    (repo / core.DEFAULT_CONFIG).write_text("a = 1\n")
    (repo / core.SPEC).write_text("spec\n")
    (repo / "tests" / "test_p9_x.py").write_text("def test(): pass\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "freeze")
    return repo, git(repo, "rev-parse", "HEAD")


OK_VERIFIER = lambda repo, commit: {"ok": True, "problems": []}  # noqa: E731
BAD_VERIFIER = lambda repo, commit: {"ok": False, "problems": ["src/arborlm/x.py: differs"]}  # noqa: E731


def fake_cell() -> core.Cell:
    return core.cells()[0]


@pytest.fixture(autouse=True)
def permissive_worker_shape(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    """Flow tests use ``python -c`` fake workers; the shape check has its own test."""
    if request.node.name != "test_plan_stage_refuses_non_module_commands_and_unknown_stage":
        monkeypatch.setattr(pool, "validate_worker_argv", lambda argv: None)


def _execute_with_code(
    tmp_path: Path,
    repo: Path,
    mode: str,
    commit: str | None,
    verifier: pool.FrozenVerifier,
    code: str = "",
) -> tuple[core.StageManifest, Path]:
    cell = fake_cell()
    result = tmp_path / "run" / "cells" / cell.label / "train.json"
    worker = "import sys, pathlib; pathlib.Path(sys.argv[1]).touch(); pathlib.Path(sys.argv[2]).write_text('{}')"
    return pool.execute_stage(
        "train",
        mode,
        [cell],
        tmp_path / "run",
        IDENTITY,
        argv_for={cell.label: [PY, "-c", worker, str(tmp_path / "launched"), str(result)]},
        repo=repo,
        freeze_commit=commit,
        workers={"train": 2},
        caps=pool.StageCaps(30.0),
        verify_frozen=verifier,
        poll=0.02,
    )


def test_registered_stage_runs_when_clean_and_frozen(tmp_path: Path) -> None:
    repo, commit = make_repo(tmp_path)
    manifest, path = _execute_with_code(tmp_path, repo, "registered", commit, OK_VERIFIER, "")
    assert manifest["status"] == "COMPLETE" and manifest["mode"] == "registered" and path.is_file()
    assert (tmp_path / "launched").exists()


def test_registered_stage_refuses_a_dirty_tree_before_launching(tmp_path: Path) -> None:
    repo, commit = make_repo(tmp_path)
    (repo / "studies" / "p9" / "a.py").write_text("x = 2\n")  # unstaged change
    with pytest.raises(pool.StageRefused, match="not clean"):
        _execute_with_code(tmp_path, repo, "registered", commit, OK_VERIFIER, "")
    assert not (tmp_path / "launched").exists() and not (tmp_path / "run").exists()


def test_registered_stage_refuses_untracked_file(tmp_path: Path) -> None:
    repo, commit = make_repo(tmp_path)
    (repo / "stray.txt").write_text("x")
    with pytest.raises(pool.StageRefused, match="not clean"):
        _execute_with_code(tmp_path, repo, "registered", commit, OK_VERIFIER, "")
    assert not (tmp_path / "launched").exists()


def test_registered_stage_refuses_missing_or_unknown_freeze(tmp_path: Path) -> None:
    repo, commit = make_repo(tmp_path)
    with pytest.raises(pool.StageRefused, match="requires --freeze-commit"):
        _execute_with_code(tmp_path, repo, "registered", None, OK_VERIFIER, "")
    with pytest.raises(pool.StageRefused, match="not a commit"):
        _execute_with_code(tmp_path, repo, "registered", "0" * 40, OK_VERIFIER, "")
    assert not (tmp_path / "launched").exists()


def test_registered_stage_refuses_a_wrong_freeze(tmp_path: Path) -> None:
    repo, first = make_repo(tmp_path)
    (repo / "studies" / "p9" / "a.py").write_text("x = 2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change after freeze")
    with pytest.raises(pool.StageRefused, match=r"studies at HEAD differs"):
        _execute_with_code(tmp_path, repo, "registered", first, OK_VERIFIER, "")
    # a changed P9 test file also refuses
    (repo / "tests" / "test_p9_x.py").write_text("def test(): assert True\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change test")
    head = git(repo, "rev-parse", "HEAD")
    (repo / "tests" / "test_p9_x.py").write_text("def test(): assert 1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "change test again")
    with pytest.raises(pool.StageRefused, match=r"test_p9"):
        _execute_with_code(tmp_path, repo, "registered", head, OK_VERIFIER, "")
    assert not (tmp_path / "launched").exists()


def test_registered_stage_refuses_when_frozen_inputs_do_not_verify(tmp_path: Path) -> None:
    repo, commit = make_repo(tmp_path)
    with pytest.raises(pool.StageRefused, match="frozen inputs do not verify"):
        _execute_with_code(tmp_path, repo, "registered", commit, BAD_VERIFIER, "")
    assert not (tmp_path / "launched").exists()


def test_registered_stage_refuses_a_non_ancestor_freeze(tmp_path: Path) -> None:
    repo, commit = make_repo(tmp_path)
    git(repo, "checkout", "-q", "-b", "side")
    (repo / "extra.txt").write_text("x")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "side commit")
    side = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-")
    with pytest.raises(pool.StageRefused, match="not an ancestor"):
        _execute_with_code(tmp_path, repo, "registered", side, OK_VERIFIER, "")
    assert commit != side


def test_registered_worker_counts_are_checked_and_rehearsal_needs_no_freeze(tmp_path: Path) -> None:
    repo, commit = make_repo(tmp_path)
    cell = fake_cell()
    with pytest.raises(pool.StageRefused, match="training workers"):
        pool.execute_stage(
            "train",
            "registered",
            [cell],
            tmp_path / "r",
            IDENTITY,
            argv_for={cell.label: [PY, "-c", "pass"]},
            repo=repo,
            freeze_commit=commit,
            workers={"train": 1},
            caps=pool.StageCaps(5.0),
            verify_frozen=OK_VERIFIER,
        )
    with pytest.raises(pool.StageRefused, match="simulation workers"):
        pool.validate_workers("registered", {"train": 2, "simulate": 5})
    pool.validate_workers("registered", {"train": 4, "simulate": 4})
    pool.validate_workers("rehearsal", {"train": 1})
    (repo / "dirty.txt").write_text("x")
    manifest, _ = _execute_with_code(tmp_path, repo, "rehearsal", None, BAD_VERIFIER, "")
    assert manifest["status"] == "COMPLETE" and manifest["mode"] == "rehearsal"


def test_stage_with_a_failing_cell_still_writes_an_incomplete_manifest(tmp_path: Path) -> None:
    repo, commit = make_repo(tmp_path)
    cells = [c for c in core.cells() if c.block == "D1" and c.arch == "flat" and c.seed == 1701] + [
        c
        for c in core.cells()
        if c.block == "D2" and c.arch == "flat" and c.seed == 1701 and c.lane_d_arm == "sequential"
    ]
    run_dir = tmp_path / "run"
    ok_code = "import sys, pathlib; p = pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True); p.write_text('{}')"
    argv_for = {
        cells[0].label: [PY, "-c", "import sys; sys.exit(5)"],
        cells[1].label: [PY, "-c", ok_code, str(run_dir / "cells" / cells[1].label / "train.json")],
    }
    manifest, path = pool.execute_stage(
        "train", "rehearsal", cells, run_dir, IDENTITY, argv_for=argv_for, repo=repo, freeze_commit=None,
        workers={"train": 2}, caps=pool.StageCaps(30.0), poll=0.02,
    )  # fmt: skip
    assert manifest["status"] == "INCOMPLETE" and path.is_file()
    by = {t["label"]: t["status"] for t in manifest["tasks"]}
    assert by == {cells[0].label: "failed", cells[1].label: "skipped_dependency"}
    assert manifest["skipped_for_dependency"] == [cells[1].label]


def test_plan_listing_cli(capsys: pytest.CaptureFixture[str]) -> None:
    assert pool.main(["plan", "--stage", "train", "--block", "D1", "--block", "D2"]) == 0
    listing = json.loads(capsys.readouterr().out)
    assert len(listing) == 20 and sum(1 for r in listing if r["depends_on"]) == 12
    assert pool.main(["plan", "--stage", "simulate", "--block", "A3"]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 2
