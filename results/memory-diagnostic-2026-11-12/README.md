# Frozen-memory diagnostic — mixed dependence, threshold unmet

All 12 preregistered evaluations completed without training, using the original learned-tree checkpoints and frozen validation set. Root interpretation under the human reviewer exception; Astra review NOT PERFORMED. Prior promotion failure remains unchanged.

| Seed | Original NLL | Disabled Δ NLL | Shuffled values Δ NLL | Paired within-branch Δ NLL |
|---|---:|---:|---:|---:|
| 42 | 2.568486039 | -0.000602443 | -0.000541624 | 0.000000000 |
| 43 | 2.585560936 | -0.000161164 | -0.000215378 | 0.000000000 |
| 44 | 2.582151536 | +0.006775584 | +0.007197935 | 0.000000000 |

Mean disabled delta: **+0.002003993** nats/byte. Mean value-shuffle delta: **+0.002146978**. Both are below the preregistered **+0.005** dependence threshold. Positive means the intervention harms prediction.

Original replay and joint key/value permutation within branches matched the parent losses exactly in every seed. All original checkpoint bytes remained unchanged. These controls support the integrity of the interventions.

## Interpretation

Seed 44 shows a harmful effect from disabling memory or breaking slot bindings, above 0.005 individually. Seeds 42 and 43 show small improvements under those interventions. Thus these checkpoints do not demonstrate reliable memory contribution across seeds at the registered mean sensitivity. This is a mixed/null aggregate diagnostic result, not a claim that memory never matters.

Nonzero router gradients and better loss than a separately trained small dense baseline were insufficient evidence of useful retained memory. Different training trajectories are a possible explanation for some observed baseline differences; this diagnostic does not establish that mechanism. It also does not show whether longer training, different initialization, objectives or task scale would change the outcome.

No scaling is justified by this screen. The concrete configuration failed promotion and the mean memory-dependence test. The broad hierarchical-memory concept remains unproven, not universally disproved. Do not tune thresholds after observing these results or discard the two unfavorable seeds.

## Reproduction and evidence

Protocol ADR-0006 was written after the first screen but before these diagnostic outcomes, so this is explicitly exploratory follow-up. Every condition used 32,768 validation targets with zero training targets. Test data remained untouched. No corpus or model weights are published.

Full records, raw evaluation metrics, permutations and parent identities are preserved per seed/condition. `root-analysis.json` and `per-evaluation.csv` are derived summaries. Original local suite: `experiments/P1DIAG-20261113T024308074540Z-ace5d3680604461a8f1e9bea48f466f0`. The diagnostic intentionally requires the retained original local checkpoint artifacts. Human merge/publication approval remains pending.
