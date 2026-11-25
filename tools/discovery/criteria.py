"""Multi-criteria selection of analog sites (task T54): the method science uses, applied to the precomputed cells.

What the literature does (T53, docs/wiki/validation/known-analogs.md):
- a site is an analog **for one use and one feature** (Foucher et al. 2021, R28; ESA/Open University catalogue, R66);
- the feature comes first, then the other criteria (R66: scientific merit, then cost, access, infrastructure;
  R68: applicability, access, infrastructure; R69: topography, access, vegetation, signal, geologic diversity);
- several criteria at once, never one alone.

How it is applied here, in plain words:
1. A **preset** names a use, what it imitates on the Moon or Mars, and its criteria, each with why and a source.
2. Each criterion is a readable condition on one variable ("permafrost >= 0.5"), or an equation the user writes.
3. **Required** criteria are gates: a cell is a candidate only if it meets all of them. A cell that fails one is
   excluded. A cell where one is unknown (missing data) is "to check": missing data is never a bad value.
4. **Preferred** criteria never exclude. Candidates are ordered by how many they meet (no weights), then by fewer
   unknowns, then by the confidence of the relief values.
5. Every rule is checked on the known analog sites of the catalogue (R66) and on the 18 random negatives.

Equations are parsed by the small grammar below, never by eval: numbers, variable names, + - * /, comparisons,
and, or, not, parentheses, min, max, abs. Logic is three-valued: unknown and true is unknown, unknown and false is false.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
PRESETS = ROOT / "data/presets/presets.yaml"
OPS = (">=", "<=", ">", "<")
ROLES = ("required", "preferred")
MAX_CRITERIA = 12
MAX_EQUATION = 500
CONF = {"low": 0.0, "medium": 1.0, "high": 2.0}


class CriteriaError(ValueError):
    """A rule, criterion or equation that cannot be used: the message says why, in plain words."""


# --- variables -------------------------------------------------------------------------------------------------

TARGET_NAMES = {
    "moon-polar-lit-highlands": ("lit polar highlands", "hautes terres polaires éclairées"),
    "moon-psr": ("permanently shadowed craters", "cratères en ombre permanente"),
    "moon-pits": ("lunar pits", "fosses lunaires"),
    "moon-mare-plains": ("mare plains", "plaines de mers"),
    "moon-south-polar-cap-v2": ("south polar region", "région polaire sud"),
    "mars-volcanic-plains": ("Martian volcanic plains", "plaines volcaniques martiennes"),
    "mars-ice-rich-midlatitudes": ("ice-rich mid-latitudes", "moyennes latitudes riches en glace"),
    "mars-north-polar": ("north polar terrain", "terrains polaires nord"),
    "mars-south-polar": ("south polar terrain", "terrains polaires sud"),
}
ROCK_SOURCE = {"en": "Macrostrat map units (CC BY 4.0), 9 samples per cell", "fr": "unités cartographiques Macrostrat (CC BY 4.0), 9 échantillons par cellule"}
ROCKS = {   # variable -> (geology group, states counted, English label, French label, help)
    "moon": {
        "basalt": ("mare", ("match",), "Basalt mapped", "Basalte cartographié",
                   ("share of the cell's resolved map samples whose unit lists basalt first",
                    "part des échantillons cartographiés et résolus de la cellule dont l'unité cite d'abord le basalte")),
        "basalt_or_related": ("mare", ("match", "partial"), "Basalt or related rock mapped", "Basalte ou roche apparentée cartographié",
                              ("basalt, dolerite, diabase, basanite, picrite... (crosswalk E17)",
                               "basalte, dolérite, diabase, basanite, picrite... (correspondance E17)")),
        "anorthosite": ("highland", ("match",), "Anorthosite mapped", "Anorthosite cartographiée",
                        ("share of the cell's resolved map samples whose unit lists anorthosite first",
                         "part des échantillons cartographiés et résolus dont l'unité cite d'abord l'anorthosite")),
        "anorthosite_or_related": ("highland", ("match", "partial"), "Anorthosite or related rock mapped",
                                   "Anorthosite ou roche apparentée cartographiée", ("anorthosite, norite, troctolite, gabbro... (E17)", "anorthosite, norite, troctolite, gabbro... (E17)")),
    },
    "mars": {
        "basalt": ("mars-volcanic", ("match",), "Basalt mapped", "Basalte cartographié",
                   ("share of the cell's resolved map samples whose unit lists basalt first",
                    "part des échantillons cartographiés et résolus de la cellule dont l'unité cite d'abord le basalte")),
        "volcanic_rock": ("mars-volcanic", ("match", "partial"), "Volcanic rock mapped", "Roche volcanique cartographiée",
                          ("any rock Macrostrat types as volcanic (basalt, andesite, tuff, scoria...)",
                           "toute roche que Macrostrat classe volcanique (basalte, andésite, tuf, scories...)")),
    },
}
FLAGS = {   # variable -> (requirement column, English, French, help)
    "base_slope_ok": ("req:base_slope", "Base footprint slope at most 10°", "Pente d'emprise de base au plus 10°",
                      ("1 when met, 0 when not (scenario A, E2; 40 m slope)", "1 si remplie, 0 sinon (scénario A, E2 ; pente à 40 m)")),
    "climb_lrv_ok": ("req:climbing_limit_lrv", "Within the Apollo rover climbing limit", "Dans la limite de pente du rover Apollo",
                     ("half of the window at or below 20° (LRV), 1 when met, 0 when not",
                      "la moitié de la fenêtre à 20° ou moins (LRV) : 1 si remplie, 0 sinon")),
    "climb_viper_ok": ("req:climbing_limit_viper", "Within a polar rover climbing limit (15°, not verified)",
                       "Dans une limite de rover polaire (15°, non vérifiée)", ("half of the window at or below 15°, 1 when met", "la moitié de la fenêtre à 15° ou moins : 1 si remplie")),
}


def _short(target: str) -> str:
    return target.split("-", 1)[1].replace("-", "_")


def variables(body: str, targets: list[str]) -> list[dict]:
    """Every variable a rule may use for this body: id, labels, unit, source, scale and a help line."""
    out = []
    for t in targets:
        en, fr = TARGET_NAMES.get(t, (t, t))
        out.append({"id": f"relief_{_short(t)}", "label": {"en": f"Relief like the {en}", "fr": f"Relief comme les {fr}"},
                    "unit": "typicality", "range": [0, 1], "column": f"{t}:median",
                    "source": {"en": "Copernicus DEM against the planetary profile (protocol v3 / mars-v3)",
                               "fr": "Copernicus DEM comparé au profil planétaire (protocole v3 / mars-v3)"},
                    "scale": {"en": "1 km windows (Moon), 2.9 to 11.6 km (Mars)", "fr": "fenêtres de 1 km (Lune), 2,9 à 11,6 km (Mars)"},
                    "help": {"en": "median typicality of the cell's slopes in the planetary distribution: 0 unlike, 1 typical",
                             "fr": "typicité médiane des pentes de la cellule dans la distribution planétaire : 0 différent, 1 typique"}})
    for vid, (group, states, en, fr, help_) in ROCKS.get(body, {}).items():
        out.append({"id": vid, "label": {"en": en, "fr": fr}, "unit": "share", "range": [0, 1], "group": group,
                    "states": list(states), "source": ROCK_SOURCE, "scale": {"en": "5 km cell, maps 1:1 M to 1:5 M", "fr": "cellule de 5 km, cartes au 1:1 M à 1:5 M"}, "help": {"en": help_[0], "fr": help_[1]}})
    out += [
        {"id": "hidden_ground", "label": {"en": "Ground hidden by vegetation, crops, buildings or water",
                                          "fr": "Sol caché par végétation, cultures, bâti ou eau"},
         "unit": "share", "range": [0, 1], "column": "masked_share", "source": {"en": "ESA WorldCover 2021 (ice-free rock in Antarctica)", "fr": "ESA WorldCover 2021 (roche sans glace en Antarctique)"},
         "scale": {"en": "share of the cell's relief windows", "fr": "part des fenêtres de relief de la cellule"}, "help": {"en": "0 all bare, 1 all hidden", "fr": "0 tout nu, 1 tout caché"}},
        {"id": "permafrost", "label": {"en": "Permafrost probability", "fr": "Probabilité de pergélisol"},
         "unit": "probability", "range": [0, 1], "column": "ctx:permafrost_prob", "source": {"en": "Obu et al. 2019 (R32), Northern Hemisphere only", "fr": "Obu et al. 2019 (R32), hémisphère nord seulement"},
         "scale": {"en": "1 km, sampled at the cell", "fr": "1 km, lu à la cellule"}, "help": {"en": "unknown in the Southern Hemisphere", "fr": "inconnue dans l'hémisphère sud"}},
        {"id": "aridity", "label": {"en": "Aridity index", "fr": "Indice d'aridité"}, "unit": "index", "range": [0, 5],
         "column": "ctx:aridity_index", "source": {"en": "Global Aridity Index v3", "fr": "Global Aridity Index v3"}, "scale": {"en": "1 km, sampled at the cell", "fr": "1 km, lu à la cellule"},
         "help": {"en": "below 0.03 hyper-arid, below 0.2 arid, below 0.5 semi-arid", "fr": "sous 0,03 hyper-aride, sous 0,2 aride, sous 0,5 semi-aride"}},
        {"id": "confidence", "label": {"en": "Confidence of the relief values", "fr": "Confiance des valeurs de relief"},
         "unit": "level", "range": [0, 2], "column": "confidence", "source": {"en": "protocol v3 (valid and hidden windows)", "fr": "protocole v3 (fenêtres valides et cachées)"},
         "scale": {"en": "5 km cell", "fr": "cellule de 5 km"}, "help": {"en": "0 low, 1 medium, 2 high", "fr": "0 faible, 1 moyenne, 2 haute"}},
    ]
    for vid, (col, en, fr, help_) in FLAGS.items():
        out.append({"id": vid, "label": {"en": en, "fr": fr}, "unit": "flag", "range": [0, 1], "column": col,
                    "source": {"en": "Copernicus GLO-30 slopes (requirements of scenarios A and B)", "fr": "pentes Copernicus GLO-30 (exigences des scénarios A et B)"},
                    "scale": {"en": "40 m slope, 1 km window", "fr": "pente à 40 m, fenêtre de 1 km"},
                    "help": {"en": help_[0], "fr": help_[1]}})
    return out


def _n(col: Callable[[str], np.ndarray | None]) -> int:
    a = col("masked_share")
    return 0 if a is None else len(a)


def _num(a) -> np.ndarray:
    try:
        return np.asarray(a, dtype=float)
    except (TypeError, ValueError):
        return np.array([np.nan if v is None else float(v) for v in a])


def values(var: str, col: Callable[[str], np.ndarray | None], body: str, targets: list[str] | None = None) -> np.ndarray:
    """Values of one variable for every cell; NaN where unknown."""
    n = _n(col)
    spec = {v["id"]: v for v in variables(body, targets or [])}.get(var)
    if spec is None and var.startswith("relief_"):
        spec = {"column": None}
    if spec is None:
        raise CriteriaError(f"unknown variable '{var}'")
    if "group" in spec:
        g = spec["group"]
        parts = [col(f"geo:{g}:{s}") for s in ("no_map", "unresolved", *spec["states"])]
        if any(p is None for p in parts):
            return np.full(n, np.nan)
        no_map, unres, *hit = (_num(p) for p in parts)
        resolved = 1.0 - no_map - unres
        with np.errstate(invalid="ignore", divide="ignore"):
            out = np.where(resolved > 1e-6, sum(hit) / np.where(resolved > 1e-6, resolved, 1.0), np.nan)
        return np.clip(out, 0.0, 1.0)
    a = col(spec["column"]) if spec.get("column") else None
    if a is None:
        return np.full(n, np.nan)
    if var == "confidence":
        return np.array([CONF.get(str(x), np.nan) for x in a]) if a.dtype.kind in "OUS" else _num(a)
    if spec.get("unit") == "flag":
        s = np.asarray(a).astype(str)
        return np.where(s == "met", 1.0, np.where(s == "failed", 0.0, np.nan))
    return _num(a)


# --- equations ---------------------------------------------------------------------------------------------------

_TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d+)?|\.\d+)|([A-Za-z_][A-Za-z0-9_]*)|(<=|>=|==|!=|<|>|\+|-|\*|/|\(|\)|,))")
_FUNCS = {"min": 2, "max": 2, "abs": 1}
_CMP = {"<", "<=", ">", ">=", "==", "!="}


def _tokens(text: str) -> list[tuple[str, str]]:
    out, i = [], 0
    while i < len(text):
        if text[i:].strip() == "":
            break
        m = _TOKEN.match(text, i)
        if not m:
            ch = text[i:].lstrip()[0]
            raise CriteriaError(f"unexpected character '{ch}' at position {i + 1}")
        num, name, op = m.groups()
        out.append(("num", num) if num else ("name", name) if name else ("op", op))
        i = m.end()
    return out


class _Parser:
    def __init__(self, text: str, names: set[str]):
        self.t = _tokens(text)
        self.i = 0
        self.names = names

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else (None, None)

    def take(self):
        if self.i >= len(self.t):
            raise CriteriaError("incomplete equation: something is missing at the end")
        tok = self.t[self.i]
        self.i += 1
        return tok

    def expect(self, value):
        kind, v = self.take()
        if v != value:
            raise CriteriaError(f"unexpected '{v}', expected '{value}'")

    def parse(self):
        node = self.or_()
        if self.i < len(self.t):
            raise CriteriaError(f"unexpected '{self.t[self.i][1]}'")
        if node[0] != "bool":
            raise CriteriaError("the equation must be a condition: compare it with a threshold, for example ... >= 0.5")
        return node

    def _need(self, node, kind, word):
        if node[0] != kind:
            raise CriteriaError(f"'{word}' needs {'conditions' if kind == 'bool' else 'numbers'} on both sides")
        return node

    def or_(self):
        left = self.and_()
        while self.peek() == ("name", "or"):
            self.take()
            left = ("bool", "or", self._need(left, "bool", "or"), self._need(self.and_(), "bool", "or"))
        return left

    def and_(self):
        left = self.not_()
        while self.peek() == ("name", "and"):
            self.take()
            left = ("bool", "and", self._need(left, "bool", "and"), self._need(self.not_(), "bool", "and"))
        return left

    def not_(self):
        if self.peek() == ("name", "not"):
            self.take()
            return ("bool", "not", self._need(self.not_(), "bool", "not"))
        return self.cmp()

    def cmp(self):
        left = self.sum_()
        kind, v = self.peek()
        if kind == "op" and v in _CMP:
            self.take()
            right = self.sum_()
            return ("bool", v, self._need(left, "num", v), self._need(right, "num", v))
        return left

    def sum_(self):
        left = self.term()
        while self.peek()[0] == "op" and self.peek()[1] in "+-":
            op = self.take()[1]
            left = ("num", op, self._need(left, "num", op), self._need(self.term(), "num", op))
        return left

    def term(self):
        left = self.unary()
        while self.peek()[0] == "op" and self.peek()[1] in ("*", "/"):
            op = self.take()[1]
            left = ("num", op, self._need(left, "num", op), self._need(self.unary(), "num", op))
        return left

    def unary(self):
        if self.peek() == ("op", "-"):
            self.take()
            return ("num", "neg", self._need(self.unary(), "num", "-"))
        return self.atom()

    def atom(self):
        kind, v = self.take()
        if kind == "num":
            return ("num", "const", float(v))
        if kind == "op" and v == "(":
            node = self.or_()
            self.expect(")")
            return node
        if kind == "name":
            if v in ("and", "or", "not"):
                raise CriteriaError(f"unexpected '{v}'")
            if self.peek() == ("op", "("):
                if v not in _FUNCS:
                    raise CriteriaError(f"unknown function '{v}' (allowed: min, max, abs)")
                self.take()
                args = [self._need(self.sum_(), "num", v)]
                while self.peek() == ("op", ","):
                    self.take()
                    args.append(self._need(self.sum_(), "num", v))
                self.expect(")")
                if len(args) != _FUNCS[v]:
                    raise CriteriaError(f"{v} takes {_FUNCS[v]} value{'s' if _FUNCS[v] > 1 else ''}")
                return ("num", v, *args)
            if v not in self.names:
                raise CriteriaError(f"unknown variable '{v}' (valid: {', '.join(sorted(self.names))})")
            return ("num", "var", v)
        raise CriteriaError(f"unexpected '{v}'")


def parse(text: str, names: set[str]):
    """Syntax tree of an equation, or CriteriaError with a reason a person can read."""
    if not isinstance(text, str) or not text.strip():
        raise CriteriaError("the equation is empty")
    if len(text) > MAX_EQUATION:
        raise CriteriaError(f"the equation is too long ({MAX_EQUATION} characters at most)")
    return _Parser(text, names).parse()


def _eval(node, get: Callable[[str], np.ndarray]) -> np.ndarray:
    kind, op, *args = node
    if op == "const":
        return np.float64(args[0])
    if op == "var":
        return get(args[0])
    if op == "neg":
        return -_eval(args[0], get)
    if op == "abs":
        return np.abs(_eval(args[0], get))
    if op in ("min", "max"):
        a, b = (_eval(x, get) for x in args)
        return np.minimum(a, b) if op == "min" else np.maximum(a, b)
    if op in ("+", "-", "*", "/"):
        a, b = (_eval(x, get) for x in args)
        with np.errstate(divide="ignore", invalid="ignore"):
            r = a + b if op == "+" else a - b if op == "-" else a * b if op == "*" else np.where(b == 0, np.nan, a / np.where(b == 0, 1, b))
        return r
    if op in _CMP:
        a, b = (np.asarray(_eval(x, get), float) for x in args)
        with np.errstate(invalid="ignore"):
            r = {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "==": a == b, "!=": a != b}[op].astype(float)
        return np.where(np.isnan(a) | np.isnan(b), np.nan, r)
    if op == "not":
        return 1.0 - _eval(args[0], get)
    a, b = (np.asarray(_eval(x, get), float) for x in args)
    if op == "and":
        return np.where((a == 0) | (b == 0), 0.0, np.where((a == 1) & (b == 1), 1.0, np.nan))
    return np.where((a == 1) | (b == 1), 1.0, np.where((a == 0) & (b == 0), 0.0, np.nan))      # or


# --- criteria and rules ------------------------------------------------------------------------------------------

def as_text(c: dict) -> str:
    """The condition of a criterion as a person reads it."""
    return c["expression"].strip() if c.get("expression") else f"{c['variable']} {c['op']} {float(c['value']):g}"


def check_criterion(c: dict, names: set[str]) -> None:
    if not isinstance(c, dict):
        raise CriteriaError("each criterion must be an object")
    if c.get("role") not in ROLES:
        raise CriteriaError("role must be required or preferred")
    if c.get("expression") is not None:
        parse(c["expression"], names)
        return
    if c.get("variable") not in names:
        raise CriteriaError(f"unknown variable '{str(c.get('variable'))[:40]}' (valid: {', '.join(sorted(names))})")
    if c.get("op") not in OPS:
        raise CriteriaError(f"op must be one of {', '.join(OPS)}")
    v = c.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise CriteriaError("value must be a number")


def check_rule(rule: dict, names: set[str]) -> None:
    crit = rule.get("criteria") if isinstance(rule, dict) else None
    if not isinstance(crit, list) or not crit:
        raise CriteriaError("a rule needs a list of criteria")
    if len(crit) > MAX_CRITERIA:
        raise CriteriaError(f"{MAX_CRITERIA} criteria at most")
    for c in crit:
        check_criterion(c, names)
    if not any(c["role"] == "required" for c in crit):
        raise CriteriaError("a rule needs at least one required criterion: preferred ones only order the candidates")


def condition(text_or_crit, col, body: str, targets: list[str]) -> np.ndarray:
    """State of a condition in every cell: 1 met, 0 failed, NaN unknown."""
    names = {v["id"] for v in variables(body, targets)}
    text = text_or_crit if isinstance(text_or_crit, str) else as_text(text_or_crit)
    tree = parse(text, names)
    cache: dict[str, np.ndarray] = {}

    def get(name):
        if name not in cache:
            cache[name] = values(name, col, body, targets)
        return cache[name]
    out = np.asarray(_eval(tree, get), float)
    return np.broadcast_to(out, (_n(col),)).copy() if out.ndim == 0 else out


def select(col, body: str, targets: list[str], rule: dict) -> dict:
    """Candidates (all required met), to check (one required unknown, none failed), excluded (one required failed)."""
    names = {v["id"] for v in variables(body, targets)}
    check_rule(rule, names)
    states = [condition(c, col, body, targets) for c in rule["criteria"]]
    roles = [c["role"] for c in rule["criteria"]]
    n = _n(col)
    req = np.stack([s for s, r in zip(states, roles) if r == "required"]) if n else np.zeros((1, 0))
    pref = [s for s, r in zip(states, roles) if r == "preferred"]
    failed = (req == 0).any(axis=0)
    met = (req == 1).all(axis=0)
    state = np.where(met, "candidate", np.where(failed, "excluded", "to check")).astype(object)
    pm = np.sum([p == 1 for p in pref], axis=0).astype(int) if pref else np.zeros(n, int)
    pu = np.sum([np.isnan(p) for p in pref], axis=0).astype(int) if pref else np.zeros(n, int)
    conf = np.nan_to_num(values("confidence", col, body, targets), nan=-1.0)
    cand = np.flatnonzero(met)
    order = cand[np.lexsort((cand, -conf[cand], pu[cand], -pm[cand]))]
    return {"state": state, "states": states, "preferred_met": pm, "preferred_unknown": pu, "order": order,
            "counts": {k: int((state == k).sum()) for k in ("candidate", "to check", "excluded")}}


# --- check on known sites --------------------------------------------------------------------------------------

_RANK = {"candidate": 0, "excluded": 1, "to check": 2}


def site_check(points: list[dict], negatives: list[str], chapters: list[int]) -> dict:
    """Known sites: a chapter is recovered when one of its points is a candidate, excluded when its points with data
    are all excluded, to check otherwise (the T53 rule). Negatives that come out as candidates are false alarms."""
    out = {}
    for ch in chapters:
        pts = [p for p in points if p["chapter"] == ch]
        if not pts:
            continue
        best = min((p["state"] for p in pts), key=_RANK.get)
        out[ch] = {"state": best, "sites": pts}
    states = [c["state"] for c in out.values()]
    return {"chapters": out, "recovered": states.count("candidate"), "with_data": len(states) - states.count("to check"),
            "unknown": states.count("to check"), "false_alarms": sum(1 for s in negatives if s == "candidate"),
            "negatives": len(negatives)}


def known_points(features: list[dict]) -> tuple[list[dict], list[int], list[dict]]:
    """Catalogue points of the chapters that list the features (R66), and the 18 random negatives."""
    from discovery import known_analogs as ka
    sites, _ = ka.load_sites()
    chapters = sorted({ch for f in features for ch in ka.chapters_of(f["body"], f["feature"])})
    neg = yaml.safe_load((ROOT / "data/validation/negatives.yaml").read_text(encoding="utf-8"))["negatives"]
    negatives = [{"name": f"{n['class_name']} ({n['lat']:.2f}, {n['lon']:.2f})", "lat": n["lat"], "lon": n["lon"]} for n in neg]
    return [s for s in sites if s["chapter"] in chapters], chapters, negatives


@lru_cache(maxsize=1)
def presets() -> list[dict]:
    """The presets, each with its full criteria list (`extra` appended) and the source text of each criterion."""
    doc = yaml.safe_load(PRESETS.read_text(encoding="utf-8"))
    out = []
    for p in doc["presets"]:
        p = dict(p)
        p["criteria"] = [{**c, "source_text": doc["sources"].get(c["source"], {"en": c["source"], "fr": c["source"]})}
                         for c in list(p["criteria"]) + list(p.pop("extra", []))]
        out.append(p)
    return out
