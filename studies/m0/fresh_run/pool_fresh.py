# ruff: noqa: E501
"""The pooling script of the M0 fresh run (ADR-0033 addendum 1, section 4A, stage 1S point 9 (v)). One script for all four evaluations.

Standard library only; exact arithmetic (fractions.Fraction), nothing is rounded; it prints no figure (only file names and, on a stop, the names
of the unit and lineage). What it does is defined by points 2, 6, 7, 8 and 11 of stage 1S; where this file and the approved text disagree the
text governs.

    python3 -I pool_fresh.py --plan run_plan.json --survivors survivor_list_of_record.json --class-table addendum1_rev7_uncounted_rules.json \
        --amendments amendment_list.json --field-table field_table.json --out OUT_DIR --expect-plan-sha256 H --expect-field-table-sha256 H \
        --expect-amendment-sha256 H [--seed-set run|dry] [--dir-override UNIT:SEEDSET=DIR ...]

Exit status: 0 the files were written (lineages may be dropped: that is a result, not an error); 3 an engineering stop of point 2 (a lineage that a
unit's output must contain has no row, or a line or field cannot be read): only the unit and the lineage (or file or field) are named, on stderr, and
no figure file is written; 4 an input cannot be read or does not match its recorded hash; 2 a usage error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from typing import Any

BOUND = Fraction(15, 100)
LEVELS = list(range(7))
CLASS_TABLE_SHA256 = "ccea7d78754480830f3887d27ac808e207c60ef4c4a444e47fe6a3fc4c2cd24d"
UNIT_ORDER = ["R1a", "R1b", "R1c", "R2a", "R2b", "M1a", "M1b", "M1c", "C1a", "C1b", "C1c"]
EVALS = ["R1", "R2", "M1", "C1"]
M1_PREFIX = {"own": "im:", "a4": "", "a3": "a3:"}  # point 6, K7: a key of own takes im:, a key of a3 takes a3:, a key of a4 is as written
R1C_VALUES = 7
BRACKET = re.compile(r"^([^\[\]]+)\[[^\[\]]*\]$")  # R-56: an M1a key of the form name[...]
ERROR_SHAPES = ("RULE_ERROR", "PARSE_FAIL")  # shapes that the C1 scripts write for an item they could not process: error markers, not rules (point 6)


class Stop(Exception):
    """An engineering stop (point 2 'what each output must contain', and unreadable lines): only the unit and the lineage or file are named."""

    def __init__(self, unit: str, what: str = "", lineage: str | None = None) -> None:
        super().__init__(unit)
        self.unit, self.what, self.lineage = unit, what, lineage


class InputError(Exception):
    pass


# ------------------------------------------------------------------------------------------------ small exact helpers
def frac_str(x: Fraction) -> str:
    return f"{x.numerator}/{x.denominator}"


def dec_str(x: Fraction, places: int = 12) -> str:
    """A display decimal of an exact fraction (the fraction string is the record)."""
    with localcontext() as ctx:
        ctx.prec = 60
        d = (Decimal(x.numerator) / Decimal(x.denominator)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
    return format(d, "f")


def fj(x: Fraction | None) -> dict[str, str] | None:
    return None if x is None else {"fraction": frac_str(x), "decimal_12dp": dec_str(x)}


def fr(x: Any, what: str = "") -> Fraction:
    if isinstance(x, bool) or x is None or isinstance(x, str):
        raise InputError(f"not a number: {what}")
    return Fraction(x)


def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _no_constant(s: str) -> Any:
    raise InputError("a JSON constant (NaN or Infinity) in an output")


def jload(path: str) -> Any:
    """JSON with every written decimal read exactly (as a Fraction)."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f, parse_float=Fraction, parse_constant=_no_constant)
    except (OSError, ValueError) as e:  # JSONDecodeError is a ValueError
        raise InputError(f"cannot read {path}: {type(e).__name__}") from e


def jlines(path: str) -> list[Any]:
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    out.append(json.loads(line, parse_float=Fraction, parse_constant=_no_constant))
    except (OSError, ValueError) as e:
        raise InputError(f"cannot read {path}: {type(e).__name__}") from e
    return out


def unc(decimals: int) -> Fraction:
    """Half a unit of the last decimal of a figure written rounded to that many decimals (point 7)."""
    return Fraction(1, 2 * 10**decimals)


# ------------------------------------------------------------------------------------------------ the field table
class FieldTable:
    def __init__(self, data: dict[str, Any]) -> None:
        self.forms = data["forms"]

    def scope(self, form: str, scope: str) -> dict[str, Any]:
        return self.forms[form]["scopes"][scope]  # type: ignore[no-any-return]

    def check(self, unit: str, form: str, scope: str, keys: Any, lineage: str | None = None) -> None:
        s = self.scope(form, scope)
        for k in keys:
            if k not in s:
                raise Stop(unit, f"field not in the field table: {form}.{scope}.{k}", lineage)

    def names(self, form: str, scope: str, role: str) -> list[str]:
        return sorted(k for k, v in self.scope(form, scope).items() if v["status"] == "read" and v["role"] == role)

    def name(self, form: str, scope: str, role: str) -> str:
        n = self.names(form, scope, role)
        if len(n) != 1:
            raise InputError(f"field table: {form}.{scope} must have exactly one field with role {role}")
        return n[0]

    def is_read(self, form: str, scope: str, field: str) -> bool:
        return field in self.scope(form, scope) and self.scope(form, scope)[field]["status"] == "read"

    def decimals(self, form: str, scope: str, role: str) -> int:
        d = {self.scope(form, scope)[n].get("decimals") for n in self.names(form, scope, role)}
        d.discard(None)
        if len(d) != 1:
            raise InputError(f"field table: no single decimals for {form}.{scope} role {role}")
        return int(d.pop())

    def field_decimals(self, form: str, scope: str, field: str) -> int:
        return int(self.scope(form, scope)[field]["decimals"])

    def report_fields(self, form: str, scope: str) -> list[str]:
        """Fields that are written into the report only (R-57: rates within one shape); they enter no decision."""
        return sorted(k for k, v in self.scope(form, scope).items() if v["status"] == "report_only")

    def not_rule_keys(self, form: str, scope: str) -> set[str]:
        """Names, in a rule map, that are not rules (not read as rules, or reported only)."""
        return {k for k, v in self.scope(form, scope).items() if v["status"] in ("not_read", "report_only")}


# ------------------------------------------------------------------------------------------------ the class table (point 8)
def r1_bare(h: str) -> str:
    return h.split(":", 1)[1] if h.startswith(("a3:", "a4:")) else h


def r1_stem(lid: str) -> str:
    return re.sub(r"_r\d+$", "", lid.split(".", 1)[1])


def m1_stem(lid: str) -> str:
    s = lid.split(".", 1)[1]
    for suf in ("_r4", "_r3", "_r2"):
        s = s.removesuffix(suf)
    return s


def r2_stem(lid: str) -> str:
    return lid.split(".", 1)[1]


class ClassTable:
    """A rule is uncounted iff it matches an entry of the table in the unit and for the lineage the entry names, or is on the amendment list."""

    def __init__(self, data: dict[str, Any], amendments: dict[str, Any]) -> None:
        self.d = data
        self.units = {ev: set(data[ev]["units"]) for ev in EVALS}
        self.r2_entries = sorted(enumerate(data["R2"]["entries"]), key=lambda t: (t[1]["order"], t[0]))
        self.r2_new = data["R2"]["new_rules"]["entries"]
        self.shape_dependent = sorted({e["text"] for e in data["R2"]["entries"] if "shape" in e})
        self.amend = [(e["unit"], e["lineage"], e["rule"]) for e in amendments.get("entries", [])]

    def amendment(self, unit: str, lineage: str, rule: str) -> str | None:
        for u, x, r in self.amend:
            if (u, x, r) == (unit, lineage, rule):
                return f"amendment list: unit {u}, lineage {x}, rule {r}"
        return None

    def r1(self, unit: str, lineage: str, rule: str) -> str | None:
        if unit not in self.units["R1"]:
            return None
        b, st = r1_bare(rule), r1_stem(lineage)
        for e in self.d["R1"]["entries"]:
            if e["rule"] == b and (e["lineage_stems"] == "every R1 lineage" or st in e["lineage_stems"]):
                return f"class table R1 {e['label']}: {e['rule']} ({e['match']}; lineages: {e['lineage_stems'] if isinstance(e['lineage_stems'], str) else ','.join(e['lineage_stems'])})"
        return None

    def r2(self, unit: str, lineage: str, rule: str, level: int, shape: str | None) -> str | None:
        if unit not in self.units["R2"]:
            return None
        if rule.startswith("[NEW] "):  # classed by the entries under new_rules only
            for e in self.r2_new:
                if e["rule"] == rule and e["lineage_stem"] == r2_stem(lineage):
                    return f"class table R2 new rule {e['label']}: {e['rule']} (lineage {e['lineage_stem']})"
            return None
        for _, e in self.r2_entries:  # klass() clauses applied in order; the first that matches decides
            m, t = e["match"], e["text"]
            if m == "name contains":
                hit = t in rule
            elif m == "name equal":
                hit = rule == t
            elif m == "name equal, and shape equal":
                hit = rule == t and shape == e["shape"]
            elif m == "name equal, and level 0":
                hit = rule == t and level == 0
            elif m == "name starts with":
                hit = rule.startswith(t)
            else:
                raise InputError(f"class table: unknown R2 match kind {m}")
            if hit:
                return f"class table R2 {e['label']} (order {e['order']}, {m}): {t}"
        return None

    def m1(self, unit: str, lineage: str, rule: str) -> str | None:
        if unit not in self.units["M1"]:
            return None
        st = m1_stem(lineage)
        for e in self.d["M1"]["entries"]:
            if e["lineage_stem"] == st and e["rule"] == rule:
                return f"class table M1 {e['label']}: {e['rule']} (lineage stem {e['lineage_stem']})"
        return None

    def c1(self, unit: str, class_source: str, rule: str, is_measure: bool) -> str | None:
        if unit not in self.units["C1"]:
            return None
        for e in self.d["C1"]["entries"]:
            if e["source"].split(" (")[0] != class_source:
                continue
            if e["match"] == "measure equal":
                hit = is_measure and e["text"] == rule
            else:
                hit = (not is_measure) and e["text"] == rule
            if hit:
                return f"class table C1 {e['label']}: {e['text']} (source {e['source']})"
        return None


# ------------------------------------------------------------------------------------------------ the registry of rows
class Row:
    __slots__ = ("unit", "source", "class_source", "lineage", "level", "rule", "shape", "reading", "answer_type", "kind", "base", "base_group",
                 "u", "unnamed", "gkey", "nums", "dens", "alt_nums", "is_measure", "extra")

    def __init__(self, unit: str, source: str, class_source: str, lineage: str, level: int, rule: str, shape: str | None, reading: str,
                 answer_type: str | None, kind: str, base: Fraction, base_group: tuple[Any, ...] | None, u: Fraction, unnamed: str,
                 gkey: tuple[Any, ...], is_measure: bool = False) -> None:
        self.unit, self.source, self.class_source, self.lineage, self.level, self.rule = unit, source, class_source, lineage, level, rule
        self.shape, self.reading, self.answer_type, self.kind, self.base, self.base_group = shape, reading, answer_type, kind, base, base_group
        self.u, self.unnamed, self.gkey, self.is_measure = u, unnamed, gkey, is_measure
        self.nums: dict[str, Fraction] = {}
        self.dens: dict[str, Fraction] = {}
        self.alt_nums: dict[str, Fraction] = {}
        self.extra: dict[str, Any] = {}

    def key(self) -> tuple[Any, ...]:
        return (UNIT_ORDER.index(self.unit), self.source, self.lineage, self.level, self.rule, self.shape or "", self.reading, self.answer_type or "")


class Registry:
    def __init__(self, seeds: list[str]) -> None:
        self.seeds = seeds
        self.rows: dict[tuple[Any, ...], Row] = {}
        self.items: dict[tuple[Any, ...], dict[str, Fraction]] = defaultdict(dict)  # group -> seed -> items (smallest written count)
        self.base_seed: dict[tuple[Any, ...], dict[str, tuple[Fraction, Fraction]]] = defaultdict(dict)
        self.present: dict[tuple[str, str], dict[str, dict[str, set[int]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        self.item_diffs: list[dict[str, Any]] = []
        self.item_diff_seen: set[tuple[Any, ...]] = set()
        self.item_disagree: list[dict[str, Any]] = []
        self.exact_data: dict[tuple[str, str, str, str], dict[str, dict[int, tuple[Any, Any, Any]]]] = defaultdict(lambda: defaultdict(dict))
        self.fallbacks: list[dict[str, Any]] = []
        self.notes: dict[str, Any] = defaultdict(int)
        self.mixed_answer_types: set[tuple[str, str, str, int]] = set()
        self.m1_collisions: set[tuple[str, str, str, int, str]] = set()
        self.shape_rates: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = defaultdict(dict)  # R-57: rates within one shape, reported only

    def row(self, unit: str, source: str, class_source: str, lineage: str, level: int, rule: str, shape: str | None, reading: str,
            answer_type: str | None, kind: str, base: Fraction, base_group: tuple[Any, ...] | None, u: Fraction, unnamed: str,
            gkey: tuple[Any, ...], is_measure: bool = False) -> Row:
        k = (unit, source, lineage, level, rule, shape, reading, answer_type)
        r = self.rows.get(k)
        if r is None:
            r = self.rows[k] = Row(unit, source, class_source, lineage, level, rule, shape, reading, answer_type, kind, base, base_group, u, unnamed, gkey, is_measure)
        return r

    def put(self, row: Row, seed: str, num: Fraction, den: Fraction) -> None:
        if seed in row.nums:
            raise InputError(f"duplicate row: {row.unit} {row.lineage} {row.rule}")
        row.nums[seed], row.dens[seed] = num, den

    def shape_rate(self, key: tuple[Any, ...], seed: str, vals: dict[str, Any]) -> None:
        self.shape_rates[key][seed] = vals

    def set_items(self, g: tuple[Any, ...], seed: str, n: Fraction) -> None:
        cur = self.items[g].get(seed)
        if cur is not None and cur != n:
            self.item_disagree.append({"group": [str(x) for x in g], "seed": seed, "counts": sorted({str(cur), str(n)})})
        self.items[g][seed] = n if cur is None else min(cur, n)


# ------------------------------------------------------------------------------------------------ readers, one per output form
class Ctx:
    def __init__(self, plan: dict[str, Any], ft: FieldTable, ct: ClassTable, reg: Registry, seed_set: str, seeds: list[str], overrides: dict[tuple[str, str], str],
                 survivors: dict[str, list[str]]) -> None:
        self.plan, self.ft, self.ct, self.reg, self.seed_set, self.seeds, self.overrides, self.survivors = plan, ft, ct, reg, seed_set, seeds, overrides, survivors
        self.plan_items: dict[str, int] = {u: plan["units"][u]["items_per_level"]["dry" if seed_set == "dry" else "run"] for u in plan["units"]}

    def unit_dir(self, unit: str, seed: str) -> str:
        if (unit, seed) in self.overrides:
            return self.overrides[(unit, seed)]
        return str(self.plan["units"][unit]["runs"][seed]["output_dir"])


def level_of(unit: str, key: Any, lineage: str | None) -> int:
    try:
        v = int(key)
    except (TypeError, ValueError) as e:
        raise Stop(unit, f"a level key that is not an integer: {key!r}", lineage) from e
    if v not in LEVELS:
        raise Stop(unit, f"a level outside 0 to 6: {v}", lineage)
    return v


def note_items(c: Ctx, unit: str, source: str, lineage: str, seed: str, level: int, n: Fraction) -> None:
    if n != c.plan_items[unit]:
        k = (unit, source, lineage, seed, level)
        if k not in c.reg.item_diff_seen:
            c.reg.item_diff_seen.add(k)
            c.reg.item_diffs.append({"unit": unit, "source": source, "lineage": lineage, "seed": seed, "level": level,
                                     "items": int(n) if n.denominator == 1 else frac_str(n), "plan_items": c.plan_items[unit]})


def read_r1_rows(c: Ctx, unit: str, spec: dict[str, Any], seed: str, d: str) -> None:
    ft, reg = c.ft, c.reg
    form, sc = "r1_rows", "row"
    f_l, f_v, f_h, f_n = ft.name(form, sc, "lineage_id"), ft.name(form, sc, "level"), ft.name(form, sc, "rule_name"), ft.name(form, sc, "items")
    f_eff, f_anti = ft.name(form, sc, "excess_eff"), ft.name(form, sc, "excess_anti")
    f_fired, f_acc = ft.name(form, sc, "exact_listing_fired"), ft.name(form, sc, "exact_listing_acc")
    u_eff, u_anti = unc(ft.field_decimals(form, sc, f_eff)), unc(ft.field_decimals(form, sc, f_anti))
    idm = spec["id_map"]
    for kind, ks in sorted(spec["kinds"].items()):
        pat = re.compile("^" + re.escape(ks["glob"]).replace(r"\*", "[^/]*") + "$")
        try:
            files = sorted(x for x in os.listdir(d) if pat.match(x))
        except OSError as e:
            raise Stop(unit, "output directory cannot be listed") from e
        seen: set[tuple[str, int, str]] = set()
        for fn in files:
            for row in jlines(os.path.join(d, fn)):
                ft.check(unit, form, sc, row.keys(), None)
                lid = idm.get(row[f_l])
                if lid is None:
                    reg.notes["r1_rows_of_non_survivors_not_read"] += 1
                    continue
                lv = level_of(unit, row[f_v], lid)
                rule = row[f_h]
                n = fr(row[f_n], "n")
                if (lid, lv, rule) in seen:
                    raise Stop(unit, "a row occurs twice", lid)
                seen.add((lid, lv, rule))
                g = (unit, kind, lid, lv)
                reg.set_items(g, seed, n)
                reg.present[(unit, kind)][seed][lid].add(lv)
                note_items(c, unit, kind, lid, seed, lv, n)
                r1 = reg.row(unit, kind, kind, lid, lv, rule, None, "eff", None, "excess", Fraction(0), None, u_eff, "group", g)
                reg.put(r1, seed, n * fr(row[f_eff], "eff"), n)
                if row[f_anti] is not None:
                    r2 = reg.row(unit, kind, kind, lid, lv, rule, None, "anti", None, "excess", Fraction(0), None, u_anti, "group", g)
                    reg.put(r2, seed, n * fr(row[f_anti], "anti"), n)
                reg.exact_data[(unit, kind, lid, rule)][seed][lv] = (n, row[f_fired], row[f_acc])


R1C_NUM = r"[+-]\d+\.\d{3}"
R1C_RE = re.compile(rf"^ eff ((?:{R1C_NUM})(?: {R1C_NUM})*)   anti ((?:{R1C_NUM})(?: {R1C_NUM})*)$")


def read_r1c(c: Ctx, unit: str, spec: dict[str, Any], seed: str, d: str) -> None:
    ft, reg = c.ft, c.reg
    form, sc = "r1c_stdout", "line"
    u_eff = Fraction(ft.scope(form, sc)[ft.name(form, sc, "excess_eff_levels")]["decimals_uncertainty"])
    u_anti = Fraction(ft.scope(form, sc)[ft.name(form, sc, "excess_anti_levels")]["decimals_uncertainty"])
    idm = spec["id_map"]
    path = os.path.join(d, spec["file"])
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError as e:
        raise Stop(unit, "stdout file cannot be read") from e
    seen: set[tuple[str, str]] = set()
    n = Fraction(c.plan_items[unit])
    for line in lines:
        if not line.strip():
            continue
        tok = line.split(None, 1)[0]
        if not tok.startswith("R1."):
            reg.notes["r1c_stdout_lines_not_read"] += 1
            continue
        lid = idm.get(tok)
        if lid is None:
            reg.notes["r1c_lines_of_non_survivors_not_read"] += 1
            continue
        pos = max(36, len(tok))
        rest = line[pos + 1 + 60:]
        m = R1C_RE.match(rest)
        if line[pos:pos + 1] != " " or m is None:
            raise Stop(unit, "a line of the standard output has an unexpected form", lid)
        name = line[pos + 1: pos + 1 + 60].rstrip()
        eff_v, anti_v = m.group(1).split(" "), m.group(2).split(" ")
        if len(eff_v) != R1C_VALUES or len(anti_v) != R1C_VALUES:
            raise Stop(unit, "a line does not have 7 values per figure, so its levels cannot be read", lid)
        if (lid, name) in seen:
            raise Stop(unit, "a rule occurs twice", lid)
        seen.add((lid, name))
        for lv in LEVELS:
            g = (unit, "new", lid, lv)
            reg.set_items(g, seed, n)
            reg.present[(unit, "new")][seed][lid].add(lv)
            r1 = reg.row(unit, "new", "new", lid, lv, name, None, "eff", None, "excess", Fraction(0), None, u_eff, "group", g)
            reg.put(r1, seed, n * Fraction(eff_v[lv]), n)
            r2 = reg.row(unit, "new", "new", lid, lv, name, None, "anti", None, "excess", Fraction(0), None, u_anti, "group", g)
            reg.put(r2, seed, n * Fraction(anti_v[lv]), n)


def read_r2(c: Ctx, unit: str, spec: dict[str, Any], seed: str, d: str) -> None:
    ft, reg, ct = c.ft, c.reg, c.ct
    form = "r2_json"
    variant = spec["variant"]
    data = jload(os.path.join(d, spec["file"]))
    ft.check(unit, form, "top", data.keys())
    lineages = data[ft.name(form, "top", "lineage_map")]
    idm = spec["id_map"]
    f_n, f_at, f_rules = ft.name(form, "shape", "items"), ft.name(form, "shape", "answer_type"), ft.name(form, "shape", "rules_map")
    f_k, f_napp = ft.name(form, "rule", "hits"), ft.name(form, "rule", "applicable")
    sd_names = set(ct.shape_dependent)
    for raw_lid, lvs in sorted(lineages.items()):
        lid = idm.get(raw_lid)
        if lid is None:
            reg.notes["r2_lineages_not_survivors_not_read"] += 1
            continue
        for lv_key, shapes in lvs.items():
            lv = level_of(unit, lv_key, lid)
            reg.present[(unit, variant)][seed][lid].add(lv)
            total_n = Fraction(0)
            by_at: dict[str, dict[str, Any]] = defaultdict(dict)
            for sh, ent in shapes.items():
                ft.check(unit, form, "shape", ent.keys(), lid)
                n = fr(ent[f_n], "n")
                total_n += n
                by_at[ent[f_at]][sh] = ent
                for rn, rv in ent[f_rules].items():
                    ft.check(unit, form, "rule", rv.keys(), lid)
                    kk, na = fr(rv[f_k]), fr(rv[f_napp])
                    reg.shape_rate((unit, variant, lid, lv, sh, rn), seed, {"k": frac_str(kk), "napp": frac_str(na), "n": frac_str(n),
                                                                           "k_over_n": frac_str(kk / n) if n else None, "k_over_napp": frac_str(kk / na) if na else None})
            note_items(c, unit, variant, lid, seed, lv, total_n)
            if len(by_at) > 1:
                reg.mixed_answer_types.add((unit, variant, lid, lv))
            for at, shs in sorted(by_at.items()):
                yn = at == "yn"
                n_group = sum((fr(e[f_n]) for e in shs.values()), Fraction(0))
                reg.set_items((unit, variant, lid, lv, at), seed, n_group)
                for sh, e in shs.items():  # items of every shape, named or not (the items of a seed in which a per-shape rule is not named)
                    reg.set_items((unit, variant, lid, lv, at, sh), seed, fr(e[f_n]))
                names = sorted({rn for e in shs.values() for rn in e[f_rules]})
                for rn in names:
                    if rn in sd_names:  # shape-dependent class: never pooled over shapes of different class; read per shape (point 6, K6)
                        for sh, e in sorted(shs.items()):
                            if rn not in e[f_rules]:
                                continue
                            rv = e[f_rules][rn]
                            _r2_rows(reg, unit, variant, lid, lv, rn, sh, at, yn, (unit, variant, lid, lv, at, sh), seed, fr(rv[f_k]), fr(rv[f_napp]), fr(e[f_n]))
                        # a shape in which the rule is not named: its items are inside the shape's group and it has no row for the rule
                        continue
                    k = sum((fr(e[f_rules][rn][f_k]) for e in shs.values() if rn in e[f_rules]), Fraction(0))
                    napp = sum((fr(e[f_rules][rn][f_napp]) for e in shs.values() if rn in e[f_rules]), Fraction(0))
                    _r2_rows(reg, unit, variant, lid, lv, rn, None, at, yn, (unit, variant, lid, lv, at), seed, k, napp, n_group)


def _r2_rows(reg: Registry, unit: str, variant: str, lid: str, lv: int, rn: str, shape: str | None, at: str, yn: bool, g: tuple[Any, ...], seed: str,
             k: Fraction, napp: Fraction, n_items: Fraction) -> None:
    zero = Fraction(0)
    if yn:  # k / napp against 1/2 (the R2 scripts' convention); the sign is kept, the decision is two-sided
        r = reg.row(unit, variant, variant, lid, lv, rn, shape, "k_over_napp", at, "rate", Fraction(1, 2), None, zero, "zero", g)
        reg.put(r, seed, k, napp)
        return
    r = reg.row(unit, variant, variant, lid, lv, rn, shape, "k_over_n", at, "rate", zero, None, zero, "group", g)
    reg.put(r, seed, k, n_items)
    if "[cond]" in rn:  # the second figure of K5: k / napp over the items where the rule applies
        r2 = reg.row(unit, variant, variant, lid, lv, rn, shape, "k_over_napp", at, "rate", zero, None, zero, "zero", g)
        reg.put(r2, seed, k, napp)


def _m1_rows(c: Ctx, unit: str, source: str, lid: str, lv: int, rates: dict[str, Any], base: Fraction, n: Fraction, seed: str, d_rates: int, d_base: int,
             prefix: str, base_name: str, form: str, scope: str) -> None:
    reg = c.reg
    g = (unit, source, lid, lv)
    reg.set_items(g, seed, n)
    reg.base_seed[g][seed] = (n * base, n)
    reg.present[(unit, source)][seed][lid].add(lv)
    note_items(c, unit, source, lid, seed, lv, n)
    rb = reg.row(unit, source, "m1", lid, lv, base_name, None, "vs_chance", None, "rate", Fraction(0), None, unc(d_base), "group", g)
    reg.put(rb, seed, n * base, n)
    if unit == "M1a":
        # R-56: a second reading of every key name[...], pooled under name; two bracketed variants of one name in one seed, section, lineage and level, or a
        # bracketed key next to a key that is already the bare name, are not combined: the output gives rates and not the items each rule answered, so
        # the hits cannot be summed without possible double counting of items, and the script stops (exit 3).
        groups: dict[str, list[str]] = defaultdict(list)
        for key in rates:
            m = BRACKET.match(key)
            if m:
                groups[m.group(1)].append(key)
        for sname, keys in groups.items():
            if len(keys) > 1 or sname in rates:
                raise Stop(unit, "bracketed variants of one name cannot be combined without double counting items", lid)
    for key, v in rates.items():
        if key.endswith("__within_applicable"):  # point 6, K7: not a rule
            continue
        name = prefix + key
        r1 = reg.row(unit, source, "m1", lid, lv, name, None, "vs_chance", None, "rate", Fraction(0), None, unc(d_rates), "group", g)
        reg.put(r1, seed, n * fr(v, "rate"), n)
        r2 = reg.row(unit, source, "m1", lid, lv, name, None, "vs_base", None, "rate", Fraction(0), g, 2 * unc(d_rates), "group", g)  # two half-units: a difference of two rounded figures (K14)
        reg.put(r2, seed, n * fr(v, "rate"), n)
        mb = BRACKET.match(key) if unit == "M1a" else None
        if mb:  # R-56: the same figure again under the name with the bracketed part removed, same section prefix
            sname = prefix + mb.group(1)
            s1 = reg.row(unit, source, "m1", lid, lv, sname, None, "vs_chance", None, "rate", Fraction(0), None, unc(d_rates), "group", g)
            s1.extra["bracket_stripped"] = True
            reg.put(s1, seed, n * fr(v, "rate"), n)
            s2 = reg.row(unit, source, "m1", lid, lv, sname, None, "vs_base", None, "rate", Fraction(0), g, 2 * unc(d_rates), "group", g)
            s2.extra["bracket_stripped"] = True
            reg.put(s2, seed, n * fr(v, "rate"), n)


def read_m1_battery(c: Ctx, unit: str, spec: dict[str, Any], seed: str, d: str) -> None:
    ft, reg = c.ft, c.reg
    form = "m1_battery"
    data = jload(os.path.join(d, spec["file"]))
    ft.check(unit, form, "top", data.keys())
    raw = data[ft.name(form, "top", "sections")]
    idm = spec["id_map"]
    for section in sorted(raw):
        if section not in M1_PREFIX:
            raise Stop(unit, f"a section that is not own, a4 or a3: {section}")
        sc = {"own": "level_own", "a4": "level_a4", "a3": "level_a3"}[section]
        f_n, f_b, f_r = ft.name(form, sc, "items"), ft.name(form, sc, "base"), ft.name(form, sc, "rates_map")
        d_b, d_r = ft.field_decimals(form, sc, f_b), ft.field_decimals(form, sc, f_r)
        for raw_lid, lvs in sorted(raw[section].items()):
            lid = idm.get(raw_lid)
            if lid is None:
                reg.notes["m1_lineages_not_survivors_not_read"] += 1
                continue
            for lv_key, row in lvs.items():
                if lv_key not in {str(x) for x in LEVELS}:
                    ft.check(unit, form, "lineage", [lv_key], lid)
                    continue
                ft.check(unit, form, sc, row.keys(), lid)
                lv = level_of(unit, lv_key, lid)
                _m1_rows(c, unit, section, lid, lv, row[f_r], fr(row[f_b], "base"), fr(row[f_n], "N"), seed, d_r, d_b, M1_PREFIX[section], f"base[{section}]", form, sc)
    # a name that two sections of M1a both give a lineage and level is two rules (different streams); reported
    names: dict[tuple[str, int, str], set[str]] = defaultdict(set)
    for r in reg.rows.values():
        if r.unit == unit and r.reading == "vs_chance" and not r.rule.startswith("base["):
            names[(r.lineage, r.level, r.rule)].add(r.source)
    for (lid, lv, rn), srcs in names.items():
        if len(srcs) > 1:
            reg.m1_collisions.add((unit, lid, rn, lv, ",".join(sorted(srcs))))


def read_m1_results(c: Ctx, unit: str, spec: dict[str, Any], seed: str, d: str) -> None:
    ft = c.ft
    form = "m1_results"
    data = jload(os.path.join(d, spec["file"]))
    ft.check(unit, form, "top", data.keys())
    res = data[ft.name(form, "top", "lineage_map")]
    idm = spec["id_map"]
    f_n, f_b, f_r = ft.name(form, "level", "items"), ft.name(form, "level", "base"), ft.name(form, "level", "rates_map")
    d_b, d_r = ft.field_decimals(form, "level", f_b), ft.field_decimals(form, "level", f_r)
    for raw_lid, lvs in sorted(res.items()):
        lid = idm.get(raw_lid)
        if lid is None:
            c.reg.notes["m1_lineages_not_survivors_not_read"] += 1
            continue
        for lv_key, row in lvs.items():
            ft.check(unit, form, "level", row.keys(), lid)
            lv = level_of(unit, lv_key, lid)
            _m1_rows(c, unit, "results", lid, lv, row[f_r], fr(row[f_b], "base"), fr(row[f_n], "N"), seed, d_r, d_b, "", "base", form, "level")


def _c1_scalars(c: Ctx, unit: str, form: str, source: str, class_source: str, lid: str, lv: int, row: dict[str, Any], n: Fraction, seed: str, g: tuple[Any, ...]) -> None:
    ft, reg = c.ft, c.reg
    for f in ft.names(form, "level", "rule_scalar"):
        if f not in row:
            continue
        r = reg.row(unit, source, class_source, lid, lv, f, None, "rate", None, "rate", Fraction(0), None, unc(ft.field_decimals(form, "level", f)), "group", g, is_measure=True)
        reg.put(r, seed, n * fr(row[f], f), n)


def _c1_hits(c: Ctx, unit: str, source: str, class_source: str, lid: str, lv: int, g: tuple[Any, ...], n: Fraction, seed: str, hits: dict[str, Fraction], u: Fraction,
             alt: dict[str, Fraction] | None = None) -> None:
    reg = c.reg
    for rule, h in hits.items():
        r = reg.row(unit, source, class_source, lid, lv, rule, None, "rate", None, "rate", Fraction(0), None, u, "group", g)
        reg.put(r, seed, h, n)
        if alt is not None:
            r.alt_nums[seed] = alt[rule]


def read_c1_s5(c: Ctx, unit: str, spec: dict[str, Any], seed: str, d: str) -> None:
    ft, reg = c.ft, c.reg
    form = "c1_s5"
    data = jload(os.path.join(d, spec["file"]))
    idm = spec["id_map"]
    f_n, f_rules = ft.name(form, "level", "items"), ft.name(form, "level", "rules_map")
    f_rate, f_ns = ft.name(form, "rule", "share_in_shape"), ft.name(form, "rule", "items_in_shape")
    f_alt = ft.name(form, "rule", "alt_recovery_share")
    u_rules = unc(ft.field_decimals(form, "rule", f_rate))
    skip = ft.not_rule_keys(form, "rule_name")
    for raw_lid, lvs in sorted(data.items()):
        lid = idm.get(raw_lid)
        if lid is None:
            reg.notes["c1_lineages_not_survivors_not_read"] += 1
            continue
        for lv_key, row in lvs.items():
            ft.check(unit, form, "level", row.keys(), lid)
            lv = level_of(unit, lv_key, lid)
            n = fr(row[f_n], "n")
            g = (unit, "s5", lid, lv)
            reg.set_items(g, seed, n)
            reg.present[(unit, "s5")][seed][lid].add(lv)
            note_items(c, unit, "s5", lid, seed, lv, n)
            _c1_scalars(c, unit, form, "s5", "a4", lid, lv, row, n, seed, g)
            hits: dict[str, Fraction] = defaultdict(Fraction)
            alt: dict[str, Fraction] = defaultdict(Fraction)
            for key, rr in row[f_rules].items():
                shape, _, rule = key.partition("|")
                if shape.startswith(ERROR_SHAPES):
                    reg.notes["error_marker_rows_not_read"] += 1
                    continue
                ft.check(unit, form, "rule", rr.keys(), lid)
                reg.shape_rate((unit, "s5", lid, lv, shape, rule), seed, {"rate_in_shape": frac_str(fr(rr[f_rate])), "n_shape": frac_str(fr(rr[f_ns]))})
                if rule in skip:
                    continue
                hits[rule] += round(fr(rr[f_rate]) * fr(rr[f_ns]))  # R-34: hits recovered as round(share x items of the shape), summed over the shapes
                alt[rule] += round(fr(rr[f_alt]) * n) if f_alt in rr else Fraction(0)
            _c1_hits(c, unit, "s5", "a4", lid, lv, g, n, seed, dict(hits), u_rules, dict(alt))


def _report_shape(reg: Registry, ft: FieldTable, unit: str, source: str, lid: str, lv: int, key: str, seed: str, form: str, rr: dict[str, Any]) -> None:
    """R-57: the report-only fields of an S row (rates and sizes within one shape), as written."""
    shape, _, rule = key.partition("|")
    vals = {f: (frac_str(fr(rr[f])) if rr.get(f) is not None else None) for f in ft.report_fields(form, "S_row") if f in rr}
    reg.shape_rate((unit, source, lid, lv, shape, rule), seed, vals)


def read_c1_a3(c: Ctx, unit: str, spec: dict[str, Any], seed: str, d: str) -> None:
    ft, reg = c.ft, c.reg
    form = "c1_a3"
    log = jload(os.path.join(d, spec["run_log"]))
    f_n, f_S = ft.name(form, "level", "items"), ft.name(form, "level", "rules_map")
    f_hit = ft.name(form, "S_row", "hits")
    f_rc, f_err = ft.name(form, "run_log", "fallback_status"), ft.name(form, "run_log", "fallback_report")
    cache: dict[str, Any] = {}
    for lid, ps in sorted(spec["per_survivor"].items()):
        rec = log.get(ps["run_log_key"])
        if rec is None:
            raise Stop(unit, "no entry in run_log.json", lid)
        ft.check(unit, form, "run_log", rec.keys(), lid)
        use_primary = ps["fallback_file"] is None or rec.get(f_rc) == 0
        if not use_primary:
            reg.fallbacks.append({"unit": unit, "seed": seed, "lineage": lid, "run_log_key": ps["run_log_key"], "alias_rc": None if rec.get(f_rc) is None else str(rec.get(f_rc)),
                                  "alias_err_first_300": str(rec.get(f_err, ""))[:300], "read_from": ps["fallback_file"]})
        fn, key = (ps["primary_file"], ps["primary_key"]) if use_primary else (ps["fallback_file"], ps["fallback_key"])
        if fn not in cache:
            try:
                cache[fn] = jload(os.path.join(d, fn))
            except InputError as e:
                raise Stop(unit, "an a3 output cannot be read", lid) from e
        body = cache[fn].get(key)
        if body is None:
            raise Stop(unit, "its key is not in its a3 output", lid)
        for lv_key, row in body.items():
            ft.check(unit, form, "level", row.keys(), lid)
            lv = level_of(unit, lv_key, lid)
            n = fr(row[f_n], "n")
            g = (unit, "a3", lid, lv)
            reg.set_items(g, seed, n)
            reg.present[(unit, "a3")][seed][lid].add(lv)
            note_items(c, unit, "a3", lid, seed, lv, n)
            _c1_scalars(c, unit, form, "a3", "a3", lid, lv, row, n, seed, g)
            hits: dict[str, Fraction] = defaultdict(Fraction)
            for k2, rr in row[f_S].items():
                if k2.startswith(ERROR_SHAPES):
                    reg.notes["error_marker_rows_not_read"] += 1
                    continue
                ft.check(unit, form, "S_row", rr.keys(), lid)
                hits[k2.partition("|")[2]] += fr(rr[f_hit], "hit")
                _report_shape(reg, ft, unit, "a3", lid, lv, k2, seed, form, rr)
            _c1_hits(c, unit, "a3", "a3", lid, lv, g, n, seed, dict(hits), Fraction(0))


def read_c1_battery(c: Ctx, unit: str, spec: dict[str, Any], seed: str, d: str) -> None:
    ft, reg = c.ft, c.reg
    form = "c1_battery"
    data = jload(os.path.join(d, spec["file"]))
    idm = spec["id_map"]
    f_n, f_S = ft.name(form, "level", "items"), ft.name(form, "level", "rules_map")
    f_msh, f_shapes = ft.name(form, "level", "rule_shape_map"), ft.name(form, "level", "shape_sizes")
    f_hit = ft.name(form, "S_row", "hits")
    u_msh = unc(ft.field_decimals(form, "level", f_msh))
    for raw_lid, lvs in sorted(data.items()):
        lid = idm.get(raw_lid)
        if lid is None:
            reg.notes["c1_lineages_not_survivors_not_read"] += 1
            continue
        for lv_key, row in lvs.items():
            ft.check(unit, form, "level", row.keys(), lid)
            lv = level_of(unit, lv_key, lid)
            n = fr(row[f_n], "n")
            g = (unit, "battery", lid, lv)
            reg.set_items(g, seed, n)
            reg.present[(unit, "battery")][seed][lid].add(lv)
            note_items(c, unit, "battery", lid, seed, lv, n)
            _c1_scalars(c, unit, form, "battery", "battery", lid, lv, row, n, seed, g)
            hits: dict[str, Fraction] = defaultdict(Fraction)
            for k2, rr in row[f_S].items():
                if k2.startswith(ERROR_SHAPES):
                    reg.notes["error_marker_rows_not_read"] += 1
                    continue
                ft.check(unit, form, "S_row", rr.keys(), lid)
                hits[k2.partition("|")[2]] += fr(rr[f_hit], "hit")
                _report_shape(reg, ft, unit, "battery", lid, lv, k2, seed, form, rr)
            _c1_hits(c, unit, "battery", "battery", lid, lv, g, n, seed, dict(hits), Fraction(0))
            for sh, rate in row[f_msh].items():
                reg.shape_rate((unit, "battery", lid, lv, sh, f_msh), seed, {"rate_in_shape": frac_str(fr(rate)), "n_shape": frac_str(fr(row[f_shapes][sh]))})
            msh = sum((round(fr(rate) * fr(row[f_shapes][sh])) for sh, rate in row[f_msh].items()), Fraction(0))  # a share per shape: hits recovered and summed
            _c1_hits(c, unit, "battery", "battery", lid, lv, g, n, seed, {f_msh: Fraction(msh)}, u_msh)


def read_c1_closed(c: Ctx, unit: str, spec: dict[str, Any], seed: str, d: str) -> None:
    ft, reg = c.ft, c.reg
    form = "c1_closed"
    data = jload(os.path.join(d, spec["file"]))
    idm = spec["id_map"]
    f_pl, f_np = ft.name(form, "lineage", "per_level_shares"), ft.name(form, "lineage", "items_per_level")
    u = unc(ft.decimals(form, "lineage", "per_level_shares"))
    src = os.path.splitext(spec["file"])[0]
    for raw_lid, body in sorted(data.items()):
        lid = idm.get(raw_lid)
        if lid is None:
            reg.notes["c1_lineages_not_survivors_not_read"] += 1
            continue
        ft.check(unit, form, "lineage", body.keys(), lid)
        for lv_key, n_raw in body[f_np].items():
            lv = level_of(unit, lv_key, lid)
            n = fr(n_raw, "n")
            g = (unit, src, lid, lv)
            reg.set_items(g, seed, n)
            reg.present[(unit, src)][seed][lid].add(lv)
            note_items(c, unit, src, lid, seed, lv, n)
            hits = {rule: Fraction(round(fr(share) * n)) for rule, share in body[f_pl].get(lv_key, {}).items()}
            _c1_hits(c, unit, src, "closed forms", lid, lv, g, n, seed, hits, u)


READERS = {"r1_rows": read_r1_rows, "r1c_stdout": read_r1c, "r2_json": read_r2, "m1_battery": read_m1_battery, "m1_results": read_m1_results,
           "c1_s5": read_c1_s5, "c1_a3": read_c1_a3, "c1_battery": read_c1_battery, "c1_closed": read_c1_closed}


def presence_keys(spec: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """(source name used in Registry.present, required lineages) for one output spec of the plan."""
    f = spec["form"]
    if f == "r1_rows":
        return [(k, v["must_contain"]) for k, v in sorted(spec["kinds"].items())]
    if f == "r1c_stdout":
        return [("new", spec["must_contain"])]
    if f == "r2_json":
        return [(spec["variant"], spec["must_contain"])]
    if f == "m1_battery":
        return [(s, spec["must_contain"]) for s in sorted(M1_PREFIX)]
    if f == "m1_results":
        return [("results", spec["must_contain"])]
    if f == "c1_s5":
        return [("s5", spec["must_contain"])]
    if f == "c1_a3":
        return [("a3", spec["must_contain"])]
    if f == "c1_battery":
        return [("battery", spec["must_contain"])]
    if f == "c1_closed":
        return [(os.path.splitext(spec["file"])[0], spec["must_contain"])]
    raise InputError("unknown form " + f)


# ------------------------------------------------------------------------------------------------ evaluation
class Result:
    def __init__(self, row: Row) -> None:
        self.row = row
        self.items = Fraction(0)
        self.items_by_seed: dict[str, Fraction] = {}
        self.named: list[str] = []
        self.rate: Fraction | None = None
        self.base: Fraction | None = None
        self.excess: Fraction | None = None
        self.margin: Fraction | None = None
        self.counted = True
        self.entry: str | None = None
        self.entry_kind: str | None = None  # 'class table' or 'amendment'
        self.over = False


def evaluate(reg: Registry, ct: ClassTable, plan_items: dict[str, int], seeds: list[str]) -> list[Result]:
    out: list[Result] = []
    for row in sorted(reg.rows.values(), key=Row.key):
        res = Result(row)
        num = den = Fraction(0)
        for s in seeds:
            if s in row.nums:
                n_s, d_s = row.nums[s], row.dens[s]
                res.named.append(s)
            else:  # a rule named only for some seeds counts no hit and that seed's items for the others (point 6)
                n_s = Fraction(0)
                if row.unnamed == "zero":
                    d_s = Fraction(0)
                elif s in reg.items[row.gkey]:
                    d_s = reg.items[row.gkey][s]
                elif row.level in reg.present[(row.unit, row.source)][s].get(row.lineage, set()):
                    d_s = Fraction(0)  # the seed has rows for this lineage and level, none in this group: the group has no items there
                else:
                    d_s = Fraction(plan_items[row.unit])  # no row of the seed at all for this lineage and level: the plan's items per level
            num += n_s
            den += d_s
            res.items_by_seed[s] = d_s
        res.items = den
        if den != 0:
            res.rate = num / den
            if row.base_group is not None:
                bn = sum((reg.base_seed[row.base_group][s][0] for s in seeds if s in reg.base_seed[row.base_group]), Fraction(0))
                bd = sum((reg.base_seed[row.base_group][s][1] for s in seeds if s in reg.base_seed[row.base_group]), Fraction(0))
                res.base = bn / bd if bd else Fraction(0)
            else:
                res.base = row.base
            res.excess = res.rate - res.base if row.kind == "rate" else res.rate
            res.margin = abs(res.excess) + row.u
            res.over = res.margin > BOUND
        classify(res, ct)
        if not res.counted:
            res.over = False
        out.append(res)
    return out


def classify(res: Result, ct: ClassTable) -> None:
    r = res.row
    ev = r.unit[:2]
    if ev == "R1":
        e = ct.r1(r.unit, r.lineage, r.rule)
    elif ev == "R2":
        e = ct.r2(r.unit, r.lineage, r.rule, r.level, r.shape)
    elif ev == "M1":
        e = ct.m1(r.unit, r.lineage, r.rule)
    else:
        e = ct.c1(r.unit, r.class_source, r.rule, r.is_measure)
    if e is not None:
        res.counted, res.entry, res.entry_kind = False, e, "class table"
        return
    a = ct.amendment(r.unit, r.lineage, r.rule)
    if a is not None:
        res.counted, res.entry, res.entry_kind = False, a, "amendment list"


# ------------------------------------------------------------------------------------------------ outputs
def row_json(res: Result) -> dict[str, Any]:
    r = res.row
    return {"unit": r.unit, "source": r.source, "lineage": r.lineage, "level": r.level, "rule": r.rule, "shape": r.shape, "reading": r.reading, "answer_type": r.answer_type,
            "figure_kind": r.kind, "items": int(res.items) if res.items.denominator == 1 else frac_str(res.items),
            "items_by_seed": {s: int(v) if v.denominator == 1 else frac_str(v) for s, v in sorted(res.items_by_seed.items())}, "named_in_seeds": res.named,
            "pooled_figure": fj(res.rate), "base": fj(res.base) if r.kind == "rate" else None, "excess": fj(res.excess),
            "rounding_uncertainty": fj(r.u), "counted": res.counted, "class_entry": res.entry, "class_entry_kind": res.entry_kind,
            "abs_excess_plus_uncertainty": fj(res.margin), "over_bound": res.over, "bracket_stripped": bool(r.extra.get("bracket_stripped", False))}


def write_json_lines(path: str, rows: list[dict[str, Any]]) -> None:
    with open(path, "x", encoding="utf-8") as f:
        f.write("[\n" + ",\n".join(json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows) + "\n]\n")


def write_json(path: str, obj: Any) -> None:
    with open(path, "x", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
        f.write("\n")


def build_outputs(c: Ctx, results: list[Result], survivors: dict[str, list[str]]) -> dict[str, Any]:
    reg, ct = c.reg, c.ct
    ev_of = {x: ev for ev, xs in survivors.items() for x in xs}
    # per lineage and level: the largest counted |excess|
    per: dict[str, dict[str, Any]] = {x: {"evaluation": ev_of[x], "levels": {str(v): None for v in LEVELS}, "dropped": False} for x in sorted(ev_of)}
    best: dict[tuple[str, int], Result] = {}
    over_rows: dict[str, list[Result]] = defaultdict(list)
    over_without_stripped: dict[str, list[Result]] = defaultdict(list)
    no_items: list[dict[str, Any]] = []
    for res in results:
        r = res.row
        if r.lineage not in per:
            continue
        if res.counted and res.excess is None:
            no_items.append({"unit": r.unit, "source": r.source, "lineage": r.lineage, "level": r.level, "rule": r.rule, "reading": r.reading})
        if res.counted and res.excess is not None:
            k = (r.lineage, r.level)
            if k not in best or abs(res.excess) > abs(best[k].excess or Fraction(0)):
                best[k] = res
        if res.over:
            over_rows[r.lineage].append(res)
            if not r.extra.get("bracket_stripped"):
                over_without_stripped[r.lineage].append(res)
    for (x, lv), res in sorted(best.items()):
        r = res.row
        per[x]["levels"][str(lv)] = {"largest_counted_abs_excess": fj(abs(res.excess or Fraction(0))), "signed_excess": fj(res.excess), "unit": r.unit, "source": r.source,
                                     "rule": r.rule, "shape": r.shape, "reading": r.reading, "answer_type": r.answer_type, "rounding_uncertainty": fj(r.u)}
    dropped = []
    for x in sorted(over_rows):
        rows = over_rows[x]
        top = max(rows, key=lambda t: (t.margin or Fraction(0)))
        per[x]["dropped"] = True
        dropped.append({"lineage": x, "evaluation": ev_of[x], "reason": {"rule": top.row.rule, "unit": top.row.unit, "source": top.row.source, "level": top.row.level,
                        "shape": top.row.shape, "reading": top.row.reading, "pooled_figure": fj(top.rate), "excess": fj(top.excess), "rounding_uncertainty": fj(top.row.u),
                        "abs_excess_plus_uncertainty": fj(top.margin), "bound": "15/100"},
                        "all_rows_over_the_bound": [{"unit": t.row.unit, "source": t.row.source, "level": t.row.level, "rule": t.row.rule, "shape": t.row.shape, "reading": t.row.reading,
                                                     "excess": fj(t.excess), "abs_excess_plus_uncertainty": fj(t.margin)} for t in rows]})
    # exact R1 rows (point 8)
    exact = []
    for (unit, kind, lid, rule), by_seed in sorted(reg.exact_data.items()):
        if lid not in per:
            continue
        ok = True
        for s in c.seeds:
            for v in LEVELS:
                t = by_seed.get(s, {}).get(v)
                if t is None:
                    ok = False  # the rule has no row at some level or seed
                    break
                n, fired, acc = t
                if acc is None or fired != n or fr(acc) != 1:
                    ok = False  # not every scored item was answered and answered right (or acc_fired is not written)
                    break
            if not ok:
                break
        if ok:
            entry = ct.r1(unit, lid, rule)
            exact.append({"unit": unit, "source": kind, "lineage": lid, "rule": rule, "rule_is_an_entry_of_the_class_table": entry is not None, "entry": entry,
                          "set_aside": entry is not None, "counted": entry is None and ct.amendment(unit, lid, rule) is None})
    # uncounted rules with the entry that matched them
    unc_map: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    for res in results:
        if not res.counted and res.row.lineage in per:
            r = res.row
            unc_map[(r.unit, r.source, r.lineage, r.rule, r.shape or "", res.entry_kind, res.entry)].append(r.level)
    uncounted = [{"unit": k[0], "source": k[1], "lineage": k[2], "rule": k[3], "shape": k[4] or None, "kind": k[5], "entry": k[6], "levels": sorted(set(v))} for k, v in sorted(unc_map.items(), key=str)]
    # s5 recovery variants whose decision differs
    alt_changes = []
    for res in results:
        r = res.row
        if r.alt_nums and res.counted and res.items != 0:
            num = sum((r.alt_nums.get(s, Fraction(0)) for s in c.seeds), Fraction(0))
            alt_ex = num / res.items
            if (abs(alt_ex) + r.u > BOUND) != res.over:
                alt_changes.append({"unit": r.unit, "lineage": r.lineage, "level": r.level, "rule": r.rule, "decision_main": res.over, "alt_excess": fj(alt_ex), "main_excess": fj(res.excess)})
    diffs: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
    for d in reg.item_diffs:
        diffs[(d["unit"], d["source"], d["lineage"], d["seed"], d["plan_items"])].append({"level": d["level"], "items": d["items"]})
    item_diff_list = [{"unit": k[0], "source": k[1], "lineage": k[2], "seed": k[3], "plan_items": k[4], "levels": sorted(v, key=lambda z: z["level"])} for k, v in sorted(diffs.items(), key=str)]
    bracket_changes = [{"lineage": x, "dropped_with_the_second_reading": True, "dropped_without_it": x in over_without_stripped,
                        "rows_over_the_bound_only_under_the_second_reading": [{"unit": t.row.unit, "source": t.row.source, "level": t.row.level, "rule": t.row.rule, "reading": t.row.reading,
                                                                               "excess": fj(t.excess), "abs_excess_plus_uncertainty": fj(t.margin)} for t in over_rows[x] if t.row.extra.get("bracket_stripped")]}
                       for x in sorted(over_rows) if x not in over_without_stripped]
    stripped_names = sorted({(r.row.unit, r.row.source, r.row.lineage, r.row.level, r.row.rule) for r in results if r.row.extra.get("bracket_stripped") and r.row.lineage in per})
    shape_rates = [{"unit": k[0], "source": k[1], "lineage": k[2], "level": k[3], "shape": k[4], "rule": k[5], "by_seed": v}
                   for k, v in sorted(reg.shape_rates.items(), key=lambda kv: (UNIT_ORDER.index(kv[0][0]), kv[0][1], kv[0][2], kv[0][3], str(kv[0][4]), str(kv[0][5]))) if k[2] in per]
    before = {ev: len(survivors.get(ev, [])) for ev in EVALS}
    dropped_by_ev = {ev: sum(1 for d in dropped if d["evaluation"] == ev) for ev in EVALS}
    extras = {
        "r1_exact_rows": exact,
        "uncounted_rules": uncounted,
        "a3_wrapper_fallbacks": sorted(reg.fallbacks, key=lambda z: (z["unit"], z["lineage"], z["seed"])),
        "rows_with_an_item_count_other_than_the_plan": item_diff_list,
        "item_counts_that_disagree_inside_one_group": reg.item_disagree,
        "lineages_before_and_after_per_evaluation": {ev: {"before": before[ev], "dropped": dropped_by_ev[ev], "after": before[ev] - dropped_by_ev[ev]} for ev in EVALS},
        "s5_recovery_alternatives_that_change_a_decision": alt_changes,
        "m1_names_given_by_more_than_one_section": sorted([list(x) for x in reg.m1_collisions]),
        "r2_levels_with_more_than_one_answer_type": sorted([list(x) for x in reg.mixed_answer_types]),
        "counted_rows_with_no_items": no_items,
        "rows_not_read": dict(reg.notes),
        "dir_overrides": {f"{u}:{s}": p for (u, s), p in sorted(c.overrides.items())},
        "dry_run_exclusions": c.plan.get("dry_run_exclusions", []),
        "m1a_bracket_second_reading_lineages_whose_outcome_differs": bracket_changes,
        "m1a_bracket_second_reading_rows": [{"unit": k[0], "source": k[1], "lineage": k[2], "level": k[3], "stripped_name": k[4]} for k in stripped_names],
        "rates_within_one_shape_reported_only": shape_rates,
        "seed_set": c.seed_set, "seeds": c.seeds,
    }
    return {"per_lineage": per, "dropped": dropped, "extras": extras}


def summary_md(o: dict[str, Any], n_rows: int, c: Ctx) -> str:
    ex = o["extras"]
    lines = ["# Pooling of the fresh run: summary (generated from the JSON files beside it)", "",
             f"Seed set: {c.seed_set} (seeds {', '.join(c.seeds)}). Pooled rows: {n_rows}. Bound: 0.15, two-sided, on the point estimate plus the rounding uncertainty (point 7).", "",
             "## Lineages before and after, per evaluation", "", "| evaluation | before | dropped | after |", "|---|---|---|---|"]
    for ev in EVALS:
        t = ex["lineages_before_and_after_per_evaluation"][ev]
        lines.append(f"| {ev} | {t['before']} | {t['dropped']} | {t['after']} |")
    lines += ["", "## Lineages dropped (rule, unit, level, figure of the row with the largest |excess| + uncertainty)", ""]
    if not o["dropped"]:
        lines.append("None.")
    for d in o["dropped"]:
        r = d["reason"]
        lines.append(f"- {d['lineage']}: rule `{r['rule']}`, unit {r['unit']}, level {r['level']}, shape {r['shape']}, reading {r['reading']}, excess {r['excess']['decimal_12dp']} "
                     f"({r['excess']['fraction']}), uncertainty {r['rounding_uncertainty']['decimal_12dp']}; {len(d['all_rows_over_the_bound'])} row(s) over the bound.")
    lines += ["", "## Counts for the report (the lists are in report_extras.json)", "",
              f"- exact R1 rows: {len(ex['r1_exact_rows'])}", f"- uncounted rule groups: {len(ex['uncounted_rules'])}", f"- a3 wrapper fallbacks: {len(ex['a3_wrapper_fallbacks'])}",
              f"- groups of rows with an item count other than the plan's: {len(ex['rows_with_an_item_count_other_than_the_plan'])}",
              f"- s5 recovery alternatives that would change a decision: {len(ex['s5_recovery_alternatives_that_change_a_decision'])}", ""]
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------ main
def parse_override(s: str) -> tuple[tuple[str, str], str]:
    left, _, path = s.partition("=")
    unit, _, seed = left.partition(":")
    if not (unit and seed and path):
        raise argparse.ArgumentTypeError("--dir-override UNIT:SEEDSET=DIR")
    return (unit, seed), path


def run(a: argparse.Namespace) -> int:
    for p, name in ((a.plan, "plan"), (a.survivors, "survivor list"), (a.class_table, "class table"), (a.amendments, "amendment list"), (a.field_table, "field table")):
        if not os.path.isfile(p):
            raise InputError(f"{name} not found: {p}")
    if sha256_file(a.class_table) != CLASS_TABLE_SHA256:
        raise InputError("the class table does not have the recorded SHA-256")
    for p, want, name in ((a.plan, a.expect_plan_sha256, "run plan"), (a.field_table, a.expect_field_table_sha256, "field table"), (a.amendments, a.expect_amendment_sha256, "amendment list")):
        if sha256_file(p) != want:
            raise InputError(f"the {name} does not have the expected SHA-256")
    plan = jload(a.plan)
    surv = jload(a.survivors)["evaluations"]
    if sha256_file(a.survivors) != plan["survivor_list"]["sha256"]:
        raise InputError("the survivor list does not have the SHA-256 recorded in the run plan")
    ft = FieldTable(jload(a.field_table))
    ct = ClassTable(jload(a.class_table), jload(a.amendments))
    seeds = ["dry"] if a.seed_set == "dry" else ["1", "2", "3"]
    overrides = dict(a.dir_override or [])
    reg = Registry(seeds)
    c = Ctx(plan, ft, ct, reg, a.seed_set, seeds, overrides, surv)
    excl_units: set[str] = set()
    excl_lineages: dict[str, set[str]] = defaultdict(set)
    for e in plan.get("dry_run_exclusions", []):
        if e.get("lineages"):
            excl_lineages[e["unit"]].update(e["lineages"])
        else:
            excl_units.add(e["unit"])
    units = [u for u in plan["unit_order"] if u not in excl_units]
    for unit in units:
        if plan["units"][unit]["evaluation"] not in EVALS:
            raise InputError("unit with an unknown evaluation")
        for spec in plan["units"][unit]["outputs"]:
            for s in seeds:
                d = c.unit_dir(unit, s)
                if not os.path.isdir(d):
                    raise Stop(unit, "output directory of seed set " + s + " is missing")
                try:
                    READERS[spec["form"]](c, unit, spec, s, d)
                except InputError as e:
                    raise Stop(unit, f"an output cannot be read ({e})") from e
    # point 2: what each output must contain; stop before any figure is written
    for unit in units:
        for spec in plan["units"][unit]["outputs"]:
            for src, required in presence_keys(spec):
                for lid in required:
                    if lid in excl_lineages[unit]:
                        continue
                    for s in seeds:
                        got = reg.present[(unit, src)][s].get(lid, set())
                        if not set(LEVELS) <= got:
                            raise Stop(unit, "", lid)
    results = evaluate(reg, ct, c.plan_items, seeds)
    o = build_outputs(c, results, surv)
    os.makedirs(a.out, exist_ok=True)
    names = ["pooled_table.json", "per_lineage.json", "dropped.json", "report_extras.json", "SUMMARY.md"]
    for n in names:
        if os.path.exists(os.path.join(a.out, n)):
            raise InputError("refusing to overwrite " + os.path.join(a.out, n))
    write_json_lines(os.path.join(a.out, "pooled_table.json"), [row_json(r) for r in results])
    write_json(os.path.join(a.out, "per_lineage.json"), o["per_lineage"])
    write_json(os.path.join(a.out, "dropped.json"), o["dropped"])
    write_json(os.path.join(a.out, "report_extras.json"), o["extras"])
    with open(os.path.join(a.out, "SUMMARY.md"), "x", encoding="utf-8") as f:
        f.write(summary_md(o, len(results), c))
    for n in names:
        print("wrote " + os.path.join(a.out, n))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--survivors", required=True)
    ap.add_argument("--class-table", required=True)
    ap.add_argument("--amendments", required=True)
    ap.add_argument("--field-table", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect-plan-sha256", required=True)
    ap.add_argument("--expect-field-table-sha256", required=True)
    ap.add_argument("--expect-amendment-sha256", required=True)
    ap.add_argument("--seed-set", choices=["run", "dry"], default="run")
    ap.add_argument("--dir-override", action="append", type=parse_override, help="UNIT:SEEDSET=DIR: read that unit's output of that seed set (1, 2, 3 or dry) from DIR instead of the plan's directory (for a retried unit, or a structural check)")
    a = ap.parse_args(argv)
    try:
        return run(a)
    except Stop as e:
        msg = f"STOP unit={e.unit}" + (f" lineage={e.lineage}" if e.lineage else "") + (f" ({e.what})" if e.what else "")
        print(msg, file=sys.stderr)
        return 3
    except InputError as e:
        print(f"INPUT ERROR: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
