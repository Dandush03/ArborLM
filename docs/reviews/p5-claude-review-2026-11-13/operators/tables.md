## e2e
| N | variant | end-to-end median us | p10-p90 us | stage sum us | sum/e2e | bitwise equal |
|---|---|---:|---|---:|---:|---|
| 512 | flat | 2,377.7 | 2,267.7-2,561.6 | 2,312.4 | 0.973 | True |
| 512 | fixed_tree | 6,529.3 | 6,231.2-6,802.0 | 6,190.1 | 0.948 | True |
| 512 | learned_tree | 6,469.9 | 6,256.1-6,867.5 | 6,167.5 | 0.953 | True |
| 64 | flat | 294.1 | 277.2-330.1 | 291.8 | 0.992 | True |
| 64 | fixed_tree | 669.7 | 633.1-818.8 | 626.1 | 0.935 | True |
| 64 | learned_tree | 671.6 | 638.7-735.6 | 619.4 | 0.922 | True |

## p5
| workload | variant | P5 retained lookup_score_select: median across 27 workers of median_ns (us) [worker min-max] | synthetic end-to-end median (us) | synthetic / P5 |
|---|---|---:|---:|---:|
| batch 8 x ctx 64 (512 queries) | flat | 2,323.4 [2,148.3-2,461.5] | 2,377.7 | 1.023 |
| batch 8 x ctx 64 (512 queries) | fixed_tree | 6,209.3 [5,807.0-6,675.1] | 6,529.3 | 1.052 |
| batch 8 x ctx 64 (512 queries) | learned_tree | 6,195.6 [5,628.5-6,781.8] | 6,469.9 | 1.044 |
| batch 1 x ctx 64 (64 queries) | flat | 312.7 [297.6-333.5] | 294.1 | 0.941 |
| batch 1 x ctx 64 (64 queries) | fixed_tree | 797.7 [753.0-870.9] | 669.7 | 0.840 |
| batch 1 x ctx 64 (64 queries) | learned_tree | 800.1 [740.3-862.3] | 671.6 | 0.839 |

## ratios
| N | synthetic fixed_tree/flat | retained P5 fixed_tree/flat |
|---|---:|---:|
| 512 | 2.75 | 2.67 |
| 64 | 2.28 | 2.55 |

## tree512
| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |
|---|---:|---|---:|---:|---|
| T1 normalize(router) | 2.5 | 2.3-3.0 | 0.0% | 1,024 | [16, 16] float32 |
| T2 route q@rn.T / TEMP | 4.1 | 3.9-4.5 | 0.1% | 32,768 | [512, 16] float32 |
| T3 topk(3) | 29.2 | 27.0-34.4 | 0.5% | 18,432 | [512, 3] float32; [512, 3] int64 |
| T3 tie-safety check | 4.4 | 4.1-5.4 | 0.1% | 512 | [512] bool; bool |
| T3 slice+contiguous | 1.0 | 1.0-1.2 | 0.0% | 8,192 | [512, 2] int64 |
| T3 final gather scores | 1.0 | 0.9-1.0 | 0.0% | 4,096 | [512, 2] float32 |
| T4 candidate index build | 64.1 | 62.0-76.4 | 1.0% | 2,097,152 | [512, 512] int64 |
| T5 keys[indices] gather | 1,950.4 | 1,879.3-2,250.3 | 31.5% | 16,777,216 | [512, 512, 16] float32 |
| T6 normalize(gathered) | 893.6 | 827.8-1,125.3 | 14.4% | 16,777,216 | [512, 512, 16] float32 |
| T7 bmm + squeeze + / TEMP | 1,103.5 | 1,063.8-1,312.3 | 17.8% | 2,097,152 | [512, 512, 1] float32; [512, 512] float32 |
| T8a routes.log_softmax | 6.5 | 6.0-8.8 | 0.1% | 32,768 | [512, 16] float32 |
| T8b prior gather(branch_ids) | 1.0 | 0.9-1.4 | 0.0% | 4,096 | [512, 2] float32 |
| T8c prior.repeat_interleave | 10.1 | 9.5-11.5 | 0.2% | 1,048,576 | [512, 512] float32 |
| T8d scores + prior | 24.8 | 24.0-27.3 | 0.4% | 1,048,576 | [512, 512] float32 |
| T9 ids.argsort | 388.8 | 364.4-428.2 | 6.3% | 2,097,152 | [512, 512] int64 |
| T9 gather scores by_id | 83.7 | 76.1-99.0 | 1.4% | 1,048,576 | [512, 512] float32 |
| T9 gather ids by_id | 88.8 | 80.1-110.0 | 1.4% | 2,097,152 | [512, 512] int64 |
| T9 topk(9) | 1,519.5 | 1,368.8-1,728.4 | 24.5% | 55,296 | [512, 9] float32; [512, 9] int64 |
| T9 tie-safety check | 6.0 | 5.5-8.3 | 0.1% | 512 | [512] bool; bool |
| T9 slice+contiguous | 1.4 | 1.2-2.1 | 0.0% | 32,768 | [512, 8] int64 |
| T9 final gather scores | 2.8 | 2.6-3.4 | 0.0% | 16,384 | [512, 8] float32 |
| T9 final gather ids | 2.9 | 2.8-3.7 | 0.0% | 32,768 | [512, 8] int64 |
| **stage-median sum** | **6,190.1** | | 100% | 45,328,384 | |
| **end-to-end Memory.lookup** | **6,529.3** | 6,231.2-6,802.0 | | | |
| stage sum / end-to-end | 0.948 | | | | |

## flat512
| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |
|---|---:|---|---:|---:|---|
| F1 normalize(keys) | 16.6 | 14.8-22.8 | 0.7% | 262,144 | [4096, 16] float32 |
| F2 q@nk.T / TEMP | 320.8 | 290.3-530.7 | 13.9% | 8,388,608 | [512, 4096] float32 |
| F3 topk(9) | 1,964.9 | 1,854.5-2,190.1 | 85.0% | 55,296 | [512, 9] float32; [512, 9] int64 |
| F3 tie-safety check | 6.0 | 5.4-6.8 | 0.3% | 512 | [512] bool; bool |
| F3 slice+contiguous | 1.4 | 1.2-1.5 | 0.1% | 32,768 | [512, 8] int64 |
| F3 final gather scores | 2.8 | 2.6-3.0 | 0.1% | 16,384 | [512, 8] float32 |
| **stage-median sum** | **2,312.4** | | 100% | 8,755,712 | |
| **end-to-end Memory.lookup** | **2,377.7** | 2,267.7-2,561.6 | | | |
| stage sum / end-to-end | 0.973 | | | | |

## tree512 groups
| Group | summed median us | share | bytes materialized |
|---|---:|---:|---:|
| final stable_top(scores, 8, indices) | 2,094.0 | 33.8% | 5,380,608 |
| gather keys | 1,950.4 | 31.5% | 16,777,216 |
| bmm+div | 1,103.5 | 17.8% | 2,097,152 |
| normalize gathered | 893.6 | 14.4% | 16,777,216 |
| candidate indices | 64.1 | 1.0% | 2,097,152 |
| prior | 42.4 | 0.7% | 2,134,016 |
| branch stable_top(routes, 2) | 35.6 | 0.6% | 31,232 |
| route matmul+div | 4.1 | 0.1% | 32,768 |
| router normalize | 2.5 | 0.0% | 1,024 |

## tree64
| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |
|---|---:|---|---:|---:|---|
| T1 normalize(router) | 2.4 | 2.2-2.7 | 0.4% | 1,024 | [16, 16] float32 |
| T2 route q@rn.T / TEMP | 2.5 | 2.3-2.9 | 0.4% | 4,096 | [64, 16] float32 |
| T3 topk(3) | 3.9 | 3.6-5.0 | 0.6% | 2,304 | [64, 3] float32; [64, 3] int64 |
| T3 tie-safety check | 2.6 | 2.4-3.0 | 0.4% | 64 | [64] bool; bool |
| T3 slice+contiguous | 0.8 | 0.8-0.9 | 0.1% | 1,024 | [64, 2] int64 |
| T3 final gather scores | 0.5 | 0.5-0.5 | 0.1% | 512 | [64, 2] float32 |
| T4 candidate index build | 9.8 | 9.4-11.0 | 1.6% | 262,144 | [64, 512] int64 |
| T5 keys[indices] gather | 238.1 | 226.2-255.6 | 38.0% | 2,097,152 | [64, 512, 16] float32 |
| T6 normalize(gathered) | 110.7 | 103.1-125.1 | 17.7% | 2,097,152 | [64, 512, 16] float32 |
| T7 bmm + squeeze + / TEMP | 115.1 | 111.5-121.0 | 18.4% | 262,144 | [64, 512, 1] float32; [64, 512] float32 |
| T8a routes.log_softmax | 1.1 | 1.0-1.4 | 0.2% | 4,096 | [64, 16] float32 |
| T8b prior gather(branch_ids) | 0.5 | 0.5-0.6 | 0.1% | 512 | [64, 2] float32 |
| T8c prior.repeat_interleave | 3.1 | 2.7-3.5 | 0.5% | 131,072 | [64, 512] float32 |
| T8d scores + prior | 3.3 | 3.2-3.6 | 0.5% | 131,072 | [64, 512] float32 |
| T9 ids.argsort | 47.7 | 44.9-49.5 | 7.6% | 262,144 | [64, 512] int64 |
| T9 gather scores by_id | 10.1 | 9.3-12.4 | 1.6% | 131,072 | [64, 512] float32 |
| T9 gather ids by_id | 11.0 | 9.6-12.8 | 1.8% | 262,144 | [64, 512] int64 |
| T9 topk(9) | 58.0 | 46.3-83.9 | 9.3% | 6,912 | [64, 9] float32; [64, 9] int64 |
| T9 tie-safety check | 2.9 | 2.6-3.3 | 0.5% | 64 | [64] bool; bool |
| T9 slice+contiguous | 0.9 | 0.8-1.0 | 0.1% | 4,096 | [64, 8] int64 |
| T9 final gather scores | 0.6 | 0.5-0.7 | 0.1% | 2,048 | [64, 8] float32 |
| T9 final gather ids | 0.6 | 0.5-0.7 | 0.1% | 4,096 | [64, 8] int64 |
| **stage-median sum** | **626.1** | | 100% | 5,666,944 | |
| **end-to-end Memory.lookup** | **669.7** | 633.1-818.8 | | | |
| stage sum / end-to-end | 0.935 | | | | |

## flat64
| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |
|---|---:|---|---:|---:|---|
| F1 normalize(keys) | 15.6 | 14.4-17.2 | 5.4% | 262,144 | [4096, 16] float32 |
| F2 q@nk.T / TEMP | 46.5 | 43.8-47.5 | 15.9% | 1,048,576 | [64, 4096] float32 |
| F3 topk(9) | 225.5 | 214.0-232.8 | 77.3% | 6,912 | [64, 9] float32; [64, 9] int64 |
| F3 tie-safety check | 2.8 | 2.6-3.5 | 1.0% | 64 | [64] bool; bool |
| F3 slice+contiguous | 0.8 | 0.8-1.0 | 0.3% | 4,096 | [64, 8] int64 |
| F3 final gather scores | 0.6 | 0.5-0.7 | 0.2% | 2,048 | [64, 8] float32 |
| **stage-median sum** | **291.8** | | 100% | 1,323,840 | |
| **end-to-end Memory.lookup** | **294.1** | 277.2-330.1 | | | |
| stage sum / end-to-end | 0.992 | | | | |

## learned512
| Stage | median us | p10-p90 us | share of stage-sum | bytes materialized (outputs only) | output shape / dtype |
|---|---:|---|---:|---:|---|
| T1 normalize(router) | 2.4 | 2.2-2.9 | 0.0% | 1,024 | [16, 16] float32 |
| T2 route q@rn.T / TEMP | 4.1 | 3.8-4.6 | 0.1% | 32,768 | [512, 16] float32 |
| T3 topk(3) | 30.3 | 28.5-34.7 | 0.5% | 18,432 | [512, 3] float32; [512, 3] int64 |
| T3 tie-safety check | 4.4 | 4.2-4.9 | 0.1% | 512 | [512] bool; bool |
| T3 slice+contiguous | 1.0 | 1.0-1.3 | 0.0% | 8,192 | [512, 2] int64 |
| T3 final gather scores | 1.0 | 0.9-1.0 | 0.0% | 4,096 | [512, 2] float32 |
| T4 candidate index build | 64.6 | 63.0-69.1 | 1.0% | 2,097,152 | [512, 512] int64 |
| T5 keys[indices] gather | 1,938.0 | 1,881.4-2,049.5 | 31.4% | 16,777,216 | [512, 512, 16] float32 |
| T6 normalize(gathered) | 890.5 | 822.6-999.0 | 14.4% | 16,777,216 | [512, 512, 16] float32 |
| T7 bmm + squeeze + / TEMP | 1,089.3 | 1,054.5-1,127.2 | 17.7% | 2,097,152 | [512, 512, 1] float32; [512, 512] float32 |
| T8a routes.log_softmax | 6.2 | 6.0-7.2 | 0.1% | 32,768 | [512, 16] float32 |
| T8b prior gather(branch_ids) | 0.9 | 0.9-1.0 | 0.0% | 4,096 | [512, 2] float32 |
| T8c prior.repeat_interleave | 9.8 | 9.3-10.3 | 0.2% | 1,048,576 | [512, 512] float32 |
| T8d scores + prior | 24.6 | 23.9-26.6 | 0.4% | 1,048,576 | [512, 512] float32 |
| T9 ids.argsort | 389.5 | 366.0-413.3 | 6.3% | 2,097,152 | [512, 512] int64 |
| T9 gather scores by_id | 81.6 | 79.0-92.2 | 1.3% | 1,048,576 | [512, 512] float32 |
| T9 gather ids by_id | 88.9 | 79.4-108.5 | 1.4% | 2,097,152 | [512, 512] int64 |
| T9 topk(9) | 1,527.3 | 1,400.2-1,764.5 | 24.8% | 55,296 | [512, 9] float32; [512, 9] int64 |
| T9 tie-safety check | 6.1 | 5.6-7.0 | 0.1% | 512 | [512] bool; bool |
| T9 slice+contiguous | 1.3 | 1.3-1.5 | 0.0% | 32,768 | [512, 8] int64 |
| T9 final gather scores | 2.8 | 2.6-3.3 | 0.0% | 16,384 | [512, 8] float32 |
| T9 final gather ids | 2.9 | 2.8-3.0 | 0.0% | 32,768 | [512, 8] int64 |
| **stage-median sum** | **6,167.5** | | 100% | 45,328,384 | |
| **end-to-end Memory.lookup** | **6,469.9** | 6,256.1-6,867.5 | | | |
| stage sum / end-to-end | 0.953 | | | | |