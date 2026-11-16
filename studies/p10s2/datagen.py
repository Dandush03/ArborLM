# ruff: noqa: E501
"""The data-generation step (ADR-0022 section 14.2 and the lead's rulings on the implementation audits): the only place where packages outside the lock are used. WRITTEN, NOT EXECUTED by this
implementation; its pure helpers are tested on synthetic files, and the module is imported by tests only for those.

Run (once, before the freeze, offline after the downloads, with the wheels resolved with hashes and installed with hashes required):
``uv run --locked --extra pilot --with-requirements studies/p10s2/requirements-datagen.txt python -m studies.p10s2.datagen --downloads DIR --out DIR --code-commit HEAD --stage-cap-seconds N``.
``uv.lock`` and ``pyproject.toml`` are untouched. The imports of ``transformers``, ``tokenizers``, ``safetensors``, ``sacrebleu`` and ``pyarrow`` are inside functions so that the module imports on the
locked environment (``pyarrow`` is the locked one: the ``pilot`` extra of ``uv.lock``).

Steps, in order, each of which stops the step on its stop condition and each of which leaves its record (a failed step's record is kept):

1. hash checks of every downloaded file: every model file, small ones included, is re-hashed from disk against the constant in ``fetch_guard`` (git-blob SHA-1 for the small files, SHA-256 for the large
   ones) and again immediately before each use; the Tatoeba exports are re-hashed against the tracked record (written and committed after the first session, ``fetch_guard.freeze_tatoeba_record``); the WikiText
   parquet files against the pins of ADR-0004 (``arborlm.fetch_wikitext.FILES``);
2. conversion of the pinned student weights to a plain FP32 torch file, whose SHA-256 is recorded;
3. the student equivalence test at each read layer (4 and 12): maximum absolute logit difference, top-1, the injection at block L with the fixed vector drawn on its own listed seed 220912;
4. token ids of every text segment and the tests (a) and (b) on every reference and teacher output (``prefreeze.tokenization_checks``), (c) on 1,000 random id sequences (220910), (d) and (e) on the
   WikiText *train* text (the validation text is reserved for GEN, section 6.4); the link files' column order, resolution and symmetry (the count of one-direction English ids is reported);
5. teacher loading (digest check, weights-only load, local configuration files only), the 100-sentence tokenizer record per teacher (220909), and generation with beam scores recomputed from transition
   scores (length penalty 1, the end-of-sequence token counted) and asserted equal to the library's on the first batch; the step stops if they differ;
6. the chrF cross-check against ``sacrebleu`` on the 1,000 pairs of Q (stop if the difference exceeds 0.001).

The step is charged to the study ledger and honours its stage cap (``charged_stage``). The study ledger is ``studies/p10s2/ledger.py``: ``main`` passes ``Ledger()`` and the step runs under
``Ledger.measure("datagen")`` (a start marker first, so a killed step is still charged) and a ``stages.StageGuard`` (the wall-clock cap enforced by a watchdog, not only between steps). A ledger-like object
that has only ``charge(stage, seconds)`` and ``remaining()`` (hours) is accepted for tests.
"""

import argparse
import contextlib
import gc
import importlib
import json
import os
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import torch

from arborlm.io import write_json

from . import core, equivalence, fetch_guard, output
from .data import (
    Sizes,
    check_link_resolution,
    link_symmetry,
    parse_links_report,
    parse_sentences_report,
)
from .model import StudentConfig, build_student, convert_hf_state_dict, load_plain_state
from .prefreeze import WindowSpec, build_bundle
from .text import chrf_item, normalize
from .tokenization import ByteDecoder, check_decoder, random_id_sequences
from .worldio import write_bundle

REQUIREMENTS = Path("studies/p10s2/requirements-datagen.txt")
PLAIN_STUDENT = "student_plain_fp32.pt"
SCORE_TOLERANCE = 1e-5  # the recomputed beam score against the library's, first batch (audit A-M7, ruling)
WIKITEXT_FILES = ("train-00000-of-00001.parquet", "validation-00000-of-00001.parquet")


class DatagenStop(RuntimeError):
    """A stop condition of the data-generation step: its record is kept and the work returns to the lead."""


class StageCapExceeded(DatagenStop):
    """The stage cap (seconds) of the step was reached, or the study ledger has less remaining than the cap."""


class RegisteredTestStop(DatagenStop):
    """A stop on a registered test of the step (a tokenization test, the student equivalence test, the filter-score assertion, the chrF cross-check, G9 of the data step, too few GEN windows): not an engineering
    error. It returns to the lead; the step is not re-run until the lead has released it (re-check A, R16)."""


class ScoreMismatch(RegisteredTestStop):
    """The recomputed beam score differs from the library's sequence score on the first batch (ruling on A-M7)."""


# --- the study ledger and the stage cap ----------------------------------------------------------------------------------------------------------
class LedgerLike(Protocol):
    """What this step needs of the single study ledger (``studies/p10s2/ledger.py``, built by lane B): charge wall seconds to a stage, and the hours still available under the cap."""

    def charge(self, stage: str, seconds: float) -> None: ...
    def remaining(self) -> float: ...


@dataclass
class StageClock:
    cap_seconds: float
    clock: Callable[[], float]
    started: float

    def elapsed(self) -> float:
        return self.clock() - self.started

    def tick(self, what: str = "") -> None:
        """Called between the long steps (and between teacher batches): past the cap, the step stops."""
        if self.elapsed() > self.cap_seconds:
            raise StageCapExceeded(f"the stage cap of {self.cap_seconds:.0f} s was reached after {self.elapsed():.0f} s ({what})")


@contextmanager
def charged_stage(led: LedgerLike, stage_cap_seconds: float, *, stage: str = "datagen", clock: Callable[[], float] = time.monotonic, guard: bool = False) -> Iterator[StageClock]:
    """Charge the wall time of the enclosed block to the study ledger, whether it completes or fails, and refuse to start if the ledger has less than the stage cap remaining.

    A ledger with ``measure`` (the study ledger) is used through it: the start marker is written before the step does anything, the end entry whether it completes or raises. With ``guard`` the block also
    runs under ``stages.StageGuard`` and a cap reached by the watchdog is raised as ``StageCapExceeded``."""
    if stage_cap_seconds <= 0:
        raise StageCapExceeded("a positive stage cap is required")
    if led.remaining() * 3600.0 < stage_cap_seconds:
        raise StageCapExceeded(f"refused: the study ledger has {led.remaining():.3f} h remaining, less than the stage cap of {stage_cap_seconds / 3600.0:.3f} h")
    sc = StageClock(stage_cap_seconds, clock, clock())
    measure = getattr(led, "measure", None)
    with contextlib.ExitStack() as stack:
        if callable(measure):
            stack.enter_context(measure(stage, process="data generation", cap_seconds=stage_cap_seconds))  # a killed step is charged at most its cap (F4)
        else:
            stack.callback(lambda: led.charge(stage, sc.elapsed()))
        if guard:
            from .stages import CapReached, MemoryLimitExceeded, StageGuard

            try:
                with StageGuard(stage, cap_seconds=stage_cap_seconds, memory_limit_bytes=int(float(core.CFG["budget"]["memory_per_worker_gib"]) * 2**30)):
                    yield sc
            except (CapReached, MemoryLimitExceeded) as e:
                raise StageCapExceeded(f"the guard stopped the step: {e}") from e
        else:
            yield sc


# --- the requirements file -------------------------------------------------------------------------------------------------------------------
def unhashed_requirements(text: str) -> list[str]:
    """The requirement lines of a requirements file that carry no ``--hash=sha256:`` (continuation lines are joined). The file must be resolved with hashes and installed with hashes required."""
    logical: list[str] = []
    cur = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cur += " " + line.rstrip("\\").strip()
        if not line.endswith("\\"):
            logical.append(cur.strip())
            cur = ""
    if cur.strip():
        logical.append(cur.strip())
    return [ln.split()[0] for ln in logical if not ln.startswith("-") and "--hash=sha256:" not in ln]


def option_lines(text: str) -> list[str]:
    """Logical lines that are options (``--hash`` continuations belong to their pin): ``-e``, ``-r``, an index URL ... (re-check A, R2: refused)."""
    logical: list[str] = []
    cur = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cur += " " + line.rstrip("\\").strip()
        if not line.endswith("\\"):
            logical.append(cur.strip())
            cur = ""
    return [ln for ln in logical if ln.startswith("-")]


def check_requirements_hashed(path: Path) -> int:
    opts = option_lines(path.read_text())
    if opts:
        raise DatagenStop(f"refused: {path} has option lines other than --hash: {opts[:3]}")
    bad = unhashed_requirements(path.read_text())
    if bad:
        raise DatagenStop(f"refused: {path} pins without a hash: {bad}; resolve it once with hashes (uv pip compile --generate-hashes, Python 3.12, torch 2.8.0) and install with hashes required")
    return len([ln for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith(("#", " ", "-"))])


# --- the local WikiText parquet files (audit A-B3) ----------------------------------------------------------------------------------------------
def read_wikitext(directory: Path, *, pinned: dict[str, dict[str, Any]] | None = None) -> tuple[dict[str, str], dict[str, Any]]:
    """The general-language text: the local parquet copy (ADR-0004 acquisition) read with the locked ``pyarrow`` (imported here), each file verified against its pinned size and SHA-256 first, the rows of
    the ``text`` column concatenated in file order exactly as stored, with nothing added or removed between them. Returns the two texts (``train``, ``validation``) and the provenance record that goes into
    the data manifest (file SHA-256, bytes, rows, characters)."""
    if pinned is None:
        pinned = dict(importlib.import_module("arborlm.fetch_wikitext").FILES)  # the pins of ADR-0004
    pq = importlib.import_module("pyarrow.parquet")  # the locked pyarrow (extra "pilot")
    texts: dict[str, str] = {}
    prov: dict[str, Any] = {"join": "the rows of the text column concatenated in file order, each exactly as stored; nothing added or removed", "files": {}}
    for split, name in (("train", WIKITEXT_FILES[0]), ("validation", WIKITEXT_FILES[1])):
        path = directory / name
        if not path.is_file():
            raise DatagenStop(f"refused: {path} does not exist")
        pin = pinned[name]
        digest = fetch_guard.sha256_file(path)
        if path.stat().st_size != pin["bytes"] or digest != pin["sha256"]:
            raise DatagenStop(f"refused: {name} does not match its pin (ADR-0004): {path.stat().st_size} bytes, SHA-256 {digest}")
        rows: list[str] = []
        with pq.ParquetFile(path) as f:
            for batch in f.iter_batches(columns=["text"], use_threads=False):
                rows.extend(batch.column(0).to_pylist())
        if not all(isinstance(r, str) for r in rows):
            raise DatagenStop(f"refused: {name} holds a row that is not a string")
        texts[split] = "".join(rows)
        prov["files"][name] = {"sha256": digest, "bytes": path.stat().st_size, "rows": len(rows), "characters": len(texts[split])}
    return texts, prov


# --- hashes of everything downloaded ------------------------------------------------------------------------------------------------------------
def model_names(*, fallback: bool = False) -> list[str]:
    return [s.name for s in fetch_guard.sources(fallback=fallback) if s.kind in ("model-large", "model-small", "fallback-model")]


def verify_downloads(downloads: Path, record_path: Path, *, root: Path | None = None, names: Sequence[str] | None = None, require_committed: bool = True) -> dict[str, Any]:
    """Step 1: every model file against its constant in reviewed code, the Tatoeba files against the tracked record (written at the first use, to be committed)."""
    digests = fetch_guard.verify_tree(downloads, list(names) if names is not None else model_names())
    tatoeba = fetch_guard.freeze_tatoeba_record(downloads, record_path, root=root, require_committed=require_committed)
    return {"models": digests, "tatoeba": tatoeba}


@dataclass
class Corpus:
    eng: dict[int, str]
    deu: dict[int, str]
    fra: dict[int, str]
    links_de: list[tuple[int, int]]
    links_fr: list[tuple[int, int]]


def load_corpus(downloads: Path, tatoeba: dict[str, Any]) -> tuple[Corpus, dict[str, Any]]:
    """Read the seven Tatoeba exports (each file's bytes are compared with the recorded digest as read), parse them with the malformed-line counts, check the link files' column order and
    resolution (stop below the share stated in ``data``), and check the symmetry of the ``eng/`` link files against the ``deu/`` and ``fra/`` ones (the link files are approved): the count of English
    ids that have a link in one direction only is reported."""
    import hashlib

    def read(name: str) -> bytes:
        data = (downloads / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != tatoeba["files"][name]["sha256"]:
            raise DatagenStop(f"refused: {name} does not hash to the frozen record as read")
        return data

    rep: dict[str, Any] = {}
    sents: dict[str, dict[int, str]] = {}
    for lang in ("eng", "deu", "fra"):
        sents[lang], r = parse_sentences_report(read(f"tatoeba/{lang}_sentences.tsv.bz2"))
        rep[f"{lang}_sentences"] = r.to_json()
    links: dict[str, list[tuple[int, int]]] = {}
    for key in ("eng_deu_links", "eng_fra_links", "deu_eng_links", "fra_eng_links"):
        links[key], r = parse_links_report(read(f"tatoeba/{key}.tsv.bz2"))
        rep[key] = r.to_json()
    resolution = {
        "eng_deu": check_link_resolution(links["eng_deu_links"], sents["eng"], sents["deu"], "eng-deu_links"),
        "eng_fra": check_link_resolution(links["eng_fra_links"], sents["eng"], sents["fra"], "eng-fra_links"),
        "deu_eng": check_link_resolution([(b, a) for a, b in links["deu_eng_links"]], sents["eng"], sents["deu"], "deu-eng_links (columns swapped for the check)"),
        "fra_eng": check_link_resolution([(b, a) for a, b in links["fra_eng_links"]], sents["eng"], sents["fra"], "fra-eng_links (columns swapped for the check)"),
    }
    symmetry = {"eng_deu": link_symmetry(links["eng_deu_links"], links["deu_eng_links"]), "eng_fra": link_symmetry(links["eng_fra_links"], links["fra_eng_links"])}
    return Corpus(sents["eng"], sents["deu"], sents["fra"], links["eng_deu_links"], links["eng_fra_links"]), {"parse": rep, "link_resolution": resolution, "link_symmetry": symmetry}


# --- beam scores (audit A-M7 and the ruling) ----------------------------------------------------------------------------------------------------
def recompute_sequence_scores(transition: torch.Tensor, generated: torch.Tensor, pad_id: int) -> list[float]:
    """The §5.3 score from transition scores: the sum of the token log-probabilities of the returned hypothesis divided by its token count, the end-of-sequence token counted, length penalty 1. The
    count is the number of generated positions that are not padding (the position after the last token of a finished hypothesis is padding with a transition score of 0)."""
    mask = generated != pad_id
    sums = (transition * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1)
    return [float(x) for x in (sums / counts).tolist()]


PROGRESS_EVERY = 100  # a progress line (elapsed time, resident set, peak) every this many teacher batches


def streaming_transition_scores(sequences: torch.Tensor, scores: Sequence[torch.Tensor], beam_indices: torch.Tensor, vocab_size: int) -> torch.Tensor:
    """``compute_transition_scores(sequences, scores, beam_indices, normalize_logits=False)`` of transformers 4.57.1, one generation step at a time: the library stacks every step's (beams x vocab) score
    tensor into one copy (a 48-step batch of 32 sources at beam 4 and a 58,101-token vocabulary: 1.4 GB beside the 1.4 GB the steps already hold) and gathers from it; here each step is gathered where it is.
    The values are the same floats (a gather copies), so the explicit sequence score is unchanged bit for bit (tested against the library's own function)."""
    mask = beam_indices < 0
    max_len = int((1 - mask.long()).sum(-1).max())
    idx = beam_indices.clone()[:, :max_len]
    mask = mask[:, :max_len]
    idx[mask] = 0
    idx = sequences[:, sequences.shape[-1] - max_len :] + idx * vocab_size
    out = torch.empty(idx.shape, dtype=scores[0].dtype, device=scores[0].device)
    for j in range(max_len):
        out[:, j] = scores[j].reshape(-1).gather(0, idx[:, j])
    out[mask] = 0
    return out


def current_rss_mib() -> float:
    """The resident set of this process now (``ru_maxrss`` is only the high-water mark); 0.0 where ``ps`` is unavailable."""
    import subprocess

    try:
        return int(subprocess.run(["ps", "-o", "rss=", "-p", str(os.getpid())], capture_output=True, text=True, check=True).stdout.strip()) / 1024.0
    except (OSError, ValueError, subprocess.CalledProcessError):
        return 0.0


def peak_rss_mib() -> float:
    import resource

    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return (r if sys.platform == "darwin" else r * 1024) / 2**20


def release_freed_memory() -> None:
    """Give the allocator's free pages back to the operating system (macOS ``malloc_zone_pressure_relief``; a no-op elsewhere). A freed Python or torch object returns its memory to the allocator, not to the
    system, so the resident set the guard reads stays at the high-water mark of the earlier steps; this lowers the resident set, it changes no value."""
    if sys.platform != "darwin":
        return
    import ctypes

    try:
        fn = ctypes.CDLL(None).malloc_zone_pressure_relief
        fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
        fn.restype = ctypes.c_size_t
        fn(None, 0)
    except (OSError, AttributeError):
        pass



def compare_scores(recomputed: Sequence[float], library: Sequence[float], tolerance: float = SCORE_TOLERANCE) -> dict[str, Any]:
    diffs = [abs(a - b) for a, b in zip(recomputed, library, strict=True)]
    worst = max(diffs, default=0.0)
    return {"n": len(diffs), "max_abs_difference": worst, "tolerance": tolerance, "ok": worst <= tolerance}


def bos_conventions(tokenizer_config: dict[str, Any], probe_ids: Sequence[int], bos_token_id: int | None) -> dict[str, Any]:
    """What the pinned ``tokenizer_config.json`` says about BOS and decoding, beside what the tokenizer actually did on a probe (recorded; audit minor 10)."""
    return {
        "add_bos_token": tokenizer_config.get("add_bos_token"), "clean_up_tokenization_spaces": tokenizer_config.get("clean_up_tokenization_spaces"), "probe_ids": list(probe_ids),
        "bos_prepended_by_default": bool(bos_token_id is not None and len(probe_ids) > 1 and probe_ids[0] == bos_token_id),
    }  # fmt: skip


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
    """``ReferenceTokenizer`` over the pinned ``tokenizer.json`` (the ``tokenizers`` package, offline). The file's bytes are verified against the constant in reviewed code and parsed from those bytes."""

    def __init__(self, downloads: Path) -> None:
        tokenizers = importlib.import_module("tokenizers")  # outside the lock: imported only here
        raw = fetch_guard.read_verified_bytes(downloads, "student/tokenizer.json")
        cfg_conf = json.loads(fetch_guard.read_verified_bytes(downloads, "student/tokenizer_config.json"))
        self.tk = tokenizers.Tokenizer.from_str(raw.decode("utf-8"))
        self.vocab_size = self.tk.get_vocab_size()
        probe = self.tk.encode("a", add_special_tokens=True)
        cfg = json.loads(raw)
        bos = None
        for t in cfg.get("added_tokens", []):
            if t.get("content") == "<|endoftext|>":
                bos = t["id"]
        # the reference default for this model: BOS is prepended only if the tokenizer itself adds it (read from the pinned files and recorded)
        self.bos_id: int | None = probe.ids[0] if bos is not None and len(probe.ids) > 1 and probe.ids[0] == bos else None
        self.conventions = bos_conventions(cfg_conf, probe.ids, bos)

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
    """``ReferenceModel`` over the Hugging Face ``LlamaForCausalLM`` built from the pinned configuration (parsed from its verified bytes) and the converted weights."""

    def __init__(self, config: dict[str, Any], state: dict[str, torch.Tensor]) -> None:
        tf = importlib.import_module("transformers")  # outside the lock: imported only here
        self.model = tf.LlamaForCausalLM(tf.LlamaConfig.from_dict(config)).to(torch.float32).eval()
        missing, unexpected = self.model.load_state_dict(state, strict=False)
        if unexpected or set(missing) - {"lm_head.weight"}:  # re-check A, R11: strict=False must not hide a key mismatch
            raise DatagenStop(f"the reference model's state does not match: missing {sorted(missing)[:5]}, unexpected {sorted(unexpected)[:5]}")
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
        eos = self.model.config.eos_token_id
        out = self.model.generate(ids, attention_mask=torch.ones_like(ids), pad_token_id=eos if isinstance(eos, int) else 0, max_new_tokens=max_new, do_sample=False, num_beams=1, min_new_tokens=max_new)  # one unpadded prompt: an all-ones mask and an explicit pad id say so (no padding, no ambiguity)
        return [int(x) for x in out[0, ids.shape[1] :].tolist()]


MARIAN_TIED_KEYS = frozenset({"lm_head.weight"})  # the output projection is tied to the shared embedding and is not stored in the checkpoint


GENERATION_CONFIG_SKIP = frozenset({"transformers_version", "_from_model_config"})  # bookkeeping keys of the file, not generation settings
EMBEDDING_COPIES = ("model.shared.weight", "model.encoder.embed_tokens.weight", "model.decoder.embed_tokens.weight")


def check_embedding_copies(state: dict[str, torch.Tensor]) -> list[str]:
    """Audit minor 2: the checkpoint stores the shared, encoder and decoder embeddings as separate copies, and loading ties them to one tensor. The copies that the checkpoint holds must be equal, or tying would
    silently replace two of them; a difference stops the step. Returns the names compared."""
    present = [k for k in EMBEDDING_COPIES if k in state]
    for k in present[1:]:
        if not torch.equal(state[present[0]], state[k]):
            raise DatagenStop(f"the checkpoint's embedding copies differ ({present[0]} and {k}): loading would tie them to one tensor and silently drop one")
    return present


def apply_generation_config(tf: Any, model: Any, pinned: dict[str, Any]) -> dict[str, Any]:
    """The registered teacher is the pinned model WITH its pinned generation settings: ``model.generation_config`` is built from the hash-verified ``generation_config.json`` bytes (``from_pretrained`` did this
    from the file; building from the config alone did not, and ``renormalize_logits`` was lost). Returns the applied configuration."""
    model.generation_config = tf.GenerationConfig.from_dict(dict(pinned))
    check_generation_config(model.generation_config, pinned)
    return dict(model.generation_config.to_dict())


def check_generation_config(applied: Any, pinned: dict[str, Any]) -> None:
    """Every key of the pinned file (but its bookkeeping keys) must equal the value on the model's generation config; a difference stops the step. Run when the config is applied and before every generate call."""
    bad = {}
    for k, v in pinned.items():
        if k in GENERATION_CONFIG_SKIP:
            continue
        got = getattr(applied, k, "<absent>")
        if got != v:
            bad[k] = {"pinned": v, "on_model": got}
    if bad:
        raise DatagenStop(f"the model's generation config differs from the pinned generation_config.json: {bad}")


def build_marian(tf: Any, config: dict[str, Any], state: dict[str, torch.Tensor]) -> tuple[Any, dict[str, Any]]:
    """The teacher model from the verified config bytes and the safely loaded state (``from_pretrained`` refuses a state dict together with a model name): ``MarianMTModel(config)``, ``load_state_dict`` with
    ``strict=False`` whose result is checked explicitly (the only key that may be missing is the tied ``lm_head.weight``, nothing may be unexpected), then ``tie_weights``; the tied output projection must share
    the embedding's storage. Returns the model and the record of what was missing and tied."""
    compared = check_embedding_copies(state)
    model = tf.MarianMTModel(tf.MarianConfig.from_dict(config))
    missing, unexpected = model.load_state_dict(state, strict=False)
    if unexpected or set(missing) - MARIAN_TIED_KEYS:
        raise DatagenStop(f"the teacher's state does not match the model: missing {sorted(missing)[:5]}, unexpected {sorted(unexpected)[:5]}")
    model.tie_weights()
    tied = model.lm_head.weight.data_ptr() == model.get_input_embeddings().weight.data_ptr()
    if not tied:
        raise DatagenStop("the teacher's output projection is not tied to its embedding after tie_weights")
    return model, {"missing_keys_tied_explicitly": sorted(missing), "unexpected_keys": [], "lm_head_shares_embedding_storage": tied, "embedding_copies_equal": compared, "parameters": int(sum(p.numel() for p in model.parameters()))}


class MarianTeacher:  # pragma: no cover - needs transformers
    """``Teacher`` over a pinned Marian repository: every file re-hashed against its constant right before loading, weights-only load, local files only; beam 4, at most 48 new tokens, CPU. The score
    is recomputed from transition scores (length penalty 1, EOS counted) and compared with the library's ``sequences_scores``: on the first batch a difference above 1e-5 stops the step."""

    def __init__(self, downloads: Path, label: str, name: str, revision: str, tick: Callable[[str], None]) -> None:
        tf = importlib.import_module("transformers")  # outside the lock: imported only here
        self.name, self.revision, self.tick = name, revision, tick
        files = [f"{label}/{f}" for f in ("pytorch_model.bin", *fetch_guard.MARIAN_FILES)]
        fetch_guard.verify_tree(downloads, files)  # re-hash from disk immediately before use
        directory = downloads / label
        extra = sorted(set(os.listdir(directory)) - {"pytorch_model.bin", *fetch_guard.MARIAN_FILES})
        if extra:  # re-check A, R5: from_pretrained looks for other weight and tokenizer files; nothing but the verified ones may be in the folder
            raise DatagenStop(f"refused: {directory} holds files beyond the verified ones: {extra}")
        self.generation_config = json.loads(fetch_guard.read_verified_bytes(downloads, f"{label}/generation_config.json"))
        state = fetch_guard.load_pickle_weights(directory / "pytorch_model.bin", fetch_guard.LARGE[f"{label}/pytorch_model.bin"][0])
        self.tokenizer = tf.MarianTokenizer.from_pretrained(str(directory), local_files_only=True)
        self.model, self.load_record = build_marian(tf, json.loads(fetch_guard.read_verified_bytes(downloads, f"{label}/config.json")), state)
        self.model.eval()
        self.applied_generation_config = apply_generation_config(tf, self.model, self.generation_config)
        if int(self.generation_config.get("num_beams", core.CFG["data"]["generation_beam"])) != int(core.CFG["data"]["generation_beam"]):
            raise DatagenStop("the pinned generation_config.json's num_beams differs from the registered beam")
        self.pad_id = int(self.model.config.pad_token_id)
        self.batches = 0
        self.progress: list[str] = []
        self.score_record: dict[str, Any] = {
            "length_penalty_used": 1.0, "num_beams": core.CFG["data"]["generation_beam"], "generation_config": self.generation_config, "generation_config_applied": self.applied_generation_config,
            "first_batch": None, "max_abs_difference_all_batches": 0.0, "batches": 0, "load": self.load_record,
        }  # fmt: skip

    @torch.no_grad()
    def translate(self, sources: Sequence[str]) -> list[tuple[str, float]]:
        out: list[tuple[str, float]] = []
        started = time.monotonic()
        n_batches = (len(sources) + 31) // 32
        for i in range(0, len(sources), 32):
            self.tick("teacher batch")
            if (i // 32) % PROGRESS_EVERY == 0:
                release_freed_memory()  # the freed score tensors of the batches before go back to the system, so the resident set the guard reads follows the live data
                line = f"[progress] teacher {self.name} batch {i // 32} of {n_batches}: elapsed {time.monotonic() - started:.0f} s, resident {current_rss_mib():.0f} MiB, peak {peak_rss_mib():.0f} MiB"
                self.progress.append(line)
                output.emit_plain(line)  # the one module that prints
                sys.stdout.flush()
            check_generation_config(self.model.generation_config, self.generation_config)  # at generate time, every pinned key is what the model will use
            batch = list(sources[i : i + 32])
            enc = self.tokenizer(batch, return_tensors="pt", padding=True)
            gen = self.model.generate(
                **enc, num_beams=core.CFG["data"]["generation_beam"], max_new_tokens=core.CFG["data"]["generation_new_tokens"], length_penalty=1.0, return_dict_in_generate=True, output_scores=True,
            )  # fmt: skip
            trans = streaming_transition_scores(gen.sequences, gen.scores, gen.beam_indices, int(self.model.config.get_text_config().vocab_size))
            mine = recompute_sequence_scores(trans, gen.sequences[:, -trans.shape[1] :], self.pad_id)
            cmp = compare_scores(mine, [float(x) for x in gen.sequences_scores.tolist()])
            if self.batches == 0:
                self.score_record["first_batch"] = cmp
                if not cmp["ok"]:
                    raise ScoreMismatch(f"the recomputed beam score differs from the library's sequence score on the first batch: {cmp}")
            self.batches += 1
            self.score_record["batches"] = self.batches
            self.score_record["max_abs_difference_all_batches"] = max(self.score_record["max_abs_difference_all_batches"], cmp["max_abs_difference"])
            texts = self.tokenizer.batch_decode(gen.sequences, skip_special_tokens=True)
            out += list(zip(texts, mine, strict=True))  # the filter uses the explicit score
            del gen, trans, enc  # the per-step score tensors (up to 1.4 GB in a batch that runs to 48 tokens) are not held across the next batch; only the text and the score are kept
        return out

    def tokenizer_record(self, sentences: Sequence[str]) -> list[dict[str, Any]]:
        """The teacher token ids of the fixed sentences (source ids, and the ids of the teacher's own translation): frozen; any later teacher run must reproduce them."""
        rows: list[dict[str, Any]] = []
        for s, (text, _score) in zip(sentences, self.translate(list(sentences)), strict=True):
            rows.append({"sentence": s, "source_ids": [int(x) for x in self.tokenizer(s)["input_ids"]], "output_text": text, "output_ids": [int(x) for x in self.tokenizer(text_target=text)["input_ids"]]})
        return rows


def crosscheck_chrf(pairs: Sequence[tuple[str, Sequence[str]]]) -> dict[str, Any]:  # pragma: no cover - needs sacrebleu
    """The study's chrF-norm against sacrebleu 2.5.1 (chrF2, character n-grams 1-6, no word n-grams, eps_smoothing False) on normalized strings, per item; agreement within 0.001."""
    CHRF = importlib.import_module("sacrebleu.metrics").CHRF  # outside the lock: imported only here
    ch = CHRF(char_order=6, word_order=0, beta=2, eps_smoothing=False)
    worst = 0.0
    for hyp, refs in pairs:
        ref_scores = [ch.sentence_score(normalize(hyp), [normalize(r)]).score / 100.0 for r in refs]
        worst = max(worst, abs(max(ref_scores, default=0.0) - chrf_item(hyp, refs)))
    return {"n": len(pairs), "max_abs_difference": worst, "ok": worst <= core.CFG["scoring"]["crosscheck_tolerance"]}


def package_versions() -> dict[str, str]:  # pragma: no cover
    from importlib import metadata

    out: dict[str, str] = {}
    for p in ("torch", "transformers", "tokenizers", "safetensors", "huggingface-hub", "sentencepiece", "numpy", "sacremoses", "sacrebleu", "pyarrow"):
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            out[p] = "not installed"
    return out


def check_installed_pins(versions: dict[str, str]) -> None:
    """The installed versions of the eight named packages must equal the ADR's pins (re-check A, R2): a differing or missing package stops the step before anything is read."""
    from .install_datagen import EXPECTED_PINS

    bad = {n: (versions.get(n), v) for n, v in EXPECTED_PINS.items() if versions.get(n) != v}
    if bad:
        raise DatagenStop(f"refused: installed versions differ from the eight pins (found, pinned): {bad}")


MODULES = ("transformers", "tokenizers", "safetensors", "huggingface_hub", "sentencepiece", "numpy", "sacremoses", "sacrebleu")  # the importable names of the eight pinned packages
PACKAGES_DIR = Path("data/datagen-packages")


def check_provenance(directory: Path, locate: Callable[[str], Any] | None = None) -> dict[str, str]:
    """F6: each of the eight packages must be imported from the hash-installed directory, not from wherever ``uv run --with ...`` or another path put a copy (the versions alone cannot tell). ``locate`` is
    ``importlib.util.find_spec`` by default and is injected in tests. Returns module -> location; a module found elsewhere or not found stops the step."""
    import importlib.util

    find = locate or importlib.util.find_spec
    root = directory.resolve()
    found: dict[str, str] = {}
    for m in MODULES:
        spec = find(m)
        loc = None if spec is None else (spec.origin if spec.origin not in (None, "namespace") else next(iter(spec.submodule_search_locations or []), None))
        if loc is None or not Path(loc).resolve().is_relative_to(root):
            raise DatagenStop(f"refused: {m} is imported from {loc!r}, not from {root}: the packages come from the hash-installed directory only")
        found[m] = str(loc)
    return found


def run_identity(code_commit: str | None, requirements: Path) -> dict[str, Any]:
    """F3: what the data record says about itself: the code commit, the configuration SHA-256, the requirements file's SHA-256 and where transformers was loaded from."""
    import importlib.util

    spec = importlib.util.find_spec("transformers")
    return {"code_commit": code_commit, "config_sha256": fetch_guard.sha256_file(core.ROOT / core.DEFAULT_CONFIG), "requirements_sha256": fetch_guard.sha256_file(requirements) if requirements.is_file() else None, "transformers_file": None if spec is None else str(spec.origin)}


def run(downloads: Path, out: Path, *, led: LedgerLike, stage_cap_seconds: float, wikitext_dir: Path | None = None, requirements: Path | None = None, tatoeba_record: Path | None = None, code_commit: str | None = None) -> dict[str, Any]:  # pragma: no cover - the registered data-generation step
    """Orchestrate the steps with the real objects. Not executed in this implementation step. The record is written even when a stop condition fires; the bundle only when none does."""
    os.environ["HF_HUB_OFFLINE"] = "1"  # assigned, never setdefault: a pre-set "0" must not survive (re-check A, R4)
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    record: dict[str, Any] = {"steps": {}, "environment": package_versions(), **run_identity(code_commit, requirements or core.ROOT / REQUIREMENTS)}
    out.mkdir(parents=True, exist_ok=True)
    core.reset_seed_record()
    attempts = out / "datagen_attempts"
    n_before = len(list(attempts.glob("attempt-*.json"))) if attempts.is_dir() else 0
    gate = datagen_rerun_gate(out)
    if gate:
        raise DatagenStop(gate)
    started = False
    try:
        with charged_stage(led, stage_cap_seconds, guard=True) as clock:
            started = True
            res = _run(downloads, out, clock, record, wikitext_dir or core.ROOT / "data" / "wikitext2", requirements or core.ROOT / REQUIREMENTS, tatoeba_record or core.ROOT / fetch_guard.TATOEBA_RECORD)
            res["bundle_manifest_sha256"] = fetch_guard.sha256_file(out / "bundle" / "manifest.json")  # the identity every pre-freeze record and the freeze check (re-check B, N3)
            res["attempt"] = n_before + 1
            write_json(out / "prefreeze_record.json", core.jsonable(res))
            return res
    except BaseException as e:  # noqa: BLE001 (every exception after the start leaves a stop record, then re-raises: re-check A, R3)
        if started:
            write_stop_record(out, record, e, n_before + 1)
        raise


def stop_kind(e: BaseException) -> str:
    """``registered-test`` for a stop on a registered test of the step (it returns to the lead), ``engineering`` for everything else (a cap, a guard, a read or format error, an unexpected exception)."""
    return "registered-test" if isinstance(e, RegisteredTestStop) or type(e).__name__ in ("WindowsInsufficient", "InputsInsufficient", "PendingLeadReview") else "engineering"


def write_stop_record(out: Path, record: dict[str, Any], e: BaseException, attempt: int) -> None:
    """Keep the stop record of this attempt (``datagen_attempts/attempt-NNN.json``, never overwritten) and leave it as ``prefreeze_record.json`` (a later successful attempt replaces that file only). Each attempt
    is charged on the study ledger by ``charged_stage``."""
    rec = {**record, "stopped": f"{type(e).__name__}: {e}", "stop_kind": stop_kind(e), "attempt": attempt, "bundle_written": False}
    if getattr(e, "counts", None) is not None:
        rec["fixed_input_counts"] = e.counts  # type: ignore[attr-defined]
    d = out / "datagen_attempts"
    d.mkdir(parents=True, exist_ok=True)
    write_json(d / f"attempt-{attempt:03d}.json", core.jsonable(rec))
    write_json(out / "prefreeze_record.json", core.jsonable(rec))


def datagen_rerun_gate(out: Path) -> str | None:
    """R16: a step that stopped on its cap or an engineering error may be re-run after the cause is recorded (it reads no outcome of the study). A stop on a registered test returns to the lead: no re-run until
    ``datagen_attempts/lead_release.json`` exists. A completed step (a bundle) is never re-run."""
    if (out / "bundle" / "manifest.json").exists():
        return f"refused: {out} already holds a completed bundle: the data-generation step is not re-run"
    d = out / "datagen_attempts"
    if d.is_dir():
        last = sorted(d.glob("attempt-*.json"))
        if last and json.loads(last[-1].read_text()).get("stop_kind") == "registered-test":
            n = int(last[-1].stem.split("-")[1])
            rel = d / "lead_release.json"
            try:
                r = json.loads(rel.read_text()) if rel.exists() else {}
            except ValueError:
                r = {}
            if not (r.get("releases_attempt") == n and str(r.get("cause", "")).strip() and str(r.get("released_by", "")).strip()):  # F2: a release names the attempt it releases, its cause and who released it
                return f"refused: the last attempt stopped on a registered test of the step ({last[-1].name}): it returns to the lead; a re-run needs {rel} with releases_attempt = {n}, a cause and released_by"
    return None


def _run(downloads: Path, out: Path, clock: StageClock, record: dict[str, Any], wikitext_dir: Path, requirements: Path, tatoeba_record: Path) -> dict[str, Any]:  # pragma: no cover
    mode = "registered-data"
    check_requirements_hashed(requirements)
    check_installed_pins(package_versions())
    record["steps"]["provenance"] = check_provenance(core.ROOT / PACKAGES_DIR)
    # (1) hashes
    record["steps"]["hashes"] = verify_downloads(downloads, tatoeba_record)
    texts, wiki_prov = read_wikitext(wikitext_dir)
    record["steps"]["wikitext"] = wiki_prov
    clock.tick("hash checks")
    # (2) student conversion
    load_file = importlib.import_module("safetensors.torch").load_file  # outside the lock: imported only here
    cfg = StudentConfig.from_hf_config(json.loads(fetch_guard.read_verified_bytes(downloads, "student/config.json")))  # rms_norm_eps from the model's own file
    fetch_guard.verify_against_constant(downloads / "student/model.safetensors", "student/model.safetensors")  # re-hashed immediately before use
    hf_state = load_file(str(downloads / "student" / "model.safetensors"))
    plain = convert_hf_state_dict(hf_state, cfg)
    student = build_student(cfg)
    load_plain_state(student, plain)
    torch.save({"cfg": cfg.__dict__, "state": plain}, out / PLAIN_STUDENT)
    record["steps"]["student_plain_sha256"] = fetch_guard.sha256_file(out / PLAIN_STUDENT)
    del plain  # the converted state is in the student and on disk: a third 540 MB copy is not held through the rest of the step
    # (3)-(4) tokenizer, equivalence at each read layer, tests (c), (d), (e)
    tok = HFTokenizer(downloads)
    record["steps"]["tokenizer_conventions"] = tok.conventions
    ref = HFReference(json.loads(fetch_guard.read_verified_bytes(downloads, "student/config.json")), hf_state)
    del hf_state  # the reference model holds its own copy of the weights
    train_ids = tok.encode(texts["train"])
    ids = torch.tensor([train_ids[:256]])  # the fixed 256-token text of WikiText-2 train (step 3)
    vec = torch.randn(cfg.width, generator=core.partition_gen(mode, "equivalence_injection", "equivalence injection vector (own listed seed)"))
    prompts = [train_ids[256 + i * 8 : 264 + i * 8] for i in range(100)]  # test (e): 100 prompts from the train text (the validation text is reserved for GEN)
    layers = {str(layer): equivalence.build_record(student, ref, ids, vec, layer, prompts, 8) for layer in core.READ_LAYERS}
    record["steps"]["equivalence"] = {k: v["at_creation"] for k, v in layers.items()}
    if not all(v["at_creation"]["logits"]["ok"] and v["at_creation"]["injection"]["ok"] for v in layers.values()):
        raise RegisteredTestStop("the student equivalence test failed at a read layer (step 3 or 4 (d))")
    del ref, ids, vec, prompts, train_ids  # the reference model (540 MB), its logits inputs and the 2.4 million train ids are needed only to build the equivalence records, which are complete
    gc.collect()
    release_freed_memory()  # and the allocator hands its free pages back: the guard reads the resident set, which a freed object does not lower
    clock.tick("equivalence")
    dec = ByteDecoder(tok.token_bytes())
    gen = core.partition_gen(mode, "random_id_sequences", "test (c) random id sequences")
    record["steps"]["check_c"] = check_decoder(dec, tok, random_id_sequences(tok.vocab_size, core.CFG["data"]["random_id_sequences"], gen))
    # (5) data and teachers
    corpus, corpus_rec = load_corpus(downloads, record["steps"]["hashes"]["tatoeba"])
    record["steps"]["corpus"] = corpus_rec
    teachers = {c: MarianTeacher(downloads, folder, name, revn, clock.tick) for c, (name, revn, folder) in {"A": ("opus-mt-en-de", fetch_guard.TEACHER_A[1], "teacher_a"), "B": ("opus-mt-en-fr", fetch_guard.TEACHER_B[1], "teacher_b")}.items()}
    provenance = {"wikitext": wiki_prov, "tatoeba": record["steps"]["hashes"]["tatoeba"], "corpus": corpus_rec, "tokenizer_conventions": tok.conventions, "student_plain_sha256": record["steps"]["student_plain_sha256"], "environment": record["environment"]}
    bundle, rec = build_bundle(corpus, tok, student, teachers, texts["validation"], texts["train"], Sizes.registered(), WindowSpec.registered(), mode, 0, crosscheck=crosscheck_chrf, tick=clock.tick, provenance=provenance)
    bundle.extra["equivalence"] = layers[str(core.READ_LAYERS[0])]  # inside the hash-checked data files (gate G8 reads it from there)
    bundle.extra["equivalence_layers"] = layers
    rec["generation_config"] = {c: t.score_record for c, t in teachers.items()}
    rec["steps"] = {k: v for k, v in record["steps"].items() if k != "equivalence"}
    rec["g9_data_step"] = core.seed_gate(core.seed_record(), core.planned_seeds(mode), planned_mode=mode, extra_foreign=core.config_seeds(), stage_mode=mode)
    record.update(rec)
    stops = []
    if not rec["tokenization"]["required_ok"]:
        stops.append("test (a): a prompt or R-icl prompt mismatch (0 required)")
    if not rec["chrf_crosscheck"]["ok"]:
        stops.append(f"the chrF cross-check differs by {rec['chrf_crosscheck']['max_abs_difference']} (0.001 allowed)")
    if not rec["g9_data_step"]["ok"]:
        stops.append(f"gate G9 on the data step: {rec['g9_data_step']['problems']}")
    if stops:
        raise RegisteredTestStop("; ".join(stops))
    write_bundle(bundle, out / "bundle")
    write_json(out / "prefreeze_record.json", core.jsonable(record))
    return record


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover
    import sys as _sys

    args_in = list(_sys.argv[1:] if argv is None else argv)
    if "--smoke" in args_in:  # the real-library smoke exercise: uncharged engineering on fixed literal sentences, writes nothing under the data folder
        from .datagen_smoke import smoke_main

        return smoke_main([a for a in args_in if a != "--smoke"])
    p = argparse.ArgumentParser(prog="python -m studies.p10s2.datagen")
    p.add_argument("--downloads", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--code-commit", required=True, help="must equal a clean HEAD")
    p.add_argument("--stage-cap-seconds", type=float, required=True)
    p.add_argument("--wikitext-dir", default=None, help="the local WikiText-2 parquet directory (default data/wikitext2)")
    a = p.parse_args(argv)
    from . import freeze

    freeze.check_code_commit(core.ROOT, a.code_commit)
    from .ledger import Ledger

    led = Ledger()  # the one study ledger (experiments/P10S2/ledger.jsonl under the repository)
    run(Path(a.downloads), Path(a.out), led=led, stage_cap_seconds=a.stage_cap_seconds, wikitext_dir=Path(a.wikitext_dir) if a.wikitext_dir else None, code_commit=a.code_commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
