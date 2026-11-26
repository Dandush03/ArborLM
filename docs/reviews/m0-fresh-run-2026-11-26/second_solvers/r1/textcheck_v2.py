"""Cross-check: parse every question TEXT with strict per-template regexes into a
structured form of my own, (a) compare it with the fixture `structured`, (b) solve
from the text-derived form with the same solver functions, (c) report every
sentence that fits no template. Also boundary / alternative-reading diagnostics."""
import json, os, re, sys
from collections import Counter
from itertools import combinations
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import solver2_r1 as S

D = "/Users/daniellaloush/dandush03/ArborLM/experiments/_scratch/m0_second_solver_fixtures_20261126/R1/"
NUMW = {}

def sents(q):
    return re.split(r'(?<=[.?])\s+(?=[A-Z0-9])', q.strip())

def lst(t):
    # "a, b and c" / "a" / "a and b"
    t = t.strip()
    if " and " in t:
        head, last = t.rsplit(" and ", 1)
        return [x.strip() for x in head.split(",")] + [last.strip()]
    return [x.strip() for x in t.split(",")]

def P_lights(q):
    st = {"switches": {}, "presses": None}
    tmpl = Counter()
    for s in sents(q):
        if m := re.fullmatch(r"There are (\d+) lamps numbered 1 to (\d+)\.", s):
            st["lamps"] = int(m[1]); assert m[1] == m[2]; tmpl["count"] += 1
        elif m := re.fullmatch(r"At the start, lamps? ([\d, and]+) (?:is|are) on, and all the lamps not named here are off\.", s):
            st["on"] = [int(x) for x in lst(m[1])]; tmpl["start:some on"] += 1
        elif s == "At the start, all lamps are off.":
            st["on"] = []; tmpl["start:all off"] += 1
        elif s == "At the start, all lamps are on.":
            st["on"] = "all"; tmpl["start:all on"] += 1
        elif m := re.fullmatch(r"The (\w+) switch toggles lamps? ([\d, and]+) \(each one goes from on to off or from off to on\)\.", s):
            st["switches"][m[1]] = [int(x) for x in lst(m[2])]; tmpl["switch"] += 1
        elif m := re.fullmatch(r"The switches are pressed in this order: ([\w, ]+)\.", s):
            st["presses"] = [x.strip() for x in m[1].split(",")]; tmpl["presses"] += 1
        elif m := re.fullmatch(r"Is lamp (\d+) on at the end\?", s):
            st["ask"] = int(m[1]); tmpl["ask"] += 1
        elif s == "Answer yes or no.":
            tmpl["answer"] += 1
        else:
            raise ValueError("unmatched: " + s)
    on = range(1, st["lamps"] + 1) if st["on"] == "all" else st["on"]
    st["initial"] = [1 if i + 1 in on else 0 for i in range(st["lamps"])]
    del st["on"]
    return st, tmpl

def P_cat(q):
    isa, rules, tmpl = {}, [], Counter()
    for s in sents(q):
        if m := re.fullmatch(r"Every (\w+) is an? (\w+)\.", s):
            assert m[1] not in isa; isa[m[1]] = m[2]; tmpl["isa"] += 1
        elif m := re.fullmatch(r"An? (\w+) (can|cannot) (\w+)\.", s):
            rules.append([m[1], m[3], m[2] == "can"]); tmpl["rule"] += 1
        elif s == "When two rules about the same thing disagree, the rule about the smaller (more specific) group wins.":
            tmpl["specificity"] += 1
        elif m := re.fullmatch(r"([A-Z]\w+) is an? (\w+)\.", s):
            member, g0 = m[1], m[2]; tmpl["member"] += 1
        elif m := re.fullmatch(r"Can ([A-Z]\w+) (\w+)\?", s):
            assert m[1] == member; verb = m[2]; tmpl["ask"] += 1
        elif s == "Answer yes or no.":
            tmpl["answer"] += 1
        else:
            raise ValueError("unmatched: " + s)
    chain = [g0]
    while chain[-1] in isa:
        chain.append(isa[chain[-1]])
    extra = set(isa) | set(isa.values())
    extra -= set(chain)
    if extra:
        tmpl["groups off the member's chain"] += 1
    return {"chain": chain, "rules": rules, "member": member, "verb": verb}, tmpl

def P_compass(q):
    tmpl = Counter(); st = {}
    m = re.fullmatch(r"You are facing (north|east|south|west)\. You (.+)\. Which direction are you facing now\? Answer north, east, south or west\.", q)
    if not m: raise ValueError("unmatched: " + q)
    st["start"] = m[1]; seq = []
    for p in m[2].split(", then "):
        if mm := re.fullmatch(r"walk (\d+) steps?", p): seq.append(["walk", int(mm[1])]); tmpl["walk"] += 1
        elif p in ("turn left", "turn right", "turn around"): seq.append(["turn", p[5:]]); tmpl[p] += 1
        elif mm := re.fullmatch(r"turn (\d+) degrees (clockwise|counterclockwise)", p):
            seq.append(["turn", ("cw" if mm[2] == "clockwise" else "ccw") + mm[1]]); tmpl["turn %s %s" % (mm[1], mm[2])] += 1
        else: raise ValueError("unmatched step: " + p)
    st["seq"] = seq
    return st, tmpl

def P_thr(q):
    m = re.fullmatch(r"A committee votes on a motion\. (.+)\. The motion passes if the total weight of the members who vote yes, minus the total weight of the members who vote no, is at least (-?\d+) \(members who abstain count for neither side\)\. The votes: (.+)\. Does the motion pass\? Answer yes or no\.", q)
    if not m: raise ValueError("unmatched: " + q)
    members = [[a, int(b)] for a, b in (re.fullmatch(r"(\w+) has weight (\d+)", x).groups() for x in m[1].split(", "))]
    votes = dict(re.fullmatch(r"(\w+) (yes|no|abstain)", x).groups() for x in m[3].split(", "))
    return {"members": members, "votes": votes, "margin": int(m[2])}, Counter(["single template"])

def P_ex(q):
    rates, tmpl = [], Counter()
    for s in sents(q):
        if m := re.fullmatch(r"(\d+) units of ([\w-]+) are worth the same as (\d+) units of ([\w-]+)\.", s):
            rates.append([int(m[1]), m[2], int(m[3]), m[4]]); tmpl["rate"] += 1
        elif m := re.fullmatch(r"How many units of ([\w-]+) are worth the same as (\d+) units of ([\w-]+)\?", s):
            y, n, x = m[1], int(m[2]), m[3]; tmpl["ask"] += 1
        else: raise ValueError("unmatched: " + s)
    return {"rates": rates, "x": x, "y": y, "n": n}, tmpl

KK = [(r'(\w+) is a knight\.', "is_knight"), (r'(\w+) is a knave\.', "is_knave"),
      (r'(\w+) and (\w+) are both knights\.', "both_knights"),
      (r'at least one of (\w+) and (\w+) is a knave\.', "some_knave"),
      (r'(\w+) and (\w+) are of the same kind\.', "same_kind"),
      (r'exactly one of (\w+) and (\w+) is a knight\.', "differ")]
def P_kk(q):
    pre = "Each person is either a knight, who always tells the truth, or a knave, who always lies. "
    assert q.startswith(pre); body = q[len(pre):]
    m = re.fullmatch(r'(.*) Is (\w+) a knight or a knave\? Answer knight or knave\.', body)
    if not m: raise ValueError("unmatched: " + body)
    says = re.findall(r'(\w+) says: "([^"]+)"', m[1])
    assert " ".join('%s says: "%s"' % t for t in says) == m[1], "unparsed residue"
    people = [p for p, _ in says]; stm = []; tmpl = Counter()
    for p, t in says:
        for rx, kind in KK:
            if mm := re.fullmatch(rx, t):
                stm.append([kind, [people.index(x) for x in mm.groups()]]); tmpl[kind] += 1; break
        else: raise ValueError("unmatched statement: " + t)
    return {"people": people, "statements": stm, "who": people.index(m[2])}, tmpl

def P_grid(q):
    tmpl = Counter(); rows = []
    for s in sents(q):
        if m := re.fullmatch(r"A map has (\d+) rows \(row 1 is the northernmost\) and (\d+) columns \(column 1 is the westernmost\)\.", s):
            R, C = int(m[1]), int(m[2]); tmpl["header"] += 1
        elif m := re.fullmatch(r"Row (\d+): (.+)\.", s):
            assert int(m[1]) == len(rows) + 1
            rows.append([None if x == "wall" else x for x in m[2].split(", ")]); tmpl["row"] += 1
        elif m := re.fullmatch(r"You start at (.+)\.", s): start = m[1]; tmpl["start"] += 1
        elif m := re.fullmatch(r"You move (.+), one cell each time\.", s):
            moves = m[1].split(", then "); assert all(x in S._STEP for x in moves); tmpl["moves"] += 1
        elif s == "A move into a wall or off the map does nothing.": tmpl["wallrule"] += 1
        elif s == "Which place do you end on?": tmpl["ask"] += 1
        elif m := re.fullmatch(r"Choose from (.+)\.", s): choices = lst(m[1]); tmpl["choices"] += 1
        else: raise ValueError("unmatched: " + s)
    assert len(rows) == R and all(len(r) == C for r in rows)
    pos = [(i, j) for i, r in enumerate(rows) for j, x in enumerate(r) if x == start]
    assert len(pos) == 1, "start name not unique"
    names = sorted(x for r in rows for x in r if x)
    assert len(names) == len(set(names)), "duplicate place names"
    assert sorted(choices) == names, "choices != all places"
    return {"grid": rows, "start": list(pos[0]), "moves": moves,
            "convention": "row 1 is the northernmost, column 1 is the westernmost", "_choices": choices}, tmpl

def P_swap(q):
    tmpl = Counter(); ops = []
    for s in sents(q):
        if m := re.fullmatch(r"At the start (.+)\.", s):
            hold = dict(re.fullmatch(r"(\w+) holds the ([\w-]+)", x).groups() for x in m[1].split(", ")); tmpl["start"] += 1
        elif m := re.fullmatch(r"(\w+) and (\w+) swap what they are holding\.", s):
            ops.append(["swap", m[1], m[2]]); tmpl["swap"] += 1
        elif m := re.fullmatch(r"(\w+) hands their item to (\w+), (\w+) hands theirs to (\w+), and (\w+) hands theirs to (\w+), all at once\.", s):
            a, b, b2, c, c2, a2 = m.groups(); assert (a, b, c) == (a2, b2, c2)
            ops.append(["rotate", a, b, c]); tmpl["rotate"] += 1
        elif m := re.fullmatch(r"What is (\w+) holding at the end\?", s): who = m[1]; tmpl["ask"] += 1
        elif m := re.fullmatch(r"Choose from (.+)\.", s): choices = lst(m[1]); tmpl["choices"] += 1
        else: raise ValueError("unmatched: " + s)
    assert sorted(choices) == sorted(hold.values())
    return {"hold": hold, "ops": ops, "who": who, "_choices": choices}, tmpl

def P_wd(q):
    tmpl = Counter(); links = []
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for s in sents(q):
        if m := re.fullmatch(r"(The .+) took place on a (\w+day)\.", s):
            anchor = [m[1][0].lower() + m[1][1:], m[2]]; tmpl["anchor"] += 1
        elif m := re.fullmatch(r"(The .+) took place (\d+) days? (after|before) (the .+)\.", s):
            a = m[1][0].lower() + m[1][1:]; n = int(m[2])
            links.append([a, m[4], n] if m[3] == "after" else [m[4], a, n]); tmpl["link " + m[3] + (" 1 day" if n == 1 else "")] += 1
        elif m := re.fullmatch(r"On which day of the week did (the .+) take place\?", s):
            ask = m[1]; tmpl["ask"] += 1
        else: raise ValueError("unmatched: " + s)
    return {"days": days, "anchor": anchor, "links": links, "ask": ask}, tmpl

def P_venn(q):
    tmpl = Counter(); sizes = {}; pairs = {}; triples = {}; quad = None
    m = re.fullmatch(r"Among (\d+) people, (.+)\. Each person is counted once in each number that applies to them\. How many of the people are in (none|exactly one|exactly two|at least two) of these groups\?", q)
    if not m: raise ValueError("unmatched: " + q)
    total = int(m[1]); ask = {"none": "none", "exactly one": "one", "exactly two": "two", "at least two": "atleast_two"}[m[3]]
    tmpl["ask " + m[3]] += 1
    groups = []
    for p in m[2].split("; "):
        if mm := re.fullmatch(r"(\d+) people are in the (\w+) group", p):
            sizes[mm[2]] = int(mm[1]); groups.append(mm[2])
        elif mm := re.fullmatch(r"(\d+) are in both the (\w+) and the (\w+) groups", p):
            pairs[mm[2] + "|" + mm[3]] = int(mm[1])
        elif mm := re.fullmatch(r"(\d+) are in all of the (\w+), (\w+) and (\w+) groups", p):
            triples["|".join(mm.groups()[1:])] = int(mm[1])
        elif mm := re.fullmatch(r"(\d+) are in all four groups", p):
            quad = int(mm[1])
        else: raise ValueError("unmatched part: " + p)
    tmpl["%d groups" % len(groups)] += 1
    triple = next(iter(triples.values())) if len(groups) == 3 else None
    return {"total": total, "groups": groups, "sizes": sizes, "pairs": pairs, "triples": triples,
            "quad": quad, "triple": triple, "ask": ask}, tmpl

PARSERS = {"R1.boolean_lights_r4": P_lights, "R1.categories_default_exceptions_r4": P_cat,
           "R1.compass_turns": P_compass, "R1.conditional_threshold_rule_r4": P_thr,
           "R1.equivalence_exchange_rates_r6": P_ex, "R1.knights_knaves_r6": P_kk,
           "R1.spatial_grid_walk_r5": P_grid, "R1.swap_tracking_r5": P_swap,
           "R1.temporal_weekday_shift_r6": P_wd, "R1.venn_counting_r5": P_venn}

ans = {}
for l in open(os.path.join(HERE, "answers_r1.jsonl")):
    r = json.loads(l); ans[(r["id"], r["level"], r["index"])] = r["answer"]

for lin, P in PARSERS.items():
    T = Counter(); mism = 0; disagree = 0; fails = 0
    for line in open(D + lin + "/fixtures.jsonl"):
        r = json.loads(line); key = (lin, r["level"], r["index"])
        try:
            st, t = P(r["question"])
        except Exception as e:
            fails += 1; print("PARSEFAIL", key, e); continue
        T.update(t)
        ref = r["structured"]
        cmp_ = {k: v for k, v in st.items() if not k.startswith("_")}
        for k, v in cmp_.items():
            rv = ref.get(k)
            if lin == "R1.equivalence_exchange_rates_r6" and k == "rates": pass
            if v != rv:
                mism += 1; print("FIELD MISMATCH", key, k, v, "vs", rv)
        missing = set(ref) - set(cmp_) - {"items", "lamps"}
        if lin == "R1.equivalence_exchange_rates_r6":
            its = {x for p, a, q, b in st["rates"] for x in (a, b)}
            if sorted(its) != sorted(ref["items"]): mism += 1; print("ITEMS MISMATCH", key)
            missing -= {"items"}
        if missing: print("NOT PARSED FROM TEXT", key, missing)
        a_text = S.SOLVERS[lin](r["question"], {**ref, **cmp_})
        if a_text != ans[key]: disagree += 1; print("TEXT/STRUCT ANSWER DIFF", key)
        if "_choices" in st and ans[key] not in st["_choices"]: print("ANSWER NOT IN CHOICES", key)
    print("==", lin, "parsefail", fails, "field mismatches", mism, "answer diffs", disagree)
    for k, v in sorted(T.items()): print("   template", repr(k), v)
