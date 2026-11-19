# ruff: noqa: E501
"""The pre-freeze check of the R-gloss-icl prompt TEXTS (ADR-0025 addendum, attempt 3, sections 3 and 4): tokenization test (a) over the prompts the study will build, with NO teacher output read and nothing sealed opened.

What it needs, and what it covers.

* The prompt text is built from the SOURCE words of E_A, E_B and D_cal (public: a pure function of the corpus and the registered partition seeds, recomputed here without writing anything) and, for each in-vocabulary
  source word, a gloss word. In the registered run the gloss words come from the lexicon of the accepted pools, a product of the generation stage, which this check does not read. So the check gives EVERY in-vocabulary
  source word an entry and cycles four placeholder glosses (a letter word, a digit-initial word, an accented word, an apostrophe word) over them: every line of every real prompt, each source word at each position and
  each repeat, is therefore tested for the source-word side of the boundaries, which is where attempt 2 failed.
* It also sweeps EVERY target-language word type of the reference sentences of the corpus (German and French, public) as a gloss word between a letter-initial, a digit-initial and a punctuation-initial source word, so
  that the gloss side of the boundaries is tested over a vocabulary much wider than any accepted pool.
* It decides the rule for the last newline from the tokenizer and the items alone and records it.

What is left for the registered ``outputs`` stage: the lexicon's actual gloss words (the target words of the accepted pools: teacher outputs, which may include a word the corpus does not) and the exact choice
of gloss word per source word. The ``outputs`` stage runs test (a) over the real prompts and stops on any mismatch, as registered."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from studies.p10s2.data import TrainItem
from studies.p10s2.text import normalize

from . import gloss

PLACEHOLDER_GLOSSES = tuple(normalize(g) for g in ("a", "7th", "été", "l'ami"))  # a letter word, a digit-initial word, an accented word, a word with an apostrophe (as the study's ``normalize`` writes them)
PROBES = ("ill", "230", "9th", "?!", "'s")  # source words of the sweep: letter-initial, digit-initial (twice), punctuation-initial (twice)


def check(tok: Any, panels: Mapping[str, Sequence[Any]], vocab: Sequence[str], gloss_words: Mapping[str, Sequence[str]], *, first_mismatches: int = 5) -> dict[str, Any]:
    """Test (a) over the registered prompt texts with placeholder glosses, plus the gloss-type sweep. ``panels`` holds E_A, E_B and D_cal; ``gloss_words`` the target-language word types per capability."""
    in_vocab = set(vocab)
    lexicon = {w: PLACEHOLDER_GLOSSES[i % len(PLACEHOLDER_GLOSSES)] for i, w in enumerate(sorted(in_vocab))}
    sources = {"A": [*panels["E_A"], *panels["D_cal"]], "B": [*panels["E_B"], *panels["D_cal"]]}
    pieces = gloss.first_task_pieces(tok, sources)
    pools = {c: [TrainItem("probe", "probe", " ".join([*PLACEHOLDER_GLOSSES, *gloss_words.get(c, ())]), 0)] for c in ("A", "B")}
    bank = gloss.gloss_bank(tok, pools, sorted({*in_vocab, *PROBES}), pieces)
    out: dict[str, Any] = {"segment_rule": gloss.SEGMENT_RULE, "last_newline": bank["last_newline"], "tests": {}, "mismatches": 0, "first": []}
    for name, cap in (("E_A", "A"), ("E_B", "B"), ("D_cal", "A"), ("D_cal", "B")):
        res = gloss.tokenization_test_a(tok, panels[name], lexicon, in_vocab, cap, bank)
        out["tests"][f"{name}/{cap}"] = {"checked": res["checked"], "mismatches": res["mismatches"]}
        out["mismatches"] += res["mismatches"]
        out["first"] += res["first"]
    sweep = 0
    sweep_first: list[dict[str, Any]] = []
    types = 0
    for cap in ("A", "B"):
        own = bank["last_newline"]["rule"] == "own-segment"
        first_piece_ids = list(tok.encode(gloss.TASK_FIRST_PIECE))
        for g in sorted({normalize(w) for w in gloss_words.get(cap, ()) if normalize(w)}):
            types += 1
            for lines in ([("ill", g), ("230", g), ("ill", g)], [("9th", g), ("?!", g), ("'s", g), ("230", g)]):
                seg = gloss.icl_prompt_ids(lines, bank, cap) + (first_piece_ids if own else [])
                whole = list(tok.encode(gloss.icl_prompt_text(lines) + gloss.TASK_FIRST_PIECE))
                if seg != whole:
                    sweep += 1
                    if len(sweep_first) < first_mismatches:
                        sweep_first.append({"capability": cap, "gloss_word": g, "lines": lines})
    out["gloss_sweep"] = {"gloss_types_checked": types, "mismatches": sweep, "first": sweep_first}
    out["items_checked"] = sum(v["checked"] for v in out["tests"].values())
    out["required_ok"] = out["mismatches"] == 0 and sweep == 0
    out["covers"] = "every in-vocabulary source word of every E_A, E_B and D_cal item, at every position and repeat, with four placeholder glosses; every reference word type of the corpus as a gloss word at the boundaries; the rule of the last newline"
    out["left_for_outputs"] = "the lexicon's actual gloss words (target words of the accepted pools, teacher outputs) and the gloss chosen per source word: test (a) on the real prompts in the registered outputs stage"
    return out


def reference_word_types(corpus: Any) -> dict[str, list[str]]:
    """The normalized word types of the German and French reference sentences of the corpus (public inputs): the vocabulary the sweep uses as gloss words."""
    return {"A": sorted({w for s in corpus.deu.values() for w in normalize(s).split()}), "B": sorted({w for s in corpus.fra.values() for w in normalize(s).split()})}


def cmd_prompt_check(repo: Path, out: Path) -> dict[str, Any]:
    """Runs the check on the REAL tokenizer and corpus (packages from the durable copy, offline, as the ledger command): recomputes the registered partition (a pure function of the corpus and the registered seeds;
    the same computation every stage makes; nothing is drawn anew and nothing is written but ``out``), builds the panels' prompts, writes the record once."""
    from studies.p10s2 import datagen

    from ..common import core, gates
    from . import partition, pipeline, real_stages, real_world

    if out.exists():
        raise core.StageRefused(f"refused: {out} exists")
    cfg = core.load_config("Q", repo / core.CONFIG_Q)
    gates.apply_platform_settings(cfg)
    real_world.assert_process_environment(cfg)
    w = real_stages.build_world(cfg, repo, out.parent / "_prompt_check_unused", "registered", load_teachers=False, light=True)  # the tokenizer and WikiText-2 only; nothing is written
    downloads = real_stages.downloads_dir(cfg)
    dl = datagen.verify_downloads(downloads, repo / real_world.TATOEBA_RECORD, root=repo)
    corpus, _rec = datagen.load_corpus(downloads, dl["tatoeba"])
    ctx = pipeline.QContext(cfg=cfg, mode="registered", corpus=corpus, teachers={}, student_scores=lambda items, p: {}, run_dir=out.parent / "_prompt_check_unused")
    p = partition.build_partition(corpus, cfg, ctx.seeds, ctx.allowed)
    res = check(w.tok, p.panels, p.vocab, reference_word_types(corpus))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({**core.envelope("block_record", "Q"), "what": "prompt_check", **res}, indent=1, default=str), encoding="utf-8")
    return res
