"""Primary-source monitor: finds new filings about a group and logs them as events.

Events are alerts, not facts. An analyst (or a later extraction step) reads each new event
and turns what matters into statements. The log in data/events.csv is append-only; an event
is "new" if its id has never been logged.

Feeds:
  edgar      SEC full-text search for the group's search terms: catches the company's own filings
             and anyone else who files about it (lenders' holdings, landlords, suppliers, customers).
  ch         Companies House filing history and charges for every UK entity with a registry id.
  news       Google News search for the group's terms. Fastest but weakest (grade C): use it to
             know something happened, then confirm in a filing before it becomes an A-grade statement.
"""

import base64
import csv
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

from .model import DATA_DIR

EVENTS = DATA_DIR / "events.csv"
FIELDS = ["event_id", "observed_date", "feed", "group", "subject", "kind", "event_date", "title", "url", "status"]
USER_AGENT = os.environ.get("EDGAR_USER_AGENT", "ai-infrastructure research tracker")
CH_KEY_FILE = Path.home() / ".config" / "ai-infrastructure" / "companies_house_api_key"
WATCHLIST = DATA_DIR / "watchlist.yaml"


def _get_json(url, headers=None, tries=3):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {}
            if e.code in (429, 500, 502, 503) and attempt < tries - 1:
                time.sleep(2 ** (attempt + 1))
                continue
            raise
    return {}


def _ch_key():
    key = os.environ.get("COMPANIES_HOUSE_API_KEY") or (CH_KEY_FILE.read_text().strip() if CH_KEY_FILE.exists() else "")
    if not key:
        raise SystemExit("No Companies House key: set COMPANIES_HOUSE_API_KEY or write it to " + str(CH_KEY_FILE))
    return "Basic " + base64.b64encode(f"{key}:".encode()).decode()


def edgar_events(group, terms, since):
    """One event per filing (accession) that mentions any search term since `since`."""
    events = {}
    for term in terms:
        q = urllib.parse.urlencode({"q": f'"{term}"', "dateRange": "custom", "startdt": since,
                                    "enddt": date.today().isoformat()})
        data = _get_json(f"https://efts.sec.gov/LATEST/search-index?{q}", {"User-Agent": USER_AGENT})
        for hit in data.get("hits", {}).get("hits", []):
            s = hit["_source"]
            acc, filename = hit["_id"].split(":")
            cik = s["ciks"][0].lstrip("0")
            eid = f"edgar:{acc}"
            events.setdefault(eid, dict(
                event_id=eid, feed="edgar", group=group, subject=s["display_names"][0],
                kind=s.get("form", ""), event_date=s.get("file_date", ""),
                title=f"{s.get('form', '')} by {s['display_names'][0]} mentions '{term}'",
                url=f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{filename}"))
        time.sleep(0.2)   # SEC fair access: well under 10 requests/second
    return list(events.values())


def news_events(group, terms):
    """One event per news article (Google News RSS) matching any term."""
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    events = []
    for term in terms:
        q = urllib.parse.urlencode({"q": f'"{term}"', "hl": "en-GB", "gl": "GB", "ceid": "GB:en"})
        req = urllib.request.Request(f"https://news.google.com/rss/search?{q}", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            root = ET.fromstring(r.read())
        for item in root.iter("item"):
            get = lambda tag: (item.findtext(tag) or "").strip()
            try:
                when = parsedate_to_datetime(get("pubDate")).date().isoformat()
            except (TypeError, ValueError):
                when = ""
            events.append(dict(
                event_id=f"news:{get('guid') or get('link')}", feed="news", group=group,
                subject=get("source") or "news", kind="news", event_date=when,
                title=get("title"), url=get("link")))
        time.sleep(1)
    return events


def ch_events(group, companies):
    """One event per filing-history item and per charge, for each (entity_id, company_number)."""
    auth = {"Authorization": _ch_key()}
    base = "https://api.company-information.service.gov.uk/company/"
    events = []
    for entity_id, number in companies:
        history = _get_json(f"{base}{number}/filing-history?items_per_page=50", auth)
        for f in history.get("items", []):
            events.append(dict(
                event_id=f"ch:{number}:filing:{f.get('transaction_id')}", feed="ch", group=group, subject=entity_id,
                kind=f.get("type", ""), event_date=f.get("date", ""),
                title=f"{number} {f.get('type', '')}: {f.get('description', '')}",
                url=f"https://find-and-update.company-information.service.gov.uk/company/{number}/filing-history"))
        charges = _get_json(f"{base}{number}/charges", auth)
        for c in charges.get("items", []):
            holders = ", ".join(p.get("name", "") for p in c.get("persons_entitled", []))
            events.append(dict(
                event_id=f"ch:{number}:charge:{c.get('charge_code') or c.get('id')}:{c.get('status')}", feed="ch",
                group=group, subject=entity_id, kind=f"charge-{c.get('status', '')}",
                event_date=c.get("satisfied_on") or c.get("created_on", ""),
                title=f"{number} charge {c.get('status', '')} in favour of {holders}",
                url=f"https://find-and-update.company-information.service.gov.uk/company/{number}/charges"))
        time.sleep(0.6)   # Companies House: 600 requests / 5 minutes
    return events


def load_events():
    if not EVENTS.exists():
        return []
    with EVENTS.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_new(events, ignore_kinds=(), baseline_days=21):
    """Append events whose id is not already logged. Returns the ones needing triage.

    status: 'new' (needs triage), 'ignored' (a form type on the watchlist's ignore list),
    or 'baseline' (on the very first run, anything older than `baseline_days` is history, not news).
    """
    logged = load_events()
    seen = {e["event_id"] for e in logged}
    feeds_seen = {e["feed"] for e in logged}
    new = [e for e in events if e["event_id"] not in seen]
    first = not EVENTS.exists()
    cutoff = (date.today() - timedelta(days=baseline_days)).isoformat()
    for e in new:
        if e["kind"] in ignore_kinds:
            e["status"] = "ignored"
        elif e["feed"] not in feeds_seen and e["event_date"] < cutoff:
            # first run of this feed: older items are history, not news
            e["status"] = "baseline"
        else:
            e["status"] = "new"
    with EVENTS.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if first:
            w.writeheader()
        for e in sorted(new, key=lambda e: (e["event_date"], e["event_id"])):
            w.writerow({**e, "observed_date": date.today().isoformat()})
    return [e for e in new if e["status"] == "new"]


def uk_companies(store, group_id):
    """(entity_id, registry number) for UK entities of a group that have a registry id."""
    from .model import entities_of_group, resolve
    out = []
    for e in entities_of_group(store, group_id):
        if store.entities[e]["type"] != "legal_entity":
            continue
        reg = resolve(store, e, "registry_id")
        jur = resolve(store, e, "jurisdiction")
        if reg.status == "value" and jur.status == "value" and jur.current[0].value in ("England and Wales", "United Kingdom"):
            out.append((e, reg.current[0].value))
    return out


def run(store, feeds=("edgar", "ch", "news"), lookback_days=45):
    import yaml
    watch = yaml.safe_load(WATCHLIST.read_text())
    since = (date.today() - timedelta(days=lookback_days)).isoformat()
    all_events = []
    for group_id, cfg in watch["groups"].items():
        if "edgar" in feeds:
            all_events += edgar_events(group_id, cfg["edgar_terms"], since)
        if "ch" in feeds:
            all_events += ch_events(group_id, uk_companies(store, group_id))
        if "news" in feeds and cfg.get("news_terms"):
            all_events += news_events(group_id, cfg["news_terms"])
    return append_new(all_events, tuple(watch.get("ignore_kinds", [])))
