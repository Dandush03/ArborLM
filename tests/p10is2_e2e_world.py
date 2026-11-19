# ruff: noqa: E501
"""A synthetic world for launching Part Q's REAL stages in fresh processes: the downloads and the teachers are fakes (a tiny byte-pair tokenizer, a tiny random student, lexicon teachers, a made-up corpus and
validation text); everything else on the path (``partq_registered.sh``, ``stages work``, ``run_stage``, ``build_world``, the plan, the stage-start checks, every stage body, P10-S2's functions) is the real code.
``install()`` is called inside the child process by ``hook.py``; the test process uses ``make_world`` to write the candidate ledger. Test-range seeds only inside this module (the launched stages use the
seeds of their mode on SYNTHETIC data). Self-check only."""

import os
import re
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from p10is2_fixtures import lex_teachers, small_corpus, test_gen  # noqa: E402

from studies.p10s2.model import StudentConfig, build_student  # noqa: E402
from studies.p10s2.synthetic import make_text  # noqa: E402
from studies.p10s2.tokenization import SyntheticTokenizer  # noqa: E402

PANELS = {"q_fit": 120, "q_check_block": 40, "q_check_blocks_max": 6, "d_cal": 20, "d_con": 10, "e_eval": 30, "e_eval_min": 10, "e_combined": 15, "e_combined_min": 5, "e_open": 5, "both_reference_min_train": 150, "gen_marker_like": 17, "gen_ordinary": 4, "general_window_tokens": 128}
GENERATION = {"accepted_min": 30, "accepted_disjoint": 60, "per_replicate": 20, "generation_block_sources": 100, "batch_size": 8, "digest_batches": 2, "regeneration_batches": 3}
QUALITY = {"q4_min_accepted": 10}


def scaled_config_text(text: str, ledger_path: Path) -> str:
    """The Part Q config scaled to the synthetic world (the only edit of the config: numbers of the [panels], [generation] and [quality] sections and the ledger path)."""
    for section, values in (("panels", PANELS), ("generation", GENERATION), ("quality", QUALITY)):
        head, body = text.split(f"[{section}]", 1)
        body_head, sep, rest = body.partition("\n[")
        for k, v in values.items():
            body_head, n = re.subn(rf"(?m)^{k} = [0-9.]+", f"{k} = {v}", body_head)
            assert n == 1, (section, k)
        text = head + f"[{section}]" + body_head + sep + rest
    text, n = re.subn(r'(?m)^panel_ledger = "[^"]*"', f'panel_ledger = "{ledger_path}"', text)
    assert n == 1
    return text


def validation_rows() -> list[str]:
    """Unique rows (every window of the text occurs once): marker rows first (each starts with the marker string 'German'), then marker-free rows."""
    marker = [f"German item {i} says {i * 7 + 3} was seen on day {i % 28 + 1}. " * 2 for i in range(40)]
    plain = [" ".join(f"Item {i}-{j} says that {i * j + 7} was seen on day {(i + j) % 28 + 1}." for j in range(6)) for i in range(60)]
    return [*marker, *plain]


class Tok(SyntheticTokenizer):
    conventions: dict[str, Any] = {"bos": None}


def build_tokenizer() -> Tok:
    corpus = small_corpus()
    text = make_text(test_gen(31), n_words=900)
    sample = " ".join(list(corpus.eng.values())[:200]) + " English: German: French:\n" + " ".join(list(corpus.deu.values())[:100]) + " " + " ".join(list(corpus.fra.values())[:100]) + " " + text[:3000] + " ".join(validation_rows())
    return Tok(sample, merges=60)


def make_world(cfg: Any, repo: Path, run_dir: Path) -> Any:
    from studies.p10is2.partq import real_world

    tok = build_tokenizer()
    rows = validation_rows()
    student = build_student(StudentConfig.tiny(len(tok.token_bytes())), test_gen(32))
    w = real_world.RealWorld(cfg, repo, run_dir, run_dir / "downloads", tok=tok, student=student, corpus=small_corpus(), teachers=lex_teachers())
    w.wikitext_rows = {"train": rows, "validation": rows}
    w.texts = {k: "".join(v) for k, v in w.wikitext_rows.items()}
    return w


def install() -> None:
    """Patches the DOWNLOAD and TEACHER entry points only (called in the child process before the stage's entry point runs)."""
    from studies.p10is2.common import plan as planmod
    from studies.p10is2.partq import real, real_stages, real_world
    from studies.p10s2 import datagen

    tok = build_tokenizer()
    rows = validation_rows()
    teachers = lex_teachers()
    for t in teachers.values():  # what stage_inputs reads of a real teacher
        t.model = SimpleNamespace(generation_config=None)
        t.generation_config = {}
        t.applied_generation_config = {}
        t.tokenizer_record = lambda sentences: {"sentences": len(sentences), "fake": True}  # FAKE: a real teacher's own tokenization of the sentences

    def student(downloads: Path, out: Path | None) -> tuple[Any, Any, dict[str, Any]]:
        return build_student(StudentConfig.tiny(len(tok.token_bytes())), test_gen(32)), None, {"fake": "student"}

    real_world.assert_process_environment = lambda cfg: None  # FAKE: the process environment of a launch is tested by test_p10is2_reaudit2_fixes.py (the real path puts the durable packages on PYTHONPATH, which a test must not)
    real_world.check_packages = lambda cfg, repo: {"versions": {}, "provenance": {}, "requirements_sha256": "x"}  # FAKE: the 28 packages
    real_world.load_student = student  # FAKE: the downloaded student
    real_world.read_wikitext_rows = lambda directory, pins: {"train": rows, "validation": rows}  # FAKE: the WikiText-2 parquet files
    real_world.equivalence_records = lambda *a, **k: {str(layer): {"at_creation": {"logits": {"ok": True}, "injection": {"ok": True}}} for layer in (4, 12)}  # FAKE: needs the downloaded reference model
    real.wikitext_pins = lambda repo: {}  # FAKE: ADR-0004's pins of the downloaded files
    real.check_wikitext = lambda directory, pins: {"directory": str(directory), "fake": True}
    overhead = float(os.environ.get("E2E_OVERHEAD", "0"))

    def verify_downloads(*a: Any, **k: Any) -> dict[str, Any]:
        time.sleep(overhead)  # a synthetic per-process cost of building the world (the real one is the hashing, the corpus, the student and the teachers)
        return {"models": {}, "tatoeba": {"fake": True}}

    datagen.verify_downloads = verify_downloads  # FAKE: the downloads
    planmod.import_walk = lambda *a, **k: {"python_files": [], "files_opened": [], "outside_study_python": [], "outside_study_data": []}  # FAKE: the import walk (a subprocess that imports the repository's code)
    datagen.load_corpus = lambda downloads, rec: (small_corpus(), {"fake": True})
    datagen.HFTokenizer = lambda downloads: tok
    datagen.check_generation_config = lambda *a, **k: None  # FAKE: the pinned configuration file of a real teacher
    datagen.crosscheck_chrf = lambda pairs: {"n": len(pairs), "max_abs_difference": 0.0, "ok": True}  # FAKE: sacrebleu is outside the lock
    real_stages.marian_batch_teacher = lambda downloads, folder, name, rev, tick: teachers["A" if folder == "teacher_a" else "B"]  # FAKE: the teachers
