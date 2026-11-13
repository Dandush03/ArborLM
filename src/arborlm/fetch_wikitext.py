"""Acquire the pinned, local WikiText-2 pilot corpus without third-party tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .io import canonical_json, file_sha256, fsync_dir

REVISION = "b08601e04326c79dfdd32d625aee71d232d685c3"
REPO = "Salesforce/WikiText"
SUBSET = "wikitext-2-raw-v1"
README_URL = f"https://huggingface.co/datasets/{REPO}/raw/{REVISION}/README.md"
MAX_PAYLOAD_BYTES = 10_000_000
CHUNK_BYTES = 64 * 1024
TIMEOUT_SECONDS = 30
ADR = "docs/decisions/ADR-0004-real-data-pilot-prerequisite.md"
LICENSE_REFERENCES = [
    "https://creativecommons.org/licenses/by-sa/3.0/",
    "https://www.gnu.org/licenses/fdl-1.3.html",
]

FILES: dict[str, dict[str, int | str]] = {
    "train-00000-of-00001.parquet": {
        "bytes": 6_357_543,
        "sha256": "e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7",
    },
    "validation-00000-of-00001.parquet": {
        "bytes": 657_209,
        "sha256": "204929b7ff9d6184953f867dedb860e40aa69c078fc1e54b3baaa8fb28511c4c",
    },
    "test-00000-of-00001.parquet": {
        "bytes": 732_610,
        "sha256": "5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91",
    },
}
DOWNLOAD_FILES = tuple(name for name in FILES if not name.startswith("test-"))
Opener = Callable[..., Any]


class DownloadError(RuntimeError):
    """A download failed a pinned size, checksum, cap, or publication check."""


def _url(filename: str) -> str:
    return (
        f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/"
        f"{SUBSET}/{filename}?download=true"
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _download(
    url: str,
    destination: Path,
    *,
    max_bytes: int,
    opener: Opener,
) -> tuple[int, str, str]:
    """Stream a bounded HTTPS response to a new staging file and return evidence."""
    digest = hashlib.sha256()
    received = 0
    created = False
    try:
        with opener(url, timeout=TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > max_bytes:
                raise DownloadError(f"declared response size exceeds limit for {url}")
            with destination.open("xb") as output:
                created = True
                while True:
                    chunk = response.read(min(CHUNK_BYTES, max_bytes - received + 1))
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > max_bytes:
                        raise DownloadError(f"response exceeds byte limit for {url}")
                    output.write(chunk)
                    digest.update(chunk)
                output.flush()
                os.fsync(output.fileno())
    except DownloadError:
        if created:
            destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if created:
            destination.unlink(missing_ok=True)
        raise DownloadError(f"failed to download {url}: {type(exc).__name__}: {exc}") from exc
    return received, digest.hexdigest(), final_url


def _existing_file(path: Path, expected_size: int, expected_sha256: str) -> bool:
    if not path.exists():
        return False
    if not path.is_file():
        raise DownloadError(f"existing path is not a regular file; preserved: {path}")
    actual_size = path.stat().st_size
    actual_hash = file_sha256(path)
    if actual_size != expected_size or actual_hash != expected_sha256:
        raise DownloadError(
            f"existing file does not match pinned bytes; preserved as failure evidence: {path}"
        )
    return True


def _publish_no_replace(staged: Path, target: Path) -> None:
    """Atomically publish a staged file without replacing any existing path."""
    try:
        os.link(staged, target)
    except FileExistsError as exc:
        raise DownloadError(
            f"target appeared during acquisition; existing path preserved: {target}"
        ) from exc
    staged.unlink()
    fsync_dir(target.parent)


def _read_manifest(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise DownloadError(
            f"existing manifest is invalid and was preserved: {path}: {exc}"
        ) from exc
    if not isinstance(value, dict) or value.get("dataset_revision") != REVISION:
        raise DownloadError(f"existing manifest conflicts with pinned revision; preserved: {path}")
    return value


def fetch_dataset(
    output_dir: Path,
    *,
    command: list[str],
    opener: Opener = urllib.request.urlopen,
    now: Callable[[], str] = _utc_now,
) -> dict[str, object]:
    """Download and verify the approved train/validation files and publisher card.

    The test split is included in provenance with its pinned identity, but this
    function never requests or opens its URL.
    """
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    existing_manifest = _read_manifest(manifest_path)
    if existing_manifest is not None:
        if existing_manifest.get("selected_files") != list(DOWNLOAD_FILES):
            raise DownloadError(
                "existing manifest has different split selection; "
                f"preserved: {manifest_path}"
            )

    budget = MAX_PAYLOAD_BYTES
    verified_existing: dict[str, dict[str, object]] = {}
    for filename in DOWNLOAD_FILES:
        details = FILES[filename]
        target = output_dir / filename
        if _existing_file(target, int(details["bytes"]), str(details["sha256"])):
            verified_existing[filename] = {
                "path": filename,
                "bytes": int(details["bytes"]),
                "sha256": str(details["sha256"]),
                "source_url": _url(filename),
                "downloaded_this_run": False,
            }

    readme_path = output_dir / "README.upstream.md"
    if readme_path.exists():
        if not readme_path.is_file() or readme_path.stat().st_size > budget:
            raise DownloadError(f"existing publisher README invalid; preserved: {readme_path}")
        readme_digest = file_sha256(readme_path)
        readme_size = readme_path.stat().st_size
        readme_existing = True
    else:
        readme_existing = False
        readme_digest = ""
        readme_size = 0

    if existing_manifest is not None:
        missing_files = [name for name in DOWNLOAD_FILES if name not in verified_existing]
        if missing_files:
            raise DownloadError(
                "existing acquisition manifest has missing corpus files "
                f"{missing_files}; manifest preserved: {manifest_path}"
            )
        recorded_files = existing_manifest.get("files")
        if not isinstance(recorded_files, dict):
            raise DownloadError(
                f"existing manifest lacks file checksums; preserved: {manifest_path}"
            )
        for filename in DOWNLOAD_FILES:
            details = FILES[filename]
            entry = recorded_files.get(filename)
            if (
                not isinstance(entry, dict)
                or entry.get("bytes") != details["bytes"]
                or entry.get("sha256") != details["sha256"]
            ):
                raise DownloadError(
                    "existing manifest conflicts with pinned file "
                    f"{filename}; preserved: {manifest_path}"
                )
        readme_entry = existing_manifest.get("publisher_readme")
        if (
            not readme_existing
            or not isinstance(readme_entry, dict)
            or readme_entry.get("bytes") != readme_size
            or readme_entry.get("sha256") != readme_digest
        ):
            raise DownloadError(
                f"existing publisher README conflicts with its manifest; preserved: {readme_path}"
            )
        history_path = output_dir / "acquisition-history.jsonl"
        history_line = canonical_json({
            "status": "completed",
            "command_argv": command,
            "attempted_utc": now(),
        })
        with history_path.open("ab") as stream:
            stream.write(history_line)
            stream.flush()
            os.fsync(stream.fileno())
        return existing_manifest

    if readme_existing:
        raise DownloadError(
            f"publisher README exists without its acquisition manifest; preserved: {readme_path}"
        )

    stage_context = tempfile.TemporaryDirectory(prefix=".wikitext2-", dir=output_dir)
    stage_dir = Path(stage_context.name)
    try:
        staged: dict[str, tuple[Path, dict[str, object]]] = {}
        acquired_bytes = 0
        for filename in DOWNLOAD_FILES:
            if filename in verified_existing:
                continue
            details = FILES[filename]
            expected_size = int(details["bytes"])
            expected_hash = str(details["sha256"])
            if expected_size > budget:
                raise DownloadError("pinned corpus exceeds the remaining 10,000,000-byte cap")
            path = stage_dir / filename
            size, checksum, final_url = _download(
                _url(filename), path, max_bytes=min(expected_size, budget), opener=opener
            )
            acquired_bytes += size
            budget -= size
            if size != expected_size or checksum != expected_hash:
                path.unlink(missing_ok=True)
                raise DownloadError(
                    f"pinned file mismatch for {filename}: got {size} bytes sha256={checksum}"
                )
            staged[filename] = (path, {
                "path": filename,
                "bytes": size,
                "sha256": checksum,
                "source_url": _url(filename),
                "resolved_url": final_url,
                "downloaded_this_run": True,
            })

        if not readme_existing:
            readme_stage = stage_dir / "README.upstream.md"
            readme_size, readme_digest, readme_final_url = _download(
                README_URL, readme_stage, max_bytes=min(1_000_000, budget), opener=opener
            )
            acquired_bytes += readme_size
            budget -= readme_size
            if readme_size == 0:
                raise DownloadError("publisher README was empty")
        else:
            readme_final_url = README_URL

        files_manifest: dict[str, dict[str, object]] = dict(verified_existing)
        for filename, (_path, evidence) in staged.items():
            files_manifest[filename] = evidence
        for filename in DOWNLOAD_FILES:
            if filename not in files_manifest:
                raise DownloadError(f"missing verified split evidence for {filename}")

        manifest: dict[str, object] = {
            "dataset": "WikiText-2 raw",
            "dataset_subset": SUBSET,
            "dataset_revision": REVISION,
            "acquisition_adr": ADR,
            "selected_files": list(DOWNLOAD_FILES),
            "files": files_manifest,
            "deferred_test": {
                "path": f"{SUBSET}/{list(FILES)[-1]}",
                "bytes": FILES["test-00000-of-00001.parquet"]["bytes"],
                "sha256": FILES["test-00000-of-00001.parquet"]["sha256"],
                "source_url": _url("test-00000-of-00001.parquet"),
                "acquired": False,
                "inspected": False,
                "reason": "deferred pending a preregistered final-evaluation decision",
            },
            "publisher_readme": {
                "path": "README.upstream.md",
                "source_url": README_URL,
                "resolved_url": readme_final_url,
                "bytes": readme_size,
                "sha256": readme_digest,
                "downloaded_this_run": not readme_existing,
            },
            "publisher": {
                "name": REPO,
                "revision": REVISION,
                "card_url": f"https://huggingface.co/datasets/{REPO}/blob/{REVISION}/README.md",
                "license_observations": {
                    "readme_front_matter": ["CC-BY-SA-3.0", "GFDL"],
                    "readme_body": [
                        {
                            "line": 326,
                            "license": "CC-BY-SA-4.0",
                            "note": "The preserved README body also names this license.",
                        }
                    ],
                    "note": (
                        "Publisher metadata is preserved as written; "
                        "no legal precedence is inferred."
                    ),
                },
                "license_references": LICENSE_REFERENCES,
                "attribution": "WikiText dataset by Salesforce; see preserved README.upstream.md.",
            },
            "payload_cap_bytes": MAX_PAYLOAD_BYTES,
            "payload_bytes_downloaded_this_run": acquired_bytes,
            "payload_bytes_selected_total": sum(
                int(FILES[name]["bytes"]) for name in DOWNLOAD_FILES
            ),
            "command_argv": command,
            "acquired_utc": now(),
        }

        # Publish only after every transfer has passed its bounded stream and
        # integrity checks. Hard-link creation is atomic and refuses overwrite.
        for filename, (path, _evidence) in staged.items():
            _publish_no_replace(path, output_dir / filename)
        if not readme_existing:
            _publish_no_replace(readme_stage, readme_path)
        elif file_sha256(readme_path) != readme_digest:
            raise DownloadError(
                f"publisher README changed during acquisition; preserved: {readme_path}"
            )

        # Recheck published corpus bytes before publishing the manifest.
        for filename in DOWNLOAD_FILES:
            details = FILES[filename]
            if not _existing_file(
                output_dir / filename, int(details["bytes"]), str(details["sha256"])
            ):
                raise DownloadError(f"published file missing: {filename}")

        manifest["files"] = {
            filename: {
                **files_manifest[filename],
                "downloaded_this_run": filename in staged,
            }
            for filename in DOWNLOAD_FILES
        }
        manifest_bytes = canonical_json(manifest)
        manifest_stage = stage_dir / "manifest.json"
        with manifest_stage.open("xb") as stream:
            stream.write(manifest_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        _publish_no_replace(manifest_stage, manifest_path)
        return manifest
    finally:
        stage_context.cleanup()


def main(argv: list[str] | None = None) -> int:
    actual_argv = sys.argv[1:] if argv is None else argv
    command = [sys.executable, "-m", "arborlm.fetch_wikitext", *actual_argv]
    parser = argparse.ArgumentParser(
        description="Fetch approved WikiText-2 train and validation splits"
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/wikitext2"),
        help="local ignored destination (default: data/wikitext2)",
    )
    args = parser.parse_args(argv)
    try:
        manifest = fetch_dataset(args.output_dir, command=command)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure_event = canonical_json({
            "status": "failed",
            "command_argv": command,
            "attempted_utc": _utc_now(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        with (args.output_dir / "acquisition-history.jsonl").open("ab") as stream:
            stream.write(failure_event)
            stream.flush()
            os.fsync(stream.fileno())
        print(f"WikiText-2 acquisition failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
