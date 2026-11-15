# Commit-hash mapping after commit-message rewrite — P8

The ten commits of this work were first created locally with a co-author trailer in the message body. The repository owner's global pre-push hook requires signed, single-line messages without such trailers, so before the single push each message was reduced to its first line and the commit re-signed. **No file content changed**: each commit's Git tree hash is identical before and after, and author timestamps are preserved. Only the commit hashes changed. Nothing had been pushed before the rewrite, so no remote history was replaced.

Documents and run manifests written before the push cite the original hashes — in particular the **freeze commit `80f46ae`**, which every stage manifest, ADR-0015 section 17 and the reviews name. It is pushed as `378aeac`. Use this table to resolve them. The tree hash is the content identity and can be checked with `git rev-parse <commit>^{tree}`.

| Original commit (cited in records) | Pushed commit | Tree hash (unchanged) | Subject |
|---|---|---|---|
| `273a1154012ab5d5e8ba522cc3e84547efc2da45` | `dae567aa4b0d2e4180dc94d8bf882e8f11f68aad` | `097c483ffd082b83480e1354c9ac679a6fdea45f` | Propose P8 locality-aware memory training pilot (ADR-0015 draft, pending Opus spec review) |
| `2579cff9d773e399c7b1113ae03f1fce14efc26b` | `01731f08db4e19a5b488a77a1632f29cd38150f2` | `e9d558292cdcff8872d65d4a87a9318c4ab224bc` | ADR-0015 revision 2: Opus spec review (1 blocker, 6 major) and the lead's response, before any P8 model exists |
| `74851bd30546ae1cafacaf6e330e191016721f3a` | `b5a80c2fac249e80e0e2b47ff05606f5e8115857` | `00910a74e509f2e530ebd912fee9df70b6a0965e` | P8 independent panel proof: validation ranks 3072-4095 eligible, unused and disjoint (auditor tool and record) |
| `ec833c82617f4822b65d83334cf27ad7c5aab1ed` | `0ed3c699c4d3452327e8f5135b61fdc0c7962657` | `5166f67a7ec0cb2d5b44de574381450713f3bd6f` | P8 pre-freeze audits: training audit, evaluation/simulation/analysis audit, re-check (READY TO FREEZE), auditor tools and kept failed attempts |
| `80f46aec96d3474a18f811ea77e68aa782b787f6` | `378aeac1f6d1b8a36b4956984b312247cf1b45a6` | `b13a9f9c09083a9b486adb9b691089f00409059f` | P8 freeze: ADR-0015 revision 3 with freeze record, implementation, tests, config, registered panel record and report generator |
| `8efdcc7a17725652d0d3b3f76dcc74d1b9be6d7c` | `b8302c247c302a4467cdaab81950774c23a28080` | `290d15dedc5cdaf57ea8bbbe3097575b1d582d14` | P8: raw records of the single registered run - 60/60 cells trained and evaluated, restore gate passed, 55/60 simulated (5 concentration cells failed in the unchanged null generator; failed records kept) |
| `e63a202167fa52de14582df2901afbec12379861` | `be6c08a6f5ebc1c7128811e47984e7f2a4bb1143` | `01a2b0181259023333acbc5c3c4b8eea34708b48` | P8: analysis records from the single registered analysis (study status INCOMPLETE, denominator 60) |
| `fee9fa051d81034d1862cd0ef7ce2ea22de826b6` | `a55995fdec1964557c86952f10e8141fa4a8b5f3` | `02e14c6d774542c9cfd37a553e5eb2a4886eafe0` | P8 independent recomputation from raw records (Opus): zero differences; analysis of the five null-generator failures; defects |
| `1c4fead9fa1512e271a7ae22d81dc37076b5ab5f` | `d47a9fd5c5204f3e6953f1b7cf3a0ba212f7badd` | `d25d33175e5820ce46b12f34e76631ca1f8c4d82` | P8 report generator: draw a ratio with zero misses in the denominator as undefined (post-run fix of a ZeroDivisionError; analysis-only tool, disclosed as defect 9) |
| `59aac827dc146c0519f3eaa606a6cbef1e969165` | `2d10338e6981d1e5d3f8b9c923818591c333fbe0` | `69ee64135ed499ac898e826737fc56b0fabe652c` | P8 results review, outcome record (study INCOMPLETE, no case LOCALITY-POSITIVE), report package and figures |

The original commits remain on the local branch `backup/p8-before-single-line-rewrite`, which was not pushed.
