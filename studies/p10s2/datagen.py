# ruff: noqa: E501
"""The data-generation step (ADR-0022 section 14.2): the only place where packages outside the lock are used. WRITTEN, NOT EXECUTED, and not imported by any test.

Run (once, before the freeze, offline after the downloads, and only after the human lead's confirmation of the package wheels with sizes is recorded):
``uv run --locked --with-requirements studies/p10s2/requirements-datagen.txt python -m studies.p10s2.datagen --downloads DIR --out DIR``.
``uv.lock`` and ``pyproject.toml`` are untouched. The imports of ``transformers``, ``tokenizers``, ``safetensors`` and ``sacrebleu`` are inside functions so that the module imports on the locked environment.

Steps: (1) hash checks of every downloaded file; (2) conversion of the pinned student weights to a plain FP32 torch file; (3) the student equivalence test against the reference implementation on a fixed
256-token WikiText-2 train text; (4) token ids of every text segment with the conventions and checks (a)-(e); (5) teacher loading (SHA-256 check, weights-only load, local configuration files only), the
100-sentence tokenizer record per teacher, and generation with beam scores; outputs on evaluation panels are stored and hashed and not scored before the registered run; (6) the chrF cross-check against
sacrebleu. The study's own code (``prefreeze.build_bundle``) does everything between the interfaces; this module only supplies the real objects behind them.

Points to verify at run time (the ADR names them): that Marian loading accepts the pinned German repository despite its tokenizer configuration; that the Hugging Face ``sequences_scores`` of beam search
equals the sum of the token log-probabilities of the returned hypothesis divided by its token count (section 5.3), or else that the score is recomputed from the token scores; the column format of the link
files; the BOS default of the student's tokenizer for this model (read from the pinned files and recorded).
"""

import argparse
import importlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import torch

from arborlm.io import write_json

from . import core, equivalence, fetch_guard
from .data import Sizes, parse_links, parse_sentences
from .model import StudentConfig, build_student, convert_hf_state_dict, load_plain_state
from .prefreeze import WindowSpec, build_bundle
from .text import chrf_item, normalize
from .tokenization import ByteDecoder, check_decoder, check_roundtrip, random_id_sequences
from .worldio import write_bundle


class Corpus:
    def __init__(self, eng: dict[int, str], deu: dict[int, str], fra: dict[int, str], links_de: list[tuple[int, int]], links_fr: list[tuple[int, int]]) -> None:
        self.eng, self.deu, self.fra, self.links_de, self.links_fr = eng, deu, fra, links_de, links_fr


def bytes_to_unicode() -> dict[int, str]:
    """The GPT-2 byte-to-unicode table used by byte-level BPE vocabularies."""
    bs = [*range(ord("!"), ord("~") + 1), *range(ord("¡"), ord("¬") + 1), *range(ord("®"), ord("ÿ") + 1)]
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(bs, cs, strict=True)}


class HFTokenizer:  # pragma: no cover - needs the tokenizers package
    """``ReferenceTokenizer`` over the pinned ``tokenizer.json`` (the ``tokenizers`` package, offline)."""

    def __init__(self, tokenizer_json: Path) -> None:
        tokenizers = importlib.import_module("tokenizers")  # outside the lock: imported only here
        self.tk = tokenizers.Tokenizer.from_file(str(tokenizer_json))
        self.vocab_size = self.tk.get_vocab_size()
        probe = self.tk.encode("a", add_special_tokens=True)
        cfg = json.loads(tokenizer_json.read_text())
        bos = None
        for t in cfg.get("added_tokens", []):
            if t.get("content") == "<|endoftext|>":
                bos = t["id"]
        # the reference default for this model: BOS is prepended only if the tokenizer itself adds it (read from the pinned files and recorded)
        self.bos_id: int | None = probe.ids[0] if bos is not None and len(probe.ids) > 1 and probe.ids[0] == bos else None

    def encode(self, text: str) -> list[int]:
        return list(self.tk.encode(text, add_special_tokens=False).ids)

    def encode_offsets(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        e = self.tk.encode(text, add_special_tokens=False)
        return list(e.ids), [(int(o[0]), int(o[1])) for o in e.offsets]

    def decode(self, ids: Sequence[int]) -> str:
        return str(self.tk.decode(list(ids), skip_special_tokens=False))

    def token_bytes(self) -> list[bytes]:
        inv = {c: b for b, c in bytes_to_unicode().items()}
        vocab = self.tk.get_vocab()
        table: list[bytes] = [b""] * self.vocab_size
        for tok, i in vocab.items():
            try:
                table[i] = bytes(inv[ch] for ch in tok)
            except KeyError:
                table[i] = tok.encode("utf-8")  # a special token decodes to its own text
        return table


class HFReference:  # pragma: no cover - needs transformers
    """``ReferenceModel`` over the Hugging Face ``LlamaForCausalLM`` built from the pinned configuration and the converted weights."""

    def __init__(self, config_json: Path, state: dict[str, torch.Tensor]) -> None:
        tf = importlib.import_module("transformers")  # outside the lock: imported only here
        self.model = tf.LlamaForCausalLM(tf.LlamaConfig.from_json_file(str(config_json))).to(torch.float32).eval()
        self.model.load_state_dict(state, strict=False)
        self.model.tie_weights()

    @torch.no_grad()
    def logits(self, ids: torch.Tensor) -> torch.Tensor:
        out: torch.Tensor = self.model(ids).logits
        return out

    @torch.no_grad()
    def logits_with_injection(self, ids: torch.Tensor, layer: int, vec: torch.Tensor) -> torch.Tensor:
        def hook(_m: Any, _i: Any, out: Any) -> Any:
            h = out[0] if isinstance(out, tuple) else out
            h = h + vec
            return (h, *out[1:]) if isinstance(out, tuple) else h

        handle = self.model.model.layers[layer].register_forward_hook(hook)
        try:
            out: torch.Tensor = self.model(ids).logits
            return out
        finally:
            handle.remove()

    @torch.no_grad()
    def generate(self, ids: torch.Tensor, max_new: int) -> list[int]:
        out = self.model.generate(ids, max_new_tokens=max_new, do_sample=False, num_beams=1, min_new_tokens=max_new)
        return [int(x) for x in out[0, ids.shape[1] :].tolist()]


class MarianTeacher:  # pragma: no cover - needs transformers
    """``Teacher`` over a pinned Marian repository: SHA-256 check, weights-only load, local files only; beam 4, at most 48 new tokens, CPU."""

    def __init__(self, directory: Path, name: str, revision: str, expected_sha256: str) -> None:
        tf = importlib.import_module("transformers")  # outside the lock: imported only here
        self.name, self.revision = name, revision
        state = fetch_guard.load_pickle_weights(directory / "pytorch_model.bin", expected_sha256)
        self.tokenizer = tf.MarianTokenizer.from_pretrained(str(directory), local_files_only=True)
        self.model = tf.MarianMTModel.from_pretrained(str(directory), state_dict=state, local_files_only=True).eval()

    @torch.no_grad()
    def translate(self, sources: Sequence[str]) -> list[tuple[str, float]]:
        out: list[tuple[str, float]] = []
        for i in range(0, len(sources), 32):
            batch = list(sources[i : i + 32])
            enc = self.tokenizer(batch, return_tensors="pt", padding=True)
            gen = self.model.generate(**enc, num_beams=core.CFG["data"]["generation_beam"], max_new_tokens=core.CFG["data"]["generation_new_tokens"], return_dict_in_generate=True, output_scores=True)
            texts = self.tokenizer.batch_decode(gen.sequences, skip_special_tokens=True)
            out += [(t, float(s)) for t, s in zip(texts, gen.sequences_scores.tolist(), strict=True)]  # to verify: length-normalized as section 5.3 defines
        return out


def crosscheck_chrf(pairs: Sequence[tuple[str, Sequence[str]]]) -> dict[str, Any]:  # pragma: no cover - needs sacrebleu
    """The study's chrF-norm against sacrebleu 2.5.1 (chrF2, character n-grams 1-6, no word n-grams, eps_smoothing False) on normalized strings, per item; agreement within 0.001."""
    CHRF = importlib.import_module("sacrebleu.metrics").CHRF  # outside the lock: imported only here
    ch = CHRF(char_order=6, word_order=0, beta=2, eps_smoothing=False)
    worst = 0.0
    for hyp, refs in pairs:
        ref_scores = [ch.sentence_score(normalize(hyp), [normalize(r)]).score / 100.0 for r in refs]
        worst = max(worst, abs(max(ref_scores, default=0.0) - chrf_item(hyp, refs)))
    return {"n": len(pairs), "max_abs_difference": worst, "ok": worst <= core.CFG["scoring"]["crosscheck_tolerance"]}


def run(downloads: Path, out: Path) -> dict[str, Any]:  # pragma: no cover - the registered data-generation step
    """Orchestrate the steps with the real objects. Not executed in this implementation step."""
    g = fetch_guard
    record: dict[str, Any] = {"steps": {}}
    manifest = json.loads((downloads / "fetch_record.json").read_text())
    for name, spec in manifest["files"].items():
        if name in g.LARGE and spec["sha256"] != g.LARGE[name][0]:
            raise ValueError(f"{name} does not match its pinned SHA-256")
    # (2) student conversion
    load_file = importlib.import_module("safetensors.torch").load_file  # outside the lock: imported only here
    cfg = StudentConfig.from_hf_config(json.loads((downloads / "student" / "config.json").read_text()))  # rms_norm_eps from the model's own file
    hf_state = load_file(str(downloads / "student" / "model.safetensors"))
    plain = convert_hf_state_dict(hf_state, cfg)
    student = build_student(cfg)
    load_plain_state(student, plain)
    out.mkdir(parents=True, exist_ok=True)
    torch.save({"cfg": cfg.__dict__, "state": plain}, out / "student_plain_fp32.pt")
    # (3)-(4) tokenizer, equivalence, checks
    tok = HFTokenizer(downloads / "student" / "tokenizer.json")
    wiki_val = (core.ROOT / "data" / "wikitext2" / "wiki.valid.raw").read_text(encoding="utf-8")
    wiki_train = (core.ROOT / "data" / "wikitext2" / "wiki.train.raw").read_text(encoding="utf-8")
    ref = HFReference(downloads / "student" / "config.json", hf_state)
    ids = torch.tensor([tok.encode(wiki_train)[:256]])
    g_vec = core.seeded_generator(core.partition_seeds("registered-data")["random_id_sequences"], "equivalence injection vector", "registered-data")
    vec = torch.randn(cfg.width, generator=g_vec)
    record["steps"]["equivalence"] = equivalence.build_record(student, ref, ids, vec, core.READ_LAYERS[0], [tok.encode(wiki_val)[i : i + 8] for i in range(0, 800, 8)], 8)
    gen = core.partition_gen("registered-data", "random_id_sequences", "test (c) random id sequences")
    dec = ByteDecoder(tok.token_bytes())
    record["steps"]["check_c"] = check_decoder(dec, tok, random_id_sequences(tok.vocab_size, core.CFG["data"]["random_id_sequences"], gen))
    record["steps"]["check_b"] = check_roundtrip([wiki_val[i : i + 80] for i in range(0, 8000, 80)], tok, dec)
    # (5) data
    d = downloads / "tatoeba"
    corpus = Corpus(parse_sentences((d / "eng_sentences.tsv.bz2").read_bytes()), parse_sentences((d / "deu_sentences.tsv.bz2").read_bytes()), parse_sentences((d / "fra_sentences.tsv.bz2").read_bytes()), parse_links((d / "eng_deu_links.tsv.bz2").read_bytes()), parse_links((d / "eng_fra_links.tsv.bz2").read_bytes()))
    rev = {"A": ("opus-mt-en-de", fetch_guard.TEACHER_A[1], "teacher_a"), "B": ("opus-mt-en-fr", fetch_guard.TEACHER_B[1], "teacher_b")}
    teachers = {c: MarianTeacher(downloads / folder, name, revn, fetch_guard.LARGE[f"{folder}/pytorch_model.bin"][0]) for c, (name, revn, folder) in rev.items()}
    bundle, rec = build_bundle(corpus, tok, student, teachers, wiki_val, wiki_train, Sizes.registered(), WindowSpec.registered(), "registered-data", 0)
    bundle.extra["equivalence"] = record["steps"]["equivalence"]  # inside the hash-checked data files (gate G8 reads it from there)
    write_bundle(bundle, out / "bundle")
    write_json(out / "prefreeze_record.json", core.jsonable({**rec, "steps": {k: v for k, v in record["steps"].items() if k != "equivalence"}}))
    return rec


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover
    p = argparse.ArgumentParser(prog="python -m studies.p10s2.datagen")
    p.add_argument("--downloads", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--code-commit", required=True, help="must equal a clean HEAD")
    p.add_argument("--stage-cap-seconds", type=float, required=True)
    a = p.parse_args(argv)
    from . import freeze

    freeze.check_code_commit(core.ROOT, a.code_commit)
    run(Path(a.downloads), Path(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
