# ruff: noqa: E501
"""ADR-0016 section 4 (W3): verification of frozen material instead of ``verify_freeze``.

* every file under ``src/arborlm/``, ``configs/p8_locality_training.toml``, ``uv.lock``,
  ``pyproject.toml`` and the ten P8 test files are compared byte for byte with the git blobs at
  pushed commit ``378aeac`` (tree ``b13a9f9c...``);
* ``p8_core.source_digest()`` must equal the frozen digest (no extra ``*.py`` under ``src/arborlm/``);
* ADR-0015 is compared with its blob at ``2d10338`` (not with the freeze);
* all 60 ``eval.json`` and the 55 registered ``sim.json`` files are compared with the blobs committed
  at ``b8302c2``.

Trace ``.bin`` files are verified by ``p8_sim.load_trace`` (see ``preflight``). Nothing is repaired.
"""

import difflib
import json
import subprocess
from pathlib import Path
from typing import Any

from arborlm import p8_core as core

from . import common


class BlobReader:
    """One ``git cat-file --batch`` process reading ``<commit>:<path>`` contents."""

    def __init__(self, repo: Path):
        self._proc = subprocess.Popen(
            ["git", "-C", str(repo), "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def read(self, spec: str) -> bytes | None:
        assert self._proc.stdin is not None and self._proc.stdout is not None
        self._proc.stdin.write(spec.encode() + b"\n")
        self._proc.stdin.flush()
        header = self._proc.stdout.readline().decode().split()
        if len(header) != 3 or header[1] != "blob":
            return None
        size = int(header[2])
        data = self._proc.stdout.read(size)
        self._proc.stdout.read(1)  # trailing newline
        return data

    def close(self) -> None:
        if self._proc.stdin:
            self._proc.stdin.close()
        self._proc.wait()

    def __enter__(self) -> "BlobReader":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _tree_files(repo: Path, commit: str, prefix: str) -> list[str]:
    out = common.git_text(repo, "ls-tree", "-r", "--name-only", commit, "--", prefix)
    return [line for line in out.splitlines() if line]


def _working_files(repo: Path, prefix: str) -> list[str]:
    base = repo / prefix
    return sorted(
        p.relative_to(repo).as_posix()
        for p in base.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )


def check_p7b_citation(
    blob: bytes | None, cited: str = common.P7B_REPRODUCTION_SHA256
) -> list[str]:
    """The cited P7-B reproduction hash must equal ``reproduction_gate.sha256`` of the registered P8S
    stage manifest (blob at ``b8302c2``). Returns the problems (empty when it matches)."""
    where = f"{common.RESULTS_COMMIT}:{common.REGISTERED_SIM_MANIFEST_PATH}"
    if blob is None:
        return [f"p7b reproduction citation: no manifest blob at {where}"]
    try:
        registered = json.loads(blob.decode("utf-8"))["reproduction_gate"]["sha256"]
    except (ValueError, KeyError, TypeError) as exc:
        return [f"p7b reproduction citation: unreadable reproduction_gate in {where}: {exc!r}"]
    if registered != cited:
        return [
            f"p7b reproduction citation {cited} differs from the registered value {registered} "
            f"(reproduction_gate.sha256 at {where})"
        ]
    return []


def verify_frozen_files(repo: Path = common.ROOT) -> dict[str, Any]:
    """Files, trees, digest and ADR-0015 only (needs git objects, no local data)."""
    problems: list[str] = []
    for name, commit, tree in (
        ("freeze", common.FREEZE_COMMIT, common.FREEZE_TREE),
        ("results", common.RESULTS_COMMIT, common.RESULTS_TREE),
    ):
        got = common.git_text(repo, "rev-parse", f"{commit}^{{tree}}")
        if got != tree:
            problems.append(f"{name} commit {commit} has tree {got}, expected {tree}")
    src_files = _tree_files(repo, common.FREEZE_COMMIT, "src/arborlm")
    extra = [p for p in _working_files(repo, "src/arborlm") if p not in set(src_files)]
    if extra:
        problems.append(f"files under src/arborlm not in the freeze tree: {extra}")
    compared = 0
    with BlobReader(repo) as blobs:
        for path in [*src_files, *common.FROZEN_EXTRA_FILES]:
            blob = blobs.read(f"{common.FREEZE_COMMIT}:{path}")
            file = repo / path
            if blob is None:
                problems.append(f"{path}: not in the freeze tree")
            elif not file.is_file():
                problems.append(f"{path}: missing in the working tree")
            elif file.read_bytes() != blob:
                problems.append(f"{path}: differs from the freeze blob")
            compared += 1
        # ADR-0015: its blob at 2d10338, not the freeze
        adr_now = common.git_text(repo, "hash-object", common.ADR15_PATH)
        adr_blob = common.git_text(repo, "rev-parse", f"{common.ADR15_COMMIT}:{common.ADR15_PATH}")
        if adr_now != common.ADR15_BLOB or adr_blob != common.ADR15_BLOB:
            problems.append(
                f"ADR-0015 working blob {adr_now}, blob at {common.ADR15_COMMIT} {adr_blob}, "
                f"expected {common.ADR15_BLOB}"
            )
        old = blobs.read(f"{common.FREEZE_COMMIT}:{common.ADR15_PATH}")
        new = blobs.read(f"{common.ADR15_COMMIT}:{common.ADR15_PATH}")
        problems += check_p7b_citation(
            blobs.read(f"{common.RESULTS_COMMIT}:{common.REGISTERED_SIM_MANIFEST_PATH}")
        )
    adr_changes = _adr15_changes(old, new)
    if not adr_changes["only_status_line_and_section_17"]:
        problems.append(
            f"ADR-0015 differs from the freeze beyond the status line and §17: {adr_changes}"
        )
    digest = core.source_digest()
    if digest != common.FROZEN_SOURCE_DIGEST:
        problems.append(
            f"p8_core.source_digest() is {digest}, expected {common.FROZEN_SOURCE_DIGEST}"
        )
    return {
        "ok": not problems,
        "problems": problems,
        "freeze_commit": common.git_text(repo, "rev-parse", f"{common.FREEZE_COMMIT}^{{commit}}"),
        "freeze_tree": common.FREEZE_TREE,
        "results_commit": common.git_text(repo, "rev-parse", f"{common.RESULTS_COMMIT}^{{commit}}"),
        "results_tree": common.RESULTS_TREE,
        "files_compared_with_freeze_blobs": compared,
        "src_arborlm_files": len(src_files),
        "extra_files_compared": len(common.FROZEN_EXTRA_FILES),
        "source_digest": digest,
        "p7b_reproduction_record_cited": {
            **common.p7b_reproduction_record_cited(),
            "verified_against": f"reproduction_gate.sha256 of {common.REGISTERED_SIM_MANIFEST_PATH} "
            f"at {common.RESULTS_COMMIT}",
        },
        "source_digest_equals_frozen": digest == common.FROZEN_SOURCE_DIGEST,
        "adr0015": {
            "compared_with": f"blob at {common.ADR15_COMMIT} ({common.ADR15_BLOB}), not the freeze",
            "working_blob": adr_now,
            "changes_from_freeze": adr_changes,
            "note": "ADR-0015 changed after the freeze only in its status line and §17 (outcome record)",
        },
    }


def _adr15_changes(old: bytes | None, new: bytes | None) -> dict[str, Any]:
    if old is None or new is None:
        return {"only_status_line_and_section_17": False, "reason": "blob missing"}
    a, b = old.decode().splitlines(), new.decode().splitlines()
    ops = [op for op in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()]
    changes = [op for op in ops if op[0] != "equal"]
    status = 0
    section_17 = 0
    other: list[str] = []
    for tag, i1, i2, j1, j2 in changes:
        added = [x for x in b[j1:j2] if x.strip()]
        if tag == "replace" and a[i1].startswith("- Status:") and i2 - i1 == 1 == j2 - j1:
            status += 1
        elif tag == "insert" and added and added[0].startswith("## 17."):
            section_17 += 1
        else:
            other.append(f"{tag} old[{i1}:{i2}] new[{j1}:{j2}]")
    return {
        "only_status_line_and_section_17": status == 1 and section_17 == 1 and not other,
        "status_line_replaced": status,
        "section_17_inserted": section_17,
        "other_changes": other,
    }


def verify_results_blobs(
    repo: Path, eval_run: Path, sim_run: Path | None, labels: list[str] | None = None
) -> dict[str, Any]:
    """The 60 ``eval.json`` of the evaluation run and the registered ``sim.json`` files against the
    blobs committed at ``b8302c2``."""
    labels = labels or core.all_labels()
    problems: list[str] = []
    counts = {"eval_json": 0, "sim_json": 0}
    with BlobReader(repo) as blobs:
        for kind, run, file, stage in (
            ("eval_json", eval_run, "eval.json", "evaluate"),
            ("sim_json", sim_run, "sim.json", "simulate"),
        ):
            if run is None:
                continue
            for label in labels:
                local = run / "cells" / label / file
                spec = (
                    f"{common.RESULTS_COMMIT}:results/p8-2026-11-14/{stage}/{run.name}"
                    f"/cells/{label}/{file}"
                )
                blob = blobs.read(spec)
                if not local.is_file():
                    if kind == "sim_json" and label in common.SUPPLEMENT_CELLS and blob is None:
                        continue  # the five registered failures: no sim.json exists or is expected
                    problems.append(f"{kind} {label}: local file missing")
                    continue
                if blob is None:
                    problems.append(f"{kind} {label}: no blob at {common.RESULTS_COMMIT}")
                elif local.read_bytes() != blob:
                    problems.append(
                        f"{kind} {label}: differs from the blob at {common.RESULTS_COMMIT}"
                    )
                else:
                    counts[kind] += 1
    return {
        "ok": not problems,
        "problems": problems,
        "eval_json_verified": counts["eval_json"],
        "sim_json_verified": counts["sim_json"],
        "eval_run": eval_run.name,
        "sim_run": None if sim_run is None else sim_run.name,
        "reference": f"git blobs at {common.RESULTS_COMMIT} (tree {common.RESULTS_TREE})",
    }


def verify_frozen_material(
    repo: Path, eval_run: Path | None, sim_run: Path | None
) -> dict[str, Any]:
    out: dict[str, Any] = {"files": verify_frozen_files(repo)}
    if eval_run is not None:
        out["results_blobs"] = verify_results_blobs(repo, eval_run, sim_run)
    out["ok"] = all(v["ok"] for v in out.values() if isinstance(v, dict))
    out["problems"] = [p for v in list(out.values()) if isinstance(v, dict) for p in v["problems"]]
    return out
