# ruff: noqa: E501
"""P10S2 student, store, arms, snapshots and the weights-only rule (ADR-0022 sections 2, 3, 6.3, 7, 12.3 G4/G5). Self-check only: not independent review, not Astra validation, not human approval."""

import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10s2 import core, fetch_guard, gates, memory, model  # noqa: E402
from studies.p10s2.synthetic import tgen  # noqa: E402

CFG = model.StudentConfig.tiny(80)


def student() -> model.Student:
    return model.build_student(CFG, tgen(41, "model tests"))


def unit(rows: int, seed: int) -> torch.Tensor:
    return torch.nn.functional.normalize(torch.randn(rows, core.KEY_WIDTH, generator=tgen(seed, "unit queries")), dim=-1)


# --- the student ---------------------------------------------------------------------------------------------------------------------------------
def test_cache_equals_full_recomputation_and_no_student_parameter_trains() -> None:
    st = student()
    ids = torch.randint(0, 80, (2, 9), generator=tgen(42, "ids"))
    full = st(ids)
    cache = model.Cache()
    first = st(ids[:, :5], cache=cache)
    rest = [st(ids[:, k : k + 1], cache=cache) for k in range(5, 9)]
    assert (full[:, :5] - first).abs().max() < 1e-5 and all((full[:, 5 + k] - r[:, 0]).abs().max() < 1e-5 for k, r in enumerate(rest))
    assert not any(p.requires_grad for p in st.parameters())
    assert full.shape == (2, 9, 80)


def test_hidden_at_stops_early_and_matches_a_full_pass_hook() -> None:
    st = student()
    ids = torch.randint(0, 80, (1, 7), generator=tgen(43, "ids"))
    captured: list[torch.Tensor] = []
    h = st.blocks[1].register_forward_hook(lambda _m, _i, out: captured.append(out[0].detach().clone()))
    st(ids)
    h.remove()
    assert torch.allclose(captured[0], st.block_output(ids, 1), atol=1e-6)


def test_injection_is_added_to_the_output_of_block_l_and_only_there() -> None:
    st = student()
    ids = torch.randint(0, 80, (1, 6), generator=tgen(44, "ids"))
    base = st(ids)
    add = torch.zeros(1, 6, CFG.width)
    st.read_layer = 1
    assert torch.equal(st(ids, add=add), base)  # a zero injection changes nothing
    add[0, 3] = 0.3 * torch.ones(CFG.width)
    out = st(ids, add=add)
    assert torch.equal(out[:, :3], base[:, :3]) and not torch.equal(out[:, 3:], base[:, 3:])  # causal: positions before the read are unchanged
    st.read_layer = None
    assert torch.equal(st(ids, add=add), base)  # no read layer: nothing is added


def test_lora_untrained_changes_nothing_and_scale_is_one() -> None:
    st = student()
    ids = torch.randint(0, 80, (1, 6), generator=tgen(45, "ids"))
    ad = model.LoRAAdapter(CFG, 4, tgen(46, "lora"))
    assert ad.scale == 1.0 and all(float(b.detach().abs().max()) == 0.0 for b in ad.b)  # alpha = r, B zero
    bound = 1.0 / CFG.width**0.5
    assert all(float(a.detach().abs().max()) <= bound for a in ad.a)  # A uniform on +-1/sqrt(fan-in)
    assert torch.equal(st(ids, adapter=ad), st(ids))
    with torch.no_grad():
        ad.b[0].fill_(0.1)
    assert not torch.equal(st(ids, adapter=ad), st(ids))


def test_hugging_face_conversion_round_trip() -> None:
    st = student()
    sd = model.export_hf_state_dict(st)
    assert "model.layers.0.self_attn.q_proj.weight" in sd and "model.embed_tokens.weight" in sd and "lm_head.weight" not in sd  # tied embeddings
    other = model.build_student(CFG)
    model.load_plain_state(other, model.convert_hf_state_dict(sd, CFG))
    ids = torch.randint(0, 80, (1, 6), generator=tgen(47, "ids"))
    assert torch.equal(other(ids), st(ids))
    bad = dict(model.convert_hf_state_dict(sd, CFG))
    bad.pop("embed")
    with pytest.raises(ValueError):
        model.load_plain_state(other, bad)


# --- the store ----------------------------------------------------------------------------------------------------------------------------------
def test_read_matches_the_definition_on_a_hand_computed_case() -> None:
    s = memory.SparseStore(4)
    keys = torch.zeros(12, core.KEY_WIDTH)
    for i in range(12):
        keys[i, 0], keys[i, 1] = 1.0, 0.1 * i  # increasing angle from the first axis
    vals = torch.arange(12, dtype=torch.float32)[:, None].repeat(1, 4)
    s.keys.append(torch.nn.Parameter(keys))
    s.values.append(torch.nn.Parameter(vals))
    s.gates.append(torch.nn.Parameter(torch.tensor([0.5])))
    s.stage_rows.append(12)
    q = torch.zeros(1, core.KEY_WIDTH)
    q[0, 0] = 1.0
    a = (q @ (keys / keys.norm(dim=-1, keepdim=True)).t())[0]
    top = torch.topk(a, 8).indices
    w = torch.softmax(a[top] / 0.2, dim=0)
    expect = (w[:, None] * 0.5 * vals[top]).sum(0)
    got = s.read(q)[0]
    assert torch.allclose(got, expect, atol=1e-6) and sorted(s.selected_rows(q)[0].tolist()) == sorted(top.tolist())
    assert sorted(s.selected_rows(q)[0].tolist()) == list(range(8))  # the 8 rows closest in angle


def test_lowest_index_tie_rule_and_gate_zero_reads_nothing() -> None:
    assert gates.tie_rule_check()["ok"]
    s = memory.SparseStore.new(4, 20, tgen(48, "store"))
    assert float(s.read(unit(3, 49)).abs().max()) == 0.0  # the gate starts at zero: a new store changes nothing
    assert s.parameter_count() == 20 * (core.KEY_WIDTH + 4) + 1


def test_initialization_draws_keys_then_values_from_one_generator_and_appended_rows_use_their_own_seed() -> None:
    k, v = memory.fresh_stage(tgen(50, "a"), 5, 7)
    k2, v2 = memory.fresh_stage(tgen(50, "b"), 5, 7)
    assert torch.equal(k, k2) and torch.equal(v, v2)  # direct seeding, a fresh generator per use
    g = tgen(50, "c")
    expect_keys = core.INIT_STD * torch.randn(5, core.KEY_WIDTH, generator=g)
    expect_vals = core.INIT_STD * torch.randn(5, 7, generator=g)
    assert torch.equal(k, expect_keys) and torch.equal(v, expect_vals)  # keys first, then values
    assert abs(float(k.std()) - 0.02) < 0.01
    s = memory.SparseStore.new(7, 5, tgen(50, "stage 1"))
    s.append_stage(5, tgen(51, "stage 2 (its own seed)"))
    assert not torch.equal(s.keys[0], s.keys[1]) and not torch.equal(s.values[0], s.values[1])
    same = memory.SparseStore.new(7, 5, tgen(50, "stage 1"))
    same.append_stage(5, tgen(50, "stage 2 reusing the stage-1 seed"))
    assert torch.equal(same.keys[0], same.keys[1])  # reuse would duplicate the first-stage keys, which the ADR avoids with a separate seed


def test_append_isolation_gate_g5c_and_first_rows_frozen_bit_for_bit() -> None:
    s = memory.SparseStore.new(6, 16, tgen(52, "stage 1"))
    with torch.no_grad():
        s.gates[0].fill_(1.0)
    s.append_stage(16, tgen(53, "stage 2"))
    q = unit(5, 54)
    r0 = memory.SparseStore.from_state(s.snapshot_state())
    with torch.no_grad():
        r0.values[1].zero_()
    r1 = memory.SparseStore.from_state(s.snapshot_state())
    with torch.no_grad():
        r1.values[1].copy_(1e4 * torch.randn(16, 6, generator=tgen(55, "arbitrary")))
    assert torch.equal(r0.read(q), r1.read(q)) and torch.equal(r0.read(q), s.read(q))  # g2 = 0 isolates the values of the new rows
    shares = memory.row_shares(s, q, 16)
    assert 0.0 < shares["weight_on_new_rows"] < 1.0  # the appended rows do take top-8 weight from the first rows (the append cost)
    before = [p.detach().clone() for p in s.stage_parameters(0)]
    s.freeze_stage(0)
    s.set_trainable([1])
    assert not any(p.requires_grad for p in s.stage_parameters(0)) and all(p.requires_grad for p in s.stage_parameters(1))
    opt = torch.optim.AdamW(s.trainable(), lr=0.1)
    for _ in range(3):
        out = s.read(q)
        (out.pow(2).sum() + 0 * s.gates[1].sum()).backward()  # type: ignore[no-untyped-call]
        opt.step()
        opt.zero_grad()
    assert all(torch.equal(a, b) for a, b in zip(before, s.stage_parameters(0), strict=True))  # first-stage keys, values and gate are bit-for-bit unchanged


# --- version store and snapshots ---------------------------------------------------------------------------------------------------------------------
def test_version_store_is_immutable_pinned_and_rolls_back(tmp_path: Path) -> None:
    vs = memory.VersionStore(tmp_path / "v")
    s1 = memory.SparseStore.new(4, 10, tgen(56, "v1"))
    m1 = vs.publish("V1", s1)
    s2 = s1.clone()
    s2.append_stage(10, tgen(57, "v2"))
    m2 = vs.publish("V2", s2, parent="V1")
    assert m1["content_hash"] != m2["content_hash"] and m2["parent"] == "V1"
    with pytest.raises(memory.VersionRefused):
        vs.publish("V1", s1)  # immutable
    with pytest.raises(memory.VersionRefused):
        vs.publish("V3", s2, parent="missing")
    vs.pin("V1")
    reader = vs.pinned()
    vs.publish("V3", s2, parent="V2")  # a later version is prepared while a reader stays pinned
    assert reader.rows == 10 and vs.pinned().rows == 10
    vs.pin("V2")
    assert vs.pinned().rows == 20  # rollback and roll-forward are the pinning of a manifest
    (tmp_path / "v" / "V1.pt").write_bytes(b"tampered")
    with pytest.raises(memory.VersionRefused):
        vs.load("V1")


def test_arm_snapshots_restore_bit_identically_and_refuse_tampering() -> None:
    from test_p10s2_support import dry_world  # noqa: PLC0415

    from studies.p10s2.world import load_arm, save_arm

    world, _ = dry_world()
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        arm = memory.MemoryArm(memory.SparseStore.new(world.cfg.width, 12, tgen(58, "arm")), world.layer, world.codes(0))
        lora = memory.new_lora_arm(world.cfg, 2, tgen(59, "lora"))
        table = memory.TableArm("A", world.cfg.width, world.vocabulary, world.layer, tgen(60, "table"))
        for name, a in (("mem", arm), ("lora", lora), ("table", table)):
            save_arm(a, Path(d), name)
            back = load_arm(world, 0, Path(d), name)
            assert back.state_hash() == a.state_hash() and type(back) is type(a)
            with pytest.raises(FileExistsError):
                save_arm(a, Path(d), name)  # immutable
        p = Path(d) / "mem.pt"
        p.write_bytes(p.read_bytes()[:-8] + b"tamper!!")
        with pytest.raises(ValueError):
            load_arm(world, 0, Path(d), "mem")


# --- oracle codes ----------------------------------------------------------------------------------------------------------------------------------
def test_codes_are_a_seeded_hash_of_the_pair_and_seed_no_generator() -> None:
    core.reset_seed_record()
    cb = memory.CodeBook(229010, vocabulary=2000)
    a, b = cb.get("A", 5), cb.get("B", 5)
    assert abs(float(a.norm()) - 1.0) < 1e-6 and not torch.equal(a, b)
    assert memory.code_identifier("A", 7) == 7 and memory.code_identifier("B", 7) == 2001 + 7 and memory.code_identifier("B", core.MARKER_INDEX) == 2001 + 2000  # 2,001 tau + j
    assert torch.equal(memory.CodeBook(229010, 2000).get("A", 5), a) and not torch.equal(memory.CodeBook(229011, 2000).get("A", 5), a)
    assert core.seed_record() == []  # the hash seeds no generator


def test_ablation_constructors() -> None:
    s = memory.SparseStore.new(4, 10, tgen(61, "abl"))
    s.append_stage(10, tgen(62, "abl2"))
    ab = memory.make_ablation("value_perm", s, tgen(63, "perm"), stages=[1], tasks=["B"], vocabulary=30)
    assert set(ab.value_perms) == {1} and sorted(ab.value_perms[1].tolist()) == list(range(10))  # second-stage rows among themselves
    cp = memory.make_ablation("code_perm", s, tgen(63, "perm"), stages=[1], tasks=["B"], vocabulary=30)
    assert cp.code_perm is not None and sorted(cp.code_perm.tolist()) == list(range(30)) and cp.code_tasks == ("B",)
    reads = [(0, "A", 3), (1, "A", 30), (2, "B", 3), (3, "B", 30)]
    out = memory.apply_read_ablation(reads, cp, 30)
    assert out[0] == reads[0] and out[1] == reads[1] and out[3] == reads[3] and out[2][2] == int(cp.code_perm[3])  # only the second task's words move; markers kept
    assert memory.apply_read_ablation(reads, memory.Ablation("marker_only"), 30) == [reads[1], reads[3]]
    assert memory.apply_read_ablation(reads, memory.Ablation("words_only"), 30) == [reads[0], reads[2]]
    assert memory.apply_read_ablation(reads, memory.Ablation("off"), 30) == []
    with pytest.raises(ValueError):
        memory.Ablation("nope")


# --- weights-only loading of pickle files (section 4.1, 15 item 4) -------------------------------------------------------------------------------------
class Evil:
    def __reduce__(self):  # type: ignore[no-untyped-def]
        return (print, ("this must never run",))


def test_weights_only_loading_accepts_tensors_and_refuses_arbitrary_pickles(tmp_path: Path) -> None:
    ok = tmp_path / "pytorch_model.bin"
    torch.save({"w": torch.arange(4.0)}, ok)
    digest = fetch_guard.sha256_file(ok)
    assert torch.equal(fetch_guard.load_pickle_weights(ok, digest)["w"], torch.arange(4.0))
    with pytest.raises(fetch_guard.FetchRefused):
        fetch_guard.load_pickle_weights(ok, "0" * 64)  # the SHA-256 is checked first
    bad = tmp_path / "evil.bin"
    with bad.open("wb") as f:
        pickle.dump({"w": Evil()}, f)
    with pytest.raises(pickle.UnpicklingError):
        fetch_guard.load_pickle_weights(bad, fetch_guard.sha256_file(bad))  # the restricted unpickler refuses; the payload never runs
