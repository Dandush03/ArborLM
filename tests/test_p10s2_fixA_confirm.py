# ruff: noqa: E501
"""P10S2 confirmation of the re-check fixes (F1, F2, F3, F4, F6, F7) for the data-generation step and its install, on fakes: no network, no install, no real file, no real ledger. Self-check only: not
independent review, not Astra validation, not human approval."""

import json
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from studies.p10s2 import datagen, fetch_guard  # noqa: E402
from studies.p10s2 import install_datagen as ins  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
H = " \\\n    --hash=sha256:" + "0" * 64


def good_requirements(path: Path) -> Path:
    path.write_text("".join(f"{n}=={v}{H}\n" for n, v in ins.EXPECTED_PINS.items()))
    return path


def fake_installer(extra: dict[str, str] | None = None):  # type: ignore[no-untyped-def]
    def install(requirements: Path, target: Path) -> None:
        for n, v in {**ins.EXPECTED_PINS, **(extra or {})}.items():
            d = target / f"{n.replace('-', '_')}-{v}.dist-info"
            d.mkdir(parents=True)
            (d / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {n}\nVersion: {v}\n")

    return install


def blank_ledger(tmp_path: Path) -> Path:
    dl = tmp_path / "DOWNLOAD_LEDGER.md"
    head, _rows, tail = fetch_guard._read_ledger(ROOT / fetch_guard.DOWNLOAD_LEDGER)
    fetch_guard._write_ledger(dl, head, [], tail)
    return dl


# --- F1: the install is its own step; datagen.sh only verifies the completed install and can be re-run ----------------------------------------------------
def test_f1_the_launchers_install_once_and_datagen_only_verifies(tmp_path: Path) -> None:
    inst = (ROOT / "studies/p10s2/launch/install_datagen.sh").read_text()
    gen = (ROOT / "studies/p10s2/launch/datagen.sh").read_text()
    assert (ROOT / "studies/p10s2/launch/install_datagen.sh").stat().st_mode & stat.S_IEXEC
    for sh in ("install_datagen.sh", "datagen.sh"):
        assert subprocess.run(["sh", "-n", str(ROOT / "studies/p10s2/launch" / sh)], check=False).returncode == 0  # noqa: S603, S607
    assert "studies.p10s2.install_datagen --code-commit" in inst and "--verify" not in inst
    assert "install_datagen --verify --code-commit" in gen and "--with-requirements" not in gen and 'PYTHONPATH="$PWD/data/datagen-packages"' in gen
    exec_lines = [ln for ln in gen.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    assert sum("install_datagen" in ln for ln in exec_lines) == 1 and "--verify" in next(ln for ln in exec_lines if "install_datagen" in ln)  # the only call of the installer module in datagen.sh is the verification


def test_f1_verify_checks_the_completed_install_writes_nothing_and_can_be_repeated(tmp_path: Path) -> None:
    req = good_requirements(tmp_path / "req.txt")
    dl, led, target = blank_ledger(tmp_path), Ledger(tmp_path / "ledger.jsonl"), tmp_path / "pkgs"
    with pytest.raises(ins.InstallRefused, match="does not exist"):
        ins.verify(req, target, dl, {})  # not installed
    ins.run(req, target, led=led, download_ledger=dl, installer=fake_installer())
    before = (dl.read_bytes(), (tmp_path / "ledger.jsonl").read_bytes())
    for _ in range(2):  # a second datagen.sh after an engineering stop: the check passes again and installs or writes nothing
        got = ins.verify(req, target, dl, {})
        assert all(got[n] == v for n, v in ins.EXPECTED_PINS.items())
    assert (dl.read_bytes(), (tmp_path / "ledger.jsonl").read_bytes()) == before
    req.write_text(req.read_text().replace("0" * 64, "1" * 64))  # another requirements file than the one installed
    with pytest.raises(ins.InstallRefused, match="no completed row"):
        ins.verify(req, target, dl, {})
    (tmp_path / "x").mkdir()
    with pytest.raises(ins.InstallRefused, match="no completed row"):
        ins.verify(good_requirements(tmp_path / "r2.txt"), target, blank_ledger(tmp_path / "x"), {})  # a ledger without the row (not committed after the install)


def test_f1_the_real_launchers_sequence_survives_an_engineering_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """install -> (the lead commits the ledger) -> datagen's start reaches ``run`` -> an engineering stop -> the same verify passes again and ``run``'s re-run gate is open."""
    req = good_requirements(tmp_path / "req.txt")
    dl, led, target = blank_ledger(tmp_path), Ledger(tmp_path / "ledger.jsonl"), tmp_path / "pkgs"
    ins.run(req, target, led=led, download_ledger=dl, installer=fake_installer())
    ins.verify(req, target, dl, {})
    out = tmp_path / "out"

    class Fake:
        def remaining(self) -> float:
            return 10.0

        def charge(self, stage: str, seconds: float) -> None:
            led.record("datagen", seconds)

    monkeypatch.setattr(datagen, "package_versions", lambda: {})
    monkeypatch.setattr(datagen, "_run", lambda *a, **k: (_ for _ in ()).throw(ValueError("an engineering error")))
    with pytest.raises(ValueError, match="engineering"):
        datagen.run(tmp_path / "dl", out, led=Fake(), stage_cap_seconds=3600.0, requirements=req, code_commit="abc123")
    ins.verify(req, target, dl, {})  # the second datagen.sh: verify passes, nothing is installed
    assert datagen.datagen_rerun_gate(out) is None  # and an engineering stop does not block the re-run


# --- F2: a release names the attempt it releases -------------------------------------------------------------------------------------------------------------
def test_f2_a_release_names_one_attempt_and_does_not_release_the_next(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Fake:
        def __init__(self) -> None:
            self.led = Ledger(tmp_path / "ledger.jsonl")

        def remaining(self) -> float:
            return 10.0

        def charge(self, stage: str, seconds: float) -> None:
            self.led.record("datagen", seconds)

    out = tmp_path / "out"
    monkeypatch.setattr(datagen, "package_versions", lambda: {})
    req = good_requirements(tmp_path / "req.txt")

    def stop(msg: str) -> None:
        monkeypatch.setattr(datagen, "_run", lambda *a, **k: (_ for _ in ()).throw(datagen.RegisteredTestStop(msg)))
        with pytest.raises(datagen.RegisteredTestStop):
            datagen.run(tmp_path / "dl", out, led=Fake(), stage_cap_seconds=3600.0, requirements=req, code_commit="abc")

    rel = out / "datagen_attempts" / "lead_release.json"
    stop("first")
    assert "returns to the lead" in (datagen.datagen_rerun_gate(out) or "")
    for bad in ({}, {"releases_attempt": 1}, {"releases_attempt": 1, "cause": "x"}, {"releases_attempt": 2, "cause": "x", "released_by": "lead"}, {"releases_attempt": 1, "cause": " ", "released_by": "lead"}):
        rel.write_text(json.dumps(bad))
        assert datagen.datagen_rerun_gate(out), bad  # an empty, partial or wrong-attempt release releases nothing
    rel.write_text("not json")
    assert datagen.datagen_rerun_gate(out)
    rel.write_text(json.dumps({"releases_attempt": 1, "cause": "the lead read the stop", "released_by": "lead"}))
    assert datagen.datagen_rerun_gate(out) is None
    stop("second")  # attempt 2 stops on a registered test again
    assert "attempt-002" in (datagen.datagen_rerun_gate(out) or "")  # the release of attempt 1 does not release attempt 2
    rel.write_text(json.dumps({"releases_attempt": 2, "cause": "again", "released_by": "lead"}))
    assert datagen.datagen_rerun_gate(out) is None


# --- F3: the data record's identity ---------------------------------------------------------------------------------------------------------------------------
def test_f3_every_attempt_record_carries_the_code_commit_configuration_and_requirements(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Fake:
        def remaining(self) -> float:
            return 10.0

        def charge(self, stage: str, seconds: float) -> None:
            Ledger(tmp_path / "l.jsonl").record("datagen", seconds)

    monkeypatch.setattr(datagen, "package_versions", lambda: {})
    monkeypatch.setattr(datagen, "_run", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    req = good_requirements(tmp_path / "req.txt")
    with pytest.raises(RuntimeError):
        datagen.run(tmp_path / "dl", tmp_path / "out", led=Fake(), stage_cap_seconds=3600.0, requirements=req, code_commit="deadbeef")
    rec = json.loads((tmp_path / "out" / "datagen_attempts" / "attempt-001.json").read_text())
    assert rec["code_commit"] == "deadbeef" and rec["config_sha256"] == fetch_guard.sha256_file(ROOT / "configs/p10s2_transfer.toml") and rec["requirements_sha256"] == fetch_guard.sha256_file(req) and "transformers_file" in rec
    src = (ROOT / "studies/p10s2/datagen.py").read_text()
    assert "code_commit=a.code_commit" in src  # main hands the commit it checked to run()


# --- F4: caps on the start markers -------------------------------------------------------------------------------------------------------------------------------
def test_f4_the_datagen_and_install_start_markers_carry_their_caps(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.jsonl")
    with datagen.charged_stage(led, 1234.0):
        pass
    assert led.entries()[0]["cap_seconds"] == 1234.0 and led.entries()[0]["status"] == "started"
    led2 = Ledger(tmp_path / "l2.jsonl")
    ins.run(good_requirements(tmp_path / "r.txt"), tmp_path / "p", led=led2, download_ledger=blank_ledger(tmp_path), installer=fake_installer())
    assert led2.entries()[0]["kind"] == "install" and led2.entries()[0]["cap_seconds"] == ins.INSTALL_CAP_SECONDS


# --- F6: provenance of the eight packages ------------------------------------------------------------------------------------------------------------------------
def test_f6_each_package_must_be_imported_from_the_install_directory(tmp_path: Path) -> None:
    d = tmp_path / "pkgs"
    d.mkdir()

    def locate_in(name: str) -> Any:
        return SimpleNamespace(origin=str(d / name / "__init__.py"), submodule_search_locations=[str(d / name)])

    assert set(datagen.check_provenance(d, locate_in)) == set(datagen.MODULES)
    with pytest.raises(datagen.DatagenStop, match="not from"):
        datagen.check_provenance(d, lambda n: SimpleNamespace(origin="/elsewhere/site-packages/numpy/__init__.py", submodule_search_locations=[]) if n == "numpy" else locate_in(n))
    with pytest.raises(datagen.DatagenStop, match="not from"):
        datagen.check_provenance(d, lambda n: None if n == "sacremoses" else locate_in(n))  # not importable at all
    namespace = SimpleNamespace(origin=None, submodule_search_locations=[str(d / "x")])
    assert datagen.check_provenance(d, lambda n: namespace)["numpy"] == str(d / "x")  # a namespace package is located by its search path


# --- F7: no package of the lock at another version in the install directory -------------------------------------------------------------------------------------
def test_f7_a_package_of_the_lock_at_another_version_is_refused() -> None:
    lock = ins.lock_versions()
    assert "torch" in lock and lock["torch"].startswith("2.8.0")
    other = "filelock" if "filelock" in lock else next(n for n in lock if n not in ins.EXPECTED_PINS and n not in ("torch", "pyarrow"))
    import tempfile

    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "p"
        fake_installer({other: "0.0.1"})(Path("r"), d)
        with pytest.raises(ins.InstallRefused, match="another version"):
            ins.check_installed(d, lock)
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "p"
        fake_installer({other: lock[other]})(Path("r"), d)
        assert other in ins.check_installed(d, lock)  # the same version as the lock is not a shadow
