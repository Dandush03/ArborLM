# ruff: noqa: E501
"""Real-library smoke of Part Q's real path on EIGHT FIXED LITERAL ENGLISH SENTENCES (ADR-0025 section 13 item 6; the coordinator's message of 2026-11-18).

Run as ``PYTHONPATH=<durable packages> UV_OFFLINE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run --locked --offline --extra pilot python -m studies.p10is2.partq.real_smoke``. It touches no registered seed, no
Q_fit, Q_check or evaluation item and no corpus row: the sentences are written below. It proves that ``teacher.marian_batch_teacher`` returns what ``FakeTeacher``'s interface promises (``Generated``: integer
token ids, text, a finite score; the same batch regenerates identically at the same threads), that the student scorer returns finite numbers in [0, 1], and that the window grid, byte spans, equivalence record
and chrF cross-check calls have the right signatures. Nothing is written; the summary goes to stdout.
"""

import json
import math
import sys
import time
from typing import Any

import torch

from studies.p10is2.common import core, gates

from . import real_world
from .teacher import Generated, marian_batch_teacher

SENTENCES = (
    "I like tea.", "The children are playing in the garden.", "Where is the station?", "She reads a book every evening.", "We are going to the market today.", "He has two brothers and a sister.",
    "The train leaves early in the morning.", "Please close the door.",
)  # fmt: skip
PARAGRAPH = "The children are playing in the garden. She reads a book every evening, and he likes tea. Where is the station? The train leaves early in the morning. "


def main() -> int:
    cfg = core.load_config("Q")
    real_world.assert_process_environment(cfg)
    torch.set_num_threads(6)
    torch.use_deterministic_algorithms(True)
    out: dict[str, Any] = {"threads": torch.get_num_threads(), "platform": gates.platform_record(), "sentences": len(SENTENCES), "steps": {}}
    t0 = time.monotonic()
    out["steps"]["packages"] = real_world.check_packages(cfg, core.ROOT)["versions"]
    from studies.p10s2 import datagen

    downloads = real_world.Path(cfg["paths"]["durable_downloads"]) / "downloads"
    teachers = {c: marian_batch_teacher(downloads, folder, name, rev, lambda s: None) for c, (name, rev, folder) in real_world.TEACHER_FOLDERS.items()}
    for c, t in teachers.items():
        first = t.generate_batch(list(SENTENCES))
        again = t.generate_batch(list(SENTENCES))
        small = t.generate_batch(list(SENTENCES[:3]))
        ok = all(isinstance(g, Generated) and all(isinstance(i, int) for i in g.tokens) and isinstance(g.text, str) and math.isfinite(g.score) and g.tokens for g in first)
        out["steps"][f"teacher_{c}"] = {
            "interface_ok": ok, "n": len(first), "same_batch_identical_tokens": [g.tokens for g in first] == [g.tokens for g in again], "max_score_difference_same_batch": max(abs(a.score - b.score) for a, b in zip(first, again, strict=True)),
            "batch_of_3_equals_first_3_tokens": [g.tokens for g in small] == [g.tokens for g in first[:3]], "first_text": first[0].text, "score_range": [min(g.score for g in first), max(g.score for g in first)],
        }  # fmt: skip
        out["steps"][f"teacher_{c}_generation_config_asserted"] = datagen.check_generation_config(t.model.generation_config, t.generation_config) is None
        assert ok
    tok = datagen.HFTokenizer(downloads)
    student, hf_state, srec = real_world.load_student(downloads, None)  # nothing is written
    dec = real_world.ByteDecoder(tok.token_bytes())
    nl = tuple(real_world.tokenize_segment(tok, "\n").ids)

    class P:  # a stand-in partition holding two literal D_cal-like items: only the references' lengths are read
        panels = {"D_cal": [type("I", (), {"refs": {"A": ("Ich mag Tee.",), "B": ("J'aime le thé.",)}})()]}

    items = [type("I", (), {"en": s, "refs": {"A": ("Ich mag Tee.",), "B": ("J'aime le thé.",)}})() for s in SENTENCES[:2]]
    sc = real_world.student_scorer(student, tok, dec, nl)(items, P)
    out["steps"]["student_scorer"] = {"scores": sc, "finite_in_unit_interval": all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in sc.values()), "student_plain_sha256": srec["student_plain_sha256"]}
    rows = [f"Sentence {i} of the smoke text says that item {i * 7 + 3} was seen on day {i % 28 + 1}. {PARAGRAPH}" for i in range(40)]  # every row differs, so every window occurs once
    text = "".join(rows)
    grid = real_world.window_grid(tok, text, 32, 8)
    spans = real_world.window_spans(grid, tok.token_bytes(), rows)
    out["steps"]["window_grid"] = {"windows": len(grid), "strata": sorted({g["stratum"] for g in grid}), "first_span": [spans[0].start, spans[0].end, spans[0].first_row, spans[0].last_row] if spans else None}
    eq = real_world.equivalence_records(student, hf_state, downloads, tok, text * 4, real_world.seed_getter(cfg, "test"), (4,))
    out["steps"]["equivalence_layer4"] = {"logits_ok": eq["4"]["at_creation"]["logits"]["ok"], "injection_ok": eq["4"]["at_creation"]["injection"]["ok"]}
    out["steps"]["check_c"] = {k: v for k, v in real_world.check_decoder_test_c(tok, real_world.seed_getter(cfg, "test"), 50).items() if k in ("n", "ok", "failures")}
    out["steps"]["crosscheck_chrf"] = datagen.crosscheck_chrf([("Ich mag Tee.", ["Ich mag Tee."]), ("Der Zug fährt früh.", ["Der Zug fährt am Morgen früh ab."]), ("Ja.", ["Nein."])])
    out["seconds"] = round(time.monotonic() - t0, 1)
    print(json.dumps(core.jsonable(out), indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
