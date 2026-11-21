# P10-I-S0: confirmation of F1 and F2 at 2daa30c, and the rebind question for 45d97ff..2daa30c

Auditor: `arbor-auditor` subagent, model Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-19. I did not write this code. `Astra review: NOT_PERFORMED`. This is independent engineering evidence, not Astra validation and not a human approval.

**Verdict: CONFIRMED — SAFE TO REBIND AND PROCEED.**
- **F1:** FIXED, with one deviation from its description (G1, advisory).
- **F2:** FIXED. The pins make the rebind exact, once only, and auditable. The only things the pins cannot judge are whether a pinned change is harmless and whether the ruling stays as committed (section 2); those rest on the ruling and on this audit trail.
- **The four files:** nothing in 45d97ff..2daa30c (drivers.py, sealed.py, stages.py, plan.py) computes, selects or reads a Stage R measurement, duration, flag, extension decision or seed.
- **plan.py:** adding the rebind record to `frozen_paths` changes neither the code identity nor the plan's content (section 3).

## Environment and commands
- Scratch at `<S0 worktree>/experiments/_scratch/audit7/` (git-ignored), with a copy made by `git archive 2daa30c`; deleted afterwards.
- I did not touch the real run directory, the sealed directory or `studies/p10is0/freeze/`. No git write, no sealed value, no registered seed, no network; one process, every command under `timeout`.
- `PYTHONPATH=$PWD timeout 600 uv run --locked python ../f1.py`: probes below.
- `timeout 1500 uv run --locked pytest tests/test_p10is0_guard.py tests/test_p10is0_guard2.py -q -p no:cacheprovider`: 46 passed (2.3 s).
- `git diff 4b2523f 2daa30c` and `git diff -U0 45d97ff 2daa30c -- studies/p10is0/{drivers,sealed,stages,plan}.py`, read in full.

## 1. F1: the leak guard
**Refused now (`out/f1.txt`):**
- every free-map key the old substring rule refused: `acc12345678`, `trainloss`, `Xacc`, and the earlier compounds;
- `accuracy/<task file>` and `x\accuracy.json` in a hashes map;
- `t…log.acc`;
- an int, a dict or a list as a hashes-map value;
- a map named like a hashes map but not one (`/identity/myhashes` with a measure key or a float);
- `sealed_files_sha256` with a measure key, and the top-level key `hashes_acc`.

`HASH_MAPS` membership is by the path ending in `hashes` or `sealed_files_sha256`. A look-alike map ending in `hashes` would only get the stricter treatment (values must be 64-hex). Outside a hashes map nothing is exempt.

**Accepted:**
- `tasks/s/taccacc00000000.log`, as designed: `t` + 14 hex can spell only hex letters and carries no value.
- **`<64hex>.loss` and `cal/<64hex>.accuracy` (G1).** `OPAQUE_DIGEST` is `^[0-9a-f]{64}(\.[a-z]+)?$`, so it exempts *any* lowercase extension, not "a 64-hex digest" as described. A measure word can ride as a file extension; it is a name, never a value.
- Free strings (`labels`, a string under `count`) and any 64-hex hashes-map value. This is the original guard's behaviour: it never checked string values.

**G1 ADVISORY:** restrict the digest suffix to the extensions the code writes, or to none. The code writes no such names today. Note that the rebind is once only, so make this change before rebinding or not at all.

## 2. F2: `rebind-pins` and `rebind-identity`
**What the code checks.** The ruling file must be committed (`ls-files`) under `results/`, with no uncommitted tracked change. It must carry the full `PIN` block:
- full commit hashes;
- Stage R's commit an ancestor of the new commit, and the new commit an ancestor of HEAD;
- the pinned file set equal to the set that differs from `durations.json`'s identity;
- each old hash equal to that identity and to the file at Stage R's commit, and each new hash equal to the current file and to the file at the new commit;
- every pinned file within `sealed.py`, `stages.py`, `drivers.py` and `plan.py`.

It refuses when a rebind record exists or `freeze/plan.json` exists, so it runs once and only before the plan. It rewrites only `code_identity` (`drivers.py:643-644`). It writes `freeze/durations_identity_rebind.json`, which records both commits, the ruler, every file with old and new SHA-256, the ruling path, the ruling's SHA-256 and the UTC time. The implementer's tests (`test_p10is0_guard2.py`) exercise the committed-ruling, pin-mismatch, out-of-scope, second-rebind and after-plan refusals; I read them and they pass.

**Laundering attempts, answered from the code:**
- **A science edit to `drivers.py` after the pinned commit:** refused. The current file's hash differs from the pinned new hash, and from the new commit's.
- **A pinned commit that contains the science edit:** accepted, if the ruling pins it. The pins prove which bytes were ruled on; they cannot judge what those bytes do.
- **The ruling amended after it was committed:** a later commit changes the file but not the record's `ruling_sha256`. Nothing re-verifies the ruling afterwards, so a change shows only in the git history and the record.
- **A `plan.py` edit beyond `frozen_paths`:** if it is pinned, it is accepted the same way.

**What remains the lead's honesty and the audit trail:**
- that the pinned diff of the four files is what this audit lists (section 3) and contains no science change;
- that the ruling is not rewritten after the rebind;
- that the ruling file names the auditor's report.

The record and the frozen hash of `durations.json` make any departure detectable afterwards; they do not prevent it.

## 3. Rebind question, 45d97ff..2daa30c (Stage R's identity is exactly 45d97ff; established in REAUDIT6)
Every changed definition, from the full `-U0` diff:

| File | Changed definitions | Computation? |
|---|---|---|
| drivers.py | `import re`; `emit_stage_r_completion` (new, completion print); `cmd_stage_r_status` (new, read-only re-print and missing EVENT files); `write_events_numbered` (new, EVENT text); `write_events` (now delegates to `write_events_numbered`: same text, still refuses to overwrite); `RULING_COSMETIC_FILES`, `REBIND_RECORD`, `PIN_RE` (new constants); `_changed_since_stage_r`, `rebind_pins`, `cmd_rebind_identity` (new); `cmd_stage_r` (its final print line only, after `durations.json` and the events are written) | No |
| sealed.py | `import re`; `PUBLIC_KEYS` (+`sealed_digest`, `sealed_files_sha256`); `OPAQUE_TASK_FILE`, `OPAQUE_DIGEST`, `HEX64`, `MEASURE_WORDS`, `HASH_MAPS` (new); `names_a_measure` (new); `validate_public` (hashes-map key and value checks); `hashes_digest` (new) | No: public-output validation and a hash of hashes. `write_sealed`, `read_sealed`, `sealed_dir`, `sealed_hashes` and `ALLOWED_READERS` are unchanged |
| stages.py | `build_parser` (subcommands `stage-r-status`, `rebind-pins`, `rebind-identity`); `main` (their dispatch) | No |
| plan.py | `frozen_paths`: adds `freeze/durations_identity_rebind.json` inside `if include_freeze_files` | No |

**The `plan.py` change.** `code_identity` calls `frozen_paths(include_freeze_files=False)`, so the identity file list and Stage R's recorded hashes are unaffected. `build_plan`, and therefore the plan's scientific content, does not use `frozen_paths`. The change only adds the record to the freeze's `inputs` and to the registered stages' identity checks.

**SAFE TO REBIND.**

## 4. The freeze and the registered stages afterwards
- `freeze.freeze` hashes `plan.hash_inputs(repo)`, which includes the rebind record once it exists, and the rewritten `durations.json`.
- `worker_guard` and `check_preconditions` verify every recorded input, so a later change to the record, `durations.json` or any code file is PAUSED — IDENTITY (exit 75). `check_code_identity` compares against the rebound identity, and a later code change is an engineering stop.
- A second rebind is refused (the record exists), as is any rebind after the plan.
- **Order:** commit the ruling with the pins, then `rebind-identity`, then the candidate plan (its `durations_sha256` changes), then the counting rehearsal, the caps and the freeze.

## 5. Other
- **G2 ADVISORY:** the rebind runs only when no uncommitted *tracked* change exists, and `freeze/` is untracked, so the rewritten `durations.json` and the record are first committed with the freeze. Make sure the freeze commit includes both.
- E3 stands, PENDING LEAD REVIEW: the checker copy excludes P10-I-R's files, and the definition of RATIO ABOVE 1.

## Appendix: probe script (verbatim; scratch deleted)

```python
"""F1 probes at 2daa30c (synthetic inputs only)."""
import json
from studies.p10is0 import sealed
def v(o):
    try:
        sealed.validate_public(o); return "ACCEPTED"
    except Exception as e:
        return "refused"
H = "0" * 64
P = {
 "free key acc12345678 (identity map, int)": {"identity": {"acc12345678": 951}},
 "free key trainloss (cell_types map)": {"cell_types": {"trainloss": {"e_star": 1}}},
 "free key Xacc": {"identity": {"Xacc": 1}},
 "hashes key: exempt task-file shape with acc hex (taccacc0000000.log)": {"hashes": {"tasks/s/taccacc00000000.log": H}},
 "hashes key: task-file shape + measure suffix (t...log.acc)": {"hashes": {"t0123456789abcd.log.acc": H}},
 "hashes key: digest + measure suffix (<64hex>.loss)": {"hashes": {H + ".loss": H}},
 "hashes key: digest + measure suffix (<64hex>.accuracy)": {"hashes": {"cal/" + H + ".accuracy": H}},
 "hashes key: measure dir + task file": {"hashes": {"accuracy/t0123456789abcd.log": H}},
 "hashes key: backslash path": {"hashes": {"x\\accuracy.json": H}},
 "hashes value int": {"hashes": {"x.json": 951}},
 "hashes value 64-hex": {"hashes": {"x.json": H}},
 "map named like a hashes map (identity/myhashes) with measure key": {"identity": {"myhashes": {"accuracy.json": H}}},
 "map named like a hashes map with float value": {"identity": {"myhashes": {"x.json": 0.95}}},
 "nested map inside hashes": {"hashes": {"x.json": {"acc": H}}},
 "sealed_files_sha256 with measure key": {"sealed_files_sha256": {"loss.json": H}},
 "top-level key hashes_acc": {"hashes_acc": {}},
 "labels free text with value": {"labels": ["accuracy 0.95"]},
 "string value under count": {"count": "accuracy=0.95"},
}
print(json.dumps({k: v(o) for k, o in P.items()}, indent=1))
```

`Astra review: NOT_PERFORMED`. Claude review is not Astra review.
