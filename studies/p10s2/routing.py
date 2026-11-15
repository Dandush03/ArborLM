# ruff: noqa: E501
"""The keyword-level router and its training recipe (ADR-0022 sections 5.4, 6.4).

Three router keys (A, B, none; for an ST1 router one task and none), cosine scores, a learned 16 x width projection of the student's hidden state at the output of block L of a memory-free
pass, top-1. Trained with route labels: the task prompts of the current snapshot's training streams as the task classes, WikiText-2 *train* prefixes as "none". The recipe (all quoted from
section 5.4): AdamW, learning rate 0.001, 500 updates of batch 64; every batch holds the same number of examples of each class as nearly as the batch allows, the remainder going to "none";
the "none" prefixes are consecutive non-overlapping 64-token pieces of the tokenized train file, 8,000 of them sampled with seed +3; the first 4,000 sampled keep their 64 tokens, each of
the other 4,000 keeps its first tokens up to a length drawn, with replacement, from the token lengths of the task prompts of that router's streams; the loss is cross-entropy over the cosine
scores divided by the read temperature 0.2; the projection and then the router keys are drawn from N(0, 0.02) by one generator seeded +3 and every router is trained from that initialization
(never continued from an earlier stage). The +3 generator draws, in order: initialization, the prefixes, their lengths, the batch order.
The router depends on the replicate and on the set of tasks, not on the arm. It is a keyword-level classifier; a pass says nothing about fine-grained addressing.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from arborlm.io import sha256

from . import core
from .model import Student, tensor_sha
from .tokenization import Example


class Router(nn.Module):
    def __init__(self, tasks: Sequence[str], width: int, generator: torch.Generator) -> None:
        super().__init__()
        self.tasks = tuple(tasks)
        self.proj = nn.Parameter(core.CFG["router"]["init_std"] * torch.randn(core.KEY_WIDTH, width, generator=generator))
        self.keys = nn.Parameter(core.CFG["router"]["init_std"] * torch.randn(len(self.tasks) + 1, core.KEY_WIDTH, generator=generator))

    @property
    def classes(self) -> tuple[str, ...]:
        return (*self.tasks, "none")

    def scores(self, h: Tensor) -> Tensor:
        z = F.normalize(h @ self.proj.t(), dim=-1)
        return z @ F.normalize(self.keys, dim=-1).t()

    @torch.no_grad()
    def predict(self, h: Tensor) -> list[str]:
        return [self.classes[int(i)] for i in torch.argmax(self.scores(h), dim=-1).tolist()]

    def state_hash(self) -> str:
        return sha256((tensor_sha(self.proj) + tensor_sha(self.keys)).encode())


@torch.no_grad()
def hidden_at_ends(student: Student, layer: int, sequences: Sequence[Sequence[int]], positions: Sequence[int] | None = None, batch: int = 64) -> Tensor:
    """The output of block ``layer`` of a memory-free pass at one position of each sequence (default: its last token). Right-padded batches; a causal model's earlier positions do not see
    the padding, so the result does not depend on the batch composition."""
    out: list[Tensor] = []
    for i in range(0, len(sequences), batch):
        chunk = sequences[i : i + batch]
        width = max(len(s) for s in chunk)
        ids = torch.zeros(len(chunk), width, dtype=torch.long)
        for k, s in enumerate(chunk):
            ids[k, : len(s)] = torch.tensor(list(s), dtype=torch.long)
        h = student.block_output(ids, layer)
        pos = [(positions[i + k] if positions is not None else len(s) - 1) for k, s in enumerate(chunk)]
        out.append(torch.stack([h[k, p] for k, p in enumerate(pos)]))
    return torch.cat(out) if out else torch.zeros(0, student.cfg.width)


def none_pieces(train_ids: Sequence[int], piece: int) -> list[list[int]]:
    """Consecutive non-overlapping ``piece``-token pieces of the tokenized train file (a trailing remainder is dropped)."""
    return [list(train_ids[i : i + piece]) for i in range(0, len(train_ids) - piece + 1, piece)]


@dataclass
class RouterSpec:
    updates: int
    batch: int
    lr: float
    none_prefixes: int
    full_length: int
    prefix_tokens: int

    @staticmethod
    def registered() -> "RouterSpec":
        r = core.CFG["router"]
        return RouterSpec(r["updates"], r["batch"], r["learning_rate"], r["none_prefixes"], r["none_prefixes_full_length"], r["prefix_tokens"])

    @staticmethod
    def dry() -> "RouterSpec":
        d, r = core.CFG["dry"], core.CFG["router"]
        return RouterSpec(d["router_updates"], d["router_batch"], r["learning_rate"], d["none_prefixes"], d["none_prefixes_full_length"], d["prefix_tokens"])


def class_counts(batch: int, classes: int) -> list[int]:
    """The same number of examples of each class as nearly as the batch allows, the remainder going to the last class ("none")."""
    base = batch // classes
    return [base] * (classes - 1) + [batch - base * (classes - 1)]


def train_router(
    student: Student,
    layer: int,
    tasks: Sequence[str],
    task_prompts: Mapping[str, Sequence[Example]],
    wiki_train_ids: Sequence[int],
    plan: core.SeedPlan,
    spec: RouterSpec,
) -> tuple[Router, dict[str, Any]]:
    """Train one router from the +3 generator. ``task_prompts[t]`` are the stored prompts of the router's stream for task t (prompts only, no teacher is run; never D_cal, D_con or an evaluation
    panel). Returns the router and a record of what was drawn."""
    gen = plan.gen(3, "router")
    router = Router(tasks, student.cfg.width, gen)  # the projection, then the keys, from one generator
    pieces = none_pieces(wiki_train_ids, spec.prefix_tokens)
    if len(pieces) < spec.none_prefixes:
        raise ValueError(f"the train file has {len(pieces)} pieces of {spec.prefix_tokens} tokens, fewer than {spec.none_prefixes}")
    pick = torch.randperm(len(pieces), generator=gen).tolist()[: spec.none_prefixes]
    lengths = [len(e.prompt_ids) for t in tasks for e in task_prompts[t]]
    n_cut = spec.none_prefixes - spec.full_length
    cut_idx = torch.randint(0, len(lengths), (n_cut,), generator=gen).tolist()
    prefixes: list[list[int]] = []
    for r, k in enumerate(pick):
        piece = pieces[k]
        prefixes.append(piece if r < spec.full_length else piece[: max(1, min(lengths[cut_idx[r - spec.full_length]], spec.prefix_tokens))])
    feats_none = hidden_at_ends(student, layer, prefixes)
    feats_task = [hidden_at_ends(student, layer, [e.prompt_ids for e in task_prompts[t]]) for t in tasks]
    pools = [*feats_task, feats_none]
    counts = class_counts(spec.batch, len(pools))
    opt = torch.optim.AdamW(router.parameters(), lr=spec.lr, weight_decay=0.0)
    losses: list[float] = []
    for _ in range(spec.updates):
        xs, ys = [], []
        for c, (pool, n) in enumerate(zip(pools, counts, strict=True)):
            idx = torch.randint(0, pool.shape[0], (n,), generator=gen)
            xs.append(pool[idx])
            ys.append(torch.full((n,), c, dtype=torch.long))
        x, y = torch.cat(xs), torch.cat(ys)
        loss = F.cross_entropy(router.scores(x) / core.CFG["router"]["temperature"], y)
        opt.zero_grad()
        loss.backward()  # type: ignore[no-untyped-call]
        opt.step()
        losses.append(float(loss.item()))
    record = {"tasks": list(tasks), "prefixes": len(prefixes), "full_length_prefixes": spec.full_length, "cut_length_min": min((len(p) for p in prefixes[spec.full_length :]), default=0), "updates": spec.updates, "final_loss": losses[-1] if losses else float("nan"), "state_hash": router.state_hash(), "class_counts": counts}
    return router, record


@torch.no_grad()
def route_accuracy(router: Router, student: Student, layer: int, panels: dict[str, Sequence[Example]], general_prefixes: Sequence[Sequence[int]]) -> dict[str, float]:
    """Route accuracy on the task panels (their stored prompts, decided at the last prompt token) and on general prefixes (the first 64 tokens of general windows, decided at their last token)."""
    out: dict[str, float] = {}
    for task, exs in panels.items():
        if not exs:
            continue
        pred = router.predict(hidden_at_ends(student, layer, [e.prompt_ids for e in exs]))
        want = task if task in router.tasks else "none"
        out[task] = sum(p == want for p in pred) / len(pred)
    if general_prefixes:
        pred = router.predict(hidden_at_ends(student, layer, general_prefixes))
        out["general"] = sum(p == "none" for p in pred) / len(pred)
    return out


@torch.no_grad()
def false_triggers(router: Router, student: Student, layer: int, windows: Sequence[Sequence[int]], positions: Sequence[int]) -> dict[str, Any]:
    """The router's decision at one position of each window: the count of windows where it returns a task (a false trigger on ordinary text). Printed beside GEN per stratum; at the last
    token of the first marker-like string within tokens 1-64 it is the diagnostic of section 5.4, which enters no rule."""
    if not windows:
        return {"count": 0, "n": 0, "rate": 0.0}
    pred = router.predict(hidden_at_ends(student, layer, windows, list(positions)))
    count = sum(p != "none" for p in pred)
    return {"count": count, "n": len(windows), "rate": count / len(windows), "predictions": pred}
