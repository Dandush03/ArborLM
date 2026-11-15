"""ADR-0016 gate 4: frozen-file blob comparison, frozen source digest with the supplement code
present, the not-called list, and the no-patching rule. The blob checks need the git objects of the
freeze commits (a shallow clone skips them; the recorded preflight run does not skip)."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from arborlm import p8_core as core  # noqa: E402
from arborlm.io import write_json  # noqa: E402
from supplements.p8s import common, frozen  # noqa: E402

needs_git = pytest.mark.skipif(
    not all(
        common.commit_available(common.ROOT, c)
        for c in (common.FREEZE_COMMIT, common.ADR15_COMMIT, common.RESULTS_COMMIT)
    ),
    reason="freeze commits not available in this clone (shallow checkout)",
)
SUPPLEMENT_FILES = sorted((common.ROOT / "supplements").rglob("*.py"))


@needs_git
def test_frozen_files_equal_the_freeze_blobs() -> None:
    out = frozen.verify_frozen_files(common.ROOT)
    assert out["ok"], out["problems"]
    assert out["freeze_tree"] == "b13a9f9c09083a9b486adb9b691089f00409059f"
    assert out["src_arborlm_files"] == 85
    assert out["files_compared_with_freeze_blobs"] == 85 + len(common.FROZEN_EXTRA_FILES)
    assert out["adr0015"]["changes_from_freeze"]["only_status_line_and_section_17"]
    assert out["p7b_reproduction_record_cited"]["sha256"] == common.P7B_REPRODUCTION_SHA256


def test_frozen_source_digest_unchanged_with_the_supplement_code_present() -> None:
    assert SUPPLEMENT_FILES, "the supplement package exists"
    assert core.source_digest() == common.FROZEN_SOURCE_DIGEST
    assert (
        core.source_digest() == "8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507"
    )
    src = common.ROOT / "src" / "arborlm"
    assert not any("supplement" in p.name or "p8s" in p.name for p in src.rglob("*.py"))


def test_no_forbidden_frozen_calls_and_no_patching() -> None:
    forbidden = {
        "verify_freeze",
        "load_cells",
        "check_provenance",
        "run_analysis",
        "require_freeze",
    }
    patching = {"monkeypatch", "setattr", "patch"}
    for path in SUPPLEMENT_FILES:
        for node in ast.walk(ast.parse(path.read_text())):
            name = None
            if isinstance(node, ast.Name):
                name = node.id
            elif isinstance(node, ast.Attribute):
                name = node.attr
            elif isinstance(node, ast.alias):
                name = node.name.rpartition(".")[2]
            if name in forbidden or name in patching:
                raise AssertionError(f"{path.name}:{getattr(node, 'lineno', '?')} uses {name}")
            if isinstance(node, ast.Assign):  # no assignment into a frozen module attribute
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                        assert target.value.id not in {"core", "b_core", "a_core", "p8_sim", "an"}


def test_no_new_file_under_src_or_other_frozen_dirs() -> None:
    for path in SUPPLEMENT_FILES:
        assert "src/arborlm" not in path.as_posix()
    assert (common.ROOT / "supplements" / "__init__.py").is_file()
    assert (common.ROOT / "supplements" / "p8s" / "__init__.py").is_file()


@needs_git
def test_results_blob_check_detects_missing_and_changed_files(tmp_path: Path) -> None:
    eval_run = tmp_path / common.EVAL_RUN_NAME
    label = core.all_labels()[0]
    (eval_run / "cells" / label).mkdir(parents=True)
    write_json(eval_run / "cells" / label / "eval.json", {"not": "the registered record"})
    out = frozen.verify_results_blobs(common.ROOT, eval_run, None)
    assert not out["ok"]
    assert any(label in p and "differs" in p for p in out["problems"])
    assert out["eval_json_verified"] == 0 and len(out["problems"]) == 60


def test_adr15_change_classifier() -> None:
    old = b"# T\n\n- Status: **A**\n\nbody\n"
    good = b"# T\n\n- Status: **B**\n\nbody\n\n## 17. Outcome record\n\ntext\n"
    assert frozen._adr15_changes(old, good)["only_status_line_and_section_17"]
    edited = b"# T\n\n- Status: **B**\n\nbody changed\n\n## 17. Outcome record\n\ntext\n"
    assert not frozen._adr15_changes(old, edited)["only_status_line_and_section_17"]
    assert not frozen._adr15_changes(old, None)["only_status_line_and_section_17"]


def test_blob_reader_returns_none_for_missing_objects() -> None:
    with frozen.BlobReader(common.ROOT) as blobs:
        assert blobs.read("HEAD:no/such/file.txt") is None
        head = blobs.read("HEAD:pyproject.toml")
    assert head is not None and head == (common.ROOT / "pyproject.toml").read_bytes()


REGISTERED_REPRO = "86608f87de87cd87b0656a35bbe0e178e9a37609e8fcd69375b1990db9d5f9a8"


def test_p7b_reproduction_record_is_cited_by_hash_not_re_run() -> None:
    cited = common.p7b_reproduction_record_cited()
    assert cited["sha256"] == REGISTERED_REPRO == common.P7B_REPRODUCTION_SHA256
    assert cited["status"] == "cited, not re-run (ADR-0016 §4)"
    assert cited["source"] == f"registered P8S stage manifest at {common.RESULTS_COMMIT}"


@needs_git
def test_frozen_inputs_carry_the_citation() -> None:
    inputs = common.frozen_inputs(common.ROOT, "0" * 64)
    assert inputs["p7b_reproduction_record_cited"] == common.p7b_reproduction_record_cited()


@needs_git
def test_citation_equals_the_registered_manifest_blob() -> None:
    with frozen.BlobReader(common.ROOT) as blobs:
        blob = blobs.read(f"{common.RESULTS_COMMIT}:{common.REGISTERED_SIM_MANIFEST_PATH}")
    assert blob is not None
    assert frozen.check_p7b_citation(blob) == []


def test_citation_check_refuses_a_mismatch_a_missing_blob_and_unreadable_content() -> None:
    import json

    good = json.dumps({"reproduction_gate": {"sha256": REGISTERED_REPRO}}).encode()
    assert frozen.check_p7b_citation(good) == []
    other = json.dumps({"reproduction_gate": {"sha256": "0" * 64}}).encode()
    problems = frozen.check_p7b_citation(other)
    assert len(problems) == 1 and "differs from the registered value" in problems[0]
    assert frozen.check_p7b_citation(good, cited="1" * 64)  # the cited value is the one compared
    assert frozen.check_p7b_citation(None)
    assert frozen.check_p7b_citation(b"not json")
    assert frozen.check_p7b_citation(b"{}")
