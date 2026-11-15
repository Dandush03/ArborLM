# ruff: noqa: E501
"""Fetch-and-verify of the approved downloads (ADR-0022 sections 14.1, 18). NOT RUN, and not called by any test.

It refuses to run unless the explicit ``--i-have-recorded-human-approval`` flag and a manifest path are given (``fetch_guard.check_authorization``), validates the manifest against the approved set
(``fetch_guard.validate_manifest``), and only then makes plain HTTPS requests with the standard library, each followed by a hash check: no account, no token, no Hub client. Files go to a git-ignored
directory named by source and revision or download date. The total download is capped at 1.5 GB and the new disk use at 6 GB. The Tatoeba files are fetched in one session, and the symmetry of the link files
is checked afterwards from the files (``data.link_symmetry``).

The package wheels of the data-generation step are not fetched here: they wait for the human lead's confirmation with sizes (ADR-0022 section 14.2) and are installed with ``uv run --locked
--with-requirements studies/p10s2/requirements-datagen.txt`` once it is recorded.

Status of this code: written, reviewed by self-check only, never executed.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from . import fetch_guard as g
from .output import emit_plain


def _download(url: str, dest: Path, expected_size: int | None) -> None:  # pragma: no cover - the only function that touches the network
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "p10s2-fetch"})  # noqa: S310
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=120) as r, tmp.open("wb") as out:  # noqa: S310
        n = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            n += len(chunk)
            if n > g.DOWNLOAD_CAP_BYTES:
                raise g.FetchRefused("refused: the download exceeded the cap")
            out.write(chunk)
    if expected_size is not None and tmp.stat().st_size != expected_size and "tatoeba" not in str(dest):
        tmp.unlink()
        raise g.FetchRefused(f"refused: {dest.name} has {n} bytes, expected {expected_size}")
    tmp.rename(dest)


def run(manifest_path: Path, dest_dir: Path) -> dict[str, object]:  # pragma: no cover - network
    manifest = json.loads(manifest_path.read_text())
    files = g.validate_manifest(manifest)
    dest_dir.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {"started": datetime.now(UTC).isoformat(timespec="seconds"), "files": {}}
    tatoeba: list[Path] = []
    for f in files:
        out = dest_dir / f["name"]
        out.parent.mkdir(parents=True, exist_ok=True)
        _download(f["url"], out, f.get("size"))
        if f.get("sha256"):
            g.verify_file(out, f["sha256"])
        if f["kind"] in ("tatoeba", "fallback-data"):
            tatoeba.append(out)
        record["files"][f["name"]] = {"sha256": g.sha256_file(out), "bytes": out.stat().st_size}  # type: ignore[index]
    record["tatoeba_recorded_at_first_download"] = g.record_tatoeba_digests(tatoeba)
    record["finished"] = datetime.now(UTC).isoformat(timespec="seconds")
    (dest_dir / "fetch_record.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    return record


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m studies.p10s2.fetch", description="Fetch and verify the approved downloads. Refuses without the explicit approval flag and a manifest.")
    p.add_argument(g.APPROVAL_FLAG, dest="approved", action="store_true")
    p.add_argument("--manifest", default=None)
    p.add_argument("--dest", default=None, help="a git-ignored directory named by source and download date")
    a = p.parse_args(argv)
    try:
        g.check_authorization(bool(a.approved), Path(a.manifest) if a.manifest else None)
        if not a.dest:
            raise g.FetchRefused("refused: --dest is required")
        run(Path(a.manifest), Path(a.dest))
    except g.FetchRefused as e:
        emit_plain(str(e), sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
