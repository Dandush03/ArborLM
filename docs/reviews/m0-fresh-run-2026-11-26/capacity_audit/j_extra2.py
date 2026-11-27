"""Item 2 extras on the audit-label sample: (a) R2.caesar_shift: invented words renamed one-to-one (as if they were
names): does the second solver's answer change, and would the key without the exception merge items with different
answers? (b) perturbation: one digit changed, or one non-name word changed, must change the key; (c) totals of the
rename test of c_names2.json."""
import collections, json, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a_common import SCR, load_solvers
from studies.m0 import vocab
from studies.m0.registration import distinct_key as dk

rows = collections.defaultdict(list)
for line in open(f"{SCR}/work/sample_items.jsonl"):
    r = json.loads(line); rows[r["id"]].append(r)
sol = load_solvers()["R2.caesar_shift"]
rng = random.Random(7)
changed = 0; n = 0; merged_diff = 0
by_key = collections.defaultdict(set)
for r in rows["R2.caesar_shift"]:
    words = sorted(set(re.findall(r"[a-z]+", r["question"].split("'")[1])))
    pseudo = [w for w in words if w in set(vocab.PSEUDO)]
    if not pseudo:
        continue
    n += 1
    image = rng.sample(vocab.PSEUDO, len(pseudo))
    mp = dict(zip(pseudo, image))
    inner = r["question"].split("'")[1]
    new_inner = " ".join(mp.get(w, w) for w in inner.split(" "))
    q2 = r["question"].replace("'" + inner + "'", "'" + new_inner + "'")
    st2 = json.loads(json.dumps(r["structured"]).replace(inner, new_inner))
    a2 = sol(q2, st2)
    changed += a2 != r["answer"]
    # the key WITHOUT the exception (invented words relabelled), on the original item and on the renamed one
    k_no_exc = dk.relabel_text(r["question"], frozenset())
    k2_no_exc = dk.relabel_text(q2, frozenset())
    if k_no_exc == k2_no_exc and a2 != r["answer"]:
        merged_diff += 1
print(f"(a) caesar_shift: {n} items with invented words renamed one-to-one; second solver's answer changed in {changed}; "
      f"key WITHOUT the exception equal for original and renamed item while the answers differ in {merged_diff}")

pert_items = 0; pert_same = 0
for lid, rs in sorted(rows.items()):
    if lid.startswith("C1."):
        continue  # the C1 key renders the program from `structured`; a question-only edit is not an item (see report)
    for r in rng.sample(rs, 40):
        q = r["question"]
        ds = [m.start() for m in re.finditer(r"[0-9]", q)]
        if ds:
            i = rng.choice(ds)
            q2 = q[:i] + str((int(q[i]) + 1) % 10) + q[i + 1:]
            pert_items += 1
            pert_same += dk.item_key(lid, q2, r["structured"]) == dk.item_key(lid, q, r["structured"])
        # a non-name word: the first word of the question replaced by a word not in any list
        q3 = re.sub(r"^[A-Za-z]+", "Zzqx", q, count=1)
        if q3 != q:
            pert_items += 1
            try:
                pert_same += dk.item_key(lid, q3, r["structured"]) == dk.item_key(lid, q, r["structured"])
            except ValueError:
                pass
print(f"(b) perturbations (text evaluations; C1 skipped): {pert_items} single-digit or first-word changes; key unchanged in {pert_same}")

d = json.load(open(f"{SCR}/deliver/c_names2.json"))
tot = collections.Counter()
for lid, r in d.items():
    tot["items"] += r["items"]; tot["my_relabel_differs"] += r["my_relabel_differs"]
    tot["renamed_items"] += r["rename"]["items_with_names"]; tot["key_changed"] += r["rename"]["key_changed"]
    tot["answer_changed"] += r["rename"]["answer_changed"]; tot["same_key_diff_answer"] += r["n_key_repeats_with_different_answers"]
    tot["lineages_with_names"] += r["rename"]["items_with_names"] > 0
print("(c) totals:", dict(tot))
