# P10-I-S2 Part Q: fifth re-audit, `git diff 16ed26f dfb801a` (69a8589 and the lead's dfb801a)

- **Auditor.** The `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-19. I wrote none of the audited code.
- **Method.** I read the diff by commit. Then I ran one short in-process check (`r5.py`, below) on a `git archive dfb801a` copy at `/Users/daniellaloush/dandush03/ArborLM-sealed/audit-s2-r5/`, deleted afterwards. This pass did not re-run the launch-script end-to-end checks; the per-stage entry point is unchanged since REAUDIT4.
- **Limits observed.** One process, `timeout` on everything, no pytest, no sealed value, no registered seed, no network, no git writes. `experiments/P10IS2-Q-rehearsal-measure4-20261119` was not touched. Only a copy of the public `measure3` record was read.
- **Status.** This audit is independent engineering evidence. It is not Astra validation and not human approval. `Astra review: NOT_PERFORMED`.

## Verdict: READY TO FREEZE, given a COMPLETE counting rehearsal against a candidate plan carrying the v2 caps

There is no blocking finding. One item is to record in Decision 2 (R1). The rest are advisory.

## 1. The formula (`whole-process-v2`)

**What it computes.** Projected seconds = overhead + rate × units, where:
- `overhead` is the world-build time measured inside `execute` of the stage's measuring process (`holder["overhead"]`, timed from before `build_world` to after `make_ctx`);
- `rate = (stage_seconds − overhead) / units_done`;
- `stage_seconds` is the stage's whole `execute` charge.

**It matches what a registered stage is charged.** `execute` charges each process its own wall time from the start of `execute`, and the same span is what is measured.

| Stage | How it is projected |
|---|---|
| `inputs`, `partition`, `analysis` | One unit each, so projected = the measured whole-process seconds. `analysis` builds no world, so its overhead is 0. It is now measured instead of the fixed 60 s, which is used only on the old path |
| `qfit`, `regeneration`, `outputs` | Units done equal the registered units |
| `qcheck` and `generation` | The per-process fixed work inside the body (partition rebuild, digest re-generation) is folded into the rate and so scaled by full ÷ done: about 16× for `qcheck` and about 21× for `generation`. This **over-projects**, which is conservative |
| Generation's batches | Counted by units (sources), inside one process |

**Pause and resume.** A paused and resumed stage pays the overhead again. That is not in the projection; the 2× cap absorbs about one resume for every stage.

**The cap rule is unchanged:**
- `caps_proposal(charged, projected)`: each stage cap is 2 × projected, rounded up to 0.01 h;
- the total is the charge + 2 × the sum of all stages;
- caps-proposal, caps-config and the freeze all go through `proposal_from_record`.

`r5.py` checks this by hand on a synthetic v2 record: the hand computation equals `proposal_from_record` (`True`). A record missing one stage's overhead is refused. **The real `measure3` record (v1) is refused** ("does not carry caps_formula 'whole-process-v2'").

**A1 (ADVISORY): `outputs` and `analysis` are under-projected.** Their units are fixed (panel items, or 1), but in the registered run they also do work that grows with the run:
- `outputs` builds the token bank and runs the tokenization checks over the **accepted pools**: about 24,000–26,000 per capability, against about 2,600 (A) and 900 (B) from one measuring block;
- both stages write the manifest by **hashing the whole run directory twice**: about 27,000 generation batch files in the registered run, about 2,500 in the measuring run.

Neither stage checks its cap after its teacher batches, so neither will be PAUSED by this. Each will finish and may record `within_cap: false` with a warning. The counting rehearsal (2 blocks) will not show it. Expect it in the registered run; it is not a stop. If you want it fixed, use accepted items and files hashed as units for these two stages.

## 2. `caps-reset`

**What it does correctly.**
- It refuses while `provisional` is true ("nothing to reset").
- It refuses while `freeze/partq_freeze_record.json` exists.
- It writes `freeze/superseded/partq_caps_superseded_<utc>.json` containing:
  - the reason;
  - the old caps;
  - `provisional_was`;
  - `config_sha256_before`;
  - a note.
- It writes a dated comment into `[stage_caps]`.

`r5.py` ran apply → reset → apply again: after the reset, `provisional` is true and every cap is 0, and the record holds the old total.

**R1 (REQUIRED as a record in Decision 2, or a small code refusal).** "Cannot be used once a registered result exists" is enforced **only** through the freeze record. With the freeze record moved aside (as was done for attempt 1), `caps-reset` succeeds (`r5.py`: "freeze record moved aside (`attempt9/`)" gives exit 0) even if a registered run had produced Q records. Either:
- state in Decision 2 that `caps-reset` is never used once a registered stage beyond `inputs` has written a record; or
- make it refuse when any `freeze/**/partq_freeze_record.json` names a run directory that holds a `qfit`, `qcheck` or `generation` record.

**The freeze.** It refuses a v1 record (`projection_from_record`) and caps that differ from the rule applied to the v2 record (`caps_match_config` on `proposal_from_record`). It still requires `kind_of_rehearsal == "measuring"` and `caps_provisional is True` on that record.

## 3. `--rehearsal-kind measuring`

- **Registered launches.** The flag takes effect only inside the `--rehearsal` branch, which keeps every refusal of REAUDIT3: commit `-` only, no freeze record, not the plan's run directory. Passed to a registered launch without `--rehearsal`, it is **silently ignored**, which is harmless. **A3 (ADVISORY):** refuse it there, as `--plan-file` is refused.
- **Registered run in a measuring directory.** Refused: measuring records carry mode `rehearsal`, and `require_one_mode` rejects them.
- **A2 (ADVISORY): measuring and counting directories can be swapped.** Measuring and counting share mode `rehearsal`, so neither driver refuses a directory left by the other. Neither driver refuses a non-empty run directory either (`run_dir.mkdir(exist_ok=True)`).
  - A counting rehearsal pointed at a measuring directory reuses the existing generation result. Its forced pause (expected exit 4) then does not happen, so it ends INCOMPLETE rather than passing.
  - A measuring rehearsal rerun in a used directory computes its rates over everything charged there.
  - Fix: both drivers refuse a run directory that already holds stage records or ledger entries. Until then, use fresh directories only.

## 4. The measuring rehearsal's own plan

- `measuring_plan.json` is written inside the measuring run directory, never under `freeze/`, and is built with the caps unset. The rehearsal refuses unless `caps-reset` has been run first.
- **It cannot be frozen on:**
  - the freeze reads only `freeze/partq_plan.json`;
  - it refuses provisional caps;
  - it requires a *counting* record naming that plan's hash.
- **Its scientific content equals the candidate plan's.** It is built by the same `qplan.build_candidate` from the same config and inputs file, in registered mode, so it also requires the shared ledger with the 144 windows. The differences are only:
  - `stage_caps` and `caps_provisional` (zero against entered);
  - the config hash in `frozen_files` and `config_sha256`, which follows from the caps lines;
  - `run_dir` (`<measuring dir>/registered_run_dir_unused`).
- The layout, items, seeds, thresholds and frozen code are equal. The candidate plan must therefore be built with the same `--inputs` file.

## 5. The removed "rehearsal-failed" entry

Removing it loses no charged second:
- The old wrapper charged the **orchestrator's** whole wall time on failure. The per-stage processes had already charged the same seconds, so it counted them twice.
- Each stage process charges itself in `execute`, in a `finally`, and a killed one is charged by the next launch.

**A4 (ADVISORY): small uncharged times, consistent with the caps.** Two kinds of time are charged neither in rehearsals nor in registered runs:
- each process's time **before** `execute` (interpreter start, imports, preconditions, `verify_plan` hashing);
- the candidate-ledger command.

Projection and charge exclude them alike, so the caps are consistent. Ruling L2's sum is undercounted by roughly seconds to tens of seconds per process. If you want it closed, charge from `main()`.

## 6. Anything else

- **Hashing the inputs twice per process** (`pkgmanifest.verify_inputs`, then `datagen.verify_downloads` and `check_wikitext`): **leave it.** It is about 2 GB of SHA-256 per process, a few seconds against an overhead dominated by corpus parsing and model loading. Both checks are wanted, and the cost is now inside the measured overhead.
- **REAUDIT3 F3** stays for Decision 2: the charges outside the total cap (959.3 s, the counting rehearsals, the ledger command, attempt 1's 13.09 s). The new measuring record's `charged_before_freeze_seconds` covers only its own run directory plus any `--charged-ledger` named.
- **dfb801a** is the correct output of `caps-reset`: the record holds the old caps (22.49 h) and the reason "counting4: partition 391 s vs cap 144 s". The config is back to provisional with zero caps. **The committed `freeze/partq_plan.json` still carries the old caps.** It must be superseded by a new candidate plan after `caps-config --apply` with the v2 record, otherwise the counting rehearsal refuses at `verify_plan` (caps differ).

## Script (verbatim; scratch deleted)

### r5.py
```python
"""REAUDIT5 quick checks on a copy of dfb801a (no clone launches): the v1 record refused for caps; the v2 rule by hand against
proposal_from_record on a synthetic v2 record; caps-config --apply then caps-reset (record, refusals: provisional, freeze record)."""
import json, math, shutil, subprocess, sys
from pathlib import Path
r, base = Path(sys.argv[1]), Path(sys.argv[2]); sys.path[:0] = [str(r), str(r / "src")]
from studies.p10is2.common import core
from studies.p10is2.partq import freeze, plan as qplan, stages
v1 = json.loads((base / "meas_v1.json").read_text())
try: freeze.proposal_from_record(v1); print("v1: NOT refused")
except core.StageRefused as e: print("v1 record:", str(e)[:120])
S = list(qplan.REHEARSAL_STAGES)
over = {s: 100.0 + i for i, s in enumerate(S)}; rate = {s: 0.01 * (i + 1) for i, s in enumerate(S)}; units = {s: 1000.0 * (i + 1) for i, s in enumerate(S)}
v2 = {**core.envelope("rehearsal", "Q"), "kind_of_rehearsal": "measuring", "caps_provisional": True, "caps_formula": qplan.CAPS_FORMULA, "rates_seconds_per_unit": rate, "overhead_seconds": over, "projection_units": units, "charged_before_freeze_seconds": 5000.0}
hand = {s: over[s] + rate[s] * units[s] for s in S}
ceil = lambda x: math.ceil(x / 3600 * 100 - 1e-9) / 100
want = {**{f"{s}_hours": ceil(2 * hand[s]) for s in S}, "total_hours": ceil(5000.0 + 2 * sum(hand.values()))}
got = freeze.proposal_from_record(v2); print("v2 rule by hand == proposal_from_record:", got == want, "| analysis projected:", hand["analysis"])
v2b = dict(v2); v2b["overhead_seconds"] = {k: v for k, v in over.items() if k != "analysis"}
try: freeze.proposal_from_record(v2b); print("missing overhead: NOT refused")
except core.StageRefused as e: print("v2 missing an overhead:", str(e)[:90])
mp = base / "meas_v2.json"; core.write_record(mp, v2, overwrite=True)
def run(*a):
    p = subprocess.run([sys.executable, "-B", "-m", "studies.p10is2.partq.stages", *a, "--repo", str(r)], cwd=r, capture_output=True, text=True, timeout=300)
    return p.returncode, ([l for l in (p.stdout + p.stderr).splitlines() if "Warn" not in l and "_conv" not in l] or [""])[-1][:150]
print("caps-reset while provisional:", run("caps-reset", "--reason", "x"))
print("caps-config --apply:", run("caps-config", "--measuring-rehearsal", str(mp), "--apply"))
print("caps-reset:", run("caps-reset", "--reason", "audit test"))
cfg = core.load_config("Q", r / core.CONFIG_Q); print("   after reset: provisional", cfg["caps"]["provisional"], "caps all 0:", all(float(v) == 0 for v in cfg["stage_caps"].values()))
recs = sorted((r / "studies/p10is2/freeze/superseded").glob("partq_caps_superseded_*.json")); last = json.loads(recs[-1].read_text())
print("   superseded record keys:", sorted(last), "| caps kept:", last["stage_caps_hours"]["total_hours"])
print("caps-config --apply again:", run("caps-config", "--measuring-rehearsal", str(mp), "--apply"))
(r / core.FREEZE_RECORD_Q).parent.mkdir(parents=True, exist_ok=True); (r / core.FREEZE_RECORD_Q).write_text("{}")
print("caps-reset with a freeze record:", run("caps-reset", "--reason", "x"))
(r / core.FREEZE_RECORD_Q).unlink(); (r / "studies/p10is2/freeze/attempt9").mkdir(); (r / "studies/p10is2/freeze/attempt9/partq_freeze_record.json").write_text("{}")
print("caps-reset with a freeze record moved aside (attempt9/):", run("caps-reset", "--reason", "x"))
```
Output:
```
v1 record: refused: the measuring record does not carry caps_formula 'whole-process-v2': it was not made through the registered ent
v2 rule by hand == proposal_from_record: True | analysis projected: 747.0
v2 missing an overhead: refused: the measuring record has no rate, overhead or units for stage(s) ['analysis']: a 
caps-reset while provisional: (2, 'REFUSED: refused: the caps are not entered (provisional is true): nothing to reset')
caps-config --apply: (0, '{"config": "-sealed/audit-s2-r5/repo/configs/p10is2_partq.toml", "applied": {"inputs_hours": 0.07, "partition_ho')
caps-reset: (0, '{"config": "-sealed/audit-s2-r5/repo/configs/p10is2_partq.toml", "superseded_record": "/Users/daniellaloush/dand')
   after reset: provisional True caps all 0: True
   superseded record keys: ['config_sha256_before', 'kind', 'note', 'oracle_line', 'part', 'provisional_was', 'reason', 'schema', 'stage_caps_hours', 'study', 'utc', 'what'] | caps kept: 2.99
caps-config --apply again: (0, '{"config": "-sealed/audit-s2-r5/repo/configs/p10is2_partq.toml", "applied": {"inputs_hours": 0.07, "partition_ho')
caps-reset with a freeze record: (2, 'REFUSED: refused: a freeze record exists; move it aside by a recorded step before correcting the caps')
caps-reset with a freeze record moved aside (attempt9/): (0, '{"config": "-sealed/audit-s2-r5/repo/configs/p10is2_partq.toml", "superseded_record": "/Users/daniellaloush/dand')
```

`Astra review: NOT_PERFORMED`. Claude review is not Astra review. This audit is not human approval.
