# ruff: noqa: E501
"""P10IS1 quiet rule (ADR-0024 addendum A3, A8): the integer-hundredths arithmetic, the conditions of the machine (marker lists, thermal parse, idle-time unit, process family), the baseline command (settle, window, the
two-sided settled test, the ceiling, discards, sessions, the fallback to the closed condition, a second baseline, the re-derivation the freeze makes). Synthetic process tables, injected clocks and load readers: no test
waits (the one real-process test starts two short-lived children). Self-check only: not an independent review, not Astra validation, not human approval."""

import contextlib
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm.io import file_sha256  # noqa: E402
from studies.p10is1 import baseline, core, loadrule, machine, quiet  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
APP_CMD = "/Applications/Claude.app/Contents/MacOS/Claude"
CLI_CMD = "/Users/x/Library/Application Support/Claude/claude-code/2.1.326/c4434d650cb3/claude.app/Contents/MacOS/claude --output-format stream-json --verbose"
HELPER_CMD = "/Applications/Claude.app/Contents/Frameworks/Claude Helper.app/Contents/MacOS/Claude Helper --type=utility"


def qcfg(**over: Any) -> dict[str, Any]:
    """The repository's config with a MEASURED quiet block (not provisional): L = 180 (P95 130 + 50), open condition, the application and Claude Code absent; any figure overridden. A copy: nothing is shared."""
    cfg = copy.deepcopy(dict(core.load_config()))
    cfg["quiet"].update(baseline_provisional=False, load_p95=130, load_limit=180, condition="open", app_present=False, cli_present=False)
    cfg["quiet"].update(over)
    return cfg


def small(**over: Any) -> dict[str, Any]:
    """A small window (6 settle + 30 window samples, a 6-minute attempt, a 7.2-minute session) so that structural tests run in a few hundred samples; the real sizes are tested once."""
    return qcfg(**{"baseline_samples": 30, "settle_samples": 6, "baseline_session_hours": 0.12, "baseline_attempt_minutes": 6, **over})


class FakeMachine:
    """Every reader of the machine from a synthetic process table, a load function of time and an injected clock."""

    def __init__(self, load: Callable[[float], tuple[float, float]] = lambda t: (1.30, 1.30)) -> None:
        self.t = 0.0
        self.load = load
        self.extra: list[machine.Row] = []
        self.hid_ns = 10**13
        self.mains, self.low, self.therm, self.boot = True, False, [], 1000
        self.hooks: list[Callable[[FakeMachine], None]] = []
        self.sleeps = 0

    def clock(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s
        self.sleeps += 1
        for h in list(self.hooks):
            h(self)

    def table(self) -> list[machine.Row]:
        return [(1, 0, "/sbin/launchd"), (500, 1, "python -m studies.p10is1.baseline run --out-dir x"), *self.extra]

    def probe(self) -> machine.Probe:
        return machine.Probe(
            load=lambda: self.load(self.t), table=self.table, power=lambda: {"mains": self.mains, "low_power_mode": self.low}, therm=lambda: list(self.therm), hid_ns=lambda: self.hid_ns, boot=lambda: self.boot, cpu=lambda: self.t * 1e-4,
            top=lambda: [{"pid": 7, "pcpu": 1.0, "comm": "x"}], pid=500,
        )  # fmt: skip


def run_session(fm: FakeMachine, out: Path, cfg: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return baseline.run_baseline(out, cfg=cfg, probe=fm.probe(), sleep=fm.sleep, clock=fm.clock, wall=fm.clock, os_build=lambda: "TEST", awake=contextlib.nullcontext, **kw)


# --- synthetic committed baseline (what the freeze re-derives): used by every test that needs a config that is not provisional ------------------------
CANON = Path(tempfile.mkdtemp(prefix="p10is1-canon-"))  # the TEST stand-in for the canonical baseline root: the autouse fixtures point ``baseline.canonical_root`` at it; no test ever writes the real one


def use_canon(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the canonical root at the per-process test directory (emptied) for one test."""
    shutil.rmtree(CANON, ignore_errors=True)
    CANON.mkdir(parents=True)
    monkeypatch.setattr(baseline, "canonical_root", lambda: CANON)
    return CANON


def use_test_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    """The TEST-ONLY override (``baseline._test_root``) and no preflight against this machine's real process table."""
    monkeypatch.setattr(baseline, "_test_root", root)
    monkeypatch.setattr(baseline, "preflight", lambda **kw: None)
    monkeypatch.setattr(baseline, "require_clean_code", lambda repo: "0" * 40)


def synthetic_baseline(out: Path, *, load: int = 130, condition: str = "open", app: bool = False, cli: bool = False, repo: Path | None = None) -> dict[str, Any]:
    """Write a record and a samples file with the schema of ``baseline.run_baseline`` (420 samples at a constant ``load`` hundredths), mirrored as the TEST canonical root's ``first/`` (``CANON``), and return the config
    figures that match them. The record says it was taken under that root, with ``test_root = false``, and lists its one attempt."""
    q = core.load_config()["quiet"]
    n = int(q["settle_samples"]) + int(q["baseline_samples"])
    out.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(1, n + 1):
        s = {"session": 1, "attempt": 1, "index": i, "phase": "settle" if i <= int(q["settle_samples"]) else "window", "utc": "2026-01-01T00:00:00+00:00", "t": 10.0 * i, "condition": condition, "load1_h": load, "load5_h": load, "failed": [], "app_present": app, "cli_present": cli, "hid_idle_seconds": 9999.0, "boot": 1000, "mains": True, "low_power_mode": False, "thermal_lines": [], "other_study_processes": [], "vm_processes": [], "sampler_cpu_seconds": 0.0}
        lines.append(json.dumps(s, sort_keys=True))
    (out / baseline.SAMPLES).write_text("\n".join(lines) + "\n", encoding="utf-8")
    d = loadrule.derive([load] * int(q["baseline_samples"]), q)
    rec = {**core.envelope("quiet_baseline"), "status": baseline.ACCEPTED, "condition": condition, "sessions": [], "attempts": [{"session": 1, "attempt": 1, "outcome": "ACCEPTED"}], "accepted": {"session": 1, "attempt": 1, **d}, "samples_file": baseline.SAMPLES, "samples_sha256": file_sha256(out / baseline.SAMPLES), "root": str(CANON.resolve()), "test_root": False, "quiet_rules_sha256": core.quiet_rules_sha256(core.load_config()), "config_file_sha256": "0" * 64, "code_commit": None}
    core.write_record(out / baseline.RECORD, rec, overwrite=True)
    mirror = CANON / "first"
    shutil.rmtree(mirror, ignore_errors=True)
    mirror.mkdir(parents=True)
    for f in (baseline.RECORD, baseline.SAMPLES):
        shutil.copy(out / f, mirror / f)
    if repo is not None:  # the repository-tracked SESSIONS.log the lead commits: one line for the one session
        log = repo / baseline.SESSIONS_LOG
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(f"2026-01-01T00:00:00+00:00\tdir=first\tsession=1\tattempts=1-1\tstatus=ACCEPTED\tsamples_sha256={rec['samples_sha256']}\n")
    return {"load_p95": d["load_p95"], "load_limit": d["load_limit"], "condition": condition, "app_present": app, "cli_present": cli, "baseline_record_sha256": file_sha256(out / baseline.RECORD)}


def set_quiet_figures(text: str, **figures: str) -> str:
    """The config text with the named ``[quiet]`` lines set (values already in TOML form); each line must exist exactly once."""
    for k, v in figures.items():
        text, n = re.subn(rf"^{k} = [^#\n]*", f"{k} = {v}  ", text, count=1, flags=re.M)
        assert n == 1, k
    return text


def measured_quiet_text(text: str, *, load_p95: int = 130, load_limit: int = 180, condition: str = "open", app: bool = False, cli: bool = False) -> str:
    """A config text whose ``[quiet]`` block is MEASURED (not provisional) with the given figures (no record: for stage tests that read L only)."""
    return set_quiet_figures(text, baseline_provisional="false", load_p95=str(load_p95), load_limit=str(load_limit), condition=f'"{condition}"', app_present=str(app).lower(), cli_present=str(cli).lower())


def stamp_code_commit(repo: Path, git: Callable[..., str]) -> None:
    """After the throw-away repository's first commit: the baseline record carries that commit (``code_commit``), the config names the record's new hash, the test canonical root mirrors the record, and a second commit holds
    it (the record's commit is then an ancestor of HEAD, and the baseline-relevant files are unchanged since)."""
    p = repo / core.CONFIG
    cfg = core.load_config(p)
    rec_path = repo / str(cfg["quiet"]["baseline_record_path"])
    rec = core.read_record(rec_path, "quiet_baseline")
    rec["code_commit"] = git(repo, "rev-parse", "HEAD").strip()
    core.write_record(rec_path, rec, overwrite=True)
    shutil.copy(rec_path, CANON / "first" / baseline.RECORD)
    p.write_text(set_quiet_figures(p.read_text(), baseline_record_sha256=f'"{file_sha256(rec_path)}"'))
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "stamp the baseline's code commit")


def install_baseline(repo: Path, **kw: Any) -> dict[str, Any]:
    """Make the throw-away repository's config carry a MEASURED quiet block (``baseline_provisional = false``) and commit-ready baseline files under ``results/``: the tests never depend on the repository's own state."""
    rel = "results/p10is1-quiet-baseline-test"
    fig = synthetic_baseline(repo / rel, repo=repo, **kw)
    p = repo / core.CONFIG
    text = p.read_text()
    text = set_quiet_figures(text, baseline_provisional="false", load_p95=str(fig["load_p95"]), load_limit=str(fig["load_limit"]), condition=f'"{fig["condition"]}"', app_present=str(fig["app_present"]).lower(), cli_present=str(fig["cli_present"]).lower(), baseline_record_path=f'"{rel}/{baseline.RECORD}"', baseline_record_sha256=f'"{fig["baseline_record_sha256"]}"')
    p.write_text(text)
    return fig


# --- the arithmetic -----------------------------------------------------------------------------------------------------------------------------------
def test_hundredths_are_integers_and_differences_do_not_drift() -> None:
    assert loadrule.hundredths(0.54) - loadrule.hundredths(0.29) == 25
    assert 0.54 - 0.29 > 0.25  # the float pair that fails in floating point (0.25000000000000006)
    assert loadrule.hundredths(0.07 + 0.5) == 57 and loadrule.hundredths(1.804) == 180 and loadrule.hundredths(1.806) == 181
    with pytest.raises(ValueError):
        loadrule.hundredths(float("nan"))


def test_nearest_rank_at_120_and_360_and_the_median_of_an_even_number() -> None:
    assert loadrule.nearest_rank(list(range(1, 121)), 95) == 114 and loadrule.nearest_rank(list(range(1, 361)), 95) == 342
    assert loadrule.nearest_rank(list(range(120, 0, -1)), 95) == 114  # sorted ascending first
    assert loadrule.nearest_rank([5], 95) == 5
    assert loadrule.median2([1, 2, 3, 4]) == 5 and loadrule.median2([1, 2, 3]) == 4 and loadrule.median2([4, 1, 2, 3]) == 5  # twice the median, exactly
    assert loadrule.median2([1, 2]) == 3  # 1.5 x 2


def window_of(t1: tuple[int, int], t3: tuple[int, int], mid: int = 100) -> list[int]:
    """A 360-sample window whose first third has median ``t1[0]`` and a top ``t1[1]`` (the seven samples at ranks 114 to 120, i.e. its P95), the last third likewise."""

    def third(med: int, top: int) -> list[int]:
        return [med] * 113 + [top] * 7

    return third(*t1) + [mid] * 120 + third(*t3)


Q = core.load_config()["quiet"]


@pytest.mark.parametrize(("a", "b", "ok"), [(54, 29, True), (29, 54, True), (55, 29, False), (29, 55, False), (100, 100, True), (125, 100, True), (126, 100, False), (100, 126, False)])
def test_settled_median_test_is_two_sided_at_its_boundary(a: int, b: int, ok: bool) -> None:
    st = loadrule.settled(window_of((a, a), (b, b)), median_diff_max=25, p95_diff_max=50)
    assert st["median_ok"] is ok and st["p95_ok"] is (abs(a - b) <= 50)  # the P95 is the median here


@pytest.mark.parametrize(("a", "b", "ok"), [(150, 100, True), (100, 150, True), (151, 100, False), (100, 151, False), (100, 100, True)])
def test_settled_p95_test_is_two_sided_at_its_boundary(a: int, b: int, ok: bool) -> None:
    st = loadrule.settled(window_of((100, a), (100, b)), median_diff_max=25, p95_diff_max=50)
    assert st["median_ok"] is True and st["p95_ok"] is ok and st["settled"] is ok
    assert st["p95_t1"] == a and st["p95_t3"] == b


def test_the_limit_is_p95_plus_fifty_and_the_ceiling_is_refused_never_clamped() -> None:
    flat = lambda v: loadrule.derive([v] * 360, Q)  # noqa: E731
    assert flat(250)["load_limit"] == 300 and flat(250)["above_ceiling"] is False and flat(250)["report_above"] is True
    assert flat(251)["load_limit"] == 301 and flat(251)["above_ceiling"] is True
    assert flat(200)["load_limit"] == 250 and flat(200)["report_above"] is False and flat(201)["report_above"] is True  # a report above 250, not a gate
    with pytest.raises(ValueError):
        loadrule.derive([100] * 359, Q)


# --- the conditions of the machine --------------------------------------------------------------------------------------------------------------------
def reading(fm: FakeMachine, *, condition: str = "open", expect: tuple[bool, bool] | None = None) -> dict[str, Any]:
    return machine.read_conditions(fm.probe(), qcfg()["quiet"], condition=condition, expect=expect)


def test_a_quiet_machine_has_no_failed_condition_and_records_the_presences() -> None:
    fm = FakeMachine()
    r = reading(fm)
    assert r["failed"] == [] and r["app_present"] is False and r["cli_present"] is False and r["hid_idle_seconds"] == 10000.0
    fm.extra = [(900, 1, APP_CMD), (901, 900, CLI_CMD), (902, 900, HELPER_CMD)]
    r2 = reading(fm)
    assert r2["failed"] == [] and r2["app_present"] is True and r2["cli_present"] is True  # open: recorded, not refused


VM_EXAMPLES = {
    "com.apple.Virtualization.VirtualMachine": "/System/Library/Frameworks/Virtualization.framework/Versions/A/XPCServices/com.apple.Virtualization.VirtualMachine.xpc/Contents/MacOS/com.apple.Virtualization.VirtualMachine",
    "qemu-system": "/opt/homebrew/bin/qemu-system-aarch64 -M virt", "limactl": "/opt/homebrew/bin/limactl hostagent default", "colima": "/opt/homebrew/bin/colima daemon", "com.docker.backend": "/Applications/Docker.app/Contents/MacOS/com.docker.backend run",
    "com.docker.virtualization": "com.docker.virtualization --kernel x", "com.docker.vmnetd": "/Library/PrivilegedHelperTools/com.docker.vmnetd", "Docker.app": "/Applications/Docker.app/Contents/MacOS/Docker Desktop --foo", "vfkit": "/opt/homebrew/bin/vfkit --cpus 2",
    "krunkit": "/opt/homebrew/bin/krunkit --memory 2048", "OrbStack": "/Applications/OrbStack.app/Contents/MacOS/OrbStack", "prl_vm_app": "/Applications/Parallels Desktop.app/Contents/MacOS/prl_vm_app", "Parallels": "/Applications/Parallels Desktop.app/Contents/MacOS/Parallels Desktop",
    "VirtualBoxVM": "/Applications/VirtualBox.app/Contents/Resources/VirtualBoxVM.app/Contents/MacOS/VirtualBoxVM", "VirtualBox.app": "/Applications/VirtualBox.app/Contents/MacOS/VirtualBox", "UTM": "/Applications/UTM.app/Contents/MacOS/UTM",
    "VMware Fusion": "/Applications/VMware Fusion.app/Contents/MacOS/VMware Fusion", "vmware-vmx": "/Applications/VMware Fusion.app/Contents/Library/vmware-vmx -s x",
}  # fmt: skip


def test_the_vm_marker_list_is_exactly_the_addendums_twelve() -> None:
    assert len(Q["vm_markers"]) == 16 and Q["app_markers"] == ["/Applications/Claude\\.app/Contents/MacOS/Claude"]
    for marker in Q["vm_markers"]:
        assert re.compile(marker).pattern == marker and marker not in ("UTM", "colima", "qemu-system")  # N1: every marker is anchored (a path component, a bundle, a bundle id), none is a bare word


@pytest.mark.parametrize("name", sorted(VM_EXAMPLES))
def test_each_vm_marker_refuses(name: str) -> None:
    fm = FakeMachine()
    fm.extra = [(700, 1, VM_EXAMPLES[name])]
    assert "VIRTUAL MACHINE PRESENT" in reading(fm)["failed"], name


def test_the_application_and_cli_markers_are_distinct_and_the_closed_condition_refuses_either() -> None:
    fm = FakeMachine()
    fm.extra = [(900, 1, HELPER_CMD)]
    r = reading(fm)
    assert r["app_present"] is False and r["cli_present"] is False  # a helper process is not the application's main binary
    fm.extra = [(901, 1, CLI_CMD)]
    r = reading(fm)
    assert r["app_present"] is False and r["cli_present"] is True
    assert "CLAUDE CODE PRESENT (CLOSED CONDITION)" in reading(fm, condition="closed")["failed"]
    fm.extra = [(900, 1, APP_CMD)]
    r = reading(fm)
    assert r["app_present"] is True and r["cli_present"] is False
    assert "APPLICATION PRESENT (CLOSED CONDITION)" in reading(fm, condition="closed")["failed"]
    fm.extra = [(902, 1, "/bin/zsh -c cd /Users/x/dev/claude/p10 && ls")]
    assert reading(fm)["cli_present"] is False  # a path component named claude is not the CLI


@pytest.mark.parametrize(("expect", "app", "cli"), [((False, False), True, False), ((False, False), False, True), ((True, False), False, False), ((True, True), True, False), ((False, True), True, True)])
def test_a_stage_reading_needs_each_presence_equal_to_the_baselines_in_both_directions(expect: tuple[bool, bool], app: bool, cli: bool) -> None:
    fm = FakeMachine()
    fm.extra = ([(900, 1, APP_CMD)] if app else []) + ([(901, 1, CLI_CMD)] if cli else [])
    assert "APPLICATION PRESENCE DIFFERS FROM THE BASELINE'S" in reading(fm, expect=expect)["failed"]
    ok = reading(fm, expect=(app, cli))
    assert ok["failed"] == []


def test_thermal_parse_and_the_idle_time_unit_and_power_conditions() -> None:
    three = "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n"
    assert machine.parse_therm(three) == [] and machine.parse_therm("") == []
    assert machine.parse_therm(three + "CPU_Scheduler_Limit = 80\n") == ["CPU_Scheduler_Limit = 80"]
    assert machine.parse_therm("Thermal warning level: 1\n" + three) == ["Thermal warning level: 1"]
    assert machine.parse_hid_idle_ns('    | |   "HIDIdleTime" = 4557984271041\n') == 4557984271041
    fm = FakeMachine()
    fm.hid_ns = 600 * 10**9
    assert reading(fm)["failed"] == []  # exactly 600 s passes
    fm.hid_ns = 600 * 10**9 - 1
    assert reading(fm)["failed"] == ["IDLE TIME UNDER THE MINIMUM"]
    fm.hid_ns, fm.mains = 10**13, False
    assert reading(fm)["failed"] == ["NOT ON MAINS POWER"]
    fm.mains, fm.low = True, True
    assert reading(fm)["failed"] == ["LOW POWER MODE"]
    fm.low, fm.therm = False, ["CPU_Scheduler_Limit = 80"]
    assert reading(fm)["failed"] == ["THERMAL WARNING"]


def test_an_unreadable_condition_fails_closed() -> None:
    fm = FakeMachine()
    pr = fm.probe()
    pr.hid_ns = lambda: (_ for _ in ()).throw(ValueError("no ioreg"))
    assert machine.read_conditions(pr, Q, condition="open")["failed"] == ["IDLE TIME UNREADABLE"]
    pr = fm.probe()
    pr.table = lambda: (_ for _ in ()).throw(OSError("no ps"))
    assert "PROCESS TABLE UNREADABLE" in machine.read_conditions(pr, Q, condition="open")["failed"]


def test_the_study_process_check_excludes_the_callers_whole_family_and_flags_a_sibling() -> None:
    table = [(1, 0, "launchd"), (10, 1, "uv run python -m studies.p10is1.stages registered timing"), (11, 10, "python -m studies.p10is1.stages registered timing"), (12, 11, "caffeinate -i -w 11 studies.p10is1.stages"), (20, 1, "caffeinate -i python -m studies.p10is1.stages registered timing")]
    assert machine.family(table, 11) == {1, 10, 11, 12}  # ancestors and descendants, not the sibling watcher 20
    fm = FakeMachine()
    fm.extra = [(10, 1, "uv run python -m studies.p10is1.stages registered timing"), (11, 10, "python -m studies.p10is1.stages registered timing"), (12, 11, "caffeinate -i -w 11 studies.p10is1.stages"), (20, 1, "caffeinate -i python -m studies.p10is1.stages registered timing")]
    pr = fm.probe()
    pr.pid = 11
    r = machine.read_conditions(pr, Q, condition="open")
    assert [x.split(":")[0] for x in r["other_study_processes"]] == ["500", "20"]  # 500 is the fake's own stand-in, not in this process's family: the sibling watcher 20 is flagged (P10-I-S5's defect)


@pytest.mark.skipif(sys.platform != "darwin", reason="caffeinate and the process tree of record are macOS")
def test_the_keep_awake_watcher_is_inside_the_stages_own_family_on_the_real_process_tree() -> None:
    """Real processes: a child python (the 'stage') starts ``caffeinate -i -w <its pid>`` through ``machine.keep_awake`` and reads the real process table: the watcher is in its family and is not another study's process;
    a process that matches the study markers and is NOT in the family (reparented to launchd) is flagged."""
    code = (
        "import json, os\nfrom studies.p10is1 import machine, quiet\n"
        "with machine.keep_awake() as w:\n    table = machine.ps_table()\n    fam = machine.family(table, os.getpid())\n"
        "    print(json.dumps({'w': w, 'in_family': w in fam, 'cmd': [c for p, _, c in table if p == w], 'others': quiet.other_study_processes()}))\n"
    )
    env = {**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}", "PYTHONDONTWRITEBYTECODE": "1"}
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120, check=True)  # noqa: S603
    got = json.loads(out.stdout.strip().splitlines()[-1])
    assert got["w"] and got["in_family"] is True and got["cmd"] and "caffeinate" in got["cmd"][0] and "studies." not in got["cmd"][0]
    assert not any(str(got["w"]) == o.split(":")[0] for o in got["others"])
    sib = subprocess.run(["sh", "-c", f"{sys.executable} -c 'import time; time.sleep(60)' studies.p10is1.sibling_probe >/dev/null 2>&1 & echo $!"], capture_output=True, text=True, timeout=30, check=True)  # noqa: S603
    pid = int(sib.stdout.strip())
    try:
        flagged = quiet.other_study_processes()
        assert any(o.split(":")[0] == str(pid) for o in flagged), flagged  # a sibling of the same marker is another study's process
    finally:
        subprocess.run(["kill", str(pid)], check=False)  # noqa: S603, S607


# --- the baseline command -----------------------------------------------------------------------------------------------------------------------------
def test_a_flat_idle_window_is_accepted_with_p95_and_l_and_every_sample_is_on_disk_when_taken(tmp_path: Path) -> None:
    fm = FakeMachine(lambda t: (1.30 + (0.05 if int(t / 10) % 7 == 0 else 0.0), 1.30))
    out = tmp_path / "bl"
    seen: list[int] = []
    fm.hooks.append(lambda m: seen.append(len((out / baseline.SAMPLES).read_text().splitlines())))  # at each sleep the samples taken so far are on disk
    rec = run_session(fm, out, qcfg())
    assert rec["status"] == "ACCEPTED" and rec["accepted"]["load_p95"] == 135 and rec["accepted"]["load_limit"] == 185 and rec["condition"] == "open"
    assert rec["accepted"]["app_present"] is False and rec["accepted"]["cli_present"] is False and rec["accepted"]["settled"]["settled"] is True
    lines = [json.loads(x) for x in (out / baseline.SAMPLES).read_text().splitlines()]
    assert len(lines) == 420 and [x["index"] for x in lines] == list(range(1, 421)) and lines[59]["phase"] == "settle" and lines[60]["phase"] == "window"
    assert seen == list(range(1, 420)) and rec["samples_sha256"] == file_sha256(out / baseline.SAMPLES) and rec["os_build"] == "TEST"
    assert rec["attempts"][0]["top_processes_start"] and rec["attempts"][0]["top_processes_end"] and "sampler_cpu_seconds" in rec
    d = baseline.rederive(out / baseline.RECORD, qcfg()["quiet"])  # the freeze's re-derivation agrees
    assert (d["load_p95"], d["load_limit"], d["condition"]) == (135, 185, "open")
    with pytest.raises(core.StageRefused, match="a baseline is taken once"):
        run_session(FakeMachine(), out, qcfg())


@pytest.mark.parametrize("direction", ["rising", "falling"])
def test_a_rising_or_falling_window_is_not_settled_and_is_retaken(direction: str, tmp_path: Path) -> None:
    def load(t: float) -> tuple[float, float]:
        x = min(max((t - 600.0) / 3590.0, 0.0), 1.0)  # a ramp across the first attempt's window, flat after
        v = 1.0 + x if direction == "rising" else 2.0 - x
        return (v, v)

    rec = run_session(FakeMachine(load), tmp_path / "bl", qcfg())
    first, second = rec["attempts"][0], rec["attempts"][1]
    assert first["outcome"] == "DISCARDED" and first["reason"].startswith("NOT SETTLED") and first["derived"]["settled"]["settled"] is False
    assert second["outcome"] == "ACCEPTED" and rec["accepted"]["attempt"] == 2
    assert len((tmp_path / "bl" / baseline.SAMPLES).read_text().splitlines()) > 420  # the discarded attempt's samples are kept


def test_a_limit_above_the_ceiling_is_refused_and_300_is_not(tmp_path: Path) -> None:
    ok = run_session(FakeMachine(lambda t: (2.50, 2.50)), tmp_path / "ok", qcfg())
    assert ok["status"] == "ACCEPTED" and ok["accepted"]["load_limit"] == 300 and ok["accepted"]["report_above"] is True
    bad = run_session(FakeMachine(lambda t: (2.51, 2.51)), tmp_path / "bad", qcfg(baseline_session_hours=2.0))
    assert bad["status"] == baseline.PAUSED_NO_BASELINE and bad["accepted"] is None
    assert "ABOVE CEILING" in bad["attempts"][0]["reason"] and bad["attempts"][0]["derived"]["load_limit"] == 301  # never clamped


@pytest.mark.parametrize(
    ("what", "expect"),
    [("vm", "VIRTUAL MACHINE PRESENT"), ("study", "OTHER STUDY PROCESS ALIVE"), ("hid", "IDLE TIME UNDER THE MINIMUM"), ("mains", "NOT ON MAINS POWER"), ("low", "LOW POWER MODE"), ("therm", "THERMAL WARNING"), ("gap", "SAMPLING GAP"), ("boot", "BOOT TIME CHANGED"), ("app", "APPLICATION PRESENCE CHANGED")],
)  # fmt: skip
def test_one_failure_at_one_sample_discards_the_attempt_and_the_next_starts_at_the_settle_period(what: str, expect: str, tmp_path: Path) -> None:
    fm = FakeMachine()
    fired = {"n": 0}

    def hook(m: FakeMachine) -> None:  # the disturbance lasts for the single sample taken at t = 200 s (settle sample 21 of attempt 1); app stays
        at = 200.0
        if what == "app":
            if m.t >= at and not m.extra:
                m.extra = [(900, 1, APP_CMD)]
            return
        if m.t == at:
            fired["n"] += 1
            {
                "vm": lambda: m.extra.append((700, 1, VM_EXAMPLES["qemu-system"])), "study": lambda: m.extra.append((701, 1, "python -m studies.p10is5.stages registered x")), "hid": lambda: setattr(m, "hid_ns", 5 * 10**9), "mains": lambda: setattr(m, "mains", False),
                "low": lambda: setattr(m, "low", True), "therm": lambda: setattr(m, "therm", ["CPU_Scheduler_Limit = 80"]), "gap": lambda: setattr(m, "t", m.t + 40.0), "boot": lambda: setattr(m, "boot", 2000),
            }[what]()  # fmt: skip
        elif m.t == at + 10.0 and what != "gap":
            m.extra, m.mains, m.low, m.therm, m.hid_ns = [], True, False, [], 10**13  # the disturbance is over

    fm.hooks.append(hook)
    rec = run_session(fm, tmp_path / "bl", qcfg())
    first = rec["attempts"][0]
    assert first["outcome"] == "DISCARDED" and expect in first["reason"], first["reason"]
    assert rec["status"] == "ACCEPTED" and rec["accepted"]["attempt"] == 2
    if what == "boot":
        assert rec["accepted"]["attempt"] == 2  # the new boot time is the second attempt's own constant
    if what == "app":
        assert rec["accepted"]["app_present"] is True  # the application's presence in the accepted window is what a stage must equal
    lines = [json.loads(x) for x in (tmp_path / "bl" / baseline.SAMPLES).read_text().splitlines()]
    second = [x for x in lines if x["attempt"] == 2]
    assert second[0]["index"] == 1 and len(second) == 420  # a fresh settle period of 60 and window of 360


def test_a_session_is_bounded_and_ends_paused_with_every_sample_kept(tmp_path: Path) -> None:
    fm = FakeMachine()
    fm.hid_ns = 0  # the machine is never idle
    rec = run_session(fm, tmp_path / "bl", small())
    assert rec["status"] == baseline.PAUSED_NO_BASELINE and rec["accepted"] is None and rec["sessions"][-1]["status"] == baseline.PAUSED_NO_BASELINE
    n = len((tmp_path / "bl" / baseline.SAMPLES).read_text().splitlines())
    assert 0 < n <= 0.12 * 3600 / 10 + 1 and fm.t <= 0.12 * 3600 + 10  # bounded by the session's six-hour figure (scaled): the deadline is checked before each sample
    assert all(json.loads(x)["phase"] == "waiting" for x in (tmp_path / "bl" / baseline.SAMPLES).read_text().splitlines())


def test_no_attempt_starts_that_could_not_finish_inside_the_session(tmp_path: Path) -> None:
    fm = FakeMachine(lambda t: (1.3, 1.3))
    rec = run_session(fm, tmp_path / "bl", small(baseline_session_hours=0.05))  # 180 s: a 6-minute attempt does not fit
    assert rec["status"] == baseline.PAUSED_NO_BASELINE and rec["attempts"] == [] and not (tmp_path / "bl" / baseline.SAMPLES).exists()


def test_three_open_sessions_without_a_baseline_change_the_condition_to_closed_by_the_rule_and_three_more_return_to_the_lead(tmp_path: Path) -> None:
    out = tmp_path / "bl"
    cfg = small()
    conds = []
    for _ in range(3):
        fm = FakeMachine(lambda t: (2.60, 2.60))  # above the ceiling: every window is refused
        rec = run_session(fm, out, cfg)
        conds.append(rec["condition"])
        assert rec["status"] == baseline.PAUSED_NO_BASELINE
    assert conds == ["open", "open", "open"] and rec["condition_changed_to_closed"] is None  # not before the third has ended
    fm = FakeMachine(lambda t: (1.3, 1.3))
    fm.extra = [(900, 1, APP_CMD)]  # the application is open: not allowed in the closed condition
    rec = run_session(fm, out, cfg)
    assert rec["condition"] == "closed" and rec["paused_sessions"] == {"open": 3, "closed": 1} and "APPLICATION PRESENT (CLOSED CONDITION)" in json.dumps(
        [json.loads(x)["failed"] for x in (out / baseline.SAMPLES).read_text().splitlines()][-1]
    )
    assert rec["condition_changed_to_closed"]["after_open_sessions"] == 3 and "not by a new decision" in rec["condition_changed_to_closed"]["by"]
    for _ in range(2):
        rec = run_session(fm, out, cfg)
    assert rec["paused_sessions"] == {"open": 3, "closed": 3}
    with pytest.raises(core.StageRefused, match="returns to the human lead"):
        run_session(fm, out, cfg)


def test_a_closed_baseline_is_accepted_when_nothing_of_the_application_is_open(tmp_path: Path) -> None:
    out = tmp_path / "bl"
    cfg = small()
    for _ in range(3):
        run_session(FakeMachine(lambda t: (2.60, 2.60)), out, cfg)
    rec = run_session(FakeMachine(lambda t: (1.30, 1.30)), out, cfg)
    assert rec["status"] == "ACCEPTED" and rec["condition"] == "closed" and rec["accepted"]["app_present"] is False and rec["accepted"]["cli_present"] is False and rec["accepted"]["condition"] == "closed"


def test_a_second_baseline_only_for_a_listed_reason_before_any_timing_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"
    first = root / "first"
    run_session(FakeMachine(), first, small())
    reg = tmp_path / "registered_run"
    for r in baseline.SECOND_REASONS:
        assert baseline.check_second(r, first, reg)["replaces_sha256"] == file_sha256(first / baseline.RECORD)
    with pytest.raises(core.StageRefused, match="only for one of"):
        baseline.check_second("the limit looked high", first, reg)
    (reg / "timing").mkdir(parents=True)
    (reg / "timing" / "timing.json").write_text("{}")
    with pytest.raises(core.StageRefused, match="no baseline is taken after it"):
        baseline.check_second("os_update", first, reg)
    (reg / "timing" / "timing.json").unlink()
    with pytest.raises(core.StageRefused, match="nothing to replace"):
        baseline.check_second("os_update", tmp_path / "missing", reg)
    # through the command: a refusal writes no reason file and takes no sample
    out2 = root / "second"
    use_test_root(monkeypatch, root)
    rc = baseline.main(["run", "--replaces", "--reason", "because", "--registered-run-dir", str(reg)])
    assert rc == 2 and not out2.exists()
    assert baseline.main(["run", "--condition", "closed"]) == 2  # the first baseline is taken: no condition argument, no new first one
    # a replacing baseline may name the condition only for the human lead's decision, and carries its reason
    rec = run_session(FakeMachine(), out2, small(), condition="closed", second={"reason": "condition_change_by_human_lead", "replaces": "x"})
    assert rec["condition"] == "closed" and rec["second_baseline"]["reason"] == "condition_change_by_human_lead"
    with pytest.raises(core.StageRefused, match="chosen by the rule"):
        run_session(FakeMachine(), tmp_path / "third", small(), condition="closed")


def test_the_second_baselines_reason_is_on_disk_before_its_first_sample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "root"
    run_session(FakeMachine(), root / "first", small())
    out2 = root / "second"

    def fake_run(o: Path, **kw: Any) -> dict[str, Any]:
        assert (o / baseline.REASON_FILE).is_file() and not (o / baseline.SAMPLES).exists()  # the reason precedes the sampling
        return {"status": baseline.PAUSED_NO_BASELINE, "condition": "open", "paused_sessions": {"open": 1, "closed": 0}, "accepted": None, "samples_sha256": None}

    use_test_root(monkeypatch, root)
    monkeypatch.setattr(baseline, "run_baseline", fake_run)
    monkeypatch.setattr(baseline, "file_sha256", lambda p: "0" * 64)
    rc = baseline.main(["run", "--replaces", "--reason", "os_update", "--reason-text", "26B131 to the next build", "--registered-run-dir", str(tmp_path / "none")])
    assert rc == baseline.EXIT_PAUSED
    assert json.loads((out2 / baseline.REASON_FILE).read_text())["text"] == "26B131 to the next build"


# --- what the freeze re-derives -----------------------------------------------------------------------------------------------------------------------
def committed(tmp_path: Path, **kw: Any) -> tuple[Path, dict[str, Any]]:
    repo = tmp_path / "repo"
    rel = repo / "results" / "b"
    fig = synthetic_baseline(rel, **kw)
    cfg = qcfg(baseline_record_path="results/b/record.json", baseline_record_sha256=fig["baseline_record_sha256"], load_p95=fig["load_p95"], load_limit=fig["load_limit"], condition=fig["condition"], app_present=fig["app_present"], cli_present=fig["cli_present"])
    return repo, cfg


def test_the_freeze_rederives_the_figures_and_refuses_each_difference(tmp_path: Path) -> None:
    repo, cfg = committed(tmp_path)
    assert baseline.verify_against_config(repo, cfg)["load_limit"] == 180
    for key, bad in (("load_p95", 131), ("load_limit", 181), ("condition", "closed"), ("app_present", True), ("cli_present", True)):
        c2 = copy.deepcopy(cfg)
        c2["quiet"][key] = bad
        with pytest.raises(core.StageRefused, match="differ from the ones re-derived"):
            baseline.verify_against_config(repo, c2)
    c3 = copy.deepcopy(cfg)
    c3["quiet"]["baseline_provisional"] = True
    with pytest.raises(core.StageRefused, match="baseline_provisional is true"):
        baseline.verify_against_config(repo, c3)
    c4 = copy.deepcopy(cfg)
    c4["quiet"]["baseline_record_sha256"] = "0" * 64
    with pytest.raises(core.StageRefused, match="does not hash"):
        baseline.verify_against_config(repo, c4)


def test_the_freeze_refuses_a_tampered_sample_an_unsettled_window_and_a_limit_above_the_ceiling(tmp_path: Path) -> None:
    repo, cfg = committed(tmp_path)
    sp = repo / "results" / "b" / baseline.SAMPLES
    original = sp.read_text()
    rows = [json.loads(x) for x in original.splitlines()]
    rows[100]["load1_h"] = 50  # a sample changed after the record was written: the samples file no longer hashes to the record
    sp.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")
    with pytest.raises(core.StageRefused, match="samples file is missing or does not hash"):
        baseline.rederive(repo / "results" / "b" / baseline.RECORD, cfg["quiet"])
    # a record whose samples are internally consistent but whose window is NOT settled (a rise), or above the ceiling, or carries a failed condition, is refused on re-derivation
    for mutate, text in (
        (lambda r: r.__setitem__("load1_h", 100 if r["index"] <= 240 else 200), "not settled"),
        (lambda r: r.__setitem__("load1_h", 260), "ABOVE CEILING"),
        (lambda r: r.__setitem__("failed", ["VIRTUAL MACHINE PRESENT"]) if r["index"] == 7 else None, "carry a failed condition"),
        (lambda r: r.__setitem__("t", r["t"] + (100 if r["index"] > 200 else 0)), "gap of"),
        (lambda r: r.__setitem__("boot", 5) if r["index"] == 9 else None, "not constant"),
    ):
        rows = [json.loads(x) for x in original.splitlines()]
        for r in rows:
            mutate(r)
        sp.write_text("\n".join(json.dumps(r, sort_keys=True) for r in rows) + "\n")
        rec = core.read_record(repo / "results" / "b" / baseline.RECORD, "quiet_baseline")
        rec["samples_sha256"] = file_sha256(sp)
        core.write_record(repo / "results" / "b" / baseline.RECORD, rec, overwrite=True)
        with pytest.raises(core.StageRefused, match=text):
            baseline.rederive(repo / "results" / "b" / baseline.RECORD, cfg["quiet"])


def test_a_baseline_above_250_prints_a_notice_for_the_human_lead_and_is_not_a_gate(tmp_path: Path) -> None:
    repo, cfg = committed(tmp_path, load=220)  # P95 220, L 270
    d = baseline.verify_against_config(repo, cfg)
    assert d["load_limit"] == 270 and "above 250" in d["notice"]
    repo2, cfg2 = committed(tmp_path / "x", load=130)
    assert baseline.verify_against_config(repo2, cfg2)["notice"] is None
