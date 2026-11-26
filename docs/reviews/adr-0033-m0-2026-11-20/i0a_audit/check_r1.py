# ruff: noqa
# ruff: noqa
"""M0-I0a audit: independent re-derivation of R1 answers FROM THE QUESTION TEXT (not the structured
form), for knights_knaves, seating_row and categories_follow. Also reports ambiguity:
- knights/seating: the queried value must be the same in every consistent world (and >= 1 world);
- categories_follow: answer under two semantics, modern (terms may be empty) and Aristotelian
  existential import (every term named in the item is non-empty); disagreement = ambiguous item.
Usage: python3 -I check_r1.py FILE.jsonl [LINEAGE ...]
"""
import itertools, json, re, sys
from collections import Counter


def knights(q):
    stm = re.findall(r'(\w+) says: "([^"]+)"', q)
    who = re.search(r"Is (\w+) a knight or a knave", q).group(1)
    people = sorted({p for p, _ in stm} | set(re.findall(r"\b([A-Z][a-z]+)\b", " ".join(s for _, s in stm))) - {"Each"})
    def truth(s, w):
        m = re.fullmatch(r"(\w+) is a (knight|knave)\.?", s)
        if m: return w[m.group(1)] == (m.group(2) == "knight")
        m = re.fullmatch(r"at least one of (\w+) and (\w+) is a knave\.?", s)
        if m: return (not w[m.group(1)]) or (not w[m.group(2)])
        m = re.fullmatch(r"(\w+) and (\w+) are both knights\.?", s)
        if m: return w[m.group(1)] and w[m.group(2)]
        raise ValueError(s)
    vals = set(); worlds = 0
    for bits in itertools.product((True, False), repeat=len(people)):
        w = dict(zip(people, bits))
        if all(truth(s, w) == w[p] for p, s in stm):
            worlds += 1; vals.add("knight" if w[who] else "knave")
    return vals, worlds


def seating(q):
    m = re.match(r"(.+?) sit in a row of (\d+) seats", q)
    names = re.split(r", | and ", m.group(1)); n = int(m.group(2))
    ask = int(re.search(r"Who sits in seat (\d+)\?", q).group(1))
    body = q[q.index("one person per seat.") + len("one person per seat."):q.index("Who sits")]
    cons = [c.strip() for c in body.split(".") if c.strip()]
    def ok(pos, c):
        if mm := re.fullmatch(r"(\w+) sits in seat (\d+)", c): return pos[mm[1]] == int(mm[2])
        if mm := re.fullmatch(r"(\w+) does not sit in seat (\d+)", c): return pos[mm[1]] != int(mm[2])
        if mm := re.fullmatch(r"(\w+) sits somewhere to the left of (\w+)", c): return pos[mm[1]] < pos[mm[2]]
        if mm := re.fullmatch(r"(\w+) sits somewhere to the right of (\w+)", c): return pos[mm[1]] > pos[mm[2]]
        if mm := re.fullmatch(r"(\w+) sits immediately to the left of (\w+)", c): return pos[mm[1]] + 1 == pos[mm[2]]
        if mm := re.fullmatch(r"(\w+) sits immediately to the right of (\w+)", c): return pos[mm[1]] == pos[mm[2]] + 1
        if mm := re.fullmatch(r"(\w+) and (\w+) sit next to each other", c): return abs(pos[mm[1]] - pos[mm[2]]) == 1
        if mm := re.fullmatch(r"(\w+) and (\w+) do not sit next to each other", c): return abs(pos[mm[1]] - pos[mm[2]]) != 1
        if mm := re.fullmatch(r"(\w+) sits at one of the two ends of the row", c): return pos[mm[1]] in (1, n)
        if mm := re.fullmatch(r"(\w+) does not sit at either end of the row", c): return pos[mm[1]] not in (1, n)
        if mm := re.fullmatch(r"(\w+) sits somewhere between (\w+) and (\w+)", c): return min(pos[mm[2]], pos[mm[3]]) < pos[mm[1]] < max(pos[mm[2]], pos[mm[3]])
        raise ValueError(c)
    vals = set(); worlds = 0
    for perm in itertools.permutations(range(1, n + 1)):
        pos = dict(zip(names, perm))
        if all(ok(pos, c) for c in cons):
            worlds += 1; vals.add([k for k, v in pos.items() if v == ask][0])
    return vals, worlds


def categories(q):
    prem = re.findall(r"(All|No) (\w+) are (\w+)\.", q.split("Does it follow")[0])
    concl = q.split("Does it follow that ")[1].split("?")[0]
    terms = sorted({a for _, a, _ in prem} | {b for _, _, b in prem} | set(re.findall(r"\b([a-z]{5})\b", concl)) - {"every", "follow"})
    T = len(terms); ix = {t: i for i, t in enumerate(terms)}
    def type_ok(s):
        for k, a, b in prem:
            ia, ib = ix[a], ix[b]
            if k == "All" and (s >> ia) & 1 and not (s >> ib) & 1: return False
            if k == "No" and (s >> ia) & 1 and (s >> ib) & 1: return False
        return True
    feas = [s for s in range(1 << T) if type_ok(s)]
    if m := re.fullmatch(r"no (\w+) is an? (\w+)", concl): kind, x, y = "no", m[1], m[2]
    elif m := re.fullmatch(r"every (\w+) is an? (\w+)", concl): kind, x, y = "every", m[1], m[2]
    elif m := re.fullmatch(r"some (\w+) are (\w+)", concl): kind, x, y = "some", m[1], m[2]
    else: raise ValueError(concl)
    X, Y = 1 << ix[x], 1 << ix[y]
    has_xy = any(s & X and s & Y for s in feas)
    has_x_noty = any(s & X and not s & Y for s in feas)
    # modern: models = any subset of feasible types (incl. empty)
    if kind == "no": modern = "yes" if not has_xy else "cannot be determined"
    elif kind == "every": modern = "yes" if not has_x_noty else "cannot be determined"
    else: modern = "no" if not has_xy else "cannot be determined"
    # existential import: every term occurring in the item is non-empty. A model is a set of feasible types
    # covering every term. Conclusion true in all such models / false in all / neither. Search exactly:
    cover_ok = all(any(s >> i & 1 for s in feas) for i in range(T))
    def models_exist(pred_must_hold):
        # does a covering model exist with the given extra requirement on X,Y types?
        # requirement 'none_xy': no type with X&Y; 'none_xnoty': no X&~Y; 'some_xy'; 'some_xnoty'
        allowed = [s for s in feas if not ((pred_must_hold == "none_xy" and s & X and s & Y) or (pred_must_hold == "none_xnoty" and s & X and not s & Y))]
        if pred_must_hold in ("some_xy",): return cover_ok and has_xy  # add an X&Y type to a cover (union of covers is a cover)
        if pred_must_hold in ("some_xnoty",): return cover_ok and has_x_noty
        return all(any(s >> i & 1 for s in allowed) for i in range(T))
    if not cover_ok:
        exist = "PREMISES FORCE AN EMPTY TERM"
    elif kind == "no":
        t_possible, f_possible = models_exist("none_xy"), models_exist("some_xy")
        exist = "yes" if not f_possible else ("no" if not t_possible else "cannot be determined")
    elif kind == "every":
        t_possible, f_possible = models_exist("none_xnoty"), models_exist("some_xnoty")
        exist = "yes" if not f_possible else ("no" if not t_possible else "cannot be determined")
    else:
        t_possible, f_possible = models_exist("some_xy"), models_exist("none_xy")
        exist = "yes" if not f_possible else ("no" if not t_possible else "cannot be determined")
    return modern, exist


if __name__ == "__main__":
    path = sys.argv[1]; want = set(sys.argv[2:])
    stats = Counter(); bad = []
    for line in open(path):
        r = json.loads(line)
        lin = r["lineage"]
        if want and lin not in want: continue
        q, a = r["question"], str(r["answer"]).lower()
        if lin == "R1.knights_knaves":
            vals, w = knights(q)
            ok = vals == {a}; stats[(lin, "agree" if ok else "DISAGREE")] += 1
            if not ok: bad.append((r["id"], a, vals, w))
        elif lin == "R1.seating_row":
            vals, w = seating(q)
            ok = {v.lower() for v in vals} == {a}; stats[(lin, "agree" if ok else "DISAGREE")] += 1
            if not ok: bad.append((r["id"], a, vals, w))
        elif lin == "R1.categories_follow":
            modern, exist = categories(q)
            stats[(lin, "modern agrees" if modern == a else "MODERN DISAGREES")] += 1
            stats[(lin, "existential-import reading agrees" if exist == a else "EXISTENTIAL-IMPORT READING DIFFERS")] += 1
            stats[(lin, f"answer={a}")] += 1
            if exist != a: stats[(lin, f"differs: key={a} vs exist={exist}")] += 1
            if modern != a: bad.append((r["id"], a, modern, exist))
    for k in sorted(stats): print(k, stats[k])
    for b in bad[:10]: print("BAD", b)
