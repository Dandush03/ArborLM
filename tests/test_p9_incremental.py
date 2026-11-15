# ruff: noqa: E501
"""P9 package I5, ``studies/p9/incremental.py``: Lane D phase A and phase B jobs, fresh optimizer at V1,
the memory-only freeze, replay composition, the joint bound, the measurements of ADR 8.5 and a tiny
end-to-end A -> B run of every arm.

Tiny sizes (128 facts per set, 4,096 slots), a random frozen backbone, test seeds (the rehearsal draw
seeds are all >= 179001) and no registered seed. No accuracy of a compared arm is recorded or judged:
the end-to-end run only asserts that every number is finite.

Self-check only: not independent review, not Astra validation, not human approval.
"""

import dataclasses
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402
from test_p9_model_support import TEST_SEED, backbone  # noqa: E402

from studies.p9 import core, data, incremental, train  # noqa: E402
from studies.p9.model import build_model, trainable_groups  # noqa: E402

make_backbone = backbone

SIZES = data.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128)
SEEDS = core.rehearsal_seeds(7)
EXPOSURE = 32
PHASE_UPDATES = 128 * EXPOSURE // 128  # 32 updates for one phase of 128 facts
ADDITION_ARMS = (
    ("flat", "sequential"),
    ("flat", "memory_only"),
    ("learned_tree", "sequential"),
    ("flat", "replay"),
    ("dense", "sequential"),
    ("dense", "replay"),
)


def _corpus() -> bytes:
    g = torch.Generator().manual_seed(11)
    return bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())


def lane_cell(
    arch: str, arm: str, seed: int = 1701, facts: int = 128, slots: int = 4096
) -> core.Cell:
    """A registered D1/D2 cell shrunk to tiny sizes (its label, dependencies and arm are unchanged)."""
    block = "D1" if arm == "phaseA" else "D2"
    base = next(
        c
        for c in core.cells_of_block(block)
        if c.arch == arch and c.lane_d_arm == arm and c.seed == seed
    )
    return dataclasses.replace(base, slots=slots, facts=2 * facts if arm == "joint" else facts)


@pytest.fixture(scope="module")
def study() -> data.StudyData:
    return data.build_study_data(SEEDS, _corpus(), sizes=SIZES)


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("lane_d")


@pytest.fixture(scope="module")
def phase_a(study: data.StudyData, run_dir: Path) -> dict[str, dict[str, Any]]:
    """Phase A of flat, learned tree and dense once: ``arch -> {cell, snapshot, executed}``."""
    out: dict[str, dict[str, Any]] = {}
    for arch in ("flat", "learned_tree", "dense"):
        cell = lane_cell(arch, "phaseA")
        job = incremental.phase_a_job(cell, study, backbone(), run_dir, EXPOSURE, "calibration")
        executed = train.run_job(job)
        out[arch] = {
            "cell": cell,
            "snapshot": core.snapshot_dir(run_dir, cell.label, PHASE_UPDATES),
            "executed": executed,
        }
    return out


def _b_cell(arch: str, arm: str) -> core.Cell:
    return lane_cell(arch, arm)


@pytest.fixture(scope="module")
def phase_b(
    study: data.StudyData, run_dir: Path, phase_a: dict[str, dict[str, Any]]
) -> dict[tuple[str, str], dict[str, Any]]:
    """Every phase-B arm run to completion: ``(arch, arm) -> {cell, job, executed}``."""
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for arch, arm in ADDITION_ARMS:
        cell = _b_cell(arch, arm)
        job = incremental.phase_b_job(
            cell, study, backbone(), run_dir, phase_a[arch]["snapshot"], EXPOSURE, "calibration"
        )
        out[(arch, arm)] = {"cell": cell, "job": job, "executed": train.run_job(job)}
    joint = lane_cell("flat", "joint")
    job = incremental.phase_b_job(joint, study, backbone(), run_dir, None, EXPOSURE, "calibration")
    out[("flat", "joint")] = {"cell": joint, "job": job, "executed": train.run_job(job)}
    return out


def v1_state(snapshot: Path) -> dict[str, torch.Tensor]:
    payload = torch.load(snapshot / "model.pt", weights_only=True, map_location="cpu")
    return dict(payload["model"])


def final_state(executed: train.Executed) -> dict[str, torch.Tensor]:
    return {k: v.detach().clone() for k, v in executed.model.state_dict().items()}


# --- data: sets A and B ----------------------------------------------------------------------------------
def test_sets_a_and_b_are_disjoint_with_their_own_clusters(study: data.StudyData) -> None:
    n = study.lane_d_set_size
    assert n == 128 and study.lane_d.trained == 256
    codes = data.encode_identifiers(study.lane_d.ident)
    assert len(set(codes[:n].tolist()) & set(codes[n:].tolist())) == 0
    assert len(set(codes.tolist())) == 2 * n
    # every cluster of 16 facts lies inside one set; A's clusters are 0..7, B's 8..15
    cluster = study.lane_d.cluster
    assert set(cluster[:n].tolist()) == set(range(8)) and set(cluster[n:].tolist()) == set(
        range(8, 16)
    )
    for c in range(16):
        members = (cluster == c).nonzero().reshape(-1)
        assert members.numel() == core.CLUSTER_SIZE
        assert bool((members < n).all()) or bool((members >= n).all())
    # the main world's identifiers are not reused
    assert not bool(torch.isin(codes, data.encode_identifiers(study.facts.ident)).any())
    # panel streams hold one set each
    for panel in ("a", "b"):
        assert bool((study.streams[f"lane_d_{panel}_A"].fact_ids < n).all())
        assert bool((study.streams[f"lane_d_{panel}_B"].fact_ids >= n).all())


# --- phase A -------------------------------------------------------------------------------------------------
def test_phase_a_job_trains_set_a_and_stores_v1_with_optimizer_state(
    phase_a: dict[str, dict[str, Any]], study: data.StudyData
) -> None:
    for arch, item in phase_a.items():
        cell, snapshot = item["cell"], item["snapshot"]
        assert cell.lane_d_arm == "phaseA" and cell.block == "D1"
        for name in ("model.pt", "optimizer.pt", "movement.pt", "snapshot.json"):
            assert (snapshot / name).is_file(), (arch, name)
        record = item["executed"].record
        assert record["status"] == "completed" and record["run_updates"] == PHASE_UPDATES
        assert record["snapshots"] == [PHASE_UPDATES // 2, PHASE_UPDATES]
        assert record["examples"] == 16 * PHASE_UPDATES
        state = torch.load(snapshot / "optimizer.pt", weights_only=True, map_location="cpu")
        moments = [
            v
            for o in state["optimizers"]
            for s in o["state"].values()
            for k, v in s.items()
            if k == "exp_avg"
        ]
        assert moments and any(float(m.abs().max()) > 0 for m in moments)
    stream = data.training_stream_for(study, phase_a["flat"]["cell"])
    assert bool((stream.facts < study.lane_d_set_size).all())


def test_phase_a_and_b_jobs_refuse_wrong_arms(study: data.StudyData, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="phase A"):
        incremental.phase_a_job(
            lane_cell("flat", "sequential"), study, backbone(), tmp_path, EXPOSURE, "calibration"
        )
    with pytest.raises(ValueError, match="phase B"):
        incremental.phase_b_job(
            lane_cell("flat", "phaseA"), study, backbone(), tmp_path, None, EXPOSURE, "calibration"
        )
    tree_memory_only = dataclasses.replace(
        lane_cell("learned_tree", "sequential"), lane_d_arm="memory_only"
    )
    with pytest.raises(ValueError, match="flat memory only"):
        incremental.phase_b_job(
            tree_memory_only, study, backbone(), tmp_path, tmp_path, EXPOSURE, "calibration"
        )


def test_v1_snapshot_path_is_the_d1_snapshot_at_u(tmp_path: Path) -> None:
    d1 = next(c for c in core.cells_of_block("D1") if c.arch == "flat" and c.seed == 1701)
    path = incremental.v1_snapshot_path(tmp_path, d1.label, 32)
    assert path == core.snapshot_dir(tmp_path, d1.label, 1024)
    assert path.name == "u0001024"
    d2 = next(
        c
        for c in core.cells_of_block("D2")
        if c.lane_d_arm == "sequential" and c.arch == "flat" and c.seed == 1701
    )
    assert d2.depends_on == (d1.label,)
    with pytest.raises(ValueError):
        incremental.v1_snapshot_path(tmp_path, d2.label, 32)


# --- dependency -----------------------------------------------------------------------------------------------
def test_phase_b_refuses_without_its_d1_snapshot_and_names_it(
    study: data.StudyData, tmp_path: Path
) -> None:
    cell = lane_cell("flat", "sequential")
    dependency = cell.depends_on[0]
    missing = core.snapshot_dir(tmp_path, dependency, PHASE_UPDATES)
    with pytest.raises(incremental.MissingDependency) as info:
        incremental.phase_b_job(cell, study, backbone(), tmp_path, missing, EXPOSURE, "calibration")
    assert (
        dependency in str(info.value)
        and str(missing) in str(info.value)
        and cell.label in str(info.value)
    )
    with pytest.raises(incremental.MissingDependency, match="D1 dependency"):
        incremental.phase_b_job(cell, study, backbone(), tmp_path, None, EXPOSURE, "calibration")
    # the joint bound has no dependency, and must not be given a V1
    joint = lane_cell("flat", "joint")
    assert joint.depends_on == ()
    with pytest.raises(ValueError, match="no V1"):
        incremental.phase_b_job(
            joint, study, backbone(), tmp_path, missing, EXPOSURE, "calibration"
        )


def test_phase_b_refuses_a_snapshot_that_is_not_v1(
    study: data.StudyData, phase_a: dict[str, dict[str, Any]], run_dir: Path
) -> None:
    cell = lane_cell("flat", "sequential")
    half = core.snapshot_dir(run_dir, cell.depends_on[0], PHASE_UPDATES // 2)
    assert (half / "model.pt").is_file()
    with pytest.raises(ValueError, match="snapshot at U"):
        incremental.phase_b_job(cell, study, backbone(), run_dir, half, EXPOSURE, "calibration")
    other = lane_cell("dense", "sequential")
    with pytest.raises(ValueError, match="depends on"):  # a snapshot of another D1 cell
        incremental.phase_b_job(
            cell, study, backbone(), run_dir, phase_a["dense"]["snapshot"], EXPOSURE, "calibration"
        )
    assert other.depends_on != cell.depends_on


# --- phase B starts from V1 exactly, with a fresh optimizer ----------------------------------------------------------
@pytest.mark.parametrize(("arch", "arm"), ADDITION_ARMS)
def test_phase_b_starts_from_v1_parameters_with_fresh_optimizer_state(
    arch: str,
    arm: str,
    study: data.StudyData,
    phase_a: dict[str, dict[str, Any]],
    run_dir: Path,
    tmp_path: Path,
) -> None:
    cell = _b_cell(arch, arm)
    v1 = phase_a[arch]["snapshot"]
    job = incremental.phase_b_job(cell, study, backbone(), tmp_path, v1, EXPOSURE, "calibration")
    assert job.restore_optimizer is False and job.init_snapshot == v1
    job.max_updates = 0
    zero = train.run_job(job)
    saved = v1_state(v1)
    for name, tensor in zero.model.state_dict().items():
        assert torch.equal(tensor, saved[name]), name
    assert zero.trainer.update == 0
    assert all(
        len(o.state) == 0 for o in zero.optimizers
    )  # no moment, no step counter carried over
    # V1's own optimizer file does hold history, so a restore would have carried it
    state = torch.load(v1 / "optimizer.pt", weights_only=True, map_location="cpu")
    assert any(
        float(s["step"]) == PHASE_UPDATES for o in state["optimizers"] for s in o["state"].values()
    )
    # one update later the optimizer's step counters count phase-B updates only, from zero moments
    job_one = incremental.phase_b_job(
        cell, study, backbone(), tmp_path / "one", v1, EXPOSURE, "calibration"
    )
    job_one.max_updates = 1
    one = train.run_job(job_one)
    steps = [float(s["step"]) for o in one.optimizers for s in o.state.values()]
    assert steps and all(s == 1.0 for s in steps)
    first_moments = [s["exp_avg"] for o in one.optimizers for s in o.state.values()]
    assert all(bool(torch.isfinite(m).all()) for m in first_moments)


# --- the memory-only freeze and the other arms' trainable sets ------------------------------------------------------------
def test_memory_only_freezes_projections_and_gate_and_trains_keys_and_values(
    phase_a: dict[str, dict[str, Any]], phase_b: dict[tuple[str, str], dict[str, Any]]
) -> None:
    item = phase_b[("flat", "memory_only")]
    before = v1_state(phase_a["flat"]["snapshot"])
    after = final_state(item["executed"])
    for frozen in ("addition.wq", "addition.wo", "addition.gate"):
        assert torch.equal(before[frozen], after[frozen]), frozen  # parameter bytes unchanged
    assert not torch.equal(before["addition.keys"], after["addition.keys"])
    assert not torch.equal(before["addition.values"], after["addition.values"])
    assert item["executed"].record["trainable_parameters"] == 4096 * 16 + 4096 * 32
    groups = {
        g: [n for n, _ in ps] for g, ps in trainable_groups(item["executed"].model).items() if ps
    }
    assert groups == {"keys": ["addition.keys"], "values": ["addition.values"]}
    assert item["job"].trainable_groups == ("keys", "values")
    # the sequential arm trains the projections as well
    seq = final_state(phase_b[("flat", "sequential")]["executed"])
    assert not torch.equal(before["addition.wq"], seq["addition.wq"])
    assert phase_b[("flat", "sequential")]["executed"].record["trainable_parameters"] == 198145


def test_tree_sequential_trains_the_router_and_dense_trains_its_weights(
    phase_a: dict[str, dict[str, Any]], phase_b: dict[tuple[str, str], dict[str, Any]]
) -> None:
    tree = phase_b[("learned_tree", "sequential")]["executed"]
    groups = {g: len(ps) for g, ps in trainable_groups(tree.model).items()}
    assert (
        groups["router"] == 1
        and groups["keys"] == 1
        and groups["values"] == 1
        and groups["projections"] == 3
    )
    assert tree.record["trainable_parameters"] == core.memory_parameters("learned_tree", 4096)
    before = v1_state(phase_a["learned_tree"]["snapshot"])
    after = final_state(tree)
    assert not torch.equal(before["addition.router"], after["addition.router"])
    dense = phase_b[("dense", "sequential")]["executed"]
    dense_before = v1_state(phase_a["dense"]["snapshot"])
    dense_after = final_state(dense)
    assert not torch.equal(dense_before["addition.w1"], dense_after["addition.w1"])
    assert dense.record["trainable_parameters"] == core.memory_parameters("flat", 4096)


# --- replay -------------------------------------------------------------------------------------------------------------------
def test_replay_batches_have_the_stated_composition_and_update_count(
    study: data.StudyData, phase_b: dict[tuple[str, str], dict[str, Any]]
) -> None:
    n = study.lane_d_set_size
    seq_cell = _b_cell("flat", "sequential")
    seq_stream = data.training_stream_for(study, seq_cell)
    for arch in ("flat", "dense"):
        replay = phase_b[(arch, "replay")]
        cell = replay["cell"]
        stream = replay["job"].stream
        assert core.contexts_per_update(cell) == 32 and core.contexts_per_update(seq_cell) == 16
        for update in (1, 7, PHASE_UPDATES):
            batch = stream.batch(update)
            assert batch.tokens.shape == (16, 64) and batch.replay_tokens.shape == (16, 64)
            assert bool((batch.fact_ids >= n).all()) and bool(
                (batch.fact_ids < 2 * n).all()
            )  # B contexts: B only
            assert bool((batch.replay_fact_ids < n).all())  # replayed contexts: A only
            assert torch.equal(batch.replay_tokens, incremental.replay_contexts(study, update))
            assert torch.equal(
                batch.tokens, seq_stream.batch(update).tokens
            )  # B's schedule is unchanged
            # the replayed contexts are whole contexts of eight A facts in one cluster
            assert bool(
                (
                    study.lane_d.cluster[batch.replay_fact_ids]
                    == study.lane_d.cluster[batch.replay_fact_ids][:, :1]
                ).all()
            )
            assert bool(
                (
                    study.lane_d.cluster[batch.fact_ids]
                    == study.lane_d.cluster[batch.fact_ids][:, :1]
                ).all()
            )
        record = replay["executed"].record
        arm_seq = phase_b[(arch, "sequential")]["executed"].record
        assert (
            record["run_updates"]
            == arm_seq["run_updates"]
            == core.updates(cell, EXPOSURE)
            == PHASE_UPDATES
        )
        assert (
            record["examples"] == 32 * PHASE_UPDATES and arm_seq["examples"] == 16 * PHASE_UPDATES
        )
        assert record["tokens"] == 2 * arm_seq["tokens"]
    # replay_contexts is a pure function of the update
    assert torch.equal(incremental.replay_contexts(study, 5), incremental.replay_contexts(study, 5))
    assert not torch.equal(
        incremental.replay_contexts(study, 5), incremental.replay_contexts(study, 6)
    )
    assert incremental.replay_contexts(study, 3).shape == (16, 64)
    # one update is one epoch of A here (128 facts = 128 answer sites per update): each A fact once
    for update in (1, 2):
        seen = study_replay_ids(study, update).reshape(-1)
        assert sorted(seen.tolist()) == list(range(n))
    assert phase_b[("flat", "sequential")]["job"].stream.batch(1).replay_tokens is None


def study_replay_ids(study: data.StudyData, update: int) -> torch.Tensor:
    cell = lane_cell("flat", "replay")
    ids = data.training_stream_for(study, cell).batch(update).replay_fact_ids
    assert ids is not None
    return ids


# --- the joint bound --------------------------------------------------------------------------------------------------------------
def test_joint_bound_has_twice_the_updates_and_trains_on_a_and_b(
    study: data.StudyData, phase_b: dict[tuple[str, str], dict[str, Any]]
) -> None:
    n = study.lane_d_set_size
    joint = phase_b[("flat", "joint")]
    cell = joint["cell"]
    record = joint["executed"].record
    assert cell.depends_on == () and cell.facts == 2 * n
    assert core.updates(cell, EXPOSURE) == 2 * PHASE_UPDATES == record["run_updates"]
    assert record["examples"] == 16 * 2 * PHASE_UPDATES
    assert (
        record["unique_facts"] == 2 * n
        and record["exposure_per_fact_min"] == record["exposure_per_fact_max"] == EXPOSURE
    )
    assert joint["job"].init_snapshot is None and joint["job"].trainable_groups is None
    ids = joint["job"].stream.facts
    assert ids.shape[0] == 2 * n and bool((ids[:n] < n).all()) and bool((ids[n:] >= n).all())
    # from initialization: the joint run's start equals a fresh model of the same seed
    job = dataclasses.replace(
        joint["job"], out_dir=joint["job"].out_dir.parent / "joint_zero", max_updates=0
    )
    zero = train.run_job(job)
    fresh = build_model(cell, backbone(), init_seed=SEEDS.facts)
    for name, tensor in fresh.state_dict().items():
        assert torch.equal(tensor, zero.model.state_dict()[name]), name


# --- measurements ----------------------------------------------------------------------------------------------------------------------------
def fake_snapshot(root: Path, update: int, state: dict[str, torch.Tensor]) -> Path:
    folder = root / "snapshots" / core.snapshot_stem(update)
    folder.mkdir(parents=True)
    torch.save(
        {"update": update, "model": {f"addition.{k}": v for k, v in state.items()}},
        folder / "model.pt",
    )
    return folder


def test_changed_slots_and_bytes_on_a_hand_case(tmp_path: Path) -> None:
    keys = torch.arange(10 * 4, dtype=torch.float32).reshape(10, 4)
    values = torch.arange(10 * 6, dtype=torch.float32).reshape(10, 6)
    base = {"keys": keys, "values": values, "wq": torch.ones(4, 6), "gate": torch.tensor(-2.0)}
    v1 = fake_snapshot(tmp_path / "v1", 1, base)
    # keys of slots 1 and 3 change, values of slots 3 and 7 change: three distinct slots
    k2, v2 = keys.clone(), values.clone()
    k2[1] += 1.0
    k2[3] += 1.0
    v2[3] += 1.0
    v2[7] += 1.0
    only_rows = fake_snapshot(tmp_path / "v2", 1, {**base, "keys": k2, "values": v2})
    assert incremental.changed_between(v1, only_rows) == (3, 2 * 4 * 4 + 2 * 6 * 4)
    assert incremental.changed_between(v1, v1) == (0, 0)
    # a changed projection row and the gate add bytes but no slot
    wq = base["wq"].clone()
    wq[2] = 5.0
    more = fake_snapshot(
        tmp_path / "v3", 1, {**base, "keys": k2, "values": v2, "wq": wq, "gate": torch.tensor(-1.0)}
    )
    assert incremental.changed_between(v1, more) == (3, 2 * 4 * 4 + 2 * 6 * 4 + 1 * 6 * 4 + 4)
    detail = incremental.changed_detail(v1, more)
    assert detail["tensors"]["keys"] == {"changed_rows": 2, "changed_bytes": 32}
    assert detail["tensors"]["wq"] == {"changed_rows": 1, "changed_bytes": 24}
    # a difference in the last bit of one element counts, a NaN that stays the same does not
    flip = keys.clone()
    flip[5, 0] = torch.nextafter(flip[5, 0], torch.tensor(1e9))
    bit = fake_snapshot(tmp_path / "v4", 1, {**base, "keys": flip})
    assert incremental.changed_between(v1, bit) == (1, 4 * 4)
    nan_keys = keys.clone()
    nan_keys[0, 0] = float("nan")
    one = fake_snapshot(tmp_path / "n1", 1, {**base, "keys": nan_keys})
    two = fake_snapshot(tmp_path / "n2", 1, {**base, "keys": nan_keys.clone()})
    assert incremental.changed_between(one, two) == (0, 0)
    # dense has no slots: its changed bytes are counted
    dense1 = fake_snapshot(
        tmp_path / "d1",
        1,
        {"w1": torch.zeros(5, 3), "w2": torch.zeros(3, 5), "gate": torch.tensor(0.0)},
    )
    dense2 = fake_snapshot(
        tmp_path / "d2",
        1,
        {"w1": torch.ones(5, 3), "w2": torch.zeros(3, 5), "gate": torch.tensor(0.0)},
    )
    assert incremental.changed_between(dense1, dense2) == (0, 5 * 3 * 4)
    with pytest.raises(ValueError):
        incremental.changed_between(v1, dense1)


def test_changed_counts_of_real_phase_b_runs(
    phase_a: dict[str, dict[str, Any]],
    phase_b: dict[tuple[str, str], dict[str, Any]],
    run_dir: Path,
) -> None:
    flat = core.snapshot_dir(run_dir, phase_b[("flat", "memory_only")]["cell"].label, PHASE_UPDATES)
    v1 = phase_a["flat"]["snapshot"]
    slots, nbytes = incremental.changed_between(v1, flat)
    detail = incremental.changed_detail(v1, flat)
    assert (
        0 < slots <= 4096
        and nbytes
        == detail["tensors"]["keys"]["changed_bytes"] + detail["tensors"]["values"]["changed_bytes"]
    )
    assert (
        detail["tensors"]["wq"]["changed_rows"] == 0
        and detail["tensors"]["gate"]["changed_bytes"] == 0
    )
    seq = core.snapshot_dir(run_dir, phase_b[("flat", "sequential")]["cell"].label, PHASE_UPDATES)
    s_slots, s_bytes = incremental.changed_between(v1, seq)
    assert (
        s_bytes > s_slots * 0
        and incremental.changed_detail(v1, seq)["tensors"]["wq"]["changed_rows"] > 0
    )
    dense = incremental.changed_between(
        phase_a["dense"]["snapshot"],
        core.snapshot_dir(run_dir, phase_b[("dense", "sequential")]["cell"].label, PHASE_UPDATES),
    )
    assert dense[0] == 0 and dense[1] > 0


def test_arithmetic_of_the_measurements() -> None:
    assert incremental.forgetting(0.8, 0.6) == pytest.approx(0.2)
    assert incremental.forgetting(0.5, 0.7) == pytest.approx(
        -0.2
    )  # a gain is a negative forgetting
    assert incremental.logical_lookup_work("flat", 16384, 10) == 163840
    assert incremental.logical_lookup_work(
        "learned_tree", 16384, 10
    ) == 10 * core.logical_key_products("learned_tree", 16384)
    assert incremental.logical_lookup_work("dense", 16384, 10) == 0
    with pytest.raises(ValueError):
        incremental.logical_lookup_work("flat", 16384, -1)
    assert incremental.lane_d_gate({"x": 0.5, "y": 0.4999, "z": 0.93}) == {
        "x": True,
        "y": False,
        "z": True,
    }
    assert incremental.lane_d_gate({}) == {}
    detail = incremental.support_overlap_detail([[1, 2], [3]], [[3, 4], [4, 5]])
    assert (
        detail["slots_a"] == 3
        and detail["slots_b"] == 3
        and detail["shared"] == 1
        and detail["union"] == 5
    )
    assert detail["jaccard"] == pytest.approx(0.2) and detail["share_of_b_in_a"] == pytest.approx(
        1 / 3
    )
    empty = incremental.support_overlap_detail([], [])
    assert empty["jaccard"] is None and empty["share_of_b_in_a"] is None


def write_eval(run_dir: Path, label: str, update: int, stream: str, accuracy: float) -> None:
    record = {
        **core.envelope("eval"),
        "label": label,
        "update": update,
        "stream": stream,
        "accuracy": accuracy,
    }
    path = core.eval_path(run_dir, label, update, stream)
    core.write_record(path, record)


def test_measure_arm_reads_records_snapshots_and_the_train_record(
    study: data.StudyData,
    phase_a: dict[str, dict[str, Any]],
    phase_b: dict[tuple[str, str], dict[str, Any]],
    run_dir: Path,
    tmp_path: Path,
) -> None:
    cell = _b_cell("flat", "memory_only")
    d1 = cell.depends_on[0]
    run = tmp_path / "run"
    # hand-made accuracies; the snapshots and the train record are those of the real tiny runs
    numbers = {
        (d1, PHASE_UPDATES, "a", "A"): 0.9,
        (cell.label, PHASE_UPDATES, "a", "A"): 0.6,
        (cell.label, PHASE_UPDATES, "a", "B"): 0.3,
        (d1, PHASE_UPDATES, "b", "A"): 0.8,
        (cell.label, PHASE_UPDATES, "b", "A"): 0.5,
        (cell.label, PHASE_UPDATES, "b", "B"): 0.25,
    }
    for (label, update, panel, which), accuracy in numbers.items():
        write_eval(run, label, update, f"lane_d_{panel}_{which}", accuracy)
    src = phase_b[("flat", "memory_only")]["executed"].record
    core.write_record(core.cell_dir(run, cell.label) / "train.json", src)
    # copy the two snapshots
    shutil.copytree(phase_a["flat"]["snapshot"], core.snapshot_dir(run, d1, PHASE_UPDATES))
    shutil.copytree(
        core.snapshot_dir(run_dir, cell.label, PHASE_UPDATES),
        core.snapshot_dir(run, cell.label, PHASE_UPDATES),
    )
    supports = {"A": ([[1, 2]], [[2, 3]]), "B": ([[1]], [[2]])}
    rows = incremental.measure_arm(cell, run, study, tmp_path, EXPOSURE, supports=supports)
    assert [r.panel for r in rows] == ["A", "B"]
    first, second = rows
    assert (first.a0_acc, first.a_acc, first.b_acc) == (0.9, 0.6, 0.3)
    assert (second.a0_acc, second.a_acc, second.b_acc) == (0.8, 0.5, 0.25)
    assert first.support_overlap == pytest.approx(1 / 3) and second.support_overlap == 0.0
    assert first.updates == PHASE_UPDATES and first.examples == 16 * PHASE_UPDATES
    assert first.logical_lookup_work == 16 * PHASE_UPDATES * 63 * 4096
    assert first.changed_slots > 0 and first.changed_bytes > 0
    assert incremental.forgetting(first.a0_acc or 0.0, first.a_acc) == pytest.approx(0.3)
    no_supports = incremental.measure_arm(cell, run, study, tmp_path, EXPOSURE)
    assert all(r.support_overlap is None for r in no_supports)
    # a missing evaluation record is named, not guessed
    core.eval_path(run, cell.label, PHASE_UPDATES, "lane_d_b_B").unlink()
    with pytest.raises(FileNotFoundError, match="lane_d_b_B"):
        incremental.measure_arm(cell, run, study, tmp_path, EXPOSURE)
    # rehearsal runs are never measured
    core.write_record(core.cell_dir(run, cell.label) / "train.json", {**src, "mode": "rehearsal"})
    with pytest.raises(ValueError, match="rehearsal"):
        incremental.measure_arm(cell, run, study, tmp_path, EXPOSURE)
    with pytest.raises(ValueError, match="phase B"):
        incremental.measure_arm(lane_cell("flat", "phaseA"), run, study, tmp_path, EXPOSURE)


def test_exact_retrieval_append_control(study: data.StudyData) -> None:
    rows = incremental.exact_append_control(study)
    assert [r.panel for r in rows] == ["A", "B"]
    for r in rows:
        assert r.label == incremental.EXACT_LABEL
        assert (r.a0_acc, r.a_acc, r.b_acc) == (
            1.0,
            1.0,
            1.0,
        )  # a stored dictionary entry is never lost
        assert (
            r.changed_slots == study.lane_d_set_size
            and r.changed_bytes == study.lane_d_set_size * 6
        )
        assert r.updates == r.examples == r.logical_lookup_work == 0 and r.support_overlap is None


# --- end to end ---------------------------------------------------------------------------------------------------------------------------------------
def direct_accuracy(model: Any, stream: data.Stream) -> float:
    """Accuracy by a direct forward on a stream, through ``core.score_answer_sites``."""
    with torch.no_grad():
        logits, _ = model(stream.tokens[:, : core.INPUT_LENGTH])
    sites = torch.tensor(core.ANSWER_SITE_POSITIONS)
    scores = core.score_answer_sites(
        logits[:, sites].reshape(-1, 256), stream.answer_targets().reshape(-1)
    )
    return float(scores.correct.float().mean())


@pytest.mark.parametrize(("arch", "arm"), [*ADDITION_ARMS, ("flat", "joint")])
def test_tiny_a_to_b_run_of_every_arm_finishes_finite(
    arch: str,
    arm: str,
    study: data.StudyData,
    phase_a: dict[str, dict[str, Any]],
    phase_b: dict[tuple[str, str], dict[str, Any]],
) -> None:
    executed = phase_b[(arch, arm)]["executed"]
    assert executed.record["status"] == "completed"
    assert all(executed.trainer.all_finite.values())
    assert all(bool(torch.isfinite(p).all()) for p in executed.model.parameters())
    expected = 2 * PHASE_UPDATES if arm == "joint" else PHASE_UPDATES
    assert executed.record["run_updates"] == expected
    for stream_name in ("lane_d_a_A", "lane_d_a_B", "lane_d_b_A", "lane_d_b_B"):
        accuracy = direct_accuracy(executed.model, study.streams[stream_name])
        assert 0.0 <= accuracy <= 1.0
    for item in phase_a.values():
        assert all(bool(torch.isfinite(p).all()) for p in item["executed"].model.parameters())
    assert all(bool(torch.isfinite(torch.tensor(u["task_loss"]))) for u in executed.updates)


# --- command line --------------------------------------------------------------------------------------------------------------------------------------
def test_cli_phase_a_then_phase_b_and_the_missing_dependency_exit(
    study: data.StudyData,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    flat_a, flat_b = lane_cell("flat", "phaseA"), lane_cell("flat", "sequential")
    current: dict[str, core.Cell] = {}

    def fake_context(args: Any, *, backbone: bool) -> tuple[core.Cell, data.StudyData, Any, Path]:
        cell = current["cell"]
        return cell, study, make_backbone() if backbone else None, tmp_path

    monkeypatch.setattr(incremental, "_load_context", fake_context)
    monkeypatch.setattr(train, "_configure", lambda: None)
    run = tmp_path / "run"
    base = ["--run-dir", str(run), "--mode", "calibration"]
    current["cell"] = flat_b
    assert (
        incremental.main(
            [
                "phase-b",
                "--label",
                flat_b.label,
                *base,
                "--v1",
                str(core.snapshot_dir(run, flat_a.label, PHASE_UPDATES)),
            ]
        )
        == 3
    )
    assert flat_a.label in capsys.readouterr().err
    current["cell"] = flat_a
    assert incremental.main(["phase-a", "--label", flat_a.label, *base]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "completed"
    current["cell"] = flat_b
    v1 = core.snapshot_dir(run, flat_a.label, PHASE_UPDATES)
    assert (
        incremental.main(
            ["phase-b", "--label", flat_b.label, *base, "--v1", str(v1), "--max-updates", "2"]
        )
        == 0
    )
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "completed" and set(out) == {
        "label",
        "status",
        "record",
    }  # no loss or accuracy printed
    assert (
        incremental.main(["measure", "--label", flat_b.label, *base[:2], "--mode", "rehearsal"])
        == 2
    )
    assert TEST_SEED >= 179001
