# ruff: noqa: E501
"""The real world of Part Q: corpus, student, tokenizer, teachers, WikiText-2, equivalence and the GEN windows (ADR-0025 sections 4.1 step 1, 11 item 1, 13 item 6).

Everything here CALLS P10-S2's own code (``studies/p10s2``: ``datagen.verify_downloads``, ``load_corpus``, ``HFTokenizer``, ``HFReference``, ``MarianTeacher`` through ``teacher.marian_batch_teacher``,
``equivalence.build_record``, ``tokenization.check_decoder``, ``windows.cut_windows``, ``model.convert_hf_state_dict`` and the rest) and edits none of it. It runs only in a process that has the 28 packages on its path
from the verified durable copy, offline, never through uv's cache (``real.package_path_problems`` is asserted first). Seeds are this study's (250909, 250910, 250908, 250907), through ``core.seeded_generator``.

Never imported by the unit tests (it needs the packages); ``real_smoke`` import-checks it in a subprocess that has them.
"""

import gc
import importlib
import json
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import torch

from arborlm.io import file_sha256, write_json
from studies.p10s2 import datagen, equivalence, fetch_guard
from studies.p10s2.evaluate import GeneralWindow, truncation_percentile
from studies.p10s2.model import (
    StudentConfig,
    build_student,
    convert_hf_state_dict,
    load_plain_state,
)
from studies.p10s2.text import chrf_item
from studies.p10s2.tokenization import (
    ByteDecoder,
    check_decoder,
    prompt_segments,
    random_id_sequences,
    tokenize_segment,
)
from studies.p10s2.windows import first_marker

from ..common import core
from ..common.core import StageRefused
from ..common.panel_ledger import RowMap, Span
from . import real

TATOEBA_RECORD = "studies/p10s2/records/tatoeba_session.json"
STUDENT_FOLDER = "student"
TEACHER_FOLDERS = {"A": ("opus-mt-en-de", fetch_guard.TEACHER_A[1], "teacher_a"), "B": ("opus-mt-en-fr", fetch_guard.TEACHER_B[1], "teacher_b")}


@dataclass
class RealWorld:
    cfg: Mapping[str, Any]
    repo: Path
    run_dir: Path
    downloads: Path
    tok: Any = None
    student: Any = None
    decoder: Any = None
    corpus: Any = None
    teachers: dict[str, Any] = field(default_factory=dict)
    record: dict[str, Any] = field(default_factory=dict)
    wikitext_rows: dict[str, list[str]] = field(default_factory=dict)
    texts: dict[str, str] = field(default_factory=dict)


# --- guards ---------------------------------------------------------------------------------------------------------------------------------
def assert_process_environment(cfg: Mapping[str, Any]) -> None:
    """Offline, the durable copy only: a process that does not look like the launch scripts' is refused before anything is read."""
    env = dict(os.environ)
    problems = real.package_path_problems(cfg, env, sys.argv)
    for v in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        if env.get(v) != "1":
            problems.append(f"{v} is not 1")
    if env.get("PYTORCH_ENABLE_MPS_FALLBACK"):
        problems.append("PYTORCH_ENABLE_MPS_FALLBACK is set")
    if problems:
        raise StageRefused("refused: " + "; ".join(problems))


def check_packages(cfg: Mapping[str, Any], repo: Path) -> dict[str, Any]:
    """The eight named packages at their pins and imported from the durable copy (P10-S2's own checks), the requirements file hashed."""
    req = repo / cfg["paths"]["packages_requirements"]
    if file_sha256(req) != cfg["paths"]["packages_requirements_sha256"]:
        raise StageRefused("refused: the requirements file is not the one the human lead approved (hash differs)")
    datagen.check_requirements_hashed(req)
    versions = datagen.package_versions()
    datagen.check_installed_pins(versions)
    return {"versions": versions, "provenance": datagen.check_provenance(Path(cfg["paths"]["durable_packages"])), "requirements_sha256": file_sha256(req)}


# --- WikiText-2 and the GEN windows -----------------------------------------------------------------------------------------------------------------
def read_wikitext_rows(directory: Path, pins: Mapping[str, Mapping[str, Any]]) -> dict[str, list[str]]:
    """The rows of the ``text`` column of each parquet file in file order, exactly as stored (ADR-0022 ruling A-B3), after the file passed its pin (``real.check_wikitext``)."""
    pq = importlib.import_module("pyarrow.parquet")
    out: dict[str, list[str]] = {}
    for split, name in (("train", real.WIKITEXT_FILES[0]), ("validation", real.WIKITEXT_FILES[1])):
        rows: list[str] = []
        with pq.ParquetFile(directory / name) as f:
            for batch in f.iter_batches(columns=["text"], use_threads=False):
                rows.extend(batch.column(0).to_pylist())
        if not all(isinstance(r, str) for r in rows):
            raise StageRefused(f"refused: {name} holds a row that is not a string")
        out[split] = rows
    return out


def window_grid(tok: Any, text: str, window: int, decision: int) -> list[dict[str, Any]]:
    """The fixed grid of ``window``-token windows over the whole text, classified exactly as P10-S2's ``windows.cut_windows`` does (marker-like if a marker-like string lies within the first ``decision``
    tokens; ordinary if none lies in the whole window; any other window is not a candidate). Each carries the token ids of the window (the BYTES of its span come from them: ``window_spans``)."""
    ids, offs = tok.encode_offsets(text)
    out: list[dict[str, Any]] = []
    for w0 in range(0, len(ids) - window + 1, window):
        head = text[offs[w0][0] : offs[w0 + decision - 1][1]]
        whole = text[offs[w0][0] : offs[w0 + window - 1][1]]
        stratum = "marker" if first_marker(head) is not None else ("ordinary" if first_marker(whole) is None else None)
        if stratum is not None:
            out.append({"w0": w0, "stratum": stratum, "ids": ids[w0 : w0 + window], "char_start": offs[w0][0], "char_end": offs[w0 + window - 1][1]})
    return out


def find_once(haystack: bytes, needle: bytes) -> int | None:
    """The position of ``needle`` in ``haystack`` if it occurs exactly once (overlapping occurrences count), else None."""
    pos = haystack.find(needle)
    if pos < 0 or haystack.find(needle, pos + 1) >= 0:
        return None
    return pos


def window_spans(grid: Sequence[Mapping[str, Any]], token_bytes: Sequence[bytes], rows: Sequence[str], text_bytes: bytes | None = None) -> list[Span]:
    """Byte spans (exclusive ends) of the grid's windows in the concatenation of the rows, found from BYTES, as the longer-training study does (audit R8): the window's bytes are the join of its tokens' bytes and
    must occur EXACTLY ONCE in the concatenated validation text; zero or several occurrences stop the step (``RegisteredTestStop``), nothing is guessed. The first and last row follow from the row map."""
    from studies.p10s2.datagen import RegisteredTestStop

    data = text_bytes if text_bytes is not None else "".join(rows).encode("utf-8")
    rm = RowMap.from_rows(rows)
    spans: list[Span] = []
    for g in grid:
        b = b"".join(token_bytes[i] for i in g["ids"])
        pos = find_once(data, b)
        if pos is None:
            raise RegisteredTestStop(f"window {g['w0']} ({g['stratum']}) occurs {'0' if data.find(b) < 0 else 'more than once'} times in the validation text; the span is not guessed")
        end = pos + len(b)
        spans.append(Span(pos, end, rm.row_of(pos), rm.row_of(end - 1), g["stratum"]))
    return spans


def cut_general_windows(tok: Any, text: str, vocab_index: Mapping[str, int], window: int, decision: int) -> list[GeneralWindow]:
    from studies.p10s2.windows import cut_windows

    return cut_windows(tok, text, vocab_index, window, decision)


# --- student, tokenizer, equivalence ---------------------------------------------------------------------------------------------------------------
def load_student(downloads: Path, out: Path | None) -> tuple[Any, Any, dict[str, Any]]:
    load_file = importlib.import_module("safetensors.torch").load_file
    cfg = StudentConfig.from_hf_config(json.loads(fetch_guard.read_verified_bytes(downloads, "student/config.json")))
    fetch_guard.verify_against_constant(downloads / "student/model.safetensors", "student/model.safetensors")
    hf_state = load_file(str(downloads / "student" / "model.safetensors"))
    plain = convert_hf_state_dict(hf_state, cfg)
    student = build_student(cfg)
    load_plain_state(student, plain)
    if out is None:  # a smoke writes nothing
        import hashlib

        from studies.p10s2.model import tensor_sha

        h = hashlib.sha256()
        for k in sorted(plain):
            h.update(k.encode())
            h.update(tensor_sha(plain[k]).encode())  # the study's own tensor hash: nothing is written
        return student, hf_state, {"student_plain_sha256": h.hexdigest(), "written": False, "note": "a digest of the tensors, not the sha of the saved file"}
    out.mkdir(parents=True, exist_ok=True)
    torch.save({"cfg": cfg.__dict__, "state": plain}, out / "student_plain.pt")
    return student, hf_state, {"student_plain_sha256": fetch_guard.sha256_file(out / "student_plain.pt"), "written": True}


def equivalence_records(student: Any, hf_state: Any, downloads: Path, tok: Any, train_text: str, ctx_seed: Callable[[str], torch.Generator], layers: Sequence[int]) -> dict[str, Any]:
    """Gate G8's records at each read layer (P10-S2's ``equivalence.build_record``), the injection vector from seed 250910."""
    ref = datagen.HFReference(json.loads(fetch_guard.read_verified_bytes(downloads, "student/config.json")), hf_state)
    train_ids = tok.encode(train_text)
    ids = torch.tensor([train_ids[:256]])
    vec = torch.randn(student.cfg.width, generator=ctx_seed("equivalence_injection"))
    prompts = [train_ids[256 + i * 8 : 264 + i * 8] for i in range(100)]
    rec = {str(layer): equivalence.build_record(student, ref, ids, vec, layer, prompts, 8) for layer in layers}
    del ref
    gc.collect()
    return rec


def check_decoder_test_c(tok: Any, ctx_seed: Callable[[str], torch.Generator], n: int = 1000) -> dict[str, Any]:
    dec = ByteDecoder(tok.token_bytes())
    return check_decoder(dec, tok, random_id_sequences(tok.vocab_size, n, ctx_seed("tokenization_test_c")))


# --- the student scorer ----------------------------------------------------------------------------------------------------------------------------
def max_new_from_dcal(tok: Any, p: Any, newline_ids: Sequence[int]) -> int:
    """The new-token limit: the 99.5th percentile of the gold references of D_cal in student tokens, German and French pooled (P10-S2's reading, section 4.1 step 8 'the truncation limit'), at least 4."""
    lens = [len(tok.encode(" " + r)) + len(newline_ids) for it in p.panels["D_cal"] for c in core.TASKS for r in it.refs.get(c, ())]
    return max(truncation_percentile(lens or [48]), 4)


def student_scorer(student: Any, tok: Any, decoder: Any, newline_ids: Sequence[int]) -> Callable[[Sequence[Any], Any], dict[str, float]]:
    """The untrained student's mean chrF-norm on the Q_fit items per capability: its greedy answer to each task prompt (P10-S2's ``Student.greedy``, no read, no adapter), stop at the first newline byte."""

    @torch.no_grad()
    def scores(items: Sequence[Any], p: Any) -> dict[str, float]:
        max_new = max_new_from_dcal(tok, p, newline_ids)
        out: dict[str, float] = {}
        for c in core.TASKS:
            vals = []
            for it in items:
                ids = [i for s in prompt_segments(tok, c, it.en) for i in s.ids]
                ans = decoder.answer_text(student.greedy(torch.tensor([ids]), add=None, adapter=None, max_new=max_new, stop_bytes=decoder.table))
                vals.append(chrf_item(ans, list(it.refs[c])))
            out[c] = sum(vals) / max(1, len(vals))
        return out

    return scores


def seed_getter(cfg: Mapping[str, Any], mode: str) -> Callable[[str], torch.Generator]:
    seeds = core.partq_seeds(cfg, mode)
    allowed = frozenset(seeds.values())

    def get(name: str) -> torch.Generator:
        return core.seeded_generator(seeds[name], name, allowed)

    return get


def now() -> float:
    return time.monotonic()


__all__ = ["ByteDecoder", "RealWorld", "tokenize_segment", "write_json"]
