# ruff: noqa
"""Integrity of the A1 records (auditor's own code; standard library only).
Run: python3 -B audit_integrity.py
"""
import collections, glob, hashlib, json, os, subprocess

RUN = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10IR-registered-20261118"
S1 = "/Users/daniellaloush/dandush03/ArborLM/experiments/P10S1-registered-attempt2-20261117"
W = "/Users/daniellaloush/dandush03/ArborLM/.claude/worktrees/arborlm-consolidation-experiment-2b31c1"
FREEZE = "c712a905b01da3f12e2f884f8eaf44933a1756db"
OUT = os.path.dirname(os.path.abspath(__file__))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_blob_sha256(rel):
    data = subprocess.run(["git", "-C", W, "show", f"{FREEZE}:{rel}"], capture_output=True, check=True).stdout
    return hashlib.sha256(data).hexdigest()


log = []
# freeze identity: plan and config at the freeze commit vs what the manifests carry
plan_sha_c = git_blob_sha256("studies/p10ir/freeze/plan.json")
cfg_sha_c = git_blob_sha256("configs/p10ir_routing.toml")
log.append(f"plan.json sha256 at {FREEZE[:7]}: {plan_sha_c}; config: {cfg_sha_c}")
for st in ("gates-a1", "a1", "analysis", "report"):
    m = json.load(open(f"{RUN}/{st}/manifest.json"))
    log.append(f"manifest {st}: status {m['status']} mode {m['mode']} clean {m.get('clean')} item_errors {m.get('item_errors')} tasks {len(m['tasks'])} "
               f"task statuses {dict(collections.Counter(t['status'] for t in m['tasks'].values()))} plan==freeze {m['identity']['plan_sha256'] == plan_sha_c} config==freeze {m['identity']['config_sha256'] == cfg_sha_c} "
               f"platform {m['identity']['platform']['system']}/{m['identity']['platform']['machine']}/torch {m['identity']['platform']['torch']}/threads {m['identity']['platform']['torch_num_threads']},{m['identity']['platform']['torch_interop_threads']}/det {m['identity']['platform']['deterministic_algorithms']} charged_s {m['charged_seconds']:.1f} history {len(m['history'])}")
# frozen files of the study at the freeze commit equal the worktree (the code the run imported)
diff = subprocess.run(["git", "-C", W, "diff", "--stat", FREEZE, "--", "studies/p10ir", "configs/p10ir_routing.toml", "studies/p10s1", "studies/p9", "src/arborlm"], capture_output=True, text=True).stdout
log.append(f"git diff {FREEZE[:7]}..worktree for studies/p10ir, config, studies/p10s1, studies/p9, src/arborlm: {'EMPTY' if not diff.strip() else diff}")
plan = json.loads(subprocess.run(["git", "-C", W, "show", f"{FREEZE}:studies/p10ir/freeze/plan.json"], capture_output=True, check=True).stdout)
a1_items = [it for it in plan["items"] if it["stage"] == "A1"] if isinstance(plan["items"], list) else None
if a1_items is None:
    a1_items = [it for it in plan["items"]["A1"]] if "A1" in plan["items"] else []
log.append(f"plan A1 items: {len(a1_items)}; digests: {len(plan['checkpoint_digests'])}")

# gate 1, independently: every checkpoint's model.pt vs snapshot.json, train.json, plan digest; train.json vs committed manifest
tm = plan.get("p10s1_train_manifest") or {}
tm_path = tm.get("path", "")
tm_path = tm_path if os.path.isabs(tm_path) else os.path.join(W, tm_path)
tm_ok = os.path.isfile(tm_path) and sha(tm_path) == tm.get("sha256")
by_label = {t["label"]: t.get("result_sha256") for t in json.load(open(tm_path))["tasks"]} if tm_ok else {}
bad, n = [], 0
cells = set()
for it in a1_items:
    snap = f"{S1}/cells/{it['cell']}/snapshots/u{it['update']:07d}"
    actual = sha(f"{snap}/model.pt")
    s_json = json.load(open(f"{snap}/snapshot.json")).get("model_sha256")
    t_json = (json.load(open(f"{S1}/cells/{it['cell']}/train.json")).get("snapshot_sha256") or {}).get(str(it["update"]))
    p_dig = plan["checkpoint_digests"].get(f"{it['cell']}|{it['update']}")
    n += 1
    cells.add(it["cell"])
    if not (actual == s_json == t_json == p_dig):
        bad.append(it["id"])
tj_bad = [c for c in sorted(cells) if sha(f"{S1}/cells/{c}/train.json") != by_label.get(c)]
log.append(f"gate 1 recomputed: checkpoints {n}, disagreeing {len(bad)} {bad[:3]}; committed train manifest hash ok {tm_ok}; train.json vs manifest result_sha256: {len(cells)} cells, disagreeing {len(tj_bad)}")

# per-item gate inventory
inv = collections.Counter()
status = collections.defaultdict(collections.Counter)
recall_tree_up, recall_ivf = 0, 0
t0path_q = []
ex = collections.defaultdict(list)
for p in sorted(glob.glob(f"{RUN}/a1/items/*/item.json")):
    it = json.load(open(p))
    for name, g in it["gates"].items():
        inv[name] += 1
        status[name][g.get("status")] += 1
        if name.startswith("index_rebuild"):
            pass
    if it["arm"] == "T-OQ":
        t0path_q.append(it["gates"]["t0_path"].get("queries_checked"))
        for k in ("tv1_priors_on_against_off", "t3_against_independent_flat", "t2_against_independent_flat"):
            g = it["gates"][k]
            ex[k].append((g["sets_differ"], g["float_ties"], g["not_float_ties"], g["max_weight_difference"]))
    if "tree_recall_reproduction" in it["gates"]:
        recall_tree_up += 1
    if "ivf_recall_reproduction" in it["gates"]:
        recall_ivf += 1
    if it["platform"]["torch_num_threads"] != 1 or not it["platform"]["deterministic_algorithms"]:
        log.append(f"platform deviation in {p}")
for name in sorted(inv):
    log.append(f"gate {name}: present in {inv[name]} items; statuses {dict(status[name])}")
log.append(f"gate 3(a) tree_recall_reproduction present in {recall_tree_up} items (expected 35: T-OQ at U_P); 3(b) ivf_recall_reproduction in {recall_ivf} (expected 140: every F-OQ checkpoint)")
log.append(f"t0_path queries checked: min {min(t0path_q)} max {max(t0path_q)} over {len(t0path_q)} tree items")
for k, v in ex.items():
    log.append(f"gate 4 {k}: items {len(v)}; total sets_differ {sum(x[0] for x in v)}; float_ties {sum(x[1] for x in v)}; not_float_ties {sum(x[2] for x in v)}; max weight diff {max(x[3] for x in v):.3e}")
g = json.load(open(f"{RUN}/gates-a1/gates.json"))
log.append(f"gates-a1: passed {g['passed']} failed {g['failed']}; gate1 checked {g['gates']['gate1_identities']['checkpoints_checked']} draws {g['gates']['gate1_identities']['draws_regenerated']} manifests {g['gates']['gate1_identities']['manifests']}; gate5 {g['gates']['gate5_rehearsal']['passed']}; gate6 {g['gates']['gate6_seeds']['passed']} {g['gates']['gate6_seeds']['checker']['result_line']}")
# tasks
tasks = sorted(glob.glob(f"{RUN}/a1/tasks/*.done.json"))
log.append(f"a1 task done-records: {len(tasks)}")
text = "\n".join(log)
print(text)
open(f"{OUT}/audit_integrity.out.txt", "w").write(text + "\n")
