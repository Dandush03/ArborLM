# ruff: noqa: E501
"""The pre-freeze steps as one function of its inputs (ADR-0022 sections 4.3, 5.2, 5.3, 6.4, 14.2): partitions, teacher generation, filter fitting, qualification, sufficiency, training draws, G1,
the example bank, the general-language windows, the frozen subsamples. ``build_bundle`` produces a ``DataBundle`` (the content of the frozen data files).

The inputs are interfaces: a ``Corpus``, a ``ReferenceTokenizer``, the study's student, ``Teacher`` objects, the two WikiText-2 texts. The synthetic stand-ins (``standins``) and the real data-generation
step (``datagen``, unexecuted here) fill them differently and call the same code, so the real-data steps add no scientific code.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch

from . import core
from .combined import draw_sigma, duplicate_normalized, pair_list, pairs_digest
from .data import (
    CorpusLike,
    Sizes,
    Streams,
    TrainItem,
    build_partition,
    draw_streams,
    fixed_subsample,
    gate_g1,
    panel_sufficiency,
    plan_generation,
    replicate_overlap,
    sufficiency_after_filter,
    timing_indices,
    tokenizer_record_sentences,
)
from .evaluate import truncation_percentile
from .filtering import (
    FilterFit,
    Teacher,
    accepted_pool,
    check_filter,
    fit_filter,
    mean_teacher_score,
    qualify,
    run_teacher,
)
from .model import Student
from .retrieval import TfidfIndex, r_icl_prompt_items
from .text import chrf_item, normalize
from .tokenization import (
    ByteDecoder,
    ReferenceTokenizer,
    check_roundtrip,
    check_segments_vs_whole,
    tokenize_segment,
)
from .windows import cut_windows, select_windows
from .world import ExampleBank
from .worldio import DataBundle, seen_order


@dataclass(frozen=True)
class WindowSpec:
    window_tokens: int
    decision_token: int
    windows: int
    marker_like: int
    ablation_subsample: int
    default_max_new: int

    @staticmethod
    def registered() -> "WindowSpec":
        d = core.CFG["data"]
        return WindowSpec(d["general_window_tokens"], d["router_decision_token"], d["general_windows"], d["general_windows_marker_like"], d["ablation_subsample"], d["generation_new_tokens"])

    @staticmethod
    def dry() -> "WindowSpec":
        d = core.CFG["dry"]
        return WindowSpec(d["window_tokens"], d["router_decision_token"], d["general_windows"], d["general_windows_marker_like"], d["ablation_subsample"], d["max_new_tokens"])


Tick = Callable[[str], None]
Crosscheck = Callable[[Sequence[tuple[str, Sequence[str]]]], dict[str, Any]]


def build_bundle(
    corpus: CorpusLike, tok: ReferenceTokenizer, student: Student, teachers: Mapping[str, Teacher], text_val: str, text_train: str, sizes: Sizes, spec: WindowSpec, mode: str, replicates: int,
    *, crosscheck: Crosscheck | None = None, tick: Tick | None = None, provenance: Mapping[str, Any] | None = None,
) -> tuple[DataBundle, dict[str, Any]]:  # fmt: skip
    """Run the pre-freeze steps. ``mode`` is ``registered-data`` for the real step and ``test`` for the stand-ins (the seed function refuses anything else). Returns the bundle and the step record
    (partition counts, panel hashes, sufficiency, filter fits and checks, qualification, G1, replicate overlap, the tokenization checks, the timing items, the teachers' tokenizer records).

    ``crosscheck`` (the chrF cross-check against sacrebleu on 1,000 pairs of Q) and ``tick`` (called between the long steps so that the caller can enforce its stage cap) are given by the data-generation
    step; ``provenance`` (for example the WikiText file digests) is stored with the data manifest. ``text_val`` is the WikiText-2 validation text (GEN windows only, section 6.4) and ``text_train`` the
    train text; both are the local parquet files joined in file order (audit A-B3)."""
    stamp: Tick = tick if tick is not None else (lambda _what: None)
    part = build_partition(corpus, mode, sizes)
    vocab_index = part.vocab_index
    rec: dict[str, Any] = {"partition": part.counts, "panel_hashes": part.panel_hashes(), "sufficiency_pools": panel_sufficiency(part)}
    decoder = ByteDecoder(tok.token_bytes())
    bank = ExampleBank()
    nl = tuple(tokenize_segment(tok, "\n").ids)
    gen_sources = plan_generation(part, mode)
    # the listed seeds drawn once, here: 220909 (the sentences of each teacher's tokenizer record) and 220908 (the timing benchmark's items); neither is drawn by a later stage (audit M8)
    record_sentences = tokenizer_record_sentences(gen_sources, core.CFG["data"]["tokenizer_record_sentences"], mode)
    timing = timing_indices({n: len(part.panels[n]) for n in ("E_A", "E_B")}, core.CFG["budget"]["timing_items"], mode)
    rec["tokenizer_record"] = tokenizer_records(teachers, record_sentences)
    stamp("teacher generation on the training sources")
    outs = {}
    for c in core.TASKS:
        outs[c] = run_teacher(teachers[c], [i.en for i in gen_sources[c]])
        stamp(f"teacher {c} on its sources")
    q_fit_out = {t: run_teacher(teachers[t], [i.en for i in part.panels["Q_fit"]]) for t in core.TASKS}
    q_chk_out = {t: run_teacher(teachers[t], [i.en for i in part.panels["Q_check"]]) for t in core.TASKS}
    stamp("teachers on Q")
    rec["outputs_with_newline"] = {c: sum("\n" in o.text for o in [*outs[c], *q_fit_out[c], *q_chk_out[c]]) for c in core.TASKS}  # never accepted (``filtering.accepts``); counted
    rec["score_checks"] = {c: getattr(teachers[c], "score_record", None) for c in core.TASKS}  # the explicit score against the library's (audit M7), filled by the real teachers
    fits: dict[str, FilterFit] = {}
    checks: dict[str, dict[str, Any]] = {}
    accepted: dict[str, list[TrainItem]] = {}
    eval_refs = {normalize(r) for n in ("E_A", "E_B", "E_C", "E_open") for it in part.panels[n] for refs in it.refs.values() for r in refs}
    dropped = {}
    for c in core.TASKS:
        refs_fit = [list(i.refs[c]) for i in part.panels["Q_fit"]]
        refs_chk = [list(i.refs[c]) for i in part.panels["Q_check"]]
        fits[c] = fit_filter(q_fit_out[c], refs_fit)
        setting = fits[c].setting
        if setting is None:
            checks[c] = {"ok": False, "accepted": 0, "precision": float("nan"), "wilson": [0, 1], "correct": 0}
            accepted[c], dropped[c] = [], 0
        else:
            checks[c] = check_filter(setting, q_chk_out[c], refs_chk, sizes.check_min_accepted)
            accepted[c], dropped[c] = accepted_pool(outs[c], gen_sources[c], setting, eval_refs)
    q_items = [*part.panels["Q_fit"], *part.panels["Q_check"]]
    t_scores = {t: {c: mean_teacher_score([*q_fit_out[t], *q_chk_out[t]], [list(i.refs[c]) for i in q_items]) for c in core.TASKS} for t in core.TASKS}
    for c in core.TASKS:
        for it in q_items:
            bank.build_from_tokenizer(tok, vocab_index, c, it.en, None)
    suff = sufficiency_after_filter(accepted, part.gold_pool, sizes)
    rec["sufficiency_after_filter"] = suff
    # pool-level G1 (a registered replicate seed is not observed in the data step; the stream-level G1 and the replicate overlap are computed by the gates stage and the registered run)
    gold_items = {c: [TrainItem(i.key, i.en, i.refs[c][0], i.group) for i in part.gold_pool[c]] for c in core.TASKS}
    pool_stream = Streams(dict(accepted), gold_items, 0, {}, 0)
    rec["g1"] = gate_g1(part, [pool_stream], {c: [x.target for x in accepted[c]] for c in core.TASKS}, pool_level=True)
    rec["g1"]["level"] = "pools (accepted outputs and gold pool); streams are checked at the gates stage"
    streams = [draw_streams(core.SeedPlan("test", r), accepted, part.gold_pool, sizes) for r in range(replicates)] if (mode == "test" and suff["ok"]) else []
    rec["overlap"] = replicate_overlap(streams) if streams else {}
    for c in core.TASKS:  # every item any replicate may draw: the bank holds the segment ids of the whole accepted pool and the whole gold pool
        for x in [*accepted[c], *gold_items[c]]:
            bank.build_from_tokenizer(tok, vocab_index, c, x.en, x.target)
            bank.build_from_tokenizer(tok, vocab_index, c, x.en, None)
    for n in ("E_A", "E_B", "E_C", "D_cal", "D_con", "Q_fit", "Q_check"):
        for it in part.panels[n]:
            for c in core.TASKS:
                if c in it.refs:
                    bank.build_from_tokenizer(tok, vocab_index, c, it.en, None)
    wl = cut_windows(tok, text_val, vocab_index, spec.window_tokens, spec.decision_token)
    windows = select_windows(wl, {"marker": spec.marker_like, "ordinary": spec.windows - spec.marker_like}, core.partition_gen(mode, "gen_windows", "GEN window selection"))
    ablation_keys = {name: [i.key for i in fixed_subsample(part.panels[name], spec.ablation_subsample, mode, "ablation_subsample")] for name in ("E_A", "E_B")}
    # the new-token limit: the 99.5th percentile of the gold references of D_cal, German and French pooled (reading, PENDING LEAD REVIEW: one limit for both languages, or one per language)
    max_new = max(truncation_percentile([len(tok.encode(" " + r)) + len(nl) for it in part.panels["D_cal"] for c in core.TASKS for r in it.refs.get(c, ())] or [spec.default_max_new]), 4)
    s0 = {
        c: sum(chrf_item(decoder.answer_text(student.greedy(torch.tensor([list(bank.prompt(c, it.en).prompt_ids)]), add=None, adapter=None, max_new=max_new, stop_bytes=decoder.table)), list(it.refs[c])) for it in q_items) / max(1, len(q_items))
        for c in core.TASKS
    }  # fmt: skip
    qual = qualify(t_scores, s0, fits, checks, {c: len(accepted[c]) for c in core.TASKS}, sizes.accepted_per_replicate)
    rec["qualification"] = {"ok": qual["ok"], "failed": qual["failed"], "detail": qual["detail"], "outcome": qual["outcome"]}
    rec["filter"] = {c: fits[c].to_json() for c in core.TASKS}
    rec["dropped_eval_equal"] = dropped
    stamp("filter, qualification")
    teacher_outputs = {
        c: {name: [o.text for o in run_teacher(teachers[c], [i.en for i in part.panels[pn]])] for name, pn in (("E_" + c, "E_" + c), ("D_cal", "D_cal"), ("E_C", "E_C"))}
        for c in core.TASKS
    }  # fmt: skip  (both teachers generate on every E_C sentence: the combined-tasks addendum)
    n_c = len(part.panels["E_C"])
    sigma = draw_sigma(n_c, mode)  # the listed seed 220911, drawn once, here, after E_C is built
    pairs = pair_list(n_c, sigma)
    rec["c1_pairing"] = {"n": n_c, "pairs_sha256": pairs_digest(pairs), "duplicate_normalized_english": duplicate_normalized([i.key for i in part.panels["E_C"]])}
    rec["combined_whole_string"] = check_combined_whole_string(tok, part.panels["E_C"], pairs)
    stamp("teacher outputs on the stored panels")
    if crosscheck is not None:  # the chrF cross-check against sacrebleu on the 1,000 pairs of Q: teacher A's outputs against the German references (audit B2, step 6)
        rec["chrf_crosscheck"] = crosscheck([(o.text, list(i.refs["A"])) for o, i in zip([*q_fit_out["A"], *q_chk_out["A"]], q_items, strict=True)])
    rec["tokenization"] = tokenization_checks(tok, decoder, bank, accepted, gold_items, part, teacher_outputs)
    stamp("tokenization checks")
    bundle = DataBundle(
        student.cfg, {k: v.detach().clone() for k, v in student.state_dict().items()}, tok.token_bytes(), nl, sizes, part.vocab, part.panels, part.gold_pool, accepted, seen_order(accepted, mode), ablation_keys,
        bank.to_records(), windows, tok.encode(text_train), teacher_outputs, max_new, {
            "conventions": {"bos": tok.bos_id, "segment": "label, source with leading space, newline, task marker; NFC text"}, "c1_pairing": {"sigma": sigma, "pairs_sha256": pairs_digest(pairs), "seed_name": "c1_pairing (220911)"},
            "timing_items": timing, "tokenizer_record": rec["tokenizer_record"], "seed_table": core.seed_table(), "provenance": dict(provenance or {}),
        },
    )  # fmt: skip
    return bundle, rec



def tokenizer_records(teachers: Mapping[str, Teacher], sentences: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """The 100-sentence tokenizer record of each teacher (section 4.1; sentences drawn with 220909): what the real teacher's tokenizer made of the sentences (a teacher without the method, a
    synthetic stand-in, records the sentences only). Frozen with the data; any later teacher run must reproduce it."""
    out: dict[str, Any] = {}
    for c in core.TASKS:
        t = teachers[c]
        fn = getattr(t, "tokenizer_record", None)
        out[c] = {"teacher": t.name, "revision": t.revision, "sentences": list(sentences[c]), "records": fn(list(sentences[c])) if callable(fn) else None}
    return out


def verify_tokenizer_record(teacher: Teacher, record: Mapping[str, Any]) -> dict[str, Any]:
    """A later teacher run reproduces the frozen record: the same ids for the same sentences. A teacher without the method, or a record without entries, does not verify."""
    fn = getattr(teacher, "tokenizer_record", None)
    if not callable(fn) or record.get("records") is None:
        return {"ok": False, "reason": "no record or no tokenizer method"}
    again = fn(list(record["sentences"]))
    same = again == record["records"]
    return {"ok": bool(same), "n": len(record["sentences"])}


def _brief(res: Mapping[str, Any], limit: int = 20) -> dict[str, Any]:
    bad = list(res.get("mismatches", res.get("failures", [])))
    return {"n": res["n"], "mismatch_count": len(bad), "mismatch_rate": len(bad) / res["n"] if res["n"] else 0.0, "first": bad[:limit]}


def tokenization_checks(
    tok: ReferenceTokenizer, decoder: ByteDecoder, bank: ExampleBank, accepted: Mapping[str, Sequence[TrainItem]], gold_items: Mapping[str, Sequence[TrainItem]], part: Any, teacher_outputs: Mapping[str, Mapping[str, Sequence[str]]],
) -> dict[str, Any]:  # fmt: skip
    """Tests (a) and (b) of section 14.2 step 4 on the real tokenizer (audit B2):

    (a) segment ids against whole-string ids for every training row (the accepted pool and the gold pool, with their targets), for every prompt in the bank (evaluation, calibration and Q prompts)
    and for every R-icl prompt (the 4 nearest accepted pairs, drawn from the whole accepted pool of the capability, before the query; a replicate's own draw is a subset, the layout is the same);
    0 mismatches are required on prompts and R-icl prompts, target mismatches are listed.
    (b) ``decode(encode(x)) == x`` for every reference and every accepted teacher output, and for every stored teacher output.
    ``required_ok`` is the stop condition of the data-generation step."""
    train_inputs = [bank.train(c, x).segments for c in core.TASKS for x in [*accepted[c], *gold_items[c]]]
    prompts = [ex.segments for ex in bank.examples.values() if ex.target_len == 0]
    icl: list[Any] = []
    for c in core.TASKS:
        pool = list(accepted[c])
        if not pool:
            continue
        idx = TfidfIndex(pool)
        for it in part.panels["E_" + c]:
            demos = r_icl_prompt_items(pool, it.en, 4, idx)
            icl.append([seg for d in demos for seg in bank.train(c, d).segments] + list(bank.prompt(c, it.en).segments))
    a_train, a_prompts, a_icl = (check_segments_vs_whole(x, tok) for x in (train_inputs, prompts, icl))
    refs = [r for items in [*part.panels.values(), *part.gold_pool.values()] for it in items for rs in it.refs.values() for r in rs]
    texts = [*refs, *[x.target for c in core.TASKS for x in accepted[c]], *[t for per in teacher_outputs.values() for outs in per.values() for t in outs]]
    b = check_roundtrip(texts, tok, decoder)
    out: dict[str, Any] = {"a_training_rows": _brief(a_train), "a_prompts": _brief(a_prompts), "a_icl_prompts": _brief(a_icl), "b_roundtrip": _brief(b)}
    out["b_failure_examples"] = [texts[i] for i in out["b_roundtrip"]["first"]]
    out["required_ok"] = out["a_prompts"]["mismatch_count"] == 0 and out["a_icl_prompts"]["mismatch_count"] == 0
    return out


def check_combined_whole_string(tok: ReferenceTokenizer, items: Sequence[Any], pairs: Sequence[Any]) -> dict[str, Any]:
    """Extension of test (a) to the combined layouts (addendum section 4.4): for every C1 item, with the first reference of s1 in the item's first language (tokenized with its leading space) in place
    of a1, and for every C2 item likewise, the concatenation of segment ids is compared with the whole-string ids. A mismatch at a segment boundary or inside a template piece or a source is required to
    be 0 (the consequence of a prompt mismatch in test (a)); a mismatch inside the substituted reference is listed and requires nothing. References are used as text only."""
    def seg(text: str) -> list[int]:
        return list(tok.encode(text))

    def one(parts: Sequence[str], ref_span: tuple[int, int]) -> str | None:
        whole = "".join(parts)
        wids, offs = tok.encode_offsets(whole)
        cat = [i for p in parts for i in seg(p)]
        if wids == cat:
            return None
        d = next((k for k, (a, b) in enumerate(zip(wids, cat, strict=False)) if a != b), min(len(wids), len(cat)) - 1)
        start = offs[min(d, len(offs) - 1)][0]
        return "reference" if ref_span[0] <= start < ref_span[1] else "required"

    required: list[str] = []
    listed = 0
    checked = 0
    lang = {"A": "German", "B": "French"}
    for p in pairs:
        s1, s2 = items[p.i1], items[p.i2]
        ref = " " + s1.refs[p.t1][0]
        parts = ["English:", " " + s1.en, "\n", lang[p.t1] + ":", ref, "\n", "English:", " " + s2.en, "\n", lang[p.t2] + ":"]
        a = len("".join(parts[:4]))
        res = one(parts, (a, a + len(ref)))
        checked += 1
        if res == "required":
            required.append(f"C1 item {p.j}")
        elif res == "reference":
            listed += 1
    for i, s in enumerate(items):
        ref = " " + s.refs["A"][0]
        parts = ["English:", " " + s.en, "\n", "German:", ref, "\n", "French:"]
        a = len("".join(parts[:4]))
        res = one(parts, (a, a + len(ref)))
        checked += 1
        if res == "required":
            required.append(f"C2 item {i}")
        elif res == "reference":
            listed += 1
    return {"checked": checked, "required_mismatches": required, "listed_inside_reference": listed, "ok": not required}


def prefreeze_summary(rec: Mapping[str, Any]) -> dict[str, Any]:
    """What the label rule reads from the pre-freeze record: whether the study stops before the freeze (TRANSFER-INCONCLUSIVE: TEACHERS-NOT-QUALIFIED or DATA-INSUFFICIENT; section 4.3, 5.2), and whether the
    training material is teacher-only (every training item is an accepted teacher output on a sentence without gold in that language, and G1 holds on the pools)."""
    stops = [rec[k]["outcome"] for k in ("qualification", "sufficiency_pools", "sufficiency_after_filter") if rec.get(k, {}).get("outcome")]
    g1_ok = bool(rec.get("g1", {}).get("ok", False))
    tok_ok = bool(rec.get("combined_whole_string", {}).get("ok", False))
    return {"stop": stops[0] if stops else None, "teacher_only": g1_ok and not stops, "g1_pool_level_ok": g1_ok, "combined_whole_string_ok": tok_ok}


def tokenization_required_ok(rec: Mapping[str, Any]) -> bool:
    """Whether test (a) of section 14.2 step 4 held on every prompt and R-icl prompt (0 mismatches required). Absent from a record means not shown: False. The freeze reads it beside
    ``prefreeze_summary`` (it is a separate function so that the summary keeps its shape)."""
    return bool(rec.get("tokenization", {}).get("required_ok", False))
