# ruff: noqa: E501
"""P9 package I5, ``studies/p9/store.py``: the copy-on-write version store and its engineering
consistency test: a reader pinned to V1 while V2 publishes (threads and a second process), a crash before
the pointer rename, a deliberately mixed manifest, replay equivalence with a tampered V2, rollback to V1
byte for byte, and the command line. This is an engineering test of a local directory, not a learning
claim and not storage I/O evidence.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402
import torch  # noqa: E402

from arborlm.io import canonical_json  # noqa: E402
from studies.p9 import store  # noqa: E402
from studies.p9.store import (  # noqa: E402
    MixedVersionError,
    SimulatedCrash,
    StaleParent,
    StoreCorruption,
    StoreError,
    VersionManifest,
    VersionStore,
    tensors_identical,
)

SEED = 179002  # test namespace


def make_versions(slots: int = 256) -> tuple[dict[str, Any], dict[str, Any]]:
    g = torch.Generator().manual_seed(SEED)
    v1 = {
        "keys": torch.randn(slots, 4, generator=g),
        "values": torch.randn(slots, 8, generator=g),
        "wq": torch.randn(4, 8, generator=g),
        "gate": torch.tensor(-2.0),
    }
    v2 = {k: t.clone() for k, t in v1.items()}
    for row in (3, 100, 101, 250):
        v2["keys"][row] += 1.0
        v2["values"][row] -= 1.0
    v2["gate"] = torch.tensor(-1.5)
    return v1, v2


def fresh(
    tmp_path: Path, chunk_rows: int = 16
) -> tuple[VersionStore, dict[str, Any], dict[str, Any]]:
    v1, v2 = make_versions()
    return VersionStore(tmp_path / "store", chunk_rows=chunk_rows), v1, v2


def publish_both(s: VersionStore, v1: dict[str, Any], v2: dict[str, Any]) -> None:
    s.stage("V1", v1, None)
    s.publish("V1")
    s.stage("V2", v2, "V1")
    s.publish("V2")


# --- basics and copy-on-write ------------------------------------------------------------------------
def test_roundtrip_of_every_supported_dtype_shape(tmp_path: Path) -> None:
    s = VersionStore(tmp_path, chunk_rows=3)
    tensors = {
        "f32": torch.randn(7, 5),
        "f64": torch.randn(4, dtype=torch.float64),
        "i64": torch.arange(20, dtype=torch.int64).reshape(10, 2),
        "i32": torch.arange(5, dtype=torch.int32),
        "u8": torch.arange(9, dtype=torch.uint8).reshape(3, 3),
        "bool": torch.tensor([[True, False], [False, True], [True, True], [False, False]]),
        "scalar": torch.tensor(1.25),
        "empty": torch.empty(0, 4),
        "nan": torch.tensor([float("nan"), 1.0, float("inf")]),
    }
    s.stage("V1", tensors, None)
    s.publish("V1")
    assert tensors_identical(s.pin().read_all(), tensors)
    with pytest.raises(ValueError):
        s.stage("bad", {"x": torch.zeros(2, dtype=torch.float16)}, None)
    with pytest.raises(ValueError):
        s.stage("../escape", tensors, None)
    with pytest.raises(FileExistsError):
        s.stage("V1", tensors, None)


def test_a_new_version_writes_only_the_chunks_that_changed(tmp_path: Path) -> None:
    s, v1, v2 = fresh(tmp_path)
    s.stage("V1", v1, None)
    first = dict(s.last_stage)
    s.stage("V2", v2, "V1")
    second = dict(s.last_stage)
    # keys and values: 256 rows in chunks of 16; rows 3, 100/101, 250 lie in three chunks
    assert first["new_blobs"] > second["new_blobs"]
    assert second["reused_blobs"] >= 2 * (16 - 3) + 1  # unchanged key and value chunks, wq
    manifest_1, manifest_2 = s.manifest("V1"), s.manifest("V2")
    assert (
        manifest_1.entries["wq"] == manifest_2.entries["wq"]
    )  # an unchanged tensor shares its index blob
    assert manifest_1.entries["keys"] != manifest_2.entries["keys"]
    keys_1 = s._get_json_blob(manifest_1.entries["keys"])["chunks"]
    keys_2 = s._get_json_blob(manifest_2.entries["keys"])["chunks"]
    assert sum(a != b for a, b in zip(keys_1, keys_2, strict=True)) == 3
    s.publish("V1")
    s.publish("V2")
    assert s.verify()["ok"]


def test_manifest_stub_construction_still_works() -> None:
    m = VersionManifest("V1", {"keys": "a" * 64}, None)
    assert m.state_digest == "" and m.update is None and m.parent is None


# --- a reader pinned to V1 ---------------------------------------------------------------------------------------
def test_pinned_reader_sees_only_v1_while_v2_stages_and_publishes_in_threads(
    tmp_path: Path,
) -> None:
    s, v1, v2 = fresh(tmp_path)
    s.stage("V1", v1, None)
    s.publish("V1")
    reader = s.pin()
    assert reader.name == "V1" and reader.published
    s.stage("V2", v2, "V1")
    assert s.current() == "V1" and s.pin().name == "V1"  # staged is not published
    digest_1, digest_2 = store.state_digest_of(v1), store.state_digest_of(v2)
    stop, published = threading.Event(), threading.Event()
    seen = {"pinned": 0, "pinned_bad": 0, "fresh_v1": 0, "fresh_v2": 0, "fresh_bad": 0, "after": 0}
    started = threading.Event()

    def pinned() -> None:
        while not stop.is_set():
            ok = tensors_identical(reader.read_all(), v1)
            seen["pinned"] += 1
            seen["pinned_bad"] += 0 if ok else 1
            seen["after"] += 1 if published.is_set() else 0
            started.set()

    def fresh_pins() -> None:
        while not stop.is_set():
            digest = store.state_digest_of(s.pin().read_all())
            if digest == digest_1:
                seen["fresh_v1"] += 1
            elif digest == digest_2:
                seen["fresh_v2"] += 1
            else:
                seen["fresh_bad"] += 1

    threads = [threading.Thread(target=pinned), threading.Thread(target=fresh_pins)]
    for t in threads:
        t.start()
    assert started.wait(timeout=30)
    s.publish("V2")
    published.set()
    for _ in range(2000):
        if seen["after"] >= 3:
            break
        threading.Event().wait(0.01)
    stop.set()
    for t in threads:
        t.join(timeout=60)
    assert seen["pinned"] >= 1 and seen["after"] >= 1
    assert seen["pinned_bad"] == 0 and seen["fresh_bad"] == 0  # never a mix, never a torn read
    assert s.current() == "V2" and reader.name == "V1"
    assert tensors_identical(reader.read_all(), v1) and tensors_identical(s.pin().read_all(), v2)


def test_reader_reads_index_before_and_values_after_publication_without_mixing(
    tmp_path: Path,
) -> None:
    s, v1, v2 = fresh(tmp_path)
    s.stage("V1", v1, None)
    s.publish("V1")
    reader = s.pin()
    keys = reader.read("keys")  # the index part, read first
    s.stage("V2", v2, "V1")
    s.publish("V2")
    values = reader.read("values")  # the value part, read after V2 is current
    assert torch.equal(keys, v1["keys"]) and torch.equal(values, v1["values"])
    assert not torch.equal(values, v2["values"])
    with pytest.raises(KeyError):
        reader.read("nope")


def test_a_second_process_pinned_to_v1_is_not_moved_by_a_publication(tmp_path: Path) -> None:
    s, v1, v2 = fresh(tmp_path)
    s.stage("V1", v1, None)
    s.publish("V1")
    script = (
        "import sys, json\n"
        f"sys.path.insert(0, {str(REPO)!r})\n"
        "from pathlib import Path\n"
        "from studies.p9.store import VersionStore, state_digest_of\n"
        f"s = VersionStore(Path({str(s.root)!r}), chunk_rows=16)\n"
        "r = s.pin()\n"
        "keys = r.read('keys')\n"
        "print('pinned', r.name, flush=True)\n"
        "sys.stdin.readline()\n"
        "values = r.read('values')\n"
        "everything = r.read_all()\n"
        "print(json.dumps({'name': r.name, 'digest': state_digest_of(everything), 'current_now': s.current()}), flush=True)\n"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        cwd=REPO,
    )
    assert child.stdin is not None and child.stdout is not None
    assert child.stdout.readline().strip() == "pinned V1"
    s.stage("V2", v2, "V1")
    s.publish("V2")
    child.stdin.write("go\n")
    child.stdin.flush()
    result = json.loads(child.stdout.readline())
    assert child.wait(timeout=60) == 0
    assert result == {"name": "V1", "digest": store.state_digest_of(v1), "current_now": "V2"}


# --- crash before the rename -----------------------------------------------------------------------------------------
class CrashBeforeRename(VersionStore):
    def _before_rename(self) -> None:
        raise SimulatedCrash("crash")


def test_crash_before_the_pointer_rename_leaves_v1_current(tmp_path: Path) -> None:
    v1, v2 = make_versions()
    root = tmp_path / "store"
    ok = VersionStore(root, chunk_rows=16)
    ok.stage("V1", v1, None)
    ok.publish("V1")
    pointer_before = (root / "CURRENT").read_bytes()
    crashing = CrashBeforeRename(root, chunk_rows=16)
    crashing.stage("V2", v2, "V1")
    with pytest.raises(SimulatedCrash):
        crashing.publish("V2")
    after = VersionStore(root, chunk_rows=16)
    assert (root / "CURRENT").read_bytes() == pointer_before  # not touched
    assert after.current() == "V1" and after.published() == ["V1"]
    assert tensors_identical(after.pin().read_all(), v1)
    report = after.verify()
    assert (
        report["ok"]
        and report["staged_unpublished"] == ["V2"]
        and len(report["leftover_temp"]) == 1
    )
    assert after.recover() == report["leftover_temp"] and not after.verify()["leftover_temp"]
    after.publish("V2")  # the staged version can still be published afterwards
    assert after.current() == "V2" and tensors_identical(after.pin().read_all(), v2)


# --- mixed versions ------------------------------------------------------------------------------------------------------
def forge_mixed(s: VersionStore) -> str:
    """A manifest taking V2's keys and V1's values, under V2's state digest."""
    m1, m2 = s.manifest("V1"), s.manifest("V2")
    entries = dict(m2.entries)
    entries["values"] = m1.entries["values"]
    forged = VersionManifest("Vmixed", entries, "V2", m2.state_digest, None, m2.chunk_rows)
    s._manifest_path("Vmixed").write_bytes(canonical_json(forged.to_json()))
    return "Vmixed"


def test_a_deliberately_mixed_manifest_is_detected_and_refused(tmp_path: Path) -> None:
    s, v1, v2 = fresh(tmp_path)
    publish_both(s, v1, v2)
    name = forge_mixed(s)
    report = s.verify_version(name)
    assert not report["ok"] and "mixed or edited" in report["problems"][0]
    assert not s.verify()["ok"]
    with pytest.raises(MixedVersionError):
        s.pin(name).read_all()
    with pytest.raises(MixedVersionError):
        s.publish(name)
    assert s.current() == "V2" and tensors_identical(s.pin().read_all(), v2)
    # even each blob of it is individually valid: only the combination is wrong
    assert torch.equal(s.pin(name).read("keys"), v2["keys"]) and torch.equal(
        s.pin(name).read("values"), v1["values"]
    )


def test_a_manifest_edited_after_publication_is_refused_by_pin_and_verify(tmp_path: Path) -> None:
    s, v1, v2 = fresh(tmp_path)
    publish_both(s, v1, v2)
    path = s._manifest_path("V1")
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(StoreCorruption, match="after publication"):
        s.pin("V1")
    assert not s.verify()["ok"]
    with pytest.raises(StoreCorruption):
        s.rollback("V1")


def test_orphan_manifest_and_corrupt_pointer_are_reported(tmp_path: Path) -> None:
    s, v1, v2 = fresh(tmp_path)
    publish_both(s, v1, v2)
    m2 = s.manifest("V2")
    orphan = VersionManifest(
        "Vorphan", dict(m2.entries), "ghost", m2.state_digest, None, m2.chunk_rows
    )
    s._manifest_path("Vorphan").write_bytes(canonical_json(orphan.to_json()))
    report = s.verify()
    assert not report["ok"] and any("orphan manifest" in p for p in report["problems"])
    (s.root / "CURRENT").write_bytes(b"{not json")
    with pytest.raises(StoreCorruption):
        s.current()


# --- replay equivalence -----------------------------------------------------------------------------------------------------
def test_replay_from_v1_reproduces_v2_byte_for_byte(tmp_path: Path) -> None:
    s, v1, v2 = fresh(tmp_path)
    publish_both(s, v1, v2)
    check = s.replay_check("V2")
    assert check["passed"] and check["problems"] == []
    assert check["changed_rows"] == {"keys": 4, "values": 4, "gate": 1}
    assert tensors_identical(s.replay("V2"), v2)
    assert tensors_identical(s.replay("V2"), s.pin("V2").read_all())
    with pytest.raises(StoreError, match="no recorded update"):
        s.replay("V1")


def test_replay_handles_added_removed_and_reshaped_entries(tmp_path: Path) -> None:
    s, v1, _ = fresh(tmp_path)
    s.stage("V1", v1, None)
    changed = {
        "keys": torch.cat([v1["keys"], torch.ones(5, 4)]),
        "extra": torch.arange(6.0),
        "gate": v1["gate"].clone(),
        "values": v1["values"].clone(),
    }
    s.stage("V2", changed, "V1")  # wq removed, extra added, keys grown
    assert s.replay_check("V2")["passed"]
    assert tensors_identical(s.replay("V2"), changed)


def test_a_tampered_v2_blob_fails_replay_and_verification(tmp_path: Path) -> None:
    s, v1, v2 = fresh(tmp_path)
    publish_both(s, v1, v2)
    m1, m2 = s.manifest("V1"), s.manifest("V2")
    old = set(s._get_json_blob(m1.entries["keys"])["chunks"])
    fresh_chunk = next(c for c in s._get_json_blob(m2.entries["keys"])["chunks"] if c not in old)
    path = s._blob_path(fresh_chunk)
    data = bytearray(path.read_bytes())
    data[0] ^= 0x01  # one bit
    path.write_bytes(bytes(data))
    assert not s.replay_check("V2")["passed"]
    assert not s.verify()["ok"]
    with pytest.raises(StoreCorruption):
        s.pin("V2").read_all()
    assert tensors_identical(s.pin("V1").read_all(), v1)  # V1 shares none of the damaged blob


def test_a_v2_that_is_self_consistent_but_not_the_recorded_update_fails_replay(
    tmp_path: Path,
) -> None:
    s, v1, v2 = fresh(tmp_path)
    s.stage("V1", v1, None)
    s.publish("V1")
    s.stage("V2", v2, "V1")
    other = {k: t.clone() for k, t in v2.items()}
    other["values"][7] += 3.0
    s.stage("Vother", other, "V1")
    m2, mo = s.manifest("V2"), s.manifest("Vother")
    # V2's manifest now points at the other content, with that content's digest, keeping V2's update record
    forged = VersionManifest(
        "V2", dict(mo.entries), "V1", mo.state_digest, m2.update, m2.chunk_rows
    )
    s._manifest_path("V2").write_bytes(canonical_json(forged.to_json()))
    assert s.verify_version("V2")["ok"]  # the content is internally consistent
    assert not s.replay_check("V2")["passed"]  # but it is not what the recorded update produces


# --- rollback ----------------------------------------------------------------------------------------------------------------
def test_rollback_restores_v1_byte_identically_and_keeps_history(tmp_path: Path) -> None:
    s, v1, v2 = fresh(tmp_path)
    publish_both(s, v1, v2)
    assert s.current() == "V2"
    s.rollback("V1")
    assert s.current() == "V1"
    restored = s.pin().read_all()
    assert tensors_identical(restored, v1)
    assert store.state_digest_of(restored) == s.manifest("V1").state_digest
    assert [h["action"] for h in s.history()] == ["publish", "publish", "rollback"]
    assert s.published() == ["V1", "V2"]
    assert tensors_identical(s.pin("V2").read_all(), v2)  # V2 is still there and verifiable
    s.publish("V2")  # roll forward: V2's parent V1 is current again
    assert s.current() == "V2"
    with pytest.raises(StoreError, match="never published"):
        s.rollback("nope")
    s.stage("V3", {**v2, "gate": torch.tensor(0.0)}, "V2")
    s.rollback("V1")
    with pytest.raises(StaleParent):
        s.publish("V3")  # derived from V2, but V1 is current


def test_publish_rules(tmp_path: Path) -> None:
    s, v1, v2 = fresh(tmp_path)
    s.stage("V1", v1, None)
    s.stage("V2", v2, "V1")
    with pytest.raises(StaleParent):
        s.publish("V2")  # nothing published yet, V2 has a parent
    with pytest.raises(StoreError):
        s.pin()
    with pytest.raises(StoreError, match="not staged"):
        s.stage("V9", v2, "missing")
    s.publish("V1")
    s.stage("Vroot", v2, None)
    with pytest.raises(StaleParent):
        s.publish("Vroot")  # a second root while something is current


# --- the consistency test and the command line ----------------------------------------------------------------------------
def test_consistency_test_passes_and_says_what_it_is(tmp_path: Path) -> None:
    v1, v2 = store.synthetic_versions(SEED, slots=512)
    result = store.consistency_test(tmp_path, v1, v2)
    assert result["passed"] is True and result["errors"] == []
    assert result["engineering_test_only"] is True
    assert (
        "no learning claim" in result["statement"]
        and "not storage I/O evidence" in result["statement"]
    )
    assert all(result["checks"].values()) and len(result["checks"]) >= 15
    assert all(result["negative_controls"].values()) and set(result["negative_controls"]) == {
        "crash_before_rename_keeps_v1_current",
        "mixed_manifest_detected_and_refused",
        "tampered_v2_blob_fails",
        "tampered_update_record_fails_replay",
    }
    assert result["concurrency"]["pinned_reader_mismatches"] == 0
    assert result["concurrency"]["pinned_reader_ran_after_publish"] is True
    assert (
        result["copy_on_write"]["v2_new_bytes"]
        < 2 * result["copy_on_write"]["v2_full_tensor_bytes"]
    )
    assert result["copy_on_write"]["v2_reused_blobs"] > 0
    with pytest.raises(FileExistsError):
        store.consistency_test(
            tmp_path, v1, v2
        )  # failed and finished attempts are kept, not overwritten


def test_consistency_test_reports_a_failure_instead_of_passing(tmp_path: Path) -> None:
    v1, _ = store.synthetic_versions(SEED, slots=64)
    result = store.consistency_test(
        tmp_path, v1, {k: t.clone() for k, t in v1.items()}
    )  # V2 identical to V1
    assert (
        result["passed"] is False
    )  # no changed row: the tamper controls have nothing to tamper with
    assert result["engineering_test_only"] is True


def run_cli(out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "studies.p9.store", "consistency", "--out", str(out)],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_cli_consistency_writes_json_and_is_deterministic(tmp_path: Path) -> None:
    first = run_cli(tmp_path / "one")
    assert first.returncode == 0, first.stderr
    printed = json.loads(first.stdout)
    on_disk = json.loads((tmp_path / "one" / "consistency.json").read_text())
    assert (
        printed == on_disk
        and on_disk["passed"] is True
        and on_disk["engineering_test_only"] is True
    )
    assert on_disk["source"] == {"kind": "synthetic", "seed": store.SYNTHETIC_SEED}
    second = run_cli(tmp_path / "two")
    assert second.returncode == 0
    assert json.loads(second.stdout) == printed  # byte-for-byte reproducible apart from nothing
    again = run_cli(tmp_path / "one")  # a used output directory is refused, not overwritten
    assert again.returncode != 0 and "FileExistsError" in again.stderr
    bad = subprocess.run(
        [
            sys.executable,
            "-m",
            "studies.p9.store",
            "consistency",
            "--out",
            str(tmp_path / "x"),
            "--v1",
            "a",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 2


def test_cli_consistency_on_snapshot_files(tmp_path: Path) -> None:
    v1, v2 = make_versions()
    for name, state in (("s1", v1), ("s2", v2)):
        folder = tmp_path / name
        folder.mkdir()
        torch.save(
            {
                "update": 1,
                "model": {f"addition.{k}": t for k, t in state.items()}
                | {"backbone.x": torch.zeros(2)},
            },
            folder / "model.pt",
        )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "studies.p9.store",
            "consistency",
            "--out",
            str(tmp_path / "out"),
            "--v1",
            str(tmp_path / "s1"),
            "--v2",
            str(tmp_path / "s2"),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert record["passed"] and record["source"]["kind"] == "snapshots"
    assert sorted(record["inputs"]["entries"]) == [
        "gate",
        "keys",
        "values",
        "wq",
    ]  # the backbone is not stored
