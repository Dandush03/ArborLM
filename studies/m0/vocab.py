# ruff: noqa: E501
"""Word lists for the generators. Fixed, sorted, unique (a test asserts it)."""

from __future__ import annotations

NAMES: tuple[str, ...] = tuple(
    sorted(
        set(
            """Ada Ben Cara Dev Eli Fay Gus Hana Ivo Jade Kai Lena Milo Nora Omar Pia Quinn Rex Sia Tom Uma Vic Wren Xavi Yara Zed
Alma Bram Cleo Dion Elsa Finn Gita Hugo Iris Joss Kira Leo Maya Nico Orla Pablo Rhea Sam Tara Ulf Vera Walt Xena Yuri Zoe
Abel Bea Cyrus Dara Emil Fern Glen Hope Igor Jana Kurt Lila Marc Neva Otto Pearl Raul Sven Tess Uri Vida Wade Yan Zara
Anja Boris Cass Dell Edna Flynn Greta Hank Ines Jules Kenji Lars Mona Ned Opal Pete Rosa Stan Thea Ugo Viv Will Yves Zita
Alva Bruno Carla Dmitri Esme Felix Gwen Hal Ivy Jon Kate Liam Nell Oscar Pru Reed Sean Tina Uzi Vance Wanda Xan Zane""".split()
        )
    )
)

OBJECTS: tuple[str, ...] = (
    "apple", "book", "candle", "compass", "drum", "feather", "flute", "globe", "hammer", "kettle", "lantern", "mirror",
    "needle", "orange", "pencil", "quilt", "ribbon", "scarf", "spoon", "teapot", "umbrella", "violin", "whistle", "yo-yo",
)

TOWNS: tuple[str, ...] = (
    "Arden", "Brook", "Calder", "Dunmore", "Eastvale", "Fenwick", "Garth", "Harrow", "Ivybridge", "Kelso", "Larkin", "Marlow",
    "Norwick", "Oakham", "Penrith", "Quarry", "Ravenna", "Selby", "Thornbury", "Upton", "Vale", "Westmere", "Yarrow", "Zennor",
)

_SYL = ("ba", "be", "bi", "bo", "da", "de", "di", "do", "ka", "ke", "ki", "ko", "la", "le", "li", "lo", "ma", "me", "mi", "mo",
        "na", "ne", "ni", "no", "ra", "re", "ri", "ro", "sa", "se", "si", "so", "ta", "te", "ti", "to", "va", "ve", "vi", "vo",
        "za", "ze", "zi", "zo")
# invented words (two syllables plus a closing consonant); 44 * 44 * 4 distinct words, deterministic order
PSEUDO: tuple[str, ...] = tuple(sorted(a + b + c for a in _SYL for b in _SYL for c in ("k", "n", "r", "x") if a != b))

COLOURS: tuple[str, ...] = ("red", "blue", "green", "yellow", "purple", "orange", "white", "black")
SHAPES: tuple[str, ...] = ("round", "square", "triangular", "hexagonal", "oval")
MARKS: tuple[str, ...] = ("a star", "a stripe", "a dot", "a cross")
PETS: tuple[str, ...] = ("cat", "dog", "parrot", "rabbit", "turtle", "goldfish", "hamster")
EVENTS: tuple[str, ...] = (
    "the concert", "the harvest fair", "the council vote", "the bridge opening", "the school play", "the boat race",
    "the market day", "the book sale", "the town parade", "the chess final", "the film night", "the bake-off",
    "the lecture", "the cycle tour", "the music recital", "the flower show", "the quiz night", "the art auction",
)
