# ruff: noqa: E501
"""The real-library smoke exercise of the data-generation step (not a test of the suite, not a charged stage): ``python -m studies.p10s2.datagen --smoke`` run with the same ``PYTHONPATH`` as ``launch/datagen.sh``.

It makes every call into a real library that ``datagen`` makes, on inputs written into this file or read from the first rows of the real files, so that a failure of the real-library path shows here before a charged
attempt is spent: the hash-installed packages and their provenance, the download and Tatoeba-record checks, the WikiText parquet reader, the first lines of the Tatoeba exports, the student's safetensors load
and conversion, the ``tokenizers`` tokenizer with its conventions, offsets, byte table and decoder, the whole-text window cut and example building, the Hugging Face reference model and the equivalence record
at each read layer (with the tensor round trip of the bundle and gate G8's verification), both Marian teachers (load, one beam-search batch with the recomputed score compared to the library's, the tokenizer
record), and sacrebleu's chrF against the study's.

Nothing registered is touched: only test-range seeds (``test`` mode), no registered sampling, fixed literal English sentences, and nothing is written under the data folder (the output is the summary on stdout).
"""

import argparse
import bz2
import json
import sys
import time
import traceback
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import torch

from . import core, datagen, equivalence, fetch_guard
from .data import parse_links_report, parse_sentences_report
from .model import StudentConfig, build_student, convert_hf_state_dict, load_plain_state
from .text import chrf_item
from .tokenization import ByteDecoder, build_example, check_decoder, random_id_sequences
from .windows import cut_windows

SENTENCES = ("I like tea.", "The children are playing in the garden.", "Where is the station?", "She reads a book every evening.")
PARAGRAPH = "The children are playing in the garden. She reads a book every evening, and he likes tea. Where is the station? The train leaves early in the morning."
VOCAB = {"the": 0, "i": 1, "like": 2, "tea": 3, "children": 4, "garden": 5, "book": 6}
FIRST_LINES = 2000


def first_lines(path: Path, count: int = FIRST_LINES) -> bytes:
    """The first ``count`` lines of a bzip2 export, decompressed (the real file's first rows, not the whole file)."""
    out: list[bytes] = []
    with bz2.open(path, "rb") as f:
        for _ in range(count):
            line = f.readline()
            if not line:
                break
            out.append(line)
    return b"".join(out)


class Smoke:
    def __init__(self) -> None:
        self.results: dict[str, Any] = {}
        self.failures: list[str] = []

    def step(self, name: str, fn: Callable[[], Any]) -> Any:
        t0 = time.perf_counter()
        try:
            res = fn()
            self.results[name] = {"ok": True, "seconds": round(time.perf_counter() - t0, 2), "detail": res}
            return res
        except BaseException as e:  # noqa: BLE001 (the smoke reports every real-library failure and goes on)
            self.failures.append(name)
            self.results[name] = {"ok": False, "seconds": round(time.perf_counter() - t0, 2), "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]}
            return None


def run_smoke(downloads: Path, wikitext_dir: Path) -> Smoke:
    s = Smoke()
    seed = core.SEEDS["test_low"] + 800  # a test-range seed: never a registered one

    def env() -> Any:
        datagen.check_requirements_hashed(core.ROOT / datagen.REQUIREMENTS)
        versions = datagen.package_versions()
        datagen.check_installed_pins(versions)
        return {"versions": versions, "provenance": datagen.check_provenance(core.ROOT / datagen.PACKAGES_DIR)}

    s.step("environment (pins, provenance)", env)

    def hashes() -> Any:
        d = datagen.verify_downloads(downloads, core.ROOT / fetch_guard.TATOEBA_RECORD)
        return {"models_verified": len(d["models"]), "tatoeba_files": len(d["tatoeba"]["files"])}

    s.step("download hashes and the Tatoeba record", hashes)

    def wikitext() -> Any:
        texts, prov = datagen.read_wikitext(wikitext_dir)
        import importlib

        pq = importlib.import_module("pyarrow.parquet")
        with pq.ParquetFile(wikitext_dir / datagen.WIKITEXT_FILES[1]) as f:
            first = [r for batch in f.iter_batches(columns=["text"], batch_size=5, use_threads=False) for r in batch.column(0).to_pylist()][:5]
        return {"train_chars": len(texts["train"]), "validation_chars": len(texts["validation"]), "first_rows_are_strings": all(isinstance(r, str) for r in first), "files": list(prov["files"])}

    s.step("WikiText parquet reader (verified, first rows)", wikitext)

    def tatoeba() -> Any:
        out = {}
        for lang in ("eng", "deu", "fra"):
            rows, rep = parse_sentences_report(first_lines(downloads / f"tatoeba/{lang}_sentences.tsv.bz2"), compressed=False)
            out[f"{lang}_sentences"] = {"kept": len(rows), **rep.to_json()}
            assert rows, lang
        links, rep = parse_links_report(first_lines(downloads / "tatoeba/eng_deu_links.tsv.bz2"), compressed=False)
        out["eng_deu_links"] = {"kept": len(links), **rep.to_json()}
        assert links
        return out

    s.step("Tatoeba readers (first lines of the real exports)", tatoeba)

    def student_load() -> Any:
        load_file = __import__("importlib").import_module("safetensors.torch").load_file
        cfg = StudentConfig.from_hf_config(json.loads(fetch_guard.read_verified_bytes(downloads, "student/config.json")))
        fetch_guard.verify_against_constant(downloads / "student/model.safetensors", "student/model.safetensors")
        hf_state = load_file(str(downloads / "student" / "model.safetensors"))
        plain = convert_hf_state_dict(hf_state, cfg)
        student = build_student(cfg)
        load_plain_state(student, plain)
        return {"cfg": cfg, "hf_state": hf_state, "student": student, "summary": {"tensors": len(hf_state), "parameters": sum(p.numel() for p in student.parameters()), "rms_norm_eps": cfg.rms_norm_eps}}

    st = s.step("student: safetensors load, conversion, plain load", student_load)
    if st is not None:
        s.results["student: safetensors load, conversion, plain load"]["detail"] = st["summary"]

    def tokenizer() -> Any:
        tok = datagen.HFTokenizer(downloads)
        ids = tok.encode(PARAGRAPH)
        ids2, offs = tok.encode_offsets(PARAGRAPH)
        assert ids == ids2 and len(offs) == len(ids) and tok.decode(ids) == PARAGRAPH
        table = tok.token_bytes()
        dec = ByteDecoder(table)
        assert dec.decode(ids) == PARAGRAPH
        gen = core.seeded_generator(seed, "smoke: random id sequences", "test")
        check_c = check_decoder(dec, tok, random_id_sequences(tok.vocab_size, 40, gen))
        ex = [build_example(tok, "A", sent, None, VOCAB, f"smoke{i}") for i, sent in enumerate(SENTENCES)]
        return {"tok": tok, "dec": dec, "summary": {"vocab": tok.vocab_size, "conventions": tok.conventions, "paragraph_tokens": len(ids), "check_c": check_c, "examples": len(ex), "example_prompt_len": ex[0].prompt_len if hasattr(ex[0], "prompt_len") else None, "bos_id": tok.bos_id}}

    tk = s.step("tokenizer (encode, offsets, byte table, decoder, conventions, test (c), examples)", tokenizer)
    if tk is not None:
        s.results["tokenizer (encode, offsets, byte table, decoder, conventions, test (c), examples)"]["detail"] = tk["summary"]

    def windows() -> Any:
        assert tk is not None
        wiki_val = (wikitext_dir / datagen.WIKITEXT_FILES[1])
        import importlib

        pq = importlib.import_module("pyarrow.parquet")
        with pq.ParquetFile(wiki_val) as f:
            text = "".join(r for batch in f.iter_batches(columns=["text"], batch_size=500, use_threads=False) for r in batch.column(0).to_pylist())[:40000]  # a slice of the validation file's first rows, to test the cut
        w = cut_windows(tk["tok"], text, VOCAB, 64, 24)
        return {"windows": len(w), "strata": sorted({x.stratum for x in w}), "marker_ends": [x.marker_end for x in w if x.stratum == "marker"][:5]}

    s.step("window cut with real offsets (first rows of the validation text)", windows)

    def equivalence_step() -> Any:
        assert st is not None and tk is not None
        cfg, hf_state, student, tok = st["cfg"], st["hf_state"], st["student"], tk["tok"]
        ref = datagen.HFReference(json.loads(fetch_guard.read_verified_bytes(downloads, "student/config.json")), hf_state)
        ids = torch.tensor([tok.encode(PARAGRAPH)[:40]])
        prompts = [tok.encode(p)[:6] for p in SENTENCES]
        vec = torch.randn(cfg.width, generator=core.seeded_generator(seed + 1, "smoke: equivalence injection vector", "test"))
        layers = {str(layer): equivalence.build_record(student, ref, ids, vec, layer, prompts, 4) for layer in core.READ_LAYERS}
        creation = {k: v["at_creation"] for k, v in layers.items()}
        # the bundle's tensor round trip and gate G8's verification on the real reference record
        from .worldio import _restore_equivalence_tensors, _strip_equivalence_tensors

        extra, tensors = _strip_equivalence_tensors({"equivalence": layers[str(core.READ_LAYERS[0])], "equivalence_layers": layers})
        json.dumps(core.jsonable(extra))  # the record is JSON without the logits
        _restore_equivalence_tensors(extra, tensors)
        verified = equivalence.verify_all(student, extra["equivalence_layers"])
        full_logits_mb = 256 * tok.vocab_size * 4 * 4 / 1e6
        return {"at_creation": creation, "g8_verify_ok": verified["ok"], "g8_layers": {k: {"ok": v["ok"], "greedy": v["greedy_matches_reference"], "cache": v["cache_matches_recomputation"]} for k, v in verified["layers"].items()}, "stored_tensors": sorted(tensors), "full_record_float32_mb_if_256_tokens": round(full_logits_mb)}

    eq = s.step("reference model + equivalence record + G8 verification (both read layers)", equivalence_step)
    if eq is not None and not (eq["g8_verify_ok"] and all(v["logits"]["ok"] and v["injection"]["ok"] for v in eq["at_creation"].values())):
        s.failures.append("equivalence did not pass on the real student")

    def teachers() -> Any:
        out = {}
        for c, (name, revn, folder) in {"A": ("opus-mt-en-de", fetch_guard.TEACHER_A[1], "teacher_a"), "B": ("opus-mt-en-fr", fetch_guard.TEACHER_B[1], "teacher_b")}.items():
            t = datagen.MarianTeacher(downloads, folder, name, revn, lambda _what: None)
            outs = t.translate(list(SENTENCES))
            rec = t.tokenizer_record(list(SENTENCES[:2]))
            out[c] = {"translations": [o[0] for o in outs], "scores": [round(o[1], 4) for o in outs], "first_batch_score_check": t.score_record["first_batch"], "load": t.load_record, "tokenizer_record_rows": len(rec), "generation_config": t.score_record["generation_config"]}
            assert all(isinstance(o[0], str) and o[0] for o in outs) and t.score_record["first_batch"]["ok"]
        return out

    s.step("both Marian teachers (load, one beam batch with the score check, tokenizer record)", teachers)

    def chrf() -> Any:
        pairs = [("Ich mag Tee.", ["Ich mag Tee."]), ("Die Kinder spielen im Garten.", ["Die Kinder spielen im Garten.", "Kinder spielen draußen."]), ("Wo ist der Bahnhof", ["Wo ist der Bahnhof?"])]
        r = datagen.crosscheck_chrf(pairs)
        import importlib

        sm = importlib.import_module("sacremoses")
        moses = sm.MosesPunctNormalizer("en").normalize("Hello,  world !")
        return {"chrf_crosscheck": r, "study_chrf_exact": chrf_item("Ich mag Tee.", ["Ich mag Tee."]), "sacremoses_normalizer": moses}

    s.step("sacrebleu chrF cross-check and sacremoses", chrf)
    return s


def smoke_main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m studies.p10s2.datagen --smoke")
    p.add_argument("--downloads", default=str(core.ROOT / "data" / "p10s2-pre-20261115" / "downloads"))
    p.add_argument("--wikitext-dir", default=str(core.ROOT / "data" / "wikitext2"))
    a = p.parse_args(argv)
    import os

    os.environ["HF_HUB_OFFLINE"] = "1"  # as datagen.run sets them: offline, never setdefault
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    torch.set_num_threads(2)
    s = run_smoke(Path(a.downloads), Path(a.wikitext_dir))
    sys.stdout.write(json.dumps(core.jsonable({"ok": not s.failures, "failures": s.failures, "steps": s.results}), indent=1, default=str) + "\n")
    return 0 if not s.failures else 1


if __name__ == "__main__":
    raise SystemExit(smoke_main())
