# ruff: noqa
"""Final R1 audit: NEW cheap rules (this auditor's, written in under an hour), text only. Reported separately; they do not decide a drop here.
Scoring as audit 4: eff = accuracy - 1/k (closed answers; a non-firing rule scores chance); anti = choosing uniformly among the options the rule
did not pick; fitted lookups are fitted on one draw (seed base FIT + level) and scored on another (TEST + level).
usage: python new_rules_final.py <n> <FIT> <TEST>"""
import os, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fgen

WD = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DIRS = ["north", "east", "south", "west"]


def sents(q):
    return [s for s in re.split(r"(?<=[.?])\s+", q) if s]


# ---- knights: lookup on (own statement kind, #others 'X is a knight' about asked, #others 'X is a knave' about asked, asked in own statement)
def kk_feat(q):
    ask = re.search(r"Is (\w+) a knight or a knave\?", q).group(1)
    st = re.findall(r'(\w+) says: "([^"]+?)\.?"', q)
    own = next(s for w, s in st if w == ask)
    kind = re.sub(r"\b[A-Z]\w+\b", "X", own)
    kn = sum(1 for w, s in st if w != ask and s == f"{ask} is a knight")
    kv = sum(1 for w, s in st if w != ask and s == f"{ask} is a knave")
    return (kind, kn, kv, ask in own)


def kk_feat2(q):  # + how many statements mention the asked person at all, and in which forms
    ask = re.search(r"Is (\w+) a knight or a knave\?", q).group(1)
    st = re.findall(r'(\w+) says: "([^"]+?)\.?"', q)
    forms = tuple(sorted(re.sub(r"\b[A-Z]\w+\b", lambda m: "A" if m.group(0) == ask else "X", s) for w, s in st if w != ask and ask in s))
    own = re.sub(r"\b[A-Z]\w+\b", lambda m: "A" if m.group(0) == ask else "X", next(s for w, s in st if w == ask))
    return (own, forms)


# ---- weekday: anchor + signed sum of ALL link offsets (ignores which links lie on the path); anchor + links touching the asked event only
def wk_parse(q):
    links = [m.groups() for m in (re.fullmatch(r"The (.+?) took place (\d+) days? (before|after) the (.+?)\.", s) for s in sents(q)) if m]
    a = re.search(r"The (.+?) took place on a (\w+day)\.", q)
    ask = re.search(r"did the (.+?) take place\?", q).group(1)
    return links, a.group(1), WD.index(a.group(2)), ask


def wk_rules(q):
    links, anc, d0, ask = wk_parse(q)
    tot = sum(int(n) * (1 if d == "after" else -1) for _, n, d, _ in links)
    touch = sum((int(n) * (1 if d == "after" else -1)) * (1 if x == ask else -1) for x, n, d, y in links if ask in (x, y))
    return {"anchor_plus_signed_sum_all_links": WD[(d0 + tot) % 7], "anchor_plus_links_touching_asked": WD[(d0 + touch) % 7]}


# ---- categories with exceptions
def cde_rules(q):
    m = re.search(r"\. ([A-Z]\w+) is an? (\w+)\. Can \1 (\w+)\?", q)
    verb = m.group(3)
    rules = re.findall(r"(?<![\w])An? (\w+) (can|cannot) (\w+)\.", q)
    rv = [(g, c) for g, c, v in rules if v == verb]
    out = {}
    if rv:
        out["first_stated_rule_for_verb"] = "yes" if rv[0][1] == "can" else "no"
        out["last_stated_rule_for_verb"] = "yes" if rv[-1][1] == "can" else "no"
        par = dict(re.findall(r"Every (\w+) is an? (\w+)\.", q))
        g, depth, seen = m.group(2), 0, {}
        while True:
            seen[g] = depth
            if g not in par:
                break
            g = par[g]; depth += 1
        # farthest (least specific) rule on the chain = the rule a reader gets if the exception order is reversed; nearest rule among the first half of the chain only
        on = [(seen[g], c) for g, c in rv if g in seen]
        if on:
            out["rule_nearest_top_of_chain"] = "yes" if max(on)[1] == "can" else "no"
    return out


def cde_feat(q):
    verb = re.search(r"Can [A-Z]\w+ (\w+)\?", q).group(1)
    rules = re.findall(r"(?<![\w])An? (\w+) (can|cannot) (\w+)\.", q)
    return (sum(1 for _, c, v in rules if v == verb and c == "can"), sum(1 for _, c, v in rules if v == verb and c == "cannot"))


# ---- boolean lights: lookup on (initial state of the asked lamp, number of switches wired to it, total presses parity)
def bool_feat(q):
    ask = int(re.search(r"Is lamp (\d+) on", q).group(1))
    m = re.search(r"At the start, (?:lamps (.+?) are on|lamp (\d+) is on)", q)
    on = set(int(x) for x in re.split(r", | and ", m.group(1) or m.group(2))) if m else (set(range(1, 99)) if "all lamps are on" in q else set())
    wired = sum(1 for c, l in re.findall(r"The (\w+) switch toggles lamps? ([\d, and]+?) \(", q) if ask in [int(x) for x in re.split(r", | and ", l)])
    np_ = len(re.search(r"pressed in this order: ([a-z, ]+)\.", q).group(1).split(", "))
    return (ask in on, wired, np_ % 2)


# ---- compass: count left/right/around only (ignore degree turns)
def compass_rules(q):
    m = re.match(r"You are facing (\w+)\. You (.+)\. Which", q)
    d = DIRS.index(m.group(1))
    for c in m.group(2).split(", then "):
        d += {"turn left": -1, "turn right": 1, "turn around": 2}.get(c, 0)
    return {"word_turns_only": DIRS[d % 4]}


# ---- decision tree: follow the root light, then take the commonest action in that subtree
def dtree_rules(q):
    rule = re.search(r"Your rule is: (.+)\. Right now", q).group(1)
    state = dict((n, t == "true") for t, n in re.findall(r"it is (true|false) that the (\w+) light is on", q))
    root = re.match(r"if the (\w+) light is on, then \(", rule).group(1)
    # split the two top-level branches by parenthesis depth
    i = rule.index("then (") + 6; depth = 1; j = i
    while depth:
        depth += {"(": 1, ")": -1}.get(rule[j], 0); j += 1
    a = rule[i:j - 1]; b = rule[j + len(", otherwise ("):-1]
    sub = a if state.get(root) else b
    acts = re.findall(r"\(([a-z ]+)\)", sub)
    c = Counter(acts).most_common()
    top = [x for x, k in c if k == c[0][1]]
    return {"root_then_commonest_action": top}


def opts_of(q, b):
    m = re.search(r"(?:Choose from|Answer) (.+?)\.$", q)
    if b.answer_type in ("yn",) or (m and m.group(1) == "yes or no"):
        return ["yes", "no"]
    if m and "knight or knave" in m.group(1):
        return ["knight", "knave"]
    if "On which day of the week" in q:
        return WD
    if m:
        return [x for x in re.split(r", | or | and ", m.group(1))]
    return None


def score(items, pred):
    eff = anti = 0.0
    for b in items:
        o = opts_of(b.question, b)
        ch = 1 / len(o)
        p = pred(b)
        if p is None:
            eff += ch; anti += ch; continue
        ps = p if isinstance(p, list) else [p]
        eff += sum(x == b.answer for x in ps) / len(ps)
        rest = [x for x in o if x not in ps]
        anti += (b.answer in rest) / len(rest) if rest else ch
    n = len(items); ch = 1 / len(opts_of(items[0].question, items[0]))
    return round(eff / n - ch, 4), round(anti / n - ch, 4)


def lookup(fit, feat):
    tab = defaultdict(Counter)
    for b in fit:
        tab[feat(b.question)][b.answer] += 1
    glob = Counter(b.answer for b in fit).most_common(1)[0][0]
    return lambda b: tab[feat(b.question)].most_common(1)[0][0] if feat(b.question) in tab else glob


n, FIT, TEST = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
L = fgen.lineages()
SPEC = {
    "R1.knights_knaves_r6": {"lookup": {"(own kind, #knight-calls, #knave-calls, self in own)": kk_feat, "(own form, forms mentioning asked)": kk_feat2}},
    "R1.temporal_weekday_shift_r6": {"rules": wk_rules},
    "R1.categories_default_exceptions_r4": {"rules": cde_rules, "lookup": {"(#can, #cannot rules for the verb)": cde_feat}},
    "R1.boolean_lights_r4": {"lookup": {"(asked on at start, #switches wired to it, #presses parity)": bool_feat}},
    "R1.compass_turns": {"rules": compass_rules},
    "R1.conditional_decision_tree_r6": {"rules": dtree_rules},
}
for lid, sp in SPEC.items():
    lin = L[lid]
    rows = defaultdict(list)
    for lv in range(7):
        test = fgen.items(lin, lv, n, TEST)
        if "rules" in sp:
            names = sorted({k for b in test[:50] for k in sp["rules"](b.question)})
            for h in names:
                rows[h].append(score(test, lambda b, h=h: sp["rules"](b.question).get(h)))
        for name, f in sp.get("lookup", {}).items():
            fit = fgen.items(lin, lv, n, FIT)
            pr = lookup(fit, f)
            rows["lookup " + name].append(score(test, pr))
    for h, v in rows.items():
        print(f"{lid:36s} {h[:60]:60s} eff " + " ".join(f"{e:+.3f}" for e, _ in v) + "   anti " + " ".join(f"{a:+.3f}" for _, a in v), flush=True)
