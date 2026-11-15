# ruff: noqa: E501
"""P10S0 governance of the registered path (the independent audit's M1-M10 and the lead's rulings): registered mode only through the driver and with the frozen plan, one refusal per override, the commit that
added the plan, the A5-D strings in every output through one emit path, the post-freeze records, the reserve in the headroom rule, the gates cap on thirteen draws, the cut-3 label, the acceptance banner read
from the record, the generation cap set by the rehearsal, the busy-process rehearsal, WX's AUC and i. Test seeds 920001-920999 only. Self-check only: not independent review, not Astra validation, not human approval."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9 import (
    controls,  # noqa: E402
    pool,  # noqa: E402
)
from studies.p10s0 import (  # noqa: E402
    analysis,
    budget,
    core,
    evaluate,
    model,
    report,
    stages,
    train,
)
from studies.p10s0 import classes as C  # noqa: E402
from studies.p10s0 import synthetic as syn  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CAPS = "studies/p10s0/freeze/stage_caps.json"


# --- M2: one refusal per override ------------------------------------------------------------------------------------------------------------------------
OVERRIDES = [
    ["--stage-cap-seconds", "1"], ["--ledger-root", "/tmp/x"], ["--experiments-root", "/tmp/x"], ["--rss-worker-bytes", "1"], ["--rss-aggregate-bytes", "1"], ["--synthetic-backbone"], ["--only", "Q1-A0-2K4K-d01-j0"],
    ["--cut3"], ["--restore-split", "4"], ["--dry"], ["--workers", "2"], ["--updates", "4"], ["--draw", "3"], ["--reserve", "1"], ["--repo", "/tmp/x"], ["--arm-selection", "/tmp/x"], ["--projection", "/tmp/x"],
    ["--busy-processes", "2"], ["--dry-candidate", "A5-D"], ["--block", "wx"], ["--results-dir", "/tmp/x"], ["--labels", "a"], ["--item", "A0,2K/4K,main"], ["--arm-selection-sha256", "0"],
    ["--gates-per-draw-seconds", "1"], ["--generate-manifest", "x"], ["--test-profile"], ["--test-candidate", "A1"], ["--i-understand-freeze-time"], ["--generation-cap-from-config"], ["--out", "x"],
]  # fmt: skip


@pytest.mark.parametrize("override", OVERRIDES, ids=[o[0] for o in OVERRIDES])
def test_the_registered_driver_refuses_every_override(override: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = stages.main(["registered", "q1", "--run-dir", str(tmp_path), "--freeze-commit", "abc", "--caps", CAPS, *override])
    err = capsys.readouterr().err
    assert code == 2 and "accepts no override" in err and override[0] in err, err
    assert not any(tmp_path.iterdir())  # nothing was started


def test_the_driver_accepts_only_the_run_directory_the_freeze_commit_and_the_caps_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.override_violations(stages.build_parser().parse_args(["registered", "q1", "--run-dir", str(tmp_path), "--freeze-commit", "abc", "--caps", CAPS]), stages.REGISTERED_ALLOWED) == []
    code = stages.main(["registered", "q1", "--run-dir", str(tmp_path), "--freeze-commit", "abc", "--caps", "elsewhere.json"])
    assert code == 2  # the preconditions refuse first (not clean or no such commit); a wrong caps path is refused after them
    assert "REFUSED" in capsys.readouterr().err
    assert stages.main(["registered", "q1", "--mode", "check", "--run-dir", str(tmp_path)]) == 2


def test_every_option_of_the_common_parser_is_covered_by_the_override_check(tmp_path: Path) -> None:
    """The check runs over every option of the parser, so a future option cannot be forgotten: set each non-allowed destination to a non-default value and see it refused."""
    parser = stages._common_parser()
    defaults = vars(parser.parse_args([]))
    base = stages.build_parser().parse_args(["registered", "q1", "--run-dir", str(tmp_path)])
    for dest, default in defaults.items():
        if dest in stages.REGISTERED_ALLOWED:
            continue
        probe = stages.build_parser().parse_args(["registered", "q1", "--run-dir", str(tmp_path)])
        setattr(probe, dest, (not default) if isinstance(default, bool) else ("x" if default is None else default + 1 if isinstance(default, int | float) else default + "x"))
        assert stages.override_violations(probe, stages.REGISTERED_ALLOWED) == ["--" + dest.replace("_", "-")], dest
    assert stages.override_violations(base, stages.REGISTERED_ALLOWED) == []


# --- M1: typed commands cannot reach registered mode, and workers re-check -------------------------------------------------------------------------------------
@pytest.mark.parametrize("argv", [["train", "--block", "q1"], ["gates"], ["analyze"], ["report"], ["q1-gate"]])
def test_a_typed_command_has_no_default_mode_and_cannot_ask_for_registered_mode(argv: list[str], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert stages.main([*argv, "--run-dir", str(tmp_path)]) == 2
    assert "has no default mode" in capsys.readouterr().err
    assert stages.main([*argv, "--run-dir", str(tmp_path), "--mode", "registered"]) == 2
    assert "not a registered stage" in capsys.readouterr().err
    assert not any(tmp_path.iterdir())


def test_a_worker_in_registered_mode_refuses_without_the_plan_and_with_overrides(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for extra in (["--synthetic-backbone"], ["--dry"], [], ["--updates", "3"], ["--repo", "/tmp/x"]):
        assert stages.main(["work", "train", "--mode", "registered", "--run-dir", str(tmp_path), "--labels", "Q1-A0-2K4K-d01-j0", *extra]) in (2, 1)
        err = capsys.readouterr().err
        if extra:
            assert extra[0] in err or "refused" in err.lower(), (extra, err)
    assert stages.main(["work", "train", "--run-dir", str(tmp_path), "--labels", "x"]) == 2  # a worker without a mode


def test_only_generation_and_the_driver_accept_registered_mode_before_the_freeze(tmp_path: Path) -> None:
    ns = stages.build_parser().parse_args(["generate", "--mode", "registered", "--run-dir", str(tmp_path), "--stage-cap-seconds", "5"])
    with pytest.raises(pool.StageRefused, match="freeze-time"):
        stages.cmd_generate(ns)
    ns = stages.build_parser().parse_args(["generate", "--mode", "registered", "--run-dir", str(tmp_path), "--i-understand-freeze-time"])
    with pytest.raises(pool.StageRefused, match="--generation-cap-from-config"):
        stages.cmd_generate(ns)
    ns = stages.build_parser().parse_args(["generate", "--mode", "registered", "--run-dir", str(tmp_path), "--i-understand-freeze-time", "--generation-cap-from-config", "--stage-cap-seconds", "9"])
    with pytest.raises(pool.StageRefused, match="accepts no override"):
        stages.cmd_generate(ns)
    assert not any(tmp_path.iterdir())


def test_registered_generation_needs_the_recorded_acceptance_the_run_decision_and_a_set_generation_cap(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "docs/decisions").mkdir(parents=True)
    (repo / "configs").mkdir()
    (repo / "docs/decisions/ADR-0019-robust-sparse-address-learning.md").write_text("no acceptance here\n")
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml())

    def attempt() -> str:
        ns = stages.build_parser().parse_args(["generate", "--mode", "registered", "--run-dir", str(tmp_path / "run"), "--i-understand-freeze-time", "--generation-cap-from-config", "--repo", str(repo)])
        ns.repo = None  # the repository override is refused for registered generation; the guards under test read the repository the code is in
        return ns

    # the real tree has the acceptance and no DECISION file: the decision file is what is missing
    with pytest.raises(pool.StageRefused, match="DECISION.md|accepted|acceptance|provisional"):
        stages.cmd_generate(attempt())
    assert core.p9ii_acceptance(repo)["accepted"] is False and core.p9ii_acceptance(ROOT)["accepted"] is True


# --- the commit that added the plan (M1) ---------------------------------------------------------------------------------------------------------------
def repo_with_plan(tmp: Path, *, plan_in_commit: bool) -> tuple[Path, str]:
    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(tmp), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@t", *a], capture_output=True, check=True, text=True).stdout.strip()

    tmp.mkdir(parents=True)
    git("init", "-q")
    for rel, text in (("studies/p10s0/a.py", "x = 1\n"), (str(core.DEFAULT_CONFIG), "a = 1\n"), (core.SPEC, "adr\n"), ("tests/test_p10s0_x.py", "def test_x(): pass\n")):
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp / rel).write_text(text)
    if plan_in_commit:
        (tmp / "studies/p10s0/freeze").mkdir(parents=True, exist_ok=True)
        (tmp / "studies/p10s0/freeze/plan.json").write_text("{}")
    git("add", "-A")
    git("commit", "-q", "-m", "c1")
    return tmp, git("rev-parse", "HEAD")


def test_head_is_not_a_freeze_the_commit_must_be_the_one_that_added_the_plan(tmp_path: Path) -> None:
    repo, head = repo_with_plan(tmp_path / "none", plan_in_commit=False)
    with pytest.raises(pool.StageRefused, match="does not exist at"):
        stages.check_preconditions("registered", repo, head)
    repo, c1 = repo_with_plan(tmp_path / "later", plan_in_commit=True)
    (repo / "studies/p10s0/b.py").write_text("y = 2\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "c2"], check=True, capture_output=True)
    head2 = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, check=True, text=True).stdout.strip()
    with pytest.raises(pool.StageRefused, match="studies at HEAD differs"):
        stages.check_preconditions("registered", repo, c1)  # c1 added the plan but studies changed since
    with pytest.raises(pool.StageRefused, match="not the commit that added"):
        stages.check_preconditions("registered", repo, head2)  # a later commit is not a freeze, even with an identical plan on disk
    with pytest.raises(pool.StageRefused, match="frozen inputs do not verify"):
        stages.check_preconditions("registered", repo_with_plan(tmp_path / "ok", plan_in_commit=True)[0], repo_with_plan(tmp_path / "ok2", plan_in_commit=True)[1] if False else subprocess.run(["git", "-C", str(tmp_path / "ok"), "rev-parse", "HEAD"], capture_output=True, check=True, text=True).stdout.strip())


def test_records_after_the_freeze_outside_the_hashed_paths_do_not_deadlock_the_run(tmp_path: Path) -> None:
    """The lead's run decision (results/p10s0-freeze-<date>/DECISION.md) and results are committed after the freeze: none of the paths the preconditions compare changes (M5)."""
    repo, freeze = repo_with_plan(tmp_path / "r", plan_in_commit=True)
    (repo / "results/p10s0-freeze-2026-11-16").mkdir(parents=True)
    (repo / "results/p10s0-freeze-2026-11-16/DECISION.md").write_text("decision\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "decision"], check=True, capture_output=True)
    with pytest.raises(pool.StageRefused) as exc:
        stages.check_preconditions("registered", repo, freeze)
    assert "frozen inputs do not verify" in str(exc.value) and "differs from the freeze commit" not in str(exc.value)  # only the stand-in repository's missing src/ stops it, not the later commit


def test_the_readme_states_the_post_freeze_rules() -> None:
    text = (ROOT / "studies/p10s0/freeze/README.md").read_text().lower()
    for needle in ("results/p10s0-freeze-<date>/DECISION.md", "after the freeze the cap is fixed", "nothing is recorded in ADR-0020 after the freeze commit", "WX runs before the probe", "set-generation-cap", "--gates-per-draw-seconds", "e2e", "the commit that added `plan.json`"):
        assert needle.lower() in text, needle


# --- M3: the A5-D strings in every output, through one emit path ---------------------------------------------------------------------------------------------
def a5d_run() -> Any:
    return syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D")


def test_stamp_adds_the_three_strings_beside_every_a5d_entry_and_at_the_top() -> None:
    out = core.stamp({"arms": {"A5-D": {"2K/4K": {"label": "RELIABLE", "arm": "A5-D"}}, "A1": {"x": 1}}, "outcome": {"arm": "A5-D", "label": "QUALIFIED"}, "hypotheses": {"H20-R (A5-D, 2K/4K)": {"reading": "supported"}}, "candidate": "A5-D"})
    assert out["arms"]["A5-D"]["2K/4K"]["a5d_provenance"] == core.a5d_fields() and "a5d_provenance" not in out["arms"]["A5-D"] and out["outcome"]["a5d_provenance"] == core.a5d_fields() and out["hypotheses"]["H20-R (A5-D, 2K/4K)"]["a5d_provenance"] == core.a5d_fields()
    assert out["a5d_provenance"] == core.a5d_fields() and "a5d_provenance" not in out["arms"]["A1"]
    assert core.stamp({"x": 1}) == {"x": 1}  # nothing about A5-D: nothing added
    with pytest.raises(ValueError, match="without the fourth-arm string"):
        core.assert_provenance("the label RELIABLE for A5-D")
    core.assert_provenance(json.dumps(out, ensure_ascii=False))
    core.assert_provenance("no mention of the fourth arm here")


def test_every_machine_product_of_an_a5d_positive_label_carries_the_strings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    res = analysis.analyze(a5d_run())
    assert res["outcome"]["row"] == 4 and res["outcome"]["arm"] == "A5-D"
    texts = {"analysis result": json.dumps(res, ensure_ascii=False)}
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    core.write_record(run_dir / "analysis.json", {**core.envelope("analysis"), "result": res})
    core.write_record(run_dir / "q1_gate.json", {**core.envelope("q1_gate"), "candidate": "A5-D", "outcome": "ADDRESSING-QUALIFIED (4,096 AND 16,384)", "blocks": {"wx": {"run": True, "status": None}, "probe": {"run": True, "status": None}}})
    paths = report.write_report(run_dir, tmp_path / "out")
    for name in ("analysis.json", "q1_gate.json"):
        texts[name] = json.dumps(json.loads((run_dir / name).read_text()), ensure_ascii=False)
    texts["results.json"] = json.dumps(json.loads(paths[1].read_text()), ensure_ascii=False)
    texts["classes.csv"], texts["RESULTS.md"] = paths[2].read_text(), paths[0].read_text()
    core.emit_stdout({"candidate": "A5-D", "row": 4})
    texts["stdout"] = capsys.readouterr().out
    for name, text in texts.items():
        assert core.mentions_a5d(text) and core.has_provenance(text), name
        assert report.check_product_provenance(text), name
    assert paths[2].read_text().startswith("# FOURTH ARM: A5-D") and report.check_a5d_provenance(texts["RESULTS.md"]) == []
    q1 = json.loads((run_dir / "q1_gate.json").read_text())
    assert q1["a5d_provenance"] == core.a5d_fields()


def test_a_product_that_does_not_name_a5d_gets_nothing_added(tmp_path: Path) -> None:
    core.write_record(tmp_path / "q.json", {**core.envelope("q1_gate"), "candidate": "A1", "blocks": {}})
    assert "a5d_provenance" not in json.loads((tmp_path / "q.json").read_text())


def test_the_emit_path_cannot_be_bypassed_for_products_by_a_missing_stamp(tmp_path: Path) -> None:
    """``write_record`` of an analysis or q1_gate record stamps and asserts; a record built by hand with an A5-D candidate and no strings still leaves with them."""
    core.write_record(tmp_path / "a.json", {**core.envelope("analysis"), "result": {"outcome": {"arm": "A5-D", "label": "ADDRESSING-QUALIFIED"}}})
    data = json.loads((tmp_path / "a.json").read_text())
    assert data["result"]["outcome"]["a5d_provenance"] == core.a5d_fields() and data["a5d_provenance"]["provenance_sentence"] == core.PROVENANCE_SENTENCE


# --- M4: no S0 test depends on the absence of review, results or freeze files -------------------------------------------------------------------------------------
def test_no_s0_test_asserts_that_a_freeze_file_is_absent() -> None:
    for path in sorted((ROOT / "tests").glob("test_p10s0_*.py")):
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        assert 'not (ROOT / "studies/p10s0/freeze/plan.json").exists()' not in text and "assert not (ROOT / \"studies/p10s0/freeze/stage_caps.json\")" not in text, path.name


# --- M6, M8: the reserve and the gates cap ----------------------------------------------------------------------------------------------------------------------
H = 3600.0


def test_both_headroom_evaluations_count_the_rehearsed_analysis_and_report_time_doubled() -> None:
    reserve = 0.05 * H
    pre = budget.pre_q1_decision(0.0, 0.8 * H, 3.89 * H, 2.71 * H, reserve_seconds=reserve)
    assert pre.action == "full" and pre.required_seconds == pytest.approx(2 * (0.8 + 3.89 + 0.05) * H)
    edge = (16 * H / 2) - (0.8 * H + reserve)  # a Q1 projection that exactly fills the cap with the reserve counted
    assert budget.pre_q1_decision(0.0, 0.8 * H, edge, 1.0 * H, reserve_seconds=reserve).action == "full"
    assert budget.pre_q1_decision(0.0, 0.8 * H, edge + 1.0, 1.0 * H, reserve_seconds=reserve).action == "cut3"
    assert budget.pre_q1_decision(0.0, 0.8 * H, edge + 1.0, 1.0 * H).action == "full"  # without the reserve it would have started and left too little for the analysis
    both = budget.post_q1_decision(4.0 * H, 0.5 * H, 2.0 * H, reserve_seconds=reserve)
    assert (both.wx, both.probe) == (True, True)
    full = (16 * H - 4.0 * H) / 2 - 0.5 * H - reserve
    assert budget.post_q1_decision(4.0 * H, 0.5 * H, full, reserve_seconds=reserve).probe is True and budget.post_q1_decision(4.0 * H, 0.5 * H, full + 1.0, reserve_seconds=reserve).probe is False
    assert budget.post_q1_decision(4.0 * H, 0.5 * H, full + 1.0).probe is True  # the reserve changes the decision at the edge and nowhere else
    assert budget.post_q1_decision(15.9 * H, 0.5 * H, 2.0 * H, reserve_seconds=0.0).wx is False


def test_the_gates_cap_is_measured_on_thirteen_draws() -> None:
    assert budget.gates_measured_seconds(100.0, 5.0) == 100.0 + 12 * 5.0
    rates = {item: budget.Rate(0.01, 1, 1, 1.0) for item in budget.rehearsal_items()}
    caps = budget.caps_table(rates, gates_wall_seconds=100, gates_per_draw_seconds=5, analysis_wall_seconds=3, report_wall_seconds=2, generate_wall_seconds=10)
    assert caps["gates"] == 2 * 160 and caps["measured"]["gates"] == 160 and caps["measured"]["reserve_analysis_report"] == 5 and caps["measured"]["gates_per_draw"] == 5
    with pytest.raises(ValueError, match="per-draw"):
        budget.caps_table(rates, gates_wall_seconds=100, gates_per_draw_seconds=0, analysis_wall_seconds=3, report_wall_seconds=2, generate_wall_seconds=10)


def test_the_caps_command_refuses_a_missing_measurement(tmp_path: Path) -> None:
    assert stages.main(["caps", "--projection", str(tmp_path / "p.json"), "--out", str(tmp_path / "c.json"), "--dry", "--gates-wall-seconds", "5", "--analysis-wall-seconds", "1", "--report-wall-seconds", "1", "--generate-wall-seconds", "1"]) in (1, 2)


# --- M9, M10 ----------------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_banner_reads_the_acceptance_from_the_recorded_fact() -> None:
    accepted = report.banner_text({"p9ii_acceptance": core.p9ii_acceptance(ROOT)})
    assert "The human lead accepted the P9-II outcome as registered" in accepted and "yes I do, yes we can raise to 16 and I approve the package" in accepted and "has not accepted" not in accepted
    none = report.banner_text({"p9ii_acceptance": {"accepted": False, "source": "ADR-0019 section 16"}})
    assert "acceptance of the P9-II outcome is not recorded in this tree" in none and "accepted the P9-II outcome" not in none
    assert "was not recorded in this result" in report.banner_text({})
    res = analysis.analyze(syn.make_run(acceptance={"accepted": False, "source": "x"}))
    assert "is not recorded in this tree" in report.render_markdown(res).splitlines()[2]
    assert "accepted the P9-II outcome as registered" in report.render_markdown(analysis.analyze(syn.make_run())).splitlines()[2]


def test_p9ii_acceptance_is_a_fact_read_from_adr_0019() -> None:
    a = core.p9ii_acceptance(ROOT)
    assert a["accepted"] and a["quote"] == core.P9II_ACCEPTANCE_QUOTE and a["source_sha256"]
    assert core.p9ii_acceptance(ROOT / "nowhere")["accepted"] is False


def test_the_cut_3_label_is_printed_wherever_the_adr_requires() -> None:
    res = analysis.analyze(syn.make_run(cut3=True, patterns=syn.a0_unreliable(), candidate="A5-D"))
    md = report.render_markdown(res)
    assert core.CUT3_LABEL == "one initialization seed per draw at 16,384" and res["cut3_label"] == core.CUT3_LABEL and core.CUT3_LABEL in res["outcome"]["label"]
    assert md.count(core.CUT3_LABEL) >= 3 and "Cut 3 of section 10.4 applies" in md and f"(label: {core.CUT3_LABEL})" in md
    assert core.CUT3_LABEL not in report.render_markdown(analysis.analyze(syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D")))
    assert res["arms"]["A5-D"]["8K/16K"]["pooled"]["text"].startswith("NOT AVAILABLE") and not res["arms"]["A5-D"]["2K/4K"]["pooled"]["text"].startswith("NOT AVAILABLE")  # m10


# --- the generation cap ---------------------------------------------------------------------------------------------------------------------------------------------------
def test_the_generation_cap_is_set_by_the_rehearsal_and_validated(tmp_path: Path) -> None:
    g = core.set_generation_cap(10.0)
    assert g == {"cap_seconds": 60.0, "provisional": False, "measured_seconds": 10.0, "floor_seconds": 60.0}
    assert core.set_generation_cap(45.0)["cap_seconds"] == 90.0
    for bad in (0.0, -1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            core.set_generation_cap(bad)
    cfg = tmp_path / "c.toml"
    cfg.write_text(core.render_config_toml(g))
    assert core.load_config(cfg)["generation"]["cap_seconds"] == 60.0 and core.generation_block(ROOT / core.DEFAULT_CONFIG)["provisional"] is True
    cfg.write_text(core.render_config_toml({**g, "cap_seconds": 59.0}))
    with pytest.raises(ValueError, match="below the floor"):
        core.load_config(cfg)
    cfg.write_text(core.render_config_toml({**g, "cap_seconds": 120.0}))  # not 2 x measured
    with pytest.raises(ValueError, match="must be max"):
        core.load_config(cfg)
    cfg.write_text(core.render_config_toml().replace("floor_seconds = 60.0", "floor_seconds = 30.0"))
    with pytest.raises(ValueError):
        core.load_config(cfg)


def test_set_generation_cap_command_rewrites_the_config_from_a_generation_manifest(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml())
    manifest = tmp_path / "manifest.json"
    core.write_record(manifest, {**core.envelope("stage_manifest"), "stage": "generate-p10s0-rehearsal", "status": "COMPLETE", "tasks": [{"seconds": 40.0}]})
    assert stages.main(["set-generation-cap", "--repo", str(repo), "--generate-manifest", str(manifest)]) == 0
    g = core.generation_block(repo / core.DEFAULT_CONFIG)
    assert g == {"cap_seconds": 80.0, "provisional": False, "measured_seconds": 40.0, "floor_seconds": 60.0}
    core.write_record(manifest, {**core.envelope("stage_manifest"), "stage": "generate-p10s0-rehearsal", "status": "INCOMPLETE", "tasks": [{"seconds": 40.0}]})
    assert stages.main(["set-generation-cap", "--repo", str(repo), "--generate-manifest", str(manifest)]) == 2


def test_freeze_plan_refuses_while_the_generation_cap_is_provisional_and_checks_the_profile(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("stages_tests", ROOT / "tests/test_p10s0_stages.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # the fixtures of the freeze-plan tests
    repo, run, sel, proj = mod.make_run_dir_with_plan(tmp_path)
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml())  # provisional
    argv = ["freeze-plan", "--repo", str(repo), "--run-dir", str(run), "--arm-selection", str(sel), "--projection", str(proj), "--out", str(tmp_path / "plan.json")]
    assert stages.main(argv) == 2 and not (tmp_path / "plan.json").exists()
    (repo / core.DEFAULT_CONFIG).write_text(core.render_config_toml(core.set_generation_cap(30.0)))
    assert stages.main([*argv, "--test-profile"]) == 2  # the run directory has no TEST_PROFILE marker
    assert stages.main([*argv, "--test-candidate", "A1"]) == 2  # a test candidate outside the test profile


# --- m3, item 8 ------------------------------------------------------------------------------------------------------------------------------------------------------
def test_g10_executes_only_the_auditor_script_the_plan_pinned(tmp_path: Path) -> None:
    from studies.p10s0 import arm_selection, gates

    record = arm_selection.build_record(ROOT, commit_of=False)
    c5, c2 = tmp_path / "c5_rev2_mapping_and_consistency.py", tmp_path / "c2_mapping_enumeration.py"
    c5.write_text('def part1():\n    print("  rule-vs-table disagreements: none")\n')
    c2.write_text("X = 1\n")
    from arborlm.io import file_sha256

    pins = {c5.name: file_sha256(c5), c2.name: file_sha256(c2)}
    ok = gates.g10_check(record, ROOT, run_script=True, script=c5, pinned=pins)
    assert ok["passed"] and ok["auditor_script"]["sibling_sha256"] == pins[c2.name]
    c2.write_text("X = 2\n")  # the sibling changed after the freeze: nothing is run
    bad = gates.g10_check(record, ROOT, run_script=True, script=c5, pinned=pins)
    assert not bad["passed"] and bad["auditor_script_run"] is False and any("c2_mapping_enumeration.py" in p for p in bad["problems"])
    assert "implementer's second reading" in (gates.independent_evaluation.__doc__ or "").replace("IMPLEMENTER'S", "implementer's")


def test_g9_asserts_p9ii_s_test_seed_constants_directly() -> None:
    from studies.p9ii import core as p9iicore
    from studies.p10s0 import gates

    g = gates.g9_check(ROOT)
    assert g["passed"] and (p9iicore.TEST_SEED_BASE, p9iicore.TEST_SEED_TOP) == (910001, 919999)
    assert all(core.TEST_SEED_BASE <= v <= core.TEST_SEED_TOP for k in range(1, 14) for v in core.registered_set(k, "test").values())


# --- m5, m6, m7 -------------------------------------------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def backbone() -> Any:
    torch.manual_seed(0)
    return controls.synthetic_backbone()


def test_wx_records_the_descriptive_auc_and_the_others_do_not(backbone: Any, tmp_path: Path) -> None:
    spec = core.test_set(3)
    draw = syn.tiny_data(spec, 2048)
    rows = evaluate.corpus_rows(syn.tiny_corpus())[:64]
    for arm in ("WX-A5-D", "A5-D"):
        cell = core.make_cell(arm, "2K/4K")
        job = train.Job(cell=cell, mode="dry", data=draw, stream=train.training_stream_for(draw, 128), backbone=backbone, out_dir=tmp_path / arm, init_seed=920041, r1_seed=draw.seeds.r1_codes, target_seed=spec.target_seed("2K/4K", 0), unit=8, diag_every=4, max_updates=8, snapshots=(8,))
        ex = train.run_job(job)
        rec = evaluate.evaluate_readout(cell, ex.model, draw, 128, 8, frozen_backbone=backbone, rows=rows, target_seed=job.target_seed, swap_seed=spec.swap_seed(2048))
        assert ("answer_site_auc" in rec) == (arm == "WX-A5-D")
        if arm == "WX-A5-D":
            a = rec["answer_site_auc"]
            assert 0.0 <= a["auc"] <= 1.0 and a["answer_sites"] == 8 * a["contexts"] and a["other_positions"] == 55 * a["contexts"] and "descriptive" in a["note"]
        obs = C.observation_from_eval(json.loads(json.dumps(core.jsonable(rec))))
        assert (obs.auc == obs.auc) == (arm == "WX-A5-D") and 0.0 <= obs.bits_a <= 5.0 and obs.bits_b == obs.bits_b


def test_the_answer_site_auc_is_exact_on_a_hand_built_query(backbone: Any) -> None:
    spec = core.test_set(3)
    draw = syn.tiny_data(spec, 2048)
    m = model.build_model("WX-A5-D", 4096, 920041, backbone)
    first = evaluate.answer_site_auc(m, draw, 128, max_contexts=16)
    again = evaluate.answer_site_auc(m, draw, 128, max_contexts=16)
    assert first == again and first["contexts"] == 16  # deterministic
    with torch.no_grad():
        m.addition.wq.zero_()  # every position has the same (zero, normalized to zero) query: every score ties and the AUC is exactly one half
    assert evaluate.answer_site_auc(m, draw, 128, max_contexts=16)["auc"] == 0.5


def test_the_analysis_reports_wx_auc_and_i_and_the_report_prints_them() -> None:
    res = analysis.analyze(syn.make_run(patterns=syn.a0_unreliable(), candidate="A5-D"))
    wx = res["record_length"]["celltypes"]["2K/4K"]
    assert wx["auc_median"] == pytest.approx(0.8) and wx["bits_median"] == pytest.approx(3.0)
    assert res["arms"]["A5-D"]["2K/4K"]["information_bits"]["median_of_the_smaller_panel"] == pytest.approx(3.0)
    md = report.render_markdown(res)
    assert "descriptive AUC of max_s a_s for answer sites against the other 55 positions: median 0.800" in md and "i = 3.000 bits per fact" in md and "ADDRESS RECALL" in md and "DENSE COMPARISON" in md and "sustained success" in md


# --- item 9: the rehearsal under load ---------------------------------------------------------------------------------------------------------------------------
def test_rehearsal_with_busy_processes_runs_records_the_count_and_leaves_nothing_behind(tmp_path: Path) -> None:
    run_dir = tmp_path / "REH"
    code = stages.main(["rehearse", "--dry", "--run-dir", str(run_dir), "--arm-selection", str(ROOT / "studies/p10s0/freeze/arm_selection.json"), "--stage-cap-seconds", "900", "--busy-processes", "2", "--only", "REH-A0-2K4K-main", "--experiments-root", str(tmp_path), "--ledger-root", str(tmp_path)])
    assert code == 0
    rec = core.read_record(run_dir / "rehearsal/REH-A0-2K4K-main/rehearsal.json", "rehearsal")
    assert rec["busy_processes"] == 2 and rec["mode"] == "dry" and set(rec) <= train.REHEARSAL_RECORD_KEYS
    assert [p.name for p in (run_dir / "rehearsal").iterdir()] == ["REH-A0-2K4K-main"]
    procs = stages.spawn_busy(2)
    assert all(p.poll() is None for p in procs)
    stages.stop_busy(procs)
    assert all(p.poll() is not None for p in procs)
    assert stages.spawn_busy(0) == []


def test_the_rehearsal_only_option_filters_items(tmp_path: Path) -> None:
    ns = stages.build_parser().parse_args(["rehearse", "--dry", "--only", "REH-A0-2K4K-main"])
    items = [i for i in budget.rehearsal_items() if budget.item_label(i) in set(ns.only)]
    assert len(items) == 1


# --- WX before the probe, and the m7 check -----------------------------------------------------------------------------------------------------------------------
def test_the_probe_refuses_until_wx_has_an_evaluation_manifest(tmp_path: Path) -> None:
    gate = {"blocks": {"wx": {"run": True, "status": None}, "probe": {"run": True, "status": None}}}
    with pytest.raises(pool.StageRefused, match="WX runs before the 65,536 probe"):
        stages.require_wx_before_probe(tmp_path, gate)
    (tmp_path / "evaluate-wx").mkdir()
    (tmp_path / "evaluate-wx" / "manifest.json").write_text("{}")
    stages.require_wx_before_probe(tmp_path, gate)  # WX has run: the probe may
    stages.require_wx_before_probe(tmp_path / "elsewhere", {"blocks": {"wx": {"run": False, "status": "NOT RUN — BUDGET"}, "probe": {"run": True, "status": None}}})  # WX is not to run: nothing to wait for


def test_the_swap_accuracy_must_equal_the_panel_accuracy() -> None:
    rec = {"read_swap": {"A": {"accuracy": 0.5}, "B": {"accuracy": 0.25}}, "panels": {"A": {"accuracy": 0.5}, "B": {"accuracy": 0.25}}}
    evaluate.check_swap_accuracy(rec)
    rec["panels"]["B"]["accuracy"] = 0.26
    with pytest.raises(ValueError, match="Panel B"):
        evaluate.check_swap_accuracy(rec)


# --- the end-to-end exercise (M7) ------------------------------------------------------------------------------------------------------------------------------------
def test_the_e2e_harness_builds_no_environment_and_cleans_up_after_itself(tmp_path: Path) -> None:
    """Fast and always on: the uv shim runs the current interpreter (no environment is created), the clone is source files only, and the working directory is deleted when the exercise ends, on failure too."""
    from studies.p10s0 import e2e

    exe = e2e.write_uv_shim(tmp_path / "shim")
    out = subprocess.run([str(exe), "run", "--locked", "python", "-c", "import sys; print(sys.executable)"], capture_output=True, text=True, check=True).stdout.strip()
    assert out == sys.executable and subprocess.run([str(exe), "pip"], capture_output=True, check=False).returncode == 64
    env = e2e.clone_env(tmp_path / "clone", tmp_path / "shim")
    assert env["PYTHONPATH"] == str(tmp_path / "clone") and env["PATH"].startswith(str(tmp_path / "shim") + os.pathsep)
    src = tmp_path / "src"
    (src / "studies").mkdir(parents=True)
    (src / "studies/a.py").write_text("x = 1\n")
    (src / ".gitignore").write_text(".venv/\n")
    (src / ".venv").mkdir()
    (src / ".venv/big").write_text("ignored")
    subprocess.run(["git", "init", "-q"], cwd=src, check=True)
    dest = tmp_path / "dest"
    dest.mkdir()
    e2e.copy_working_tree(src, dest)
    assert sorted(p.name for p in dest.rglob("*") if p.is_file()) == [".gitignore", "a.py"]  # no environment, nothing ignored
    keep = tmp_path / "keep"
    with pytest.raises(e2e.E2EError):
        e2e.run_e2e(keep, source=src)  # this tree has no arm-selection record: the exercise fails at once
    assert not (keep / "work").exists() and (keep / "e2e.log").is_file()  # the working directory is gone; the log stays
    assert not any(p.name == ".venv" for p in keep.rglob("*"))


@pytest.mark.skipif(os.environ.get("P10S0_E2E") != "1", reason="the full end-to-end exercise takes about 20 minutes: opt in with P10S0_E2E=1 (or run python -m studies.p10s0.e2e)")
def test_the_whole_registered_sequence_runs_end_to_end_through_the_real_launch_scripts(tmp_path: Path) -> None:
    from studies.p10s0 import e2e

    summary = e2e.run_e2e(tmp_path / "e2e")
    assert summary["steps"]["scripts"] == [["gates", 0], ["q1", 0], ["q1_gate", 0], ["wx", 0], ["probe", 2], ["analysis", 0], ["report", 0], ["q1", 2]]
    s = summary["steps"]
    assert s["cut3"] is True and s["cut_label"] == core.CUT3_LABEL and s["candidate"] == "A5-D" and s["blocks"]["probe"]["status"] == "NOT RUN — MEMORY" and s["blocks"]["wx"]["run"] is True
    assert summary["steps"]["generate.sh"] == 0 and core.CUT3_LABEL in s["outcome_label"] and s["generation_cap"]["provisional"] is False
    assert not (tmp_path / "e2e" / "work").exists() and (tmp_path / "e2e" / "summary.json").is_file()
