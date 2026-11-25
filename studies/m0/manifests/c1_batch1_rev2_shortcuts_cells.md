# C1 shortcut battery, revision 2: per level and shape (measured)

| lineage | level | n | const key | const rate | best rules (rate) | shape |
|---|---|---|---|---|---|---|
| C1.bfs_queue | 1 | 516 | `2` | 0.490 | O.const_2 0.490; O.len_list1_minus1 0.283; A.list1_min 0.279 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.bfs_queue | 1 | 498 | `8` | 0.205 | O.n_distinct_nums 0.183; O.len_list_last 0.082; O.len_list_longest 0.082 | `Name('v5', Load())|Constant('int')@-|Subscript(N` |
| C1.bfs_queue | 1 | 496 | `5` | 0.284 | A.lit_max 0.304; O.max#1 0.304; O.max#2 0.216 | `Subscript(Name('v2', Load()), BinOp(Name('v4', L` |
| C1.bfs_queue | 1 | 490 | `[0, 1, 2, 3, 4, 5]` | 0.012 |  | `Subscript(Name('v2', Load()), Slice(Constant('in` |
| C1.bfs_queue | 2 | 525 | `2` | 0.489 | O.const_2 0.489; O.len_list1_minus1 0.267; A.list1_len 0.227 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.bfs_queue | 2 | 525 | `[1, 0, 2, 3, 6, 5, 4]` | 0.006 |  | `Subscript(Name('v2', Load()), Slice(Constant('in` |
| C1.bfs_queue | 2 | 508 | `6` | 0.230 | A.lit_max 0.250; O.max#1 0.250; O.max#3 0.199 | `Subscript(Name('v2', Load()), BinOp(Name('v4', L` |
| C1.bfs_queue | 2 | 442 | `11` | 0.158 | O.n_distinct_nums 0.093; O.len_list_last 0.059; O.len_list_longest 0.059 | `Name('v5', Load())|Constant('int')@-|Subscript(N` |
| C1.bfs_queue | 3 | 505 | `12` | 0.125 | A.list1_posum 0.032; A.list1_sum 0.032; O.sum_list1 0.032 | `Name('v5', Load())|Constant('int')@-|Subscript(N` |
| C1.bfs_queue | 3 | 505 | `[0, 1, 2, 4, 3, 7, 6, 5]` | 0.006 |  | `Subscript(Name('v2', Load()), Slice(Constant('in` |
| C1.bfs_queue | 3 | 504 | `2` | 0.446 | O.const_2 0.446; O.len_list1_minus1 0.278; A.list1_len 0.272 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.bfs_queue | 3 | 486 | `7` | 0.210 | A.lit_max 0.224; O.max#1 0.224; O.max#2 0.204 | `Subscript(Name('v2', Load()), BinOp(Name('v4', L` |
| C1.bfs_queue | 4 | 513 | `16` | 0.084 | O.n_distinct_nums 0.039; O.len_list_last 0.035; O.len_list_longest 0.035 | `Name('v5', Load())|Constant('int')@-|Subscript(N` |
| C1.bfs_queue | 4 | 513 | `8` | 0.210 | A.lit_max 0.224; O.max#1 0.224; O.max#2 0.209 | `Subscript(Name('v2', Load()), BinOp(Name('v4', L` |
| C1.bfs_queue | 4 | 491 | `2` | 0.387 | O.const_2 0.387; O.const_3 0.291; O.len_list1_minus1 0.257 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.bfs_queue | 4 | 483 | `[0, 1, 2, 4, 3, 7, 6, 8,` | 0.002 |  | `Subscript(Name('v2', Load()), Slice(Constant('in` |
| C1.bfs_queue | 5 | 520 | `9` | 0.192 | A.lit_max 0.210; O.max#1 0.210; O.max#3 0.150 | `Subscript(Name('v2', Load()), BinOp(Name('v4', L` |
| C1.bfs_queue | 5 | 512 | `[0, 1, 2, 3, 8, 5, 7, 4]` | 0.002 |  | `Subscript(Name('v2', Load()), Slice(Constant('in` |
| C1.bfs_queue | 5 | 491 | `2` | 0.401 | O.const_2 0.401; O.const_3 0.293; A.list1_len 0.251 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.bfs_queue | 5 | 477 | `18` | 0.096 | A.list1_posum 0.029; A.list1_sum 0.029; O.sum_list1 0.029 | `Name('v5', Load())|Constant('int')@-|Subscript(N` |
| C1.binary_search | 1 | 682 | `29` | 0.028 | O.num[-8] 0.060; O.num[3] 0.056; O.num[7] 0.056 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.binary_search | 1 | 652 | `2` | 0.253 | O.const_2 0.253; O.min#3 0.253; O.num[-4] 0.244 | `Name('v4', Load())|Constant('int')@-|Name('v5', ` |
| C1.binary_search | 1 | 331 | `rrr` | 0.172 |  | `Name('v4', Load())|BinOp(Name('v4', Load()), Add` |
| C1.binary_search | 2 | 678 | `38` | 0.021 | O.num[-8] 0.032; O.num[4] 0.031; A.list1_last 0.016 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.binary_search | 2 | 675 | `0` | 0.185 | A.echo_printed_initial 0.185; A.lit_min 0.185; O.const_0 0.185 | `Name('v4', Load())|Constant('int')@-|Name('v5', ` |
| C1.binary_search | 2 | 336 | `rrrr` | 0.122 |  | `Name('v4', Load())|BinOp(Name('v4', Load()), Add` |
| C1.binary_search | 3 | 658 | `0` | 0.123 | O.num[-4] 0.125; A.echo_printed_initial 0.123; A.lit_min 0.123 | `Name('v4', Load())|Constant('int')@-|Name('v5', ` |
| C1.binary_search | 3 | 651 | `64` | 0.017 | O.num[-8] 0.028; O.num[7] 0.021; O.max#3 0.012 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.binary_search | 3 | 346 | `rrrr` | 0.075 |  | `Name('v4', Load())|BinOp(Name('v4', Load()), Add` |
| C1.binary_search | 4 | 679 | `0` | 0.081 | A.echo_printed_initial 0.081; A.lit_min 0.081; O.const_0 0.081 | `Name('v4', Load())|Constant('int')@-|Name('v5', ` |
| C1.binary_search | 4 | 645 | `80` | 0.014 | O.num[-8] 0.014; A.list1_last 0.009; A.list1_max 0.009 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.binary_search | 4 | 333 | `lrrrl` | 0.066 |  | `Name('v4', Load())|BinOp(Name('v4', Load()), Add` |
| C1.binary_search | 5 | 697 | `16` | 0.070 | O.const_2 0.053; O.min#3 0.053; A.echo_printed_initial 0.050 | `Name('v4', Load())|Constant('int')@-|Name('v5', ` |
| C1.binary_search | 5 | 650 | `110` | 0.011 | O.num[-8] 0.009; O.max#3 0.005; O.max#2 0.002 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.binary_search | 5 | 336 | `rrlrr` | 0.066 |  | `Name('v4', Load())|BinOp(Name('v4', Load()), Add` |
| C1.bracket_matching | 1 | 1164 | `1` | 0.202 | R.standard_code 1.000; R.net_balance 0.477; R.standard_height 0.477 | `BinOp(BinOp(Name('v4', Load()), Mult(), Constant` |
| C1.bracket_matching | 1 | 548 | `1` | 0.325 | R.standard_height 1.000; R.net_balance 0.533; R.standard_code 0.533 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching | 1 | 288 | `0` | 0.309 | R.standard_first 1.000; A.lit_first 0.309; A.lit_last 0.309 | `Name('v5', Load())|Name('v2', Load())@Compare(Na` |
| C1.bracket_matching | 2 | 1106 | `12` | 0.191 | R.standard_code 1.000; R.net_balance 0.392; R.standard_height 0.392 | `BinOp(BinOp(Name('v4', Load()), Mult(), Constant` |
| C1.bracket_matching | 2 | 523 | `2` | 0.222 | R.standard_height 1.000; R.net_balance 0.419; R.standard_code 0.419 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching | 2 | 371 | `0` | 0.232 | R.standard_first 1.000; A.lit_first 0.232; A.lit_last 0.232 | `Name('v5', Load())|Name('v2', Load())@Compare(Na` |
| C1.bracket_matching | 3 | 1078 | `13` | 0.162 | R.standard_code 1.000; R.net_balance 0.249; R.standard_height 0.249 | `BinOp(BinOp(Name('v4', Load()), Mult(), Constant` |
| C1.bracket_matching | 3 | 546 | `2` | 0.205 | R.standard_height 1.000; R.net_balance 0.287; R.standard_code 0.287 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching | 3 | 376 | `0` | 0.200 | R.standard_first 1.000; A.lit_first 0.200; A.lit_last 0.200 | `Name('v5', Load())|Name('v2', Load())@Compare(Na` |
| C1.bracket_matching | 4 | 1081 | `12` | 0.130 | R.standard_code 1.000; R.net_balance 0.203; R.standard_height 0.203 | `BinOp(BinOp(Name('v4', Load()), Mult(), Constant` |
| C1.bracket_matching | 4 | 491 | `3` | 0.212 | R.standard_height 1.000; R.net_balance 0.257; R.standard_code 0.257 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching | 4 | 428 | `0` | 0.196 | R.standard_first 1.000; A.lit_first 0.196; A.lit_last 0.196 | `Name('v5', Load())|Name('v2', Load())@Compare(Na` |
| C1.bracket_matching | 5 | 1052 | `13` | 0.102 | R.standard_code 1.000; R.net_balance 0.138; R.standard_height 0.138 | `BinOp(BinOp(Name('v4', Load()), Mult(), Constant` |
| C1.bracket_matching | 5 | 493 | `4` | 0.164 | R.standard_height 1.000; A.lit_max 0.148; O.const_2 0.148 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching | 5 | 455 | `0` | 0.158 | R.standard_first 1.000; A.lit_first 0.158; A.lit_last 0.158 | `Name('v5', Load())|Name('v2', Load())@Compare(Na` |
| C1.bracket_matching_traced | 1 | 1022 | `10` | 0.111 | A.str1_len 0.080; O.len_str1 0.080; R.opens 0.075 | `Name('v4', Load())|Constant('int')@-|Name('v2', ` |
| C1.bracket_matching_traced | 1 | 978 | `1` | 0.292 | A.lit_last 0.292; A.lit_mode 0.292; O.const_1 0.292 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching_traced | 2 | 1014 | `1` | 0.301 | A.lit_last 0.301; A.lit_mode 0.301; O.const_1 0.301 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching_traced | 2 | 986 | `11` | 0.081 | O.sum_nums 0.080; A.str1_len 0.063; O.count_nums 0.063 | `Name('v4', Load())|Constant('int')@-|Name('v2', ` |
| C1.bracket_matching_traced | 3 | 1027 | `1` | 0.263 | A.lit_last 0.263; A.lit_mode 0.263; O.const_1 0.263 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching_traced | 3 | 973 | `28` | 0.050 | O.count_nums 0.027; A.str1_len 0.022; O.len_str1 0.022 | `Name('v4', Load())|Constant('int')@-|Name('v2', ` |
| C1.bracket_matching_traced | 4 | 1036 | `1` | 0.221 | A.lit_last 0.221; A.lit_mode 0.221; O.const_1 0.221 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching_traced | 4 | 964 | `40` | 0.039 | R.standard_code 0.018; A.str1_len 0.007; O.count_nums 0.007 | `Name('v4', Load())|Constant('int')@-|Name('v2', ` |
| C1.bracket_matching_traced | 5 | 1000 | `2` | 0.193 | O.const_2 0.193; O.max#2 0.193; O.min#3 0.193 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.bracket_matching_traced | 5 | 1000 | `49` | 0.029 | R.standard_code 0.004; A.str1_len 0.003; O.len_str1 0.003 | `Name('v4', Load())|Constant('int')@-|Name('v2', ` |
| C1.bytecode_loop | 1 | 1013 | `24` | 0.041 | R.sum_all_args 0.867; O.count_nums 0.040; A.list1_len 0.003 | `Name('v3', Load())|Constant('int')@-|Name('v5', ` |
| C1.bytecode_loop | 1 | 987 | `12` | 0.042 | A.echo_printed_initial 0.037; A.lit_min 0.037; O.const_0 0.037 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop | 2 | 1003 | `24` | 0.047 | R.sum_all_args 0.870; O.count_nums 0.024 | `Name('v3', Load())|Constant('int')@-|Name('v5', ` |
| C1.bytecode_loop | 2 | 997 | `0` | 0.136 | A.echo_printed_initial 0.136; A.lit_min 0.136; O.const_0 0.136 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop | 3 | 838 | `0` | 0.107 | A.echo_printed_initial 0.107; A.lit_min 0.107; O.const_0 0.107 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop | 3 | 809 | `35` | 0.042 | R.sum_all_args 0.870; O.count_nums 0.024; O.len_list1_minus1 0.003 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.bytecode_loop | 3 | 353 | `1` | 0.091 | O.num[1] 0.297; A.list1_mode 0.105; O.const_1 0.091 | `Name('v3', Load())|Constant('int')@-|Name('v2', ` |
| C1.bytecode_loop | 4 | 790 | `0` | 0.113 | A.echo_printed_initial 0.113; A.lit_min 0.113; O.const_0 0.113 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop | 4 | 782 | `44` | 0.037 | R.sum_all_args 0.841; O.count_nums 0.014; A.list1_len 0.001 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.bytecode_loop | 4 | 428 | `2` | 0.101 | O.num[1] 0.199; A.lit_mode 0.101; O.const_2 0.101 | `Name('v3', Load())|Constant('int')@-|Name('v2', ` |
| C1.bytecode_loop | 5 | 819 | `58` | 0.034 | R.sum_all_args 0.822; O.count_nums 0.004 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.bytecode_loop | 5 | 725 | `0` | 0.120 | A.echo_printed_initial 0.120; A.lit_min 0.120; O.const_0 0.120 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop | 5 | 456 | `4` | 0.072 | O.num[1] 0.200; A.list1_mode 0.086; A.lit_last 0.077 | `Name('v3', Load())|Constant('int')@-|Name('v2', ` |
| C1.bytecode_loop_r2 | 1 | 1017 | `12` | 0.044 | O.num[7] 0.040; O.num[8] 0.040; O.num[1] 0.039 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop_r2 | 1 | 983 | `23` | 0.062 | R.sum_all_args 0.157; O.count_nums 0.055; A.list1_len 0.018 | `Name('v3', Load())|Constant('int')@-|Name('v5', ` |
| C1.bytecode_loop_r2 | 2 | 1001 | `30` | 0.066 | R.sum_all_args 0.160; O.count_nums 0.053; A.list1_len 0.008 | `Name('v3', Load())|Constant('int')@-|Name('v5', ` |
| C1.bytecode_loop_r2 | 2 | 999 | `0` | 0.121 | A.echo_printed_initial 0.121; A.lit_min 0.121; O.const_0 0.121 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop_r2 | 3 | 802 | `37` | 0.056 | R.sum_all_args 0.155; O.count_nums 0.044; A.list1_len 0.006 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.bytecode_loop_r2 | 3 | 776 | `0` | 0.095 | A.echo_printed_initial 0.095; A.lit_min 0.095; O.const_0 0.095 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop_r2 | 3 | 422 | `0` | 0.211 | O.num[1] 0.291; A.echo_printed_initial 0.211; A.lit_min 0.211 | `Name('v3', Load())|Constant('int')@-|Name('v2', ` |
| C1.bytecode_loop_r2 | 4 | 778 | `0` | 0.129 | A.echo_printed_initial 0.129; A.lit_min 0.129; O.const_0 0.129 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop_r2 | 4 | 771 | `42` | 0.058 | R.sum_all_args 0.143; O.count_nums 0.045; O.len_list1_minus1 0.001 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.bytecode_loop_r2 | 4 | 451 | `0` | 0.189 | O.num[1] 0.224; A.echo_printed_initial 0.189; A.lit_min 0.189 | `Name('v3', Load())|Constant('int')@-|Name('v2', ` |
| C1.bytecode_loop_r2 | 5 | 745 | `51` | 0.052 | R.sum_all_args 0.126; O.count_nums 0.025 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.bytecode_loop_r2 | 5 | 724 | `0` | 0.120 | A.echo_printed_initial 0.120; A.lit_min 0.120; O.const_0 0.120 | `Name('v2', Load())|BinOp(Name('v2', Load()), Add` |
| C1.bytecode_loop_r2 | 5 | 531 | `0` | 0.143 | O.num[1] 0.171; A.echo_printed_initial 0.143; A.lit_min 0.143 | `Name('v3', Load())|Constant('int')@-|Name('v2', ` |
| C1.cellular_update | 1 | 1011 | `[0, 0, 0, 0, 0, 0]` | 0.093 | A.echo_printed_initial 0.097; O.echo 0.097; O.list1 0.097 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update | 1 | 844 | `5` | 0.107 | O.len_list1_minus1 0.107; O.max#2 0.107; O.num[-8] 0.107 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.cellular_update | 2 | 984 | `[0, 0, 0, 0, 0, 0, 0]` | 0.075 | A.echo_printed_initial 0.040; O.echo 0.040; O.list1 0.040 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update | 2 | 848 | `21` | 0.087 | A.echo_printed_initial 0.079; A.list1_min 0.079; A.lit_min 0.079 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.cellular_update | 3 | 1041 | `[0, 0, 0, 0, 0, 0, 0, 0]` | 0.067 | A.echo_printed_initial 0.026; O.echo 0.026; O.list1 0.026 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update | 3 | 826 | `28` | 0.091 | A.echo_printed_initial 0.080; A.list1_min 0.080; A.lit_min 0.080 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.cellular_update | 4 | 1047 | `[1, 1, 1, 1, 1, 1, 1, 1,` | 0.070 | A.echo_printed_initial 0.047; O.echo 0.047; O.list1 0.047 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update | 4 | 809 | `0` | 0.072 | A.echo_printed_initial 0.072; A.list1_min 0.072; A.lit_min 0.072 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.cellular_update | 5 | 1013 | `[1, 1, 1, 1, 1, 1, 1, 1,` | 0.059 | A.echo_printed_initial 0.045; O.echo 0.045; O.list1 0.045 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update | 5 | 840 | `0` | 0.063 | A.echo_printed_initial 0.063; A.list1_min 0.063; A.lit_min 0.063 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.cellular_update_r2 | 1 | 1036 | `15` | 0.107 | A.list1_len 0.089; A.lit_last 0.089; A.lit_max 0.089 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.cellular_update_r2 | 1 | 964 | `[0, 0, 0, 0, 0, 0]` | 0.080 | A.echo_printed_initial 0.093; O.echo 0.093; O.list1 0.093 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update_r2 | 2 | 1009 | `[0, 0, 0, 0, 0, 0, 0]` | 0.077 | A.echo_printed_initial 0.034; O.echo 0.034; O.list1 0.034 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update_r2 | 2 | 991 | `0` | 0.102 | A.echo_printed_initial 0.102; A.list1_min 0.102; A.lit_min 0.102 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.cellular_update_r2 | 3 | 1010 | `28` | 0.083 | A.echo_printed_initial 0.068; A.list1_min 0.068; A.lit_min 0.068 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.cellular_update_r2 | 3 | 990 | `[0, 0, 0, 0, 0, 0, 0, 0]` | 0.080 | A.echo_printed_initial 0.038; O.echo 0.038; O.list1 0.038 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update_r2 | 4 | 1011 | `[1, 1, 1, 1, 1, 1, 1, 1,` | 0.050 | A.echo_printed_initial 0.050; O.echo 0.050; O.list1 0.050 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update_r2 | 4 | 989 | `36` | 0.068 | A.echo_printed_initial 0.056; A.list1_min 0.056; A.lit_min 0.056 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.cellular_update_r2 | 5 | 1001 | `[0, 0, 0, 0, 0, 0, 0, 0,` | 0.058 | A.echo_printed_initial 0.040; O.echo 0.040; O.list1 0.040 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.cellular_update_r2 | 5 | 999 | `0` | 0.068 | A.echo_printed_initial 0.068; A.list1_min 0.068; A.lit_min 0.068 | `Name('v5', Load())|BinOp(Name('v4', Load()), Mul` |
| C1.circle_elimination | 1 | 687 | `0` | 0.233 | R.first_live_index 0.274; O.max#3 0.242; A.list1_min 0.233 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination | 1 | 671 | `5` | 0.134 | R.last_live_index 0.136; O.num[1] 0.113; A.echo_printed_initial 0.112 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.circle_elimination | 1 | 642 | `10` | 0.044 | A.list1_len 0.044; A.lit_max 0.044; O.len_list1 0.044 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination | 2 | 698 | `15` | 0.042 | A.list1_len 0.020; A.lit_max 0.020; O.len_list1 0.020 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination | 2 | 659 | `0` | 0.140 | R.first_live_index 0.172; A.list1_min 0.140; A.lit_min 0.140 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination | 2 | 643 | `7` | 0.112 | R.last_live_index 0.126; O.num[1] 0.123; O.num[4] 0.121 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.circle_elimination | 3 | 693 | `11` | 0.107 | R.last_live_index 0.118; A.echo_printed_initial 0.107; O.echo 0.107 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.circle_elimination | 3 | 659 | `12` | 0.033 | A.list1_len 0.033; A.lit_max 0.033; O.len_list1 0.033 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination | 3 | 648 | `0` | 0.148 | R.first_live_index 0.173; A.lit_min 0.148; O.const_0 0.148 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination | 4 | 683 | `2` | 0.102 | O.num[1] 0.110; R.last_live_index 0.110; O.const_2 0.102 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.circle_elimination | 4 | 660 | `38` | 0.030 | R.last_live_index 0.024; O.len_list1_minus1 0.023; O.max#2 0.023 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination | 4 | 657 | `0` | 0.158 | R.first_live_index 0.190; A.list1_min 0.158; A.lit_min 0.158 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination | 5 | 684 | `7` | 0.092 | R.last_live_index 0.105; A.echo_printed_initial 0.086; O.echo 0.086 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.circle_elimination | 5 | 668 | `21` | 0.024 | O.sum_nums 0.018; R.last_live_index 0.018; O.len_list1_minus1 0.015 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination | 5 | 648 | `10` | 0.148 | A.list1_min 0.173; O.min_list1 0.173; R.first_live_index 0.154 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination_r2 | 1 | 680 | `5` | 0.122 | R.last_live_index 0.128; O.max#3 0.113; O.const_2 0.109 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.circle_elimination_r2 | 1 | 668 | `13` | 0.051 | O.count_nums 0.037; A.list1_len 0.034; A.lit_max 0.034 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination_r2 | 1 | 652 | `8` | 0.121 | R.last_live_index 0.138; R.first_live_index 0.126; O.n_distinct_nums 0.117 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination_r2 | 2 | 694 | `10` | 0.111 | R.last_live_index 0.125; O.len_list1_minus1 0.111; R.first_live_index 0.105 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination_r2 | 2 | 672 | `4` | 0.104 | R.first_live_index 0.120; A.echo_printed_initial 0.113; O.echo 0.113 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.circle_elimination_r2 | 2 | 634 | `22` | 0.047 | O.count_nums 0.032; O.sum_nums 0.022; A.list1_len 0.021 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination_r2 | 3 | 681 | `32` | 0.034 | O.sum_nums 0.031; O.count_nums 0.025; A.list1_posum 0.018 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination_r2 | 3 | 673 | `4` | 0.101 | O.num[-8] 0.107; O.num[2] 0.104; O.num[1] 0.102 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination_r2 | 3 | 646 | `10` | 0.101 | A.echo_printed_initial 0.136; O.echo 0.136; O.last_set_int 0.136 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.circle_elimination_r2 | 4 | 680 | `4` | 0.097 | R.first_live_index 0.099; O.num[1] 0.084; O.n_distinct_nums 0.082 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination_r2 | 4 | 677 | `3` | 0.093 | A.echo_printed_initial 0.098; O.echo 0.098; O.last_set_int 0.098 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.circle_elimination_r2 | 4 | 643 | `25` | 0.034 | O.count_nums 0.022; O.sum_nums 0.022; O.len_list1_minus1 0.019 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination_r2 | 5 | 686 | `24` | 0.025 | O.count_nums 0.025; O.sum_nums 0.018; A.list1_len 0.013 | `Name('v2', Load())|Constant('int')@-|Name('v1', ` |
| C1.circle_elimination_r2 | 5 | 669 | `7` | 0.094 | R.last_live_index 0.094; O.loop_bound 0.090; O.num[-10] 0.090 | `Name('v5', Load())|Name('v4', Load())@Compare(Su` |
| C1.circle_elimination_r2 | 5 | 645 | `4` | 0.087 | O.n_distinct_nums 0.090; O.max#3 0.085; O.num[-6] 0.085 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.coin_change_table | 1 | 1466 | `1` | 0.216 | R.greedy_fewest 0.280; R.T_div_maxcoin 0.229; O.const_1 0.216 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.coin_change_table | 1 | 534 | `5` | 0.101 | O.const_3 0.075; O.n_distinct_nums 0.073; O.count_nums 0.069 | `Call(Name('sum', Load()), [Name('v1', Load())], ` |
| C1.coin_change_table | 2 | 1486 | `2` | 0.190 | R.greedy_fewest 0.210; O.const_2 0.190; O.len_list1_minus1 0.186 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.coin_change_table | 2 | 514 | `4` | 0.060 | O.count_nums 0.062; O.n_distinct_nums 0.062; O.const_3 0.045 | `Call(Name('sum', Load()), [Name('v1', Load())], ` |
| C1.coin_change_table | 3 | 1478 | `3` | 0.171 | R.greedy_fewest 0.244; O.len_list1_minus1 0.184; O.const_3 0.171 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.coin_change_table | 3 | 522 | `7` | 0.046 | O.count_nums 0.048; O.n_distinct_nums 0.048; A.list1_last 0.027 | `Call(Name('sum', Load()), [Name('v1', Load())], ` |
| C1.coin_change_table | 4 | 1465 | `3` | 0.179 | R.greedy_fewest 0.210; O.len_list1_minus1 0.193; O.const_3 0.179 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.coin_change_table | 4 | 535 | `10` | 0.045 | A.list1_last 0.039; A.list1_max 0.039; O.count_nums 0.039 | `Call(Name('sum', Load()), [Name('v1', Load())], ` |
| C1.coin_change_table | 5 | 1476 | `3` | 0.173 | R.greedy_fewest 0.200; O.const_3 0.173; O.len_list1_minus1 0.171 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.coin_change_table | 5 | 524 | `6` | 0.042 | O.count_nums 0.042; O.n_distinct_nums 0.042; A.list1_last 0.023 | `Call(Name('sum', Load()), [Name('v1', Load())], ` |
| C1.digit_peel | 1 | 521 | `1001` | 0.011 | O.const_1 0.002 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.digit_peel | 1 | 507 | `11` | 0.081 | R.decimal_digit_sum_of_literal 0.562; A.lit_last 0.047; O.max#2 0.047 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 1 | 498 | `0` | 0.219 | A.echo_printed_initial 0.219; A.lit_min 0.219; A.lit_mode 0.219 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 1 | 474 | `1` | 0.260 | O.const_1 0.260; O.min#2 0.260; O.num[-2] 0.260 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.digit_peel | 2 | 524 | `0` | 0.170 | A.echo_printed_initial 0.170; A.lit_min 0.170; A.lit_mode 0.170 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 2 | 508 | `2` | 0.254 | O.const_2 0.254; O.const_3 0.183; O.const_1 0.177 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.digit_peel | 2 | 501 | `111111` | 0.010 | O.const_1 0.006 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.digit_peel | 2 | 467 | `18` | 0.066 | R.decimal_digit_sum_of_literal 0.576; A.lit_last 0.038; O.max#2 0.038 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 3 | 519 | `23` | 0.052 | R.decimal_digit_sum_of_literal 0.561; O.count_nums 0.029; R.decimal_digit_count 0.015 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 3 | 511 | `2` | 0.219 | O.const_2 0.219; O.const_3 0.202; O.const_1 0.157 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.digit_peel | 3 | 500 | `100001` | 0.006 |  | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.digit_peel | 3 | 470 | `8` | 0.157 | O.max#3 0.136; A.echo_printed_initial 0.119; A.lit_min 0.119 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 4 | 503 | `26` | 0.052 | R.decimal_digit_sum_of_literal 0.610; O.count_nums 0.020; R.decimal_digit_count 0.016 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 4 | 499 | `10000101` | 0.004 |  | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.digit_peel | 4 | 499 | `3` | 0.186 | O.const_3 0.186; O.const_2 0.178; O.const_1 0.132 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.digit_peel | 4 | 499 | `8` | 0.124 | O.max#3 0.100; A.echo_printed_initial 0.096; A.lit_min 0.096 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 5 | 560 | `8` | 0.125 | A.lit_last 0.091; O.max#2 0.091; O.min#3 0.091 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 5 | 495 | `32` | 0.051 | R.decimal_digit_sum_of_literal 0.576; O.count_nums 0.014; R.decimal_digit_count 0.008 | `Name('v1', Load())|Constant('int')@-|Name('v2', ` |
| C1.digit_peel | 5 | 489 | `1000000011` | 0.004 |  | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.digit_peel | 5 | 456 | `3` | 0.178 | O.const_3 0.178; O.n_distinct_nums 0.138; O.const_2 0.114 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.euclid_gcd | 1 | 689 | `7` | 0.224 | R.sum_quot_naive_max_div_min 0.078; O.count_nums 0.068; R.gcd_of_literals 0.052 | `Name('v2', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.euclid_gcd | 1 | 678 | `24` | 0.059 | R.gcd_of_literals 0.292; O.num[-3] 0.183; O.num[1] 0.183 | `Name('v2', Load())|Constant('int')@-|Name('v3', ` |
| C1.euclid_gcd | 1 | 633 | `4` | 0.144 | R.gcd_of_literals 1.000; O.const_1 0.126; O.const_3 0.120 | `Name('v0', Load())|Constant('int')@-|Name('v1', ` |
| C1.euclid_gcd | 2 | 698 | `12` | 0.050 | O.num[-3] 0.231; O.num[1] 0.231; O.max#2 0.117 | `Name('v2', Load())|Constant('int')@-|Name('v3', ` |
| C1.euclid_gcd | 2 | 693 | `8` | 0.219 | R.gcd_of_literals 0.069; O.count_nums 0.053; O.const_3 0.022 | `Name('v2', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.euclid_gcd | 2 | 609 | `8` | 0.135 | R.gcd_of_literals 1.000; O.const_2 0.113; O.const_3 0.102 | `Name('v0', Load())|Constant('int')@-|Name('v1', ` |
| C1.euclid_gcd | 3 | 673 | `8` | 0.120 | R.gcd_of_literals 1.000; O.const_3 0.097; O.count_nums 0.097 | `Name('v0', Load())|Constant('int')@-|Name('v1', ` |
| C1.euclid_gcd | 3 | 667 | `8` | 0.213 | R.gcd_of_literals 0.054; O.count_nums 0.033; O.const_3 0.019 | `Name('v2', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.euclid_gcd | 3 | 660 | `24` | 0.053 | O.num[-3] 0.208; O.num[1] 0.208; A.lit_max 0.118 | `Name('v2', Load())|Constant('int')@-|Name('v3', ` |
| C1.euclid_gcd | 4 | 695 | `10` | 0.121 | R.gcd_of_literals 1.000; O.const_2 0.102; O.const_3 0.092 | `Name('v0', Load())|Constant('int')@-|Name('v1', ` |
| C1.euclid_gcd | 4 | 666 | `72` | 0.030 |  | `Name('v2', Load())|Constant('int')@-|Name('v3', ` |
| C1.euclid_gcd | 4 | 639 | `9` | 0.232 | R.gcd_of_literals 0.072; O.count_nums 0.008; O.max#2 0.003 | `Name('v2', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.euclid_gcd | 5 | 673 | `120` | 0.019 | R.sum_quot_naive_max_div_min 0.002 | `Name('v2', Load())|Constant('int')@-|Name('v3', ` |
| C1.euclid_gcd | 5 | 670 | `10` | 0.170 | R.gcd_of_literals 0.057; O.count_nums 0.007; A.lit_first 0.006 | `Name('v2', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.euclid_gcd | 5 | 657 | `2` | 0.099 | R.gcd_of_literals 1.000; O.const_2 0.099; O.const_1 0.093 | `Name('v0', Load())|Constant('int')@-|Name('v1', ` |
| C1.euclid_gcd_traced | 1 | 1014 | `12 6` | 0.025 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v0'` |
| C1.euclid_gcd_traced | 1 | 986 | `5` | 0.160 | O.n_distinct_nums 0.160; O.count_nums 0.143; R.gcd_of_literals 0.094 | `Name('v3', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.euclid_gcd_traced | 2 | 1013 | `6` | 0.199 | O.count_nums 0.176; O.n_distinct_nums 0.163; R.gcd_of_literals 0.100 | `Name('v3', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.euclid_gcd_traced | 2 | 987 | `12 6` | 0.022 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v0'` |
| C1.euclid_gcd_traced | 3 | 1014 | `12 6` | 0.017 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v0'` |
| C1.euclid_gcd_traced | 3 | 986 | `7` | 0.172 | O.count_nums 0.172; O.n_distinct_nums 0.163; R.gcd_of_literals 0.105 | `Name('v3', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.euclid_gcd_traced | 4 | 1022 | `20 10` | 0.019 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v0'` |
| C1.euclid_gcd_traced | 4 | 978 | `7` | 0.195 | O.count_nums 0.195; O.n_distinct_nums 0.126; R.gcd_of_literals 0.094 | `Name('v3', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.euclid_gcd_traced | 5 | 1007 | `4 2` | 0.012 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v0'` |
| C1.euclid_gcd_traced | 5 | 993 | `8` | 0.171 | O.count_nums 0.156; O.n_distinct_nums 0.111; R.gcd_of_literals 0.091 | `Name('v3', Load())|BinOp(Name('v0', Load()), Flo` |
| C1.fast_power | 1 | 683 | `1` | 0.239 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.348; A.lit_first 0.239 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power | 1 | 669 | `18` | 0.054 | O.num[-8] 0.036; O.num[1] 0.036; R.base_mod 0.027 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power | 1 | 648 | `1` | 0.116 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.279; R.base_mod 0.241 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power | 2 | 686 | `1` | 0.137 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.338; R.base_mod 0.243 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power | 2 | 684 | `1` | 0.206 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.317; A.lit_mode 0.212 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power | 2 | 630 | `54` | 0.035 | O.num[-8] 0.041; O.num[1] 0.041; A.lit_max 0.027 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power | 3 | 679 | `24` | 0.021 | O.num[-8] 0.047; O.num[1] 0.047; R.base_mod 0.035 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power | 3 | 668 | `1` | 0.196 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.328; A.lit_first 0.196 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power | 3 | 653 | `1` | 0.129 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.342; R.base_mod 0.228 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power | 4 | 711 | `1` | 0.184 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.288; A.lit_first 0.184 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power | 4 | 670 | `1` | 0.085 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.279; R.base_mod 0.206 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power | 4 | 619 | `60` | 0.026 | O.num[-8] 0.031; O.num[1] 0.031; R.base_mod 0.026 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power | 5 | 701 | `1` | 0.168 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.292; A.lit_first 0.168 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power | 5 | 687 | `12` | 0.013 | O.num[-8] 0.050; O.num[1] 0.050; O.max#3 0.038 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power | 5 | 612 | `1` | 0.108 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.273; R.base_mod 0.167 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_r2 | 1 | 690 | `1` | 0.200 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.313; A.lit_first 0.200 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power_r2 | 1 | 664 | `15` | 0.044 | O.num[-8] 0.041; O.num[1] 0.041; A.lit_max 0.029 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_r2 | 1 | 646 | `1` | 0.133 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.285; R.base_mod 0.271 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_r2 | 2 | 693 | `1` | 0.134 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.330; R.base_mod 0.214 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_r2 | 2 | 654 | `1` | 0.203 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.312; A.lit_first 0.203 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power_r2 | 2 | 653 | `54` | 0.038 | O.num[-8] 0.038; O.num[1] 0.038; R.base_mod 0.028 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_r2 | 3 | 671 | `30` | 0.024 | O.num[-8] 0.046; O.num[1] 0.046; R.base_mod 0.031 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_r2 | 3 | 666 | `1` | 0.113 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.363; R.base_mod 0.221 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_r2 | 3 | 663 | `1` | 0.201 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.315; A.lit_first 0.201 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power_r2 | 4 | 704 | `1` | 0.112 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.305; R.base_mod 0.196 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_r2 | 4 | 657 | `1` | 0.207 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.286; A.lit_mode 0.208 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power_r2 | 4 | 639 | `18` | 0.034 | O.num[-8] 0.041; O.num[1] 0.041; R.base_mod 0.031 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_r2 | 5 | 692 | `1` | 0.173 | R.base^(2^bits) 1.000; R.pow(base,exp,mod) 0.289; A.lit_first 0.173 | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.fast_power_r2 | 5 | 690 | `70` | 0.015 | O.num[-8] 0.046; O.num[1] 0.046; O.max#3 0.029 | `Name('v4', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_r2 | 5 | 618 | `1` | 0.102 | R.pow(base,exp,mod) 1.000; R.base^(2^bits) 0.278; R.base_mod 0.189 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_traced | 1 | 1036 | `162` | 0.012 | R.pow(base,exp,mod) 0.134; R.base^(2^bits) 0.031; A.lit_max 0.011 | `Name('v5', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_traced | 1 | 964 | `1` | 0.290 | R.base_mod 0.313; O.num[-10] 0.297; O.num[1] 0.297 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_traced | 2 | 1011 | `1` | 0.228 | R.base_mod 0.253; O.num[-10] 0.246; O.num[1] 0.246 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_traced | 2 | 989 | `0` | 0.008 | R.pow(base,exp,mod) 0.069; R.base^(2^bits) 0.017; O.num[-10] 0.015 | `Name('v5', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_traced | 3 | 1014 | `1` | 0.192 | R.base_mod 0.226; O.num[-10] 0.220; O.num[1] 0.220 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_traced | 3 | 986 | `0` | 0.007 | R.pow(base,exp,mod) 0.036; R.base^(2^bits) 0.010; A.echo_printed_initial 0.007 | `Name('v5', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_traced | 4 | 1004 | `3` | 0.006 | R.pow(base,exp,mod) 0.028; O.const_3 0.006; O.num[-10] 0.006 | `Name('v5', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_traced | 4 | 996 | `1` | 0.193 | R.base_mod 0.205; O.num[-10] 0.201; O.num[1] 0.201 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fast_power_traced | 5 | 1015 | `5` | 0.005 | R.pow(base,exp,mod) 0.016; O.num[-10] 0.008; O.num[1] 0.008 | `Name('v5', Load())|Constant('int')@-|Name('v1', ` |
| C1.fast_power_traced | 5 | 985 | `1` | 0.153 | R.base_mod 0.157; O.num[-10] 0.154; O.num[1] 0.154 | `Name('v0', Load())|BinOp(BinOp(Name('v0', Load()` |
| C1.fib_shapes_recursive | 1 | 2000 | `38` | 0.011 | O.max#2 0.013; O.sum_nums 0.011; O.const_0 0.009 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.fib_shapes_recursive | 2 | 2000 | `16` | 0.009 | O.sum_nums 0.008; O.num[-2] 0.006; O.num[5] 0.006 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.fib_shapes_recursive | 3 | 2000 | `101` | 0.008 | O.count_nums 0.006; A.lit_last 0.003; A.lit_max 0.003 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.fib_shapes_recursive | 4 | 2000 | `99` | 0.009 | A.lit_last 0.003; A.lit_max 0.003; O.count_nums 0.003 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.fib_shapes_recursive | 5 | 2000 | `182` | 0.009 |  | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.grid_path_table | 1 | 2000 | `3` | 0.087 | R.greedy_max_path 0.323; R.greedy_min_path 0.315; A.list1_posum 0.107 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.grid_path_table | 2 | 2000 | `3` | 0.057 | R.greedy_min_path 0.285; R.greedy_max_path 0.280; A.list1_posum 0.076 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.grid_path_table | 3 | 2000 | `3` | 0.040 | R.greedy_max_path 0.273; R.greedy_min_path 0.255; A.list1_posum 0.054 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.grid_path_table | 4 | 2000 | `50` | 0.030 | R.greedy_min_path 0.237; R.greedy_max_path 0.232; A.list1_posum 0.043 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.grid_path_table | 5 | 2000 | `57` | 0.031 | R.greedy_min_path 0.218; R.greedy_max_path 0.207; A.list1_posum 0.032 | `Subscript(Name('v1', Load()), Constant('int'), L` |
| C1.insertion_sort | 1 | 689 | `5` | 0.078 | R.sorted_prefix_at 1.000; A.list1_mode 0.309; O.num[1] 0.276 | `Subscript(Name('v0', Load()), Constant('int'), L` |
| C1.insertion_sort | 1 | 659 | `[12, 8, 7, 4, 2]` | 0.003 | R.sorted_prefix_list 1.000; A.echo_printed_initial 0.220; O.echo 0.220 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.insertion_sort | 1 | 652 | `1` | 0.261 | R.inversions_prefix 1.000; A.lit_last 0.261; A.lit_mode 0.261 | `Name('v1', Load())|Constant('int')@-` |
| C1.insertion_sort | 2 | 699 | `1` | 0.183 | R.inversions_prefix 1.000; A.lit_last 0.183; A.lit_mode 0.183 | `Name('v1', Load())|Constant('int')@-` |
| C1.insertion_sort | 2 | 691 | `14` | 0.083 | R.sorted_prefix_at 1.000; A.list1_mode 0.282; O.num[-10] 0.232 | `Subscript(Name('v0', Load()), Constant('int'), L` |
| C1.insertion_sort | 2 | 610 | `[1, 1, 12, 14, 18, 16]` | 0.002 | R.sorted_prefix_list 1.000; A.echo_printed_initial 0.182; O.echo 0.182 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.insertion_sort | 3 | 698 | `[1, 1, 1, 12, 13, 13, 18` | 0.001 | R.sorted_prefix_list 1.000; A.echo_printed_initial 0.135; O.echo 0.135 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.insertion_sort | 3 | 651 | `1` | 0.126 | R.inversions_prefix 1.000; O.loop_bound 0.138; O.num[-7] 0.138 | `Name('v1', Load())|Constant('int')@-` |
| C1.insertion_sort | 3 | 651 | `2` | 0.065 | R.sorted_prefix_at 1.000; A.list1_mode 0.243; O.max#2 0.201 | `Subscript(Name('v0', Load()), Constant('int'), L` |
| C1.insertion_sort | 4 | 690 | `2` | 0.055 | R.sorted_prefix_at 1.000; A.list1_mode 0.243; A.list1_last 0.178 | `Subscript(Name('v0', Load()), Constant('int'), L` |
| C1.insertion_sort | 4 | 658 | `[1, 1, 14, 14, 15, 15, 1` | 0.002 | R.sorted_prefix_list 1.000; A.list1_sorted 0.129; O.list1_sorted 0.129 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.insertion_sort | 4 | 652 | `1` | 0.107 | R.inversions_prefix 1.000; A.lit_last 0.107; A.lit_mode 0.107 | `Name('v1', Load())|Constant('int')@-` |
| C1.insertion_sort | 5 | 671 | `[1, 1, 2, 15, 21, 22, 22` | 0.002 | R.sorted_prefix_list 1.000; A.list1_sorted 0.121; O.list1_sorted 0.121 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.insertion_sort | 5 | 671 | `1` | 0.127 | R.inversions_prefix 1.000; A.lit_last 0.127; A.lit_mode 0.127 | `Name('v1', Load())|Constant('int')@-` |
| C1.insertion_sort | 5 | 658 | `24` | 0.050 | R.sorted_prefix_at 1.000; A.list1_mode 0.199; O.num[3] 0.153 | `Subscript(Name('v0', Load()), Constant('int'), L` |
| C1.insertion_sort_traced | 1 | 1005 | `0` | 0.272 | A.lit_min 0.272; O.const_0 0.272; O.min#1 0.272 | `Name('v3', Load())|BinOp(Name('v1', Load()), Sub` |
| C1.insertion_sort_traced | 1 | 995 | `0` | 0.252 | A.echo_printed_initial 0.252; A.lit_min 0.252; O.const_0 0.252 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.insertion_sort_traced | 2 | 1037 | `0` | 0.225 | A.echo_printed_initial 0.225; A.lit_min 0.225; O.const_0 0.225 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.insertion_sort_traced | 2 | 963 | `-1` | 0.254 | A.lit_min 0.233; O.const_0 0.233; O.min#1 0.233 | `Name('v3', Load())|BinOp(Name('v1', Load()), Sub` |
| C1.insertion_sort_traced | 3 | 1039 | `-1` | 0.225 | A.lit_min 0.220; O.const_0 0.220; O.min#1 0.220 | `Name('v3', Load())|BinOp(Name('v1', Load()), Sub` |
| C1.insertion_sort_traced | 3 | 961 | `-1` | 0.164 | A.echo_printed_initial 0.161; A.lit_min 0.161; O.const_0 0.161 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.insertion_sort_traced | 4 | 1034 | `0` | 0.156 | A.echo_printed_initial 0.156; A.lit_min 0.156; O.const_0 0.156 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.insertion_sort_traced | 4 | 966 | `1` | 0.211 | A.lit_last 0.211; A.lit_mode 0.211; O.const_1 0.211 | `Name('v3', Load())|BinOp(Name('v1', Load()), Sub` |
| C1.insertion_sort_traced | 5 | 1005 | `0` | 0.148 | A.echo_printed_initial 0.148; A.lit_min 0.148; O.const_0 0.148 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.insertion_sort_traced | 5 | 995 | `0` | 0.203 | O.ones_list1 0.215; A.lit_min 0.203; O.const_0 0.203 | `Name('v3', Load())|BinOp(Name('v1', Load()), Sub` |
| C1.kadane_scan | 1 | 1008 | `9` | 0.016 | O.n_distinct_nums 0.015; A.list1_posum 0.014; O.num[2] 0.013 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.kadane_scan | 1 | 544 | `10` | 0.072 | R.max_subarray 1.000; O.count_nums 0.055; O.n_distinct_nums 0.053 | `Name('v2', Load())|Call(Name('max', Load()), [Na` |
| C1.kadane_scan | 1 | 448 | `5` | 0.062 | A.list1_sum 0.458; O.sum_list1 0.458; O.max#3 0.060 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.kadane_scan | 2 | 877 | `57` | 0.014 | O.sum_nums 0.010; A.list1_first 0.008; A.lit_first 0.008 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.kadane_scan | 2 | 651 | `13` | 0.069 | R.max_subarray 1.000; O.count_nums 0.060; O.n_distinct_nums 0.040 | `Name('v2', Load())|Call(Name('max', Load()), [Na` |
| C1.kadane_scan | 2 | 472 | `11` | 0.059 | A.list1_sum 0.400; O.sum_list1 0.400; A.list1_max 0.057 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.kadane_scan | 3 | 828 | `133` | 0.011 | A.list1_posum 0.006; O.len_list1_minus1 0.006; O.num[-7] 0.006 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.kadane_scan | 3 | 675 | `18` | 0.055 | R.max_subarray 1.000; O.count_nums 0.040; O.len_list1_minus1 0.037 | `Name('v2', Load())|Call(Name('max', Load()), [Na` |
| C1.kadane_scan | 3 | 497 | `10` | 0.050 | A.list1_sum 0.364; O.sum_list1 0.364; O.len_list1_minus1 0.050 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.kadane_scan | 4 | 833 | `94` | 0.010 | O.count_nums 0.006; A.list1_first 0.004; A.list1_max 0.004 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.kadane_scan | 4 | 712 | `21` | 0.051 | R.max_subarray 1.000; O.count_nums 0.052; A.list1_len 0.035 | `Name('v2', Load())|Call(Name('max', Load()), [Na` |
| C1.kadane_scan | 4 | 455 | `9` | 0.046 | A.list1_sum 0.332; O.sum_list1 0.332; O.max#3 0.044 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.kadane_scan | 5 | 823 | `116` | 0.012 | O.num[2] 0.009; O.const_2 0.004; A.list1_max 0.002 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.kadane_scan | 5 | 709 | `21` | 0.046 | R.max_subarray 1.000; A.list1_len 0.032; A.lit_last 0.032 | `Name('v2', Load())|Call(Name('max', Load()), [Na` |
| C1.kadane_scan | 5 | 468 | `10` | 0.038 | A.list1_sum 0.333; O.sum_list1 0.333; A.list1_len 0.036 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.kadane_scan_traced | 1 | 1036 | `9` | 0.060 | R.max_subarray 0.108; A.list1_max 0.088; O.max_list1 0.088 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.kadane_scan_traced | 1 | 964 | `0` | 0.337 | A.echo_printed_initial 0.337; A.lit_last 0.337; O.const_0 0.337 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.kadane_scan_traced | 2 | 1045 | `13` | 0.046 | R.max_subarray 0.073; A.list1_max 0.063; O.max_list1 0.063 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.kadane_scan_traced | 2 | 955 | `0` | 0.327 | A.echo_printed_initial 0.327; A.lit_last 0.327; O.const_0 0.327 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.kadane_scan_traced | 3 | 1041 | `0` | 0.328 | A.echo_printed_initial 0.328; A.lit_last 0.328; O.const_0 0.328 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.kadane_scan_traced | 3 | 959 | `9` | 0.049 | R.max_subarray 0.066; A.list1_max 0.061; O.max_list1 0.061 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.kadane_scan_traced | 4 | 1021 | `6` | 0.049 | R.max_subarray 0.054; O.num[4] 0.042; A.list1_max 0.037 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.kadane_scan_traced | 4 | 979 | `0` | 0.292 | A.echo_printed_initial 0.292; A.lit_last 0.292; O.const_0 0.292 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.kadane_scan_traced | 5 | 1038 | `0` | 0.291 | A.echo_printed_initial 0.291; A.lit_last 0.291; O.const_0 0.291 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.kadane_scan_traced | 5 | 962 | `8` | 0.044 | R.max_subarray 0.059; A.list1_max 0.043; O.max_list1 0.043 | `Name('v1', Load())|Call(Name('max', Load()), [Bi` |
| C1.majority_vote_scan | 1 | 1093 | `2 0` | 0.167 | R.mode_space_0 0.312 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan | 1 | 518 | `4` | 0.481 | O.max#3 0.328; O.const_3 0.307; A.list1_max 0.237 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.majority_vote_scan | 1 | 389 | `2` | 0.221 | O.num[-9] 0.802; O.num[6] 0.802; O.num[-10] 0.347 | `Name('v1', Load())|Constant('int')@-|Subscript(N` |
| C1.majority_vote_scan | 2 | 1108 | `2 0` | 0.160 | R.mode_space_0 0.274 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan | 2 | 532 | `5` | 0.338 | O.max#3 0.308; A.list1_max 0.267; O.max#2 0.267 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.majority_vote_scan | 2 | 360 | `2` | 0.225 | O.num[-9] 0.833; O.num[8] 0.833; O.num[-10] 0.322 | `Name('v1', Load())|Constant('int')@-|Subscript(N` |
| C1.majority_vote_scan | 3 | 1084 | `3 0` | 0.167 | R.mode_space_0 0.282 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan | 3 | 547 | `5` | 0.327 | A.list1_max 0.316; O.max#2 0.316; O.max_list1 0.316 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.majority_vote_scan | 3 | 369 | `3` | 0.252 | O.num[-9] 0.840; O.num[-10] 0.325; O.num[9] 0.325 | `Name('v1', Load())|Constant('int')@-|Subscript(N` |
| C1.majority_vote_scan | 4 | 1070 | `1 0` | 0.162 | R.mode_space_0 0.256 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan | 4 | 551 | `6` | 0.299 | O.n_distinct_nums 0.229; A.list1_max 0.200; O.max#2 0.200 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.majority_vote_scan | 4 | 379 | `2` | 0.232 | O.num[-9] 0.850; O.num[-10] 0.346; O.num[8] 0.259 | `Name('v1', Load())|Constant('int')@-|Subscript(N` |
| C1.majority_vote_scan | 5 | 1099 | `1 0` | 0.169 | R.mode_space_0 0.253 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan | 5 | 541 | `7` | 0.242 | O.n_distinct_nums 0.238; A.list1_max 0.141; O.max#2 0.141 | `Name('v3', Load())|Constant('int')@-|Constant('i` |
| C1.majority_vote_scan | 5 | 360 | `2` | 0.239 | O.num[-9] 0.797; O.num[-10] 0.344; O.min#3 0.242 | `Name('v1', Load())|Constant('int')@-|Subscript(N` |
| C1.majority_vote_scan_r2 | 1 | 1005 | `2 0` | 0.176 | R.mode_space_0 0.293 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan_r2 | 1 | 995 | `7` | 0.096 | O.n_distinct_nums 0.097; O.len_list1_minus1 0.096; A.list1_len 0.093 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.majority_vote_scan_r2 | 2 | 1010 | `3 0` | 0.155 | R.mode_space_0 0.261 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan_r2 | 2 | 990 | `9` | 0.086 | O.len_list1_minus1 0.086; A.list1_len 0.076; A.lit_max 0.076 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.majority_vote_scan_r2 | 3 | 1037 | `2 0` | 0.154 | R.mode_space_0 0.279 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan_r2 | 3 | 963 | `10` | 0.075 | A.list1_len 0.063; A.lit_max 0.063; O.len_list1 0.063 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.majority_vote_scan_r2 | 4 | 1006 | `15` | 0.071 | A.list1_len 0.070; A.lit_max 0.070; O.len_list1 0.070 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.majority_vote_scan_r2 | 4 | 994 | `2 0` | 0.158 | R.mode_space_0 0.285 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan_r2 | 5 | 1004 | `3 0` | 0.169 | R.mode_space_0 0.275 | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.majority_vote_scan_r2 | 5 | 996 | `14` | 0.062 | A.list1_len 0.055; A.lit_max 0.055; O.len_list1 0.055 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.merge_two_sorted | 1 | 690 | `[1, 1, 1, 2]` | 0.004 | R.sorted_all_but_last 0.568; A.list1_sorted 0.016; O.list1 0.016 | `Name('v4', Load())|List([], Load())@-` |
| C1.merge_two_sorted | 1 | 623 | `3` | 0.279 | A.list1_len 0.307; O.len_list1 0.307; O.const_3 0.279 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted | 1 | 343 | `6` | 0.248 | R.len_a+len_b-1 0.560; O.max#2 0.280; O.n_distinct_nums 0.271 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted | 2 | 677 | `5` | 0.288 | A.list1_len 0.250; O.len_list1 0.250; O.len_list_last 0.232 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted | 2 | 646 | `[1, 1, 2, 3, 3, 5, 6, 7,` | 0.003 | R.sorted_all_but_last 0.522; A.list1_sorted 0.006; O.list1 0.006 | `Name('v4', Load())|List([], Load())@-` |
| C1.merge_two_sorted | 2 | 349 | `9` | 0.278 | R.len_a+len_b-1 0.513; O.n_distinct_nums 0.249; O.max#2 0.215 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted | 3 | 688 | `[1, 1, 1, 1, 2, 2, 5, 9,` | 0.002 | R.sorted_all_but_last 0.513; A.list1_sorted 0.002; O.list1 0.002 | `Name('v4', Load())|List([], Load())@-` |
| C1.merge_two_sorted | 3 | 661 | `5` | 0.250 | A.list1_len 0.240; O.len_list1 0.240; O.len_list_last 0.222 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted | 3 | 343 | `10` | 0.192 | R.len_a+len_b-1 0.516; O.n_distinct_nums 0.239; O.max#2 0.233 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted | 4 | 664 | `[1, 1, 1, 1, 1, 2, 4, 5,` | 0.002 | R.sorted_all_but_last 0.538; A.list1_sorted 0.003; O.list1 0.003 | `Name('v4', Load())|List([], Load())@-` |
| C1.merge_two_sorted | 4 | 651 | `7` | 0.215 | A.list1_len 0.243; O.len_list1 0.243; O.len_list_last 0.226 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted | 4 | 322 | `11` | 0.208 | R.len_a+len_b-1 0.503; O.max#3 0.217; O.max#2 0.205 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted | 5 | 670 | `[1, 1, 1, 2, 2, 2, 3, 7,` | 0.002 | R.sorted_all_but_last 0.513 | `Name('v4', Load())|List([], Load())@-` |
| C1.merge_two_sorted | 5 | 637 | `7` | 0.220 | A.list1_len 0.196; O.len_list1 0.196; O.len_list1_minus1 0.182 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted | 5 | 365 | `12` | 0.178 | R.len_a+len_b-1 0.474; O.max#3 0.197; O.n_distinct_nums 0.159 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted_r2 | 1 | 2000 | `3` | 0.296 | O.const_3 0.296; O.len_list_last 0.291; A.list1_len 0.285 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted_r2 | 2 | 2000 | `5` | 0.292 | A.list1_len 0.260; O.len_list1 0.260; O.len_list_last 0.235 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted_r2 | 3 | 2000 | `5` | 0.270 | A.list1_len 0.228; O.len_list1 0.228; O.len_list_last 0.222 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted_r2 | 4 | 2000 | `7` | 0.223 | A.list1_len 0.214; O.len_list1 0.214; O.len_list_last 0.198 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.merge_two_sorted_r2 | 5 | 2000 | `7` | 0.218 | A.list1_len 0.200; O.len_list1 0.200; O.len_list_last 0.198 | `Name('v5', Load())|Constant('int')@-|Constant('i` |
| C1.mirror_pointers | 1 | 689 | `mt` | 0.007 |  | `Name('v3', Load())|BinOp(BinOp(Name('v3', Load()` |
| C1.mirror_pointers | 1 | 677 | `a` | 0.040 | A.str1_first 0.383; A.str1_last 0.148 | `Name('v3', Load())|BinOp(Name('v3', Load()), Add` |
| C1.mirror_pointers | 1 | 634 | `2` | 0.338 | R.unequal_pairs 0.352; O.const_2 0.338; O.n_distinct_nums 0.338 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.mirror_pointers | 2 | 707 | `c` | 0.041 | A.str1_first 0.280; A.str1_last 0.134 | `Name('v3', Load())|BinOp(Name('v3', Load()), Add` |
| C1.mirror_pointers | 2 | 651 | `3` | 0.281 | O.const_3 0.281; O.sum_nums 0.281; R.unequal_pairs 0.249 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.mirror_pointers | 2 | 642 | `ab` | 0.006 |  | `Name('v3', Load())|BinOp(BinOp(Name('v3', Load()` |
| C1.mirror_pointers | 3 | 683 | `3` | 0.170 | O.const_3 0.170; O.sum_nums 0.170; R.unequal_pairs 0.139 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.mirror_pointers | 3 | 668 | `n` | 0.033 | A.str1_first 0.208; A.str1_last 0.129 | `Name('v3', Load())|BinOp(Name('v3', Load()), Add` |
| C1.mirror_pointers | 3 | 649 | `vz` | 0.008 |  | `Name('v3', Load())|BinOp(BinOp(Name('v3', Load()` |
| C1.mirror_pointers | 4 | 689 | `5` | 0.161 | O.count_nums 0.161; O.const_3 0.122; O.sum_nums 0.122 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.mirror_pointers | 4 | 678 | `u` | 0.032 | A.str1_first 0.156; A.str1_last 0.111 | `Name('v3', Load())|BinOp(Name('v3', Load()), Add` |
| C1.mirror_pointers | 4 | 633 | `cu` | 0.006 |  | `Name('v3', Load())|BinOp(BinOp(Name('v3', Load()` |
| C1.mirror_pointers | 5 | 683 | `c` | 0.026 | A.str1_first 0.143; A.str1_last 0.084 | `Name('v3', Load())|BinOp(Name('v3', Load()), Add` |
| C1.mirror_pointers | 5 | 662 | `6` | 0.136 | O.count_nums 0.091; O.const_3 0.083; O.sum_nums 0.083 | `Name('v3', Load())|Constant('int')@-|Name('v1', ` |
| C1.mirror_pointers | 5 | 655 | `sz` | 0.008 |  | `Name('v3', Load())|BinOp(BinOp(Name('v3', Load()` |
| C1.partition_pass | 1 | 1191 | `[1, 1, 10, 14, 2, 17]` | 0.001 | R.stable_partition 0.381; A.list1_sorted 0.066; O.list1_sorted 0.066 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.partition_pass | 1 | 387 | `0` | 0.253 | A.echo_printed_initial 0.253; O.const_0 0.253; O.echo 0.253 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.partition_pass | 2 | 1265 | `[1, 1, 1, 6, 7, 14, 21]` | 0.001 | R.stable_partition 0.329; A.list1_sorted 0.015; O.list1_sorted 0.015 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.partition_pass | 2 | 371 | `0` | 0.170 | A.echo_printed_initial 0.170; O.const_0 0.170; O.echo 0.170 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.partition_pass | 3 | 1253 | `[1, 1, 14, 3, 14, 21, 22` | 0.001 | R.stable_partition 0.276; A.list1_sorted 0.004; O.list1_sorted 0.004 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.partition_pass | 3 | 377 | `0` | 0.162 | A.echo_printed_initial 0.162; O.const_0 0.162; O.echo 0.162 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.partition_pass | 4 | 1257 | `[1, 1, 1, 11, 12, 2, 19,` | 0.001 | R.stable_partition 0.263; A.list1_sorted 0.001; O.list1_sorted 0.001 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.partition_pass | 4 | 395 | `0` | 0.147 | A.echo_printed_initial 0.147; O.const_0 0.147; O.echo 0.147 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.partition_pass | 5 | 1276 | `[1, 1, 10, 9, 21, 15, 5,` | 0.001 | R.stable_partition 0.227; A.list1_sorted 0.001; O.list1_sorted 0.001 | `Name('v0', Load())|List([Constant('int'), Consta` |
| C1.partition_pass | 5 | 334 | `0` | 0.171 | A.echo_printed_initial 0.171; O.const_0 0.171; O.echo 0.171 | `Name('v3', Load())|Constant('int')@-|Name('v4', ` |
| C1.postfix_evaluation | 1 | 1017 | `0` | 0.021 | A.list1_posum 0.038; O.const_0 0.021; O.last_set_int 0.021 | `Subscript(Name('v1', Load()), BinOp(Name('v3', L` |
| C1.postfix_evaluation | 1 | 983 | `8` | 0.016 | A.list1_posum 0.017; A.list1_sum 0.016; O.sum_list1 0.016 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.postfix_evaluation | 2 | 1017 | `18` | 0.010 | O.num[4] 0.011; O.len_list1_minus1 0.009; O.max#3 0.009 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.postfix_evaluation | 2 | 983 | `0` | 0.034 | O.const_0 0.034; O.last_set_int 0.034; O.zeros_list1 0.034 | `Subscript(Name('v1', Load()), BinOp(Name('v3', L` |
| C1.postfix_evaluation | 3 | 1022 | `0` | 0.020 | O.const_0 0.020; O.last_set_int 0.020; O.zeros_list1 0.020 | `Subscript(Name('v1', Load()), BinOp(Name('v3', L` |
| C1.postfix_evaluation | 3 | 978 | `32` | 0.007 | O.count_nums 0.007; O.num[9] 0.007; A.list1_sum 0.006 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.postfix_evaluation | 4 | 1031 | `0` | 0.024 | O.const_0 0.024; O.last_set_int 0.024; O.zeros_list1 0.024 | `Subscript(Name('v1', Load()), BinOp(Name('v3', L` |
| C1.postfix_evaluation | 4 | 969 | `19` | 0.005 | O.count_nums 0.004; O.n_distinct_nums 0.004; A.list1_first 0.003 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.postfix_evaluation | 5 | 1003 | `132` | 0.004 | O.len_list1_minus1 0.004; A.echo_printed_initial 0.003; A.list1_first 0.003 | `Name('v4', Load())|Constant('int')@-|Subscript(N` |
| C1.postfix_evaluation | 5 | 997 | `0` | 0.020 | O.const_0 0.020; O.last_set_int 0.020; O.zeros_list1 0.020 | `Subscript(Name('v1', Load()), BinOp(Name('v3', L` |
| C1.recursive_calls | 1 | 1583 | `26` | 0.022 | O.min#3 0.023; O.sum_nums 0.013; A.lit_first 0.013 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls | 1 | 417 | `65` | 0.048 | O.sum_nums 0.014; O.const_1 0.012; O.len_list1_minus1 0.012 | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.recursive_calls | 2 | 1597 | `47` | 0.017 | O.max#2 0.019; O.count_nums 0.014; O.sum_nums 0.012 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls | 2 | 403 | `105` | 0.027 | A.list1_min 0.007; A.lit_mode 0.007; O.const_1 0.007 | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.recursive_calls | 3 | 1588 | `47` | 0.022 | O.n_distinct_nums 0.008 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls | 3 | 412 | `105` | 0.017 | O.sum_nums 0.002 | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.recursive_calls | 4 | 1567 | `116` | 0.022 | A.lit_last 0.015; A.lit_max 0.015; O.count_nums 0.015 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls | 4 | 433 | `393` | 0.014 | A.list1_min 0.002; A.list1_mode 0.002; A.lit_mode 0.002 | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.recursive_calls | 5 | 1637 | `212` | 0.015 |  | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls | 5 | 363 | `1185` | 0.008 |  | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.recursive_calls_r2 | 1 | 1338 | `124` | 0.007 | O.count_nums 0.001; O.sum_nums 0.001 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls_r2 | 1 | 662 | `69` | 0.008 | A.lit_first 0.014; O.num[0] 0.014; O.num[-8] 0.012 | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.recursive_calls_r2 | 2 | 1343 | `170` | 0.004 | O.count_nums 0.001; O.sum_nums 0.001 | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls_r2 | 2 | 657 | `68` | 0.006 | A.lit_first 0.005; O.num[-10] 0.005; O.num[-5] 0.005 | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.recursive_calls_r2 | 3 | 1313 | `126` | 0.003 |  | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls_r2 | 3 | 687 | `2081` | 0.004 | A.lit_first 0.004; O.num[0] 0.004; O.num[6] 0.004 | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.recursive_calls_r2 | 4 | 1339 | `85` | 0.003 |  | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls_r2 | 4 | 661 | `1109` | 0.003 | A.lit_first 0.003; O.const_3 0.003; O.num[0] 0.003 | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.recursive_calls_r2 | 5 | 1293 | `151` | 0.002 |  | `Call(Name('v0', Load()), [Constant('int')], [])` |
| C1.recursive_calls_r2 | 5 | 707 | `894784854` | 0.003 | A.lit_first 0.004; O.num[0] 0.004; O.num[6] 0.003 | `Call(Name('v0', Load()), [List([Constant('int'),` |
| C1.run_length_scan | 1 | 680 | `1212` | 0.022 |  | `Name('v1', Load())|BinOp(Name('v1', Load()), Add` |
| C1.run_length_scan | 1 | 633 | `c3` | 0.005 |  | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.run_length_scan | 2 | 671 | `33341` | 0.007 |  | `Name('v1', Load())|BinOp(Name('v1', Load()), Add` |
| C1.run_length_scan | 2 | 657 | `a2g2v4` | 0.002 |  | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.run_length_scan | 3 | 662 | `133144` | 0.004 |  | `Name('v1', Load())|BinOp(Name('v1', Load()), Add` |
| C1.run_length_scan | 3 | 650 | `a2a2t4z3a2` | 0.002 |  | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.run_length_scan | 4 | 685 | `1111134` | 0.002 |  | `Name('v1', Load())|BinOp(Name('v1', Load()), Add` |
| C1.run_length_scan | 4 | 670 | `a2c2c5c3a5` | 0.002 |  | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.run_length_scan | 5 | 666 | `25442212` | 0.003 |  | `Name('v1', Load())|BinOp(Name('v1', Load()), Add` |
| C1.run_length_scan | 5 | 650 | `a2a2x3a4` | 0.002 |  | `Name('v1', Load())|BinOp(BinOp(Name('v1', Load()` |
| C1.shared_lists | 1 | 310 | `16` | 0.061 | A.list1_posum 0.026; A.list1_sum 0.026; O.sum_list1 0.026 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.shared_lists | 1 | 229 | `25` | 0.083 | A.lit_max 0.018; O.max#1 0.018; A.list1_posum 0.013 | `Call(Name('sum', Load()), [Name('v4', Load())], ` |
| C1.shared_lists | 1 | 163 | `27` | 0.061 | O.count_nums 0.025; A.list1_posum 0.012; A.list1_sum 0.012 | `Call(Name('sum', Load()), [Name('v6', Load())], ` |
| C1.shared_lists | 2 | 292 | `17` | 0.062 | A.list1_posum 0.031; A.list1_sum 0.031; O.sum_list1 0.031 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.shared_lists | 2 | 201 | `17` | 0.065 | A.lit_max 0.020; O.max#1 0.020; A.list1_posum 0.015 | `Call(Name('sum', Load()), [Name('v4', Load())], ` |
| C1.shared_lists | 2 | 194 | `28` | 0.083 | O.count_nums 0.031; A.list1_posum 0.021; A.list1_sum 0.021 | `Call(Name('sum', Load()), [Name('v6', Load())], ` |
| C1.shared_lists | 2 | 100 | `9` | 0.140 | O.last_set_int 0.160; O.num[-2] 0.130; O.num[8] 0.120 | `Subscript(Name('v5', Load()), Constant('int'), L` |
| C1.shared_lists | 3 | 284 | `28` | 0.060 | O.count_nums 0.021; A.list1_posum 0.018; A.list1_sum 0.018 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.shared_lists | 3 | 196 | `22` | 0.071 | O.count_nums 0.020; A.list1_posum 0.010; A.list1_sum 0.010 | `Call(Name('sum', Load()), [Name('v4', Load())], ` |
| C1.shared_lists | 3 | 171 | `21` | 0.070 | O.count_nums 0.029; A.list1_last 0.012; A.lit_last 0.012 | `Call(Name('sum', Load()), [Name('v6', Load())], ` |
| C1.shared_lists | 4 | 306 | `25` | 0.062 | O.count_nums 0.020; A.list1_posum 0.013; A.list1_sum 0.013 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.shared_lists | 4 | 228 | `27` | 0.057 | A.list1_posum 0.022; A.list1_sum 0.022; O.count_nums 0.022 | `Call(Name('sum', Load()), [Name('v6', Load())], ` |
| C1.shared_lists | 4 | 152 | `24` | 0.086 | A.list1_posum 0.013; A.list1_sum 0.013; O.count_nums 0.013 | `Call(Name('sum', Load()), [Name('v4', Load())], ` |
| C1.shared_lists | 5 | 307 | `30` | 0.052 | A.list1_posum 0.013; A.list1_sum 0.013; O.sum_list1 0.013 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.shared_lists | 5 | 206 | `27` | 0.078 | O.count_nums 0.010; A.list1_posum 0.005; A.list1_sum 0.005 | `Call(Name('sum', Load()), [Name('v6', Load())], ` |
| C1.shared_lists | 5 | 138 | `27` | 0.072 | A.list1_posum 0.015; A.list1_sum 0.015; O.sum_list1 0.015 | `Call(Name('sum', Load()), [Name('v4', Load())], ` |
| C1.shared_lists | 5 | 103 | `8` | 0.117 | O.last_set_int 0.175; O.num[-2] 0.165; O.max#2 0.136 | `Subscript(Name('v5', Load()), Constant('int'), L` |
| C1.sieve_marking | 1 | 685 | `7` | 0.336 | R.mine_allones_dbl_count 0.336; R.mine_allones_sq_count 0.336; R.ones_minus_strikes_naive 0.210 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.sieve_marking | 1 | 670 | `6` | 0.300 | R.ones_minus_strikes_naive 0.498; R.mine_allones_dbl_count 0.273; R.mine_allones_sq_count 0.273 | `Call(Name('sum', Load()), [Name('v0', Load())], ` |
| C1.sieve_marking | 1 | 645 | `29` | 0.155 | R.mine_allones_dbl_indexsum 0.155; R.mine_allones_sq_indexsum 0.155; R.mine_allones_tri_indexsum 0.042 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking | 2 | 671 | `7` | 0.267 | R.ones_minus_strikes_naive 0.477; R.mine_allones_dbl_count 0.237; R.mine_allones_sq_count 0.237 | `Call(Name('sum', Load()), [Name('v0', Load())], ` |
| C1.sieve_marking | 2 | 667 | `10` | 0.291 | A.list1_posum 0.076; A.list1_sum 0.076; O.ones_list1 0.076 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.sieve_marking | 2 | 662 | `42` | 0.103 | R.mine_allones_dbl_indexsum 0.103; R.mine_allones_sq_indexsum 0.103; R.mine_allones_tri_indexsum 0.026 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking | 3 | 677 | `9` | 0.264 | R.ones_minus_strikes_naive 0.451; R.prime_count_below_n 0.259; R.mine_allones_dbl_count 0.152 | `Call(Name('sum', Load()), [Name('v0', Load())], ` |
| C1.sieve_marking | 3 | 663 | `14` | 0.237 | A.list1_posum 0.085; A.list1_sum 0.085; O.ones_list1 0.085 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.sieve_marking | 3 | 660 | `78` | 0.070 | R.mine_allones_dbl_indexsum 0.070; R.mine_allones_sq_indexsum 0.070; R.mine_allones_tri_indexsum 0.026 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking | 4 | 673 | `9` | 0.250 | R.ones_minus_strikes_naive 0.373; R.prime_count_below_n 0.250; R.mine_allones_dbl_count 0.140 | `Call(Name('sum', Load()), [Name('v0', Load())], ` |
| C1.sieve_marking | 4 | 665 | `101` | 0.044 | R.mine_allones_dbl_indexsum 0.044; R.mine_allones_sq_indexsum 0.044; O.sum_nums 0.015 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking | 4 | 662 | `19` | 0.198 | A.list1_posum 0.072; A.list1_sum 0.072; O.ones_list1 0.072 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.sieve_marking | 5 | 681 | `142` | 0.021 | R.mine_allones_dbl_indexsum 0.019; R.mine_allones_sq_indexsum 0.019; R.mine_allones_tri_indexsum 0.010 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking | 5 | 677 | `24` | 0.163 | A.list1_len 0.129; A.lit_max 0.129; O.len_list1 0.129 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.sieve_marking | 5 | 642 | `11` | 0.248 | R.ones_minus_strikes_naive 0.350; R.prime_count_below_n 0.248; R.mine_allones_dbl_count 0.120 | `Call(Name('sum', Load()), [Name('v0', Load())], ` |
| C1.sieve_marking_r2 | 1 | 1050 | `61` | 0.185 | R.mine_allones_tri_indexsum 0.046; A.echo_printed_initial 0.027; A.list1_min 0.027 | `Name('v1', Load())|Constant('int')@-|Name('v3', ` |
| C1.sieve_marking_r2 | 1 | 950 | `29` | 0.131 | R.mine_allones_dbl_indexsum 0.131; R.mine_allones_sq_indexsum 0.131; R.mine_allones_tri_indexsum 0.065 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking_r2 | 2 | 1008 | `42` | 0.099 | R.mine_allones_dbl_indexsum 0.099; R.mine_allones_sq_indexsum 0.099; R.mine_allones_tri_indexsum 0.041 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking_r2 | 2 | 992 | `106` | 0.175 | O.len_list1_minus1 0.014; A.echo_printed_initial 0.012; A.list1_min 0.012 | `Name('v1', Load())|Constant('int')@-|Name('v3', ` |
| C1.sieve_marking_r2 | 3 | 1002 | `78` | 0.061 | R.mine_allones_dbl_indexsum 0.061; R.mine_allones_sq_indexsum 0.061; R.mine_allones_tri_indexsum 0.019 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking_r2 | 3 | 998 | `183` | 0.172 | A.echo_printed_initial 0.011; A.list1_min 0.011; A.lit_last 0.011 | `Name('v1', Load())|Constant('int')@-|Name('v3', ` |
| C1.sieve_marking_r2 | 4 | 1001 | `101` | 0.045 | R.mine_allones_dbl_indexsum 0.045; R.mine_allones_sq_indexsum 0.045; R.mine_allones_tri_indexsum 0.020 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking_r2 | 4 | 999 | `304` | 0.130 | A.echo_printed_initial 0.001; A.list1_min 0.001; A.lit_last 0.001 | `Name('v1', Load())|Constant('int')@-|Name('v3', ` |
| C1.sieve_marking_r2 | 5 | 1004 | `161` | 0.047 | R.mine_allones_dbl_indexsum 0.047; R.mine_allones_sq_indexsum 0.047; O.sum_nums 0.014 | `Name('v1', Load())|Constant('int')@-|Name('v4', ` |
| C1.sieve_marking_r2 | 5 | 996 | `449` | 0.137 | A.echo_printed_initial 0.002; A.list1_min 0.002; A.lit_last 0.002 | `Name('v1', Load())|Constant('int')@-|Name('v3', ` |
| C1.string_pair_table | 1 | 687 | `42` | 0.060 | O.count_nums 0.054; R.multiset_overlap 0.029; O.sum_nums 0.025 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.string_pair_table | 1 | 670 | `[0, 1, 2, 2, 2]` | 0.100 |  | `Subscript(Name('v5', Load()), Slice(BinOp(BinOp(` |
| C1.string_pair_table | 1 | 643 | `2` | 0.465 | R.multiset_overlap 0.575; O.const_2 0.465; O.n_distinct_nums 0.465 | `Subscript(Name('v5', Load()), BinOp(BinOp(Name('` |
| C1.string_pair_table | 2 | 698 | `[0, 1, 2, 2, 2]` | 0.110 |  | `Subscript(Name('v5', Load()), Slice(BinOp(BinOp(` |
| C1.string_pair_table | 2 | 659 | `54` | 0.049 | O.count_nums 0.023; A.str1_len 0.015; O.len_str1 0.015 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.string_pair_table | 2 | 643 | `2` | 0.451 | R.hamming_plus_lendiff 0.538; R.multiset_overlap 0.515; O.const_2 0.451 | `Subscript(Name('v5', Load()), BinOp(BinOp(Name('` |
| C1.string_pair_table | 3 | 680 | `[0, 1, 2, 2, 2, 2]` | 0.072 |  | `Subscript(Name('v5', Load()), Slice(BinOp(BinOp(` |
| C1.string_pair_table | 3 | 663 | `3` | 0.427 | O.const_3 0.427; R.multiset_overlap 0.394; O.const_2 0.354 | `Subscript(Name('v5', Load()), BinOp(BinOp(Name('` |
| C1.string_pair_table | 3 | 657 | `28` | 0.041 | O.sum_nums 0.009; O.count_nums 0.008; A.lit_min 0.005 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.string_pair_table | 4 | 688 | `[0, 1, 2, 3, 3, 3]` | 0.068 |  | `Subscript(Name('v5', Load()), Slice(BinOp(BinOp(` |
| C1.string_pair_table | 4 | 668 | `94` | 0.033 | O.count_nums 0.006; A.lit_min 0.003; O.const_0 0.003 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.string_pair_table | 4 | 644 | `3` | 0.419 | R.hamming_plus_lendiff 0.488; O.const_3 0.419; R.multiset_overlap 0.360 | `Subscript(Name('v5', Load()), BinOp(BinOp(Name('` |
| C1.string_pair_table | 5 | 692 | `3` | 0.409 | O.const_3 0.409; R.multiset_overlap 0.371; R.hamming_plus_lendiff 0.324 | `Subscript(Name('v5', Load()), BinOp(BinOp(Name('` |
| C1.string_pair_table | 5 | 663 | `44` | 0.024 | A.lit_min 0.002; O.const_0 0.002; O.len_list_longest 0.002 | `Call(Name('sum', Load()), [Name('v5', Load())], ` |
| C1.string_pair_table | 5 | 645 | `[0, 1, 2, 3, 3, 3, 3]` | 0.064 |  | `Subscript(Name('v5', Load()), Slice(BinOp(BinOp(` |
| C1.turtle_walk | 1 | 673 | `4` | 0.227 | R.F_minus_B 0.816; R.count_F 0.816; R.count_F_plus_B 0.816 | `Name('v4', Load())|Call(Name('max', Load()), [Na` |
| C1.turtle_walk | 1 | 670 | `0,0` | 0.034 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.turtle_walk | 1 | 657 | `4` | 0.210 | R.F_minus_B 0.775; R.count_F 0.775; R.count_F_plus_B 0.775 | `BinOp(Call(Name('abs', Load()), [Name('v1', Load` |
| C1.turtle_walk | 2 | 713 | `-1,1` | 0.021 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.turtle_walk | 2 | 653 | `6` | 0.188 | R.F_minus_B 0.620; R.count_F 0.620; R.count_F_plus_B 0.620 | `Name('v4', Load())|Call(Name('max', Load()), [Na` |
| C1.turtle_walk | 2 | 634 | `4` | 0.155 | R.F_minus_B 0.636; R.count_F 0.636; R.count_F_plus_B 0.636 | `BinOp(Call(Name('abs', Load()), [Name('v1', Load` |
| C1.turtle_walk | 3 | 699 | `3` | 0.186 | R.F_minus_B 0.559; O.const_3 0.186; O.max#2 0.186 | `BinOp(Call(Name('abs', Load()), [Name('v1', Load` |
| C1.turtle_walk | 3 | 680 | `3` | 0.218 | R.F_minus_B 0.426; O.const_3 0.218; O.max#2 0.218 | `Name('v4', Load())|Call(Name('max', Load()), [Na` |
| C1.turtle_walk | 3 | 621 | `0,0` | 0.045 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.turtle_walk | 4 | 676 | `3` | 0.169 | R.F_minus_B 0.498; O.const_3 0.169; O.max#2 0.169 | `BinOp(Call(Name('abs', Load()), [Name('v1', Load` |
| C1.turtle_walk | 4 | 663 | `-1,-1` | 0.032 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.turtle_walk | 4 | 661 | `4` | 0.212 | R.F_minus_B 0.357; A.lit_max 0.212; O.max#1 0.212 | `Name('v4', Load())|Call(Name('max', Load()), [Na` |
| C1.turtle_walk | 5 | 702 | `5` | 0.228 | R.F_minus_B 0.310; O.n_distinct_nums 0.228; O.const_3 0.174 | `Name('v4', Load())|Call(Name('max', Load()), [Na` |
| C1.turtle_walk | 5 | 673 | `-1,0` | 0.025 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.turtle_walk | 5 | 625 | `2` | 0.144 | R.F_minus_B 0.426; O.const_2 0.144; O.const_3 0.144 | `BinOp(Call(Name('abs', Load()), [Name('v1', Load` |
| C1.turtle_walk_r2 | 1 | 523 | `0` | 0.214 | A.echo_printed_initial 0.214; A.lit_min 0.214; O.const_0 0.214 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 1 | 507 | `0` | 0.207 | R.sum_forward_minus_back 0.290; R.sum_forward_steps 0.290; A.echo_printed_initial 0.207 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.turtle_walk_r2 | 1 | 497 | `0,0` | 0.034 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.turtle_walk_r2 | 1 | 473 | `0` | 0.256 | A.echo_printed_initial 0.256; A.lit_min 0.256; O.const_0 0.256 | `Name('v2', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 2 | 526 | `0,1` | 0.017 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.turtle_walk_r2 | 2 | 505 | `0` | 0.184 | A.echo_printed_initial 0.184; A.lit_min 0.184; O.const_0 0.184 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 2 | 495 | `0` | 0.196 | A.echo_printed_initial 0.196; A.lit_min 0.196; O.const_0 0.196 | `Name('v2', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 2 | 474 | `0` | 0.183 | R.sum_forward_minus_back 0.228; R.sum_forward_steps 0.228; A.echo_printed_initial 0.183 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.turtle_walk_r2 | 3 | 525 | `0` | 0.139 | A.echo_printed_initial 0.139; A.lit_min 0.139; O.const_0 0.139 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 3 | 494 | `0,-1` | 0.018 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.turtle_walk_r2 | 3 | 493 | `0` | 0.164 | A.echo_printed_initial 0.164; A.lit_min 0.164; O.const_0 0.164 | `Name('v2', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 3 | 488 | `0` | 0.180 | R.sum_forward_steps 0.199; A.echo_printed_initial 0.180; A.lit_min 0.180 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.turtle_walk_r2 | 4 | 526 | `0` | 0.126 | A.echo_printed_initial 0.126; A.lit_min 0.126; O.const_0 0.126 | `Name('v2', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 4 | 505 | `1,1` | 0.022 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.turtle_walk_r2 | 4 | 490 | `0` | 0.127 | A.echo_printed_initial 0.127; A.lit_min 0.127; O.const_0 0.127 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 4 | 479 | `0` | 0.138 | A.echo_printed_initial 0.138; A.lit_min 0.138; O.const_0 0.138 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.turtle_walk_r2 | 5 | 521 | `0` | 0.098 | A.echo_printed_initial 0.098; A.lit_min 0.098; O.const_0 0.098 | `Name('v2', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 5 | 520 | `6` | 0.112 | R.sum_forward_steps 0.123; A.lit_max 0.112; O.max#1 0.112 | `Name('v4', Load())|Constant('int')@-|Name('v6', ` |
| C1.turtle_walk_r2 | 5 | 492 | `0` | 0.096 | A.echo_printed_initial 0.096; A.lit_min 0.096; O.const_0 0.096 | `Name('v1', Load())|Constant('int')@-|Constant('i` |
| C1.turtle_walk_r2 | 5 | 467 | `0,-1` | 0.017 |  | `BinOp(BinOp(Call(Name('str', Load()), [Name('v1'` |
| C1.union_find_links | 1 | 1089 | `[0, 0, 0, 3, 1, 0]` | 0.007 | R.naive_links_v->u 0.047; R.naive_links_u->v 0.041 | `Name('v1', Load())|List([Constant('int'), Consta` |
| C1.union_find_links | 1 | 578 | `5` | 0.100 | A.list1_last 0.100; A.list1_max 0.100; O.len_list1_minus1 0.100 | `Name('v8', Load())|Call(Name('v0', Load()), [Nam` |
| C1.union_find_links | 1 | 333 | `0` | 0.333 | A.list1_first 0.333; A.list1_min 0.333; A.list1_mode 0.333 | `Call(Name('v0', Load()), [Name('v1', Load()), Co` |
| C1.union_find_links | 2 | 1112 | `[0, 0, 0, 3, 0, 0, 0]` | 0.005 | R.naive_links_v->u 0.025; R.naive_links_u->v 0.021 | `Name('v1', Load())|List([Constant('int'), Consta` |
| C1.union_find_links | 2 | 549 | `6` | 0.060 | A.list1_last 0.060; A.list1_max 0.060; O.len_list1_minus1 0.060 | `Name('v8', Load())|Call(Name('v0', Load()), [Nam` |
| C1.union_find_links | 2 | 339 | `0` | 0.286 | A.list1_first 0.286; A.list1_min 0.286; A.list1_mode 0.286 | `Call(Name('v0', Load()), [Name('v1', Load()), Co` |
| C1.union_find_links | 3 | 1116 | `[0, 0, 0, 0, 4, 0, 0, 7]` | 0.004 | R.naive_links_u->v 0.007; R.naive_links_v->u 0.004 | `Name('v1', Load())|List([Constant('int'), Consta` |
| C1.union_find_links | 3 | 535 | `11` | 0.054 | O.n_distinct_nums 0.049; A.list1_last 0.043; A.list1_max 0.043 | `Name('v8', Load())|Call(Name('v0', Load()), [Nam` |
| C1.union_find_links | 3 | 349 | `0` | 0.269 | A.list1_first 0.269; A.list1_min 0.269; A.list1_mode 0.269 | `Call(Name('v0', Load()), [Name('v1', Load()), Co` |
| C1.union_find_links | 4 | 1102 | `[0, 1, 1, 1, 3, 5, 4, 0,` | 0.002 | R.naive_links_v->u 0.004; R.naive_links_u->v 0.001 | `Name('v1', Load())|List([Constant('int'), Consta` |
| C1.union_find_links | 4 | 565 | `11` | 0.041 | A.list1_last 0.037; A.list1_len 0.037; A.list1_max 0.037 | `Name('v8', Load())|Call(Name('v0', Load()), [Nam` |
| C1.union_find_links | 4 | 333 | `0` | 0.249 | A.list1_first 0.249; A.list1_min 0.249; A.list1_mode 0.249 | `Call(Name('v0', Load()), [Name('v1', Load()), Co` |
| C1.union_find_links | 5 | 1078 | `[0, 1, 1, 1, 1, 1, 1, 5,` | 0.002 | R.naive_links_v->u 0.001 | `Name('v1', Load())|List([Constant('int'), Consta` |
| C1.union_find_links | 5 | 566 | `12` | 0.035 | A.list1_last 0.035; A.list1_max 0.035; O.len_list1_minus1 0.035 | `Name('v8', Load())|Call(Name('v0', Load()), [Nam` |
| C1.union_find_links | 5 | 356 | `0` | 0.323 | A.list1_first 0.323; A.list1_min 0.323; A.list1_mode 0.323 | `Call(Name('v0', Load()), [Name('v1', Load()), Co` |
