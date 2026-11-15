# ruff: noqa: E501
"""The synthetic world for tests and the dry stage: stand-ins (a made-up translation pair, lexicon teachers, a WikiText-like text, a tiny tokenizer and a tiny student) fed to the same pre-freeze steps the
real data-generation step calls (``prefreeze.build_bundle``), producing the same ``DataBundle`` and from it the same ``World``. No real model, no real data, no result.
"""

from typing import Any

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
    return build_bundle(corpus, tok, student, teachers, text_val, text_train, sizes, WindowSpec.dry(), "test", replicates)


def build_synthetic_world(replicates: int = 2, *, updates: int | None = None, sizes: Sizes | None = None, merges: int = 60, data_seed_offset: int = 0, add_bos: bool = False) -> tuple[World, dict[str, Any]]:
    """Returns the world and the pre-freeze record."""
    bundle, rec = build_synthetic_bundle(replicates, sizes=sizes, merges=merges, data_seed_offset=data_seed_offset, add_bos=add_bos)
    return build_world(bundle, "test", replicates, RunConfig.dry(updates)), rec


def items_of(world: World, name: str) -> list[Item]:
    return world.partition.panels[name]
