"""Search by jurisdiction: run every live registry adapter for a country, then list one-click links for the rest.

    python -m tracker search uk "Nscale"          live: Companies House, Gazette, Find Case Law, GLEIF (GB)
    python -m tracker search lu,ie "Nscale"       several jurisdictions at once (aliases like 'lux' work)
    python -m tracker sources lu                  the directory: every source for a jurisdiction, free and paid

The directory of sources is data in data/source_directory.yaml; this module only adds the adapters that can
query a source live. Each adapter takes a name and returns Hits. Search results are leads, not statements:
confirm a hit in the register before recording a fact.
"""

import os
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache

import yaml

from . import net
from .model import DATA_DIR

DIRECTORY = DATA_DIR / "source_directory.yaml"
ATOM = "{http://www.w3.org/2005/Atom}"
LIMIT = 20
# Adapters written from the provider's documentation but not yet run against the live service.
UNTESTED = {"fr_bodacc", "nl_kvk"}


@dataclass
class Hit:
    name: str
    id: str = ""
    detail: str = ""
    date: str = ""
    url: str = ""


@lru_cache(maxsize=None)
def directory(path=DIRECTORY):
    return yaml.safe_load(path.read_text())


def jurisdiction_key(text, d=None):
    """'UK', 'gb', 'lux' -> 'uk', 'uk', 'lu'. Raises KeyError for unknown names."""
    d = d or directory()
    t = text.strip().lower()
    for key, j in d["jurisdictions"].items():
        if t == key or t in j.get("aliases", []) or t == str(j.get("country", "")).lower():
            return key
    raise KeyError(f"unknown jurisdiction '{text}'; known: {', '.join(d['jurisdictions'])}")


def resources(jur=None, channel=None, access=None, d=None):
    d = d or directory()
    return [r for r in d["resources"]
            if (jur is None or r["jurisdiction"] == jur)
            and (channel is None or channel in r["channels"])
            and (access is None or r["access"] in access)]


def link(resource, term):
    """The best page for a person to look the name up: a search URL with the name filled in, else the landing page."""
    if resource.get("search_url"):
        return resource["search_url"].replace("{q}", urllib.parse.quote(term)), True
    return resource["url"], False


# ---------- adapters ----------

def _atom_entries(body):
    return [e for e in ET.fromstring(body) if e.tag == f"{ATOM}entry"] if body else []


def eu_gleif(term, country=None):
    params = {"filter[fulltext]": term, "page[size]": LIMIT}
    if country:
        params["filter[entity.legalAddress.country]"] = country
    data = net.get_json("https://api.gleif.org/api/v1/lei-records?" + urllib.parse.urlencode(params))
    hits = []
    for r in data.get("data", []):
        e = r["attributes"]["entity"]
        reg = e.get("registeredAs") or ""
        ra = (e.get("registeredAt") or {}).get("id") or ""
        hits.append(Hit(e["legalName"]["name"], r["id"],
                        f"{e['legalAddress']['country']} · reg no {reg or '?'} ({ra}) · {e.get('status', '')}".strip(),
                        url=f"https://search.gleif.org/#/record/{r['id']}"))
    return hits


def eu_esef(term):
    flt = f'[{{"name":"name","op":"ilike","val":"%{term}%"}}]'
    data = net.get_json("https://filings.xbrl.org/api/entities?" + urllib.parse.urlencode({"filter": flt, "page[size]": LIMIT}))
    return [Hit(e["attributes"]["name"], e["attributes"]["identifier"], "ESEF filer (LEI)",
                url=f"https://filings.xbrl.org/api/entities/{e['attributes']['identifier']}/filings")
            for e in data.get("data", [])]


def uk_ch(term):
    from .monitor import _ch_key
    data = net.get_json("https://api.company-information.service.gov.uk/search/companies?"
                        + urllib.parse.urlencode({"q": term, "items_per_page": LIMIT}), {"Authorization": _ch_key()})
    return [Hit(i.get("title", ""), i.get("company_number", ""),
                f"{i.get('company_status', '')} · {i.get('address_snippet', '')}", i.get("date_of_creation", ""),
                f"https://find-and-update.company-information.service.gov.uk/company/{i.get('company_number', '')}")
            for i in data.get("items", [])]


def uk_gazette(term):
    q = urllib.parse.urlencode({"text": f'"{term}"', "results-page-size": LIMIT, "sort-by": "latest-date"})
    body, _ = net.get(f"https://www.thegazette.co.uk/insolvency/notice/data.feed?{q}")
    hits = []
    for e in _atom_entries(body):
        cat = e.find(f"{ATOM}category")
        page = next((l.get("href") for l in e.findall(f"{ATOM}link") if not l.get("rel")), e.findtext(f"{ATOM}id"))
        hits.append(Hit(e.findtext(f"{ATOM}title", ""), (e.findtext(f"{ATOM}id") or "").rsplit("/", 1)[-1],
                        cat.get("term", "") if cat is not None else "", (e.findtext(f"{ATOM}published") or "")[:10], page))
    return hits


def uk_caselaw(term):
    q = urllib.parse.urlencode({"query": f'"{term}"', "per_page": LIMIT})   # relevance order: date order surfaces weak matches
    body, _ = net.get(f"https://caselaw.nationalarchives.gov.uk/atom.xml?{q}")
    hits = []
    for e in _atom_entries(body):
        alt = next((l.get("href") for l in e.findall(f"{ATOM}link") if l.get("rel") == "alternate"), "")
        cite = next((i.text for i in e if i.tag.endswith("identifier") and (i.text or "").startswith("[")), "")
        hits.append(Hit(e.findtext(f"{ATOM}title", ""), cite, "judgment", (e.findtext(f"{ATOM}published") or "")[:10], alt))
    return hits


def ie_cro(term):
    q = urllib.parse.urlencode({"resource_id": "3fef41bc-b8f4-4b10-8434-ce51c29b1bba", "q": term, "limit": LIMIT})
    data = net.get_json(f"https://opendata.cro.ie/api/3/action/datastore_search?{q}")
    return [Hit(r["company_name"], str(r["company_num"]),
                f"{(r.get('company_status') or '').strip()} · {r.get('company_type', '')}", (r.get("company_reg_date") or "")[:10],
                "https://core.cro.ie/")
            for r in data.get("result", {}).get("records", [])]


def fr_entreprises(term):
    data = net.get_json("https://recherche-entreprises.api.gouv.fr/search?" + urllib.parse.urlencode({"q": term, "per_page": LIMIT}))
    out = []
    for r in data.get("results", []):
        status = {"A": "active", "C": "closed"}.get(r.get("etat_administratif"), r.get("etat_administratif", ""))
        town = (r.get("siege") or {}).get("libelle_commune") or ""
        out.append(Hit(r.get("nom_complet", ""), r.get("siren", ""), f"{status} · {town}", r.get("date_creation", ""),
                       f"https://annuaire-entreprises.data.gouv.fr/entreprise/{r.get('siren', '')}"))
    return out


def fr_bodacc(term):
    q = urllib.parse.urlencode({"where": f'search(commercant, "{term}")', "order_by": "dateparution desc", "limit": LIMIT})
    data = net.get_json(f"https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records?{q}")
    return [Hit(r.get("commercant", ""), str(r.get("registre") or ""),
                f"{r.get('familleavis_lib', '')} · {r.get('tribunal', '')}", r.get("dateparution", ""), r.get("url_complete", ""))
            for r in data.get("results", [])]


def nl_kvk(term):
    key = os.environ.get("KVK_API_KEY")
    if not key:
        raise RuntimeError("needs KVK_API_KEY (paid KVK API); use the search link instead")
    data = net.get_json("https://api.kvk.nl/api/v2/zoeken?" + urllib.parse.urlencode({"naam": term, "resultatenPerPagina": LIMIT}),
                        {"apikey": key})
    return [Hit(r.get("naam", ""), r.get("kvkNummer", ""), r.get("type", ""),
                url=f"https://www.kvk.nl/zoeken/?source=all&q={r.get('kvkNummer', '')}")
            for r in data.get("resultaten", [])]


def no_brreg(term):
    data = net.get_json("https://data.brreg.no/enhetsregisteret/api/enheter?" + urllib.parse.urlencode({"navn": term, "size": LIMIT}))
    flags = {"konkurs": "BANKRUPT", "underAvvikling": "in liquidation",
             "underTvangsavviklingEllerTvangsopplosning": "forced dissolution",
             "underRekonstruksjonsforhandling": "in reconstruction"}
    out = []
    for e in data.get("_embedded", {}).get("enheter", []):
        marks = [label for k, label in flags.items() if e.get(k)]
        out.append(Hit(e.get("navn", ""), e.get("organisasjonsnummer", ""),
                       " · ".join([(e.get("organisasjonsform") or {}).get("kode", "")] + marks),
                       e.get("registreringsdatoEnhetsregisteret", ""),
                       f"https://virksomhet.brreg.no/nb/oppslag/enheter/{e.get('organisasjonsnummer', '')}"))
    return out


def fi_prh(term):
    data = net.get_json("https://avoindata.prh.fi/opendata-ytj-api/v3/companies?" + urllib.parse.urlencode({"name": term}))
    out = []
    for c in data.get("companies", [])[:LIMIT]:
        names = c.get("names") or [{}]
        situations = [s.get("type", "") for s in c.get("companySituations") or []]
        detail = "situations: " + ", ".join(situations) if situations else "no bankruptcy/restructuring situation recorded"
        bid = (c.get("businessId") or {}).get("value", "")
        out.append(Hit(names[0].get("name", ""), bid, detail, c.get("registrationDate", ""),
                       f"https://tietopalvelu.ytj.fi/yritys/{bid}"))
    return out


def us_edgar(term):
    """Every filing naming the term, newest first, without fund-registration noise (the watchlist's ignore_kinds)."""
    from .monitor import WATCHLIST, edgar_hits
    ignore = set(yaml.safe_load(WATCHLIST.read_text()).get("ignore_kinds", []))
    hits = edgar_hits(term, "2001-01-01", {"User-Agent": net.user_agent(require_contact=True)})
    out = {}
    for h in hits:
        s = h["_source"]
        if s.get("form") in ignore:
            continue
        acc, filename = h["_id"].split(":")
        out.setdefault(acc, Hit(s["display_names"][0], acc, s.get("form", ""), s.get("file_date", ""),
                                f"https://www.sec.gov/Archives/edgar/data/{s['ciks'][0].lstrip('0')}/{acc.replace('-', '')}/{filename}"))
    return sorted(out.values(), key=lambda x: x.date, reverse=True)


ADAPTERS = {f.__name__: f for f in (eu_gleif, eu_esef, uk_ch, uk_gazette, uk_caselaw, ie_cro, fr_entreprises,
                                    fr_bodacc, nl_kvk, no_brreg, fi_prh, us_edgar)}


def search(jur, term, live=True, d=None):
    """Run a jurisdiction's live adapters. Returns (results, failures, links).

    results: [(resource, [Hit])]; failures: [(resource name, message)]; links: [(resource, url, filled)].
    GLEIF runs for every country jurisdiction, filtered to that country, because the LEI record gives the
    registry number needed to open the company in its national register."""
    d = d or directory()
    j = d["jurisdictions"][jur]
    own = resources(jur, d=d)
    runs = [(r, ADAPTERS[r["adapter"]], {}) for r in own if r.get("adapter") in ADAPTERS]
    if j.get("country") and jur != "eu":
        gleif = next(r for r in d["resources"] if r["id"] == "eu_gleif")
        runs.append((gleif, eu_gleif, {"country": j["country"]}))
    results, failures = [], []
    if live:
        for res, fn, kw in runs:
            try:
                results.append((res, fn(term, **kw)))
            except Exception as e:   # noqa: BLE001 - one source failing must not hide the others
                failures.append((res["name"], f"{type(e).__name__}: {str(e)[:160]}"))
    links = [(r, *link(r, term)) for r in own]
    return results, failures, links


def format_search(jur, term, results, failures, links, d=None, show=8):
    d = d or directory()
    j = d["jurisdictions"][jur]
    lines = [f"=== {j['name']}: \"{term}\"", f"Restructuring regimes: {j['regimes']}" if j.get("regimes") else ""]
    for res, hits in results:
        tag = " [adapter untested]" if res.get("adapter") in UNTESTED else ""
        lines.append(f"\n{res['name']}{tag}: {len(hits)} hit(s)")
        for h in hits[:show]:
            lines.append(f"  - {h.name} [{h.id}] {h.detail}" + (f" · {h.date}" if h.date else "") + (f"\n    {h.url}" if h.url else ""))
        if len(hits) > show:
            lines.append(f"  ... {len(hits) - show} more")
    for name, msg in failures:
        lines.append(f"\n{name}: not searched ({msg})")
    lines.append("\nLook up by hand (search links have the name filled in):")
    searched = {res["id"] for res, _ in results}
    for r, url, filled in links:
        if r["id"] in searched:
            continue
        if r.get("gap"):
            lines.append(f"  - {r['name']}: {r['what']}")
            continue
        lines.append(f"  - {r['name']} [{r['access']}]{'' if filled else ' (search on site)'}: {url}")
    return "\n".join(l for l in lines if l is not None)


def format_sources(rows, d=None):
    d = d or directory()
    lines, current = [], None
    for r in sorted(rows, key=lambda r: (list(d["jurisdictions"]).index(r["jurisdiction"]), r["id"])):
        if r["jurisdiction"] != current:
            current = r["jurisdiction"]
            lines.append(f"\n=== {d['jurisdictions'][current]['name']}")
        lines.append(f"- {r['name']}  [{r['access']} · {r['api']} · automation {r['automation']}]"
                     f"  {', '.join(r['channels'])}\n    {r['what']}\n    {r['url']}")
    return "\n".join(lines).lstrip()


def validate_directory(d=None):
    """Problems with the directory file: unknown jurisdictions, channels, access levels or adapters."""
    d = d or directory()
    problems, ids = [], set()
    for r in d["resources"]:
        where = f"source directory {r.get('id')}"
        if r.get("id") in ids:
            problems.append(f"{where}: duplicate id")
        ids.add(r.get("id"))
        for field in ("jurisdiction", "name", "channels", "access", "api", "automation", "url", "what"):
            if not r.get(field):
                problems.append(f"{where}: missing {field}")
        if r.get("jurisdiction") not in d["jurisdictions"]:
            problems.append(f"{where}: unknown jurisdiction '{r.get('jurisdiction')}'")
        problems += [f"{where}: unknown channel '{c}'" for c in r.get("channels", []) if c not in d["channels"]]
        if r.get("access") not in d["access_levels"]:
            problems.append(f"{where}: unknown access '{r.get('access')}'")
        if r.get("api") not in ("api", "bulk", "feed", "web"):
            problems.append(f"{where}: api must be api, bulk, feed or web")
        if r.get("automation") not in ("ok", "limited", "manual"):
            problems.append(f"{where}: automation must be ok, limited or manual")
        if r.get("adapter") and r["adapter"] not in ADAPTERS:
            problems.append(f"{where}: no adapter named '{r['adapter']}'")
        if r.get("search_url") and "{q}" not in r["search_url"]:
            problems.append(f"{where}: search_url needs {{q}}")
        if r.get("id_url") and "{id}" not in r["id_url"]:
            problems.append(f"{where}: id_url needs {{id}}")
    return problems
