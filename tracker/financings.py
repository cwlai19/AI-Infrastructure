"""Financing table and timeline: one row per facility, built from the statements, plus detected financing waves.

    python -m tracker financings [--group <id>] [--csv <path>] [--json <path>]

Rules (all here; nothing else decides what is charted):
  - A financing is an entity of type `facility`. Its values are the resolved values (model.resolve), so conflicts,
    history and analyst reviews apply exactly as in the credit file.
  - Umbrella: a facility that others are `part_of` (entity_links) is listed, but only its parts are summed, so the
    same debt is never counted twice (CCIR's $790M Norway financing = the S-1's $725M term loan + $65M VAT facility).
  - Date: `signing_date`. Without one the financing is "undated": in the table, not on the timeline.
  - Amount: `amount_max` (the commitment), converted to USD with data/fx.yaml (ECB rates, dated) for chart totals;
    the original amount and currency are kept.
  - Instrument: `facility_type`, labelled by INSTRUMENTS below.
  - Region: country of the site the facility is secured on (where the asset is), else the borrower's jurisdiction,
    else the group's headquarters country; grouped by REGIONS below. The countries used are kept.
  - Grade: the grade of the statement behind the amount (A filings and registries, B company and aggregators,
    C news and estimates).
  - Detected waves: charges created at several companies of a group within three days (tracker/watch.py), read from
    data/events.csv (feed 'signal'). They have dates but no terms, and are drawn separately from known facilities.
    A wave is matched to a recorded facility of the same group signed within MATCH_DAYS of it. That is a date match
    only (check that the charged companies are the facility's obligors); an unmatched wave is a lead for a financing
    not yet recorded.
  - Lender holdings: BDC positions from reports/lender_positions_*.csv (python -m tracker lenders), matched to a
    group by its name.
"""

import csv
import json
import re
from datetime import date

import yaml

from .model import DATA_DIR, ROOT, load, resolve

INSTRUMENTS = {
    "term_loan": "Term loan", "delayed_draw_term_loan": "Delayed-draw term loan", "revolver": "Revolver",
    "project_finance": "Project finance", "bond": "Bond / notes", "abs": "ABS / securitisation",
    "vendor_financing": "Vendor financing", "lease_financing": "Lease financing", "convertible_notes": "Convertible notes",
    "private_placement": "Private placement", "holdco_pik": "Holdco / PIK", "preferred_equity": "Preferred equity",
    "other": "Other",
}
REGIONS = [
    ("United States", r"united states|delaware|\bus\b|usa|new york|texas|california|north carolina"),
    ("UK & Ireland", r"united kingdom|england|wales|scotland|northern ireland|jersey|guernsey|isle of man|ireland"),
    ("Nordics", r"norway|sweden|denmark|finland|iceland"),
    ("Continental Europe", r"netherlands|luxembourg|germany|france|spain|italy|portugal|belgium|austria|switzerland|"
                           r"poland|czech|greece|hungary|romania|estonia|latvia|lithuania|slovakia|slovenia|croatia"),
]


MATCH_DAYS = 3


def match_waves(waves_list, facility_rows, days=MATCH_DAYS):
    """Attach to each wave the recorded facilities of its group signed within `days` of the wave's first charge."""
    for w in waves_list:
        wd = date.fromisoformat(w["date"])
        hits = []
        for f in facility_rows:
            if f["group"] != w["group"] or len(f["date"]) < 10:
                continue
            if abs((date.fromisoformat(f["date"][:10]) - wd).days) <= days:
                hits.append(f["name"])
        w["matched"] = hits
    return waves_list


def region_of(country):
    for name, pattern in REGIONS:
        if country and re.search(pattern, country, re.I):
            return name
    return "Other" if country else "Unknown"


def fx_to_usd(amount, currency, fx=None):
    fx = fx or yaml.safe_load((DATA_DIR / "fx.yaml").read_text())
    rates = fx["per_eur"]
    if amount is None or currency not in rates:
        return None
    return amount / rates[currency] * rates["USD"]


def _one(store, entity, prop):
    r = resolve(store, entity, prop)
    return r.current[0] if r.status == "value" and r.current else None


def _many(store, entity, prop):
    r = resolve(store, entity, prop)
    return r.current if r.status in ("value", "multi") else []


def _name(store, entity_id):
    s = _one(store, entity_id, "name") or next(iter(_many(store, entity_id, "name")), None)
    return s.value if s else store.entities.get(entity_id, {}).get("label") or entity_id


def _group_hq(store, group):
    s = _one(store, group.value, "hq_country") if group else None
    return s.value if s else ""


def _num(text):
    from .model import parse_number
    return parse_number(text) if text else None


def facilities(store=None, fx=None):
    store = store or load()
    fx = fx or yaml.safe_load((DATA_DIR / "fx.yaml").read_text())
    umbrellas = {l["entity_b"] for l in store.links if l["relation"] == "part_of" and l["entity_a"].startswith("fac")
                 and store.entities.get(l["entity_b"], {}).get("type") == "facility"}
    parts = {}
    for l in store.links:
        if l["relation"] == "part_of" and l["entity_b"] in umbrellas:
            parts.setdefault(l["entity_b"], []).append(l["entity_a"])
    rows = []
    for fid, ent in store.entities.items():
        if ent["type"] != "facility" or store.canonical.get(fid, fid) != fid:
            continue
        group = _one(store, fid, "group")
        amount = _one(store, fid, "amount_max")
        ftype = _one(store, fid, "facility_type")
        borrower = _one(store, fid, "borrower")
        signing = _one(store, fid, "signing_date")
        site = next(iter(_many(store, fid, "secured_on_site")), None)
        b_country = _one(store, borrower.value, "jurisdiction").value if borrower and _one(store, borrower.value, "jurisdiction") else ""
        a_country = _one(store, site.value, "country").value if site and _one(store, site.value, "country") else ""
        value = _num(amount.value) if amount else None
        currency = amount.unit if amount else ""
        names = [s.value for s in _many(store, fid, "name")]
        sources = []
        for s in [amount, signing, ftype, borrower]:
            if s and s.source in store.sources and store.sources[s.source]["url"] not in [x["url"] for x in sources]:
                src = store.sources[s.source]
                sources.append({"title": src["title"], "url": src["url"], "type": src["type"]})
        rows.append(dict(
            id=fid, group=group.value if group else "", group_name=_name(store, group.value) if group else "",
            name=names[0] if names else ent.get("label") or fid,
            instrument=ftype.value if ftype else "other",
            instrument_label=INSTRUMENTS.get(ftype.value if ftype else "other", "Other"),
            amount=value, currency=currency, amount_usd=fx_to_usd(value, currency, fx),
            date=signing.value if signing else "", year=(signing.value[:4] if signing else ""),
            maturity=(_one(store, fid, "maturity_date").value if _one(store, fid, "maturity_date") else ""),
            status=(_one(store, fid, "status").value if _one(store, fid, "status") else ""),
            borrower=_name(store, borrower.value) if borrower else "", borrower_country=b_country, asset_country=a_country,
            region=region_of(a_country or b_country or _group_hq(store, group)),
            lenders=[_name(store, s.value) for s in _many(store, fid, "lender")],
            agent=[_name(store, s.value) for s in _many(store, fid, "agent")],
            collateral=[s.value for s in _many(store, fid, "collateral")],
            grade=amount.grade if amount else "", umbrella=fid in umbrellas, parts=parts.get(fid, []),
            counted=fid not in umbrellas, sources=sources))
    return sorted(rows, key=lambda r: (r["group"], r["date"] or "9999", r["id"]))


def waves(events_path=DATA_DIR / "events.csv"):
    """Detected financings (charge waves) per group from the monitor's signal events."""
    from .watch import Signal, financing_waves
    if not events_path.exists():
        return []
    with events_path.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["feed"] == "signal" and r["kind"] in ("charge_registered", "articles_changed")]
    by_group = {}
    for r in rows:
        detail = r["title"].split("(", 1)[1].rstrip(")") if "(" in r["title"] else ""
        ident = r["event_id"].split(":")[3] if r["event_id"].count(":") >= 3 else ""
        by_group.setdefault(r["group"], []).append(Signal(r["group"], r["kind"], r["event_date"], r["subject"], ident, detail, r["url"], ""))
    out = []
    for group, sigs in by_group.items():
        for first, last, companies, prep in financing_waves(sigs):
            out.append(dict(group=group, date=first, end=last, companies=[c for c, _ in companies],
                            articles_changed=len(prep), source="Companies House charges (python -m tracker watch)"))
    return sorted(out, key=lambda w: (w["group"], w["date"]))


def holdings(store=None, reports=ROOT / "reports"):
    """BDC positions from the lender reports, with the tracked group they belong to where the name matches."""
    store = store or load()
    group_names = {g: _name(store, g) for g, e in store.entities.items() if e["type"] == "group"}
    out = []
    for path in sorted(reports.glob("lender_positions_*.csv")):
        with path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                term = r["term"].split(", ")[0]
                group = next((g for g, n in group_names.items() if n.lower() == term.lower()), "")
                out.append(dict(group=group, term=term, borrower=r["borrower"], bdc=r["bdc"], period=r["period"],
                                instrument=r["instrument"], kind=r["kind"], fair_value=_num(r["fair_value"]),
                                cost=_num(r["cost"]), mark=r["mark"], url=r["url"], source=path.name))
    return out


def build(store=None):
    store = store or load()
    fx = yaml.safe_load((DATA_DIR / "fx.yaml").read_text())
    fin = facilities(store, fx)
    return dict(built=date.today().isoformat(), fx=dict(as_of=str(fx["as_of"]), source=fx["source"]),
                financings=fin, waves=match_waves(waves(), fin), holdings=holdings(store),
                instruments=INSTRUMENTS, regions=[r for r, _ in REGIONS] + ["Other", "Unknown"])


def write_csv(rows, path):
    cols = ["group_name", "name", "instrument_label", "amount", "currency", "amount_usd", "date", "maturity", "status",
            "borrower", "borrower_country", "asset_country", "region", "lenders", "agent", "grade", "counted", "id"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**r, "lenders": "; ".join(r["lenders"]), "agent": "; ".join(r["agent"])})


def format_table(data, group=None):
    rows = [r for r in data["financings"] if not group or r["group"] == group]
    lines = [f"{len(rows)} financing(s); amounts in USD at ECB rates of {data['fx']['as_of']} (originals kept)"]
    for r in rows:
        amt = f"{r['amount_usd'] / 1e6:,.0f}m" if r["amount_usd"] else "amount unknown"
        flag = "  [umbrella: not summed, parts counted]" if r["umbrella"] else ""
        lines.append(f"  {r['date'] or 'undated':10}  {r['group_name']}: {r['name']} | {r['instrument_label']} | {amt} | "
                     f"{r['region']} | lenders: {', '.join(r['lenders'][:4]) or '?'}{'…' if len(r['lenders']) > 4 else ''} | grade {r['grade']}{flag}")
    ws = [w for w in data["waves"] if not group or w["group"] == group]
    if ws:
        lines.append(f"\n{len(ws)} detected financing wave(s) from charges (terms unknown):")
        lines += [f"  {w['date']}  {w['group']}: {len(w['companies'])} companies charged -> "
                  + (f"date match: {', '.join(w['matched'])} (check the borrower)" if w.get("matched") else "unmatched: a financing not yet recorded?") for w in ws]
    return "\n".join(lines)


def quarter(d):
    return f"{d[:4]}-Q{(int(d[5:7]) - 1) // 3 + 1}" if len(d) >= 7 else (f"{d[:4]}" if d else "")


def dashboard_rows(data):
    """Flat rows for the dashboard: one dataset each for financings, detected waves and lender holdings.
    Display values (USD millions, joined lists) are computed here so the page shows exactly what the data holds."""
    group_names = {r["group"]: r["group_name"] for r in data["financings"]}
    fin = []
    for r in data["financings"]:
        src = r["sources"][0] if r["sources"] else {}
        fin.append(dict(id=r["id"], group=r["group"], group_name=r["group_name"], name=r["name"],
                        instrument=r["instrument_label"], amount_usd_m=round(r["amount_usd"] / 1e6, 1) if r["amount_usd"] else None,
                        amount=r["amount"], currency=r["currency"], date=r["date"], quarter=quarter(r["date"]),
                        year=r["year"], maturity=r["maturity"], status=r["status"].replace("_", " "), region=r["region"],
                        borrower=r["borrower"], country=r["asset_country"] or r["borrower_country"],
                        lenders="; ".join(r["lenders"]), lender_count=len(r["lenders"]), agent="; ".join(r["agent"]),
                        grade=r["grade"], counted=r["counted"], dated=bool(r["date"]),
                        note="umbrella: its parts are counted" if r["umbrella"] else "",
                        source=src.get("title", ""), source_url=src.get("url", "")))
    waves = []
    for w in data["waves"]:
        waves.append(dict(id=f"{w['group']}:{w['date']}", group=w["group"],
                          group_name=group_names.get(w["group"]) or w["group"].replace("group_", "").replace("_", " ").title(),
                          date=w["date"], quarter=quarter(w["date"]), companies=len(w["companies"]),
                          company_names="; ".join(w["companies"]), articles_changed=w["articles_changed"],
                          matched=("date match: " + "; ".join(w["matched"])) if w.get("matched") else "unmatched",
                          source=w["source"]))
    hold = []
    for i, h in enumerate(data["holdings"]):
        hold.append(dict(id=f"h{i}", group=h["group"], term=h["term"], borrower=h["borrower"], bdc=h["bdc"],
                         period=h["period"], instrument=h["instrument"], kind=h["kind"],
                         fair_value_m=round(h["fair_value"] / 1e6, 1) if h["fair_value"] else None,
                         cost_m=round(h["cost"] / 1e6, 1) if h["cost"] else None, mark=h["mark"], url=h["url"]))
    return dict(financings=fin, waves=waves, holdings=hold)
