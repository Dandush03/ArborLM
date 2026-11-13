"""Recoverable source snapshots and append-only local run events."""

import io
import os
import platform
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from importlib.metadata import distributions
from pathlib import Path
from typing import Any
from uuid import uuid4

import psutil

from .config import SCHEMA, SPEC
from .io import atomic_write, canonical_json, file_sha256, sha256, write_json

ROOT_FILES = {
    ".gitignore",
    ".python-version",
    "AGENTS.md",
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "uv.lock",
}
SOURCE_DIRS = {".github", "configs", "docs", "prompts", "src", "templates", "tests"}
SOURCE_TYPES = {".json", ".md", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml"}
EXCLUDED = {"experiments", "results", "secrets", "__pycache__", "node_modules"}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def allocate_run(root: Path, *, prefix: str = "E0") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    run = root / f"{prefix}-{stamp}-{uuid4().hex}"
    run.mkdir(mode=0o700)
    return run


def _git(cwd: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(cwd), *arguments])


def _source_file(name: Path) -> bool:
    if str(name) in ROOT_FILES:
        return True
    if name.parts[0] not in SOURCE_DIRS or name.suffix.lower() not in SOURCE_TYPES:
        return False
    return all(
        part.lower() not in EXCLUDED
        and not any(
            word in part.lower() for word in ("secret", "credential", "private_key", ".env")
        )
        and (part == ".github" or not part.startswith("."))
        for part in name.parts
    )


def record_source(run: Path, cwd: Path, *, spec: str = SPEC) -> dict[str, Any]:
    root = Path(os.fsdecode(_git(cwd, "rev-parse", "--show-toplevel").rstrip(b"\n")))
    commit = _git(root, "rev-parse", "HEAD").decode().strip()
    status = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    tracked = _git(root, "ls-files", "--cached", "-z").split(b"\0")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    names = sorted({Path(os.fsdecode(n)) for n in tracked + untracked if n})
    selected = [name for name in names if _source_file(name)]
    # Restrict the patch to recoverable source paths; never copy ignored/private material.
    diff = _git(root, "diff", "--binary", "--no-ext-diff", "HEAD", "--", *map(str, selected))
    atomic_write(run / "source.diff", diff)
    stream = io.BytesIO()
    contents: dict[str, str] = {}
    with tarfile.open(fileobj=stream, mode="w") as tar:
        for name in selected:
            path = root / name
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
                continue
            data = path.read_bytes()
            member = tarfile.TarInfo(name.as_posix())
            member.size = len(data)
            member.mode = 0o755 if os.access(path, os.X_OK) else 0o644
            tar.addfile(member, io.BytesIO(data))
            contents[name.as_posix()] = sha256(data)
    atomic_write(run / "source.tar", stream.getvalue())
    identity = {
        "code_commit": commit,
        "dirty": bool(status),
        "git_root": str(root),
        "patch": {"file": "source.diff", "sha256": file_sha256(run / "source.diff")},
        "archive": {"file": "source.tar", "sha256": file_sha256(run / "source.tar")},
        "archive_file_sha256": contents,
        "scope": "tracked and untracked allowlisted project source and documentation; "
        "excluded secrets, virtual environments, caches, experiment output and .git",
        "lock_sha256": contents["uv.lock"],
        "spec_sha256": contents[spec],
    }
    write_json(run / "source.json", identity)
    return identity


def record_environment(run: Path, *, family: str = "E0") -> dict[str, Any]:
    mem = psutil.virtual_memory()
    cpu = platform.processor()
    if sys.platform == "darwin":
        cpu = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).decode().strip()
    elif sys.platform == "linux":
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    env = {
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": cpu,
        "logical_cpus": psutil.cpu_count(),
        "ram_bytes": mem.total,
        "ram_unit": "bytes",
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "python_compiler": platform.python_compiler(),
        "accelerator": "cpu",
        "storage_device": None,
        "storage_device_reason": f"no storage experiment in {family}",
        "packages": {dist.metadata["Name"]: dist.version for dist in distributions()},
    }
    write_json(run / "environment.json", env)
    return env


def manifest(run: Path, operation: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "run_id": run.name,
        "operation": operation,
        "experiment_family": "E0",
        "question_id": "G0",
        "hypothesis": None,
        "hypothesis_null_reason": "infrastructure validation only; does not test H1-H5",
        "astra_spec_review": "NOT_PERFORMED",
        "astra_result_review": "NOT_PERFORMED",
        "authorized_spec_reference": SPEC,
        "authorized_result_review": "PENDING",
        "human_merge_approval": "PENDING",
        "human_publication_approval": "PENDING",
        "status": "running",
        "created_utc": utc_now(),
        **extra,
    }


def append_event(run: Path, event: dict[str, Any]) -> None:
    with (run / "metrics.jsonl").open("ab") as stream:
        stream.write(canonical_json(event))
        stream.flush()
        os.fsync(stream.fileno())


def runtime_supported() -> None:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("E0 requires Python 3.12")
    if (sys.platform, platform.machine()) not in {("darwin", "arm64"), ("linux", "x86_64")}:
        raise RuntimeError("E0 supports macOS arm64 and Linux x86_64 CPU")
