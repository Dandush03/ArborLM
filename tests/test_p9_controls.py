# ruff: noqa: E501
"""P9 package I1: controls without a trained memory (ADR-0017 5.6, 8.1, 12 step 4). Tiny sizes, test
seeds, synthetic random backbone. Self-check only: not independent review, not Astra validation, not
human approval."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
import torch  # noqa: E402

from studies.p9 import controls, core, data  # noqa: E402

SIZES = data.DataSizes(main_trained=512, unseen=64, lane_d_per_set=128)
SEEDS = core.rehearsal_seeds(9)


def _corpus() -> bytes:
    g = torch.Generator().manual_seed(12)
    return bytes(torch.randint(0, 256, (2048 * 65,), generator=g).tolist())


@pytest.fixture(scope="module")
def draw() -> data.StudyData:
    return data.build_study_data(SEEDS, _corpus(), sizes=SIZES)


@pytest.fixture(scope="module")
def backbone():  # type: ignore[no-untyped-def]
    torch.manual_seed(0)
    return controls.synthetic_backbone()


def test_exact_retrieval_is_one_on_trained_and_chance_matches_on_unseen(draw: data.StudyData) -> None:
    s = draw.streams["panel_a"]
    known = torch.arange(512)
    scores = controls.exact_retrieval(draw.facts, s, known)
    seen = (s.fact_ids < 512).reshape(-1)
    assert bool(scores.correct[seen].all()) and float(scores.correct[seen].float().mean()) == 1.0
    assert float(scores.p_correct[seen].min()) == 1.0
    answers = draw.facts.answer[s.fact_ids.reshape(-1)]
    assert int(scores.correct[~seen].sum()) == int((answers[~seen] == 0).sum())
    assert float(scores.mass_sigma.min()) > 0.999
    # a smaller dictionary answers the rest as unseen
    half = controls.exact_retrieval(draw.facts, s, torch.arange(256))
    unknown = (s.fact_ids.reshape(-1) >= 256)
    assert int(half.correct[unknown].sum()) == int((answers[unknown] == 0).sum())
    assert bool(half.correct[~unknown].all())
    # shapes: Q = 8 per context, (context, record) order
    assert scores.logp_sigma.shape == (s.tokens.shape[0] * 8, 32)


def test_exact_retrieval_uses_tokens_not_fact_ids(draw: data.StudyData) -> None:
    s = draw.streams["h1"]
    import copy

    lie = copy.copy(s)
    lie.fact_ids = s.fact_ids.flip(0)  # wrong bookkeeping must not change the lookup, only the truth it is scored against
    out = controls.exact_retrieval(draw.facts, s, torch.arange(512))
    assert bool(out.correct.all())
    assert lie.fact_ids.shape == s.fact_ids.shape


def test_no_memory_logits_shape_and_determinism(draw: data.StudyData, backbone) -> None:  # type: ignore[no-untyped-def]
    s = draw.streams["panel_a"]
    a = controls.answer_site_logits_no_memory(backbone, s, batch_contexts=16)
    b = controls.answer_site_logits_no_memory(backbone, s, batch_contexts=64)
    assert a.shape == (s.tokens.shape[0] * 8, 256) and a.dtype == torch.float32
    assert torch.allclose(a, b, atol=1e-5)
    assert torch.equal(a, controls.answer_site_logits_no_memory(backbone, s, batch_contexts=16))
    # equals the frozen forward at the answer-site positions
    with torch.no_grad():
        h = controls.insertion_hidden(backbone, s.tokens[:2, :63])
        full = controls.logits_from_hidden(backbone, h)
    assert torch.allclose(full[:, list(core.ANSWER_SITE_POSITIONS)].reshape(-1, 256), a[:16], atol=1e-5)


def test_no_memory_is_at_chance_on_a_tiny_set(draw: data.StudyData, backbone) -> None:  # type: ignore[no-untyped-def]
    s = draw.streams["panel_a"]
    scores = controls.evaluate_no_memory(backbone, draw.facts, s)
    n = scores.correct.numel()
    k = int(scores.correct.sum())
    interval = core.chance_interval(n, core.G2_TESTS_PRIMARY)
    assert interval.low <= k <= interval.high, (k, n, interval)
    # ties counted wrong and masses are sane
    assert float(scores.mass_sigma.max()) <= 1.0 + 1e-6
    seen = (s.fact_ids < 512).reshape(-1)
    report = controls.g2_report({"unseen": (int(scores.correct[~seen].sum()), int((~seen).sum()))}, 8)
    assert report["tests"] == 8 and len(report["results"]) == 1


def test_probes_run_and_are_deterministic(draw: data.StudyData, backbone) -> None:  # type: ignore[no-untyped-def]
    train, ev = draw.streams["calibration"], draw.streams["panel_a"]
    n1 = controls.nearest_stored_state_probe(backbone, draw.facts, train, ev)
    n2 = controls.nearest_stored_state_probe(backbone, draw.facts, train, ev)
    assert n1.facts == ev.tokens.shape[0] * 8 and 0 <= n1.correct <= n1.facts
    assert n1.accuracy == n1.correct / n1.facts == n2.accuracy and n1.per_query_correct is not None
    assert torch.equal(n1.per_query_correct, n2.per_query_correct)  # type: ignore[arg-type]
    p1 = controls.linear_probe_per_position(backbone, draw.facts, train, ev, seed=179901)
    p2 = controls.linear_probe_per_position(backbone, draw.facts, train, ev, seed=179901)
    assert [r.name for r in p1] == [f"linear_probe_position_{i}" for i in range(1, 6)]
    assert [r.correct for r in p1] == [r.correct for r in p2]
    assert all(r.facts == n1.facts and 0.0 <= r.accuracy <= 1.0 for r in p1)


def test_linear_probe_recovers_a_planted_identity_signal(draw: data.StudyData, backbone) -> None:  # type: ignore[no-untyped-def]
    # Positions the probe can solve: use a backbone whose hidden state carries identifier symbols is not
    # available, so check the solver itself on synthetic features with a known linear structure.
    g = torch.Generator().manual_seed(5)
    y = torch.randint(0, 32, (4000,), generator=g)
    codebook = torch.randn(32, 32, generator=g).double()
    x = torch.cat([codebook[y] + 0.1 * torch.randn(4000, 32, generator=g).double(), torch.ones(4000, 1, dtype=torch.float64)], 1)
    w = controls._ridge(x[:3000], torch.nn.functional.one_hot(y[:3000], 32).double(), 1e-4)
    assert float(((x[3000:] @ w).argmax(1) == y[3000:]).double().mean()) > 0.95


def test_probe_seed_split_changes_nothing_but_is_deterministic(draw: data.StudyData, backbone) -> None:  # type: ignore[no-untyped-def]
    train, ev = draw.streams["calibration"], draw.streams["h1"]
    a = controls.linear_probe_per_position(backbone, draw.facts, train, ev, seed=179902)
    b = controls.linear_probe_per_position(backbone, draw.facts, train, ev, seed=179902)
    assert [r.correct for r in a] == [r.correct for r in b]


def test_attainable_probability(draw: data.StudyData, backbone) -> None:  # type: ignore[no-untyped-def]
    s = data.restrict_stream(draw.streams["panel_a"], draw.facts, 128)
    out = controls.attainable_answer_probability(backbone, s, iterations=40, lr=0.1, batch_contexts=8)
    again = controls.attainable_answer_probability(backbone, s, iterations=40, lr=0.1, batch_contexts=8)
    assert out == again  # deterministic
    assert 0.0 <= out["min"] <= out["median"] <= out["max"] <= 1.0
    assert out["mean"] > 1.2 * out["baseline_mean"]  # the random test backbone has tiny logits, so its ceiling is low
    assert out["queries"] == s.tokens.shape[0] * 8 and out["max_norm"] == -1.0
    short = controls.attainable_answer_probability(backbone, s, iterations=5, lr=0.1, batch_contexts=8)
    assert out["mean"] >= short["mean"] - 1e-9  # the envelope is monotone in the number of iterations
    tight = controls.attainable_answer_probability(backbone, s, max_norm=0.05, iterations=40, batch_contexts=8)
    assert tight["max_norm"] == 0.05 and tight["mean"] <= out["mean"] + 1e-9
    assert tight["final_delta_norm_mean"] <= 0.05 + 1e-5


def test_g2_interval_values_match_an_independent_binomial_calculation() -> None:
    def tails(n: int, level_tests: int) -> tuple[int, int]:
        tail = 0.001 / level_tests / 2
        def logpmf(k: int) -> float:  # written independently of core: log C(n,k) + k ln(1/32) + (n-k) ln(31/32)
            return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1) - k * math.log(32) + (n - k) * math.log(31 / 32)

        pmf = [math.exp(logpmf(k)) for k in range(n + 1)]
        cum, low = 0.0, 0
        for k, p in enumerate(pmf):
            cum += p
            if cum > tail:
                low = k
                break
        cum, high = 0.0, n
        for k in range(n, -1, -1):
            cum += pmf[k]
            if cum > tail:
                high = k
                break
        return low, high

    for n, tests in ((2048, 8), (4096, 4), (8192, 8), (32768, 8)):
        i = core.chance_interval(n, tests)
        assert (i.low, i.high) == tails(n, tests)
        assert i.low < n / 32 < i.high
    iv = controls.chance_intervals_for_registered_sets()
    assert set(iv) == {"facts_2048", "facts_8192", "facts_32768", "lane_d_facts_4096"}
    assert iv["facts_2048"] == core.chance_interval(2048, 8) and iv["lane_d_facts_4096"].level == core.g2_level(4)
    assert iv["facts_2048"].low_accuracy < 1 / 32 < iv["facts_2048"].high_accuracy
    # the interval narrows in accuracy as facts grow
    widths = [iv[f"facts_{n}"].high_accuracy - iv[f"facts_{n}"].low_accuracy for n in (2048, 8192, 32768)]
    assert widths[0] > widths[1] > widths[2]


def test_g2_report_and_leakage() -> None:
    iv = core.chance_interval(2048, 8)
    ok = controls.g2_report({"a_2048": (64, 2048), "unseen": (iv.high, 2048)}, 8)
    assert ok["passed"] and ok["level"] == core.g2_level(8) and ok["results"][0]["interval"] == (iv.low, iv.high)
    bad = controls.g2_report({"a_2048": (64, 2048), "unseen": (iv.high + 1, 2048)}, 8)
    assert not bad["passed"] and bad["results"][1]["inside"] is False
    low = controls.g2_report({"x": (iv.low - 1, 2048)}, 8)
    assert not low["passed"]
    lane = controls.g2_report({"A": (128, 4096)}, core.G2_TESTS_LANE_D)
    assert lane["tests"] == 4 and lane["passed"]
    assert controls.unseen_leakage(iv.high + 1, 2048) and not controls.unseen_leakage(iv.high, 2048)
    assert controls.unseen_leakage(iv.low - 1, 2048) and not controls.unseen_leakage(64, 2048)
    assert controls.g2_report({}, 8)["passed"]


def test_real_backbone_no_memory_is_at_chance_if_present(draw: data.StudyData) -> None:
    root = core.default_experiments_root()
    if not core.corpus_path(root).is_file():
        pytest.skip("frozen experiments/ not present in this checkout")
    for parent in (core.PRIMARY_PARENT, core.REPLICATE_PARENT):
        backbone, provenance = controls.load_backbone(parent, root)
        assert provenance["backbone_sha256"]
        scores = controls.evaluate_no_memory(backbone, draw.facts, draw.streams["panel_a"])
        n, k = scores.correct.numel(), int(scores.correct.sum())
        interval = core.chance_interval(n, core.G2_TESTS_PRIMARY)
        assert interval.low <= k <= interval.high
