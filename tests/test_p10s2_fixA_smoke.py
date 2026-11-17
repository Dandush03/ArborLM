# ruff: noqa: E501
"""P10S2: the real-transformers failures of the first data-generation attempts, on fakes (no library of the datagen set, no network, no real file): the teacher load, the student's generate call, the
equivalence tensors of the bundle, and the smoke command's discipline. Self-check only: not independent review, not Astra validation, not human approval."""

import bz2
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10s2 import datagen, datagen_smoke, worldio  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class FakeMarian(torch.nn.Module):
    """A Marian-shaped stand-in: a shared embedding, one layer and an output projection tied to the embedding by ``tie_weights``; the checkpoint does not store ``lm_head.weight``."""

    def __init__(self, config: Any) -> None:
        super().__init__()
        self.config = config
        self.shared = torch.nn.Embedding(5, 3)
        self.layer = torch.nn.Linear(3, 3)
        self.lm_head = torch.nn.Linear(3, 5, bias=False)

    def get_input_embeddings(self) -> torch.nn.Module:
        return self.shared

    def tie_weights(self) -> None:
        self.lm_head.weight = self.shared.weight


def fake_tf() -> Any:
    return SimpleNamespace(MarianConfig=SimpleNamespace(from_dict=lambda d: SimpleNamespace(**d)), MarianMTModel=FakeMarian)


def good_state() -> dict[str, torch.Tensor]:
    m = FakeMarian(SimpleNamespace())
    return {k: v.clone() for k, v in m.state_dict().items() if k != "lm_head.weight"}


def test_the_teacher_is_built_from_the_config_and_the_safely_loaded_state_with_the_tied_key_explicit() -> None:
    state = good_state()
    model, rec = datagen.build_marian(fake_tf(), {"pad_token_id": 0}, state)
    assert rec["missing_keys_tied_explicitly"] == ["lm_head.weight"] and rec["unexpected_keys"] == [] and rec["lm_head_shares_embedding_storage"] is True
    assert torch.equal(model.shared.weight, state["shared.weight"]) and model.lm_head.weight.data_ptr() == model.shared.weight.data_ptr()
    src = (ROOT / "studies/p10s2/datagen.py").read_text()
    assert "state_dict=state" not in src and "from_pretrained(str(directory), state_dict" not in src  # the call that the real library refuses is gone
    assert "build_marian(tf, json.loads(fetch_guard.read_verified_bytes(downloads" in src and "load_pickle_weights" in src  # config from the verified bytes, weights from the safe loader


def test_an_untied_missing_or_unexpected_key_stops_the_step() -> None:
    state = good_state()
    del state["layer.bias"]
    with pytest.raises(datagen.DatagenStop, match="missing"):
        datagen.build_marian(fake_tf(), {}, state)
    state = good_state()
    state["extra.weight"] = torch.zeros(1)
    with pytest.raises(datagen.DatagenStop, match="unexpected"):
        datagen.build_marian(fake_tf(), {}, state)

    class Untied(FakeMarian):
        def tie_weights(self) -> None:
            return None  # the library did not tie the projection

    with pytest.raises(datagen.DatagenStop, match="not tied"):
        datagen.build_marian(SimpleNamespace(MarianConfig=fake_tf().MarianConfig, MarianMTModel=Untied), {}, good_state())


def test_the_student_reference_generates_with_an_explicit_mask_and_pad_id() -> None:
    seen: dict[str, Any] = {}

    class M:
        config = SimpleNamespace(eos_token_id=0)

        def generate(self, ids: torch.Tensor, **kw: Any) -> torch.Tensor:
            seen.update(kw)
            return torch.cat([ids, torch.ones(1, 3, dtype=torch.long)], dim=1)

    ref = datagen.HFReference.__new__(datagen.HFReference)
    ref.model = M()
    out = ref.generate(torch.tensor([[5, 6, 7]]), 3)
    assert out == [1, 1, 1] and torch.equal(seen["attention_mask"], torch.ones(1, 3, dtype=torch.long)) and seen["pad_token_id"] == 0  # one unpadded prompt: nothing to mask, said explicitly


def test_the_equivalence_logits_are_tensors_in_a_hashed_file_not_json_lists(tmp_path: Path) -> None:
    rec = lambda layer: {"layer": layer, "rms_norm_eps": 1e-5, "reference_logits": torch.randn(2, 3, 7), "reference_injection_logits": torch.randn(2, 3, 7), "at_creation": {"logits": {"ok": True}, "injection": {"ok": True}}}  # noqa: E731
    extra = {"equivalence_layers": {"4": rec(4), "12": rec(12)}}
    extra["equivalence"] = extra["equivalence_layers"]["4"]  # the first layer appears twice
    stripped, tensors = worldio._strip_equivalence_tensors(extra)
    assert sorted(tensors) == ["L12/reference_injection_logits", "L12/reference_logits", "L4/reference_injection_logits", "L4/reference_logits"]  # once each
    assert isinstance(extra["equivalence"]["reference_logits"], torch.Tensor)  # the caller's record is not changed
    import json

    assert "@tensor:L4/reference_logits" in json.dumps(stripped) and len(json.dumps(stripped)) < 2000  # JSON without the logits
    worldio._restore_equivalence_tensors(stripped, tensors)
    assert torch.equal(stripped["equivalence"]["reference_logits"], extra["equivalence"]["reference_logits"]) and torch.equal(stripped["equivalence_layers"]["12"]["reference_injection_logits"], extra["equivalence_layers"]["12"]["reference_injection_logits"])
    again, none = worldio._strip_equivalence_tensors(stripped)  # a record already restored is stripped again identically; a stripped one is left alone
    assert sorted(none) == sorted(tensors) and worldio._strip_equivalence_tensors(worldio._strip_equivalence_tensors(extra)[0])[1] == {}


def test_a_bundle_round_trips_its_equivalence_records_through_the_hashed_tensor_file(tmp_path: Path) -> None:
    from studies.p10s2 import equivalence, standins
    from studies.p10s2.stages import _dry_equivalence

    bundle, _ = standins.build_synthetic_bundle(1)
    bundle.extra["equivalence"] = _dry_equivalence(bundle, 1)
    bundle.extra["equivalence_layers"] = {"1": bundle.extra["equivalence"]}
    manifest = worldio.write_bundle(bundle, tmp_path / "b")
    assert "equivalence_tensors.pt" in manifest["files"] and '"reference_logits":"@tensor:' in (tmp_path / "b" / "extra.json").read_text()
    back = worldio.read_bundle(tmp_path / "b")
    rec = back.extra["equivalence"]
    assert isinstance(rec["reference_logits"], torch.Tensor) and torch.equal(rec["reference_logits"], bundle.extra["equivalence"]["reference_logits"])
    world = worldio.build_world(back, "test", 1, worldio.RunConfig.dry())
    assert equivalence.verify_all(world.student, back.extra["equivalence_layers"])["ok"]  # G8 on the round-tripped record
    (tmp_path / "b" / "equivalence_tensors.pt").write_bytes(b"x")
    with pytest.raises(ValueError, match="does not hash"):
        worldio.read_bundle(tmp_path / "b")  # the tensor file is under the manifest like every other file


def test_the_smoke_command_reads_first_rows_reports_every_failure_and_writes_nothing(tmp_path: Path) -> None:
    p = tmp_path / "x.tsv.bz2"
    p.write_bytes(bz2.compress(b"".join(f"{i}\teng\tsentence {i}\n".encode() for i in range(50))))
    assert datagen_smoke.first_lines(p, 7).count(b"\n") == 7 and datagen_smoke.first_lines(p, 500).count(b"\n") == 50
    s = datagen_smoke.Smoke()
    assert s.step("good", lambda: {"a": 1}) == {"a": 1}

    def boom() -> None:
        raise RuntimeError("a real-library failure")

    assert s.step("bad", boom) is None and s.step("after", lambda: 2) == 2  # a failure is recorded and the exercise goes on
    assert s.failures == ["bad"] and s.results["bad"]["error"].startswith("RuntimeError") and s.results["after"]["ok"] is True
    src = (ROOT / "studies/p10s2/datagen_smoke.py").read_text()
    assert not re.search(r"write_text|write_bytes|write_json|torch\.save|open\([^)]*[\"']w", src)  # nothing is written anywhere
    assert "partition_gen" not in src and "registered-" not in src.replace("registered-data", "") and 'seeded_generator(seed' in src and '"test")' in src  # test-range seeds only, never a registered stream
    main_src = (ROOT / "studies/p10s2/datagen.py").read_text()
    assert '"--smoke" in args_in' in main_src and "smoke_main" in main_src
    for literal in datagen_smoke.SENTENCES:
        assert isinstance(literal, str) and literal.isascii()  # fixed literal English sentences written into the code


PINNED = {"bad_words_ids": [[3]], "bos_token_id": 0, "decoder_start_token_id": 3, "eos_token_id": 0, "forced_eos_token_id": 0, "max_length": 512, "num_beams": 4, "pad_token_id": 3, "renormalize_logits": True, "transformers_version": "4.32.0.dev0"}


def gen_tf() -> Any:
    class GC(SimpleNamespace):
        @staticmethod
        def from_dict(d: dict[str, Any]) -> "GC":
            return GC(**{k: v for k, v in d.items() if k != "transformers_version"})

        def to_dict(self) -> dict[str, Any]:
            return dict(self.__dict__)

    return SimpleNamespace(GenerationConfig=GC)


def test_the_pinned_generation_config_is_applied_to_the_model_and_every_key_is_checked() -> None:
    model = SimpleNamespace(generation_config=SimpleNamespace(renormalize_logits=False, num_beams=4))  # what building from config.json alone leaves
    applied = datagen.apply_generation_config(gen_tf(), model, PINNED)
    assert model.generation_config.renormalize_logits is True and applied["renormalize_logits"] is True and applied["bad_words_ids"] == [[3]] and applied["forced_eos_token_id"] == 0
    assert set(applied) >= {k for k in PINNED if k != "transformers_version"}  # the full applied configuration, not four keys
    datagen.check_generation_config(model.generation_config, PINNED)
    for key, bad in (("renormalize_logits", False), ("num_beams", 5), ("bad_words_ids", [[4]])):
        setattr(model.generation_config, key, bad)
        with pytest.raises(datagen.DatagenStop, match=key):
            datagen.check_generation_config(model.generation_config, PINNED)  # a difference at generate time stops the step
        setattr(model.generation_config, key, PINNED[key])
    del model.generation_config.pad_token_id
    with pytest.raises(datagen.DatagenStop, match="pad_token_id"):
        datagen.check_generation_config(model.generation_config, PINNED)  # a key that is absent on the model is a difference too


def test_the_teacher_checks_the_pinned_config_before_every_generate_call_and_records_the_applied_one() -> None:
    src = (ROOT / "studies/p10s2/datagen.py").read_text()
    assert "apply_generation_config(tf, self.model, self.generation_config)" in src and '"generation_config_applied": self.applied_generation_config' in src
    assert src.index("check_generation_config(self.model.generation_config, self.generation_config)") < src.index("enc = self.tokenizer(batch")  # before the batch is generated


def test_the_embedding_copies_of_the_checkpoint_must_be_equal() -> None:
    e = torch.randn(5, 3)
    ok = {"model.shared.weight": e, "model.encoder.embed_tokens.weight": e.clone(), "model.decoder.embed_tokens.weight": e.clone(), "other": torch.zeros(1)}
    assert datagen.check_embedding_copies(ok) == list(datagen.EMBEDDING_COPIES)
    bad = {**ok, "model.decoder.embed_tokens.weight": e + 1e-3}
    with pytest.raises(datagen.DatagenStop, match="embedding copies differ"):
        datagen.check_embedding_copies(bad)
    with pytest.raises(datagen.DatagenStop, match="embedding copies differ"):
        datagen.build_marian(fake_tf(), {}, {**good_state(), "model.shared.weight": e, "model.encoder.embed_tokens.weight": e + 1})
    assert datagen.check_embedding_copies({"layer.weight": e}) == []  # a checkpoint without copies has nothing to compare


def test_the_gen_report_says_kl_and_top1_are_plain_means_over_all_144_windows() -> None:
    from studies.p10s2 import report

    text = "\n".join(report.gen_lines([], []))
    assert "plain per-window means over all 144 windows" in text and "enter no rule" in text
    assert "200 general-language" not in (ROOT / "studies/p10s2/core.py").read_text()


def test_the_step_frees_the_copies_it_no_longer_needs_before_the_corpus_and_the_teachers_are_loaded() -> None:
    """Attempt 6 stopped on the 8 GiB memory guard (8.09 GiB sampled). Measured on the real inputs, the step held the student three times over (converted state, Hugging Face state, reference model) through the
    corpus and the teachers; the peak up to the first teacher generation fell from 7,929 MB to 6,560 MB when they were freed, with every digest of the step identical (partition, sources, windows, equivalence
    records, tokenizer records)."""
    src = (ROOT / "studies/p10s2/datagen.py").read_text()
    body = src[src.index("def _run(") :]
    for stmt in ("del plain", "del hf_state", "del ref, ids, vec, prompts, train_ids"):
        assert stmt in body
    order = [body.index(x) for x in ("HFReference(", "del hf_state", "build_record(student, ref", "del ref, ids, vec, prompts, train_ids", "gc.collect()", "load_corpus(downloads", "MarianTeacher(downloads")]
    assert order == sorted(order)  # each copy is freed after its last use and before the corpus and the teachers
    after_free = body[body.index("del ref, ids, vec, prompts, train_ids") :]
    for name in ("hf_state", "plain", "ref", "train_ids"):
        assert not __import__("re").search(rf"\b{name}\b", after_free.replace("del ref, ids, vec, prompts, train_ids", "")), name  # none of them is used again
