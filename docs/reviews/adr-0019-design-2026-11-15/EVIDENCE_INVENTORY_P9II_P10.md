# Evidence inventory: P9-II (Part A) and P10 (Part B)

- Produced by the clerk (Haiku 5.5, claude-haiku-5-5) as a read-only inventory. Not a review, not interpretation, not Astra review (`Astra review: NOT_PERFORMED`).
- Worktree: `/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1`; branch `claude/adr-0017-design`; HEAD at inventory time `413d747`.
- Every number is copied from the file cited beside it. Numbers were produced by scripts in the scratchpad directory (`evalkeys.py`, `build_inventory.py`); no repository file was edited, nothing was run that trains, benchmarks, downloads or touches the network.
- Labels follow each source's own wording: `registered result`, `calibration/rehearsal`, `exploratory diagnostic`. Environment facts carry `n/a (environment record)`.
- Items not present in the repository are listed as `NOT FOUND` at the end. Items that need judgement are listed under `NEEDS REVIEW`.

## PART A: P9-II inputs

### A0. What "P9-II" is in the repository

- No specification, ADR, config or result for "P9-II", "robust sparse address learning", "ADR-0019" or "P10" exists in the worktree (searched all worktree text (outside .git and .venv)). The only mentions: `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 570-576 (the human lead's mission text, quoted at §15.9) and `docs/reviews/p9i-consolidation-2026-11-15/INTEGRATION_AUDIT.md` line 259 ("Next study (ADR-0019, address learning) is not started"). The Part A content below therefore draws on P9-I (ADR-0017 §18, `studies/p9i/`) and on the P9 code it imports (`studies/p9/`).

### A1. P9-I registered run (ADR-0017 Part I, attempt 2): per-cell accuracy, distinct slots, query and attention diagnostics, next-byte loss

Source status: `results/p9i-run-attempt2-2026-11-15/OUTCOME.md` line 3: `**Study status: COMPLETE.** 57 of 57 cells`; line 4: `**Registered outcome: NO_INTERFACE_SELECTED (§I.8.3 step 4).**` Label: **registered result**.

Per-cell values from `results/p9i-run-attempt2-2026-11-15/cells.csv` (columns `accuracy_A`, `accuracy_B`, `optimizer_state_bytes`, `lm_before_nats`, `lm_after_nats`, `wall_seconds`) and from the eval record of each cell (`eval/<label>.eval.json`, keys `panels/A/distinct_selected_slots` etc.). "not recorded" = key absent in that eval file.

| label | arm | slots | facts | parent | seed | accuracy_A (cells.csv) | accuracy_B (cells.csv) | distinct_selected_slots A (eval) | distinct_selected_slots B (eval) | query diagnostics present (eval) | attention diagnostics present (eval) | lm_before_nats | lm_after_nats | optimizer_state_bytes | wall_seconds | eval file |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A4-n16384-b101-o301-s1801 | A4 | 16384 | 8192 | b101-o301 | 1801 | 0.028076171875 | 0.028076171875 | 10 | 10 | yes (cos A 0.999923684290831; B 0.9999240326597201) | yes (id mass 0.24083614349365234) | - | - | 6328360 | 159.4181198750157 | eval/A4-n16384-b101-o301-s1801.eval.json |
| A4-n16384-b101-o301-s1802 | A4 | 16384 | 8192 | b101-o301 | 1802 | 0.028076171875 | 0.028076171875 | 33 | 35 | yes (cos A 0.9998228940383848; B 0.9998207427832706) | yes (id mass 0.21788281202316284) | - | - | 6328360 | 124.94491366599686 | eval/A4-n16384-b101-o301-s1802.eval.json |
| A4-n16384-b102-o302-s1801 | A4 | 16384 | 8192 | b102-o302 | 1801 | 0.0323486328125 | 0.0343017578125 | 12 | 12 | yes (cos A 0.9999764995149671; B 0.9999778735242246) | yes (id mass 0.23837272822856903) | - | - | 6328360 | 136.1064141250099 | eval/A4-n16384-b102-o302-s1801.eval.json |
| A4-n4096-b101-o301-s1801 | A4 | 4096 | 2048 | b101-o301 | 1801 | 0.04296875 | 0.03955078125 | 59 | 61 | yes (cos A 0.9998558628516175; B 0.9998593644604754) | yes (id mass 0.24071764945983887) | - | - | 1609768 | 91.81456333299866 | eval/A4-n4096-b101-o301-s1801.eval.json |
| A4-n4096-b101-o301-s1802 | A4 | 4096 | 2048 | b101-o301 | 1802 | 0.04248046875 | 0.0400390625 | 32 | 33 | yes (cos A 0.999886798702159; B 0.9998777353747877) | yes (id mass 0.2472323477268219) | - | - | 1609768 | 83.41206366597908 | eval/A4-n4096-b101-o301-s1802.eval.json |
| A4-n65536-b101-o301-s1801 | A4 | 65536 | 32768 | b101-o301 | 1801 | 0.03021240234375 | 0.03021240234375 | 18 | 15 | yes (cos A 0.9994466646636678; B 0.9994396646013687) | yes (id mass 0.19748368859291077) | - | - | 25202728 | 507.4881364579778 | eval/A4-n65536-b101-o301-s1801.eval.json |
| A4-n65536-b101-o301-s1802 | A4 | 65536 | 32768 | b101-o301 | 1802 | 0.03021240234375 | 0.03021240234375 | 50 | 53 | yes (cos A 0.9962897653987; B 0.9962906259721134) | yes (id mass 0.2594347596168518) | - | - | 25202728 | 489.4688525419915 | eval/A4-n65536-b101-o301-s1802.eval.json |
| A4E-n16384-b101-o301-s1801 | A4E | 16384 | 8192 | b101-o301 | 1801 | 0.028076171875 | 0.028076171875 | 11 | 14 | yes (cos A 0.9998220851208686; B 0.9998227852141282) | yes (id mass 0.22984102368354797) | - | - | 6328360 | 125.23940741701517 | eval/A4E-n16384-b101-o301-s1801.eval.json |
| A4E-n16384-b101-o301-s1802 | A4E | 16384 | 8192 | b101-o301 | 1802 | 0.028076171875 | 0.028076171875 | 9 | 9 | yes (cos A 0.9997918500493876; B 0.9997940039817146) | yes (id mass 0.22968222200870514) | - | - | 6328360 | 132.03530074999435 | eval/A4E-n16384-b101-o301-s1802.eval.json |
| BB-0-n16384-b101-o301-s1801 | BB-0 | 16384 | 8192 | b101-o301 | 1801 | 0.0440673828125 | 0.0445556640625 | not recorded | not recorded | no | yes (id mass 0.7082514762878418) | 2.3494174778461456 | 4.1837552189826965 | 33808 | 36.85462945798645 | eval/BB-0-n16384-b101-o301-s1801.eval.json |
| BB-0-n16384-b101-o301-s1802 | BB-0 | 16384 | 8192 | b101-o301 | 1802 | 0.0440673828125 | 0.0445556640625 | not recorded | not recorded | no | yes (id mass 0.7082514762878418) | 2.3494174778461456 | 4.1837552189826965 | 33808 | 38.11788804200478 | eval/BB-0-n16384-b101-o301-s1802.eval.json |
| BB-0-n4096-b101-o301-s1801 | BB-0 | 4096 | 2048 | b101-o301 | 1801 | 0.0888671875 | 0.08349609375 | not recorded | not recorded | no | yes (id mass 0.7387561798095703) | 2.3494174778461456 | 4.694405972957611 | 33808 | 37.40475725004217 | eval/BB-0-n4096-b101-o301-s1801.eval.json |
| BB-0-n4096-b101-o301-s1802 | BB-0 | 4096 | 2048 | b101-o301 | 1802 | 0.0888671875 | 0.08349609375 | not recorded | not recorded | no | yes (id mass 0.7387561798095703) | 2.3494174778461456 | 4.694405972957611 | 33808 | 36.81996179098496 | eval/BB-0-n4096-b101-o301-s1802.eval.json |
| BB-0-n65536-b101-o301-s1801 | BB-0 | 65536 | 32768 | b101-o301 | 1801 | 0.03375244140625 | 0.03326416015625 | not recorded | not recorded | no | yes (id mass 0.38043510913848877) | 2.3494174778461456 | 4.525157868862152 | 33808 | 37.926978459057864 | eval/BB-0-n65536-b101-o301-s1801.eval.json |
| BB-0-n65536-b101-o301-s1802 | BB-0 | 65536 | 32768 | b101-o301 | 1802 | 0.03375244140625 | 0.03326416015625 | not recorded | not recorded | no | yes (id mass 0.38043510913848877) | 2.3494174778461456 | 4.525157868862152 | 33808 | 37.99937079101801 | eval/BB-0-n65536-b101-o301-s1802.eval.json |
| BB-D-n16384-b101-o301-s1801 | BB-D | 16384 | 8192 | b101-o301 | 1801 | 0.0401611328125 | 0.0400390625 | not recorded | not recorded | no | yes (id mass 0.6141890287399292) | 2.3494174778461456 | 4.063165009021759 | 6337572 | 130.04079908394488 | eval/BB-D-n16384-b101-o301-s1801.eval.json |
| BB-D-n16384-b101-o301-s1802 | BB-D | 16384 | 8192 | b101-o301 | 1802 | 0.0440673828125 | 0.0439453125 | not recorded | not recorded | no | yes (id mass 0.7123357057571411) | 2.3494174778461456 | 4.379750370979309 | 6337572 | 130.9135998749989 | eval/BB-D-n16384-b101-o301-s1802.eval.json |
| BB-D-n65536-b101-o301-s1801 | BB-D | 65536 | 32768 | b101-o301 | 1801 | 0.03021240234375 | 0.03021240234375 | not recorded | not recorded | no | yes (id mass 0.33895182609558105) | 2.3494174778461456 | 3.924946218729019 | 25211940 | 390.63801079202676 | eval/BB-D-n65536-b101-o301-s1801.eval.json |
| BB-D-n65536-b101-o301-s1802 | BB-D | 65536 | 32768 | b101-o301 | 1802 | 0.03021240234375 | 0.03021240234375 | not recorded | not recorded | no | yes (id mass 0.32396209239959717) | 2.3494174778461456 | 4.011045902967453 | 25211940 | 386.5209424160421 | eval/BB-D-n65536-b101-o301-s1802.eval.json |
| BB-n16384-b101-o301-s1801 | BB | 16384 | 8192 | b101-o301 | 1801 | 0.044677734375 | 0.045654296875 | 8 | 8 | yes (cos A 0.9995875749602845; B 0.9995920622034231) | yes (id mass 0.7263450622558594) | 2.3494174778461456 | 4.183033764362335 | 6337580 | 122.08305295795435 | eval/BB-n16384-b101-o301-s1801.eval.json |
| BB-n16384-b101-o301-s1802 | BB | 16384 | 8192 | b101-o301 | 1802 | 0.0447998046875 | 0.0440673828125 | 8 | 8 | yes (cos A 0.9996620337780074; B 0.9996627998348799) | yes (id mass 0.7460728287696838) | 2.3494174778461456 | 4.187950670719147 | 6337580 | 122.10344866599189 | eval/BB-n16384-b101-o301-s1802.eval.json |
| BB-n16384-b102-o302-s1801 | BB | 16384 | 8192 | b102-o302 | 1801 | 0.05078125 | 0.048583984375 | 10 | 9 | yes (cos A 0.9969331038114938; B 0.9970162527774893) | yes (id mass 0.8115650415420532) | 2.370128720998764 | 4.000984042882919 | 6337580 | 125.05719820800005 | eval/BB-n16384-b102-o302-s1801.eval.json |
| BB-n4096-b101-o301-s1801 | BB | 4096 | 2048 | b101-o301 | 1801 | 0.556640625 | 0.54345703125 | 2277 | 2274 | yes (cos A 0.022589531903173546; B 0.02074148519740057) | yes (id mass 0.6884765625) | 2.3494174778461456 | 4.214079141616821 | 1618988 | 92.19196670799283 | eval/BB-n4096-b101-o301-s1801.eval.json |
| BB-n4096-b101-o301-s1802 | BB | 4096 | 2048 | b101-o301 | 1802 | 0.64892578125 | 0.6494140625 | 2377 | 2356 | yes (cos A 0.007199731712140613; B 0.006456715469391146) | yes (id mass 0.6772890090942383) | 2.3494174778461456 | 4.465320706367493 | 1618988 | 89.25760945904767 | eval/BB-n4096-b101-o301-s1802.eval.json |
| BB-n65536-b101-o301-s1801 | BB | 65536 | 32768 | b101-o301 | 1801 | 0.033477783203125 | 0.0341796875 | 8 | 8 | yes (cos A 0.9999903714727937; B 0.9999904100453443) | yes (id mass 0.4200350344181061) | 2.3494174778461456 | 4.397760987281799 | 25211948 | 335.4286418330157 | eval/BB-n65536-b101-o301-s1801.eval.json |
| BB-n65536-b101-o301-s1802 | BB | 65536 | 32768 | b101-o301 | 1802 | 0.033538818359375 | 0.0343017578125 | 8 | 8 | yes (cos A 0.9999878473454167; B 0.9999878380854308) | yes (id mass 0.41251999139785767) | 2.3494174778461456 | 4.40457147359848 | 25211948 | 331.2759883340332 | eval/BB-n65536-b101-o301-s1802.eval.json |
| D-n16384-b101-o301-s1801 | D | 16384 | 8192 | b101-o301 | 1801 | 0.03564453125 | 0.03564453125 | not recorded | not recorded | no | no | - | - | 6303764 | 115.02532745798817 | eval/D-n16384-b101-o301-s1801.eval.json |
| D-n16384-b101-o301-s1802 | D | 16384 | 8192 | b101-o301 | 1802 | 0.03564453125 | 0.03564453125 | not recorded | not recorded | no | no | - | - | 6303764 | 115.11741770803928 | eval/D-n16384-b101-o301-s1802.eval.json |
| D7-n16384-b101-o301-s1801 | D7 | 16384 | 8192 | b101-o301 | 1801 | 0.7867431640625 | 0.7828369140625 | not recorded | not recorded | no | no | - | - | 6328340 | 84.8608072079951 | eval/D7-n16384-b101-o301-s1801.eval.json |
| D7-n16384-b101-o301-s1802 | D7 | 16384 | 8192 | b101-o301 | 1802 | 0.797607421875 | 0.8021240234375 | not recorded | not recorded | no | no | - | - | 6328340 | 84.89253658399684 | eval/D7-n16384-b101-o301-s1802.eval.json |
| D7-n16384-b102-o302-s1801 | D7 | 16384 | 8192 | b102-o302 | 1801 | 0.4393310546875 | 0.441162109375 | not recorded | not recorded | no | no | - | - | 6328340 | 76.99081629200373 | eval/D7-n16384-b102-o302-s1801.eval.json |
| D7-n65536-b101-o301-s1801 | D7 | 65536 | 32768 | b101-o301 | 1801 | 0.130584716796875 | 0.129974365234375 | not recorded | not recorded | no | no | - | - | 25202708 | 228.71447116602212 | eval/D7-n65536-b101-o301-s1801.eval.json |
| D7-n65536-b101-o301-s1802 | D7 | 65536 | 32768 | b101-o301 | 1802 | 0.127105712890625 | 0.1278076171875 | not recorded | not recorded | no | no | - | - | 25202708 | 226.0022034579888 | eval/D7-n65536-b101-o301-s1802.eval.json |
| E7-n16384-b101-o301-s1801 | E7 | 16384 | 8192 | b101-o301 | 1801 | 0.028076171875 | 0.028076171875 | 79 | 73 | yes (cos A 0.9476314357255995; B 0.9478228475171425) | no | - | - | 6328348 | 121.8794293749961 | eval/E7-n16384-b101-o301-s1801.eval.json |
| E7-n16384-b101-o301-s1802 | E7 | 16384 | 8192 | b101-o301 | 1802 | 0.028076171875 | 0.028076171875 | 103 | 104 | yes (cos A 0.9873898649062771; B 0.987616638169258) | no | - | - | 6328348 | 121.8771780419629 | eval/E7-n16384-b101-o301-s1802.eval.json |
| N-n16384-b101-o301-s1801 | N | 16384 | 8192 | b101-o301 | 1801 | 0.0279541015625 | 0.028076171875 | 67 | 66 | yes (cos A 0.08674226768813904; B 0.06781597031229847) | no | - | - | 6303772 | 108.65254741703393 | eval/N-n16384-b101-o301-s1801.eval.json |
| N-n16384-b101-o301-s1802 | N | 16384 | 8192 | b101-o301 | 1802 | 0.029541015625 | 0.02783203125 | 74 | 73 | yes (cos A 0.5403113731950071; B 0.5053856658297561) | no | - | - | 6303772 | 108.41816595796263 | eval/N-n16384-b101-o301-s1802.eval.json |
| N-n4096-b101-o301-s1801 | N | 4096 | 2048 | b101-o301 | 1801 | 0.04150390625 | 0.03857421875 | 76 | 87 | yes (cos A 0.921319877625931; B 0.9247125853328882) | no | - | - | 1585180 | 81.91809541702969 | eval/N-n4096-b101-o301-s1801.eval.json |
| N-n4096-b101-o301-s1802 | N | 4096 | 2048 | b101-o301 | 1802 | 0.0439453125 | 0.04052734375 | 47 | 44 | yes (cos A 0.6399914504847529; B 0.6056142636438739) | no | - | - | 1585180 | 67.72455308301141 | eval/N-n4096-b101-o301-s1802.eval.json |
| N-n65536-b101-o301-s1801 | N | 65536 | 32768 | b101-o301 | 1801 | 0.03021240234375 | 0.03021240234375 | 144 | 147 | yes (cos A 0.5424716345384; B 0.5384410125387386) | no | - | - | 25178140 | 319.6701495409943 | eval/N-n65536-b101-o301-s1801.eval.json |
| N-n65536-b101-o301-s1802 | N | 65536 | 32768 | b101-o301 | 1802 | 0.03106689453125 | 0.03009033203125 | 102 | 100 | yes (cos A 0.394054802342407; B 0.38886705881449624) | no | - | - | 25178140 | 320.538931875024 | eval/N-n65536-b101-o301-s1802.eval.json |
| R1-n16384-b101-o301-s1801 | R1 | 16384 | 8192 | b101-o301 | 1801 | 0.99951171875 | 0.9996337890625 | 16162 | 16162 | yes (cos A 7.887961763631797e-05; B 7.887961763631797e-05) | no | - | - | 6299672 | 105.86525674996665 | eval/R1-n16384-b101-o301-s1801.eval.json |
| R1-n16384-b101-o301-s1802 | R1 | 16384 | 8192 | b101-o301 | 1802 | 0.999267578125 | 0.9996337890625 | 16159 | 16159 | yes (cos A 7.887961763631797e-05; B 7.887961763631797e-05) | no | - | - | 6299672 | 105.97625629097456 | eval/R1-n16384-b101-o301-s1802.eval.json |
| R1-n16384-b102-o302-s1801 | R1 | 16384 | 8192 | b102-o302 | 1801 | 0.999755859375 | 0.999755859375 | 16259 | 16259 | yes (cos A 7.887961763631797e-05; B 7.887961763631797e-05) | no | - | - | 6299672 | 110.56224004202522 | eval/R1-n16384-b102-o302-s1801.eval.json |
| R1-n4096-b101-o301-s1801 | R1 | 4096 | 2048 | b101-o301 | 1801 | 1.0 | 1.0 | 4068 | 4068 | yes (cos A -8.233112249096244e-05; B -8.233112249096244e-05) | no | - | - | 1581080 | 73.7427565830294 | eval/R1-n4096-b101-o301-s1801.eval.json |
| R1-n4096-b101-o301-s1802 | R1 | 4096 | 2048 | b101-o301 | 1802 | 1.0 | 1.0 | 4069 | 4069 | yes (cos A -8.233112249096244e-05; B -8.233112249096244e-05) | no | - | - | 1581080 | 76.57496912498027 | eval/R1-n4096-b101-o301-s1802.eval.json |
| R1-n65536-b101-o301-s1801 | R1 | 65536 | 32768 | b101-o301 | 1801 | 0.967437744140625 | 0.96771240234375 | 64782 | 64782 | yes (cos A 1.5802666426357474e-06; B 1.5802666426357474e-06) | no | - | - | 25174040 | 309.2830517910188 | eval/R1-n65536-b101-o301-s1801.eval.json |
| R1-n65536-b101-o301-s1802 | R1 | 65536 | 32768 | b101-o301 | 1802 | 0.97137451171875 | 0.9720458984375 | 64737 | 64737 | yes (cos A 1.5802666426357474e-06; B 1.5802666426357474e-06) | no | - | - | 25174040 | 309.8832867090241 | eval/R1-n65536-b101-o301-s1802.eval.json |
| R2-n16384-b101-o301-s1801 | R2 | 16384 | 8192 | b101-o301 | 1801 | 1.0 | 1.0 | 8192 | 8192 | no | no | - | - | 4202516 | 50.295591457979754 | eval/R2-n16384-b101-o301-s1801.eval.json |
| R2-n16384-b101-o301-s1802 | R2 | 16384 | 8192 | b101-o301 | 1802 | 1.0 | 1.0 | 8192 | 8192 | no | no | - | - | 4202516 | 50.33076166699175 | eval/R2-n16384-b101-o301-s1802.eval.json |
| W7-n16384-b101-o301-s1801 | W7 | 16384 | 8192 | b101-o301 | 1801 | 0.028076171875 | 0.028076171875 | 232 | 242 | yes (cos A 0.9943784632794548; B 0.9943390497950225) | no | - | - | 6328348 | 112.40813116700156 | eval/W7-n16384-b101-o301-s1801.eval.json |
| W7-n16384-b101-o301-s1802 | W7 | 16384 | 8192 | b101-o301 | 1802 | 0.028076171875 | 0.028076171875 | 115 | 106 | yes (cos A 0.9969388727777738; B 0.9969378897957567) | no | - | - | 6328348 | 113.31329024996376 | eval/W7-n16384-b101-o301-s1802.eval.json |
| W7-n16384-b102-o302-s1801 | W7 | 16384 | 8192 | b102-o302 | 1801 | 0.0323486328125 | 0.0341796875 | 65 | 61 | yes (cos A 0.9977566892536859; B 0.9977672928331305) | no | - | - | 6328348 | 115.64156000001822 | eval/W7-n16384-b102-o302-s1801.eval.json |
| W7-n4096-b101-o301-s1801 | W7 | 4096 | 2048 | b101-o301 | 1801 | 0.041015625 | 0.03955078125 | 207 | 210 | yes (cos A 0.9936338081117455; B 0.9935433412082343) | no | - | - | 1609756 | 80.17159474996151 | eval/W7-n4096-b101-o301-s1801.eval.json |
| W7-n4096-b101-o301-s1802 | W7 | 4096 | 2048 | b101-o301 | 1802 | 0.041015625 | 0.037109375 | 17 | 16 | yes (cos A 0.9616204712837968; B 0.9604442288435434) | no | - | - | 1609756 | 80.25561354198726 | eval/W7-n4096-b101-o301-s1802.eval.json |
| W7-n65536-b101-o301-s1801 | W7 | 65536 | 32768 | b101-o301 | 1801 | 0.03021240234375 | 0.03021240234375 | 124 | 126 | yes (cos A 0.9909059384401933; B 0.9910165650868965) | no | - | - | 25202716 | 384.85175874998095 | eval/W7-n65536-b101-o301-s1801.eval.json |
| W7-n65536-b101-o301-s1802 | W7 | 65536 | 32768 | b101-o301 | 1802 | 0.03021240234375 | 0.03021240234375 | 83 | 82 | yes (cos A 0.9945864885641422; B 0.994567551427726) | no | - | - | 25202716 | 435.3720241669798 | eval/W7-n65536-b101-o301-s1802.eval.json |

Key inventory of the 57 eval records (`results/p9i-run-attempt2-2026-11-15/eval/*.eval.json`); count = number of files containing the key path (panel keys counted for A and B each):

| key path (JSON) | count (eval files, panels counted per panel) |
|---|---|
| /arm | 57 |
| /calibration_selected_updates | 57 |
| /calibration_sha256 | 57 |
| /facts | 57 |
| /identity/config_sha256 | 57 |
| /identity/frozen_source_sha256 | 57 |
| /identity/source_sha256 | 57 |
| /identity/spec_sha256 | 57 |
| /kind | 57 |
| /label | 57 |
| /language_modelling/after_nats | 17 |
| /language_modelling/before_nats | 17 |
| /language_modelling/degraded | 17 |
| /language_modelling/relative_rise | 17 |
| /panels/{A,B}/accuracy | 114 |
| /panels/{A,B}/accuracy_with_neighbour | 114 |
| /panels/{A,B}/accuracy_without_neighbour | 114 |
| /panels/{A,B}/attention/identifier_mass_mean | 52 |
| /panels/{A,B}/attention/identifier_mass_per_head | 52 |
| /panels/{A,B}/attention/uniform_mass | 52 |
| /panels/{A,B}/chance_interval | 114 |
| /panels/{A,B}/correct | 114 |
| /panels/{A,B}/disabled_accuracy | 114 |
| /panels/{A,B}/disabled_at_chance | 114 |
| /panels/{A,B}/disabled_correct | 114 |
| /panels/{A,B}/distinct_selected_slots | 80 |
| /panels/{A,B}/facts | 114 |
| /panels/{A,B}/i_acc_bits | 114 |
| /panels/{A,B}/i_acc_bits_per_fact | 114 |
| /panels/{A,B}/leakage | 114 |
| /panels/{A,B}/logloss_gain_bits | 114 |
| /panels/{A,B}/loss_256_nats | 114 |
| /panels/{A,B}/mass_in_alphabet | 114 |
| /panels/{A,B}/memory_dependence_chance | 114 |
| /panels/{A,B}/permuted_accuracy | 114 |
| /panels/{A,B}/permuted_at_chance | 80 |
| /panels/{A,B}/permuted_correct | 80 |
| /panels/{A,B}/query/facts | 76 |
| /panels/{A,B}/query/mean_cosine_different | 76 |
| /panels/{A,B}/query/share_nearest_above_0_9 | 76 |
| /panels/{A,B}/sha256 | 114 |
| /panels/{A,B}/stream | 114 |
| /panels/{A,B}/support/correct_facts | 80 |
| /panels/{A,B}/support/mean_length | 80 |
| /panels/{A,B}/support/share_with_support | 80 |
| /panels/{A,B}/support/site_read_removed_stays_correct_share | 80 |
| /panels/{A,B}/support/useful_slots | 80 |
| /panels/{A,B}/support/with_support | 80 |
| /panels/{A,B}/unseen_accuracy | 114 |
| /panels/{A,B}/unseen_correct | 114 |
| /panels/{A,B}/unseen_facts | 114 |
| /parent | 57 |
| /schema | 57 |
| /secondary/H1/accuracy | 57 |
| /secondary/H1/chance_interval | 57 |
| /secondary/H1/correct | 57 |
| /secondary/H1/facts | 57 |
| /secondary/H1/sha256 | 57 |
| /secondary/H1/stream | 57 |
| /secondary/H2/accuracy | 57 |
| /secondary/H2/chance_interval | 57 |
| /secondary/H2/correct | 57 |
| /secondary/H2/facts | 57 |
| /secondary/H2/sha256 | 57 |
| /secondary/H2/stream | 57 |
| /secondary/MIXED/accuracy | 57 |
| /secondary/MIXED/chance_interval | 57 |
| /secondary/MIXED/correct | 57 |
| /secondary/MIXED/facts | 57 |
| /secondary/MIXED/sha256 | 57 |
| /secondary/MIXED/stream | 57 |
| /seed | 57 |
| /slots | 57 |
| /study | 57 |
| /update | 57 |

Distinct selected slots exist only where `panels/{A,B}/distinct_selected_slots` is present (N, W7, E7, A4, A4E, R1, R2, BB arms); query diagnostics only under `panels/{A,B}/query/` (arms N, W7, E7, A4, A4E, R1, BB; not R2, BB-0, BB-D, D, D7); attention under `panels/{A,B}/attention/` (A4, A4E, BB, BB-0, BB-D); next-byte loss under top-level `language_modelling/` (BB, BB-D, BB-0 only). Source: the key table above and `outputs` of `evalkeys.py` in the scratchpad.

Summary per arm and size, from `classes.csv` (label `registered result`) and `OUTCOME.md` lines 10-23:

| arm | slots | class | raw classes (seed/panel) | B102 present | dense comparison | language modelling |
|---|---|---|---|---|---|---|
| A4 | 16384 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | True | NOT COMPARED |  |
| A4 | 4096 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False | NOT COMPARED |  |
| A4 | 65536 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False | NOT COMPARED |  |
| A4E | 16384 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False | NOT COMPARED |  |
| BB | 16384 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | True | NOT COMPARED | LANGUAGE MODELLING DEGRADED |
| BB | 4096 | INTERFACE_PARTIAL | {"1801/A": "PARTIAL", "1801/B": "PARTIAL", "1802/A": "PARTIAL", "1802/B": "PARTIAL"} | False |  | LANGUAGE MODELLING DEGRADED |
| BB | 65536 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False | NOT COMPARED | LANGUAGE MODELLING DEGRADED |
| E7 | 16384 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False | NOT COMPARED |  |
| N | 16384 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False | NOT COMPARED |  |
| N | 4096 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False | NOT COMPARED |  |
| N | 65536 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False | NOT COMPARED |  |
| W7 | 16384 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | True | NOT COMPARED |  |
| W7 | 4096 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False |  |  |
| W7 | 65536 | INTERFACE_FAILS | {"1801/A": "FAILS", "1801/B": "FAILS", "1802/A": "FAILS", "1802/B": "FAILS"} | False | NOT COMPARED |  |

BB next-byte loss (cells.csv, `lm_before_nats` = 2.3494174778461456 for B101 cells and 2.370128720998764 for the B102 BB cell; `lm_after_nats` range per arm from the table above; `lm_relative_rise` in cells.csv): BB 4.000984042882919-4.465320706367493 nats (rise 0.6880872365433884-0.9006075967652734); BB-D 3.924946218729019-4.379750370979309; BB-0 4.1837552189826965-4.694405972957611 (rise 0.7807627884075333-0.998114859203848). Source: `cells.csv` columns `lm_before_nats`, `lm_after_nats`, `lm_relative_rise`; `OUTCOME.md` line 26 ("next-byte loss 2.35 → 3.92–4.69 nats (rise 67–100%)").

### A2. Collapse diagnostics, diagnostic training runs, and the scripts that produced them

**Label: exploratory diagnostic.** Source wording: `REVIEW.md` line 6 ("They are **diagnostics, not results**") and `OUTCOME.md` line 29 ("What the review found about why (diagnostic, not registered results)"). Reviewer: Claude Opus 5.5 (`REVIEW.md` line 3); Astra review NOT_PERFORMED.

Collapse numbers, verbatim from the review:

`docs/reviews/p9i-results-2026-11-15/REVIEW.md` lines 46-46:
> L46: - Did W, the interface and the keys receive gradient and move? Yes, but little in the collapsed state. Registered snapshots (d3): W7 `wq` moved 2.4× (seed 1801) and 8.1× (seed 1802) its initial norm at 4,096, 2.5–3.3× at 16,384, 4.6× at 65,536; A4 q/k/v 1.5–6.6×; every key row moved at 4,096 (mean 0.17 against an initial row norm of about 0.08) and **the keys aligned with the collapsed query** (mean cosine of a unit key to the mean key direction 0.93 at 4,096, 0.47 at 16,384). At the trained W7-4096 snapshot the gradient on `wq` is 2.7e-6 against 1.9e-2 on `wo` (d5). Loss curves (r2): every learned-query arm falls from 4.68–4.78 to 3.465–3.471 nats ≈ ln 32 = 3.466 within about 1,000 updates and then stays there: it learns the alphabet marginal and nothing fact-specific. R1 continues to 0.72–1.12.

`docs/reviews/p9i-results-2026-11-15/REVIEW.md` lines 50-61:
> L50: \| cell \| mean query cosine \| eff. rank (centred) \| distinct top-1 \| largest top-1 share \| facts with a private slot \| fact-independent share of E‖z‖² (init → trained) \| identifier share of the fact-dependent variance (init → trained) \|
> L51: \|---\|---\|---\|---\|---\|---\|---\|---\|
> L52: \| W7 4,096 s1801 \| 0.994 \| 3.2 \| 1 \| 1.00 \| 2.3% \| 0.57 → 0.95 \| 0.62 → 0.25 \|
> L53: \| W7 4,096 s1802 \| 0.962 \| 1.6 \| 2 \| 1.00 \| 0.1% \| 0.50 → 0.94 \| 0.54 → 0.76 \|
> L54: \| W7 16,384 s1801 \| 0.994 \| 2.6 \| 4 \| 0.53 \| 0.8% \| 0.56 → 0.97 \| 0.61 → 0.44 \|
> L55: \| W7 65,536 s1801 \| 0.991 \| 5.2 \| 5 \| 0.45 \| 0.1% \| 0.56 → 0.97 \| 0.61 → 0.75 \|
> L56: \| E7 16,384 s1801 \| 0.948 \| 1.2 \| 4 \| 0.66 \| 0.2% \| 0.37 → 0.91 \| 0.57 → 0.67 \|
> L57: \| A4 16,384 s1801 \| 1.000 \| 1.7 \| 4 \| 0.57 \| 0% \| — → 0.99 \| — \|
> L58: \| A4E 16,384 s1801 \| 1.000 \| 1.1 \| 2 \| 0.95 \| 0% \| — → 0.98 \| — \|
> L59: \| N 16,384 s1801 \| 0.087 \| 1.2 \| 5 \| 0.35 \| 0.05% \| → 0.22 \| — \|
> L60: \| BB 4,096 s1801 (PARTIAL) \| 0.023 \| 13.2 \| 1,233 \| 0.006 \| 8.4% \| → 0.02 \| — \|
> L61: \| BB 16,384 s1801 \| 1.000 \| 3.0 \| 6 \| 0.43 \| 0% \| → 0.98 \| — \|

`docs/reviews/p9i-results-2026-11-15/REVIEW.md` lines 62-63:
> L62: 
> L63: "Private slot" = in the top 8 of exactly one fact (the learned arms have no designated own-fact key, so the requested "rank of the own-fact key" is not defined for them; this is my substitute). Reading: 91–99% of the pre-normalization query is the same vector for every fact (the separator/binding/position common mode); of the small fact-dependent remainder the identifier positions carry 25–76%. A4/A4E attention on the identifier positions is at the uniform level (0.24 against 0.23 for uniform attention). N's queries are spread (cosine 0.09) but carry essentially one direction (effective rank 1.2) and still reach 5 top-1 slots.

`docs/reviews/p9i-results-2026-11-15/REVIEW.md` lines 67-74:
> L67: \| data \| seeds \| accuracy at 8,192 (Panel A of that draw) \|
> L68: \|---\|---\|---\|
> L69: \| rehearsal draw 2 \| 500001 (frozen code; my trainer), 500002 (mine), 500003, 500004 (frozen) \| 0.981, 0.984, 0.973, 0.937, 0.969 \|
> L70: \| rehearsal draw 0 \| 500001 (mine), 500003, 500004 (frozen) \| 0.981, 0.984, 0.960 \|
> L71: \| p9i-test-2 \| 500001 (frozen) \| 0.951 \|
> L72: \| p9i-test-0 \| 500001 (frozen) \| 0.159 (escape under way, cosine 0.08) \|
> L73: \| p9i-test-1 \| 500001 (frozen) \| 0.056 (escape starting, cosine 0.59) \|
> L74: \| *registered (for comparison)* \| *1801, 1802* \| *0.041, 0.041 (cosine 0.994, 0.962)* \|

`docs/reviews/p9i-results-2026-11-15/REVIEW.md` lines 76-76:
> L76: In every run the queries collapse by update 64 (cosine 0.95–0.998, 1–6 distinct top-1 slots) and the loss sits at ≈ ln 32; in most draws `wq` then keeps growing (≈ 9× at 2,048, ≈ 15× at 4,096, ≈ 18× at 8,192) and the queries separate between about 2,000 and 6,000 updates, after which accuracy rises to 0.94–0.98. In the registered draw `wq` grew only 2.4–8.1× by 8,192, so the escape had not begun. Within a draw the outcome hardly depends on the init seed; between draws it does. At 16,384 slots / 8,192 facts (draws 0 and 2, frozen code, seed 500001) the escape had begun but was far from complete at 8,192 updates (0.043 and 0.039; cosine 0.49 and 0.69). A4 stays collapsed on draw 2 with both implementations (0.035, cosine ≈ 1). Two mechanism probes on draw 2 did **not** prevent the early collapse and escaped at the same time as plain W7: a trainable fact-independent bias at the answer site (0.978) and keys initialized at the initial queries (0.981). So the collapse is not caused only by the fact-independent alphabet prior. My hypothesis that it was is refuted.

Geometry and shared-vector share per registered snapshot, from `outputs/d3_snapshot_diagnostics.jsonl` (one JSON record per label; fields `query_geometry.*`, `window_split_init.*`, `window_split_trained.*`, `movement.*`; the first line of that file is plain text). Values as recorded:

| label (registered snapshot) | mean_cos_different (trained) | eff_rank_centred_queries | distinct_top1 | largest_top1_share | private_slots | facts_with_a_private_slot | fact-independent share of E|z|^2 (init -> trained) | identifier-slot share of fact-dependent variance (init -> trained) |
|---|---|---|---|---|---|---|---|---|
| W7-n4096-b101-o301-s1801 | 0.9936338065684082 | 3.1965181999463135 | 1 | 1.0 | 53 | 0.02294921875 | 0.5653592624179166 -> 0.9493489545093624 | 0.6182 -> 0.2463 |
| W7-n4096-b101-o301-s1802 | 0.9616204717591548 | 1.5515451002667637 | 2 | 0.9951171875 | 2 | 0.0009765625 | 0.4983988545352755 -> 0.9427563308549166 | 0.5424 -> 0.7589 |
| W7-n16384-b101-o301-s1801 | 0.9943784645828749 | 2.5698410915330343 | 4 | 0.532470703125 | 71 | 0.0084228515625 | 0.5645431633647204 -> 0.9664797621461938 | 0.6107 -> 0.4431 |
| W7-n16384-b101-o301-s1802 | 0.996938871627123 | 4.052510682566709 | 4 | 0.3807373046875 | 49 | 0.0057373046875 | 0.49930266353934905 -> 0.9733367013933163 | 0.5413 -> 0.7441 |
| W7-n16384-b102-o302-s1801 | 0.9977566880191411 | 4.8411777240790705 | 4 | 0.474609375 | 14 | 0.001708984375 | 0.674952139036084 -> 0.9898889841464799 | 0.5215 -> 0.381 |
| W7-n65536-b101-o301-s1801 | 0.9909059389761232 | 5.2491318904335005 | 5 | 0.4530029296875 | 40 | 0.001190185546875 | 0.561681412268764 -> 0.967903998455859 | 0.6077 -> 0.7542 |
| E7-n16384-b101-o301-s1801 | 0.9476314341805242 | 1.189146856890561 | 4 | 0.6561279296875 | 21 | 0.002197265625 | 0.37201815149571577 -> 0.9104574188157809 | 0.5699 -> 0.6681 |
| A4-n4096-b101-o301-s1801 | 0.9998558624172126 | 2.2199637901530065 | 1 | 1.0 | 10 | 0.0048828125 | not in record | not in record |
| A4-n16384-b101-o301-s1801 | 0.9999236865507092 | 1.725981802691937 | 4 | 0.568115234375 | 0 | 0.0 | not in record | not in record |
| A4-n65536-b101-o301-s1801 | 0.9994466655372908 | 2.6696754237469533 | 1 | 1.0 | 1 | 3.0517578125e-05 | not in record | not in record |
| A4E-n16384-b101-o301-s1801 | 0.9998220859646366 | 1.056092633632803 | 2 | 0.9481201171875 | 0 | 0.0 | not in record | not in record |
| N-n16384-b101-o301-s1801 | 0.08674226739350785 | 1.2059798739024508 | 5 | 0.348876953125 | 4 | 0.00048828125 | not in record | not in record |
| BB-n4096-b101-o301-s1801 | 0.02258953357415271 | 13.229087077581397 | 1233 | 0.00634765625 | 215 | 0.08447265625 | not in record | not in record |
| BB-n16384-b101-o301-s1801 | 0.9995875757675572 | 3.0287614960325158 | 6 | 0.4339599609375 | 0 | 0.0 | not in record | not in record |
| R1-n16384-b101-o301-s1801 | None | None | None | None | None | None | not in record | not in record |

Parameter movement from initialization (same file, `movement`):

| label | movement.wq_rel_change | movement.keys_mean_row_change | movement.key_mean_cos_to_mean_direction |
|---|---|---|---|
| W7-n4096-b101-o301-s1801 | 2.433682918548584 | 0.1666870266199112 | 0.9338659048080444 |
| W7-n4096-b101-o301-s1802 | 8.09766960144043 | 0.21199104189872742 | 0.9179153442382812 |
| W7-n16384-b101-o301-s1801 | 2.4867963790893555 | 0.17924125492572784 | 0.47239387035369873 |
| W7-n16384-b101-o301-s1802 | 2.9036526679992676 | 0.1985807567834854 | 0.5514453649520874 |
| W7-n16384-b102-o302-s1801 | 3.2601757049560547 | 0.17422081530094147 | 0.36466121673583984 |
| W7-n65536-b101-o301-s1801 | 4.611784934997559 | 0.10887528955936432 | 0.18452930450439453 |
| E7-n16384-b101-o301-s1801 | 5.758317470550537 | 0.16734462976455688 | 0.42818522453308105 |
| A4-n4096-b101-o301-s1801 | 2.326399803161621 | 0.20984986424446106 | 0.901167094707489 |
| A4-n16384-b101-o301-s1801 | 2.681222677230835 | 0.17922702431678772 | 0.35219690203666687 |
| A4-n65536-b101-o301-s1801 | 4.374847888946533 | 0.0695243775844574 | 0.12031985819339752 |
| A4E-n16384-b101-o301-s1801 | 3.181028366088867 | 0.21885919570922852 | 0.5139505863189697 |
| N-n16384-b101-o301-s1801 | 6.649395942687988 | 0.24304907023906708 | 0.28330424427986145 |
| BB-n4096-b101-o301-s1801 | 19.052461624145508 | 0.7262436151504517 | 0.14367900788784027 |
| BB-n16384-b101-o301-s1801 | 5.726644515991211 | 0.008670679293572903 | 0.026972780004143715 |
| R1-n16384-b101-o301-s1801 | None | 0.8365609645843506 | 0.013251930475234985 |

Gradient magnitudes (`outputs/d5_gradient_check.txt`, `addition.wq` and `addition.wo` lines, own forward vs implementation; `|grad| impl` is the value shown):

| case (d5 line label) | parameter (d5 line) | |grad| impl |
|---|---|---|
| W7 4096 init seed 500001 | addition.keys | 4.970e-04 |
| W7 4096 init seed 500001 | addition.values | 7.356e-04 |
| W7 4096 init seed 500001 | addition.wq | 4.077e-04 |
| W7 4096 init seed 500001 | addition.wo | 7.296e-04 |
| W7 4096 init seed 500001 | addition.gate | 6.937e-06 |
| A4 4096 init seed 500001 | addition.keys | 1.047e-03 |
| A4 4096 init seed 500001 | addition.values | 1.637e-03 |
| A4 4096 init seed 500001 | addition.wq | 1.324e-03 |
| A4 4096 init seed 500001 | addition.wo | 1.488e-03 |
| A4 4096 init seed 500001 | addition.gate | 1.679e-05 |
| E7 16384 init seed 500001 | addition.keys | 2.907e-04 |
| E7 16384 init seed 500001 | addition.values | 3.846e-04 |
| E7 16384 init seed 500001 | addition.wq | 2.674e-04 |
| E7 16384 init seed 500001 | addition.wo | 3.059e-04 |
| E7 16384 init seed 500001 | addition.gate | 1.097e-06 |
| W7 4096 registered snapshot W7-n4096-b101-o301-s1801 | addition.keys | 5.628e-06 |
| W7 4096 registered snapshot W7-n4096-b101-o301-s1801 | addition.values | 3.765e-04 |
| W7 4096 registered snapshot W7-n4096-b101-o301-s1801 | addition.wq | 2.698e-06 |
| W7 4096 registered snapshot W7-n4096-b101-o301-s1801 | addition.wo | 1.861e-02 |
| W7 4096 registered snapshot W7-n4096-b101-o301-s1801 | addition.gate | 3.427e-04 |
| W7 16384 registered snapshot W7-n16384-b101-o301-s1801 | addition.keys | 6.901e-05 |
| W7 16384 registered snapshot W7-n16384-b101-o301-s1801 | addition.values | 1.017e-04 |
| W7 16384 registered snapshot W7-n16384-b101-o301-s1801 | addition.wq | 5.921e-05 |
| W7 16384 registered snapshot W7-n16384-b101-o301-s1801 | addition.wo | 9.695e-03 |
| W7 16384 registered snapshot W7-n16384-b101-o301-s1801 | addition.gate | 3.156e-05 |
| A4 16384 registered snapshot A4-n16384-b101-o301-s1801 | addition.keys | 1.427e-05 |
| A4 16384 registered snapshot A4-n16384-b101-o301-s1801 | addition.values | 5.000e-05 |
| A4 16384 registered snapshot A4-n16384-b101-o301-s1801 | addition.wq | 4.616e-06 |
| A4 16384 registered snapshot A4-n16384-b101-o301-s1801 | addition.wo | 9.651e-03 |
| A4 16384 registered snapshot A4-n16384-b101-o301-s1801 | addition.gate | 3.171e-05 |
| E7 16384 registered snapshot E7-n16384-b101-o301-s1801 | addition.keys | 1.516e-04 |
| E7 16384 registered snapshot E7-n16384-b101-o301-s1801 | addition.values | 6.732e-05 |
| E7 16384 registered snapshot E7-n16384-b101-o301-s1801 | addition.wq | 4.382e-05 |
| E7 16384 registered snapshot E7-n16384-b101-o301-s1801 | addition.wo | 9.683e-03 |
| E7 16384 registered snapshot E7-n16384-b101-o301-s1801 | addition.gate | 3.229e-05 |

Source lines: `docs/reviews/p9i-results-2026-11-15/outputs/d5_gradient_check.txt`. The review quotes the same numbers at `REVIEW.md` line 46 ("At the trained W7-4096 snapshot the gradient on `wq` is 2.7e-6 against 1.9e-2 on `wo`").

Collapse-escape diagnostic trainings (rehearsal draws 0 and 2, and unit-test seed sets; none registered). Per-run values are read from the jsonl files; the "onset" and "escape" columns are **clerk-derived** from the recorded checkpoints (updates 0, 64, 256, 512, 1024, 2048, 4096, 8192 only): onset = first checkpoint with `mean_cos` >= 0.95 after update 0; escape = earliest checkpoint from which `mean_cos` stays < 0.5 through update 8192 (so a transient dip is not counted); "not on grid" if no such checkpoint. No field named "escape" exists in the files.

Completed diagnostic runs (`outputs/*.jsonl`, not named KILLED):

| file | script (outputs/ from docs/reviews/p9i-results-2026-11-15/) | draw; data seed set; init seed | arm | slots | facts | updates | accuracy @4096 (Panel A of draw) | mean_cos @4096 | accuracy @8192 | mean_cos @8192 | distinct_top1 @8192 | wq_change_rel @8192 | collapse onset (update) | escape (update, derived) | first checkpoint with accuracy >= 0.5 | seconds (meta) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| d1_draw0_W7_n4096_f2048.jsonl | d1_diag_train.py (threads 2; no determinism call; auditor trainer) | draw 0; data -; seed 500001 | W7 | 4096 | 2048 | 8192 | 0.16455078125 | 0.04337117012567461 | 0.98095703125 | 0.0014581393548515542 | 1608 | 17.917009353637695 | 64 | 4096 | 8192 | 48.1 |
| d1_draw2_A4_n4096_f2048.jsonl | d1_diag_train.py (threads 2; no determinism call; auditor trainer) | draw 2; data -; seed 500001 | A4 | 4096 | 2048 | 8192 | 0.03466796875 | 0.9911215461227618 | 0.03466796875 | 0.9992965085920743 | 1 | 4.5719218254089355 | 64 | not on grid | not on grid | 62.8 |
| d1_draw2_R1_n4096_f2048.jsonl | d1_diag_train.py (threads 2; no determinism call; auditor trainer) | draw 2; data -; seed 500001 | R1 | 4096 | 2048 | 8192 | 0.99951171875 | 2.680472859309354e-05 | 1.0 | 2.680472859309354e-05 | 2012 | None | not on grid | not on grid | 2048 | 48.3 |
| d1_draw2_W7_n4096_f2048.jsonl | d1_diag_train.py (threads 2; no determinism call; auditor trainer) | draw 2; data -; seed 500001 | W7 | 4096 | 2048 | 8192 | 0.11474609375 | 0.10147893081528805 | 0.98388671875 | 0.0008350201602321614 | 1632 | 18.115066528320312 | 64 | 4096 | 8192 | 47.7 |
| d1_draw2_W7_n4096_f2048_s500002.jsonl | d1_diag_train.py (threads 2; no determinism call; auditor trainer) | draw 2; data -; seed 500002 | W7 | 4096 | 2048 | 8192 | 0.0986328125 | 0.2721731088858063 | 0.97314453125 | 0.0010934147631507488 | 1566 | 18.034347534179688 | 64 | 4096 | 8192 | 47.5 |
| d1_draw2_W7bias_n4096_f2048.jsonl | d1_diag_train.py (threads 2; no determinism call; auditor trainer) | draw 2; data -; seed 500001 | W7bias | 4096 | 2048 | 8192 | 0.125 | 0.14219861304878817 | 0.97802734375 | 0.0008672761074744077 | 1576 | 18.615205764770508 | 64 | 4096 | 8192 | 47.2 |
| d1_draw2_W7keyinit_n4096_f2048.jsonl | d1_diag_train.py (threads 2; no determinism call; auditor trainer) | draw 2; data -; seed 500001 | W7keyinit | 4096 | 2048 | 8192 | 0.240234375 | 0.03564957241775644 | 0.98046875 | 0.0005766938539601251 | 1537 | 18.186344146728516 | 64 | 4096 | 8192 | 47.8 |
| d2_their_A4_draw2_n4096_s500001.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data -; seed 500001 | A4 | 4096 | 2048 | 8192 | 0.03515625 | 0.9999682827726933 | 0.03466796875 | 0.9969485146167936 | 2 | 4.335412502288818 | 64 | not on grid | not on grid | 91.1 |
| d2_their_W7_draw0_n16384_s500001.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 0; data -; seed 500001 | W7 | 16384 | 8192 | 8192 | 0.036865234375 | 0.845792122074518 | 0.0433349609375 | 0.494110316348147 | 323 | 16.100875854492188 | 64 | 8192 | not on grid | 100.3 |
| d2_their_W7_draw0_n4096_s500003.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 0; data -; seed 500003 | W7 | 4096 | 2048 | 8192 | 0.0771484375 | 0.2245285988732766 | 0.984375 | 0.00017176737475209434 | 1708 | 17.169343948364258 | 64 | 4096 | 8192 | 83.5 |
| d2_their_W7_draw0_n4096_s500004.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 0; data -; seed 500004 | W7 | 4096 | 2048 | 8192 | 0.060546875 | 0.47716420223747946 | 0.95947265625 | 0.0018082165212671992 | 1542 | 17.685108184814453 | 64 | 4096 | 8192 | 84.6 |
| d2_their_W7_draw2_n16384_s500001.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data -; seed 500001 | W7 | 16384 | 8192 | 8192 | 0.0350341796875 | 0.8765638165896261 | 0.0390625 | 0.6856869176004444 | 63 | 15.048233032226562 | 64 | not on grid | not on grid | 101.0 |
| d2_their_W7_draw2_n4096_s500001.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data -; seed 500001 | W7 | 4096 | 2048 | 8192 | 0.1279296875 | 0.14519078869946797 | 0.98095703125 | 0.0009814273168265752 | 1613 | 18.31163215637207 | 64 | 4096 | 8192 | 61.1 |
| d2_their_W7_draw2_n4096_s500003.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data -; seed 500003 | W7 | 4096 | 2048 | 8192 | 0.06298828125 | 0.4966624659368844 | 0.93701171875 | 0.0006486680980454937 | 1396 | 18.047407150268555 | 64 | 4096 | 8192 | 83.2 |
| d2_their_W7_draw2_n4096_s500004.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data -; seed 500004 | W7 | 4096 | 2048 | 8192 | 0.0751953125 | 0.2795169667917251 | 0.96875 | 0.0005349807518962696 | 1508 | 18.074846267700195 | 64 | 4096 | 8192 | 84.5 |
| d4_their_W7_test0_n4096_s500001.jsonl | d4_their_trainer_seedsets.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data p9i-test-0; seed 500001 | W7 | 4096 | 2048 | 8192 | 0.0390625 | 0.917985493325365 | 0.1591796875 | 0.07704702488861738 | 431 | 17.92571449279785 | 64 | 8192 | not on grid | 76.5 |
| d4_their_W7_test1_n4096_s500001.jsonl | d4_their_trainer_seedsets.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data p9i-test-1; seed 500001 | W7 | 4096 | 2048 | 8192 | 0.0400390625 | 0.9863569795249328 | 0.0556640625 | 0.5935324332491749 | 25 | 17.35177993774414 | 64 | not on grid | not on grid | 68.7 |
| d4_their_W7_test2_n4096_s500001.jsonl | d4_their_trainer_seedsets.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data p9i-test-2; seed 500001 | W7 | 4096 | 2048 | 8192 | 0.052734375 | 0.5735116801473965 | 0.951171875 | 0.00048051735601274854 | 1529 | 17.495567321777344 | 64 | 8192 | 8192 | 71.0 |

Files named `*_attempt1_KILLED_at_4096.jsonl` (7 files). **Their contents are not partial**: each has 9 records, the last at update 8192, and meta `updates` = 8192 (see NEEDS REVIEW N3). Recorded here as found:

| file | script (outputs/ from docs/reviews/p9i-results-2026-11-15/) | draw; data seed set; init seed | arm | slots | facts | updates | accuracy @4096 (Panel A of draw) | mean_cos @4096 | accuracy @8192 | mean_cos @8192 | distinct_top1 @8192 | wq_change_rel @8192 | collapse onset (update) | escape (update, derived) | first checkpoint with accuracy >= 0.5 | seconds (meta) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| d2_their_A4_draw2_n4096_s500001_attempt1_KILLED_at_4096.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data -; seed 500001 | A4 | 4096 | 2048 | 8192 | 0.03369140625 | 0.9898632299543375 | 0.03515625 | 0.9984298659010423 | 1 | 3.0788772106170654 | 64 | not on grid | not on grid | 83.8 |
| d2_their_W7_draw0_n16384_s500001_attempt1_KILLED_at_4096.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 0; data -; seed 500001 | W7 | 16384 | 8192 | 8192 | 0.0362548828125 | 0.8537373744544615 | 0.0457763671875 | 0.4453248842787584 | 291 | 15.97465705871582 | 64 | 8192 | not on grid | 97.0 |
| d2_their_W7_draw0_n4096_s500003_attempt1_KILLED_at_4096.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 0; data -; seed 500003 | W7 | 4096 | 2048 | 8192 | 0.0546875 | 0.6023766498734924 | 0.94580078125 | 0.0008415471770640314 | 1455 | 17.981388092041016 | 64 | 8192 | 8192 | 78.7 |
| d2_their_W7_draw0_n4096_s500004_attempt1_KILLED_at_4096.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 0; data -; seed 500004 | W7 | 4096 | 2048 | 8192 | 0.07080078125 | 0.47333429897086077 | 0.94384765625 | 0.0007783329536696061 | 1439 | 18.26110076904297 | 64 | 4096 | 8192 | 80.2 |
| d2_their_W7_draw2_n16384_s500001_attempt1_KILLED_at_4096.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data -; seed 500001 | W7 | 16384 | 8192 | 8192 | 0.0338134765625 | 0.8888462818850094 | 0.03759765625 | 0.8238063139382024 | 42 | 14.578043937683105 | 64 | not on grid | not on grid | 96.7 |
| d2_their_W7_draw2_n4096_s500003_attempt1_KILLED_at_4096.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data -; seed 500003 | W7 | 4096 | 2048 | 8192 | 0.11962890625 | 0.1287707120439014 | 0.97998046875 | 0.0004498864489800389 | 1599 | 17.920520782470703 | 64 | 4096 | 8192 | 79.3 |
| d2_their_W7_draw2_n4096_s500004_attempt1_KILLED_at_4096.jsonl | d2_their_trainer_draw2.py (threads 2; no determinism call; frozen studies.p9i code) | draw 2; data -; seed 500004 | W7 | 4096 | 2048 | 8192 | 0.06494140625 | 0.4240655795028927 | 0.96142578125 | 0.00022096520430541517 | 1422 | 18.426443099975586 | 64 | 4096 | 8192 | 81.5 |

Diagnostic scripts and stated settings (from each script's docstring and code; line numbers from the script):

| script | what it does | line of thread setting | stated settings |
|---|---|---|---|
| d1_diag_train.py | auditor's own trainer (not imported from studies.p9i); AdamW lr 0.003, clip 1.0; variants W7, W7bias, W7keyinit, E7, A4, R1 | 52 | threads 2 (line 52); no use_deterministic_algorithms call found |
| d2_their_trainer_draw2.py | frozen studies.p9i code path (build_model, train.Trainer.step); auditor scoring | 42 | threads 2 (line 42); no determinism call found |
| d3_snapshot_diagnostics.py | no training; reads registered snapshots; geometry and movement | 31 | threads 4 (line 31); no determinism call found |
| d4_their_trainer_seedsets.py | as d2, with unit-test seed sets p9i-test-0/1/2 (studies.p9i.core.test_seeds, 900001 + 100 k) | 47 | threads 2 (line 47); no determinism call found |
| d5_gradient_check.py | gradient comparison, own forward vs implementation; no training | 26 | threads 4 (line 26); no determinism call found |

Registered pipeline setting for comparison: `studies/p9i/train.py` lines 775-782 (`configure_cpu`): `torch.set_num_threads(1)` and `torch.use_deterministic_algorithms(True, warn_only=False)`. The review says (REVIEW.md line 131) the diagnostics "ran with 2 threads and without `use_deterministic_algorithms`"; d3 and d5 set 4 threads (see NEEDS REVIEW N2).

Diagnostic statements the review itself makes (quoted):

`docs/reviews/p9i-results-2026-11-15/REVIEW.md` lines 65-65:
> L65: **2.3 The collapse happens in the first 64 updates; escape from it is slow and draw-dependent (diagnostics, not results).** With the frozen code or my trainer, W7 at 4,096 slots / 2,048 facts, U = 8,192:

`docs/reviews/p9i-results-2026-11-15/REVIEW.md` lines 76-76:
> L76: In every run the queries collapse by update 64 (cosine 0.95–0.998, 1–6 distinct top-1 slots) and the loss sits at ≈ ln 32; in most draws `wq` then keeps growing (≈ 9× at 2,048, ≈ 15× at 4,096, ≈ 18× at 8,192) and the queries separate between about 2,000 and 6,000 updates, after which accuracy rises to 0.94–0.98. In the registered draw `wq` grew only 2.4–8.1× by 8,192, so the escape had not begun. Within a draw the outcome hardly depends on the init seed; between draws it does. At 16,384 slots / 8,192 facts (draws 0 and 2, frozen code, seed 500001) the escape had begun but was far from complete at 8,192 updates (0.043 and 0.039; cosine 0.49 and 0.69). A4 stays collapsed on draw 2 with both implementations (0.035, cosine ≈ 1). Two mechanism probes on draw 2 did **not** prevent the early collapse and escaped at the same time as plain W7: a trainable fact-independent bias at the answer site (0.978) and keys initialized at the initial queries (0.981). So the collapse is not caused only by the fact-independent alphabet prior. My hypothesis that it was is refuted.

`docs/reviews/p9i-results-2026-11-15/REVIEW.md` lines 78-78:
> L78: **Conclusion for task 2.** The forward, the loss and the gradients are as specified, and the frozen code learns W7 at 4,096 within U on most other draws. So chance-level W7 is not explained by a code defect. It is an optimization failure of answer-loss training through top-8 cosine addressing: the queries collapse early, and whether they escape within U depends on the draw. The registered outcome stands as registered: under §I.8.3 W7 would need WORKS at all three sizes, and the 16,384 diagnostics suggest that it would fail there within U on these draws too. **The W7 class at 4,096 (FAILS) is a property of the registered draw. In 9 of 11 diagnostic runs on five other draws the same recipe reached 0.94–0.98.** This sensitivity is not visible from the registered records. `PENDING LEAD REVIEW`: how to state it, and whether it bears on any revision.

### A3. Calibration and rehearsal (P9-I, rehearsal draw 1 and draw 2; no registered seed)

**Label: calibration/rehearsal.** `results/p9i-calibration-2026-11-14/README.md` line 5: "Status: the lead's reading. Not audited at the time of writing. Rehearsal seeds, not registered seeds." (The later audit is `docs/reviews/p9i-prefreeze-audit-2026-11-14/AUDIT.md`, which ADR-0017 §15.5 cites as confirming the calibration.) Rehearsal README line 1-4: "time, memory, shapes, counts and identity were written; no loss or accuracy was read out".

Calibration rule inputs (`calibration.json`; keys `r1_min_accuracy`, `r2_min_accuracy`; minimum over the two B101 runs and both panels; `selected_updates` = 8192; `failed_sizes` = {}):

| rung | slots (facts = slots/2) | U=1024 | U=2048 | U=4096 | U=8192 | U=16384 |
|---|---|---|---|---|---|---|
| R2 | 4096 | 0.91357421875 | 1.0 | 1.0 | 1.0 | 1.0 |
| R2 | 16384 | 0.7701416015625 | 0.97509765625 | 1.0 | 1.0 | 1.0 |
| R2 | 65536 | 0.40472412109375 | 0.928314208984375 | 0.9969482421875 | 1.0 | 1.0 |
| R1 | 4096 | 0.296875 | 0.91064453125 | 0.99853515625 | 1.0 | 1.0 |
| R1 | 16384 | 0.095458984375 | 0.427001953125 | 0.97314453125 | 0.9991455078125 | 0.9998779296875 |
| R1 | 65536 | 0.05804443359375 | 0.100372314453125 | 0.42999267578125 | 0.96502685546875 | 0.9970703125 |

Controls (`calibration.json` key `controls`, also `calibration_controls.json`): exact_accuracy {"2048": 1.0, "32768": 1.0, "8192": 1.0}; G2 tests 8, level 0.999875, passed True. Chance intervals as recorded: A/2048 [36, 96]; A/8192 [198, 318]; A/32768 [905, 1147]. The no-memory counts are listed in `calibration.json` `controls.no_memory`.

| task label | status | returncode | task seconds (manifest.json) | peak_rss_bytes (manifest.json) | peak RSS GiB (clerk conversion) | seconds per update (DERIVED: task seconds / 16,384; includes snapshot scoring) |
|---|---|---|---|---|---|---|
| controls | completed | 0 | 5.432473458000459 | 501645312 | 0.467 | n/a |
| CAL-R1-n4096-b101-o301-s1791 | completed | 0 | 158.85603066696785 | 416776192 | 0.388 | 0.009695802653013175 |
| CAL-R1-n4096-b101-o301-s1792 | completed | 0 | 159.88902533397777 | 415268864 | 0.387 | 0.009758851643919542 |
| CAL-R1-n4096-b102-o302-s1791 | completed | 0 | 159.1547744999989 | 412893184 | 0.385 | 0.009714036529540948 |
| CAL-R1-n16384-b101-o301-s1791 | completed | 0 | 233.75914570799796 | 557383680 | 0.519 | 0.014267525983154172 |
| CAL-R1-n16384-b101-o301-s1792 | completed | 0 | 233.91774087498197 | 546390016 | 0.509 | 0.014277205863951536 |
| CAL-R1-n16384-b102-o302-s1791 | completed | 0 | 234.90305245795753 | 558039040 | 0.520 | 0.014337344510373384 |
| CAL-R1-n65536-b101-o301-s1791 | completed | 0 | 659.4287810830283 | 883769344 | 0.823 | 0.040248338689149676 |
| CAL-R1-n65536-b101-o301-s1792 | completed | 0 | 661.6416075000307 | 969867264 | 0.903 | 0.04038339889526554 |
| CAL-R1-n65536-b102-o302-s1791 | completed | 0 | 669.2423394159996 | 871219200 | 0.811 | 0.04084731075537107 |
| CAL-R2-n4096-b101-o301-s1791 | completed | 0 | 85.31204229098512 | 389349376 | 0.363 | 0.005207033831236885 |
| CAL-R2-n4096-b101-o301-s1792 | completed | 0 | 85.30191070900764 | 389545984 | 0.363 | 0.00520641544854783 |
| CAL-R2-n4096-b102-o302-s1791 | completed | 0 | 85.09565987501992 | 389677056 | 0.363 | 0.005193826896668696 |
| CAL-R2-n16384-b101-o301-s1791 | completed | 0 | 118.56183604203397 | 441106432 | 0.411 | 0.007236440188112425 |
| CAL-R2-n16384-b101-o301-s1792 | completed | 0 | 118.0962937080185 | 440942592 | 0.411 | 0.007208025739014801 |
| CAL-R2-n16384-b102-o302-s1791 | completed | 0 | 117.75833437498659 | 439042048 | 0.409 | 0.0071873983383170525 |
| CAL-R2-n65536-b101-o301-s1791 | completed | 0 | 243.63705179200042 | 684244992 | 0.637 | 0.014870425524414088 |
| CAL-R2-n65536-b101-o301-s1792 | completed | 0 | 243.4825638330076 | 660176896 | 0.615 | 0.014860996327698217 |
| CAL-R2-n65536-b102-o302-s1791 | completed | 0 | 241.80534174997592 | 618086400 | 0.576 | 0.014758626815794429 |

Per-update seconds and RSS are **not recorded** per update in the calibration records; the derived column assumes the 16,384-update schedule of `studies/p9i/stages.py` line 614-616 (`marks[-1]` = 16,384) and is not a recorded value (see NOT FOUND).

| slots | arm | cells | seconds per update (min - max) | max training peak RSS GiB | evaluation seconds (min - max) | max evaluation peak RSS GiB |
|---|---|---|---|---|---|---|
| 4096 | A4 | 2 | 0.008346 - 0.009638 | 0.326 | 0.603 - 0.828 | 0.387 |
| 4096 | BB | 2 | 0.011065 - 0.01171 | 0.325 | 0.981 - 1.054 | 0.468 |
| 4096 | BB-0 | 2 | 0.004421 - 0.004754 | 0.315 | 0.382 - 0.385 | 0.439 |
| 4096 | N | 2 | 0.009283 - 0.010248 | 0.320 | 0.699 - 0.813 | 0.379 |
| 4096 | R1 | 2 | 0.009364 - 0.009567 | 0.323 | 0.88 - 0.883 | 0.384 |
| 4096 | W7 | 2 | 0.009166 - 0.01035 | 0.324 | 0.86 - 0.889 | 0.381 |
| 16384 | A4 | 3 | 0.014258 - 0.014521 | 0.357 | 2.717 - 2.75 | 0.644 |
| 16384 | A4E | 2 | 0.014608 - 0.014637 | 0.352 | 2.657 - 2.69 | 0.642 |
| 16384 | BB | 3 | 0.013415 - 0.015319 | 0.352 | 2.478 - 2.772 | 0.736 |
| 16384 | BB-0 | 2 | 0.004641 - 0.004878 | 0.321 | 0.943 - 0.966 | 0.488 |
| 16384 | BB-D | 2 | 0.015123 - 0.015145 | 0.357 | 2.06 - 2.065 | 0.494 |
| 16384 | D | 2 | 0.014295 - 0.014316 | 0.349 | 1.832 - 1.834 | 0.450 |
| 16384 | D7 | 3 | 0.008607 - 0.008868 | 0.339 | 1.072 - 1.124 | 0.401 |
| 16384 | E7 | 2 | 0.014157 - 0.014164 | 0.355 | 2.659 - 2.692 | 0.624 |
| 16384 | N | 2 | 0.013922 - 0.014141 | 0.359 | 2.65 - 2.677 | 0.630 |
| 16384 | R1 | 3 | 0.014212 - 0.014359 | 0.355 | 2.657 - 2.69 | 0.639 |
| 16384 | R2 | 2 | 0.006162 - 0.00639 | 0.330 | 1.014 - 1.017 | 0.407 |
| 16384 | W7 | 3 | 0.013285 - 0.0142 | 0.354 | 2.514 - 2.669 | 0.626 |
| 65536 | A4 | 2 | 0.038893 - 0.039618 | 0.477 | 25.554 - 26.528 | 1.366 |
| 65536 | BB | 2 | 0.036931 - 0.041136 | 0.466 | 20.852 - 21.202 | 1.490 |
| 65536 | BB-0 | 2 | 0.004911 - 0.004993 | 0.322 | 3.307 - 3.307 | 0.691 |
| 65536 | BB-D | 2 | 0.048093 - 0.049317 | 0.456 | 19.713 - 19.765 | 0.903 |
| 65536 | D7 | 2 | 0.023755 - 0.026486 | 0.416 | 7.637 - 7.733 | 0.728 |
| 65536 | N | 2 | 0.038822 - 0.039654 | 0.473 | 20.76 - 21.303 | 1.390 |
| 65536 | R1 | 2 | 0.035103 - 0.03843 | 0.480 | 19.932 - 19.976 | 1.433 |
| 65536 | W7 | 2 | 0.037957 - 0.042612 | 0.477 | 20.775 - 21.914 | 1.382 |

Source: `results/p9i-rehearsal-2026-11-14/rehearsal_cells.csv` (57 rows; columns `seconds_per_update`, `train_peak_rss_bytes`, `evaluation_seconds`, `evaluation_peak_rss_bytes`), grouped by label arm and size by the clerk. The rehearsal README (lines 8-12) states the same measurements in rounded form ("0.008–0.012" seconds per update at 4,096 etc.). Measured with six workers running (README line 6).

Charged time (`results/p9i-calibration-2026-11-14/` ledger, `ledger_after_calibration.json`: calibrate 829.2843401249847 s; `results/p9i-rehearsal-2026-11-14/ledger_after_rehearsal.json`: rehearse 101.03409216698492 s; cap 14400.0 s).

### A4. Code assets in `studies/p9i/` and `studies/p9/`

**Label: n/a (code inventory).** Module descriptions are the first paragraph of each module docstring (read by parsing the file; cut at 260 characters).

| module | docstring (first paragraph, cut at 260 characters) |
|---|---|
| studies/p9i/__init__.py | P9I (ADR-0017 Part I, section 18): the query-interface prerequisite study. |
| studies/p9i/classes.py | P9I classes (ADR-0017 Part I, section I.8): pure functions from measurements to the raw class, the class at a size, the annotations and the selection outcome. Nothing here reads a file, trains or evaluates a model; ``stages.analyze`` turns eval records into... |
| studies/p9i/core.py | P9I shared contract: constants of ADR-0017 Part I (section 18), the 57-cell registry, seeds, the update-count rule of section I.6, thresholds of sections I.6 and I.8, config, identity hashes, record IO and the charged-time ledger of the 4-hour cap. |
| studies/p9i/evaluate.py | P9I evaluation (ADR-0017 Part I, section I.5): accuracy on Panels A and B (primary) and the H1, H2 and mixed-cluster streams (secondary), interface efficiency inputs, I_acc, the Sigma-renormalized log-loss gain and the 256-way loss (descriptive), query diag... |
| studies/p9i/model.py | P9I models (ADR-0017 Part I, section I.3): arms N, W7, E7, A4, A4E, R1, R2 on the flat memory of section 5, read at the answer sites only; the dense controls D plain and D7 (answer sites only); and block BB (BB, BB-D, BB-0), in which the block-0 attention o... |
| studies/p9i/report.py | P9I report (ADR-0017 Part I, sections I.8.3 and I.13): CSV, JSON and Markdown of the classes, the annotations, the selection, the exposures per fact per size, and the parameters and optimizer-state bytes per arm, written from the records of a run directory.... |
| studies/p9i/stages.py | P9I stages (ADR-0017 Part I, sections I.6, I.9-I.12): ``generate``, ``calibrate``, ``rehearse``, ``gates``, ``train``, ``evaluate``, ``analyze``, ``report`` and ``dry`` (tiny synthetic end to end). |
| studies/p9i/train.py | P9I training (ADR-0017 Part I, sections I.4, I.5 and 6.3): alphabet-only cross-entropy at answer sites, matched updates U for every cell, optimizer groups, snapshots with optimizer state, the training diagnostics of ADR-0017 section 6.3, and the modes ``reg... |
| studies/p9/__init__.py | P9 (ADR-0017): parallel useful-capacity, anti-collapse and locality diagnostics. |
| studies/p9/analysis_a.py | P9 Lane A analysis (package I6): capacity classes, annotations and the ladder report. |
| studies/p9/analysis_b.py | P9 Lane B analysis (package I6): utilization classes and the optimization annotations. |
| studies/p9/analysis_c.py | P9 Lane C analysis (package I6): the Lane C gate, locality classes, the hierarchy rule, and the synthetic-trace classes. |
| studies/p9/analysis_d.py | P9 Lane D analysis (package I6): incremental classes. |
| studies/p9/controls.py | P9 controls that involve no trained memory (package I1): exact retrieval, the no-memory baseline, frozen-hidden probes, the answer probability attainable through the frozen final layers, and the G2 chance report. |
| studies/p9/core.py | P9 shared contract: constants, the 100-cell registry, schedules, coefficients, record schemas, identity helpers and record IO. |
| studies/p9/data.py | P9 task data (package I1): alphabet, checksum identifiers, facts, clusters, templates, streams and panels, Lane D sets, hashing, the G1 generator checks and the rehearsal seed namespace. |
| studies/p9/evaluate.py | P9 evaluation (package I3): cached selections and weights, accuracy, I_acc with the chance floor, log-loss gain, seven-position knock-outs, minimal supports, U*, specificity, group ablation, value permutation and disabling, usage statistics, the LEAKAGE che... |
| studies/p9/incremental.py | P9 Lane D (package I5): phase A and phase B arms, replay, fresh optimizer at V1, and the Lane D measurements. |
| studies/p9/layout.py | P9 physical layouts for general N (package I4): identity, frequency packing, sparse co-access, random partition, branch-constrained co-access and the oracle cluster layout. |
| studies/p9/model.py | P9 models (package I2): the scalable memory (sizes, key widths, constant-candidate tree, ladder rungs R0/R0a/R1/R2/oracle branch), the parameter-matched dense adapter, and the wrapper around the frozen backbone. |
| studies/p9/objective.py | P9 objectives (package I2): soft inclusion, the global usage floor with the b-free gradient, the co-access term, and the absolute coefficients. |
| studies/p9/pool.py | P9 job manager (package I6): immutable task ids, stage manifests, worker semaphores, RSS and time limits, failed records kept, and the dependent-cell stop rule in every stage. |
| studies/p9/report.py | P9 reporting (package I6): decision map, study status, CSV/JSON/Markdown and the dashboard. |
| studies/p9/sim.py | P9 page-cache simulator for general N (package I4): LRU page misses, cache rule, count-preserving nulls with ADR-0016's identity null, pages per query and cross-query reuse, planted-trace generator and the key-traffic identity. |
| studies/p9/stages.py | P9 command-line driver (package I7): the single entry point of every stage. |
| studies/p9/store.py | P9 version store (package I5): copy-on-write snapshots and atomic manifest publication in a local directory; an engineering test only. |
| studies/p9/train.py | P9 training (package I2): answer-site loss, AdamW and row-lazy Adam, the training loop, snapshots with optimizer state, the instrumentation of ADR 6.3, and the modes ``registered``, ``calibration`` and ``rehearsal``. |

Where each asset lives (line numbers found by searching the file for the stated text):

| asset | file | line: matched text |
|---|---|---|
| W7 query construction (7-position window; query = normalize(W · window)) | studies/p9i/model.py | 105: `def window(`; 98: `WIDTH * core.WINDOW`; 141: `F.normalize(F.linear(features, self.wq)` |
| Key normalization (cosine keys) and query normalization (p9) | studies/p9/model.py | 361: `normalized = F.normalize(keys, dim=-1, eps=EPS)`; 318: `return F.normalize(F.linear(x, self.wq), dim=-1, eps=EPS).re` |
| Top-8 hard selection; soft candidate set of 64; temperature 0.2 (constants) | studies/p9/core.py | 71: `TOP, TEMPERATURE = 8, 0.2`; 75: `SOFT_TOP = 64` |
| Top-8 selection output (selected = first TOP of SOFT_TOP candidates) | studies/p9/model.py | 345: `selected=i[..., :TOP]`; 366: `stable_top(scores, SOFT_TOP)` |
| R1 oracle codes: identifier code and fixed unit code per identifier | studies/p9/model.py | 220: `def identifier_codes(`; 191: `def unit_code(`; 294: `def _oracle_codes(` |
| R1 code seed (P9 namespace) | studies/p9/core.py | 143: `"r1_codes": 170101` |
| R2 encoding of identifiers | studies/p9/data.py | 305: `def encode_identifiers(` |
| R2 lookup table identifier -> fact slot | studies/p9/data.py | 356: `def identifier_lut(` |
| R2 lookup used at selection (-1 where no slot) | studies/p9/model.py | 428: `slots = lut[identifier_codes(tokens)]` |
| R2 table of the first N facts (p9i) | studies/p9i/train.py | 114: `def fact_lut_for(` |
| Per-update training record: group names | studies/p9i/train.py | 83: `NORM_GROUPS = ` |
| Per-update record returned by Trainer.step (update, task_loss, answer_loss_256, grad_norm, param_change_norm, clip_total_norm) | studies/p9i/train.py | 489: `"task_loss": loss.detach().item()` |
| updates.jsonl writer | studies/p9i/train.py | 592: `log.write(json.dumps(record` |
| Snapshot-level diagnostics (margin quantiles, soft mass outside top-8, dead slots, keys entered top-64) | studies/p9i/train.py | 426: `def snapshot_diagnostics(`; 295: `"keys_entered_top64_after_0": diag` |
| snapshot.json writer | studies/p9i/train.py | 293: `"soft_mass_outside_top8": diag["soft_mass_outside_top8"]` |
| Snapshot marks (which updates are saved) | studies/p9i/train.py | 555: `def snapshot_marks(` |
| Calibration snapshot schedule | studies/p9i/core.py | 89: `CALIBRATION_SNAPSHOTS = (1024, 2048, 4096, 8192, 16384)` |
| Calibration stage marks | studies/p9i/stages.py | 614: `marks = DRY_CAL_SNAPSHOTS if args.dry else core.CALIBRATION_` |
| Registered train stage: no snapshots argument (single snapshot at U) | studies/p9i/stages.py | 566: `def work_train(`; 575: `job = build_job(args, cell, study, core.cell_dir(run_dir, ce` |
| Rehearsal snapshot (single, at its update count) | studies/p9i/stages.py | 701: `snapshots=(updates,), max_updates=updates, mode=REHEARSAL` |
| Registered and other seed constants (p9i) | studies/p9i/core.py | 94: `INIT_SEEDS = (1801, 1802)`; 95: `REGISTERED_DATA_SEED_BASE = 182001`; 96: `TEST_SEED_BASE = 900001`; 93: `CALIBRATION_INIT_SEEDS = (1791, 1792)` |
| Seed-set functions (p9i) | studies/p9i/core.py | 329: `def registered_seeds(`; 348: `def test_seeds(`; 361: `def rehearsal_draw_seeds(`; 369: `def calibration_seeds(`; 374: `def seed_namespaces(` |
| P9 data-seed names and base (namespace of the imported P9 code) | studies/p9/core.py | 131: `DATA_SEEDS: dict[str, int] = {`; 147: `NULL_SEEDS_A = (171331`; 149: `INIT_SEEDS = (1701, 1702)`; 151: `REHEARSAL_SEED_BASE = (`; 839: `REHEARSAL_STRIDE = 100` |
| Rehearsal seed set construction (base + stride * draw; null seeds base+20.., base+30..) | studies/p9/core.py | 842: `def rehearsal_seeds(` |
| Charged-time ledger class and cap constants (p9i) | studies/p9i/core.py | 114: `CAP_HOURS = 4.0`; 112: `RSS_WORKER_BYTES`; 116: `WORKERS = 6`; 682: `class Ledger`; 727: `def default_ledger(` |
| RSS constants (imported P9 job manager) | studies/p9/core.py | 156: `RSS_WORKER_BYTES = 3 * 1024**3`; 157: `RSS_AGGREGATE_BYTES = 24 * 1024**3` |

Registered seed values (computed by the clerk from the constants above; the data-seed names are the 14 keys of `DATA_SEEDS` in `studies/p9/core.py`):

| namespace | what | numeric range | note |
|---|---|---|---|
| registered (p9i) | data seeds, in DATA_SEEDS order | 182001-182014 | 14 names: facts, templates, clusters, training_order, calibration_stream, panel_a, panel_b, held_out, mixed_cluster, lane_d_a, lane_d_b, r1_codes, branch_hash, permutation_tests; r1_codes = 182012; facts = 182001 |
| registered (p9i) | null seeds A and B | 182015-182017 (A); 182018-182020 (B) | null_seeds_a, null_seeds_b |
| registered (p9i) | init seeds | 1801, 1802 | INIT_SEEDS (B101/O301; B102/O302 replicate uses the same init seeds) |
| calibration (p9i), draw 1 | data seeds | 179101-179114 | base 179001 + 100 * 1; r1_codes = 179112 |
| calibration (p9i), draw 1 | null seeds A / B | 179121-179123 / 179131-179133 | base + 20.. and base + 30.. |
| calibration (p9i), draw 1 | init seeds | 1791, 1792 | CALIBRATION_INIT_SEEDS |
| rehearsal (p9i), draws k in {0, 2..9} | data seeds per draw | base_k .. base_k + 13, base_k = 179001 + 100k | draw 1 refused outside calibration (REHEARSAL_MAX_DRAW = 9) |
| rehearsal (p9i), overall range | all rehearsal draws incl. nulls | 179001-179933 | k = 9: base 179901; last null 179933 |
| test (p9i unit tests), offsets 0..2 | data seeds per offset | 900001 + 100o .. + 13; nulls +20.. and +30.. | offset 0: data 900001-900014, nulls 900021-900023 and 900031-900033; overall 900001-900233 |
| P9 (ADR-0017 original, imported) | data seeds / nulls / init | 170001-170111 / 171331-171343 / 1701-1702 | p9 core; ADR-0017 registered seeds stay unused (ADR-0017 §18 I.7) |

Ledger and caps (values as coded): `CAP_HOURS = 4.0`, `CAP_SECONDS = 14400.0`, `WORKERS = 6`, per-worker RSS 3 GiB = 3,221,225,472 bytes, aggregate 24 GiB = 25,769,803,776 bytes (`studies/p9i/core.py` lines 112-116; `configs/p9i_interface.toml` `[resources]`). Ledger file: `<experiments>/P9I-ledger.json` (`core.default_ledger`, `studies/p9i/core.py` line 727), entries `{stage, run, seconds, utc}`. Stage caps for the registered run (ADR-0017 §15.5, lines 520-524): gates 600 s, train 3,600 s, evaluate 900 s, analyze 300 s, report 300 s.

Attempt-2 ledger (`results/p9i-run-attempt2-2026-11-15/ledger.json`): 12 entries; sum of `seconds` = 2690.9884089580155; `OUTCOME.md` line 3 states "Charged 2,691 s of the 14,400 s cap". Entries include the stages of attempt 2 and two entries labelled `P9IG-rehearsal-gates-draw2-20261115T003153Z` (generate 11.68841004098067 s, gates 6.12073791702278 s), which no document in the worktree describes (see NEEDS REVIEW N6).

### A5. ADR-0017 §18 (Part I) thresholds, class rules, measurements and "must not be claimed" items; §15.x approvals (quoted from the file)

Quoted exactly from `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` (line numbers are the file's):

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 703-705:
> L703: - Accuracy on primary panels A and B; H1/H2 and mixed-cluster panels secondary. **Every rule in §I.8 uses accuracy.** I_acc (Fano bound with the chance floor, §6.1), the Σ-renormalized log-loss gain (§6.1 secondary) and the 256-way loss are reported descriptively.
> L704: - **Interface efficiency** η = accuracy(arm) / accuracy(R1), same size, seed and panel.
> L705: - Query diagnostics: mean cosine between queries of different facts; share of facts whose nearest other query is closer than 0.9; for A4, A4E and BB, the attention weight on the five identifier positions.

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 707-707:
> L707: - No-memory baseline, exact retrieval, unseen-fact control with the LEAKAGE flag; gate G2 as §8.1. **"Chance" in every rule means inside the G2 interval.**

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 714-716:
> L714: - Allowed: controls; **R2 and R1** at the three sizes with the alphabet loss, snapshots at 1,024 / 2,048 / 4,096 / 8,192 / 16,384 updates. Initialization seeds 1791 and 1792 on parent B101/O301, and 1791 on B102/O302 (calibration only; never registered).
> L715: - **Rule:** U is the smallest of {2,048, 4,096, 8,192, 16,384} at which, at every size, R2 accuracy ≥ 0.95 **and R1 accuracy ≥ 0.90**. Each is the minimum over the two B101 calibration runs and both panels; the B102 run is reported.
> L716: - A size at which no U qualifies is `TASK_CEILING_FAIL` (R2) or `ORACLE_QUERY_FAIL` (R1) and is not run. U is then the smallest value qualifying at the remaining sizes.

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 744-766:
> L744: **Step 1 — raw class per B101 seed and panel, first match wins.**
> L745: 
> L746: \| Order \| Raw class \| Rule \|
> L747: \|---\|---\|---\|
> L748: \| 1 \| NOT_EVALUATED \| R1 accuracy below 0.5 at that size, in any B101 seed or panel (then every seed and panel of that size is NOT_EVALUATED) \|
> L749: \| 2 \| WORKS \| accuracy ≥ 0.5 and η ≥ 0.90; value permutation and disabling give chance \|
> L750: \| 3 \| PARTIAL \| accuracy above the G2 interval and ≥ 0.25, not row 2 \|
> L751: \| 4 \| FAILS \| otherwise \|
> L752: 
> L753: **Step 2 — class at the size, first match wins.**
> L754: 
> L755: \| Order \| Class \| Rule \|
> L756: \|---\|---\|---\|
> L757: \| 1 \| NOT_EVALUATED \| raw class NOT_EVALUATED (R1 below 0.5 at that size) \|
> L758: \| 2 \| NOT REPLICATED \| for at least one B101 seed, the raw classes on Panels A and B differ \|
> L759: \| 3 \| INTERMEDIATE \| not row 2, and the two B101 seeds give different raw classes \|
> L760: \| 4 \| INTERFACE_WORKS / INTERFACE_PARTIAL / INTERFACE_FAILS \| the common raw class of all four seed–panel pairs \|
> L761: 
> L762: Step 0 of §I.8.3 refers to the size: a size is NOT_EVALUATED when R1 is below 0.5 there, whatever an arm prints.
> L763: 
> L764: The B102 replicate is reported and must not have raw class FAILS on either panel for INTERFACE_WORKS to stand at 16,384; otherwise the class there is INTERMEDIATE.
> L765: 
> L766: For BB, after the B102 rule: a class INTERFACE_WORKS becomes **MODEL_STORES_FACTS** if BB-0's accuracy is above the G2 interval at that size on either B101 seed or panel. Reading fixed now: the trainable attention can by itself retrieve facts at that size, so BB's result cannot be attributed to the memory interface alone, even though BB's own ablations show that it uses its memory.

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 768-772:
> L768: #### I.8.2 Annotations (printed per size; they do not change a class)
> L769: 
> L770: - **Dense comparison**, for W7 against D7 and BB against BB-D, at each size where both run. Compared only if the arm's class is INTERFACE_WORKS or INTERFACE_PARTIAL; otherwise NOT COMPARED. With r = accuracy(arm) / accuracy(dense), paired by seed and panel, the smallest of the four values: **BEATS DENSE** if r ≥ 1.10; **DENSE SUFFICES** otherwise. BEATS DENSE is unreachable when the dense accuracy exceeds 1/1.10 ≈ 0.909; DENSE SUFFICES then means within 10% relative accuracy. Reading fixed now: DENSE SUFFICES means a dense adapter on the same input does as well within U updates at that size. It is a statement about this task and budget, not about the query interface or about memory in general. The auditor's toy predicts DENSE SUFFICES at 16,384 and probably not at 65,536; such a difference between sizes would be consistent with the sixteenfold difference in exposures per fact and is not evidence about capacity or the interface. A4 and A4E have no dense comparator (no dense arm reads the full prefix); their dense comparison is NOT COMPARED, and that is carried if A4 is selected.
> L771: - **Backbone contrast** at 16,384, for the pairs E7/W7 and A4E/A4. With r = accuracy(embedding arm) / accuracy(state arm), paired by B101 seed and panel (four values): **BACKBONE HURTS ADDRESSING** if all four r ≥ 1.03; else **BACKBONE ADDS NOTHING** if all four r ≥ 0.97; else **BACKBONE CONTRIBUTES** if all four r < 0.97; else **BACKBONE CONTRAST MIXED**. Not printed if both arms are INTERFACE_FAILS. BACKBONE HURTS is unreachable when the state arm exceeds 0.971.
> L772: - **Language modelling** (BB arms only): **LANGUAGE MODELLING DEGRADED** if the backbone's next-byte loss on its own corpus rows rises by more than 5% relative to before training, on either B101 seed. It does not block selection; it is carried with BB, and whether a degraded backbone is acceptable is the human lead's decision when ADR-0017 is revised.

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 774-782:
> L774: #### I.8.3 Selection rule for a revision of ADR-0017 (fixed now)
> L775: 
> L776: 0. If any of the three sizes is TASK_CEILING_FAIL, ORACLE_QUERY_FAIL or NOT_EVALUATED → **INCONCLUSIVE AT that size.** No interface is selected, the classes at the remaining sizes are reported, and the human lead decides. This is not step 4.
> L777: 1. If BB is INTERFACE_WORKS at all three sizes → BB: the model forms the query. A revision of ADR-0017 would then train the block-0 attention, and needs approval for that.
> L778: 2. Else if A4 is INTERFACE_WORKS at all three sizes → A4.
> L779: 3. Else if W7 is INTERFACE_WORKS at all three sizes → W7, with the limit that it is told the record length.
> L780: 4. Else → no tested interface reached INTERFACE_WORKS at all three sizes within U updates; the class of each arm at each size is reported; ADR-0017 stays blocked on this backbone.
> L781: 
> L782: The selected interface carries its scope statement (§I.2), its backbone-contrast annotation and its dense-comparison annotation into the revision of ADR-0017 and into every summary. If BB is selected, the before/after next-byte loss of BB, BB-D and BB-0 and the language-modelling annotation are carried with it. If A4 or W7 is selected, ADR-0017 would test a memory with its own input encoder, a different system from the P4–P8 memory addressed by the backbone's state.

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 790-795:
> L790: ### I.10 Resources (projection, not a measurement of this study)
> L791: 
> L792: - Measured in P9: R2 at 65,536 slots ran 32,768 updates in 386 s (0.012 s per update). That is the only measurement. With the auditor's assumed costs (0.05 / 0.02 / 0.015 s per update at 65,536 / 16,384 / 4,096 slots), the core matrix takes 2.4 hours serial at U = 8,192 and 4.8 hours serial at U = 16,384, or about 0.4 and 0.8 hours with six single-thread workers. Block BB backpropagates through block 0 at every position and is not estimated; the rehearsal measures it.
> L793: - Calibration (18 runs up to 16,384 updates): about 93 minutes serial, about 16 minutes with six workers, at assumed costs.
> L794: - **Caps (human decision, §15.3):** 3 GiB per worker and 24 GiB aggregate; **4 hours of charged execution for calibration, rehearsal and the run together, block BB included** (the lead's stricter reading of the decision; if the cap would be exceeded the work stops and returns to the human lead). The rehearsal measures time and memory only and fixes the stage caps.
> L795: 

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 812-820:
> L812: ### I.13 What must not be claimed
> L813: 
> L814: - Anything about capacity scaling, utilization, locality or incremental learning. None is tested. **A difference in class between sizes is not evidence about capacity:** exposures per fact differ sixteenfold.
> L815: - That a WORKS class for W7, E7, A4 or A4E shows the language model communicating what it needs (§I.2).
> L816: - That INTERFACE_WORKS for BB shows that a language model reliably communicates what it needs. BB retrains the block-0 attention on this task's answer loss alone, with its next-byte loss unprotected; it shows that a jointly trained backbone attention can form a query for this synthetic task within U updates.
> L817: - That an interface that works here would work on natural language. The task has fixed-length records and random identifiers.
> L818: - That W7 is a general interface: it is told the record length.
> L819: - That a failure of all interfaces is a failure of the ArborLM concept, or more than a statement about this backbone within U updates.
> L820: - That DENSE SUFFICES says memory is not needed in general.

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 486-489:
> L486: - **Arm BB is included.** Training the block-0 attention (4,224 parameters) is approved for block BB of Part I only. No other backbone parameter is trained anywhere.
> L487: - **Folded.** The prerequisite is Part I (§18) of this ADR, revision 4. `ADR-0018` is withdrawn as a separate ADR and its file points here.
> L488: - **Cap.** The answer names 4 hours and "calibration". The lead applies the stricter reading: 4 hours of charged execution for calibration, rehearsal and the run together, with BB included, 24 GiB aggregate. If that cannot hold, the work stops and the question returns to the human lead; the cap is not raised by the lead.
> L489: - **Decision 1 of Part I: approved** — implementation, calibration on rehearsal draw 1, rehearsal.

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 520-524:
> L520:   \| Stage \| Cap (s) \|
> L521:   \|---\|---\|
> L522:   \| gates \| 600 \|
> L523:   \| train \| 3,600 \|
> L524:   \| evaluate \| 900 \|

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 574-574:
> L574: > I accept this as a registered negative result. Preserve that classification, all original data, audits, deviations, and exploratory findings.

§13 (Lanes A-D, not Part I) "What must not be claimed" for reference, lines 406-415:

`docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` lines 406-415:
> L406: ## 13. What must not be claimed
> L407: 
> L408: - That slot entropy, distinct slots or the floored information sum show capacity.
> L409: - That R0a, R1, R2 or oracle-branch results are system results, or that the ladder gives upper bounds.
> L410: - That logical work is measured efficiency, or that simulation or the key-traffic identity is storage I/O.
> L411: - That cross-query locality found here would arise without planted structure; equal-frequency planted clusters are a best case, and within-query packing is not evidence about clusters.
> L412: - That the usage term revives dead slots, unless §6.2's revival count shows it.
> L413: - That Lane D shows continual learning in general, or teacher absorption.
> L414: - Anything about composition or reasoning.
> L415: - Any generalization across data draws, beyond 65,536 slots, or to a trainable backbone.

Registered run, per-cell training records (`experiments/P9IP-20261115T020303574595Z-674730f6b8a147c0a47cac404321f2df/cells/*/train.json`, in the main checkout, git-ignored; fields `peak_rss_bytes`, `wall_seconds`, `run_updates`). Clerk groups by slots and arm:

| slots | arm | cells | wall_seconds (min - max) | seconds per update (derived) | max peak_rss GiB |
|---|---|---|---|---|---|
| 4096 | A4 | 2 | 83.41206366597908 - 91.81456333299866 | 0.010182 - 0.011208 (DERIVED: wall / 8,192) | 0.334 |
| 4096 | BB | 2 | 89.25760945904767 - 92.19196670799283 | 0.010896 - 0.011254 (DERIVED: wall / 8,192) | 0.339 |
| 4096 | BB-0 | 2 | 36.81996179098496 - 37.40475725004217 | 0.004495 - 0.004566 (DERIVED: wall / 8,192) | 0.333 |
| 4096 | N | 2 | 67.72455308301141 - 81.91809541702969 | 0.008267 - 0.010000 (DERIVED: wall / 8,192) | 0.333 |
| 4096 | R1 | 2 | 73.7427565830294 - 76.57496912498027 | 0.009002 - 0.009348 (DERIVED: wall / 8,192) | 0.335 |
| 4096 | W7 | 2 | 80.17159474996151 - 80.25561354198726 | 0.009787 - 0.009797 (DERIVED: wall / 8,192) | 0.336 |
| 16384 | A4 | 3 | 124.94491366599686 - 159.4181198750157 | 0.015252 - 0.019460 (DERIVED: wall / 8,192) | 0.406 |
| 16384 | A4E | 2 | 125.23940741701517 - 132.03530074999435 | 0.015288 - 0.016118 (DERIVED: wall / 8,192) | 0.389 |
| 16384 | BB | 3 | 122.08305295795435 - 125.05719820800005 | 0.014903 - 0.015266 (DERIVED: wall / 8,192) | 0.377 |
| 16384 | BB-0 | 2 | 36.85462945798645 - 38.11788804200478 | 0.004499 - 0.004653 (DERIVED: wall / 8,192) | 0.335 |
| 16384 | BB-D | 2 | 130.04079908394488 - 130.9135998749989 | 0.015874 - 0.015981 (DERIVED: wall / 8,192) | 0.377 |
| 16384 | D | 2 | 115.02532745798817 - 115.11741770803928 | 0.014041 - 0.014052 (DERIVED: wall / 8,192) | 0.375 |
| 16384 | D7 | 3 | 76.99081629200373 - 84.89253658399684 | 0.009398 - 0.010363 (DERIVED: wall / 8,192) | 0.352 |
| 16384 | E7 | 2 | 121.8771780419629 - 121.8794293749961 | 0.014878 - 0.014878 (DERIVED: wall / 8,192) | 0.373 |
| 16384 | N | 2 | 108.41816595796263 - 108.65254741703393 | 0.013235 - 0.013263 (DERIVED: wall / 8,192) | 0.372 |
| 16384 | R1 | 3 | 105.86525674996665 - 110.56224004202522 | 0.012923 - 0.013496 (DERIVED: wall / 8,192) | 0.384 |
| 16384 | R2 | 2 | 50.295591457979754 - 50.33076166699175 | 0.006140 - 0.006144 (DERIVED: wall / 8,192) | 0.354 |
| 16384 | W7 | 3 | 112.40813116700156 - 115.64156000001822 | 0.013722 - 0.014116 (DERIVED: wall / 8,192) | 0.373 |
| 65536 | A4 | 2 | 489.4688525419915 - 507.4881364579778 | 0.059750 - 0.061949 (DERIVED: wall / 8,192) | 0.631 |
| 65536 | BB | 2 | 331.2759883340332 - 335.4286418330157 | 0.040439 - 0.040946 (DERIVED: wall / 8,192) | 0.488 |
| 65536 | BB-0 | 2 | 37.926978459057864 - 37.99937079101801 | 0.004630 - 0.004639 (DERIVED: wall / 8,192) | 0.333 |
| 65536 | BB-D | 2 | 386.5209424160421 - 390.63801079202676 | 0.047183 - 0.047685 (DERIVED: wall / 8,192) | 0.464 |
| 65536 | D7 | 2 | 226.0022034579888 - 228.71447116602212 | 0.027588 - 0.027919 (DERIVED: wall / 8,192) | 0.423 |
| 65536 | N | 2 | 319.6701495409943 - 320.538931875024 | 0.039022 - 0.039128 (DERIVED: wall / 8,192) | 0.489 |
| 65536 | R1 | 2 | 309.2830517910188 - 309.8832867090241 | 0.037754 - 0.037828 (DERIVED: wall / 8,192) | 0.504 |
| 65536 | W7 | 2 | 384.85175874998095 - 435.3720241669798 | 0.046979 - 0.053146 (DERIVED: wall / 8,192) | 0.493 |

## PART B: P10 inputs

### B0. P10 in the repository

No file defines "P10", "capacity scaling" as a study, or "two-teacher transfer" (searched all worktree text (outside .git and .venv); the word "capacity scaling" appears only as a not-authorized item in ADR-0013/0014/0015/0017 and in RESEARCH_HANDOFF §6 Phase 6). Items below cover what is recorded about capacity and transfer; none of it is a P10 specification.


### B6. Completed studies P1 to P9-I: ADR, question, registered outcome string, result files, stated limitation

Outcome strings are copied from the source named in the column. "Label" follows the source wording. Astra review is NOT_PERFORMED for all of them (for example `docs/RESEARCH_LOG.md` lines 44, 65, 75, 105, 126, 145, 153, 192-200, 208-209, 225, 251, 261, 267, 279-280).

| ADR | study / question | registered outcome string (source) | label | result files | stated limitation (quote, source) |
|---|---|---|---|---|---|
| ADR-0003 (E0) | Executable E0 specification: tiny CPU correctness and reproducibility gate | "G0 engineering gate accepted by the authorized reviewer" (`docs/RESEARCH_LOG.md` line 44) | registered result (engineering gate, per source) | results/e0-2026-11-12/ | `docs/RESEARCH_LOG.md` line 44: "No memory architecture has yet been tested." |
| ADR-0005 (P1) | Preregistered bounded RAM signal screen: does learned tree beat small dense? | "Promotion gate FAILED; do not scale this configuration under this protocol." (`docs/RESEARCH_LOG.md` line 65) | registered result | results/p1-2026-11-12/; results/p1-preflight-2026-11-12/ | `results/p1-2026-11-12/README.md` line 26: "Three seeds and a short fixed training budget do not establish statistical significance, novelty, general reasoning or a quality/compute frontier." |
| ADR-0006 | Frozen-checkpoint memory contribution diagnostic (zero training) | "Useful memory contribution was not reliably demonstrated across seeds at this budget." (`docs/RESEARCH_LOG.md` line 75) | exploratory diagnostic (source: "explicitly exploratory follow-up", `results/memory-diagnostic-2026-11-12/README.md` line 25) | results/memory-diagnostic-2026-11-12/ | `results/memory-diagnostic-2026-11-12/README.md` line 19: "...this diagnostic does not establish that mechanism." |
| ADR-0007 (P2) | Controlled initialization and batch-order follow-up of P1 | "P2 completed — memory effects below registered sensitivity" (`docs/RESEARCH_LOG.md` line 102) | registered result | results/p2-2026-11-12/ | `docs/RESEARCH_LOG.md` line 105: "a strong retained memory benefit was not established at this budget." |
| ADR-0008 (P3-LT) | Bounded longer training (1024 steps) of the 36 P2 checkpoints | "P3-LT completed — prediction improved; memory-dependence thresholds missed" (`docs/RESEARCH_LOG.md` line 123) | registered result | results/p3-lt-2026-11-12/ | `docs/RESEARCH_LOG.md` line 126: "the result neither settles the broad concept nor authorizes scaling." |
| ADR-0009 (P4) | Frozen nine-backbone capacity: does trainable hierarchical memory add capacity to a frozen backbone, compared with a dense adapter? | "P4 completed — memory adds capacity; the dense adapter leads" (`docs/RESEARCH_LOG.md` line 145) | registered result | results/p4-2026-11-12/ | `docs/RESEARCH_LOG.md` line 153: "P4 does not establish that freezing is better than joint training" |
| ADR-0010 (P5) | Flat vs fixed-tree vs learned-tree memory ablation on the nine P4 parents | usefulness passed for all three; "R failed" (learned-routing contrast); composite criterion remains FAILED (`docs/RESEARCH_LOG.md` lines 192, 200) | registered result | results/p5-2026-11-13/ | `results/p5-2026-11-13/README.md` line 74: "This study does not establish novelty, a general architectural impossibility, storage scalability, physical I/O savings, learned topology, or a reason to skip further scientific review." |
| ADR-0011 (P6-E, P6-Q) | Inference-only retrieval optimization (P6-E) and routing fidelity (P6-Q) on the frozen P5 checkpoints | P6-E: "timing criteria SP, PAR and PR are INCONCLUSIVE for both tree kinds" (`docs/RESEARCH_LOG.md` line 208); P6-Q: "all four flags FAIL for both tree kinds" (line 209) | registered result | results/p6-e-2026-11-13/; results/p6-q-2026-11-13/ | `docs/RESEARCH_LOG.md` line 208: "No efficiency claim follows." |
| ADR-0013 (P7-A) | Storage-page locality of the existing P5 memories (trace-driven simulation) | "CONCENTRATION-ONLY for both tree kinds." (`docs/RESEARCH_LOG.md` line 225) | registered result (simulation) | results/p7a-2026-11-13/ | `docs/reviews/p7a-results-2026-11-13/README.md` line 69: "The primary setting uses a hypothetical row size. At the memory's true row size the question is degenerate." |
| ADR-0014 (P7-B) | Co-access layout equivalence: is hierarchy-specific locality beyond flat co-access placement? | "WITHIN 10% OF FLAT CO-ACCESS, REPLICATED on both streams, for both tree kinds. The hierarchy-specific locality hypothesis failed." (`docs/RESEARCH_LOG.md` line 251) | registered result (simulation) | results/p7b-2026-11-13/ | `docs/reviews/p7b-results-2026-11-13/README.md` line 7: "This is a simulation of value-page cache misses on traces. No storage device was used." |
| ADR-0015 (P8) | Locality-aware memory training, bounded ten-case pilot | "Study status: INCOMPLETE (55 of 60 cells simulated). No case is LOCALITY-POSITIVE." (`results/p8-2026-11-14/SUMMARY.md` line 3); registered decision-map output "none" (line 24) | registered result (INCOMPLETE) | results/p8-2026-11-14/ | `results/p8-2026-11-14/SUMMARY.md` line 3: "All page numbers are simulated value-page cache misses at hypothetical row sizes, not physical I/O." |
| ADR-0016 (P8 supplement) | Simulate the five collapsed P8 cells (human-approved exception to ADR-0015 §11) | source label: "SUPPLEMENTARY (ADR-0016) — not the registered P8 output"; "5 of 5 cells completed" (`results/p8-supplement-2026-11-14/README.md` line 10); registered P8 stays INCOMPLETE, decision none (ADR-0016 line 3) | registered result (supplementary, per source) | results/p8-supplement-2026-11-14/ | `docs/RESEARCH_LOG.md` line 267: "the supplement tested nothing new." |
| ADR-0017 §12, §15.2 (P9 testbed calibration, old design) | Testbed calibration on rehearsal seeds before the registered design | source: "rehearsal seeds only, not a study result" (`results/p9-calibration-2026-11-14/README.md` line 1); registered rule gives "task_ceiling_fail = [4096]" (line 24) | calibration/rehearsal | results/p9-calibration-2026-11-14/ | ADR-0017 §15.2 (line 469): "classify ADR-0017 as calibration blocked, not scientifically failed." |
| ADR-0017 §18 (P9-I, Part I) | Query interface prerequisite: can the model (or a memory-side encoder) form a query that retrieves facts? | "COMPLETE — NO_INTERFACE_SELECTED" (`results/p9i-run-attempt2-2026-11-15/OUTCOME.md` lines 3-4; accepted at ADR-0017 §15.9 line 576) | registered result (negative; accepted by the human lead) | results/p9i-calibration-2026-11-14/; results/p9i-rehearsal-2026-11-14/; results/p9i-run-attempt1-2026-11-14/ (stopped at gates); results/p9i-run-attempt2-2026-11-15/ | `results/p9i-run-attempt2-2026-11-15/OUTCOME.md` line 40: "May not: anything about capacity, utilization or locality; a failure of the ArborLM concept; ..." |
| ADR-0001, 0002, 0004, 0012, 0018 | Not studies: direction; phase-0 plan; data-selection approval; governance amendment (PROPOSAL, not approved: ADR-0012 line 4); ADR-0018 WITHDRAWN as a separate ADR (line 3) | n/a | n/a | docs/decisions/ | n/a |

Dates: P1 2026-11-12; P2 2026-11-12/13; P3-LT 2026-11-12/13; P4 2026-11-13; P5 2026-11-13; P6 2026-11-13; P7-A and P7-B 2026-11-13; P8 and P8 supplement 2026-11-14; P9 calibration 2026-11-14; P9-I attempt 2 2026-11-15 (`docs/RESEARCH_LOG.md`).

### B7. Everything recorded about capacity, scale, locality, active work and page misses

Capacity and scale (labels per source):

| quantity | value(s) as recorded | file and line | label |
|---|---|---|---|
| Memory slots | 4,096 (flat and trees, P1, P4, P5, P8) | `configs/p1_ram_screen.toml` [model] `slots = 4096`; `docs/decisions/ADR-0010-hierarchical-memory-ablation.md` line 54 ("4,096 independent key rows"); `configs/p8_locality_training.toml` `slots = 4096` | registered result (config and spec) |
| Memory slots | 768 KiB memory at 4,096 slots | `docs/reviews/p7a-results-2026-11-13/README.md` line 70 ("One memory size (4,096 slots, 768 KiB)") | registered result (simulation input) |
| Memory slots (P9-I) | 4,096 / 16,384 / 65,536 | `configs/p9i_interface.toml` `[memory] slots`; `results/p9i-run-attempt2-2026-11-15/cells.csv` | registered result |
| Facts (P9-I) | 2,048 / 8,192 / 32,768 (facts = slots / 2) | `configs/p9i_interface.toml` `[memory] facts`; `results/p9i-run-attempt2-2026-11-15/cells.csv` column `facts` | registered result |
| Backbone parameters | 27,392 unique (P1 to P9-I frozen or trained backbone, two blocks, width 32, 4 heads, vocabulary 256, context 64) | `docs/decisions/ADR-0005-ram-pilot-spec.md` line 27; `docs/decisions/ADR-0010-hierarchical-memory-ablation.md` line 52; `configs/p4_frozen_capacity.toml` `[model] backbone_parameters = 27392`; `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` line 632 ("On the frozen 27,392-parameter backbones") | registered result (config) |
| Backbone parameters (E0 smoke model) | 18,688 (vocabulary 16, 32 positions) | `docs/decisions/ADR-0003-e0-approved-spec.md` line 35; `configs/e0_cpu_smoke.toml` `parameters = 18688` | registered result (engineering gate) |
| Memory addition parameters | flat 198,145; learned tree 198,145 + 256 trainable router scalars = 198,401 (P4 trained addition); fixed tree stores the same 256 as a buffer | `docs/decisions/ADR-0010-hierarchical-memory-ablation.md` line 71 ("= 198145"; "adds 256 trainable scalars") and table lines 65-67; `docs/RESEARCH_LOG.md` line 147 (P4 trained addition 198,401 via `results/p4-2026-11-12/README.md` line 12) | registered result (spec and records) |
| Trainable parameters, P9-I cells | N 16,384: 787,969 total stored 815,361; BB arms +4,224 backbone parameters | A1 table (cells.csv `trainable_parameters`, `stored_parameters`, `trainable_backbone_parameters`); `results/p9i-run-attempt2-2026-11-15/RESULTS.md` lines 42-70 | registered result |
| Exposures per fact (P9-I, U = 8,192) | 512 / 128 / 32 at 2,048 / 8,192 / 32,768 facts (analytical; sixteenfold difference) | `results/p9i-run-attempt2-2026-11-15/RESULTS.md` (column "exposures per fact (analytical)"); `results/p9i-calibration-2026-11-14/README.md` line 28; `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` line 698 ("sixteenfold: 256 / 64 / 16 at U = 4,096") | registered result |
| Updates (P4, P5) | P4: 27,648 updates (9 baselines + 54 trained additions); P5: 55,296 updates, 28,311,552 new targets | `docs/RESEARCH_LOG.md` lines 147 and 191 | registered result |
| Optimizer state bytes (P9-I) | N 16,384 6,303,772 (cells.csv `optimizer_state_bytes` 6303772 on the N cell row); R2 16,384 4,202,516; BB 16,384 6,337,580; BB-0 33,808 (4,224 params) | A1 table; `results/p9i-run-attempt2-2026-11-15/cells.csv` column `optimizer_state_bytes` | registered result (measured counts, bytes) |
| Optimizer state bytes (P1 to P8) | NOT FOUND | searched the P1, P4, P5 and P8 readmes and summaries | n/a |
| Memory-gain capacity measure (P4) | mean capacity gain C = 0.021988695 nats/byte; positive in all 27 memory runs | `docs/RESEARCH_LOG.md` line 148 | registered result |
| Memory-gain capacity measure (P5) | gains 0.022938682 flat, 0.022133329 fixed, 0.021549867 learned; positive in 27/27 cells | `docs/RESEARCH_LOG.md` line 192 | registered result |
| P9 testbed readout at 65,536 slots | R2 ran 32,768 updates in 386 s (0.012 s per update) — the only P9 measurement of cost | `docs/decisions/ADR-0017-parallel-capacity-and-locality-diagnostics.md` line 792 ("Measured in P9") | calibration/rehearsal (P9 testbed; source wording "Measured in P9") |
| P9 testbed readout at 4,096 slots, E = 128 | R2 accuracy 0.723 (4,096 slots / 2,048 facts), 0.971 (16,384 / 8,192), 0.970 (65,536 / 32,768) | `results/p9-calibration-2026-11-14/README.md` line 17 | calibration/rehearsal ("not a study result", line 1) |
| P9-I rehearsal cost | about 0.04 s per update and 1.49 GiB at the largest size (six workers); the 65,536 cell evaluation 20-27 s | `results/p9i-rehearsal-2026-11-14/README.md` lines 8-12; `docs/RESEARCH_LOG.md` line 276 | calibration/rehearsal |

Locality, active work and page misses (labels per source):

| study | measurement as recorded | file and line | label |
|---|---|---|---|
| P5 (ADR-0010) | observed score-work W = 0.12890625 x flat for both trees; primary addition latency ratios 2.603052 (fixed) and 2.598485 (learned) against flat; all L criteria failed | `docs/RESEARCH_LOG.md` line 192 | registered result (in-RAM CPU timing; "logical work" not "measured efficiency") |
| P5 critical review | trees took about 4.6 x flat training time (recorded, not reported in P5); CPU operator profile attributes slowness to key gather, topk, batched product and re-normalization | `docs/RESEARCH_LOG.md` line 200 | exploratory diagnostic (`docs/reviews/p5-claude-review-2026-11-13/`) |
| P6-E (ADR-0011) | timing criteria INCONCLUSIVE; 26.5% of confirmation timing records failed the stability rule; point estimates about 0.29 x original tree and 0.73-0.75 x flat at 512 queries per call | `docs/RESEARCH_LOG.md` line 208 | registered result (INCONCLUSIVE) |
| P6-Q (ADR-0011) | top-2 routing recalls 0.79 (fixed) and 0.91 (learned) of exhaustive selection; removing the prior hurt in all 54 checkpoints by about 0.0039 nats/byte | `docs/RESEARCH_LOG.md` line 209 | registered result (all four flags FAIL) |
| P7-A (ADR-0013) | warm capacity misses per query (primary): 3.164 flat, 2.100 fixed, 1.650 learned; trees read 34% (fixed) and 48% (learned) fewer cached value pages; effective slot count explains 96.6% of variance in cached misses | `docs/reviews/p7a-results-2026-11-13/README.md` line 31 (column order Flat \| Fixed \| Learned) and line 36; `docs/RESEARCH_LOG.md` line 225 | registered result (simulation of page misses, hypothetical row size) |
| P7-A null | count-preserving null reproduces the whole gap: "It reproduces 98% of the flat-minus-fixed gap and 103% of the flat-minus-learned gap."; effective slot count alone accounts for 96.6% of the variance in cached misses | `docs/reviews/p7a-results-2026-11-13/README.md` line 29 | registered result (simulation) |
| P7-B (ADR-0014) | co-access clustering cuts flat misses by 25% and 41%; branch-constrained co-access cuts trees' misses by 20-22% and 29-34%; primary incremental-locality ratio tree/flat 0.994-1.027 | `docs/RESEARCH_LOG.md` line 251; `docs/reviews/p7b-results-2026-11-13/README.md` lines 28 and 47 | registered result (simulation) |
| P8 (ADR-0015) | every locality term reduced slots in use by 46-92%; simulated misses fell as the working set shrank; count-preserving null fell with them; five of twelve C04/C05 cells select the same eight slots on every one of 32,768 queries | `docs/RESEARCH_LOG.md` line 261; `results/p8-2026-11-14/SUMMARY.md` lines 61 and 67 (N_eff 84-103 for trees vs 127 for flat) | registered result (INCOMPLETE; simulation) |
| P8 supplement (ADR-0016) | five collapsed cells: zero counted misses, null equal to the actual stream | `results/p8-supplement-2026-11-14/README.md` line 10; `docs/RESEARCH_LOG.md` line 267 | registered result (supplementary) |
| P9-I active work and locality | NOT MEASURED: ADR-0017 §I.13 (line 814) "Anything about capacity scaling, utilization, locality or incremental learning. None is tested."; BB at 16,384 uses 8 distinct selected slots (eval key `panels/A/distinct_selected_slots` = 8, cells.csv), disabling the memory changes nothing (OUTCOME.md line 27) | ADR-0017 line 814; `results/p9i-run-attempt2-2026-11-15/OUTCOME.md` line 27 | registered result (negative, not a locality measurement) |
| P9 review: address collapse | query cosine 0.95-1.00 in learned-query arms; 1-6 distinct top-1 slots | `results/p9i-run-attempt2-2026-11-15/OUTCOME.md` line 32; `docs/reviews/p9i-results-2026-11-15/REVIEW.md` lines 50-63 | exploratory diagnostic |

Stated limits on these measurements: `docs/RESEARCH_HANDOFF.md` lines 259-260 (metrics) and 275 (I/O gate); `docs/reviews/p7b-results-2026-11-13/README.md` line 7 ("No storage device was used. Nothing here is a measurement of I/O, latency, throughput or hardware speed.").

### B8. What RESEARCH_HANDOFF.md and AGENTS.md say (exact lines)

Quoted with line numbers from the files. Where the requested rule is not in the file, that is stated.

**Joint training of backbone and memory:**

`docs/RESEARCH_HANDOFF.md` lines 93-93:
> L93: 1. **Small causal transformer backbone:** handles token context, attention, composition, and the computations memory lookup cannot replace. First tests use a train-from-scratch small model, not a huge existing checkpoint.

`docs/RESEARCH_HANDOFF.md` lines 242-243:
> L242: - Train backbone + hierarchical memory jointly from scratch once earlier gates pass.
> L243: - Consider external compute if needed, but do not deploy or spend substantial money without explicit approval.

`docs/RESEARCH_HANDOFF.md` lines 297-297:
> L297: 5. **Fresh native model:** train backbone and memory jointly under a new version; use benchmark continuity, not direct weight compatibility, as the migration contract.

`docs/RESEARCH_HANDOFF.md` lines 244-244:
> L244: - Scale total learned memory while keeping *active* parameters and I/O as controlled metrics.

**Teachers and distillation:**

`docs/RESEARCH_HANDOFF.md` lines 145-145:
> L145: `L_total = L_language + λ L_router + β L_io_proxy + γ L_load_balance [+ δ L_distillation]`

`docs/RESEARCH_HANDOFF.md` lines 232-237:
> L232: ### Phase 5 — migrate an existing teacher model (optional research branch)
> L233: 
> L234: - Use a legally compatible open-weight pretrained teacher (candidate: small Qwen model; **verify exact checkpoint and license before choosing**).
> L235: - Begin **additive**: freeze teacher backbone, learn memory projections and values with language-model + teacher-logit distillation; then optionally unfreeze adapters.
> L236: - Compare to teacher, same-size student without memory, flat-memory student, and additive HNM student. Record distillation compute and data cost.
> L237: - Only attempt partial FFN replacement after quality survives. It is **not** a direct file-format conversion of arbitrary teacher weights.

`docs/RESEARCH_HANDOFF.md` lines 295-295:
> L295: 3. **New backbone, same hidden dimension:** test adapter alignment; do **not** assume old memory is semantically compatible; re-distill and evaluate.

**SSD and storage claims:**

`docs/RESEARCH_HANDOFF.md` lines 71-71:
> L71: **H4 — SSD viability:** After porting the learned values to NVMe, the savings in transferred bytes outweigh routing, indexing, page fetching and decompression overhead under at least one controlled workload with total memory exceeding available RAM.

`docs/RESEARCH_HANDOFF.md` lines 99-99:
> L99: 7. **Storage policy (later):** indexes and frequently accessed values in RAM; cold values in block-aligned NVMe segments; cache/prefetch routines; immutable/versioned memory snapshots for reproducibility.

`docs/RESEARCH_HANDOFF.md` lines 205-205:
> L205: - Keep memory in RAM to remove NVMe system noise and isolate the model-learning question.

`docs/RESEARCH_HANDOFF.md` lines 216-218:
> L216: ### Phase 3 — SSD-backed inference without changing weights
> L217: 
> L218: - Freeze a trained checkpoint and memory index; store memory values in block-aligned immutable NVMe segments with versioned metadata.

`docs/RESEARCH_HANDOFF.md` lines 223-223:
> L223: - Deliverables: read traces, SSD-vs-RAM curves, hardware fingerprint, correctness parity tests.

`docs/RESEARCH_HANDOFF.md` lines 275-275:
> L275: - **I/O gate:** SSD implementation demonstrates a real measured byte or latency benefit at matched quality, not just synthetic bandwidth projection.

`AGENTS.md` lines 24-24:
> L24: - Keep model-learning questions separate from SSD I/O questions: first RAM only, then same checkpoint with different storage policies.

**Downloads and external spend:**

`docs/RESEARCH_HANDOFF.md` lines 405-405:
> L405: - Do not fetch large datasets or launch expensive cloud compute without explicit approval.

`docs/RESEARCH_HANDOFF.md` lines 243-243:
> L243: - Consider external compute if needed, but do not deploy or spend substantial money without explicit approval.

`AGENTS.md` lines 15-15:
> L15: 2. After Astra approves, implement the smallest useful change with tests. Do not run costly external services or download large training data without approval.

`CLAUDE.md` lines 17-17:
> L17: - No implementation or execution of a new study before its specification has a recorded human approval. No training, SSD work, downloads, paid services, merges, pushes of weights or publication without explicit human approval.

**Dependencies (`uv.lock` and `pyproject.toml`):**

`docs/RESEARCH_HANDOFF.md` lines 194-194:
> L194: - Pin Python, PyTorch and dependencies; deterministic seeding; one tiny text or synthetic dataset; uniform tokenizer; unit tests.

`docs/RESEARCH_HANDOFF.md` lines 355-355:
> L355: 2. Create `pyproject.toml`, a small `src/arborlm/` package, tests, and deterministic train/eval scripts. Prefer PyTorch + standard Python, no premature Rust or custom SSD kernel.

`AGENTS.md` contains no `uv.lock` or `pyproject.toml` rule (`grep -n "uv.lock\|pyproject" AGENTS.md` returns nothing). The rule is in CLAUDE.md, not in the two requested files:

`CLAUDE.md` lines 34-34:
> L34: Local binaries live in `experiments/` and the corpus in `data/` (both git-ignored). `uv.lock` and `pyproject.toml` do not change without an approved amendment; use `uv run --locked --with <pkg>==<version>` for analysis-only tools such as plotting.

**Astra label:**

`AGENTS.md` lines 7-8:
> L7: - **Astra is responsible for research reasoning, hypothesis/architecture decisions, experiment design, orchestration, interpretation, and final scientific validation.** The actual model must be selected by the user/operator where available.
> L8: - A **lower-tier coding model** should perform implementation, tests, scripts, CI, refactors and routine formatting strictly according to an Astra-reviewed specification. It may solve local code tasks, but must not invent or silently change scientific assumptions or report its own work as Astra-validated.

`AGENTS.md` lines 17-17:
> L17: 4. Submit code and results for **independent Astra scientific validation**; mark `ASTRA VALIDATED` only with evidence of a real review.

`docs/RESEARCH_HANDOFF.md` lines 305-305:
> L305: **This is a workflow policy, not a capability claim.** Repository files and prompts cannot forcibly select Astra or dynamically switch the Codex model. The operator must choose the actual model in the product/environment where available. If Astra is not available in a particular environment, leave a pending **Astra-review checkpoint**; a lower-tier coding agent must not claim that review occurred.

`docs/RESEARCH_HANDOFF.md` lines 312-312:
> L312: 4. **Astra — VALIDATE:** independently review diffs, math, data splits, loss functions, gradients, benchmark fairness, reproducibility, results and claims. Re-run or request verification for suspicious metrics. Mark `ASTRA VALIDATED` only if an Astra session demonstrably performed that review, with a link/record.

`docs/RESEARCH_HANDOFF.md` lines 330-330:
> L330: `STATUS: PROPOSAL`, `STATUS: SPEC-APPROVED`, `STATUS: IMPLEMENTED-UNREVIEWED`, `STATUS: ASTRA-VALIDATED`, `STATUS: HUMAN-APPROVED`, `STATUS: REJECTED`, `STATUS: SUPERSEDED`.

`CLAUDE.md` lines 19-19:
> L19: - `Astra review: NOT_PERFORMED` is historically true. Claude review is not Astra review.

**Scope and model-learning vs SSD, general rules:**

`AGENTS.md` lines 22-23:
> L22: - Small, portable Python/PyTorch prototype first; **no infrastructure deployment** and no premature distributed framework/Rust backend.
> L23: - Preserve strong baselines: same dataset/tokenizer and fair training/inference budgets for dense, flat memory, fixed tree and learned hierarchy.

`AGENTS.md` lines 25-25:
> L25: - Do not confuse *stored parameters* with *active parameters* or *reasoning quality*; report them separately.

`AGENTS.md` lines 27-27:
> L27: - Run relevant tests before describing work as complete; if tests weren't run, explicitly state so.

**Phase order (handoff):**

`docs/RESEARCH_HANDOFF.md` lines 190-190:
> L190: The scientific path must move from cheapest falsification to costly scale. **Do not start with a 700B model, multi-GPU cloud cluster, Rust engine or production service.**

`docs/RESEARCH_HANDOFF.md` lines 205-205:
> L205: - Keep memory in RAM to remove NVMe system noise and isolate the model-learning question.

### B9. Environment facts (commands as allowed; nothing opened except small records)

Commands and outputs (recorded at inventory time):

| item | recorded value | source or command |
|---|---|---|
| Python | 3.12.14 (`uv run --locked python -c` output) | pyproject.toml line 9: `requires-python = "==3.12.*"`; uv.lock header `requires-python = "==3.12.*"` |
| torch | 2.8.0 installed (`uv pip list --python .venv/bin/python`); uv.lock entry `torch` 2.8.0+cpu | pyproject.toml line 11: `dependencies = ["torch==2.8.0", "psutil==7.0.0"]` |
| MPS (Apple GPU backend) | torch.backends.mps.is_available() = True; is_built() = True | output of `uv run --locked python -c "import torch; ..."` |
| torch default threads in that process | 6 | same output (`torch.get_num_threads()`) |
| transformers | NO (not in uv pip list; not in uv.lock) | uv pip list output; uv.lock |
| tokenizers | NO | same |
| safetensors | NO | same |
| numpy | NO (torch prints "Failed to initialize NumPy: No module named 'numpy'") | same; `outputs/d5_gradient_check.txt` line 1 |
| datasets | NO | same |
| sentencepiece | NO | same |
| mlx | NO | same |
| pyarrow (optional pilot extra) | YES, 21.0.0 | pyproject.toml line 14: `pilot = ["pyarrow==21.0.0"]` |
| CPU | Apple M5 Max; hw.ncpu = 18 | `sysctl -n hw.memsize hw.ncpu machdep.cpu.brand_string` |
| RAM | hw.memsize = 51539607552 bytes (48 GiB) | same command |
| Free disk | /Users/daniellaloush: Size 1.8Ti, Used 1.7Ti, Avail 103Gi, Capacity 95% (/System/Volumes/Data) | `df -h /Users/daniellaloush` |
| Hugging Face cache | NOT FOUND (`~/.cache/huggingface` does not exist) | `ls ~/.cache/huggingface` |

Pretrained model weights present locally (names and sizes only; no weight file was opened):

| location | size | what is there (names and sizes only) |
|---|---|---|
| ~/.ollama/models/blobs (Ollama model store) |  96G | 11 manifest files: hf.co/OBLITERATUS/Qwen3.8-27B-OBLITERATED/Q4_K_M; registry.ollama.ai/huihui_ai/qwen3.5-abliterated/9b; registry.ollama.ai/library/qwen-obl/latest; registry.ollama.ai/library/qwen2.5/3b-instruct; registry.ollama.ai/library/qwen2.5/7b-instruct; registry.ollama.ai/library/qwen2.5vl/7b; registry.ollama.ai/library/qwen3.5/9b; registry.ollama.ai/library/qwen3.6/35b-a3b; registry.ollama.ai/library/qwen3.8/27b; registry.ollama.ai/library/qwen3.8/27b-dev; registry.ollama.ai/library/qwen3.8/27b-mlx |
| ~/.cache/uv (uv package cache; not inspected for weights) | 9.7G | directory size only |
| ~/Downloads (personal files; contents not listed) |  35G | no file with extension .safetensors, .gguf, .bin, .pt, .pth, .onnx, .mlpackage, .npz or .ckpt at depth <= 3 |

Main checkout `experiments/` (git-ignored; top-level names and sizes, `du -sk`):

| entry | size |
|---|---|
| E0-20261113T021519633244Z-7cb9a2c706074a459efb8b82107696f5 | 3.7 MiB |
| E0-20261113T021737609016Z-f9af346e45f94803973c1a4e681d233a | 3.9 MiB |
| E0-20261113T021751395579Z-022ace6673384498a39ce74f2ddea257 | 3.9 MiB |
| E0-20261113T023000474943Z-68c623a86fc34e199f863b21904a56de | 4.6 MiB |
| E0-20261113T023057321599Z-db358750bd8144bf98db0a06d9244db7 | 4.7 MiB |
| E0-20261113T023150557313Z-f15c15bf02b840da9638fc7f34c60d4d | 4.7 MiB |
| E0-20261113T025937174570Z-38e182f980da40abbccb0efad9edfa6b | 5.2 MiB |
| E0-20261113T030013937138Z-0178955490dc4cf4b3ee7e9e0aebed9d | 5.2 MiB |
| E0-20261113T033146241027Z-5fdc210cb927450a8ce42b65e9d96ec5 | 5.9 MiB |
| E0-20261113T033317763832Z-d3235d1651914531a2d568df747b9552 | 5.9 MiB |
| E0-20261113T042831282007Z-2fc48517d9ab4ac696fe30aa5264a3de | 6.7 MiB |
| E0-20261113T042925468139Z-b37a34341068462b8781b945ead74079 | 6.7 MiB |
| E0-20261113T043021992435Z-b82abb95271c43f79f5fa9871bec417b | 6.7 MiB |
| E0-20261113T044851909363Z-1a7aa64e65bd4d91a2544ad34c6a2664 | 6.9 MiB |
| E0-20261113T124019386667Z-dd95f779549449dc8a1c1ea7d5723ac5 | 8.0 MiB |
| E0-20261113T124435147087Z-c639d979f77240718281e53bab42d482 | 8.1 MiB |
| E0-20261113T124524395330Z-83849e36dff2465499a30b8bead714d7 | 8.1 MiB |
| P1-20261113T023302942989Z-acbad32bf88f40b3b60e1993e042d5d8 | 88.4 MiB |
| P1DIAG-20261113T024308074540Z-ace5d3680604461a8f1e9bea48f466f0 | 6.8 MiB |
| P2-20261113T030106857200Z-d08b874d11e74a7391b15f762e40f0c7 | 191.9 MiB |
| P3LT-20261113T033545902673Z-befd369dda744953a2ed6fc3a8108d1d | 292.7 MiB |
| P4CAP-20261113T043320081674Z-d109080245df457da81e95c6b7300ccd | 379.0 MiB |
| P5HIER-20261113T125206040109Z-8a40c493791641028f8eb8dfa26f71be | 837.3 MiB |
| P6EANA-20261113T180400246467Z-b0ad0be91c75450eb482ef6cf8b3ab59 | 2.6 MiB |
| P6ECON-20261113T175807956983Z-2f66ed206eb24230b888583ae892bd39 | 8.5 MiB |
| P6EEQ-20261113T173700724372Z-c3d45d6d7fa140bea302c4aaf44fc95f | 6.1 MiB |
| P6ESCR-20261113T174408566062Z-28df28f7b3b3436492d2d8379b217a2d | 17.2 MiB |
| P6Q-20261113T180439281981Z-fdc287dd79274cfd962ab29fbffd1087 | 1700.0 MiB |
| P7AA-20261113T215004286617Z-1d1e2c7e136e466f9e423f94d58d602a | 7.1 MiB |
| P7AS-20261113T213357135402Z-af93d829f722456e95f394462eedc57b | 14.3 MiB |
| P7AT-20261113T213133591303Z-0605157511b24311919ddfab8ac89b2e | 94.0 MiB |
| P7BA-20261114T024054852573Z-72ade53e0ef74ddf893e0d30f8cd3044 | 18.6 MiB |
| P7BL-20261114T013707250613Z-31637f68420b415ebc73f333bb21993b | 70.2 MiB |
| P7BP-20261114T013656010347Z-9433b10446e5458885b6cb83f8d1a915 | 14.6 MiB |
| P7BSA-20261114T015358875869Z-b5028326a722484bbbb49ec1c8518d57 | 42.2 MiB |
| P7BSB-20261114T021416466847Z-5a15dae8e51147ce9a888613aced4527 | 42.2 MiB |
| P7BT-20261114T015044654616Z-c8ecc1e86e434a6b9ec1b76f6b5f23ae | 59.8 MiB |
| P8A-20261114T044147896561Z-4a9976ed3c7d493c8a92293786f2572c | 1.0 MiB |
| P8E-20261114T043753008527Z-ab07648862054617b63d9e4d83e5407f | 97.6 MiB |
| P8PANEL-cache | 0.3 MiB |
| P8S-20261114T043952694180Z-088e6814edcd465894aebd125d53ddc3 | 9.6 MiB |
| P8SUP-20261114T144104227089Z-fbfb3d18513749b081f9cdd93f22ad81 | 0.8 MiB |
| P8T-20261114T043005466913Z-5da1f4d298534e9390b007efd8d98156 | 359.4 MiB |
| P8TI-20261114T034510617868Z-79bf1c3a2c8547d7bcc2f946c9f7ce6c | 2.4 MiB |
| P8TI-20261114T035952913866Z-c5d5b77c9e2c4cdda7355824df21fe56 | 2.4 MiB |
| P9C-20261114T182513034263Z-a529fd1946ff4e52b19980bd6d3b6fcd | 415.3 MiB |
| P9I-ledger.json | 0.0 MiB |
| P9IC-20261114T225847947431Z-b0cf703a0d7c4f7ab8f308c3de6ddf78 | 1396.6 MiB |
| P9IG-rehearsal-gates-draw2-20261115T003153Z | 5.1 MiB |
| P9IH-20261114T231255388625Z-8c6758d15894479b840ff5b5afd93630 | 793.5 MiB |
| P9IP-20261114T235955649302Z-8756ef5f9d1541bd9e0efaece6f7c27b | 5.2 MiB |
| P9IP-20261115T020303574595Z-674730f6b8a147c0a47cac404321f2df | 1067.0 MiB |
| ci | 55.6 MiB |
| review | 33.5 MiB |

Main checkout `data/` (git-ignored; top level):

| entry | size |
|---|---|
| wikitext2 | 6.72 MiB |

- `data/wikitext2/train-00000-of-00001.parquet`: 6357543 bytes (ADR-0004 expected: 6,357,543 bytes).
- `data/wikitext2/validation-00000-of-00001.parquet`: 657209 bytes (ADR-0004 expected: 657,209 bytes).

Training corpus for the backbone (files and sizes):

- Corpus: WikiText-2, `wikitext-2-raw-v1`, Salesforce/WikiText, pinned revision `b08601e04326c79dfdd32d625aee71d232d685c3`; expected total payload 7,747,362 bytes (train 6,357,543; validation 657,209). Source: `docs/decisions/ADR-0004-real-data-pilot-prerequisite.md` lines 10-20. Local files match these sizes (above).
- Chunking: 65-byte UTF-8 chunks; P1 uses 4,096 training chunks and 512 validation chunks (`configs/p1_ram_screen.toml` `[data]`; `chunk_bytes = 65`). P3 to P9 reuse the same approved bytes (`docs/decisions/ADR-0008-bounded-longer-training.md` line 28; `docs/decisions/ADR-0009-frozen-backbone-capacity.md` line 46).
- Licence: the publisher README lists CC-BY-SA-3.0 (front matter) and CC BY-SA 4.0 (licensing paragraph); both preserved, not resolved (`docs/decisions/ADR-0004-real-data-pilot-prerequisite.md` line 32; `docs/RESEARCH_LOG.md` line 53). Local use approved; publication and redistribution not (ADR-0004 line 5).
- Backbone: width 32, 2 blocks, 4 heads (dimension 8), FFN width 64 (1,588 for the dense-matched control), byte vocabulary 256, context 64, 27,392 unique parameters (`docs/decisions/ADR-0005-ram-pilot-spec.md` line 27; `configs/p1_ram_screen.toml` `[model]`; `configs/p4_frozen_capacity.toml` `[model]`). Origin, as stated in the handoff (a design statement, not a training record): "First tests use a train-from-scratch small model, not a huge existing checkpoint." (`docs/RESEARCH_HANDOFF.md` line 93).

## NEEDS REVIEW (not decided by the clerk)

- **N1.** REVIEW.md line 121 says the C4-C8 comparison output "is not in the committed folder". `results/p9i-run-attempt2-2026-11-15/c4_c8_comparison_output.txt` is now present and states "(lead's run of compare_with_attempt1.py gates ... transcribed from the session)". Whether a transcription meets ADR-0017 §15.8 is a judgement for the lead or auditor.
- **N2.** Thread and determinism settings. REVIEW.md line 131 says the diagnostics "ran with 2 threads and without `use_deterministic_algorithms`". The scripts set 2 threads (d1 line 52, d2 line 42, d4 line 47) and 4 threads (d3 line 31, d5 line 26); none calls a determinism setting. The registered path sets 1 thread and deterministic algorithms (`studies/p9i/train.py` lines 775-782). How this is described is for the lead.
- **N3.** The seven `outputs/*_attempt1_KILLED_at_4096.jsonl` files each contain 9 records through update 8192, with meta `updates` = 8192 and `seconds` 78.7 to 97.0. REVIEW.md §7 item 3 says they were "killed at about 4,096 updates" and kept as partial output. Their update-8192 values differ from the completed reruns: d2 W7 draw 2, 4,096 slots, seed 500003 gives accuracy 0.980 in the killed file and 0.937 in the rerun; d2 W7 draw 0, 4,096 slots, seed 500004 gives 0.944 and 0.959. The clerk does not determine which account is correct.
- **N4.** The escape times in A2 are clerk-derived from the checkpoint grid (updates 0, 64, 256, 512, 1024, 2048, 4096, 8192). No file records an escape time. "not on grid" means no grid checkpoint meets the rule, not that no escape occurred between checkpoints.
- **N5.** `results/p9i-run-attempt2-2026-11-15/README.md` still reads "Status at the freeze: data generated, G1 passed ...; nothing trained" and does not describe the completed run; `OUTCOME.md` and `RESULTS.md` do. Not corrected (read-only).
- **N6.** ledger entries for run `P9IG-rehearsal-gates-draw2-20261115T003153Z` (generate and gates) appear in `results/p9i-run-attempt2-2026-11-15/ledger.json`; no document in the worktree describes that run (search of worktree text (outside .git and .venv) found only the ledger and a gate-audit mention).
- **N7.** per-update seconds and RSS for the registered run are not written as per-update fields; the table above uses the per-cell totals (`wall_seconds`, `peak_rss_bytes`) and a derived division. The 57 cells are in the git-ignored experiments directory of the main checkout, not in the worktree.
- **N8.** ~/.ollama holds 96 GB of model blobs (manifests name Qwen-family and other models; see the list above). The worktree's rules (CLAUDE.md line 17; AGENTS.md line 15; RESEARCH_HANDOFF line 405) cover downloads and external services, not local model files. Whether any local weight may be used is a human decision; the clerk did not open or evaluate them.
- **N9.** REVIEW.md §2.3 and §5 state that the W7 4,096 failure on the registered draw is a draw-dependent property and ask for lead review (REVIEW.md line 78 "PENDING LEAD REVIEW"; line 115). The clerk records the numbers (A2 tables) and does not interpret them.
- **N10.** Seed check: the rehearsal range printed above is the clerk's computation from the stride and offsets in `studies/p9/core.py` lines 839-856, not a value copied from a record.
- **N11.** During the run an untracked file appeared in the worktree: `docs/reviews/p9i-consolidation-2026-11-15/INTEGRATION_LOG.md` (`git status --short` shows `??`). The clerk did not create or edit it and did not read or change it. Its origin and status are for the lead to confirm.

## NOT FOUND (complete list)

- P9-II specification: no file defines "P9-II", "robust sparse address learning", or ADR-0019 (only mentions at ADR-0017 §15.9 and `docs/reviews/p9i-consolidation-2026-11-15/INTEGRATION_AUDIT.md` line 259).
- P10 specification, "two-teacher transfer", and a "capacity scaling" study definition: not in any worktree file (RESEARCH_HANDOFF.md §6 Phases 5 and 6 describe teacher distillation and joint training as future phases only).
- Per-update seconds and per-update RSS for calibration runs: not recorded (only per-task totals in `results/p9i-calibration-2026-11-14/manifest.json`).
- Per-update seconds and per-update RSS for the registered run: not recorded (only per-cell `wall_seconds` and `peak_rss_bytes`, in the git-ignored experiments directory of the main checkout).
- Escape time as a field of any diagnostic file: not recorded (derived only, see N4).
- Optimizer state bytes for studies P1 to P8: not in their readmes or summaries (P1, P4, P5, P8 searched).
- Hugging Face cache (`~/.cache/huggingface`): absent.
- Explicit uv.lock / pyproject.toml change rule in AGENTS.md or docs/RESEARCH_HANDOFF.md: not present (the rule is at CLAUDE.md line 34 only).
- WikiText-2 test split: not present locally (by design; ADR-0004 line 20 says test content remains uninspected).

Astra review: NOT_PERFORMED. Claude review is not Astra review. This file is an inventory; it makes no scientific judgement.

