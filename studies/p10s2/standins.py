# ruff: noqa: E501
"""The synthetic world for tests and the dry stage: stand-ins (a made-up translation pair, lexicon teachers, a WikiText-like text, a tiny tokenizer and a tiny student) fed to the same pre-freeze steps the
real data-generation step calls (``prefreeze.build_bundle``), producing the same ``DataBundle`` and from it the same ``World``. No real model, no real data, no result.
"""

from typing import Any

from . import core
from .data import Item, Sizes
from .model import StudentConfig, build_student
from .prefreeze import WindowSpec, build_bundle
from .synthetic import LexiconTeacher, lexicon, make_corpus, make_text, make_tokenizer, tgen
from .world import World
from .worldio import DataBundle, RunConfig, build_world


def build_synthetic_bundle(replicates: int = 2, *, sizes: Sizes | None = None, merges: int = 60, data_seed_offset: int = 0, add_bos: bool = False) -> tuple[DataBundle, dict[str, Any]]:
    """The pre-freeze steps on synthetic stand-ins. Returns the bundle (what the data files would hold) and the record of the steps."""
    sizes = sizes or Sizes.dry()
    corpus = make_corpus(tgen(data_seed_offset + 1, "synthetic corpus"), sentences=1500)
    text_val = make_text(tgen(data_seed_offset + 2, "synthetic wikitext validation"), n_words=1500, marker_rate=0.06)
    text_train = make_text(tgen(data_seed_offset + 3, "synthetic wikitext train"), n_words=1200, marker_rate=0.02)
    tok = make_tokenizer(corpus, text_val, merges=merges, add_bos=add_bos)
    student = build_student(StudentConfig.tiny(tok.vocab_size), tgen(data_seed_offset + 4, "stand-in student weights"), std=0.4)  # larger weights than the default so that logits are not near-uniform
    _, de_map, fr_map = lexicon(25)
    teachers = {"A": LexiconTeacher("stand-in German", de_map, tgen(data_seed_offset + 5, "teacher A noise")), "B": LexiconTeacher("stand-in French", fr_map, tgen(data_seed_offset + 6, "teacher B noise"))}
    bundle, rec = build_bundle(corpus, tok, student, teachers, text_val, text_train, sizes, WindowSpec.dry(), "test", replicates)
    if not bundle.panels.get("E_open"):
        # The synthetic corpus has no evaluation sentence with an out-of-vocabulary word at these sizes, so E_open would be empty and never scored by any test, the dry stage or the exercise (re-check B, N1). The
        # stand-in E_open is made from the first D_cal sentences with one out-of-vocabulary pseudo-word appended to the English and to every reference, an identity group of -1 and their own keys (so no gate
        # of G1 can see a shared group or reference); prompts are built with the stand-in tokenizer and both teachers translate them. Mechanics only: no number from it is a result.
        from dataclasses import replace

        from .filtering import run_teacher
        from .text import normalize
        from .world import ExampleBank

        k = min(sizes.panel_open, len(bundle.panels["D_cal"]))
        vocab_index = {w: i for i, w in enumerate(bundle.vocab)}
        bank = ExampleBank.from_records(bundle.bank_records, vocab_index)
        items = []
        for src in bundle.panels["D_cal"][:k]:
            en = f"{src.en} qzxq"
            items.append(replace(src, key=normalize(en), en=en, refs={c: tuple(f"{r} qzyq" for r in v) for c, v in src.refs.items()}, group=-1))
            for c in core.TASKS:
                if c in src.refs:
                    bank.build_from_tokenizer(tok, vocab_index, c, en, None)
        bundle.panels["E_open"] = items
        bundle.bank_records = bank.to_records()
        for c in core.TASKS:
            bundle.teacher_outputs[c]["E_open"] = [o.text for o in run_teacher(teachers[c], [i.en for i in items])]
        rec["stand_in_e_open"] = f"E_open is the first {k} D_cal sentences with an out-of-vocabulary pseudo-word appended (the synthetic corpus has no out-of-vocabulary evaluation sentence)"
    return bundle, rec


def build_synthetic_world(replicates: int = 2, *, updates: int | None = None, sizes: Sizes | None = None, merges: int = 60, data_seed_offset: int = 0, add_bos: bool = False) -> tuple[World, dict[str, Any]]:
    """Returns the world and the pre-freeze record."""
    bundle, rec = build_synthetic_bundle(replicates, sizes=sizes, merges=merges, data_seed_offset=data_seed_offset, add_bos=add_bos)
    return build_world(bundle, "test", replicates, RunConfig.dry(updates)), rec


def items_of(world: World, name: str) -> list[Item]:
    return world.partition.panels[name]
