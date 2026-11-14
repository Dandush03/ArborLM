"""Synthetic tests for the P7-B confirmation-file gates (ADR-0014 section 15) and the panel
reconstruction (section 7a). Every gate is exercised with: agree, differ, wrong coverage, stale
hash, missing file."""

import copy
from pathlib import Path
from typing import Any

import pytest

from arborlm import p7b_core as core
from arborlm import p7b_gates as gates
from arborlm import p7b_panel as panel
from arborlm.io import file_sha256, sha256, write_json
from arborlm.p7b_synth import synthetic_corpus
from arborlm.pilot_data import select

FAKE_TOOL_SHA = sha256(b"the auditor tool as it exists at HEAD")


@pytest.fixture(autouse=True)
def tool_at_head(monkeypatch: pytest.MonkeyPatch) -> None:
    """The tracked auditor tool files are not committed yet, so the HEAD lookup is replaced by a
    fixed hash (the real lookup is exercised against a temporary Git repository below)."""
    monkeypatch.setattr(core, "auditor_tool_sha256_at_head", lambda kind, repo=None: FAKE_TOOL_SHA)


# --- (a) panel confirmation
ROW_HASHES = [sha256(f"row-{i}".encode()) for i in range(512)]


def panel_files(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    record = {"panel_sha256": sha256(b"panel"), "row_sha256": ROW_HASHES, "ranks": [2560, 3072]}
    record_path = tmp_path / "panel_record.json"
    write_json(record_path, record)
    confirmation = {
        "schema": core.SCHEMA_PANEL_CONFIRMATION,
        "verdict": "AGREE",
        "tool": "auditor-tool 1.0",
        "tool_sha256": FAKE_TOOL_SHA,
        "panel_stage_run_id": "P7BP-run",
        "panel_record_sha256": file_sha256(record_path),
        "ranks": [2560, 3072],
        "panel_sha256": record["panel_sha256"],
        "row_sha256": list(ROW_HASHES),
        "earlier_panels_reproduced": dict(core.PRIOR_PANEL_SHA256),
        "overlap": {
            "with_P1_to_P5_panels": 0,
            "with_calibration_stream": 0,
            "with_full_training_pool": 0,
            "duplicates_within_panel": 0,
        },
    }
    path = tmp_path / "panel_confirmation.json"
    write_json(path, confirmation)
    return path, record_path, confirmation


def panel_gate(path: Path | None, record_path: Path, run: str = "P7BP-run") -> dict[str, Any]:
    return gates.check_panel_confirmation(path, panel_record_path=record_path, panel_run_id=run)


def test_panel_gate_agrees_and_records_the_file_hash(tmp_path: Path) -> None:
    path, record_path, _ = panel_files(tmp_path)
    result = panel_gate(path, record_path)
    assert result["verdict"] == "AGREE" and result["sha256"] == file_sha256(path)
    assert result["panel_record_sha256"] == file_sha256(record_path)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda c: c.update(verdict="DIFFER"), "not 'AGREE'"),
        (lambda c: c.update(schema="other"), "wrong schema"),
        (lambda c: c.update(tool=""), "no tool"),
        (lambda c: c.update(panel_sha256="0" * 64), "panel SHA-256 differs"),
        (lambda c: c["row_sha256"].__setitem__(5, "0" * 64), "per-row"),
        (lambda c: c["row_sha256"].pop(), "per-row"),  # wrong coverage: 511 rows
        (lambda c: c.update(ranks=[2048, 2560]), "rank range"),
        (lambda c: c.update(panel_stage_run_id="P7BP-other"), "different panel run"),
        (lambda c: c.update(panel_record_sha256="0" * 64), "stale or different"),
        (lambda c: c["earlier_panels_reproduced"].update(P3="0" * 64), "registered"),
        (lambda c: c["overlap"].update(with_full_training_pool=1), "overlap"),
        (lambda c: c.pop("overlap"), "overlap"),
    ],
)
def test_panel_gate_refuses(tmp_path: Path, mutate: Any, message: str) -> None:
    path, record_path, confirmation = panel_files(tmp_path)
    broken = copy.deepcopy(confirmation)
    mutate(broken)
    write_json(path, broken)
    with pytest.raises(core.GateError, match=message):
        panel_gate(path, record_path)


def test_panel_gate_refuses_a_missing_or_unreadable_file(tmp_path: Path) -> None:
    _, record_path, _ = panel_files(tmp_path)
    with pytest.raises(core.GateError, match="required"):
        panel_gate(None, record_path)
    with pytest.raises(core.GateError, match="not found"):
        panel_gate(tmp_path / "absent.json", record_path)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    with pytest.raises(core.GateError, match="not JSON"):
        panel_gate(bad, record_path)


def test_panel_gate_refuses_a_confirmation_made_for_an_earlier_record(tmp_path: Path) -> None:
    path, record_path, _ = panel_files(tmp_path)
    record = {"panel_sha256": sha256(b"panel"), "row_sha256": ROW_HASHES, "ranks": [2560, 3072]}
    record["extra"] = 1  # the record changed after the auditor confirmed it
    write_json(record_path, record)
    with pytest.raises(core.GateError, match="stale"):
        panel_gate(path, record_path)


# --- (b) layout-hash confirmation
LABELS = core.all_labels()


def layout_files(tmp_path: Path) -> tuple[Path, Path, dict[str, Any]]:
    table: dict[str, Any] = {"layouts": {}}
    checkpoints: dict[str, Any] = {}
    for label in LABELS:
        _, kind = core.parse_label(label)
        table["layouts"][label] = {}
        checkpoints[label] = {}
        for rows in (2, 8):
            checkpoints[label][f"R{rows}"] = {}
            for name in core.required_confirmation_layouts(kind):
                digest = sha256(f"{label}|{name}|{rows}".encode())
                table["layouts"][label][core.layout_key(name, rows)] = digest
                checkpoints[label][f"R{rows}"][name] = digest
    table_path = tmp_path / "layout_hash_table.json"
    write_json(table_path, table)
    confirmation = {
        "schema": core.SCHEMA_LAYOUT_CONFIRMATION,
        "verdict": "AGREE",
        "tool": "auditor-tool 1.0",
        "tool_sha256": FAKE_TOOL_SHA,
        "layout_stage_run_id": "P7BL-run",
        "layout_hash_table_sha256": file_sha256(table_path),
        "rows": [2, 8],
        "checkpoints": checkpoints,
    }
    path = tmp_path / "layout_confirmation.json"
    write_json(path, confirmation)
    return path, table_path, confirmation


def layout_gate(path: Path | None, table_path: Path) -> dict[str, Any]:
    return gates.check_layout_confirmation(
        path, hash_table_path=table_path, layout_run_id="P7BL-run"
    )


def test_layout_gate_agrees_for_all_81_checkpoints(tmp_path: Path) -> None:
    path, table_path, _ = layout_files(tmp_path)
    result = layout_gate(path, table_path)
    assert result["checkpoints"] == 81 and result["sha256"] == file_sha256(path)
    flat = next(lb for lb in LABELS if "flat" in lb)
    tree = next(lb for lb in LABELS if "fixed_tree" in lb)
    data = __import__("json").loads(path.read_text())
    assert sorted(data["checkpoints"][flat]["R2"]) == sorted(
        ["L-COAX", "L-NCOAX", *core.L_PCOAX]
    )  # 7 layouts, no BCOAX for flat
    assert "L-BCOAX" in data["checkpoints"][tree]["R8"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda c: c.update(verdict="DIFFER"), "not 'AGREE'"),
        (lambda c: c.update(layout_stage_run_id="P7BL-other"), "different layouts run"),
        (lambda c: c.update(layout_hash_table_sha256="0" * 64), "stale"),
        (lambda c: c.update(rows=[2, 32]), "rows"),
        (lambda c: c["checkpoints"].pop(LABELS[0]), "cover exactly"),  # wrong coverage
        (lambda c: c["checkpoints"][LABELS[0]]["R2"].pop("L-NCOAX"), "wrong layout set"),
        (lambda c: c["checkpoints"][LABELS[1]]["R8"].pop("L-BCOAX"), "wrong layout set"),
        (lambda c: c["checkpoints"][LABELS[2]]["R8"].update({"L-COAX": "0" * 64}), "differs"),
        (lambda c: c["checkpoints"][LABELS[4]]["R2"].update({"L-PCOAX-5": "0" * 64}), "differs"),
    ],
)
def test_layout_gate_refuses(tmp_path: Path, mutate: Any, message: str) -> None:
    path, table_path, confirmation = layout_files(tmp_path)
    broken = copy.deepcopy(confirmation)
    mutate(broken)
    write_json(path, broken)
    with pytest.raises(core.GateError, match=message):
        layout_gate(path, table_path)


def test_layout_gate_refuses_a_missing_file_and_a_stale_table(tmp_path: Path) -> None:
    path, table_path, _ = layout_files(tmp_path)
    with pytest.raises(core.GateError, match="required"):
        layout_gate(None, table_path)
    with pytest.raises(core.GateError, match="not found"):
        layout_gate(tmp_path / "x.json", table_path)
    table = __import__("json").loads(table_path.read_text())
    table["layouts"][LABELS[0]]["L-COAX|R2"] = "0" * 64  # the table changed after confirmation
    write_json(table_path, table)
    with pytest.raises(core.GateError, match="stale"):
        layout_gate(path, table_path)


# --- (c) re-simulation confirmation
SELECTION = core.independent_selection()


def resim_files(tmp_path: Path, stream: str = "A") -> tuple[Path, dict[str, str], dict[str, Any]]:
    hashes = {label: sha256(f"record-{stream}-{label}".encode()) for label in SELECTION}
    confirmation = {
        "schema": core.SCHEMA_RESIM_CONFIRMATION,
        "verdict": "AGREE",
        "tool": "auditor-tool 1.0",
        "tool_sha256": FAKE_TOOL_SHA,
        "stream": stream,
        "simulate_stage_run_id": "P7BSA-run",
        "selection": list(SELECTION),
        "settings": [{"R": 2, "C": 32}, {"R": 8, "C": 8}],
        "tie_rules": ["asc", "desc"],
        "streams_compared": ["actual", "null_1", "null_2", "null_3"],
        "layouts_compared": ["L-FREQ", "L-COAX", "L-BCOAX", *core.L_PCOAX],
        "record_sha256": dict(hashes),
        "checkpoints": {lb: {"differences": [], "integrity_problems": []} for lb in SELECTION},
    }
    path = tmp_path / f"resim_{stream}.json"
    write_json(path, confirmation)
    return path, hashes, confirmation


def resim_gate(path: Path | None, hashes: dict[str, str], stream: str = "A") -> dict[str, Any]:
    return gates.check_resim_confirmation(
        path, stream=stream, simulate_run_id="P7BSA-run", record_sha256=hashes
    )


def test_resim_gate_agrees_on_the_registered_18_checkpoint_selection(tmp_path: Path) -> None:
    assert len(SELECTION) == 18
    path, hashes, _ = resim_files(tmp_path)
    result = resim_gate(path, hashes)
    assert result["verdict"] == "AGREE" and result["sha256"] == file_sha256(path)
    assert len(result["selection"]) == 18


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda c: c.update(verdict="DIFFER"), "not 'AGREE'"),
        (lambda c: c.update(stream="B"), "stream 'B'"),
        (lambda c: c.update(simulate_stage_run_id="other"), "different simulate run"),
        (lambda c: c["selection"].pop(), "selection"),  # wrong coverage
        (lambda c: c.update(settings=[{"R": 2, "C": 32}]), "settings"),
        (lambda c: c.update(tie_rules=["asc"]), "tie rules"),
        (lambda c: c.update(streams_compared=["actual"]), "streams_compared"),
        (lambda c: c.update(layouts_compared=["L-FREQ", "L-COAX"]), "layouts_compared"),
        (lambda c: c["record_sha256"].update({SELECTION[0]: "0" * 64}), "stale"),
        (lambda c: c["record_sha256"].pop(SELECTION[3]), "record_sha256"),
        (lambda c: c["checkpoints"][SELECTION[5]].update(differences=["x"]), "differences"),
        (lambda c: c["checkpoints"][SELECTION[6]].update(integrity_problems=["x"]), "integrity"),
    ],
)
def test_resim_gate_refuses(tmp_path: Path, mutate: Any, message: str) -> None:
    path, hashes, confirmation = resim_files(tmp_path)
    broken = copy.deepcopy(confirmation)
    mutate(broken)
    write_json(path, broken)
    with pytest.raises(core.GateError, match=message):
        resim_gate(path, hashes)


def test_resim_gate_refuses_a_missing_file_and_checks_each_stream_separately(
    tmp_path: Path,
) -> None:
    path, hashes, _ = resim_files(tmp_path, "A")
    with pytest.raises(core.GateError, match="required"):
        resim_gate(None, hashes)
    with pytest.raises(core.GateError, match="not found"):
        resim_gate(tmp_path / "x.json", hashes)
    with pytest.raises(core.GateError, match="stream 'A'"):
        resim_gate(path, hashes, stream="B")  # the stream-A file does not confirm stream B


# --- panel reconstruction
PS = 4


def corpora() -> tuple[list[str], list[str]]:
    return synthetic_corpus(1, 300), synthetic_corpus(2, 160)


def small_expected() -> dict[str, str]:
    train, validation = corpora()
    _, full_train, _ = select(train, "train", 40)
    ranked, _, _ = select(validation, "validation", 5 * PS, excluded=full_train)  # P5's recipe
    return {
        name: sha256(b"".join(c.payload for c in ranked[n * PS : (n + 1) * PS]))
        for n, name in enumerate(("P1", "P2", "P3", "P4", "P5"))
    }


def test_ranks_before_the_new_panel_are_unchanged_by_asking_for_more() -> None:
    train, validation = corpora()
    _, full_train, _ = select(train, "train", 40)
    five, _, _ = select(validation, "validation", 5 * PS, excluded=full_train)
    six, _, _ = select(validation, "validation", 6 * PS, excluded=full_train)
    assert six[: 5 * PS] == five  # the SAME recipe: the first 20 ranks are identical


def test_reconstruction_reproduces_the_earlier_panels_and_gives_a_clean_panel() -> None:
    train, validation = corpora()
    result = panel.reconstruct_from_rows(
        train, validation, train_ranked=40, panel_size=PS, expected_earlier=small_expected()
    )
    record = result.record
    assert record["ranks"] == [5 * PS, 6 * PS] and record["rows"] == PS
    assert all(v["match"] for v in record["earlier_panels"].values())
    assert record["overlap"] == {
        "duplicates_within_panel": 0,
        "with_P1_to_P5_panels": 0,
        "with_calibration_stream": 0,
        "with_full_training_candidate_pool": 0,
    } or all(v == 0 for v in record["overlap"].values())
    assert len(record["row_sha256"]) == PS and record["panel_sha256"] == sha256(result.panel_bytes)
    assert [d["rank"] for d in record["rows_detail"]] == list(range(5 * PS, 6 * PS))
    # an independent second reconstruction agrees byte for byte
    again = panel.reconstruct_from_rows(
        train, validation, train_ranked=40, panel_size=PS, expected_earlier=small_expected()
    )
    assert again.panel_bytes == result.panel_bytes and again.record == record
    # the panel is exactly ranks 20..23 of the ranking P5's recipe produces
    _, full_train, _ = select(train, "train", 40)
    six, _, _ = select(validation, "validation", 6 * PS, excluded=full_train)
    assert result.panel_bytes == b"".join(c.payload for c in six[5 * PS :])


def test_a_reconstruction_that_does_not_reproduce_a_registered_hash_stops() -> None:
    train, validation = corpora()
    wrong = dict(small_expected())
    wrong["P4"] = "0" * 64
    with pytest.raises(core.StopError, match="earlier_panels_reproduced"):
        panel.reconstruct_from_rows(
            train, validation, train_ranked=40, panel_size=PS, expected_earlier=wrong
        )
    with pytest.raises(core.StopError, match="train_pool_reproduced"):
        panel.reconstruct_from_rows(
            train,
            validation,
            train_ranked=40,
            panel_size=PS,
            expected_earlier=small_expected(),
            registered_train_hash="0" * 64,
        )


def test_overlap_with_the_calibration_stream_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    train, validation = corpora()
    real = panel.select

    def tainted(rows: Any, split: str, count: int, *, excluded: set[str] | None = None) -> Any:
        ranked, pool, counts = real(rows, split, count, excluded=excluded)
        if split == "validation":
            calibration, _, _ = real(train, "train", 40)
            ranked = list(ranked)
            old = ranked[5 * PS]
            ranked[5 * PS] = type(old)(old.rank, old.row, old.offset, calibration[4 * PS].payload)
        return ranked, pool, counts

    monkeypatch.setattr(panel, "select", tainted)
    with pytest.raises(core.StopError, match="zero_overlap"):
        panel.reconstruct_from_rows(
            train, validation, train_ranked=40, panel_size=PS, expected_earlier=small_expected()
        )


def test_panel_bytes_are_verified_before_use() -> None:
    train, validation = corpora()
    result = panel.reconstruct_from_rows(
        train, validation, train_ranked=40, panel_size=PS, expected_earlier=small_expected()
    )
    tensor = panel.panel_tensor(result.panel_bytes, result.record)
    assert tuple(tensor.shape) == (PS, panel.CHUNK_BYTES)
    tampered = bytearray(result.panel_bytes)
    tampered[0] ^= 1
    with pytest.raises(core.StopError, match="SHA-256"):
        panel.panel_tensor(bytes(tampered), result.record)
    record = copy.deepcopy(result.record)
    record["row_sha256"][1] = "0" * 64
    with pytest.raises(core.StopError, match="per-row"):
        panel.panel_tensor(result.panel_bytes, record)


def test_data_dir_reconstruction_refuses_unexpected_provenance_without_reading_data(
    tmp_path: Path,
) -> None:
    write_json(
        tmp_path / "manifest.json",
        {
            "dataset_revision": "not-the-pinned-revision",
            "selected_files": [],
            "deferred_test": {"acquired": False, "inspected": False},
        },
    )
    with pytest.raises(core.StopError, match="provenance"):
        panel.reconstruct_from_data_dir(tmp_path)


# --- the binding of each gate to the auditor's tool file (audit m1)
def _gate_cases(tmp_path: Path) -> list[tuple[str, Path, Any]]:
    panel_path, record_path, _ = panel_files(tmp_path / "a")
    layout_path, table_path, _ = layout_files(tmp_path / "b")
    resim_path, hashes, _ = resim_files(tmp_path / "c")
    return [
        (
            "panel",
            panel_path,
            lambda path, **kw: gates.check_panel_confirmation(
                path, panel_record_path=record_path, panel_run_id="P7BP-run", **kw
            ),
        ),
        (
            "layouts",
            layout_path,
            lambda path, **kw: gates.check_layout_confirmation(
                path, hash_table_path=table_path, layout_run_id="P7BL-run", **kw
            ),
        ),
        (
            "resim",
            resim_path,
            lambda path, **kw: gates.check_resim_confirmation(
                path, stream="A", simulate_run_id="P7BSA-run", record_sha256=hashes, **kw
            ),
        ),
    ]


@pytest.fixture
def gate_cases(tmp_path: Path) -> list[tuple[str, Path, Any]]:
    for sub in "abc":
        (tmp_path / sub).mkdir()
    return _gate_cases(tmp_path)


def test_every_gate_records_the_tool_hash_it_matched(gate_cases: list[Any]) -> None:
    for kind, path, gate in gate_cases:
        binding = gate(path)["tool_binding"]
        assert binding["tool_sha256"] == FAKE_TOOL_SHA == binding["tool_sha256_at_head"]
        assert binding["tool_path"] == core.AUDITOR_TOOLS[kind] and binding["stand_in"] is False


@pytest.mark.parametrize("change", ["missing", "wrong", "empty"])
def test_every_gate_refuses_a_missing_or_wrong_tool_hash(
    gate_cases: list[Any], change: str
) -> None:
    for _, path, gate in gate_cases:
        data = __import__("json").loads(path.read_text())
        if change == "missing":
            data.pop("tool_sha256")
        elif change == "wrong":
            data["tool_sha256"] = sha256(b"an edited tool")
        else:
            data["tool_sha256"] = ""
        write_json(path, data)
        with pytest.raises(core.GateError, match="tool_sha256"):
            gate(path)


def test_the_dry_run_stand_in_is_refused_outside_a_dry_run(gate_cases: list[Any]) -> None:
    for kind, path, gate in gate_cases:
        data = __import__("json").loads(path.read_text())
        data["tool"], data["tool_sha256"] = core.STAND_IN_TOOL, core.STAND_IN_TOOL_SHA256
        write_json(path, data)
        with pytest.raises(core.GateError, match="stand-in is not accepted outside a dry run"):
            gate(path)  # the default is a registered run
        with pytest.raises(core.GateError, match="stand-in is not accepted outside a dry run"):
            gate(path, dry_run=False)
        binding = gate(path, dry_run=True)["tool_binding"]
        assert binding["stand_in"] is True and binding["tool_path"] == core.AUDITOR_TOOLS[kind]


def test_the_stand_in_label_cannot_hide_a_real_looking_hash(gate_cases: list[Any]) -> None:
    for _, path, gate in gate_cases:
        data = __import__("json").loads(path.read_text())
        data["tool"] = core.STAND_IN_TOOL  # stand-in name, real hash: still refused outside dry run
        write_json(path, data)
        with pytest.raises(core.GateError, match="stand-in"):
            gate(path)
        with pytest.raises(core.GateError, match="both the stand-in tool name and hash"):
            gate(path, dry_run=True)


def test_a_real_tool_hash_must_be_that_of_the_file_at_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lookup itself, against a temporary Git repository: ``git show HEAD:<path>``."""
    import subprocess

    monkeypatch.undo()
    repo = tmp_path / "repo"
    tool = repo / core.AUDITOR_TOOLS["layouts"]
    tool.parent.mkdir(parents=True)
    tool.write_text("print('v1')\n")

    def git(*args: str) -> None:
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@example.org",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=repo,
            check=True,
            capture_output=True,
        )

    git("init", "-q")
    with pytest.raises(core.GateError, match="not tracked at HEAD"):
        core.auditor_tool_sha256_at_head("layouts", repo)
    git("add", ".")
    git("commit", "-q", "-m", "tool")
    committed = file_sha256(tool)
    assert core.auditor_tool_sha256_at_head("layouts", repo) == committed
    tool.write_text("print('v2 edited, not committed')\n")  # the working copy is not what counts
    assert core.auditor_tool_sha256_at_head("layouts", repo) == committed
