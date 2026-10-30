"""Pre-financing watcher: signs that a group is setting up, closing or has closed a financing.

    python -m tracker watch                       every group in data/watchlist.yaml, last 90 days
    python -m tracker watch --names "Nscale,Evroc" --since 180
    python -m tracker stream --seconds 300        Companies House charges stream (needs a stream key)

What it looks for, and why, is in data/disclosure_map.yaml (signals); each line printed names its signal so you can
look up the reasoning with `python -m tracker signals`. Checks, per name:

  UK (Companies House, key needed)
    spv_incorporated   companies whose name contains the group name, incorporated since the date. Flags names that
                       look like financing vehicles and companies registered at the group's usual postcode.
    psc_link           the corporate parent of each new company.
    articles_changed   new articles (MA) or resolutions (RESOLUTIONS) at any group company since the date.
    charge_registered  new charges (MR01, MR02); charge_released: satisfactions and releases (MR04, MR05).
  Norway (Brønnøysund)
    spv_incorporated   entities whose name contains the group name, registered since the date.
  Any country (GLEIF)
    new_lei            LEIs first registered since the date whose legal name contains the group name (funds such
                       as ETFs on the group's shares are dropped), with their parent where reported.

A name search can catch unrelated companies; the postcode check and the financing-name flag help, and every signal
is a lead to confirm. Signals go into data/events.csv (feed 'signal') through the daily monitor.
"""

import collections
import json
import re
import urllib.parse
from dataclasses import dataclass
from datetime import date, timedelta

from . import net
from .model import DATA_DIR

CH_API = "https://api.company-information.service.gov.uk"
CH_SITE = "https://find-and-update.company-information.service.gov.uk/company/"
FINANCING_NAME = re.compile(r"\b(hold ?co|holdings?|mid ?co|bid ?co|prop ?co|fin ?co|top ?co|finance|financing|funding|issuer|"
                            r"borrower|spv|gpu|dc|data ?cent(er|re)s?|intermediate|ventures|land|site|campus|opco)\b", re.I)
WATCH_TYPES = {"MA": "articles_changed", "RESOLUTIONS": "articles_changed", "MR01": "charge_registered",
               "MR02": "charge_registered", "MR04": "charge_released", "MR05": "charge_released"}
MAX_COMPANIES = 60          # per name, newest first: caps Companies House calls for very large groups
STREAM_STATE = DATA_DIR / "stream_state.json"


@dataclass
class Signal:
    group: str
    signal: str             # id from disclosure_map.yaml signals
    date: str
    entity: str
    ident: str
    detail: str
    url: str
    source: str


def financing_name(name):
    return bool(FINANCING_NAME.search(name or ""))


def _ch_auth():
    from .monitor import _ch_key
    return {"Authorization": _ch_key()}


def uk_signals(group, name, since):
    auth = _ch_auth()
    companies, start = [], 0
    while start < 500:
        q = urllib.parse.urlencode({"company_name_includes": name, "size": 100, "start_index": start})
        page = net.get_json(f"{CH_API}/advanced-search/companies?{q}", auth)
        items = page.get("items", [])
        companies += items
        start += len(items)
        if not items or start >= int(page.get("hits") or 0):
            break
    postcodes = collections.Counter((c.get("registered_office_address") or {}).get("postal_code") for c in companies)
    home, home_n = (postcodes.most_common(1) or [(None, 0)])[0]
    out = []
    new = [c for c in companies if (c.get("date_of_creation") or "") >= since]
    for c in new:
        pc = (c.get("registered_office_address") or {}).get("postal_code")
        notes = [n for n, ok in (("financing-style name", financing_name(c.get("company_name"))),
                                 (f"same postcode as {home_n - 1} other '{name}' companies ({home})", pc == home and home_n > 1)) if ok]
        out.append(Signal(group, "spv_incorporated", c.get("date_of_creation", ""), c.get("company_name", ""),
                          c.get("company_number", ""), "; ".join(notes) or "name match only: confirm it belongs to the group",
                          CH_SITE + c.get("company_number", ""), "Companies House"))
        for p in net.get_json(f"{CH_API}/company/{c['company_number']}/persons-with-significant-control", auth).get("items", []):
            if "corporate" in p.get("kind", "") or "legal-person" in p.get("kind", ""):   # companies only: no personal data
                out.append(Signal(group, "psc_link", p.get("notified_on", ""), c.get("company_name", ""), c["company_number"],
                                  f"parent: {p.get('name')}", f"{CH_SITE}{c['company_number']}/persons-with-significant-control",
                                  "Companies House"))
    active = sorted([c for c in companies if c.get("company_status") == "active"],
                    key=lambda c: c.get("date_of_creation") or "", reverse=True)[:MAX_COMPANIES]
    for c in active:
        num = c["company_number"]
        q = urllib.parse.urlencode({"category": "incorporation,resolution,mortgage", "items_per_page": 100})
        for f in net.get_json(f"{CH_API}/company/{num}/filing-history?{q}", auth).get("items", []):
            if (f.get("date") or "") < since or f.get("type") not in WATCH_TYPES:
                continue
            from .documents import ch_title
            out.append(Signal(group, WATCH_TYPES[f["type"]], f.get("date", ""), c.get("company_name", ""), num, ch_title(f),
                              f"{CH_SITE}{num}/filing-history/{f.get('transaction_id')}/document?format=pdf&download=0",
                              "Companies House"))
    return out


def no_signals(group, name, since):
    q = urllib.parse.urlencode({"navn": name, "fraRegistreringsdatoEnhetsregisteret": since, "size": 100})
    data = net.get_json(f"https://data.brreg.no/enhetsregisteret/api/enheter?{q}")
    out = []
    for e in data.get("_embedded", {}).get("enheter", []):
        flag = "financing-style name" if financing_name(e.get("navn")) else "name match only: confirm it belongs to the group"
        out.append(Signal(group, "spv_incorporated", e.get("registreringsdatoEnhetsregisteret", ""), e.get("navn", ""),
                          e.get("organisasjonsnummer", ""), flag,
                          f"https://virksomhet.brreg.no/nb/oppslag/enheter/{e.get('organisasjonsnummer', '')}", "Brønnøysund"))
    return out


def lei_signals(group, name, since):
    params = {"filter[fulltext]": name, "filter[registration.initialRegistrationDate]": f">{since}", "page[size]": 100}
    data = net.get_json("https://api.gleif.org/api/v1/lei-records?" + urllib.parse.urlencode(params))
    out = []
    for r in data.get("data", []):
        e, reg = r["attributes"]["entity"], r["attributes"]["registration"]
        if e.get("category") == "FUND" or not re.search(re.escape(name), e["legalName"]["name"], re.I):
            continue    # ETFs on the group's shares, and full-text hits that do not carry the name
        parent = (net.get_json(f"https://api.gleif.org/api/v1/lei-records/{r['id']}/direct-parent").get("data") or {})
        pname = parent.get("attributes", {}).get("entity", {}).get("legalName", {}).get("name")
        where = e["legalAddress"].get("region") or e["legalAddress"].get("country")
        out.append(Signal(group, "new_lei", reg.get("initialRegistrationDate", "")[:10], e["legalName"]["name"], r["id"],
                          f"{where}; " + (f"parent: {pname}" if pname else "no parent reported yet")
                          + ("; financing-style name" if financing_name(e["legalName"]["name"]) else ""),
                          f"https://search.gleif.org/#/record/{r['id']}", "GLEIF"))
    return out


def watch(groups, since_days=90):
    """groups: {group id: [names]}. Returns (signals, failures). Each source runs on its own."""
    since = (date.today() - timedelta(days=since_days)).isoformat()
    signals, failures = [], []
    for group, names in groups.items():
        for name in names:
            for label, fn in (("Companies House", uk_signals), ("Brønnøysund", no_signals), ("GLEIF", lei_signals)):
                try:
                    signals += fn(group, name, since)
                except Exception as e:   # noqa: BLE001 - report and carry on
                    failures.append(f"{label} for '{name}': {type(e).__name__}: {str(e)[:150]}")
    seen, unique = set(), []
    for s in signals:
        key = (s.signal, s.ident, s.date, s.detail)
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique, failures


def watch_groups(path=DATA_DIR / "watchlist.yaml"):
    import yaml
    w = yaml.safe_load(path.read_text())
    groups = {g: cfg.get("watch_names") or cfg.get("news_terms") or cfg.get("edgar_terms") or [] for g, cfg in w["groups"].items()}
    groups.update({g: names for g, names in (w.get("watch_only") or {}).items()})
    return groups


def to_events(signals):
    return [dict(event_id=f"signal:{s.signal}:{s.source}:{s.ident}:{s.date}:{s.detail[:40]}", feed="signal", group=s.group,
                 subject=s.entity, kind=s.signal, event_date=s.date, title=f"{s.signal}: {s.entity} ({s.detail})", url=s.url)
            for s in signals]


def financing_waves(signals, window_days=3, min_companies=2):
    """Charges created at several group companies within a few days of each other: usually one financing, because a
    facility's security package is signed at closing across every obligor. Returns
    [(first date, last date, [(company, ident)], companies whose articles changed within 60 days either side)]."""
    from datetime import date as d
    charges = []
    for s in signals:
        if s.signal != "charge_registered":
            continue
        m = re.search(r"created (\d{4}-\d{2}-\d{2})", s.detail)
        charges.append((m.group(1) if m else s.date, s.entity, s.ident))
    charges.sort()
    waves, current = [], []
    for c in charges:
        if current and (d.fromisoformat(c[0]) - d.fromisoformat(current[0][0])).days > window_days:
            waves.append(current)
            current = []
        current.append(c)
    if current:
        waves.append(current)
    out = []
    for w in waves:
        companies = sorted({(c[1], c[2]) for c in w})
        if len(companies) < min_companies:
            continue
        first, last = w[0][0], w[-1][0]
        idents = {c[1] for c in companies}
        prep = sorted({s.entity for s in signals if s.signal == "articles_changed" and s.ident in idents
                       and abs((d.fromisoformat(first) - d.fromisoformat(s.date)).days) <= 60})
        out.append((first, last, companies, prep))
    return out


def format_watch(signals, failures):
    from .disclosure import disclosure_map
    meta = {s["id"]: s for s in disclosure_map()["signals"]}
    meta.setdefault("charge_released", {"name": "Charge satisfied or released", "stage": "closing",
                                        "why": "Repayment or refinancing: compare with new charges around the same date"})
    order = {"pre": 0, "closing": 1, "after": 2}
    lines = [f"not searched: {f}" for f in failures]
    for group in sorted({s.group for s in signals}):
        lines.append(f"\n=== {group}")
        mine = [s for s in signals if s.group == group]
        waves = financing_waves(mine)
        if waves:
            lines.append("\n## Likely financings: charges created at several companies within 3 days")
            for first, last, companies, prep in sorted(waves, reverse=True):
                when = first if first == last else f"{first} to {last}"
                lines.append(f"  - {when}: {len(companies)} companies charged: {', '.join(c for c, _ in companies[:8])}"
                             + (" …" if len(companies) > 8 else ""))
                if prep:
                    lines.append(f"      articles or resolutions changed at {len(prep)} of them within 60 days "
                                 "(lenders taking share security need transfer restrictions removed)")
        for sig in sorted({s.signal for s in mine}, key=lambda k: (order.get(meta.get(k, {}).get("stage"), 9), k)):
            m = meta.get(sig, {})
            rows = sorted([s for s in mine if s.signal == sig], key=lambda s: s.date, reverse=True)
            lines.append(f"\n## {m.get('name', sig)} [{sig}, {m.get('stage', '?')}]: {len(rows)}")
            lines.append(f"   why it matters: {m.get('why', '')}")
            for s in rows[:25]:
                lines.append(f"  - {s.date}  {s.entity} ({s.ident}): {s.detail}\n      {s.url}")
            if len(rows) > 25:
                lines.append(f"    ... {len(rows) - 25} more")
    return "\n".join(lines).strip() or "No signals in the period."


# ---------- Companies House charges stream ----------

def stream_charges(seconds=300, numbers=None):
    """Read the charges stream for up to `seconds`, resuming from the saved timepoint. Keeps events for company
    numbers in `numbers` (all events if None). Needs COMPANIES_HOUSE_STREAM_KEY: stream keys are created separately
    from REST keys in the Companies House developer hub. Untested here: no stream key was available."""
    import base64
    import os
    import time
    import urllib.request
    key = os.environ.get("COMPANIES_HOUSE_STREAM_KEY")
    if not key:
        raise RuntimeError("Set COMPANIES_HOUSE_STREAM_KEY (create a stream key in the Companies House developer hub)")
    state = json.loads(STREAM_STATE.read_text()) if STREAM_STATE.exists() else {}
    url = "https://stream.companieshouse.gov.uk/charges"
    if state.get("timepoint"):
        url += f"?timepoint={state['timepoint']}"
    req = urllib.request.Request(url, headers={"Authorization": "Basic " + base64.b64encode(f"{key}:".encode()).decode(),
                                               "User-Agent": net.user_agent()})
    events, end = [], time.monotonic() + seconds
    with urllib.request.urlopen(req, timeout=60) as r:
        for line in r:
            if time.monotonic() > end:
                break
            line = line.strip()
            if not line:
                continue    # heartbeat
            ev = json.loads(line)
            state["timepoint"] = ev.get("event", {}).get("timepoint", state.get("timepoint"))
            uri = ev.get("resource_uri", "")
            m = re.match(r"/company/([A-Z0-9]+)/charges", uri)
            if not m or (numbers is not None and m.group(1) not in numbers):
                continue
            d = ev.get("data", {})
            holders = ", ".join(p.get("name", "") for p in d.get("persons_entitled", []))
            events.append(dict(event_id=f"stream:{uri}:{d.get('status')}", feed="stream", group="", subject=m.group(1),
                               kind=f"charge-{d.get('status', '')}", event_date=d.get("created_on") or d.get("delivered_on", ""),
                               title=f"{m.group(1)} charge {d.get('status', '')} in favour of {holders}", url=CH_SITE + m.group(1) + "/charges"))
    STREAM_STATE.write_text(json.dumps(state))
    return events
