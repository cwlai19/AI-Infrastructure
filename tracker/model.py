"""Load, validate and resolve statements.

Statements are the only facts. Everything a reader sees (a debt ledger, a
credit file) is a *view* built from them by the rules in `resolve()`.
Nothing is ever overwritten: new information is a new statement.
"""

import csv
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VOCAB_PATH = ROOT / "schema" / "vocabulary.yaml"
DATA_DIR = ROOT / "data"

METHOD_ORDER = ["disclosed", "derived", "reported", "estimated", "checked_absent"]
GRADE_ORDER = ["A", "B", "C"]
LINK_RELATIONS = {"same_as", "part_of"}
REVIEW_VERDICTS = {"rejected", "explained"}
PARENT_JURISDICTION = {"england and wales": "united kingdom", "scotland": "united kingdom",
                       "northern ireland": "united kingdom"}
NUMERIC_KINDS = {"money", "number", "percent", "bps"}
# Two numbers closer than this (relative) are treated as the same value.
NUMERIC_TOLERANCE = 0.001
SUFFIXES = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
DATE_RE = re.compile(r"^(<)?(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$")


@dataclass
class Statement:
    id: str
    entity: str
    property: str
    value: str
    unit: str
    source: str
    locator: str
    effective_date: str
    observed_date: str
    method: str
    derived_from: list
    extractor: str
    note: str
    grade: str = ""


@dataclass
class Store:
    vocab: dict
    sources: dict
    entities: dict
    links: list
    statements: list
    canonical: dict = field(default_factory=dict)
    reviews: dict = field(default_factory=dict)   # statement id -> analyst review row


# ---------- parsing helpers ----------

def parse_number(text):
    """'1.85B' -> 1.85e9, '500' -> 500.0. Returns None if not a number."""
    t = text.strip().replace(",", "").replace("$", "")
    mult = 1.0
    if t and t[-1].upper() in SUFFIXES:
        mult = SUFFIXES[t[-1].upper()]
        t = t[:-1]
    try:
        return float(t) * mult
    except ValueError:
        return None


def date_key(text):
    """Sortable key for 'YYYY', 'YYYY-MM', 'YYYY-MM-DD', optionally prefixed '<' (before).

    A partial date sorts at the start of its period; '<2026-06' sorts just before '2026-06'.
    """
    m = DATE_RE.match(text.strip())
    if not m:
        return None
    before, y, mo, d = m.groups()
    y, mo, d = int(y), int(mo or 0), int(d or 0)
    try:
        date(y, mo or 1, d or 1)
    except ValueError:
        return None
    return (y, mo, d, -1 if before else 0)


def format_value(st):
    if st.method == "checked_absent":
        return "undisclosed"
    n = parse_number(st.value) if st.unit else None
    if n is None:
        return st.value
    if st.unit == "pct":
        return f"{n:g}%"
    for suffix, size in (("B", 1e9), ("M", 1e6)):
        if abs(n) >= size:
            return f"{n / size:,.4g}{suffix} {st.unit}"
    return f"{int(n):,} {st.unit}" if n == int(n) else f"{n:,.4g} {st.unit}"


# ---------- loading ----------

def _read_csv(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)
                if any((v or "").strip() for v in row.values())]


def load(data_dir=DATA_DIR, vocab_path=VOCAB_PATH):
    vocab = yaml.safe_load(vocab_path.read_text())
    sources = {r["id"]: r for r in _read_csv(data_dir / "sources.csv")}
    entities = {r["id"]: r for r in _read_csv(data_dir / "entities.csv")}
    links = _read_csv(data_dir / "entity_links.csv")
    statements = []
    for r in _read_csv(data_dir / "statements.csv"):
        r["derived_from"] = [x for x in r.get("derived_from", "").split(";") if x]
        statements.append(Statement(**r))
    store = Store(vocab, sources, entities, links, statements)
    store.reviews = {r["statement_id"]: r for r in _read_csv(data_dir / "reviews.csv")}
    store.canonical = _canonical_ids(store)
    for st in statements:
        st.grade = _grade(store, st)
    return store


def _canonical_ids(store):
    """Merge entities joined by same_as links (union-find). Merges are judgements kept
    in entity_links.csv, so a wrong merge is undone by deleting one row."""
    parent = {e: e for e in store.entities}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x

    for link in store.links:
        if link["relation"] == "same_as" and link["entity_a"] in parent and link["entity_b"] in parent:
            a, b = sorted((find(link["entity_a"]), find(link["entity_b"])))
            parent[b] = a
    return {e: find(e) for e in store.entities}


def _grade(store, st, _seen=None):
    src = store.sources.get(st.source)
    if not src:
        return "C"
    grade = store.vocab["source_types"].get(src["type"], {}).get("grade", "C")
    if src.get("access") == "excerpt":
        grade = max(grade, "B", key=GRADE_ORDER.index)
    if st.method == "derived":
        # A derived number is only as good as its weakest input.
        _seen = (_seen or set()) | {st.id}
        by_id = {s.id: s for s in store.statements}
        for dep in st.derived_from:
            if dep in by_id and dep not in _seen:
                grade = max(grade, _grade(store, by_id[dep], _seen), key=GRADE_ORDER.index)
    return grade


# ---------- validation ----------

def validate(store):
    """Return a list of human-readable problems. An empty list means the data is clean."""
    errors = []
    v = store.vocab
    types = v["entity_types"]

    for sid, s in store.sources.items():
        if s.get("type") not in v["source_types"]:
            errors.append(f"source {sid}: unknown type '{s.get('type')}'")
        if s.get("access") not in v["access_levels"]:
            errors.append(f"source {sid}: unknown access '{s.get('access')}'")
        for col in ("published_date", "retrieved_date"):
            if s.get(col) and date_key(s[col]) is None:
                errors.append(f"source {sid}: bad {col} '{s[col]}'")

    for eid, e in store.entities.items():
        if e.get("type") not in types:
            errors.append(f"entity {eid}: unknown type '{e.get('type')}'")

    for link in store.links:
        for side in ("entity_a", "entity_b"):
            if link[side] not in store.entities:
                errors.append(f"link {link['entity_a']}->{link['entity_b']}: unknown entity '{link[side]}'")
        if link["relation"] not in LINK_RELATIONS:
            errors.append(f"link {link['entity_a']}->{link['entity_b']}: unknown relation '{link['relation']}'")

    all_ids = {s.id for s in store.statements}
    for sid, r in store.reviews.items():
        if sid not in all_ids:
            errors.append(f"review of {sid}: unknown statement")
        if r.get("verdict") not in REVIEW_VERDICTS:
            errors.append(f"review of {sid}: verdict must be one of {sorted(REVIEW_VERDICTS)}")
        if not r.get("reason"):
            errors.append(f"review of {sid}: a reason is required")

    seen_ids = set()
    for st in store.statements:
        where = f"statement {st.id}"
        if st.id in seen_ids:
            errors.append(f"{where}: duplicate id")
        seen_ids.add(st.id)
        ent = store.entities.get(st.entity)
        if not ent:
            errors.append(f"{where}: unknown entity '{st.entity}'")
            continue
        props = types.get(ent["type"], {}).get("properties", {})
        spec = props.get(st.property)
        if spec is None:
            errors.append(f"{where}: '{st.property}' is not a property of {ent['type']}")
            continue
        if st.source not in store.sources:
            errors.append(f"{where}: unknown source '{st.source}'")
        if st.method not in v["methods"]:
            errors.append(f"{where}: unknown method '{st.method}'")
        if date_key(st.observed_date) is None or st.observed_date.startswith("<"):
            errors.append(f"{where}: observed_date must be a date, got '{st.observed_date}'")
        if st.effective_date and date_key(st.effective_date) is None:
            errors.append(f"{where}: bad effective_date '{st.effective_date}'")
        if st.method == "derived" and not st.derived_from:
            errors.append(f"{where}: derived statements must list derived_from")
        for dep in st.derived_from:
            if dep not in all_ids:
                errors.append(f"{where}: derived_from unknown statement '{dep}'")
        if st.method == "checked_absent":
            if st.value:
                errors.append(f"{where}: checked_absent statements must have an empty value")
            continue
        if not st.value:
            errors.append(f"{where}: empty value (use method checked_absent if the source omits it)")
            continue
        errors.extend(f"{where}: {p}" for p in _check_value(store, st, spec))
    return errors


def _check_value(store, st, spec):
    kind = spec["kind"]
    if kind in NUMERIC_KINDS:
        if parse_number(st.value) is None:
            yield f"'{st.value}' is not a number"
        if kind == "money" and not re.fullmatch(r"[A-Z]{3}", st.unit):
            yield f"money needs a 3-letter currency in unit, got '{st.unit}'"
        if kind == "number" and spec.get("unit") and st.unit != spec["unit"]:
            yield f"unit must be '{spec['unit']}', got '{st.unit}'"
    elif kind == "date":
        if date_key(st.value) is None:
            yield f"'{st.value}' is not a date"
    elif kind == "enum":
        if st.value not in spec["values"]:
            yield f"'{st.value}' not in {spec['values']}"
    elif kind == "bool":
        if st.value not in ("true", "false"):
            yield f"'{st.value}' must be true or false"
    elif kind == "entity":
        target = store.entities.get(st.value)
        if not target:
            yield f"refers to unknown entity '{st.value}'"
        elif target["type"] not in spec["ref"]:
            yield f"'{st.value}' is a {target['type']}, expected {spec['ref']}"


# ---------- resolution: statements -> records ----------

@dataclass
class Resolved:
    entity: str
    property: str
    status: str                 # value | multi | undisclosed | not_checked
    current: list               # statements behind the displayed value(s)
    conflicts: list             # statements that disagree with the current value
    history: list               # earlier values, superseded by later effective dates
    absent: list                # sources we checked that do not state it
    flags: list
    explained: list = field(default_factory=list)   # disagreements an analyst has explained
    rejected: list = field(default_factory=list)    # statements an analyst rejected (kept, not used)


def _dates_overlap(a, b):
    """True if two effective dates can refer to the same moment ('2026-02' vs '2026-02-11')."""
    if a.startswith("<") != b.startswith("<"):
        return False   # 'before June' is never the same moment as 'June'
    return a.startswith(b) or b.startswith(a)


def _same_value(a, b, kind):
    if kind in NUMERIC_KINDS:
        x, y = parse_number(a.value), parse_number(b.value)
        if x is None or y is None:
            return a.value == b.value
        same_unit = a.unit == b.unit or kind != "money"
        return same_unit and abs(x - y) <= NUMERIC_TOLERANCE * max(abs(x), abs(y), 1e-9)
    x, y = a.value.strip().lower(), b.value.strip().lower()
    if kind == "date":
        # '2026-02' and '2026-02-11' agree: the second is a more precise version of the first.
        return x.startswith(y) or y.startswith(x)
    if kind == "text":
        # 'SOFR' and 'Term SOFR' agree: one wording contains the other.
        # 'England and Wales' and 'United Kingdom' agree: one is part of the other.
        return x in y or y in x or PARENT_JURISDICTION.get(x) == y or PARENT_JURISDICTION.get(y) == x
    return x == y


def _strength(store, st):
    """Lower is stronger: source rank, then whether we read the full document, then method.
    A derived value is as strong as its weakest input."""
    if st.method == "derived" and st.derived_from:
        by_id = {s.id: s for s in store.statements}
        inputs = [by_id[i] for i in st.derived_from if i in by_id and by_id[i].method != "derived"]
        if inputs:
            weakest = max(_strength(store, i) for i in inputs)
            return weakest[:2] + (METHOD_ORDER.index("derived"),)
    src = store.sources.get(st.source, {})
    rank = store.vocab["source_types"].get(src.get("type"), {}).get("rank", 99)
    excerpt = 1 if src.get("access") == "excerpt" else 0
    return (rank, excerpt, METHOD_ORDER.index(st.method) if st.method in METHOD_ORDER else 99)


def resolve(store, entity_id, prop):
    """Turn every statement about (entity, property) into one displayable answer.

    Rules, in order:
      1. Values with an effective date describe a point in time. The latest date is current;
         earlier different values are history, not conflicts.
      2. Among statements for the same latest date, the strongest source wins
         (vocabulary rank, then method). Any disagreement among them is a conflict.
      3. Undated values cannot supersede dated ones; if they disagree with the current
         value they are flagged as conflicts.
      4. If nothing states a value but a source was checked, the answer is 'undisclosed'.
         If nothing was checked at all, it is 'not_checked'.
    Multi-valued properties (lenders, collateral types) list every distinct value instead.
    """
    canon = store.canonical.get(entity_id, entity_id)
    members = {e for e, c in store.canonical.items() if c == canon}
    ent_type = store.entities[canon]["type"]
    spec = store.vocab["entity_types"][ent_type]["properties"][prop]
    every = [s for s in store.statements if s.entity in members and s.property == prop]
    rejected = [s for s in every if store.reviews.get(s.id, {}).get("verdict") == "rejected"]
    sts = [s for s in every if s not in rejected]
    absent = [s for s in sts if s.method == "checked_absent"]
    vals = [s for s in sts if s.method != "checked_absent"]

    if not vals:
        return Resolved(canon, prop, "undisclosed" if absent else "not_checked", [], [], [], absent, [],
                        rejected=rejected)

    if spec.get("multi"):
        distinct = []
        for s in sorted(vals, key=lambda s: _strength(store, s)):
            if not any(_same_value(s, d, spec["kind"]) for d in distinct):
                distinct.append(s)
        return Resolved(canon, prop, "multi", distinct, [], [], absent, [], rejected=rejected)

    dated = [s for s in vals if s.effective_date]
    undated = [s for s in vals if not s.effective_date]
    flags, history = [], []
    if dated:
        latest_st = max(dated, key=lambda s: date_key(s.effective_date))
        latest = date_key(latest_st.effective_date)
        # '2026-02' and '2026-02-11' describe the same moment at different precision.
        same_moment = lambda s: _dates_overlap(s.effective_date, latest_st.effective_date)
        top = sorted([s for s in dated if same_moment(s)], key=lambda s: _strength(store, s))
        current = top[0]
        conflicts = [s for s in top[1:] if not _same_value(s, current, spec["kind"])]
        conflicts += [s for s in undated if not _same_value(s, current, spec["kind"])]
        for s in sorted(dated, key=lambda s: (date_key(s.effective_date), _strength(store, s))):
            if not same_moment(s) and date_key(s.effective_date) < latest and not _same_value(s, current, spec["kind"]):
                # Several sources stating the same earlier value are one step of history, not several.
                if not history or not _same_value(history[-1], s, spec["kind"]):
                    history.append(s)
    else:
        ranked = sorted(undated, key=lambda s: _strength(store, s))
        current = ranked[0]
        conflicts = [s for s in ranked[1:] if not _same_value(s, current, spec["kind"])]
    agreeing = [s for s in vals if s is not current and s not in conflicts and s not in history
                and _same_value(s, current, spec["kind"])]
    backing = sorted([current] + agreeing, key=lambda s: _strength(store, s))
    if history and _strength(store, backing[0])[:2] > min(_strength(store, s)[:2] for s in history):
        # The newer value is only supported by weaker sources than the value it replaces.
        flags.append("newer value rests on weaker sources than the value it replaces; confirm the change")
    explained = [s for s in conflicts if store.reviews.get(s.id, {}).get("verdict") == "explained"]
    conflicts = [s for s in conflicts if s not in explained]
    if conflicts:
        flags.append("sources disagree")
    return Resolved(canon, prop, "value", backing, conflicts, history, absent, flags, explained, rejected)


def entities_of_group(store, group_id):
    """Every entity that belongs to a group: the group itself, entities with group=<id>,
    and entities linked to those by part_of."""
    members = {group_id}
    for s in store.statements:
        if s.property == "group" and s.value == group_id and s.method != "checked_absent":
            members.add(store.canonical.get(s.entity, s.entity))
    for link in store.links:
        if link["relation"] == "part_of" and (link["entity_a"] in members or link["entity_b"] in members):
            members.update({link["entity_a"], link["entity_b"]})
    return sorted(members)
