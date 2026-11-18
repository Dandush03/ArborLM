# ruff: noqa: E501
"""P10IS2 Part Q, the road from the measuring rehearsal to the freeze: the rehearsals run the regeneration check, a failed rehearsal is charged, and the files the lead needs (inputs, units, caps) are produced by code.
Nothing here runs a teacher, a registered stage or a freeze. Seeds 937001-937999. Self-check only."""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from test_p10is2_audit_fixes import ctx_of  # noqa: E402

from arborlm.io import file_sha256, write_json  # noqa: E402
from studies.p10is2.common import core  # noqa: E402
from studies.p10is2.partq import freeze, pipeline, pkgmanifest, real, stages  # noqa: E402
from studies.p10is2.partq import plan as qplan  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def measuring_record(tmp: Path, *, regeneration: bool = True) -> Path:
    units = {"inputs": 1.0, "partition": 1.0, "qfit": 4000.0, "qcheck": 16000.0, "generation": 845079.0, "regeneration": 2048.0, "outputs": 5800.0}
    rates = {"inputs": 99.1, "partition": 72.1, "qfit": 0.2488, "qcheck": 0.0459, "generation": 0.0455, "regeneration": 0.05, "outputs": 0.0612}
    if not regeneration:
        del rates["regeneration"]
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / "rehearsal_measuring.json"
    write_json(path, {**core.envelope("rehearsal", "Q"), "kind_of_rehearsal": "measuring", "caps_provisional": True, "rates_seconds_per_unit": rates, "projection_units": units, "charged_before_freeze_seconds": 3468.4})
    return path


# --- the regeneration check is run (and timed) by a rehearsal whose limited generation ends below the target ----------------------------------------
def test_a_rehearsal_runs_and_times_the_regeneration_check_when_generation_ends_data_exhausted(tmp_path: Path) -> None:
    forced = ctx_of(tmp_path / "f", accepted_min=100000, accepted_disjoint=200000, force_generation=True)
    pipeline.run_all(forced)
    assert json.loads(forced.d("generation/result.json").read_text())["draws_label"] == "DATA-EXHAUSTED"
    assert forced.d("regeneration.json").is_file() and "regeneration" in forced.timings  # the measuring record gets its rate
    plain = ctx_of(tmp_path / "p", accepted_min=100000, accepted_disjoint=200000)
    pipeline.run_all(plain)
    assert not plain.d("regeneration.json").exists()  # the registered run does not run it after DATA-EXHAUSTED (section 4.3 rule 6)


def test_a_measuring_record_without_a_rate_for_a_registered_stage_cannot_give_caps(tmp_path: Path) -> None:
    with pytest.raises(core.StageRefused, match="regeneration"):
        freeze.proposal_from_record(core.read_record(measuring_record(tmp_path, regeneration=False), "rehearsal"))
    assert set(freeze.proposal_from_record(core.read_record(measuring_record(tmp_path / "ok"), "rehearsal"))) == {f"{s}_hours" for s in (*qplan.STAGES, "analysis", "total")}


# --- a failed rehearsal is charged; earlier ledgers join the charge --------------------------------------------------------------------------------
def test_a_failed_rehearsal_charges_its_wall_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: object, **k: object) -> None:
        raise RuntimeError("code error in the outputs stage")

    monkeypatch.setattr(real, "_run_rehearsal", boom)
    run = tmp_path / "run"
    with pytest.raises(RuntimeError):
        real.run_rehearsal("measuring", ROOT, run, argparse.Namespace(charged_ledger=[]))
    entries = json.loads((run / "charged_ledger.json").read_text())["entries"]
    assert len(entries) == 1 and entries[0]["stage"] == "rehearsal-failed" and entries[0]["seconds"] >= 0.0


def test_charged_ledger_paths_must_be_absolute(tmp_path: Path) -> None:
    assert stages.main(["rehearse", "--kind", "measuring", "--run-dir", str(tmp_path / "r"), "--charged-ledger", "relative/charged_ledger.json"]) == 2


# --- units, caps ---------------------------------------------------------------------------------------------------------------------------------
def test_the_units_file_is_the_records_projection_units_and_written_once(tmp_path: Path) -> None:
    rec = measuring_record(tmp_path)
    out = tmp_path / "units.json"
    assert stages.main(["units-file", "--measuring-rehearsal", str(rec), "--out", str(out)]) == 0
    assert json.loads(out.read_text()) == json.loads(rec.read_text())["projection_units"]
    assert stages.main(["units-file", "--measuring-rehearsal", str(rec), "--out", str(out)]) == 2  # never overwritten


def test_caps_proposal_defaults_to_what_the_freeze_compares_against(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rec = measuring_record(tmp_path)
    assert stages.main(["caps-proposal", "--measuring-rehearsal", str(rec)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["proposal_hours"] == freeze.proposal_from_record(core.read_record(rec, "rehearsal")) and out["charged_before_freeze_seconds"] == 3468.4


def test_caps_config_apply_enters_exactly_the_proposal_and_then_matches_the_freeze_rule(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "configs").mkdir(parents=True)
    text = (ROOT / core.CONFIG_Q).read_text()  # the repository's config may already hold the caps: this test starts from the unset state
    text = re.sub(r"(?m)^((?:inputs|partition|qfit|qcheck|generation|regeneration|outputs|analysis|total)_hours) = [0-9.]+", r"\1 = 0.0", text).replace("provisional = false", "provisional = true")
    (repo / core.CONFIG_Q).write_text(text)
    rec = measuring_record(tmp_path)
    assert stages.main(["caps-config", "--measuring-rehearsal", str(rec), "--repo", str(repo)]) == 0  # print only: nothing written
    assert core.load_config("Q", repo / core.CONFIG_Q)["caps"]["provisional"] is True
    assert stages.main(["caps-config", "--measuring-rehearsal", str(rec), "--repo", str(repo), "--apply"]) == 0
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    proposal = freeze.proposal_from_record(core.read_record(rec, "rehearsal"))
    assert cfg["caps"]["provisional"] is False and qplan.caps_match_config(cfg, proposal) == [] and all(cfg["stage_caps"][k] > 0 for k in proposal)
    assert stages.main(["caps-config", "--measuring-rehearsal", str(rec), "--repo", str(repo), "--apply"]) == 2  # caps already entered: refused
    other = core.read_record(rec, "rehearsal")
    other["rates_seconds_per_unit"]["generation"] *= 2
    assert qplan.caps_match_config(cfg, freeze.proposal_from_record(other))  # the freeze refuses a config whose caps differ from the rule applied to the record


# --- the inputs file -------------------------------------------------------------------------------------------------------------------------------
def test_the_inputs_block_names_every_file_with_its_hash_and_verifies_at_stage_start(tmp_path: Path) -> None:
    downloads, wt = tmp_path / "downloads", tmp_path / "wikitext2"
    for d, names in ((downloads, ["model.bin", "student/config.json", "tatoeba/a.bz2"]), (wt, list(real.WIKITEXT_FILES))):
        for n in names:
            (d / n).parent.mkdir(parents=True, exist_ok=True)
            (d / n).write_bytes(n.encode())
    dl = {"models": {"model.bin": file_sha256(downloads / "model.bin"), "student/config.json": "ccf3dac2" * 5}, "tatoeba": {"files": {"tatoeba/a.bz2": {"sha256": file_sha256(downloads / "tatoeba/a.bz2"), "bytes": 12}}}}
    wrec = {"directory": str(wt), **{n: {"sha256": file_sha256(wt / n), "bytes": 1} for n in real.WIKITEXT_FILES}}
    manifest = {"path": "/durable", "packages": {}, "file_count": 0, "tree_sha256": "x", "files": {}, "shadowed_lock_packages": {}}
    block = freeze.build_inputs_block(core.load_config("Q"), ROOT, downloads, dl, wrec, manifest)
    assert {"download:model.bin", "download:tatoeba/a.bz2", "requirements", "adr_0004", pkgmanifest.KEY} <= set(block) and sum(k.startswith("wikitext:") for k in block) == 2
    files = {k: v for k, v in block.items() if k != pkgmanifest.KEY}
    pkgmanifest.verify_inputs(files, uses_packages=False, repo=ROOT)  # the paths and hashes hold: a freshly built block passes the stage-start check, un-stubbed
    assert all(len(v["sha256"]) == 64 and set(v["sha256"]) <= set("0123456789abcdef") for v in files.values())  # every "sha256" is a real SHA-256
    cfg_json = block["download:student/config.json"]
    assert cfg_json["sha256"] == file_sha256(downloads / "student/config.json") and cfg_json["upstream_checksum"] == "ccf3dac2" * 5 and cfg_json["upstream_checksum_kind"] == "git-blob-sha1"
    assert block["download:model.bin"]["upstream_checksum_kind"] == "sha256"
    assert not Path(block["requirements"]["path"]).is_absolute() and not Path(block["adr_0004"]["path"]).is_absolute()  # repository files: repo-relative
    copy = tmp_path / "other_checkout"  # another checkout of the same files resolves the same entries
    for rel in (block["requirements"]["path"], block["adr_0004"]["path"]):
        (copy / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, copy / rel)
    pkgmanifest.verify_inputs(files, uses_packages=False, repo=copy)
    with pytest.raises(core.StageRefused, match="no repository"):
        pkgmanifest.verify_inputs(files, uses_packages=False)
    (downloads / "model.bin").write_bytes(b"changed")
    with pytest.raises(core.StageRefused, match="PAUSED — IDENTITY"):
        pkgmanifest.verify_inputs(files, uses_packages=False, repo=ROOT)
    assert block["requirements"]["sha256"] == core.load_config("Q")["paths"]["packages_requirements_sha256"]


def test_the_inputs_file_command_writes_the_block_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from studies.p10is2.partq import real_stages
    from studies.p10s2 import datagen

    wt, downloads = tmp_path / "wt", tmp_path / "dl"
    for d, names in ((downloads, ["m.bin", "tatoeba/x.bz2"]), (wt, list(real.WIKITEXT_FILES))):
        for n in names:
            (d / n).parent.mkdir(parents=True, exist_ok=True)
            (d / n).write_bytes(n.encode())
    dl = {"models": {"m.bin": "a" * 40}, "tatoeba": {"files": {"tatoeba/x.bz2": {"sha256": "b" * 64, "bytes": 1}}}}
    wrec = {"directory": str(wt), **{n: {"sha256": "c" * 64, "bytes": 1} for n in real.WIKITEXT_FILES}}
    manifest = {"path": "/durable", "packages": {"p": "1"}, "file_count": 1, "tree_sha256": pkgmanifest.tree_sha256({"p/a.py": "1" * 64}), "files": {"p/a.py": "1" * 64}, "shadowed_lock_packages": {}}
    monkeypatch.setattr(real_stages, "downloads_dir", lambda cfg: downloads)  # FAKE locations: the real run reads the durable copies
    monkeypatch.setattr(datagen, "verify_downloads", lambda *a, **k: dl)  # FAKE: the real call checks the files against P10-S2's constants (the lead's run does that)
    monkeypatch.setattr(real, "check_wikitext", lambda *a, **k: wrec)  # FAKE: likewise the WikiText-2 pins
    monkeypatch.setattr(pkgmanifest, "build_manifest", lambda *a, **k: manifest)  # FAKE: likewise the 4,270-file package copy (covered on a fake tree in test_p10is2_pkgmanifest.py)
    out = tmp_path / "inputs.json"
    assert stages.main(["inputs-file", "--out", str(out)]) == 0
    block = json.loads(out.read_text())
    assert block["download:m.bin"]["sha256"] == file_sha256(downloads / "m.bin") and block["download:m.bin"]["upstream_checksum_kind"] == "git-blob-sha1" and block[pkgmanifest.KEY]["file_count"] == 1
    assert all(len(v["sha256"]) == 64 for k, v in block.items() if k != pkgmanifest.KEY)
    pkgmanifest.require_package_manifest(block)  # what the freeze requires
    pkgmanifest.verify_inputs({k: v for k, v in block.items() if k != pkgmanifest.KEY}, uses_packages=False, repo=ROOT)  # the stage-start check passes on what the command wrote
    assert stages.main(["inputs-file", "--out", str(out)]) == 2  # written once


# --- a malformed record is a refusal, not a crash ------------------------------------------------------------------------------------------------
def test_the_freeze_refuses_malformed_rehearsal_records(tmp_path: Path) -> None:
    for name in ("counting", "measuring"):
        bad = tmp_path / f"{name}.json"
        bad.write_text("{}")
        other = tmp_path / ("meas.json" if name == "counting" else "cnt.json")
        other.write_text("{}")
        args = argparse.Namespace(repo=None, measuring_rehearsal=str(bad if name == "measuring" else other), counting_rehearsal=str(bad if name == "counting" else other), attest_sealed_unopened="", seal_broken=False)
        with pytest.raises(core.StageRefused):
            freeze.cmd_freeze(args)
