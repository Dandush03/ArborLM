# ruff: noqa: E501
"""Constants, git helpers and identity values shared by the ADR-0016 supplement modules."""

import subprocess
from pathlib import Path

from arborlm.io import canonical_json, file_sha256, sha256

ROOT = Path(__file__).resolve().parents[2]

SUPPLEMENT_LABEL = "SUPPLEMENTARY (ADR-0016) — not the registered P8 output"
RECORD_LABEL = "SUPPLEMENTARY (ADR-0016) — not a registered P8 record"
SPEC_PATH = "docs/decisions/ADR-0016-p8-supplement-collapsed-cell-simulations.md"
ADR15_PATH = "docs/decisions/ADR-0015-p8-locality-aware-memory-training.md"

# the five cells of ADR-0016 section 1 (exactly these labels)
SUPPLEMENT_CELLS: tuple[str, ...] = (
    "b101-o301-s601-C04",
    "b101-o301-s601-C05",
    "b101-o301-s602-C04",
    "b101-o301-s602-C05",
    "b102-o302-s601-C05",
)

# frozen references of ADR-0016 section 4 (W3)
FREEZE_COMMIT = "378aeac"
FREEZE_TREE = "b13a9f9c09083a9b486adb9b691089f00409059f"
ADR15_COMMIT = "2d10338"
ADR15_BLOB = "add0a37659e228ba3f6e9a1cd414ec271d88c7c8"
RESULTS_COMMIT = "b8302c2"
RESULTS_TREE = "290d15dedc5cdaf57ea8bbbe3097575b1d582d14"
FROZEN_SOURCE_DIGEST = "8b5a03a08fc10a4ac29bdf9c6dd2d21945b9bb3aff459766b58304545d570507"
FROZEN_CONFIG = "configs/p8_locality_training.toml"
FROZEN_TEST_FILES: tuple[str, ...] = (
    "tests/conftest.py",
    "tests/p8_dry.py",
    "tests/p8_fake.py",
    "tests/test_p8_analysis.py",
    "tests/test_p8_core.py",
    "tests/test_p8_eval.py",
    "tests/test_p8_objective.py",
    "tests/test_p8_panel.py",
    "tests/test_p8_sim.py",
    "tests/test_p8_train.py",
)
FROZEN_EXTRA_FILES: tuple[str, ...] = (
    FROZEN_CONFIG,
    "uv.lock",
    "pyproject.toml",
    *FROZEN_TEST_FILES,
)

# ADR-0016 section 4: the registered P7-B reproduction record is cited by hash, not re-run
P7B_REPRODUCTION_SHA256 = "86608f87de87cd87b0656a35bbe0e178e9a37609e8fcd69375b1990db9d5f9a8"
EVAL_RUN_NAME = "P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f"
SIM_RUN_NAME = "P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3"
ANALYSIS_RUN_NAME = "P8A-20261114T044147896561Z-4a9976ed3c7d493c8a92293786f2572c"
RESULTS_DIR = "results/p8-supplement-2026-11-14"

REGISTERED_SIM_MANIFEST_PATH = f"results/p8-2026-11-14/simulate/{SIM_RUN_NAME}/manifest.json"

WALL_LIMIT_SECONDS = 1800.0  # ADR-0016 section 7: execution and analysis together
RSS_LIMIT_BYTES = 2 * 1024**3


def p7b_reproduction_record_cited() -> dict[str, str]:
    """The registered P7-B reproduction record, cited by hash; the supplement does not re-run it."""
    return {
        "sha256": P7B_REPRODUCTION_SHA256,
        "status": "cited, not re-run (ADR-0016 §4)",
        "source": f"registered P8S stage manifest at {RESULTS_COMMIT}",
    }


class SupplementError(Exception):
    """A supplement check failed; the supplement stops (never repaired, never retried)."""


def git(repo: Path, *args: str, check: bool = True) -> bytes:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)
    if check and done.returncode != 0:
        raise SupplementError(
            f"git {' '.join(args)} failed ({done.returncode}): {done.stderr.decode().strip()}"
        )
    return done.stdout


def git_text(repo: Path, *args: str) -> str:
    return git(repo, *args).decode().strip()


def main_checkout(repo: Path = ROOT) -> Path:
    """The main checkout of the repository (where the git-ignored ``experiments/`` lives)."""
    common = Path(git_text(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    return common.parent


def default_experiments_root(repo: Path = ROOT) -> Path:
    return main_checkout(repo) / "experiments"


def commit_available(repo: Path, commit: str) -> bool:
    done = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{commit}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    return done.returncode == 0


def is_ancestor(repo: Path, commit: str, descendant: str) -> bool:
    done = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", commit, descendant],
        capture_output=True,
        check=False,
    )
    return done.returncode == 0


def supplement_source_hashes(root: Path = ROOT) -> dict[str, str]:
    base = root / "supplements" / "p8s"
    return {
        f"supplements/p8s/{p.relative_to(base).as_posix()}": file_sha256(p)
        for p in sorted(base.rglob("*.py"))
    }


def supplement_source_digest(root: Path = ROOT) -> str:
    """Digest of every ``*.py`` under ``supplements/p8s/`` (same recipe as the frozen source digest)."""
    return sha256(canonical_json(supplement_source_hashes(root)))


def supplement_spec_sha256(root: Path = ROOT) -> str:
    return file_sha256(root / SPEC_PATH)


def frozen_inputs(repo: Path, eval_spec_sha256: str) -> dict[str, object]:
    """What the supplement was verified *against*; never stated as the producer's own identity."""
    return {
        "label": "inputs verified against; not the producer of this record",
        "source_sha256": FROZEN_SOURCE_DIGEST,
        "spec_sha256_registered_records": eval_spec_sha256,
        "freeze_commit": git_text(repo, "rev-parse", f"{FREEZE_COMMIT}^{{commit}}"),
        "freeze_tree": FREEZE_TREE,
        "freeze_commit_cited_in_older_records_as": "80f46ae",
        "results_commit": git_text(repo, "rev-parse", f"{RESULTS_COMMIT}^{{commit}}"),
        "results_tree": RESULTS_TREE,
        "p7b_reproduction_record_cited": p7b_reproduction_record_cited(),
    }
