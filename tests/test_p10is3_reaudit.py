# ruff: noqa: E501
"""P10IS3 tests of the re-audit's items: window spans from P10-S2's recorded windows (no tokenizer), N1 (a clean checkout), N2 (the sealed folder), N3 (the failed-cell rule takes precedence). Self-check only."""

import hashlib
import json
import os
import random
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from studies.p10i_s3 import analysis, calibration, core, stages, synthetic  # noqa: E402
from studies.p10i_s3 import window_spans as ws  # noqa: E402
from studies.p10i_s3.core import DENSE, FRESH, TREE  # noqa: E402
from studies.p10i_s3.synthetic import Spec  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CFG = core.load_config()
CFG_S2 = tomllib.loads((ROOT / "configs" / "p10s2_transfer.toml").read_text())


# ---------------- item 4: spans from recorded windows ----------------
def make_bundle(tmp: Path, n_marker: int = 3, n_ord: int = 5, per: int = 8, seed: int = 935301) -> tuple[list[str], Path, Path, dict[str, Any]]:
    """A synthetic corpus (rows with multi-byte characters), a vocabulary of one token per distinct word, windows of ``per`` consecutive tokens, and the pinning manifest."""
    rng = random.Random(seed)
    words = [f" w{i}é{rng.randrange(10**6)}" for i in range(400)]
    stream = [rng.randrange(len(words)) for _ in range(len(words) * 0 + 1600)]
    text = "".join(words[i] for i in stream)
    cuts = sorted(rng.sample(range(1, len(text)), 20))
    rows = [text[a:b] for a, b in zip([0, *cuts], [*cuts, len(text)], strict=True)]
    starts = sorted(rng.sample(range(0, len(stream) - per, per), n_marker + n_ord))
    wins = [{"ids": stream[s : s + per], "stratum": "marker" if k < n_marker else "ordinary", "marker_end": 3, "reads": []} for k, s in enumerate(starts)]
    bundle = tmp / "bundle"
    bundle.mkdir()
    (bundle / "windows.json").write_text(json.dumps({"wiki_train_ids": [], "windows": wins}))
    (bundle / "tokenizer_table.json").write_text(json.dumps({"newline_ids": [0], "token_bytes_hex": [w.encode().hex() for w in words]}))
    man = tmp / "bundle_manifest.json"
    man.write_text(json.dumps({"schema": 1, "files": {n: {"algo": "sha256", "digest": hashlib.sha256((bundle / n).read_bytes()).hexdigest()} for n in ("windows.json", "tokenizer_table.json")}}))
    cfg = {"data": {"general_windows_marker_like": n_marker, "general_windows_ordinary": n_ord}}
    return rows, bundle, man, cfg


def test_spans_from_records_are_exact_once_byte_matches(tmp_path: Path) -> None:
    rows, bundle, man, cfg = make_bundle(tmp_path)
    rec = ws.p10s2_windows_from_records(rows, bundle, man, cfg)
    text = "".join(rows).encode()
    wins = json.loads((bundle / "windows.json").read_text())["windows"]
    table = json.loads((bundle / "tokenizer_table.json").read_text())["token_bytes_hex"]
    assert rec["found_exactly_once"] == 8 and [w["stratum"] for w in rec["windows"]] == ["marker"] * 3 + ["ordinary"] * 5
    lay = ws.RowLayout(rows)
    for w, r in zip(wins, rec["windows"], strict=True):
        b = b"".join(bytes.fromhex(table[i]) for i in w["ids"])
        assert text[r["start"] : r["end"]] == b and text.count(b) == 1 and r["end"] - r["start"] == len(b)  # end exclusive
        assert lay.row_of(r["start"]) == r["first_row"] and lay.row_of(r["end"] - 1) == r["last_row"]
    assert set(rec["bundle_digests"]) == {"windows.json", "tokenizer_table.json"}


def test_spans_from_records_refuse_a_changed_file_zero_or_several_matches_and_wrong_counts(tmp_path: Path) -> None:
    rows, bundle, man, cfg = make_bundle(tmp_path)
    ok = ws.p10s2_windows_from_records(rows, bundle, man, cfg)
    assert ok["found_exactly_once"] == 8
    # zero matches: a corpus without the window's text
    with pytest.raises(core.EngineeringStop, match=r"window 0 \(marker\) occurs 0 times"):
        ws.p10s2_windows_from_records(["unrelated text"], bundle, man, cfg)
    # several matches: the first window's text appears twice
    w0 = ok["windows"][0]
    dup = "".join(rows).encode()[w0["start"] : w0["end"]].decode()
    with pytest.raises(core.EngineeringStop, match=r"window 0 \(marker\) occurs more than once"):
        ws.p10s2_windows_from_records([*rows, dup], bundle, man, cfg)
    # wrong counts against the P10-S2 configuration
    with pytest.raises(core.EngineeringStop, match="configuration states"):
        ws.p10s2_windows_from_records(rows, bundle, man, {"data": {"general_windows_marker_like": 44, "general_windows_ordinary": 100}})
    # a changed windows.json or tokenizer table: the pinned digest differs
    for name in ("windows.json", "tokenizer_table.json"):
        good = (bundle / name).read_bytes()
        (bundle / name).write_bytes(good + b" ")
        with pytest.raises(core.EngineeringStop, match=f"{name} differs from the digest pinned"):
            ws.p10s2_windows_from_records(rows, bundle, man, cfg)
        (bundle / name).write_bytes(good)
    assert ws.find_once(b"abcabc", b"abc") is None and ws.find_once(b"aaa", b"aa") is None  # overlapping occurrences count
    assert ws.find_once(b"xabcx", b"abc") == 1


def test_ledger_marker_windows_must_equal_the_recorded_44(tmp_path: Path) -> None:
    rows, bundle, man, cfg = make_bundle(tmp_path)
    rec = ws.p10s2_windows_from_records(rows, bundle, man, cfg)
    lay = ws.RowLayout(rows)
    marks = [{**ws.ledger_entry(lay, w["start"], w["end"], "ADR-0025"), "stratum": "marker"} for w in rec["windows"] if w["stratum"] == "marker"]
    extra = {**ws.ledger_entry(lay, 5, 200, "ADR-0025 ordinary"), "stratum": "ordinary"}
    led = tmp_path / "ledger.json"
    led.write_text(json.dumps({"format": ws.LEDGER_FORMAT, "windows": [*marks, extra]}))
    doc = ws.build_excluded(rows, rec, ledger_path=led, ledger_absent=False)
    assert doc["ledger"]["state"] == "read" and any("same 44" in a for a in doc["assumptions"])
    led.write_text(json.dumps({"format": ws.LEDGER_FORMAT, "windows": [*marks[:-1], extra]}))  # one marker-like window missing
    with pytest.raises(core.EngineeringStop, match="not the 3 marker-like windows"):
        ws.build_excluded(rows, rec, ledger_path=led, ledger_absent=False)
    shifted = [{**marks[0], "start": marks[0]["start"] + 1}, *marks[1:]]
    led.write_text(json.dumps({"format": ws.LEDGER_FORMAT, "windows": shifted}))
    with pytest.raises(core.EngineeringStop):
        ws.build_excluded(rows, rec, ledger_path=led, ledger_absent=False)
    led.write_text(json.dumps({"format": ws.LEDGER_FORMAT, "windows": [{k: v for k, v in m.items() if k != "stratum"} for m in marks]}))  # a ledger that cannot be checked is refused
    with pytest.raises(core.EngineeringStop):
        ws.build_excluded(rows, rec, ledger_path=led, ledger_absent=False)
    absent = ws.build_excluded(rows, rec, ledger_path=None, ledger_absent=True)
    assert absent["ledger"]["state"] == "ABSENT-DECLARED" and "assumptions" in absent and "same 44" in absent["assumptions"][0]


def test_window_spans_command_on_a_parquet_fixture_without_a_tokenizer(tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    pa = pytest.importorskip("pyarrow")
    from pyarrow import parquet

    from arborlm.fetch_wikitext import DOWNLOAD_FILES

    rows, bundle, man, _ = make_bundle(tmp_path, n_marker=44, n_ord=100, per=8, seed=935302)
    src = tmp_path / "wikitext"
    src.mkdir()
    parquet.write_table(pa.table({"text": rows}), src / DOWNLOAD_FILES[1])
    from studies.p10i_s3 import data

    pin = {n: {"bytes": (src / n).stat().st_size, "sha256": hashlib.sha256((src / n).read_bytes()).hexdigest()} for n in (DOWNLOAD_FILES[1],)}
    monkeypatch.setattr(data, "pinned_files", lambda: pin)  # the fixture stands in for the pinned parquet
    out = tmp_path / "out" / "excluded.json"
    code = stages.main(["window-spans", "--source", str(src), "--bundle", str(bundle), "--manifest", str(man), "--out", str(out), "--ledger-absent", "--repo", str(ROOT)])
    assert code == 0
    res = json.loads(capsys.readouterr().out)
    assert res["found_exactly_once"] == 144 and res["windows"] == 144 and res["ledger"] == "ABSENT-DECLARED"
    doc = json.loads(out.read_text())
    assert doc["inputs"]["method"].startswith("recorded windows.json") and doc["end_offsets"] == "exclusive" and len(doc["spans"]) >= 144
    assert stages.main(["window-spans", "--source", str(src), "--bundle", str(bundle), "--manifest", str(man), "--out", str(out), "--ledger-absent", "--repo", str(ROOT)]) == 2  # never overwritten
    assert "tokenizers" not in sys.modules and "studies.p10s2.datagen" not in sys.modules


def test_the_command_no_longer_imports_the_p10s2_tokenizer_loader() -> None:
    import inspect

    from studies.p10i_s3 import rehearsal

    src = inspect.getsource(rehearsal.cmd_window_spans)
    assert "HFTokenizer" not in src and "p10s2.datagen" not in src and "tokenizers" not in src.replace("no tokenizer", "")


# ---------------- N1: a clean checkout ----------------
def test_n1_write_rate_table_and_freeze_writers_create_the_folder(tmp_path: Path) -> None:
    repo = tmp_path / "bare"
    repo.mkdir()
    pub = tmp_path / "pub.json"
    core.write_record(pub, {**core.envelope("rehearsal_public"), "rate_table": synthetic.rate_table(CFG)})
    assert stages.main(["write-rate-table", "--public", str(pub), "--repo", str(repo)]) == 0
    assert json.loads((repo / core.RATE_TABLE).read_text()) == synthetic.rate_table(CFG)
    assert stages.main(["write-rate-table", "--public", str(pub), "--repo", str(repo)]) == 2  # written once
    assert (ROOT / "studies/p10i_s3/freeze/README.md").is_file()  # the placeholder a clean checkout carries


# ---------------- N2: the sealed folder ----------------
def test_n2_sealed_folder_is_refused_inside_any_working_tree_and_under_the_lead_root(tmp_path: Path) -> None:
    ok = tmp_path / "sealed" / "items"
    calibration.require_outside_repo(ok, ROOT)
    for bad in (ROOT / "x", Path("/Users/daniellaloush/dandush03/ArborLM/sealed-x"), Path("/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/other/sealed")):
        with pytest.raises(core.EngineeringStop, match="refused"):
            calibration.require_outside_repo(bad, ROOT)
    # symlinks are resolved first
    link = tmp_path / "link"
    link.symlink_to(ROOT / "experiments")
    with pytest.raises(core.EngineeringStop, match="inside"):
        calibration.require_outside_repo(link / "sealed", ROOT)
    # any git working tree, not only this repository
    other = tmp_path / "other_repo"
    other.mkdir()
    subprocess.run(["git", "init", "-q", str(other)], check=True, env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull})
    with pytest.raises(core.EngineeringStop, match="git working tree"):
        calibration.require_outside_repo(other / "deep" / "sealed", ROOT)
    calibration.require_outside_repo(ROOT / "x", ROOT, allow_inside_repo=True)  # the synthetic device only
    assert CFG["seal"]["forbidden_roots"] == ["/Users/daniellaloush/dandush03/ArborLM"] and CFG["seal"]["expected_snapshot_gb"] == [1.4, 2.6]


def test_n2_r1_and_r3_refuse_without_an_explicit_sealed_dir(tmp_path: Path) -> None:
    run = tmp_path / "run"
    assert stages.main(["rehearse", "r1", "--run-dir", str(run), "--repo", str(ROOT)]) == 2
    assert stages.main(["rehearse", "r3", "--run-dir", str(run), "--repo", str(ROOT)]) == 2
    with pytest.raises(core.EngineeringStop, match="refused"):  # an explicit folder inside the repository is refused too
        stages.main(["rehearse", "r1", "--run-dir", str(run), "--repo", str(ROOT), "--sealed-dir", str(ROOT / "experiments" / "_scratch" / "s")])


# ---------------- N3: the failed-cell rule takes precedence ----------------
def _failed_at_ustar(reg: dict[str, Any], arm: str, cell: int) -> None:
    reg[core.nll_key(arm, FRESH, 0.003, cell, 16384, "enabled")] = None


def test_n3_a_nonfinite_value_at_ustar_is_a_failed_cell_not_an_integrity_case() -> None:
    # case A: M-TREE cell 3 is non-finite at U*, and its replay differs from enabled at 512: the failed-cell rule applies (NO CAPACITY), not NOT EVALUABLE
    specs = {(TREE, FRESH): Spec(gain=0.02, bad_replay=[3], bad_ckpts=[512]), (DENSE, FRESH): Spec(gain=0.03)}
    reg = synthetic.registry(CFG, specs)
    _failed_at_ustar(reg, TREE, 3)
    out = analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    assert out["regimes"][FRESH]["line1"]["label"] == "NO CAPACITY" and out["regimes"][FRESH]["integrity_problems"][TREE] == []
    assert out["regimes"][FRESH]["line2_tree"]["base_label"] == "NOT COMPETITIVE"  # memory failed cell: K1 and K3 false, not NOT EVALUABLE
    # case B: disabled differs from BASE at 2,048 for the failed cell
    specs = {(TREE, FRESH): Spec(gain=0.02, bad_disabled=[3], bad_ckpts=[2048]), (DENSE, FRESH): Spec(gain=0.03)}
    reg = synthetic.registry(CFG, specs)
    _failed_at_ustar(reg, TREE, 3)
    out = analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    assert out["regimes"][FRESH]["line1"]["label"] == "NO CAPACITY" and out["regimes"][FRESH]["integrity_problems"][TREE] == []
    # case C: the dense arm's failed cell with an earlier mismatch: line 2 is NOT EVALUABLE by the dense failed-cell rule (section 10), the integrity list stays empty
    specs = {(TREE, FRESH): Spec(gain=0.02), (DENSE, FRESH): Spec(gain=0.03, bad_replay=[5], bad_ckpts=[512])}
    reg = synthetic.registry(CFG, specs)
    _failed_at_ustar(reg, DENSE, 5)
    out = analysis.analyse(reg, synthetic.rate_table(CFG), CFG)
    assert out["regimes"][FRESH]["integrity_problems"][DENSE] == [] and out["regimes"][FRESH]["line2_tree"]["label"] == "NOT EVALUABLE"
    assert out["regimes"][FRESH]["line1"]["label"] == "DEPENDENT"
    # a cell that is finite at U* still gets the integrity check at an earlier checkpoint
    reg = synthetic.registry(CFG, {(TREE, FRESH): Spec(gain=0.02, bad_replay=[4], bad_ckpts=[512]), (DENSE, FRESH): Spec(gain=0.03)})
    assert analysis.analyse(reg, synthetic.rate_table(CFG), CFG)["regimes"][FRESH]["line1"]["label"] == "NOT EVALUABLE"


# ---------------- the loader never configures the process ----------------
SUITE = Path("/Users/daniellaloush/dandush03/ArborLM/experiments/P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d")


def test_parent_loader_does_not_call_configure_cpu() -> None:
    import inspect

    from studies.p10i_s3 import parents

    assert "configure_cpu(" not in inspect.getsource(parents.load_backbone) and "import configure_cpu" not in inspect.getsource(parents.load_backbone)


@pytest.mark.skipif(not SUITE.is_dir(), reason="needs the lead's P3 parent suite")
def test_two_real_parents_load_in_an_already_configured_process() -> None:
    from studies.p10i_s3 import gates, parents

    gates.configure_process()  # the entry point's one configuration; the old loader configured again and torch refused
    a, da = parents.load_backbone(ROOT, SUITE, 0)
    b, db = parents.load_backbone(ROOT, SUITE, 4)
    assert da != db and len(da) == 64 and sum(p.numel() for p in a.parameters()) == 27392
    assert parents.recorded_backbone_sha(ROOT, 0) == da and parents.recorded_backbone_sha(ROOT, 4) == db
