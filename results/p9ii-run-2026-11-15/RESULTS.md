# ADR-0019 (P9II) results

Study status: **COMPLETE** (measured: derived from the run's manifests, gates and records).
Outcome: **ADDRESSING-RELIABLE: A5-D (LABEL-FREE), paired against A0 at 4,096: IMPROVES ON A0; at 16,384: NOT DISTINGUISHED FROM A0**
Stage 2 status: COMPLETE; Stage 3 status: COMPLETE.
Updates per unit U: 8192.

Interface carried forward: A0 (LABEL-FREE)

## Classes (measured counts, rules of section 8.4)

| stage | slots | arm | supervision | class | evaluated | successes | paired against A0 | d | median escape update (escaped cells only) | median escape update (censored at the readout) | dense |
|---|---|---|---|---|---|---|---|---|---|---|---|
| stage1 | 4096 | A0 | (LABEL-FREE) | UNRELIABLE | 16 | 4 |  |  | 5856.0 | 6176.0 |  |
| stage1 | 4096 | A1 | (ADDRESS-SUPERVISED IN TRAINING) | RELIABLE | 16 | 16 | IMPROVES ON A0 | 12 | 128.0 | 128.0 | DENSE AT CEILING |
| stage1 | 4096 | A1-S |  | FAILS | 16 | 0 | HARMS | -4 | nan | 8192.0 |  |
| stage1 | 4096 | A2 | (ADDRESS-SUPERVISED IN TRAINING) | FAILS | 16 | 0 | HARMS | -4 | 7488.0 | 8192.0 |  |
| stage1 | 4096 | A4 | (LABEL-FREE) | FAILS | 16 | 0 | HARMS | -4 | 7232.0 | 7584.0 |  |
| stage1 | 4096 | A5-C | (LABEL-FREE) | UNRELIABLE | 16 | 9 | IMPROVES ON A0 | 5 | 4160.0 | 4160.0 |  |
| stage1 | 4096 | A5-D | (LABEL-FREE) | RELIABLE | 16 | 16 | IMPROVES ON A0 | 12 | nan | 8192.0 | DENSE AT CEILING |
| stage2 | 16384 | A0 | (LABEL-FREE) | RELIABLE | 8 | 8 |  |  | 15392.0 | 15392.0 | DENSE AT CEILING |
| stage2 | 16384 | A1 | (ADDRESS-SUPERVISED IN TRAINING) | UNRELIABLE | 8 | 6 | NOT DISTINGUISHED FROM A0 | -2 | 448.0 | 448.0 |  |
| stage2 | 16384 | A1-S |  | FAILS | 8 | 0 | HARMS | -8 | nan | 32768.0 |  |
| stage2 | 16384 | A5-D | (LABEL-FREE) | RELIABLE | 8 | 8 | NOT DISTINGUISHED FROM A0 | 0 | nan | 32768.0 | DENSE AT CEILING |

Every contrast against A0 compares an arm at its better of two calibrated settings with an untuned baseline.

## Annotations at 4,096 slots

- NEGATIVE CONTROL FAILED: not printed
- A6 (oracle reference) relative next-byte loss rise r by draw (measured): d1: 0.154382308588131, d2: 0.1497474121650186, d3: 0.1498209279879945, d4: 0.1591536256683385, d5: 0.14721957398522445, d6: 0.1473839777163399, d7: 0.1580621843016756, d8: 0.14819368559524584
- A0 (LABEL-FREE): class UNRELIABLE; categories collapsed and not recovered: 4; collapsed and recovered: 12; never collapsed and separated: 0; never collapsed, not separated: 0; r by cell {'1/0': 0.083771067807593, '1/1': 0.0720280329513762, '2/0': 0.15903488153601555, '2/1': 0.07858822448651154, '3/0': 0.14119291286409438, '3/1': 0.1255330341140184, '4/0': 0.1467833247111385, '4/1': 0.18994911913507084, '5/0': 0.12993006806546603, '5/1': 0.13113161509055893, '6/0': 0.08659218915279392, '6/1': 0.11793117074572824, '7/0': 0.1491612454111913, '7/1': 0.13053893459760676, '8/0': 0.12348507520971228, '8/1': 0.14667633321620444}; absolute rise (percent) {'1/0': 8.3771067807593, '1/1': 7.20280329513762, '2/0': 15.903488153601556, '2/1': 7.8588224486511535, '3/0': 14.119291286409439, '3/1': 12.553303411401838, '4/0': 14.67833247111385, '4/1': 18.994911913507085, '5/0': 12.993006806546603, '5/1': 13.113161509055892, '6/0': 8.659218915279391, '6/1': 11.793117074572825, '7/0': 14.91612454111913, '7/1': 13.053893459760676, '8/0': 12.348507520971227, '8/1': 14.667633321620443}; ADDRESS STABLE median 0.866455078125 -> ADDRESS STABLE
- A1 (ADDRESS-SUPERVISED IN TRAINING): class RELIABLE; categories collapsed and not recovered: 0; collapsed and recovered: 15; never collapsed and separated: 1; never collapsed, not separated: 0; r by cell {'1/0': 0.1551142892294759, '1/1': 0.15582183224974186, '2/0': 0.1550545873537385, '2/1': 0.14522009708858186, '3/0': 0.15329053741189216, '3/1': 0.15591864404526465, '4/0': 0.17247897270507365, '4/1': 0.16259947611778458, '5/0': 0.14975995127139624, '5/1': 0.1510858174791439, '6/0': 0.15840826236920053, '6/1': 0.15841989449924435, '7/0': 0.15846755198296802, '7/1': 0.15405216920261267, '8/0': 0.14579505665931897, '8/1': 0.1504835027410791}; absolute rise (percent) {'1/0': 15.51142892294759, '1/1': 15.582183224974186, '2/0': 15.50545873537385, '2/1': 14.522009708858185, '3/0': 15.329053741189217, '3/1': 15.591864404526465, '4/0': 17.247897270507366, '4/1': 16.259947611778458, '5/0': 14.975995127139624, '5/1': 15.108581747914391, '6/0': 15.840826236920053, '6/1': 15.841989449924435, '7/0': 15.846755198296803, '7/1': 15.405216920261267, '8/0': 14.579505665931897, '8/1': 15.04835027410791}; ADDRESS RECALL median 1.0 -> ADDRESS RECALL; ADDRESS STABLE median 1.0 -> ADDRESS STABLE; dense comparison DENSE AT CEILING
- A1-S : class FAILS; categories collapsed and not recovered: 16; collapsed and recovered: 0; never collapsed and separated: 0; never collapsed, not separated: 0; r by cell {'1/0': 0.08802589674938287, '1/1': 0.08114082375446875, '2/0': 0.08123949390010213, '2/1': 0.08226927990353933, '3/0': 0.08357552878401023, '3/1': 0.09846679900233618, '4/0': 0.09185446584174273, '4/1': 0.09043574555338361, '5/0': 0.07221376648256654, '5/1': 0.07295878094465302, '6/0': 0.07797749326176838, '6/1': 0.07460017977919985, '7/0': 0.0812744664001357, '7/1': 0.08243537707997739, '8/0': 0.08101250880195163, '8/1': 0.08680197341306066}; absolute rise (percent) {'1/0': 8.802589674938286, '1/1': 8.114082375446875, '2/0': 8.123949390010212, '2/1': 8.226927990353932, '3/0': 8.357552878401023, '3/1': 9.846679900233617, '4/0': 9.185446584174272, '4/1': 9.043574555338362, '5/0': 7.221376648256654, '5/1': 7.295878094465302, '6/0': 7.797749326176838, '6/1': 7.460017977919985, '7/0': 8.12744664001357, '7/1': 8.243537707997739, '8/0': 8.101250880195163, '8/1': 8.680197341306066}; ADDRESS STABLE median 0.97314453125 -> ADDRESS STABLE
- A2 (ADDRESS-SUPERVISED IN TRAINING): class FAILS; categories collapsed and not recovered: 14; collapsed and recovered: 2; never collapsed and separated: 0; never collapsed, not separated: 0; r by cell {'1/0': 0.052302934053217995, '1/1': 0.05720175424698645, '2/0': 0.06779784459040435, '2/1': 0.06658077114527479, '3/0': 0.07859174456948555, '3/1': 0.08797067267288805, '4/0': 0.08677575989426507, '4/1': 0.06129058114971593, '5/0': 0.07009342706132475, '5/1': 0.08066182608534718, '6/0': 0.06238357008438901, '6/1': 0.06796221026656872, '7/0': 0.11638346954320829, '7/1': 0.08045239066213192, '8/0': 0.13788383190879486, '8/1': 0.12022012531267058}; absolute rise (percent) {'1/0': 5.2302934053218, '1/1': 5.720175424698645, '2/0': 6.779784459040434, '2/1': 6.658077114527479, '3/0': 7.859174456948555, '3/1': 8.797067267288805, '4/0': 8.677575989426508, '4/1': 6.129058114971593, '5/0': 7.009342706132475, '5/1': 8.066182608534717, '6/0': 6.238357008438901, '6/1': 6.796221026656872, '7/0': 11.638346954320829, '7/1': 8.045239066213192, '8/0': 13.788383190879486, '8/1': 12.022012531267059}; ADDRESS RECALL median 0.00341796875 -> not printed; ADDRESS STABLE median 0.795654296875 -> not printed; SUPERVISION-DEPENDENT: SUPERVISION-DEPENDENT (14 of 16 evaluated cells; ADDRESSES RE-MAPPED: 0 cells, descriptive); d(A2 against A1) -16 (descriptive)
- A4 (LABEL-FREE): class FAILS; categories collapsed and not recovered: 5; collapsed and recovered: 11; never collapsed and separated: 0; never collapsed, not separated: 0; r by cell {'1/0': 0.12775484706228907, '1/1': 0.12397976420365849, '2/0': 0.1535008988389168, '2/1': 0.1482758398921147, '3/0': 0.15262987174885295, '3/1': 0.14630313465355008, '4/0': 0.167660182073406, '4/1': 0.17275561951437088, '5/0': 0.15574055955923943, '5/1': 0.12305432487605597, '6/0': 0.10035434994538925, '6/1': 0.05625673564705829, '7/0': 0.14381240005104945, '7/1': 0.16117823151767116, '8/0': 0.08449810130529878, '8/1': 0.11896835209465677}; absolute rise (percent) {'1/0': 12.775484706228907, '1/1': 12.397976420365849, '2/0': 15.350089883891679, '2/1': 14.82758398921147, '3/0': 15.262987174885295, '3/1': 14.630313465355007, '4/0': 16.7660182073406, '4/1': 17.275561951437087, '5/0': 15.574055955923944, '5/1': 12.305432487605596, '6/0': 10.035434994538925, '6/1': 5.625673564705829, '7/0': 14.381240005104946, '7/1': 16.117823151767116, '8/0': 8.449810130529878, '8/1': 11.896835209465676}; ADDRESS STABLE median 0.818603515625 -> ADDRESS STABLE
- A5-C (LABEL-FREE): class UNRELIABLE; categories collapsed and not recovered: 0; collapsed and recovered: 16; never collapsed and separated: 0; never collapsed, not separated: 0; r by cell {'1/0': 0.18517506844087814, '1/1': 0.12888629052501865, '2/0': 0.09217598578084364, '2/1': 0.08005372065222786, '3/0': 0.10175357975630853, '3/1': 0.11437537320014828, '4/0': 0.14056964253297358, '4/1': 0.15066359145452735, '5/0': 0.1518714429165142, '5/1': 0.11128543168058694, '6/0': 0.1818895561852748, '6/1': 0.15163046628135352, '7/0': 0.11966814458988807, '7/1': 0.10085482963438998, '8/0': 0.15756621412437669, '8/1': 0.11334835886564737}; absolute rise (percent) {'1/0': 18.517506844087812, '1/1': 12.888629052501866, '2/0': 9.217598578084365, '2/1': 8.005372065222787, '3/0': 10.175357975630853, '3/1': 11.437537320014828, '4/0': 14.056964253297357, '4/1': 15.066359145452735, '5/0': 15.18714429165142, '5/1': 11.128543168058695, '6/0': 18.18895561852748, '6/1': 15.163046628135351, '7/0': 11.966814458988807, '7/1': 10.085482963438999, '8/0': 15.756621412437669, '8/1': 11.334835886564736}; ADDRESS STABLE median 0.898681640625 -> ADDRESS STABLE
- A5-D (LABEL-FREE): class RELIABLE; categories collapsed and not recovered: 0; collapsed and recovered: 0; never collapsed and separated: 16; never collapsed, not separated: 0; r by cell {'1/0': 0.15226250827869603, '1/1': 0.15259170263292945, '2/0': 0.14930086268417628, '2/1': 0.14782518681904866, '3/0': 0.15651617654447827, '3/1': 0.14789972378321165, '4/0': 0.1561568046140461, '4/1': 0.15564782598597302, '5/0': 0.13978099806948502, '5/1': 0.14886630051292113, '6/0': 0.15186812579327924, '6/1': 0.14815490125761338, '7/0': 0.15607442832996266, '7/1': 0.15808610818091512, '8/0': 0.13102404642886695, '8/1': 0.13635133365922747}; absolute rise (percent) {'1/0': 15.226250827869602, '1/1': 15.259170263292946, '2/0': 14.930086268417627, '2/1': 14.782518681904866, '3/0': 15.651617654447827, '3/1': 14.789972378321165, '4/0': 15.61568046140461, '4/1': 15.5647825985973, '5/0': 13.978099806948501, '5/1': 14.886630051292112, '6/0': 15.186812579327924, '6/1': 14.815490125761338, '7/0': 15.607442832996266, '7/1': 15.808610818091513, '8/0': 13.102404642886695, '8/1': 13.635133365922748}; ADDRESS STABLE median 0.913818359375 -> ADDRESS STABLE; dense comparison DENSE AT CEILING

## Annotations at 16,384 slots

- NEGATIVE CONTROL FAILED: not printed
- A6 (oracle reference) relative next-byte loss rise r by draw (measured): d10: 0.15889226426438785, d11: 0.1571125420251924, d12: 0.15999277539438914, d9: 0.1569181509926336
- A0 (LABEL-FREE): class RELIABLE; categories collapsed and not recovered: 0; collapsed and recovered: 8; never collapsed and separated: 0; never collapsed, not separated: 0; r by cell {'10/0': 0.14280769226036757, '10/1': 0.1470428467924541, '11/0': 0.1515715381896212, '11/1': 0.15658884247354696, '12/0': 0.1464498111199586, '12/1': 0.15608451923448813, '9/0': 0.15671887624135408, '9/1': 0.16011130388198935}; absolute rise (percent) {'10/0': 14.280769226036757, '10/1': 14.704284679245411, '11/0': 15.157153818962122, '11/1': 15.658884247354695, '12/0': 14.644981111995861, '12/1': 15.608451923448813, '9/0': 15.671887624135408, '9/1': 16.011130388198936}; ADDRESS STABLE median 0.89385986328125 -> ADDRESS STABLE; readout at U: not RELIABLE at U; dense comparison DENSE AT CEILING
- A1 (ADDRESS-SUPERVISED IN TRAINING): class UNRELIABLE; categories collapsed and not recovered: 0; collapsed and recovered: 8; never collapsed and separated: 0; never collapsed, not separated: 0; r by cell {'10/0': 0.16286258804948447, '10/1': 0.14703243242084452, '11/0': 0.15334600884556893, '11/1': 0.1600057331052286, '12/0': 0.15402225801107142, '12/1': 0.1615909945444549, '9/0': 0.15565351520115803, '9/1': 0.16241539797696583}; absolute rise (percent) {'10/0': 16.286258804948446, '10/1': 14.70324324208445, '11/0': 15.334600884556892, '11/1': 16.00057331052286, '12/0': 15.402225801107141, '12/1': 16.159099454445492, '9/0': 15.565351520115803, '9/1': 16.241539797696582}; ADDRESS RECALL median 1.0 -> ADDRESS RECALL; ADDRESS STABLE median 0.9996337890625 -> ADDRESS STABLE; readout at U: not RELIABLE at U
- A1-S : class FAILS; categories collapsed and not recovered: 8; collapsed and recovered: 0; never collapsed and separated: 0; never collapsed, not separated: 0; r by cell {'10/0': 0.0941351180868599, '10/1': 0.09890308633137321, '11/0': 0.09005313473283122, '11/1': 0.09650192674120016, '12/0': 0.11146404893592712, '12/1': 0.09398314563976075, '9/0': 0.1098664830625214, '9/1': 0.11125560928393152}; absolute rise (percent) {'10/0': 9.413511808685989, '10/1': 9.890308633137321, '11/0': 9.005313473283122, '11/1': 9.650192674120015, '12/0': 11.146404893592713, '12/1': 9.398314563976076, '9/0': 10.98664830625214, '9/1': 11.125560928393153}; ADDRESS STABLE median 0.94830322265625 -> ADDRESS STABLE; readout at U: not RELIABLE at U
- A5-D (LABEL-FREE): class RELIABLE; categories collapsed and not recovered: 0; collapsed and recovered: 0; never collapsed and separated: 8; never collapsed, not separated: 0; r by cell {'10/0': 0.15643954021551457, '10/1': 0.1586307506406329, '11/0': 0.15612372217658235, '11/1': 0.15440273141187205, '12/0': 0.15786693069022587, '12/1': 0.15327901944670155, '9/0': 0.15148141772299495, '9/1': 0.14793077028079316}; absolute rise (percent) {'10/0': 15.643954021551457, '10/1': 15.86307506406329, '11/0': 15.612372217658235, '11/1': 15.440273141187205, '12/0': 15.786693069022586, '12/1': 15.327901944670156, '9/0': 15.148141772299494, '9/1': 14.793077028079315}; ADDRESS STABLE median 0.8714599609375 -> ADDRESS STABLE; readout at U: ALSO AT MATCHED UPDATES; dense comparison DENSE AT CEILING

## Stage 3 (probe)

- SCALE PROBE UNINFORMATIVE: 0 of 2 cells succeed (A0); a probe at 32 exposures per fact: it can only be positive or uninformative; a non-positive result is exposure-limited

## Hypothesis readings (section 8.6)

- H19-A: not supported
- H19-B: supported
- H19-C: CONTRADICTED
- H19-D: CONTRADICTED
- H19-E (A0): not supported
- H19-E (A1): supported
- H19-E (A1-S): not supported
- H19-E (A2): not supported
- H19-E (A4): not supported
- H19-E (A5-C): not supported
- H19-E (A5-D): supported
- H19-F: not supported
- H19-G: supported

## What must not be claimed (section 13)

- Nothing about memory capacity, useful-capacity scaling, locality or incremental learning is tested here. More slots in use is not more capacity.
- A reliable arm is not shown reliable on natural language, on another backbone, with another interface than W7, or at 65,536 slots. Stage 3 is a probe at 32 exposures per fact and can only be positive or uninformative.
- Address supervision is a training label this task provides; a supervised arm's success says nothing about learning addresses without labels.
- W7 is told the record length and the memory is told the answer position; the LM-capability criterion is measured under that condition and says nothing about a deployed system.
- Matched exposure at 16,384 is not matched optimization.
- A0 is untuned by design; no tuned arm is shown to beat a tuned baseline.
- No success probability above the per-draw bounds stated in section 5 is claimed.
- No efficiency claim: work counts and CPU seconds are descriptive.
- A failure here is not a failure of the ArborLM concept.
- Astra review: NOT_PERFORMED. A Claude review is not an Astra review; no human approval is implied by this report.

