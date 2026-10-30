"""Documents by credit question: org chart, guarantors, debt documents, security, financials, restructuring, lenders.

    python -m tracker company uk 16925886          one company's filings sorted by question, then what to read by hand
    python -m tracker company us 2110365           (US: CIK; any country: an LEI works too)
    python -m tracker sector data_centres --jur us,no,uk   debt documents and debt totals across a sector
    python -m tracker documents lu --need guarantors       which document answers a question in a jurisdiction

data/document_types.yaml says which document answers which question and how to recognise it in a feed
(Companies House filing types, EDGAR form and exhibit types, 8-K items). Everything here is a lead to read,
not a statement: record facts in statements.csv after reading the document.
"""

import re
import urllib.parse
from dataclasses import dataclass, field
from functools import lru_cache

import yaml

from . import jurisdictions, net
from .model import DATA_DIR

TAXONOMY = DATA_DIR / "document_types.yaml"
LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
CH_SITE = "https://find-and-update.company-information.service.gov.uk/company/"
CH_API = "https://api.company-information.service.gov.uk/company/"
SEC_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/"
MAX_PAGES = 5


@dataclass
class Doc:
    need: str
    title: str
    date: str = ""
    url: str = ""
    kind: str = ""          # the document type's name from the taxonomy


@dataclass
class Dossier:
    name: str
    jurisdiction: str
    ids: dict = field(default_factory=dict)        # lei, registry number, cik
    docs: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    failures: list = field(default_factory=list)


@lru_cache(maxsize=None)
def taxonomy(path=TAXONOMY):
    return yaml.safe_load(path.read_text())


# ---------- classification ----------

def _matches(code, patterns):
    code = (code or "").upper()
    return any(code.startswith(p[:-1].upper()) if p.endswith("*") else code == p.upper() for p in patterns or [])


def classify(ch=None, edgar_form=None, edgar_type=None, edgar_items=None, t=None):
    """Document types (taxonomy entries) that a filing matches. Pass one Companies House type, or EDGAR fields."""
    t = t or taxonomy()
    items = set(edgar_items or [])
    out = []
    for doc in t["documents"]:
        m = doc.get("match") or {}
        if (ch and _matches(ch, m.get("ch"))) or \
           (edgar_form and _matches(edgar_form, m.get("edgar_forms"))) or \
           (edgar_type and _matches(edgar_type, m.get("edgar_types"))) or \
           (items and items & set(m.get("edgar_items") or [])):
            out.append(doc)
    return out


def exhibit_title(raw):
    """The title of an exhibit from its first bytes: the first heading-like line that is not the exhibit label."""
    import sys
    from .model import ROOT
    sys.path.insert(0, str(ROOT / "scripts"))
    from html2text import to_text
    for line in to_text(raw.decode("utf-8", "replace")).splitlines():
        ln = line.strip()
        if len(ln) < 8 or re.fullmatch(r"(EX-[\d.A-Z]+|exhibit [\d.()a-z]+|[\w.-]+\.htm|\d+)", ln, re.I):
            continue
        if ln.isupper() or re.search(r"\b(agreement|indenture|guarant|deed|letter|amendment|statement of work|lease)\b", ln, re.I):
            return ln[:140]
    return ""


def exhibit_needs(raw, fallback="", t=None):
    """(title, needs, how) for an Exhibit 10 from its first bytes: by title, else by strict phrases in the opening text."""
    import sys
    from .model import ROOT
    sys.path.insert(0, str(ROOT / "scripts"))
    from html2text import to_text
    t = t or taxonomy()
    title = exhibit_title(raw) or fallback
    needs = title_needs(title, t)
    if needs != ["contracts"]:
        return title, needs, "title"
    text = to_text(raw.decode("utf-8", "replace")).lower()[:6000]
    body = [n for n, phrases in t.get("body_rules", {}).items() if any(p in text for p in phrases)]
    if "debt_docs" in body:
        return title, body, "opening text"
    return title, ["contracts"], "title"


def title_needs(title, t=None):
    """Sort an Exhibit 10 by its title: debt documents (and guarantors/security), or a contract."""
    t = t or taxonomy()
    low = title.lower()
    needs = [n for n, phrases in t["title_rules"].items() if any(p in low for p in phrases)]
    return needs or ["contracts"]


def event_needs(event):
    """Questions a monitor event bears on, for grouping the daily issue."""
    if event["feed"] == "ch":
        kind = "MR01" if event["kind"].startswith("charge-") else event["kind"]
        return sorted({n for d in classify(ch=kind) for n in d["needs"]})
    if event["feed"] == "edgar":
        return sorted({n for d in classify(edgar_form=event["kind"]) for n in d["needs"]})
    return []


def _add(dossier, docs, title, date="", url=""):
    for doc in docs:
        for need in doc["needs"]:
            dossier.docs.append(Doc(need, title, date, url, doc["name"]))


# ---------- structure: GLEIF ----------

def _gleif(path):
    return net.get_json(f"https://api.gleif.org/api/v1/lei-records/{path}")


def find_lei(jur, registry_id):
    country = jurisdictions.directory()["jurisdictions"].get(jur, {}).get("country")
    params = {"filter[entity.registeredAs]": registry_id}
    if country:
        params["filter[entity.legalAddress.country]"] = country
    data = net.get_json("https://api.gleif.org/api/v1/lei-records?" + urllib.parse.urlencode(params))
    return data["data"][0]["id"] if data.get("data") else None


def gleif_structure(dossier, lei):
    rec = _gleif(lei).get("data")
    if not rec:
        dossier.notes.append(f"LEI {lei} not found in GLEIF")
        return
    e = rec["attributes"]["entity"]
    dossier.name = dossier.name or e["legalName"]["name"]
    dossier.ids.setdefault("registry", e.get("registeredAs") or "")
    page = f"https://search.gleif.org/#/record/{lei}"
    for rel, label in (("direct-parent", "Direct parent"), ("ultimate-parent", "Ultimate parent")):
        parent = _gleif(f"{lei}/{rel}").get("data")
        if parent:
            pe = parent["attributes"]["entity"]
            dossier.docs.append(Doc("structure", f"{label}: {pe['legalName']['name']} ({pe['legalAddress']['country']}, LEI {parent['id']})",
                                    url=f"https://search.gleif.org/#/record/{parent['id']}", kind="LEI relationship"))
        else:
            exc = (_gleif(f"{lei}/{rel}-reporting-exception").get("data") or {}).get("attributes", {})
            reason = exc.get("reason", "not reported").replace("_", " ").lower()
            dossier.docs.append(Doc("structure", f"{label}: none reported to GLEIF ({reason})", url=page, kind="LEI relationship"))
    children, start = [], 1
    for _ in range(MAX_PAGES):
        data = _gleif(f"{lei}/direct-children?page[size]=100&page[number]={start}")
        children += data.get("data", [])
        if start >= data.get("meta", {}).get("pagination", {}).get("lastPage", 1):
            break
        start += 1
    for c in children:
        ce = c["attributes"]["entity"]
        dossier.docs.append(Doc("structure", f"Subsidiary: {ce['legalName']['name']} ({ce['legalAddress']['country']}, reg {ce.get('registeredAs') or '?'})",
                                url=f"https://search.gleif.org/#/record/{c['id']}", kind="LEI relationship"))
    total = _gleif(f"{lei}/ultimate-children?page[size]=1").get("meta", {}).get("pagination", {}).get("total", 0)
    dossier.notes.append(f"GLEIF: {len(children)} direct and {total} ultimate subsidiaries with LEIs (entities without an LEI are not shown)")


def esef_financials(dossier, lei):
    data = net.get_json(f"https://filings.xbrl.org/api/entities/{lei}/filings?sort=-period_end&page[size]=5")
    for f in data.get("data", []):
        a = f["attributes"]
        dossier.docs.append(Doc("financials", f"ESEF annual report, period ending {a.get('period_end')}", a.get("published", "")[:10],
                                "https://filings.xbrl.org" + (a.get("viewer_url") or a.get("report_url") or ""), "ESEF annual report"))


# ---------- jurisdiction-specific pulls ----------

def _ch_all(url, auth):
    from .monitor import _ch_items
    return _ch_items(url, auth)


def uk_company(dossier, number):
    from .monitor import _ch_key
    auth = {"Authorization": _ch_key()}
    profile = net.get_json(f"{CH_API}{number}", auth)
    dossier.name = dossier.name or profile.get("company_name", "")
    for f in _ch_all(f"{CH_API}{number}/filing-history", auth):
        docs = classify(ch=f.get("type"))
        url = f"{CH_SITE}{number}/filing-history/{f.get('transaction_id')}/document?format=pdf&download=0"
        _add(dossier, docs, f"{f.get('type')}: {f.get('description', '').replace('-', ' ')}", f.get("date", ""), url)
    for c in _ch_all(f"{CH_API}{number}/charges", auth):
        holders = ", ".join(p.get("name", "") for p in c.get("persons_entitled", [])) or "chargee not stated"
        cid = (c.get("links", {}).get("self", "") or "").rstrip("/").rsplit("/", 1)[-1]
        what = (c.get("classification") or {}).get("description", "")
        title = f"Charge {c.get('charge_code') or cid} ({c.get('status', '')}) in favour of {holders}; {what}".strip("; ")
        for need in ("security", "lenders"):
            dossier.docs.append(Doc(need, title, c.get("created_on", ""), f"{CH_SITE}{number}/charges/{cid}", "Registered charge"))
    for p in _ch_all(f"{CH_API}{number}/persons-with-significant-control", auth):
        if "corporate" in p.get("kind", "") or "legal-person" in p.get("kind", ""):   # companies only: no personal data
            dossier.docs.append(Doc("structure", f"Parent (PSC): {p.get('name')}; {', '.join(p.get('natures_of_control', []))}",
                                    p.get("notified_on", ""), f"{CH_SITE}{number}/persons-with-significant-control", "PSC register"))
    for case in net.get_json(f"{CH_API}{number}/insolvency", auth).get("cases", []):
        dates = ", ".join(f"{d.get('type', '')} {d.get('date', '')}" for d in case.get("dates", []))
        dossier.docs.append(Doc("restructuring", f"Insolvency case: {case.get('type', '').replace('-', ' ')} ({dates})",
                                url=f"{CH_SITE}{number}/insolvency", kind="Insolvency case"))


def us_company(dossier, cik, expand=12):
    """Every recent filing sorted by question; the exhibits of the filings most likely to hold debt documents."""
    cik = str(int(cik))
    headers = {"User-Agent": net.user_agent(require_contact=True)}
    sub = net.get_json(f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json", headers)
    dossier.name = dossier.name or sub.get("name", "")
    r = sub.get("filings", {}).get("recent", {})
    filings = [dict(zip(r, vals)) for vals in zip(*r.values())] if r else []
    for f in filings:
        items = [i for i in (f.get("items") or "").split(",") if i]
        docs = classify(edgar_form=f["form"]) + classify(edgar_items=items)
        base = f"{SEC_ARCHIVE}{cik}/{f['accessionNumber'].replace('-', '')}/"
        title = f"{f['form']}" + (f" (items {', '.join(items)})" if items else "")
        _add(dossier, docs, title, f["filingDate"], base + f.get("primaryDocument", ""))
    # Open the filings that carry debt exhibits: latest annual report and registration statement, recent 424Bs,
    # and 8-Ks reporting new debt.
    pick, seen = [], set()
    for want, n in (({"10-K", "20-F", "40-F"}, 1), ({"S-1", "S-1/A", "F-1", "F-1/A", "S-4", "F-4"}, 1), ({"10-Q"}, 1)):
        pick += [f for f in filings if f["form"] in want][:n]
    pick += [f for f in filings if f["form"].startswith("424B")][:3]
    pick += [f for f in filings if f["form"] == "8-K" and {"1.01", "2.03"} & set((f.get("items") or "").split(","))][:5]
    for f in pick[:expand]:
        if f["accessionNumber"] in seen:
            continue
        seen.add(f["accessionNumber"])
        base = f"{SEC_ARCHIVE}{cik}/{f['accessionNumber'].replace('-', '')}/"
        body, _ = net.get(f"{base}{f['accessionNumber']}-index.htm", headers)
        for doc_type, name, desc in filing_index(body):
            docs = classify(edgar_type=doc_type)
            if not docs:
                continue
            if doc_type.upper().startswith("EX-10"):
                head, _ = net.get(base + name, headers, max_bytes=20_000)
                title, needs, how = exhibit_needs(head or b"", desc if desc != doc_type else name)
                note = " [sorted by opening text]" if how == "opening text" else ""
                for need in needs:
                    dossier.docs.append(Doc(need, f"{doc_type} {title} (in {f['form']}){note}", f["filingDate"], base + name,
                                            "Material agreement (Exhibit 10)"))
                continue
            label = desc if desc and desc != doc_type else name
            _add(dossier, docs, f"{doc_type} {label} (in {f['form']})", f["filingDate"], base + name)


def filing_index(body):
    """(type, file name, description) for each document row of an EDGAR filing index page."""
    if not body:
        return []
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", body.decode("utf-8", "replace"), re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if len(cells) >= 4 and cells[3]:
            out.append((cells[3], cells[2].split()[0] if cells[2] else "", cells[1]))
    return out


def no_company(dossier, orgnr):
    e = net.get_json(f"https://data.brreg.no/enhetsregisteret/api/enheter/{orgnr}")
    dossier.name = dossier.name or e.get("navn", "")
    flags = [k for k in ("konkurs", "underAvvikling", "underTvangsavviklingEllerTvangsopplosning", "underRekonstruksjonsforhandling") if e.get(k)]
    if flags:
        dossier.docs.append(Doc("restructuring", "Register flags: " + ", ".join(flags), url=f"https://virksomhet.brreg.no/nb/oppslag/enheter/{orgnr}",
                                kind="Brønnøysund flags"))
    body, _ = net.get(f"https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}")
    if body:
        import json
        for r in json.loads(body):
            dossier.docs.append(Doc("financials", norway_figures(r), r.get("regnskapsperiode", {}).get("tilDato", ""),
                                    f"https://virksomhet.brreg.no/nb/oppslag/enheter/{orgnr}", "Annual accounts key figures"))


def norway_figures(r):
    g = r.get("egenkapitalGjeld", {})
    debt = g.get("gjeldOversikt", {})
    cur = r.get("valuta", "NOK")
    fmt = lambda v: f"{v / 1e6:,.0f}m" if isinstance(v, (int, float)) else "?"
    scope = {"KONSERN": "group", "SELSKAP": "company"}.get(r.get("regnskapstype", ""), r.get("regnskapstype", "").lower())
    return (f"{scope + ' ' if scope else ''}FY to {r.get('regnskapsperiode', {}).get('tilDato', '?')}: total debt {cur} {fmt(debt.get('sumGjeld'))} "
            f"(long-term {fmt(debt.get('langsiktigGjeld', {}).get('sumLangsiktigGjeld'))}, short-term "
            f"{fmt(debt.get('kortsiktigGjeld', {}).get('sumKortsiktigGjeld'))}), equity {fmt(g.get('egenkapital', {}).get('sumEgenkapital'))}, "
            f"assets {fmt(r.get('eiendeler', {}).get('sumEiendeler'))}")


def fr_company(dossier, siren):
    data = net.get_json("https://recherche-entreprises.api.gouv.fr/search?" + urllib.parse.urlencode({"q": siren}))
    r = next((x for x in data.get("results", []) if x.get("siren") == siren), None)
    if not r:
        dossier.notes.append(f"SIREN {siren} not found in the French register API")
        return
    dossier.name = dossier.name or r.get("nom_complet", "")
    page = f"https://annuaire-entreprises.data.gouv.fr/entreprise/{siren}"
    for year, f in sorted((r.get("finances") or {}).items(), reverse=True):
        dossier.docs.append(Doc("financials", f"{year}: revenue EUR {f.get('ca', 0) / 1e6:,.1f}m, net result EUR {f.get('resultat_net', 0) / 1e6:,.1f}m",
                                year, page, "Filed accounts summary"))
    for d in r.get("dirigeants", []):
        if d.get("type_dirigeant") == "personne morale":   # companies only: no personal data
            dossier.docs.append(Doc("structure", f"Corporate officer: {d.get('denomination')} ({d.get('qualite', '')})", url=page,
                                    kind="Register officers"))


def fi_company(dossier, business_id):
    data = net.get_json("https://avoindata.prh.fi/opendata-ytj-api/v3/companies?" + urllib.parse.urlencode({"businessId": business_id}))
    for c in data.get("companies", []):
        dossier.name = dossier.name or (c.get("names") or [{}])[0].get("name", "")
        for s in c.get("companySituations") or []:
            dossier.docs.append(Doc("restructuring", f"Company situation: {s.get('type')} since {s.get('registrationDate', '?')}",
                                    url=f"https://tietopalvelu.ytj.fi/yritys/{business_id}", kind="PRH company situation"))


def ie_company(dossier, number):
    q = urllib.parse.urlencode({"resource_id": "3fef41bc-b8f4-4b10-8434-ce51c29b1bba", "filters": f'{{"company_num": {int(number)}}}'})
    for r in net.get_json(f"https://opendata.cro.ie/api/3/action/datastore_search?{q}").get("result", {}).get("records", []):
        dossier.name = dossier.name or r["company_name"]
        status = (r.get("company_status") or "").strip()
        if status and status != "Normal":
            dossier.docs.append(Doc("restructuring", f"CRO status: {status}", url="https://core.cro.ie/", kind="CRO status"))


PULLS = {"uk": uk_company, "us": us_company, "no": no_company, "fr": fr_company, "fi": fi_company, "ie": ie_company}


def company(jur, ident, name=""):
    """Gather one company's documents by question. Each source that fails is noted; the rest still run."""
    d = Dossier(name, jur)
    ident = ident.strip()

    def attempt(label, fn, *args):
        try:
            fn(*args)
        except Exception as e:   # noqa: BLE001 - report and carry on
            d.failures.append(f"{label}: {type(e).__name__}: {str(e)[:160]}")

    lei = ident.upper() if LEI_RE.match(ident.upper()) else None
    if not lei and jur in PULLS:
        d.ids["registry"] = ident
        attempt("registry", PULLS[jur], d, ident)
    if not lei and jur != "us":
        try:
            lei = find_lei(jur, ident)
        except Exception as e:   # noqa: BLE001
            d.failures.append(f"GLEIF lookup: {type(e).__name__}: {e}")
    if lei:
        d.ids["lei"] = lei
        attempt("GLEIF", gleif_structure, d, lei)
        attempt("ESEF", esef_financials, d, lei)
    elif jur != "us":
        d.notes.append("No LEI found for this registry number, so no GLEIF org chart; try the group's top company or its LEI")
    return d


def guidance(jur, need=None, t=None):
    """Documents to look for by hand, for a jurisdiction (plus pan-EU and paid ones)."""
    t = t or taxonomy()
    scope = {jur, "eu", "global"} if jur not in ("eu", "global") else {jur}
    return [doc for doc in t["documents"] if doc["jurisdiction"] in scope and (need is None or need in doc["needs"])]


def format_company(d, show=12, t=None):
    t = t or taxonomy()
    dirx = jurisdictions.directory()
    src = {r["id"]: r for r in dirx["resources"]}
    ids = " · ".join(f"{k} {v}" for k, v in d.ids.items() if v)
    lines = [f"=== {d.name or '(name unknown)'} [{dirx['jurisdictions'][d.jurisdiction]['name']}] {ids}"]
    lines += [f"note: {n}" for n in d.notes]
    lines += [f"not searched: {f}" for f in d.failures]
    for need, label in t["needs"].items():
        found = sorted([x for x in d.docs if x.need == need], key=lambda x: x.date, reverse=True)
        lines.append(f"\n## {label}")
        for x in found[:show]:
            lines.append(f"  - {x.date or '':10}  {x.title}" + (f"\n                {x.url}" if x.url else ""))
        if len(found) > show:
            lines.append(f"    ... {len(found) - show} more")
        if not found:
            lines.append("  (nothing found live)")
        for doc in guidance(d.jurisdiction, need, t):
            r = src.get(doc["source"], {})
            url, _ = jurisdictions.link(r, d.name) if r else ("", False)
            lines.append(f"  look for: {doc['name']} [{r.get('name', doc['source'])}, {r.get('access', '?')}]: {doc['tip']}"
                         + (f"\n            {url}" if url else ""))
    return "\n".join(lines)


# ---------- sector ----------

def sector_us(preset, since, pages=3):
    """Debt documents in EDGAR that mention a sector term and a debt phrase: credit agreements, indentures,
    guarantor lists and 8-Ks reporting new debt, grouped by filer. Exhibit 10s count only if their title is a
    debt document (a GPU services contract that mentions a credit agreement is not one)."""
    headers = {"User-Agent": net.user_agent(require_contact=True)}
    filers, titles = {}, {}
    forms = "8-K,10-K,10-Q,S-1,S-1/A,F-1,S-4,20-F,424B2,424B3,424B4,424B5"
    for term in preset["terms"]:
        for phrase in preset["debt_phrases"]:
            start = 0
            for _ in range(pages):
                q = urllib.parse.urlencode({"q": f'"{term}" "{phrase}"', "dateRange": "custom", "startdt": since,
                                            "enddt": "2100-01-01", "forms": forms, "from": start})
                page = net.get_json(f"https://efts.sec.gov/LATEST/search-index?{q}", headers).get("hits", {})
                batch = page.get("hits", [])
                for h in batch:
                    s_ = h["_source"]
                    ftype = s_.get("file_type") or ""
                    docs = classify(edgar_type=ftype) + classify(edgar_items=s_.get("items") or [])
                    if not any(n in ("debt_docs", "guarantors") for doc in docs for n in doc["needs"]):
                        continue
                    acc, fname = h["_id"].split(":")
                    url = f"{SEC_ARCHIVE}{s_['ciks'][0].lstrip('0')}/{acc.replace('-', '')}/{fname}"
                    title = ftype
                    if ftype.upper().startswith("EX-10"):
                        if url not in titles:
                            head, _ = net.get(url, headers, max_bytes=20_000)
                            titles[url] = exhibit_needs(head or b"")
                        ex_title, ex_needs, _ = titles[url]
                        if "debt_docs" not in ex_needs:
                            continue
                        title = f"{ftype} {ex_title}"
                    who = re.sub(r"\s+\(CIK.*$", "", s_["display_names"][0]).strip()
                    f = filers.setdefault(who, {"docs": {}, "latest": ""})
                    f["docs"][h["_id"]] = (s_.get("file_date", ""), title, url)
                    f["latest"] = max(f["latest"], s_.get("file_date", ""))
                start += len(batch)
                if not batch or start >= page.get("total", {}).get("value", 0):
                    break
    return filers


def sector_no(preset, max_companies=60, min_employees=10):
    """Norwegian companies in the sector, ranked by total debt from their latest filed accounts (group accounts
    where filed). Known groups and name keywords come first, then industry-code matches with at least
    `min_employees` staff, so the largest real players are not crowded out by small firms."""
    import json
    orgs = {}
    for kw in preset.get("groups", []) + preset.get("keywords", []):
        q = {"navn": kw, "size": 20}
        for e in net.get_json("https://data.brreg.no/enhetsregisteret/api/enheter?" + urllib.parse.urlencode(q)).get("_embedded", {}).get("enheter", []):
            orgs.setdefault(e["organisasjonsnummer"], e["navn"])
    for code in preset.get("no_nace", []):
        q = {"naeringskode": code, "size": 100, "fraAntallAnsatte": min_employees}
        for e in net.get_json("https://data.brreg.no/enhetsregisteret/api/enheter?" + urllib.parse.urlencode(q)).get("_embedded", {}).get("enheter", []):
            orgs.setdefault(e["organisasjonsnummer"], e["navn"])
    rows = []
    for orgnr, name in list(orgs.items())[:max_companies]:
        body, _ = net.get(f"https://data.brreg.no/regnskapsregisteret/regnskap/{orgnr}")
        accounts = json.loads(body) if body else []
        if not accounts:
            continue
        r = max(accounts, key=lambda a: (a.get("regnskapsperiode", {}).get("tilDato", ""), a.get("regnskapstype") == "KONSERN"))
        debt = r.get("egenkapitalGjeld", {}).get("gjeldOversikt", {})
        rows.append(dict(name=name, orgnr=orgnr, year=r.get("regnskapsperiode", {}).get("tilDato", "")[:4],
                         scope="group" if r.get("regnskapstype") == "KONSERN" else "company",
                         debt=debt.get("sumGjeld") or 0, long_term=debt.get("langsiktigGjeld", {}).get("sumLangsiktigGjeld") or 0,
                         currency=r.get("valuta", "NOK")))
    return sorted(rows, key=lambda x: x["debt"], reverse=True), len(orgs)


def sector_uk(preset, max_companies=100):
    """UK companies with the sector's SIC codes and their registered charges: who lends to the sector, against what."""
    from .monitor import _ch_items, _ch_key
    auth = {"Authorization": _ch_key()}
    companies = []
    for sic in preset.get("uk_sic", []):
        q = urllib.parse.urlencode({"sic_codes": sic, "company_status": "active", "size": max_companies})
        companies += net.get_json(f"https://api.company-information.service.gov.uk/advanced-search/companies?{q}", auth).get("items", [])
    lenders, borrowers = {}, []
    for c in companies[:max_companies]:
        num = c.get("company_number")
        charges = [x for x in _ch_items(f"{CH_API}{num}/charges", auth) if x.get("status") == "outstanding"]
        if not charges:
            continue
        borrowers.append((c.get("company_name"), num, len(charges)))
        for x in charges:
            for p in x.get("persons_entitled", []):
                lenders.setdefault(p.get("name", "?"), set()).add(c.get("company_name"))
    return lenders, borrowers, len(companies)


def sector(preset_id, jurs=("us", "no", "uk"), since="2024-01-01", max_companies=60):
    t = taxonomy()
    preset = t["sectors"][preset_id]
    out, failures = {}, []
    runs = {"us": lambda: sector_us(preset, since), "no": lambda: sector_no(preset, max_companies),
            "uk": lambda: sector_uk(preset, max_companies)}
    for j in jurs:
        if j not in runs:
            failures.append(f"{j}: no live sector search yet; see the directory for its sources")
            continue
        try:
            out[j] = runs[j]()
        except Exception as e:   # noqa: BLE001
            failures.append(f"{j}: {type(e).__name__}: {str(e)[:160]}")
    return preset, out, failures


def format_sector(preset, out, failures, show=25):
    lines = [f"=== Sector: {preset['name']}", f"note: {preset['note']}"] if preset.get("note") else [f"=== Sector: {preset['name']}"]
    lines += [f"not searched: {f}" for f in failures]
    if "us" in out:
        filers = out["us"]
        lines.append(f"\n## SEC filings with debt documents mentioning the sector ({len(filers)} filers)")
        for who, f in sorted(filers.items(), key=lambda kv: kv[1]["latest"], reverse=True)[:show]:
            lines.append(f"  - {who}: {len(f['docs'])} debt document(s), latest {f['latest']}")
            for date, title, url in sorted(f["docs"].values(), reverse=True)[:3]:
                lines.append(f"      {date}  {title[:90]}\n                  {url}")
    if "no" in out:
        rows, n = out["no"]
        lines.append(f"\n## Norway: {n} companies by known group, name keyword or industry code; largest debt from latest filed accounts")
        for r in rows[:show]:
            lines.append(f"  - {r['name']} ({r['orgnr']}, {r['scope']} FY{r['year']}): total debt {r['currency']} {r['debt'] / 1e6:,.0f}m, "
                         f"long-term {r['long_term'] / 1e6:,.0f}m")
    if "uk" in out:
        lenders, borrowers, n = out["uk"]
        lines.append(f"\n## UK: {n} active companies with the sector's SIC codes; {len(borrowers)} have outstanding charges")
        for name, holders in sorted(lenders.items(), key=lambda kv: len(kv[1]), reverse=True)[:show]:
            lines.append(f"  - {name}: security over {len(holders)} compan{'y' if len(holders) == 1 else 'ies'} "
                         f"({', '.join(sorted(holders)[:4])}{'…' if len(holders) > 4 else ''})")
    lines.append("\n## Also check (sector-wide debt is mostly in paid databases)")
    for r in jurisdictions.directory()["resources"]:
        if r["id"] in ("us_bdc", "eu_firds", "eu_eib", "eu_eca", "gl_9fin", "gl_loanconnector", "gl_pitchbook_lcd", "gl_ijglobal", "gl_octus"):
            lines.append(f"  - {r['name']} [{r['access']}]: {r['what']}")
    return "\n".join(lines)


def format_guidance(jur=None, need=None, t=None):
    t = t or taxonomy()
    src = {r["id"]: r for r in jurisdictions.directory()["resources"]}
    docs = [d for d in t["documents"] if (jur is None or d["jurisdiction"] == jur) and (need is None or need in d["needs"])]
    lines = []
    for d in docs:
        r = src.get(d["source"], {})
        how = d.get("match") or {}
        code = "; ".join(f"{k}: {', '.join(v)}" for k, v in how.items())
        lines.append(f"- [{d['jurisdiction']}] {d['name']}  ->  {', '.join(d['needs'])}\n    where: {r.get('name', d['source'])} "
                     f"({r.get('access', '?')})" + (f"\n    recognised by {code}" if code else "") + f"\n    read for: {d['tip']}")
    return "\n".join(lines) or "No document types match."


def validate_taxonomy(t=None):
    t = t or taxonomy()
    dirx = jurisdictions.directory()
    ids = {r["id"] for r in dirx["resources"]}
    problems = []
    for doc in t["documents"]:
        where = f"document type {doc.get('id')}"
        if doc.get("jurisdiction") not in dirx["jurisdictions"]:
            problems.append(f"{where}: unknown jurisdiction '{doc.get('jurisdiction')}'")
        if doc.get("source") not in ids:
            problems.append(f"{where}: unknown source '{doc.get('source')}'")
        problems += [f"{where}: unknown need '{n}'" for n in doc.get("needs", []) if n not in t["needs"]]
        for k in (doc.get("match") or {}):
            if k not in ("ch", "edgar_forms", "edgar_types", "edgar_items"):
                problems.append(f"{where}: unknown match key '{k}'")
        if not doc.get("tip"):
            problems.append(f"{where}: missing tip")
    for sid, s in t.get("sectors", {}).items():
        problems += [f"title/body rules: unknown need '{n}'" for n in list(t.get("title_rules", {})) + list(t.get("body_rules", {}))
                 if n not in t["needs"]]
    for k in ("name", "terms", "debt_phrases"):
            if not s.get(k):
                problems.append(f"sector {sid}: missing {k}")
    return problems
