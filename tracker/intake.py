"""Intake: turn a simple CSV of financings (one row per deal) into sourced, validated statements.

    python -m tracker intake data/intake/<file>.csv [--dry-run]

Use it to add data-centre and neocloud financings you find (filings, registers, press releases, news). Template:
data/intake/financings_template.csv. For each row it creates, if missing: the group, the borrower and lenders
(legal entities), the source document, a site carrying the asset country (if given), and the facility; then one
statement per filled field. Ids are derived from the row's content, so running the same file twice adds nothing.
Everything is validated with the normal rules; if anything fails, no file is changed and every problem is listed.

Columns: group_name, borrower, borrower_country, instrument (a facility_type, e.g. term_loan), amount, currency,
signing_date, maturity_date, lenders (separated by ;), agent, status, asset_country, name, source_title, source_url,
source_type (filing, registry, company_release, counterparty_release, news, aggregator, internal...), source_access
(full_document or excerpt), published_date, locator, note.

The repository is public: do not enter data from paid services (9fin, Debtwire, Octus, Bloomberg...) here; keep it
in a private copy.
"""

import csv
import hashlib
import re
import shutil
import tempfile
from datetime import date
from pathlib import Path

from .model import DATA_DIR, load, validate

FILES = ("sources.csv", "entities.csv", "statements.csv")
METHOD_BY_SOURCE = {"filing": "disclosed", "registry": "disclosed", "counterparty_filing": "disclosed",
                    "company_release": "disclosed", "counterparty_release": "disclosed", "rating_agency": "disclosed"}


def slug(text, n=40):
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")[:n]


def short_hash(*parts):
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:8]


def _read(path):
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def plan(rows, existing_entities, existing_sources, existing_statements, today=None):
    """New sources, entities and statements for the intake rows (nothing already present is repeated)."""
    today = today or date.today().isoformat()
    sources, entities, statements = {}, {}, {}

    def entity(eid, etype, label, note=""):
        if eid not in existing_entities and eid not in entities:
            entities[eid] = dict(id=eid, type=etype, label=label, note=note)
        return eid

    for i, r in enumerate(rows, 1):
        r = {k: (v or "").strip() for k, v in r.items()}
        if not r.get("group_name") or not r.get("source_title"):
            raise ValueError(f"row {i}: group_name and source_title are required")
        src = f"src_in_{slug(r['source_title'], 30)}_{short_hash(r['source_title'], r.get('source_url', ''))}"
        if src not in existing_sources and src not in sources:
            sources[src] = dict(id=src, type=r.get("source_type") or "news", access=r.get("source_access") or "full_document",
                                publisher="", title=r["source_title"], url=r.get("source_url", ""),
                                published_date=r.get("published_date", ""), retrieved_date=today, note="added by intake")
        group = entity(f"group_{slug(r['group_name'])}", "group", r["group_name"])
        fac = entity(f"fac_in_{slug(r['group_name'], 20)}_{short_hash(r['group_name'], r.get('instrument', ''), r.get('amount', ''), r.get('signing_date', ''), r.get('borrower', ''))}",
                     "facility", r.get("name") or f"{r['group_name']} {r.get('instrument', 'financing').replace('_', ' ')} {r.get('signing_date', '')}".strip())
        method = METHOD_BY_SOURCE.get(sources.get(src, {}).get("type") or r.get("source_type"), "reported")

        def stmt(ent, prop, value, unit=""):
            if not value:
                return
            sid = f"in{short_hash(ent, prop, value, unit, src)}"
            if sid in existing_statements or sid in statements:
                return
            statements[sid] = dict(id=sid, entity=ent, property=prop, value=value, unit=unit, source=src,
                                   locator=r.get("locator") or "see source", effective_date="", observed_date=today,
                                   method=method, derived_from="", extractor="intake", note=r.get("note", ""))

        stmt(group, "name", r["group_name"])
        stmt(fac, "group", group)
        stmt(fac, "name", r.get("name"))
        stmt(fac, "facility_type", r.get("instrument"))
        stmt(fac, "amount_max", r.get("amount"), r.get("currency", ""))
        stmt(fac, "signing_date", r.get("signing_date"))
        stmt(fac, "maturity_date", r.get("maturity_date"))
        stmt(fac, "status", r.get("status"))
        if r.get("borrower"):
            b = entity(f"le_{slug(r['borrower'])}", "legal_entity", r["borrower"])
            stmt(b, "name", r["borrower"])
            stmt(b, "group", group)
            stmt(b, "jurisdiction", r.get("borrower_country"))
            stmt(fac, "borrower", b)
        for lender in [x.strip() for x in r.get("lenders", "").split(";") if x.strip()]:
            le = entity(f"le_{slug(lender)}", "legal_entity", lender)
            stmt(le, "name", lender)
            stmt(fac, "lender", le)
        if r.get("agent"):
            ag = entity(f"le_{slug(r['agent'])}", "legal_entity", r["agent"])
            stmt(ag, "name", r["agent"])
            stmt(fac, "agent", ag)
        if r.get("asset_country"):
            site = entity(f"site_in_{slug(r['group_name'], 20)}_{slug(r['asset_country'], 20)}", "site",
                          f"{r['group_name']} assets in {r['asset_country']}")
            stmt(site, "group", group)
            stmt(site, "country", r["asset_country"])
            stmt(fac, "secured_on_site", site)
    return sources, entities, statements


def run(path, dry_run=False, data_dir=DATA_DIR):
    """Returns (counts, problems). Writes nothing if there are problems or if dry_run."""
    _, rows = _read(Path(path))
    files = {name: _read(data_dir / name) for name in FILES}
    existing = {name: {r["id"] for r in files[name][1]} for name in FILES}
    sources, entities, statements = plan(rows, existing["entities.csv"], existing["sources.csv"], existing["statements.csv"])
    counts = dict(sources=len(sources), entities=len(entities), statements=len(statements))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for p in data_dir.glob("*.csv"):
            shutil.copy(p, tmp / p.name)
        for name, new in (("sources.csv", sources), ("entities.csv", entities), ("statements.csv", statements)):
            fields, old = files[name]
            with (tmp / name).open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fields)
                w.writeheader()
                w.writerows(old + list(new.values()))
        problems = validate(load(data_dir=tmp))
        if problems or dry_run:
            return counts, problems
        for name in FILES:
            shutil.copy(tmp / name, data_dir / name)
    return counts, []
