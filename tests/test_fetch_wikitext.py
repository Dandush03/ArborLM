"""Mocked-network safety checks for the pinned WikiText-2 acquisition."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pytest

import arborlm.fetch_wikitext as fetch


class FakeResponse:
    def __init__(self, body: bytes, url: str, *, content_length: bool = True) -> None:
        self._stream = io.BytesIO(body)
        self.headers = {"Content-Length": str(len(body))} if content_length else {}
        self._url = url

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def geturl(self) -> str:
        return self._url

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)


class BrokenResponse(FakeResponse):
    def __init__(self, body: bytes, url: str) -> None:
        super().__init__(body, url, content_length=False)
        self._calls = 0

    def read(self, size: int = -1) -> bytes:
        self._calls += 1
        if self._calls == 1:
            return self._stream.read(2)
        raise OSError("simulated connection reset")


def _small_fixture(monkeypatch: pytest.MonkeyPatch, *, cap: int = 64) -> dict[str, bytes]:
    contents = {
        "train-00000-of-00001.parquet": b"train bytes",
        "validation-00000-of-00001.parquet": b"valid bytes",
        "test-00000-of-00001.parquet": b"test bytes",
    }
    metadata = {
        name: {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
        for name, value in contents.items()
    }
    monkeypatch.setattr(fetch, "FILES", metadata)
    monkeypatch.setattr(
        fetch, "DOWNLOAD_FILES",
        ("train-00000-of-00001.parquet", "validation-00000-of-00001.parquet"),
    )
    monkeypatch.setattr(fetch, "MAX_PAYLOAD_BYTES", cap)
    contents["README.md"] = b"Pinned publisher card.\n"
    return contents


def _opener_for(contents: dict[str, bytes], seen: list[str]) -> Any:
    def opener(url: str, *, timeout: int) -> FakeResponse:
        assert timeout == fetch.TIMEOUT_SECONDS
        seen.append(url)
        if url == fetch.README_URL:
            name = "README.md"
        else:
            name = url.split("?")[0].rsplit("/", 1)[-1]
        return FakeResponse(contents[name], url)

    return opener


def test_success_is_pinned_atomic_and_does_not_request_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contents = _small_fixture(monkeypatch)
    requests: list[str] = []
    manifest = fetch.fetch_dataset(
        tmp_path / "wikitext2",
        command=["python", "-m", "arborlm.fetch_wikitext"],
        opener=_opener_for(contents, requests),
        now=lambda: "2026-11-12T12:00:00+00:00",
    )

    out = tmp_path / "wikitext2"
    assert (out / "train-00000-of-00001.parquet").read_bytes() == contents[
        "train-00000-of-00001.parquet"
    ]
    assert (out / "validation-00000-of-00001.parquet").read_bytes() == contents[
        "validation-00000-of-00001.parquet"
    ]
    assert (out / "README.upstream.md").read_bytes() == contents["README.md"]
    assert manifest["command_argv"] == ["python", "-m", "arborlm.fetch_wikitext"]
    assert manifest["acquired_utc"] == "2026-11-12T12:00:00+00:00"
    deferred = manifest["deferred_test"]
    assert isinstance(deferred, dict)
    assert deferred["acquired"] is False
    assert deferred["inspected"] is False
    assert deferred["sha256"] == hashlib.sha256(
        contents["test-00000-of-00001.parquet"]
    ).hexdigest()
    assert all("test-00000-of-00001.parquet" not in url for url in requests)

    # A successful rerun verifies existing files and records its command in
    # history without making any network request or replacing the manifest.
    original_manifest = (out / "manifest.json").read_bytes()

    def no_network(_url: str, *, timeout: int) -> FakeResponse:
        raise AssertionError("verified acquisition should not request the network")

    fetched_again = fetch.fetch_dataset(
        out, command=["rerun"], opener=no_network, now=lambda: "later"
    )
    assert fetched_again["acquired_utc"] == "2026-11-12T12:00:00+00:00"
    assert (out / "manifest.json").read_bytes() == original_manifest
    assert b'"command_argv":["rerun"]' in (out / "acquisition-history.jsonl").read_bytes()


@pytest.mark.parametrize("bad_train", [b"short", b"wrong bytes"])
def test_bad_pinned_checksum_or_size_is_not_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_train: bytes
) -> None:
    contents = _small_fixture(monkeypatch)
    bad = dict(contents)
    bad["train-00000-of-00001.parquet"] = bad_train
    requests: list[str] = []
    with pytest.raises(fetch.DownloadError, match="pinned file mismatch"):
        fetch.fetch_dataset(
            tmp_path / "wikitext2",
            command=["mock"],
            opener=_opener_for(bad, requests),
        )
    assert not (tmp_path / "wikitext2" / "train-00000-of-00001.parquet").exists()
    assert not (tmp_path / "wikitext2" / "manifest.json").exists()


def test_total_payload_cap_stops_before_exceeding_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contents = _small_fixture(monkeypatch, cap=15)
    requests: list[str] = []

    def oversized(url: str, *, timeout: int) -> FakeResponse:
        requests.append(url)
        body = contents["train-00000-of-00001.parquet"]
        return FakeResponse(body, url, content_length=False)

    with pytest.raises(fetch.DownloadError, match="remaining 10,000,000-byte cap"):
        fetch.fetch_dataset(tmp_path / "wikitext2", command=["mock"], opener=oversized)
    assert len(requests) == 1
    assert not (tmp_path / "wikitext2" / "train-00000-of-00001.parquet").exists()
    assert not (tmp_path / "wikitext2" / "manifest.json").exists()


def test_streaming_size_limit_stops_oversized_response_without_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contents = _small_fixture(monkeypatch)
    requests: list[str] = []

    def oversized(url: str, *, timeout: int) -> FakeResponse:
        requests.append(url)
        body = contents["train-00000-of-00001.parquet"] + b"extra"
        return FakeResponse(body, url, content_length=False)

    with pytest.raises(fetch.DownloadError, match="exceeds byte limit"):
        fetch.fetch_dataset(tmp_path / "wikitext2", command=["mock"], opener=oversized)
    assert len(requests) == 1
    assert not (tmp_path / "wikitext2" / "train-00000-of-00001.parquet").exists()


def test_failed_partial_transfer_is_removed_and_not_published(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contents = _small_fixture(monkeypatch)
    requests: list[str] = []

    def broken(url: str, *, timeout: int) -> BrokenResponse:
        requests.append(url)
        return BrokenResponse(contents["train-00000-of-00001.parquet"], url)

    with pytest.raises(fetch.DownloadError, match="simulated connection reset"):
        fetch.fetch_dataset(tmp_path / "wikitext2", command=["mock"], opener=broken)
    out = tmp_path / "wikitext2"
    assert len(requests) == 1
    assert list(out.iterdir()) == []


def test_invalid_existing_file_is_preserved_as_failure_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _small_fixture(monkeypatch)
    out = tmp_path / "wikitext2"
    out.mkdir()
    invalid = b"keep me as evidence"
    target = out / "train-00000-of-00001.parquet"
    target.write_bytes(invalid)

    def no_network(_url: str, *, timeout: int) -> FakeResponse:
        raise AssertionError("invalid local evidence must fail before networking")

    with pytest.raises(fetch.DownloadError, match="preserved as failure evidence"):
        fetch.fetch_dataset(out, command=["mock"], opener=no_network)
    assert target.read_bytes() == invalid


def test_existing_manifest_with_missing_corpus_file_is_rejected_and_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contents = _small_fixture(monkeypatch)
    out = tmp_path / "wikitext2"
    requests: list[str] = []
    fetch.fetch_dataset(out, command=["mock"], opener=_opener_for(contents, requests))
    manifest_bytes = (out / "manifest.json").read_bytes()
    missing = out / "validation-00000-of-00001.parquet"
    missing.unlink()

    def no_network(_url: str, *, timeout: int) -> FakeResponse:
        raise AssertionError("incomplete committed acquisition must fail before networking")

    with pytest.raises(fetch.DownloadError, match="missing corpus files"):
        fetch.fetch_dataset(out, command=["mock"], opener=no_network)
    assert not missing.exists()
    assert (out / "manifest.json").read_bytes() == manifest_bytes


def test_cli_appends_failed_attempt_status_and_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "wikitext2"

    def fail(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise fetch.DownloadError("mocked failure")

    monkeypatch.setattr(fetch, "fetch_dataset", fail)
    result = fetch.main(["--output-dir", str(out)])
    assert result == 1
    history = [
        json.loads(line)
        for line in (out / "acquisition-history.jsonl").read_text().splitlines()
    ]
    assert history[-1]["status"] == "failed"
    assert history[-1]["error_type"] == "DownloadError"
    assert history[-1]["error"] == "mocked failure"
    assert "mocked failure" in capsys.readouterr().err
