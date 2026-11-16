# ruff: noqa: E501
"""P10S2 fix lane A: the pure helpers of the data-generation step and the pre-freeze checks it relies on (audit A-B2, A-B3, A-M7, A-M8, B-B3 half, minors 8-10, 12). ``datagen`` is imported only to run these
helpers on synthetic files and fakes (no Hugging Face package, no model, no network, no real data); ``datagen.run`` and the classes that wrap real packages are never called. Self-check only: not independent
review, not Astra validation, not human approval."""

import bz2
import hashlib
import sys
import time
import types
import zlib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p10s2 import core, datagen, equivalence, ledger, standins, tokenization  # noqa: E402
from studies.p10s2 import fetch_guard as g  # noqa: E402
from studies.p10s2.ledger import Ledger  # noqa: E402
from studies.p10s2.prefreeze import (  # noqa: E402
    tokenization_checks,
    tokenization_required_ok,
    tokenizer_records,
    verify_tokenizer_record,
)
from studies.p10s2.world import ExampleBank  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


# --- B-B3 (this lane's half): the stage cap and the study ledger -----------------------------------------------------------------------------------------
class StubLedger:
    def __init__(self, remaining_hours: float) -> None:
        self.hours = remaining_hours
        self.charges: list[tuple[str, float]] = []

    def charge(self, stage: str, seconds: float) -> None:
        self.charges.append((stage, seconds))

    def remaining(self) -> float:
        return self.hours


class FakeClock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


def test_the_step_charges_its_wall_time_to_the_study_ledger_even_when_it_fails() -> None:
    led, clock = StubLedger(10.0), FakeClock()
    with datagen.charged_stage(led, 3600.0, clock=clock) as sc:
        clock.t += 120.0
        sc.tick("fine")
    assert led.charges == [("datagen", 120.0)]
    with pytest.raises(datagen.DatagenStop):
        with datagen.charged_stage(led, 3600.0, clock=clock):
            clock.t += 30.0
            raise datagen.DatagenStop("a stop condition")
    assert led.charges[-1] == ("datagen", 30.0)  # charged although the block failed


def test_the_stage_cap_stops_the_step_and_a_ledger_without_room_refuses_to_start() -> None:
    led, clock = StubLedger(10.0), FakeClock()
    with pytest.raises(datagen.StageCapExceeded, match="stage cap of 60 s was reached after 61 s"):
        with datagen.charged_stage(led, 60.0, clock=clock) as sc:
            clock.t += 61.0
            sc.tick("teacher batch")
    assert led.charges == [("datagen", 61.0)]
    low = StubLedger(0.5)  # 1,800 s remaining, a cap of 6,480 s
    with pytest.raises(datagen.StageCapExceeded, match="remaining, less than the stage cap"):
        with datagen.charged_stage(low, 6480.0, clock=clock):
            raise AssertionError("must not start")
    assert low.charges == []  # a refused start charges nothing
    with pytest.raises(datagen.StageCapExceeded, match="positive"):
        with datagen.charged_stage(led, 0.0, clock=clock):
            raise AssertionError("must not start")
    assert issubclass(datagen.StageCapExceeded, datagen.DatagenStop) and issubclass(datagen.ScoreMismatch, datagen.DatagenStop)


# --- the requirements file ---------------------------------------------------------------------------------------------------------------------------
def test_requirements_without_hashes_are_refused_and_hashed_ones_pass(tmp_path: Path) -> None:
    good = "# c\ntransformers==4.57.1 \\\n    --hash=sha256:" + "a" * 64 + " \\\n    --hash=sha256:" + "b" * 64 + "\ntokenizers==0.22.1 --hash=sha256:" + "c" * 64 + "\n"
    assert datagen.unhashed_requirements(good) == []
    p = tmp_path / "r.txt"
    p.write_text(good)
    assert datagen.check_requirements_hashed(p) == 2
    p.write_text(good + "--index-url https://pypi.org/simple\n")
    with pytest.raises(datagen.DatagenStop, match="option lines"):
        datagen.check_requirements_hashed(p)  # re-check A, R2: an option line other than --hash is refused
    p.write_text(good + "numpy==2.3.3\n")
    with pytest.raises(datagen.DatagenStop, match=r"numpy==2\.3\.3"):
        datagen.check_requirements_hashed(p)
    real = datagen.unhashed_requirements((ROOT / datagen.REQUIREMENTS).read_text())
    assert real == ["transformers==4.57.1", "tokenizers==0.22.1", "safetensors==0.6.2", "huggingface-hub==0.35.3", "sentencepiece==0.2.1", "numpy==2.3.3", "sacremoses==0.1.1", "sacrebleu==2.5.1"]  # the committed file is not yet resolved with hashes: datagen refuses to run on it


# --- A-B3: the local WikiText parquet files ------------------------------------------------------------------------------------------------------------
class FakeParquetFile:
    """A stand-in for ``pyarrow.parquet.ParquetFile``: the 'parquet' files of the test hold the rows as text, one per line of a JSON list."""

    def __init__(self, path: Path) -> None:
        import json

        self.rows = json.loads(path.read_text())

    def __enter__(self) -> "FakeParquetFile":
        return self

    def __exit__(self, *a: Any) -> None:
        return None

    def iter_batches(self, columns: list[str], use_threads: bool) -> Any:
        assert columns == ["text"] and use_threads is False
        for i in range(0, len(self.rows), 2):
            chunk = self.rows[i : i + 2]
            yield types.SimpleNamespace(column=lambda k, chunk=chunk: types.SimpleNamespace(to_pylist=lambda: list(chunk)))


@pytest.fixture()
def fake_pyarrow(monkeypatch: pytest.MonkeyPatch) -> None:
    pq = types.ModuleType("pyarrow.parquet")
    pq.ParquetFile = FakeParquetFile  # type: ignore[attr-defined]
    pa = types.ModuleType("pyarrow")
    pa.parquet = pq  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyarrow", pa)
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", pq)


def write_wikitext(d: Path, train_rows: list[Any], val_rows: list[Any]) -> dict[str, dict[str, Any]]:
    import json

    d.mkdir(parents=True, exist_ok=True)
    pins = {}
    for name, rows in zip(datagen.WIKITEXT_FILES, (train_rows, val_rows), strict=True):
        (d / name).write_text(json.dumps(rows))
        pins[name] = {"bytes": (d / name).stat().st_size, "sha256": hashlib.sha256((d / name).read_bytes()).hexdigest()}
    return pins


def test_wikitext_rows_are_joined_in_file_order_exactly_as_stored(tmp_path: Path, fake_pyarrow: None) -> None:
    train = ["", " = Title = \n", "\n", " The first line . \n", " second line \n", "no newline at the end"]
    val = [" = V = \n", "\n", " text \n"]
    pins = write_wikitext(tmp_path / "w", train, val)
    texts, prov = datagen.read_wikitext(tmp_path / "w", pinned=pins)
    assert texts["train"] == "".join(train) == " = Title = \n\n The first line . \n second line \nno newline at the end"  # nothing added or removed between the rows
    assert texts["validation"] == " = V = \n\n text \n"
    f = prov["files"]["train-00000-of-00001.parquet"]
    assert f["sha256"] == pins["train-00000-of-00001.parquet"]["sha256"] and f["rows"] == 6 and f["characters"] == len(texts["train"]) and "exactly as stored" in prov["join"]  # the file's SHA-256 goes in the manifest


def test_wikitext_files_that_differ_from_their_pins_or_hold_a_non_string_are_refused(tmp_path: Path, fake_pyarrow: None) -> None:
    pins = write_wikitext(tmp_path / "w", ["a\n"], ["b\n"])
    with pytest.raises(datagen.DatagenStop, match="does not match its pin"):
        datagen.read_wikitext(tmp_path / "w", pinned={**pins, "train-00000-of-00001.parquet": {**pins["train-00000-of-00001.parquet"], "sha256": "0" * 64}})
    with pytest.raises(datagen.DatagenStop, match="does not exist"):
        datagen.read_wikitext(tmp_path / "absent", pinned=pins)
    pins2 = write_wikitext(tmp_path / "w2", ["a\n", None], ["b\n"])
    with pytest.raises(datagen.DatagenStop, match="not a string"):
        datagen.read_wikitext(tmp_path / "w2", pinned=pins2)


def test_the_real_pins_are_the_adr_0004_pins_and_the_module_imports_pyarrow_lazily() -> None:
    from arborlm.fetch_wikitext import FILES

    assert FILES["train-00000-of-00001.parquet"]["sha256"] == "e83889baabc497075506f91975be5fac0d45c5290b6b20582c8cd1e853d0c9f7" and FILES["validation-00000-of-00001.parquet"]["bytes"] == 657_209
    import ast

    for n in ast.parse((ROOT / "studies/p10s2/datagen.py").read_text()).body:
        if isinstance(n, ast.Import | ast.ImportFrom):
            mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
            assert not any(m.split(".")[0] in ("pyarrow", "transformers", "tokenizers", "safetensors", "sacrebleu", "numpy") for m in mods)  # none of them at module level


# --- A-B1/B2: hashes before use; the corpus ----------------------------------------------------------------------------------------------------------------
def test_verify_downloads_rehashes_models_and_the_tatoeba_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    files = {"student/config.json": b'{"hidden_size": 8}', "student/tokenizer.json": b'{"added_tokens": []}'}
    for n, d in files.items():
        (tmp_path / n).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / n).write_bytes(d)
        monkeypatch.setitem(g.SMALL, n, (hashlib.sha1(f"blob {len(d)}\0".encode() + d, usedforsecurity=False).hexdigest(), len(d)))  # noqa: S324
    for n in g.TATOEBA_NAMES:
        (tmp_path / n).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / n).write_bytes(f"t {n}".encode())
    import json

    fr = {"session_date": "2026-11-16", "started": "s", "finished": "f", "tatoeba_recorded_at_first_download": {Path(n).name: g.sha256_file(tmp_path / n) for n in g.TATOEBA_NAMES}}
    (tmp_path / "fetch_record.json").write_text(json.dumps(fr))
    rec_path = tmp_path / "records" / "tatoeba_session.json"
    out = datagen.verify_downloads(tmp_path, rec_path, names=list(files), require_committed=False)
    assert set(out["models"]) == set(files) and out["tatoeba"]["status"].startswith("written") and rec_path.exists()
    again = datagen.verify_downloads(tmp_path, rec_path, names=list(files), require_committed=False)
    assert again["tatoeba"]["status"].startswith("verified")
    (tmp_path / "student/tokenizer.json").write_bytes(b'{"added_tokens": [1]}')
    with pytest.raises(g.FetchRefused, match="not the constant"):
        datagen.verify_downloads(tmp_path, rec_path, names=list(files), require_committed=False)
    (tmp_path / "student/tokenizer.json").write_bytes(files["student/tokenizer.json"])
    (tmp_path / "tatoeba/deu_sentences.tsv.bz2").write_bytes(b"another export")
    with pytest.raises(g.FetchRefused, match="differs from the frozen"):
        datagen.verify_downloads(tmp_path, rec_path, names=list(files), require_committed=False)
    assert set(datagen.model_names()) == {s.name for s in g.primary_sources() if s.kind != "tatoeba"}


def write_tatoeba(d: Path, *, swapped: bool = False) -> dict[str, Any]:
    eng = {1: "Hello.", 2: "Good day.", 3: "Bye."}
    deu = {10: "Hallo.", 11: "Guten Tag."}
    fra = {20: "Salut.", 21: "Bonjour."}

    def sent(lang: str, m: dict[int, str], extra: str = "") -> bytes:
        return bz2.compress(("".join(f"{i}\t{lang}\t{t}\n" for i, t in m.items()) + extra).encode())

    def links(rows: list[tuple[int, int]], sw: bool = False) -> bytes:
        return bz2.compress("".join(f"{b}\t{a}\n" if sw else f"{a}\t{b}\n" for a, b in rows).encode())

    payload = {
        "eng_sentences": sent("eng", eng, "bad line\n"), "deu_sentences": sent("deu", deu), "fra_sentences": sent("fra", fra),
        "eng_deu_links": links([(1, 10), (2, 11)], swapped), "eng_fra_links": links([(1, 20), (2, 21), (3, 21)]),
        "deu_eng_links": links([(10, 1), (11, 2), (11, 3)]), "fra_eng_links": links([(20, 1), (21, 2)]),
    }  # fmt: skip
    (d / "tatoeba").mkdir(parents=True, exist_ok=True)
    rec: dict[str, Any] = {"files": {}}
    for k, b in payload.items():
        name = f"tatoeba/{k}.tsv.bz2"
        (d / name).write_bytes(b)
        rec["files"][name] = {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}
    return rec


def test_the_corpus_is_read_from_the_verified_bytes_with_counts_resolution_and_symmetry(tmp_path: Path) -> None:
    rec = write_tatoeba(tmp_path)
    corpus, info = datagen.load_corpus(tmp_path, rec)
    assert corpus.eng[1] == "Hello." and corpus.links_de == [(1, 10), (2, 11)] and info["parse"]["eng_sentences"] == {"lines": 4, "kept": 3, "malformed": 1, "extra_tabs": 0}
    assert info["link_resolution"]["eng_deu"]["share_resolved"] == 1.0 and info["link_resolution"]["deu_eng"]["ok"]
    assert info["link_symmetry"]["eng_deu"] == {"english_ids_forward": 2, "english_ids_backward": 3, "only_forward": 0, "only_backward": 1}  # English id 3 has a link in one direction only
    assert info["link_symmetry"]["eng_fra"] == {"english_ids_forward": 3, "english_ids_backward": 2, "only_forward": 1, "only_backward": 0}
    rec["files"]["tatoeba/eng_sentences.tsv.bz2"]["sha256"] = "0" * 64  # changed after it was frozen
    with pytest.raises(datagen.DatagenStop, match="does not hash to the frozen record as read"):
        datagen.load_corpus(tmp_path, rec)


def test_a_link_file_with_swapped_columns_stops_the_step(tmp_path: Path) -> None:
    from studies.p10s2.data import LinkFormatError

    rec = write_tatoeba(tmp_path, swapped=True)
    with pytest.raises(LinkFormatError, match="swapped order resolves"):
        datagen.load_corpus(tmp_path, rec)


# --- A-M7 and the ruling: the filter score from transition scores ------------------------------------------------------------------------------------
def test_the_score_is_recomputed_from_transition_scores_with_the_eos_token_counted() -> None:
    pad, eos = 9, 0
    generated = torch.tensor([[5, 6, eos, pad, pad], [7, eos, pad, pad, pad], [1, 2, 3, 4, eos]])
    trans = torch.tensor([[-1.0, -2.0, -3.0, 0.0, 0.0], [-0.5, -0.5, 0.0, 0.0, 0.0], [-0.1, -0.1, -0.1, -0.1, -0.6]])
    mine = datagen.recompute_sequence_scores(trans, generated, pad)
    assert mine == pytest.approx([-6.0 / 3, -1.0 / 2, -1.0 / 5])  # the EOS token is one of the counted tokens (length penalty 1)
    exact = datagen.compare_scores(mine, [-2.0, -0.5, -0.2])
    assert exact["ok"] and exact["max_abs_difference"] < 1e-6 and exact["n"] == 3
    excl_eos = datagen.compare_scores(mine, [-6.0 / 2, -1.0 / 1, -1.0 / 4])  # a library that left the EOS token out of the length would differ
    assert not excl_eos["ok"] and excl_eos["max_abs_difference"] > 0.5
    assert datagen.SCORE_TOLERANCE == 1e-5 and not datagen.compare_scores([0.0], [2e-5])["ok"] and datagen.compare_scores([0.0], [5e-6])["ok"]
    assert datagen.recompute_sequence_scores(torch.zeros(1, 3), torch.full((1, 3), pad), pad) == [0.0]  # an empty hypothesis does not divide by zero


def test_bos_and_decoding_conventions_are_recorded_from_both_files() -> None:
    cfg = {"add_bos_token": False, "clean_up_tokenization_spaces": False, "model_max_length": 8192}
    assert datagen.bos_conventions(cfg, [5, 6], 3) == {"add_bos_token": False, "clean_up_tokenization_spaces": False, "probe_ids": [5, 6], "bos_prepended_by_default": False}
    assert datagen.bos_conventions({}, [3, 6], 3)["bos_prepended_by_default"] is True and datagen.bos_conventions({}, [3], 3)["add_bos_token"] is None


# --- the pre-freeze checks that datagen relies on (prefreeze.py) ----------------------------------------------------------------------------------------
def test_the_dry_bundle_carries_the_tokenization_checks_the_timing_items_the_tokenizer_record_and_the_seed_table() -> None:
    core.reset_seed_record()
    bundle, rec = standins.build_synthetic_bundle(replicates=1)
    t = rec["tokenization"]
    assert t["required_ok"] and tokenization_required_ok(rec) and t["a_prompts"]["n"] > 0 and t["a_icl_prompts"]["n"] > 0 and t["a_training_rows"]["n"] > 0 and t["b_roundtrip"]["n"] > 0
    assert set(bundle.extra["timing_items"]) == {"E_A", "E_B"} and all(len(v) == min(core.CFG["budget"]["timing_items"], len(bundle.panels[k])) for k, v in bundle.extra["timing_items"].items())
    assert len(rec["tokenizer_record"]["A"]["sentences"]) == 100 and rec["tokenizer_record"]["A"]["records"] is None  # a synthetic stand-in has no tokenizer; the real teachers do
    assert len(bundle.extra["seed_table"]) == 56 and bundle.extra["provenance"] == {} and rec["outputs_with_newline"] == {"A": 0, "B": 0}
    assert not tokenization_required_ok({}) and not tokenization_required_ok({"tokenization": {"required_ok": False}})
    core.reset_seed_record()


def test_the_world_carries_the_stored_timing_items() -> None:
    from tests.test_p10s2_support import dry_world  # the cached synthetic world

    world, _ = dry_world()
    assert set(world.timing_items) == {"E_A", "E_B"} and all(v == sorted(set(v)) for v in world.timing_items.values())


class MergingTok:
    """A tokenizer whose whole-string ids differ from the concatenation of segment ids: a newline merges with the word that follows it, as no pre-tokenizer of the real model does."""

    bos_id: int | None = None
    vocab_size = 100000

    def encode(self, text: str) -> list[int]:
        import re

        return [zlib.crc32(p.encode()) % 99991 for p in re.findall(r"\n?\w+:?|\n|[^\w\n]+", text)]

    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        import re

        ms = list(re.finditer(r"\n?\w+:?|\n|[^\w\n]+", text))
        return [zlib.crc32(m.group(0).encode()) % 99991 for m in ms], [(m.start(), m.end()) for m in ms]

    def decode(self, ids: list[int]) -> str:
        return ""

    def token_bytes(self) -> list[bytes]:
        return [b""] * 100000


def test_a_prompt_mismatch_makes_required_ok_false() -> None:
    from studies.p10s2.data import Item, TrainItem

    tok = MergingTok()
    bank = ExampleBank()
    item = Item("red blue green", "red blue green", {"A": ("rot blau grün",), "B": ("rouge",)}, 0)
    acc = {c: [TrainItem("red blue green", "red blue green", "x", -1)] for c in core.TASKS}
    for c in core.TASKS:
        bank.build_from_tokenizer(tok, {"red": 0, "blue": 1, "green": 2}, c, item.en, None)
        bank.build_from_tokenizer(tok, {"red": 0, "blue": 1, "green": 2}, c, item.en, "x")
    part = types.SimpleNamespace(panels={"E_A": [item], "E_B": [item]}, gold_pool={"A": [], "B": []})
    dec = tokenization.ByteDecoder(tok.token_bytes())
    t = tokenization_checks(tok, dec, bank, acc, {c: [] for c in core.TASKS}, part, {"A": {}, "B": {}})  # type: ignore[arg-type]
    assert t["a_prompts"]["mismatch_count"] > 0 and not t["required_ok"] and not tokenization_required_ok({"tokenization": t})


def test_the_teacher_tokenizer_record_must_be_reproduced() -> None:
    class T:
        name, revision = "t", "r"

        def __init__(self, shift: int) -> None:
            self.shift = shift

        def translate(self, sources: Any) -> Any:
            return []

        def tokenizer_record(self, sentences: list[str]) -> list[dict[str, Any]]:
            return [{"sentence": s, "source_ids": [len(s) + self.shift]} for s in sentences]

    recs = tokenizer_records({"A": T(0), "B": T(0)}, {"A": ["x", "yy"], "B": ["zzz"]})  # type: ignore[arg-type]
    assert recs["A"]["records"] == [{"sentence": "x", "source_ids": [1]}, {"sentence": "yy", "source_ids": [2]}] and recs["B"]["teacher"] == "t"
    assert verify_tokenizer_record(T(0), recs["A"]) == {"ok": True, "n": 2}  # type: ignore[arg-type]
    assert verify_tokenizer_record(T(1), recs["A"])["ok"] is False  # a later teacher run that tokenizes differently does not verify
    assert verify_tokenizer_record(object(), recs["A"])["ok"] is False  # type: ignore[arg-type]


def test_equivalence_is_verified_at_every_read_layer() -> None:
    from tests.test_p10s2_support import dry_world

    world, _ = dry_world()
    assert equivalence.verify_all(world.student, {})["ok"] is False  # nothing recorded: not a pass
    assert core.READ_LAYERS == (4, 12)  # the layers calibration may choose: the record is made for both


# --- the data-generation step goes through the study ledger's measure and a guard ---------------------------------------------------------------------------
def test_datagen_is_measured_on_the_study_ledger_with_a_start_marker_and_an_end_entry_even_on_failure(tmp_path: Path) -> None:
    led = Ledger(tmp_path / "ledger.jsonl")
    with datagen.charged_stage(led, 3600.0) as sc:
        assert [e["status"] for e in led.entries()] == ["started"] and led.entries()[0]["kind"] == "datagen"  # the start marker is written before the step does anything
        sc.tick("x")
    assert [e["status"] for e in led.entries()] == ["started", "completed"]
    with pytest.raises(RuntimeError, match="boom"), datagen.charged_stage(led, 3600.0):
        raise RuntimeError("boom")
    assert [e["status"] for e in led.entries()][-1] == "failed" and led.unfinished() == []
    with pytest.raises(datagen.StageCapExceeded, match="less than the stage cap"):
        with datagen.charged_stage(Ledger(tmp_path / "small.jsonl"), 37 * 3600.0):
            pass


def test_the_datagen_guard_stops_the_step_at_its_wall_clock_cap_and_the_ledger_is_still_charged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    led = Ledger(tmp_path / "ledger.jsonl")
    monkeypatch.setitem(core.CFG["budget"], "watchdog_interval_seconds", 0.02)
    t0 = time.perf_counter()
    with pytest.raises(datagen.StageCapExceeded, match="guard stopped"):
        with datagen.charged_stage(led, 0.3, guard=True):
            while True:
                time.sleep(0.01)
    assert time.perf_counter() - t0 < 10 and [e["status"] for e in led.entries()][-1] == "failed"
    assert led.total_hours() > 0 and led.unfinished() == []


def test_the_fetch_step_and_the_datagen_main_charge_the_one_study_ledger() -> None:
    src_fetch = (Path(ledger.__file__).parent / "fetch.py").read_text()
    src_gen = (Path(ledger.__file__).parent / "datagen.py").read_text()
    assert 'Ledger().measure("fetch"' in src_fetch and "from .ledger import Ledger" in src_gen and "led = Ledger()" in src_gen and "importlib.import_module(f\"{__package__}.ledger\")" not in src_gen
