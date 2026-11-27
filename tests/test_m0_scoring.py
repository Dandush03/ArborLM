# ruff: noqa: E501
"""M0 stage I0-a: scorers and answer grammars (ADR-0033 section 7). The hand labels below are written by the
implementer who wrote the scorer, so they are NOT the registered labels (which come from a context that did not write
the scorer, on real outputs). Self-checked only."""

from __future__ import annotations

from studies.m0.scoring import (
    HandLabel,
    chance_level,
    check_hand_labels,
    draw_label_sample,
    extract,
    normalise_answer,
    score,
    score_any,
)

C, I_, F, L = "correct", "incorrect", "format_failure", "limit_hit"

CASES = [
    # raw, finish, type, gold, fmt, label
    ("Let me think.\nAnswer: 42", "stop", "number", "42", 0, C),
    ("Answer: 42.", "stop", "number", "42", 0, C),
    ("Answer: 1,234", "stop", "number", "1234", 0, C),
    ("Answer: 12.50", "stop", "number", "12.5", 0, C),
    ("Answer: 12.5", "stop", "number", "12.50", 0, C),
    ("Answer: $12.5", "stop", "number", "12.5", 0, F),
    ("Answer: 41", "stop", "number", "42", 0, I_),
    ("Answer: 41\nAnswer: 42", "stop", "number", "42", 0, C),
    ("Answer: 42\nAnswer: 41", "stop", "number", "42", 0, I_),
    ("so the answer: 42", "stop", "number", "42", 0, F),
    ("The result is 42", "stop", "number", "42", 0, F),
    ("Answer:", "stop", "number", "42", 0, F),
    ("Answer:   ", "stop", "number", "42", 0, F),
    ("Step 1 ... still working", "length", "number", "42", 0, L),
    ("Step 1 ... still working", "stop", "number", "42", 0, F),
    ("Answer: 42 apples", "stop", "number", "42", 0, F),
    ("Answer: 42 apples", "length", "number", "42", 0, L),
    ("Answer: 42 (truncated by the limit", "length", "number", "42", 0, L),
    ("Final answer: yes", "stop", "ynu", "yes", 1, C),
    ("FINAL ANSWER:   Cannot   be determined.", "stop", "ynu", "cannot be determined", 1, C),
    ("Answer: maybe", "stop", "ynu", "yes", 0, F),
    ("Answer: no", "stop", "yn", "yes", 0, I_),
    ("Answer: cannot be determined", "stop", "yn", "yes", 0, F),
    ("#### C", "stop", "letter", "C", 2, C),
    ("#### c", "stop", "letter", "C", 2, C),
    ("#### (C)", "stop", "letter", "C", 2, F),
    ("#### K", "stop", "letter", "C", 2, F),
    ("#### B", "stop", "letter", "C", 2, I_),
    ("Answer: Ada", "stop", "name", "Ada", 0, C),
    ("Answer: ada.", "stop", "name", "Ada", 0, C),
    ("Answer: Bea", "stop", "name", "Ada", 0, I_),
    ("Answer: the concert", "stop", "text", "the concert", 0, C),
    ("Answer: 3, 5, 9", "stop", "list", "3, 5, 9", 0, C),
    ("Answer: 3,5,9", "stop", "list", "3, 5, 9", 0, C),
    ("Answer: [3, 5, 9]", "stop", "list", "3, 5, 9", 0, F),
    ("Answer: 3, 9, 5", "stop", "list", "3, 5, 9", 0, I_),
    ("Answer: [1, 2]", "stop", "line", "[1, 2]", 0, C),
    ("Answer: HELLO", "stop", "line", "hello", 0, C),
    ("Answer: north", "stop", "word", "north", 0, C),
    ("  answer :  7", "stop", "number", "7", 0, C),
    ("1. 7\n2. answer: 7 is it", "stop", "number", "7", 0, F),
]


def test_hand_labelled_cases_agree_with_the_scorer() -> None:
    labels = [HandLabel(*c) for c in CASES]
    assert len(labels) >= 40
    assert check_hand_labels(labels) == []


def test_the_hand_label_check_reports_a_disagreement() -> None:
    bad = [HandLabel("Answer: 41", "stop", "number", "42", 0, C)]
    assert check_hand_labels(bad) == [(0, C, I_)]


def test_extraction_takes_the_last_marker_on_its_own_line() -> None:
    assert extract("Answer: 1\nblah\nAnswer: 2", 0) == "2"
    assert extract("x Answer: 1", 0) is None
    assert extract("Answer:", 0) is None
    assert extract("#### 5", 0) is None and extract("#### 5", 2) == "5"


def test_normalisation_rules() -> None:
    assert normalise_answer("  The   Answer. ") == "the answer"
    assert normalise_answer("3.") == "3"
    assert normalise_answer("3..") == "3."


def test_public_free_text_scoring_is_exact_match_against_any_alias() -> None:
    assert score_any("Answer: Paris", "stop", ["paris", "Paris, France"], 0).score == 1
    assert score_any("Answer: Paris, France.", "stop", ["paris", "Paris, France"], 0).score == 1
    assert score_any("Answer: the city of Paris", "stop", ["paris"], 0).score == 0
    assert score_any("none", "length", ["paris"], 0).status == L


def test_chance_level_is_the_item_mean_of_one_over_k() -> None:
    assert chance_level([4, 4, None, None]) == 0.125
    assert chance_level([3]) == 1 / 3
    assert chance_level([None, None]) == 0.0


def test_label_sample_is_registered_stratified_and_deterministic() -> None:
    recs = {"A": [f"a{i}" for i in range(100)], "B": [f"b{i}" for i in range(100)], "C": [f"c{i}" for i in range(100)]}
    s1, s2 = draw_label_sample(recs, 200), draw_label_sample(recs, 200)
    assert s1 == s2 and len(s1) == 200
    per = {k: sum(1 for sysname, _ in s1 if sysname == k) for k in recs}
    assert max(per.values()) - min(per.values()) <= 1
    assert len({x for x in s1}) == len(s1)
    assert draw_label_sample(recs, 30, seed=400014) != draw_label_sample(recs, 30)


def test_scores_are_zero_or_one_and_status_matches() -> None:
    for raw, fin, ty, gold, fmt, _ in CASES:
        s = score(raw, fin, ty, gold, fmt)
        assert s.score in (0, 1)
        assert (s.score == 1) == (s.status == C)
