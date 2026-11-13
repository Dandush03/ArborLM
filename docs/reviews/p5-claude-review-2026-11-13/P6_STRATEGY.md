# Proposed P6 strategy — P6-E and P6-Q

Status: **PROPOSAL — PENDING HUMAN REVIEW (Fable-drafted). Nothing here is approved or started.** The binding text, with thresholds, is the draft [ADR-0011](../../decisions/ADR-0011-p6-retrieval-optimization-and-routing-fidelity.md). This note explains the reasoning. **Astra review: NOT_PERFORMED.**

## The decision this serves

Before spending on larger memories or on moving learned memory to SSD, find out whether hierarchical retrieval can be made computationally practical at all, and whether its routing loses anything. Both can be answered on the existing P5 checkpoints with inference only: no training, no new data, minutes of local CPU.

## What P5 leaves open

1. **Is the tree slow because of how it is written, or because of what it is?** P5 measured 2.6× slower. The exploratory operator profile attributes most of the tree's time to work the mathematics does not require (per-query gather of raw keys, re-normalization, a per-query sort of candidate IDs) and to a batched product that is a poor fit for the CPU. But it also shows that `topk` selection is a large cost both paths share, and that flat's scoring product is already cheap at 4,096 slots. So there is a real chance that an optimized tree only reaches parity with flat at this size rather than beating it.
2. **Does the top-2 restriction change what is retrieved?** Never measured.
3. **Does the branch prior help or hurt?** Never isolated. The prior adds up to several nats to every candidate in the top branch, which could by itself explain why the trees concentrate on fewer slots than flat. That is a hypothesis.
4. **What can this "learned router" learn?** The router receives gradient only through the prior, only when a query's selected slots span both visited branches, and only on those two router rows (checked on synthetic tensors, `lead-checks/`). It gets no signal about which branches should have been visited. P5's failed R gate is therefore evidence about this weak training signal, and says little about learned routing as a concept. Fixing that would need a new estimator and new training, which is out of scope for P6.

## Two studies, kept apart

**P6-E — same outputs, faster?** A fixed list of inference-only implementations of the existing retrieval (cached normalization; ID-ordered candidates so the sort disappears; block contraction; gather-free branch-grouped scoring; an exact selection kernel), each first held to a numerical-equivalence gate against the frozen implementation on all 54 tree checkpoints and the full P5 panel, then timed under P5's own protocol. Flat gets the same kinds of optimization, so the comparison stays fair. Latency decisions come from a confirmation timing pass, not from the pass used to pick the fastest variant. P5's registered latency margins are reused unchanged as the practicality test; passing them would not alter P5's failed result.

**P6-Q — does routing lose candidates, and does it matter?** A 2×2 comparison of selection rules on the same weights: top-2 or all 16 branches, with or without the prior. It measures recall of the exhaustive selection, which candidates are lost and from which branches, how much attention weight they would have carried, selection concentration under each rule, and the change in NLL when the same weights are evaluated under each rule. The asymmetry is fixed in advance: an NLL improvement under exhaustive search is strong evidence the restriction costs quality; no improvement proves nothing about harmlessness, because the weights were trained under the restricted rule.

## Order and cost

Neither study depends on the other. Suggested order if both are approved: P6-E equivalence → P6-E timing → P6-Q, run one at a time because timing needs a quiet machine. Proposed caps: P6-E 3,000 s, P6-Q 1,800 s (2,400 s with a replication panel), 2 GiB RSS, local CPU, no downloads.

## What comes after, depending on results (each needs its own approval)

- **Tree practical and routing faithful:** propose a kernel size-scaling study on synthetic tensors (4,096 → ~1M slots) to find where, if anywhere, the tree's work reduction beats flat's kernel efficiency. Still no capacity or SSD claim.
- **Tree at parity only:** the same size-scaling question becomes the whole case for hierarchy; at 4,096 slots there is no efficiency argument.
- **No material speedup:** the implementation-overhead explanation fails; stop pursuing hierarchy on efficiency grounds.
- **Routing loses useful candidates, or the prior hurts:** propose a routing-design study (search width, prior, a router training signal that reflects branch choice). That involves training and a fresh preregistration.

## Deliberately not in P6

Training of any kind; larger memories; SSD or any storage measurement; GPU; compiled or native kernels; a new router estimator; changes to the P5 implementation; any claim about capacity scaling, I/O or reasoning.

## Alternatives considered and set aside

- **Profile and optimize ad hoc, then report the best number.** Rejected: no equivalence guarantee and winner-picking on noise.
- **One combined study.** Rejected: it invites reading a speedup as a quality result or the reverse.
- **Oracle branch selection per token (which branch would minimize loss).** Rejected for now: later positions depend on earlier retrievals through attention, so a per-token oracle is ill-defined without a much larger design.
- **Retrain with wider search to settle the fidelity question directly.** That is the decisive experiment for retrieval quality, but it is training and belongs to a later, separately approved study.
