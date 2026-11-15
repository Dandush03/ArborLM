# ruff: noqa: E501
"""Fetch-and-verify of the approved downloads (ADR-0022 sections 14.1, 18 and the lead's rulings on the implementation audits). NOT RUN, and not called by any test with a real network.

It refuses to run unless the explicit ``--i-have-recorded-human-approval`` flag and a manifest path are given (``fetch_guard.check_authorization``), validates the manifest against the approved set and
the hash constants in reviewed code (``fetch_guard.validate_manifest``: a missing or wrong digest is refused), and only then makes plain HTTPS requests with the standard library: TLS certificate and
host verification on (a redirect to a non-HTTPS address is refused), no account, no token, no Hub client. Every downloaded file, small files included, is verified against its constant in reviewed code
(git-blob SHA-1 for the small files, SHA-256 for the large ones) and deleted on a mismatch. Everything else, the ledger rows written before and after each file, the refusal to overwrite, the session
cap and the destination rules, is in ``fetch_guard.fetch_session``, which takes the download function as an argument and is tested on synthetic files.

The destination is a fresh folder under the git-ignored ``data/`` (for example ``data/p10s2-downloads-<UTC date>/``); the seven Tatoeba files are fetched in one session. If the fallback is invoked,
the manifest lists the fallback rows (5 and 6) only and names a committed record of the human lead's decision; it goes to a different fresh folder, so the frozen primary files are untouched.

The package wheels of the data-generation step are not fetched here. They are resolved once with hashes (``uv pip compile --generate-hashes`` for Python 3.12 against torch 2.8.0), written to
``studies/p10s2/requirements-datagen.txt``, recorded in the download ledger with their total size, and installed with hashes required (``datagen`` refuses a requirements file whose pins carry no hash).

Status of this code: written, reviewed by self-check only, never executed against the network.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import fetch_guard as g
from .core import ROOT
from .output import emit_plain


def _download(url: str, dest: Path, limit: int) -> int:  # pragma: no cover - the only function that touches the network
    """Fetch ``url`` into ``dest`` with certificate verification on and HTTPS-only redirects; refuse past ``limit`` bytes (a cumulative limit computed by the session). Returns the bytes written."""
    import urllib.request

    class HttpsOnly(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
            if not newurl.lower().startswith("https://"):
                raise g.FetchRefused(f"refused: redirect to a non-HTTPS address {newurl!r}")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=g.make_ssl_context()), HttpsOnly())
    req = urllib.request.Request(url, headers={"User-Agent": "p10s2-fetch"})  # noqa: S310
    n = 0
    with opener.open(req, timeout=120) as r, dest.open("xb") as out:  # "xb": an existing file is never overwritten
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            n += len(chunk)
            if n > limit:
                raise g.FetchRefused(f"refused: {url} exceeded the byte limit of {limit}")
            out.write(chunk)
    return n


def run(manifest_path: Path, dest_dir: Path) -> dict[str, object]:  # pragma: no cover - network
    manifest = json.loads(manifest_path.read_text())
    return g.fetch_session(manifest, dest_dir, download=_download, ledger_path=ROOT / g.DOWNLOAD_LEDGER)


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m studies.p10s2.fetch", description="Fetch and verify the approved downloads. Refuses without the explicit approval flag and a manifest.")
    p.add_argument(g.APPROVAL_FLAG, dest="approved", action="store_true")
    p.add_argument("--manifest", default=None)
    p.add_argument("--dest", default=None, help="a fresh folder under the git-ignored data/ directory, named by source and download date")
    a = p.parse_args(argv)
    try:
        g.check_authorization(bool(a.approved), Path(a.manifest) if a.manifest else None)
        if not a.dest:
            raise g.FetchRefused("refused: --dest is required")
        if not g.is_git_ignored(Path(a.dest)):
            raise g.FetchRefused(f"refused: {a.dest} is not git-ignored")
        run(Path(a.manifest), Path(a.dest))
    except g.FetchRefused as e:
        emit_plain(str(e), sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
