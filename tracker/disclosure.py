"""The disclosure map: where each kind of debt leaves a public trace, and the signals that a financing is coming.

    python -m tracker where [<instrument>] [--region uk]     traces with timing, legal basis and sources
    python -m tracker signals [--region uk] [--stage pre]    signs of a financing: pre, closing, after
    python -m tracker refs [<ref id>]                        the citations behind every claim

All content is in data/disclosure_map.yaml; this module only filters and prints it, and `check` validates it
(every ref cited exists, every source id is in the source directory, every region is known).
"""

from functools import lru_cache

import yaml

from . import jurisdictions
from .model import DATA_DIR

MAP = DATA_DIR / "disclosure_map.yaml"
STATUS = ("mandatory", "conditional", "voluntary", "confidential", "none")
EVIDENCE = ("law", "regulator", "market_practice", "judgement")
STAGES = ("pre", "closing", "after")
SPECIAL_REGIONS = {"all": None, "nordics": ("no", "se", "dk", "fi")}


@lru_cache(maxsize=None)
def disclosure_map(path=MAP):
    return yaml.safe_load(path.read_text())


def covers(region, wanted):
    """Does a trace for `region` apply to the region the user asked about?"""
    if wanted is None or region == wanted or region == "all":
        return True
    if region == "nordics":
        return wanted in SPECIAL_REGIONS["nordics"]
    if region == "eu":
        return wanted not in ("us", "uk", "global")   # EU-wide rules (MAR, FIRDS, prospectus) apply in EU states
    return False


def instruments(instrument=None, region=None, m=None):
    m = m or disclosure_map()
    out = []
    for ins in m["instruments"]:
        if instrument and instrument not in (ins["id"], ins["name"]):
            continue
        traces = [t for t in ins["traces"] if covers(t["region"], region)]
        if traces:
            out.append((ins, traces))
    return out


def signals(region=None, stage=None, m=None):
    m = m or disclosure_map()
    d = jurisdictions.directory()
    src = {r["id"]: r for r in d["resources"]}
    out = []
    for s in m["signals"]:
        if stage and s["stage"] != stage:
            continue
        if region and s.get("where") and not any(covers(src.get(w, {}).get("jurisdiction", ""), region) or
                                                 src.get(w, {}).get("jurisdiction") in ("eu", "global") for w in s["where"]):
            continue
        out.append(s)
    return out


def _src_names(ids):
    src = {r["id"]: r for r in jurisdictions.directory()["resources"]}
    return ", ".join(f"{src[i]['name']} [{src[i]['access']}]" if i in src else i for i in ids or [])


def _refs(ids, m):
    return "; ".join(f"{m['references'][r]['title']} <{m['references'][r]['url']}>" for r in ids or [] if r in m["references"])


def format_where(rows, m=None):
    m = m or disclosure_map()
    if not rows:
        return "No instrument matches. Instruments: " + ", ".join(i["id"] for i in m["instruments"])
    lines = []
    for ins, traces in rows:
        lines.append(f"=== {ins['name']}  [{ins['id']}]")
        if ins.get("in_this_sector"):
            lines.append(f"In this sector: {ins['in_this_sector']}")
        for t in traces:
            lines.append(f"\n  [{t['region']}] {t['status'].upper()} ({t['evidence'].replace('_', ' ')})")
            lines.append(f"    what is public: {t['trace']}")
            if t.get("timing"):
                lines.append(f"    when: {t['timing']}")
            if t.get("where"):
                lines.append(f"    where: {_src_names(t['where'])}")
            if t.get("detect"):
                lines.append(f"    tracker: python -m tracker {t['detect']}")
            if t.get("note"):
                lines.append(f"    note: {t['note']}")
            if t.get("refs"):
                lines.append(f"    basis: {_refs(t['refs'], m)}")
        lines.append(f"\n  Never public: {ins.get('never_public', '?')}\n")
    return "\n".join(lines)


def format_signals(rows, m=None):
    m = m or disclosure_map()
    lines = []
    for stage in STAGES:
        group = [s for s in rows if s["stage"] == stage]
        if not group:
            continue
        lines.append(f"\n## {dict(pre='Before closing', closing='At closing', after='After closing')[stage]}")
        for s in group:
            lines.append(f"- {s['name']}  ({s['evidence'].replace('_', ' ')}; {s.get('lead_time', '')})")
            lines.append(f"    why: {s['why']}")
            if s.get("where"):
                lines.append(f"    where: {_src_names(s['where'])}")
            if s.get("detect"):
                lines.append(f"    tracker: python -m tracker {s['detect']}")
            if s.get("refs"):
                lines.append(f"    basis: {_refs(s['refs'], m)}")
    return "\n".join(lines).lstrip() or "No signals match."


def format_refs(ref=None, m=None):
    m = m or disclosure_map()
    items = [(k, v) for k, v in m["references"].items() if ref in (None, k)]
    return "\n".join(f"- {k}: {v['title']}\n    {v['url']}\n    supports: {v['supports']} (checked {v.get('checked', '?')})"
                     for k, v in items) or f"No reference '{ref}'."


def validate_map(m=None):
    m = m or disclosure_map()
    d = jurisdictions.directory()
    ids = {r["id"] for r in d["resources"]}
    regions = set(d["jurisdictions"]) | set(SPECIAL_REGIONS)
    problems = []

    def check(where, item):
        if item.get("region") is not None and item["region"] not in regions:
            problems.append(f"{where}: unknown region '{item['region']}'")
        if "status" in item and item["status"] not in STATUS:
            problems.append(f"{where}: status must be one of {STATUS}")
        if item.get("evidence") not in EVIDENCE:
            problems.append(f"{where}: evidence must be one of {EVIDENCE}")
        problems.extend(f"{where}: unknown source '{w}'" for w in item.get("where") or [] if w not in ids)
        problems.extend(f"{where}: unknown reference '{r}'" for r in item.get("refs") or [] if r not in m["references"])

    for ins in m["instruments"]:
        for i, t in enumerate(ins["traces"]):
            check(f"instrument {ins['id']} trace {i + 1}", t)
    for i, t in enumerate(m.get("borrower_traces", [])):
        check(f"borrower trace {i + 1}", t)
    for s in m["signals"]:
        check(f"signal {s['id']}", s)
        if s.get("stage") not in STAGES:
            problems.append(f"signal {s['id']}: stage must be one of {STAGES}")
    for k, v in m["references"].items():
        for f in ("title", "url", "supports"):
            if not v.get(f):
                problems.append(f"reference {k}: missing {f}")
    return problems
