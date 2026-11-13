# P1 RAM screen — completed, promotion gate failed

All 18 registered cells completed in 92.935 seconds, consuming 2,359,296 training targets total. This is a bounded exploratory screen under ADR-0005, interpreted by the human-authorized root reviewer. Astra review NOT PERFORMED. Human merge/publication approval remains pending.

| Variant | Seed 42 NLL | Seed 43 NLL | Seed 44 NLL | Mean ± sample SD | Mean train seconds |
|---|---:|---:|---:|---:|---:|
| dense_small | 2.580156 | 2.594510 | 2.589389 | 2.588018 ± 0.007275 | 0.840 |
| dense_parameter_matched | 2.560003 | 2.570665 | 2.575886 | 2.568851 ± 0.008096 | 2.626 |
| flat | 2.579296 | 2.656692 | 2.653200 | 2.629730 ± 0.043711 | 1.914 |
| product_key | 2.579872 | 2.601106 | 2.594865 | 2.591948 ± 0.010913 | 1.360 |
| fixed_tree | 2.582553 | 2.636642 | 2.593846 | 2.604347 ± 0.028533 | 7.405 |
| learned_tree | 2.568486 | 2.585561 | 2.582152 | 2.578733 ± 0.009036 | 7.459 |

NLL is nats per byte on 32,768 validation targets; lower is better. Byte perplexity is tokenizer-specific. All models saw the same 131,072 training targets per seed. Training time includes logging/checkpoint writes and is not inference latency. FLOPs were not matched. The product-key control has fewer key parameters; the larger dense control approximately matches total learned-tree/flat capacity.

## Registered decision

**Do not promote or scale this configuration under this protocol.** The required improvement over small dense was at least 0.010000 nats/byte. Observed mean improvement was **0.0092854773**, missing by **0.0007145227**. The threshold remains unchanged. This is a failed screening gate, not a statistical rejection of all hierarchical memory architectures.

Other gates passed: all cells completed with correct budgets; learned-router checkpoints improved from their initial loss, had nonzero router gradients in all 256 steps and changed router weights; mean loss was within 0.02 of the strongest flat control and parameter-matched dense; all three met the registered gross-collapse rule. Learned routing beat fixed routing in each seed. The parameter-matched dense model had lower validation NLL in each seed and lower observed training time.

Learned-tree top-1 routing used 7, 7 and 5 of 16 branches; hottest shares were 57.01%, 52.96% and 70.91%. It selected only 110, 76 and 91 distinct memory slots over the validation set out of 4,096 stored slots. Passing the gross-collapse screen does not establish healthy capacity utilization or scaling.

## Limits and next diagnostic

Three seeds and a short fixed training budget do not establish statistical significance, novelty, general reasoning or a quality/compute frontier. This is a small byte-level subset, without a final test evaluation or exhaustive contamination audit. The product-key baseline is a simplified exact lookup control, not a tuned reproduction of modern systems. Logical lookup counts are not measured physical traffic; tree code is not an optimized inference kernel.

ADR-0006 separately preregisters a post-screen, frozen-checkpoint diagnostic: replay, disable memory, permute values, and jointly permute key/value pairs within branches. It uses no training and cannot rescue the failed promotion gate. Scaling remains stopped.

## Evidence

Suite: `experiments/P1-20261113T023302942989Z-acbad32bf88f40b3b60e1993e042d5d8`. Code was frozen at `0b0555c`; later result-only commits during the run did not change forward/data/config code. Source archives, checkpoints and frozen data remain local. All six controls for all three seeds are preserved under seed directories here, including raw per-step events, configs, environment, source/data/checkpoint hashes and logs. `analysis.json` retains full precision and Boolean gate outcomes; `per-run.csv` is a derived table. Original run manifests remain immutable with their original pending-review fields; this report is the separate review record.
