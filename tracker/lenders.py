"""Lender layer: which BDCs hold a group's or a sector's debt (or equity), at what cost and mark.

    python -m tracker lenders data_centres                 every name in the preset's lender_terms
    python -m tracker lenders --terms "Nscale,Fluidstack"  specific names
    options: --months 3 (monthly SEC data sets to scan), --no-reconcile, --csv <path>

Two steps, each for a reason:
 1. Discovery. SEC publishes the schedules of investments of every BDC filing as monthly data sets (quarterly until
    2025). One download covers all ~175 BDCs. We search every name column for the terms, because edgartools' own
    search reads one column and missed Nscale. Only the filing's own period counts: filings also carry prior-period
    comparatives. Each BDC's newest filing wins.
 2. Confirmation. For each BDC filing with a match, edgartools parses that filing's XBRL. Its list is the one we
    report: it found a Blue Owl loan to Nscale Services UK that the data set search missed. Its rows are summed and
    compared with the BDC's own reported total investments at fair value; a gap above 2% is flagged, because then
    some holdings are tagged twice and shares of the portfolio are unreliable (individual positions still stand).

Needs `pip install edgartools` and EDGAR_USER_AGENT. Results are leads for statements (source type
counterparty_filing), not statements themselves.
"""

import csv
import pickle
import re
from dataclasses import asdict, dataclass, fields

from . import net
from .model import ROOT

INDEX = "https://www.sec.gov/data-research/sec-markets-data/bdc-data-sets"
CACHE = ROOT / "build" / "cache"
NAME_COLUMNS = ("company", "investment_id", "investment_name", "Investment, Issuer Name [Extensible Enumeration]",
                "Investee", "legal_entity", "subsidiary", "investment")
GAP_OK = 0.02


@dataclass
class Position:
    bdc: str
    cik: str
    form: str
    period: str
    term: str
    borrower: str
    instrument: str
    kind: str              # debt | equity | other
    interest_rate: str
    spread: str
    principal: float | None
    cost: float | None
    fair_value: float | None
    mark: str              # fair value per 100 of principal (debt) or of cost
    source: str            # "filing XBRL" (confirmed) or "SEC data set" (not confirmed)
    url: str


def _edgar():
    try:
        import edgar
    except ImportError as e:
        raise RuntimeError("pip install edgartools (needed for the lender layer)") from e
    edgar.set_identity(net.user_agent(require_contact=True))
    return edgar


def monthly_files(n=3):
    """The newest n monthly BDC data sets on SEC's index page, as (year, month), newest first."""
    body, _ = net.get(INDEX, {"User-Agent": net.user_agent(require_contact=True)})
    found = {(int(y), int(m)) for y, m in re.findall(r"(\d{4})_(\d{2})_bdc\.zip", (body or b"").decode("utf-8", "replace"))}
    return sorted(found, reverse=True)[:n]


def load_month(year, month):
    """One monthly data set, cached under build/cache (re-downloading takes about 35 seconds)."""
    path = CACHE / f"bdc_{year}_{month:02d}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    _edgar()
    from edgar.bdc import fetch_bdc_dataset_monthly
    ds = fetch_bdc_dataset_monthly(year, month)
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(ds))
    return ds


def _num(v):
    try:
        f = float(v)
        return None if f != f else f    # NaN -> None
    except (TypeError, ValueError):
        return None


def _mark(fv, principal, cost, instrument=""):
    """Fair value per 100 of principal (debt) or of cost. A delayed-draw loan whose cost is well below principal is
    partly undrawn (principal includes the commitment), so it is marked against cost. Otherwise a mark outside 50-150
    usually means the filing reports principal in other units or as the whole facility: flagged, not trusted."""
    if fv is None:
        return ""
    if principal and cost and cost < 0.9 * principal and re.search(r"delayed|ddtl|draw", instrument or "", re.I):
        return f"{fv / cost * 100:.1f} (of cost; delayed draw, partly undrawn: principal includes the commitment)"
    base, label = (principal, "of principal") if principal else (cost, "of cost") if cost else (None, "")
    if not base:
        return ""
    m = fv / base * 100
    flag = "" if 50 <= m <= 150 or label == "of cost" else "; check units"
    return f"{m:.1f} ({label}{flag})"


def _kind(text):
    t = (text or "").lower()
    if any(w in t for w in ("loan", "note", "bond", "debt", "lien", "revolver", "delayed draw", "term")):
        return "debt"
    if any(w in t for w in ("equity", "preferred", "shares", "warrant", "units", "common", "membership")):
        return "equity"
    return "other"


FIELD_WORDS = re.compile(r"\s(?:Industry|Investment|Instrument|Interest|Security|Type of|Reference|Maturity|Initial|"
                         r"Delayed|First Lien|Second Lien|Senior|Term Loan|Revolver|Equity|Ref|Spread)\b", re.I)


def borrower_label(identifier, company_name, terms):
    """The borrower as the filing names it: the identifier segment that contains the matched term, because the
    parsed company name is sometimes a heading ('Technology', 'First Lien Senior Secured'). Some BDCs put the whole
    description in one string; then the label runs from the matched name to the first field word ('Industry',
    'Investment', 'Interest'...)."""
    for part in re.split(r"\s*\|\s*|\s{2,}", identifier or ""):
        if not matches(part, terms):
            continue
        part = part.strip(" ,")
        if len(part) <= 80:
            return part
        m = min((re.search(_term_re(t), part, re.I) for t in terms if re.search(_term_re(t), part, re.I)), key=lambda m: m.start())
        tail = part[m.start():]
        stop = FIELD_WORDS.search(tail, len(m.group(0)))
        return tail[:stop.start()].strip(" ,-") if stop else tail[:80].strip()
    return (company_name or identifier or "").strip()


def _term_re(term):
    """Whole-word, case-insensitive: 'IREN' must not match 'Firenze'."""
    return r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"


def matches(text, terms):
    return [t for t in terms if re.search(_term_re(t), text or "", re.I)]


def discover(terms, months):
    """{adsh: filing info with matched data-set rows}, newest filing per BDC only."""
    found = {}
    for year, month in months:
        df = load_month(year, month).schedule_of_investments.to_dataframe(clean=True)
        cols = [c for c in NAME_COLUMNS if c in df.columns]
        if not cols or df.empty:
            continue
        current = df[df["data_date"].astype(str) == df["period"].astype(str)] if "data_date" in df.columns else df
        hay = current[cols].fillna("").astype(str).agg(" | ".join, axis=1)
        pattern = "|".join(_term_re(t) for t in terms)
        for idx, row in current[hay.str.contains(pattern, case=False, regex=True)].iterrows():
            adsh = row["adsh"]
            f = found.setdefault(adsh, dict(adsh=adsh, bdc=row["name"], cik=str(row["cik"]), form=row.get("form", ""),
                                            period=str(row["period"])[:10], filed=str(row.get("filed", ""))[:10],
                                            url=row.get("filing_url", "") or "", rows=[]))
            ident = next((str(row[c]) for c in ("investment_id", "company", "investment_name") if str(row.get(c, "nan")) != "nan"), "")
            f["rows"].append(dict(term=", ".join(matches(hay[idx], terms)), identifier=ident,
                                  interest_rate=row.get("interest_rate"), spread=row.get("spread"),
                                  principal=_num(row.get("principal")), cost=_num(row.get("cost")),
                                  fair_value=_num(row.get("fair_value"))))
    newest = {}
    for f in found.values():
        key = f["cik"]
        if key not in newest or (f["period"], f["filed"]) > (newest[key]["period"], newest[key]["filed"]):
            newest[key] = f
    return {f["adsh"]: f for f in newest.values()}


def confirm(filing, terms):
    """Parse the filing's own XBRL: matched positions and the reconciliation against the reported total."""
    edgar = _edgar()
    from edgar.bdc import PortfolioInvestments
    xbrl = edgar.get_by_accession_number(filing["adsh"]).xbrl()
    pi = PortfolioInvestments.from_xbrl(xbrl, period=filing["period"])
    recon = dict(bdc=filing["bdc"], period=filing["period"], positions=len(pi), summed=float(pi.total_fair_value or 0),
                 reported=float(pi.reported_total_fair_value) if pi.reported_total_fair_value else None,
                 gap=pi.reconciliation_gap)
    out = []
    for inv in pi:
        hit = matches(f"{inv.identifier} {inv.company_name}", terms)
        if not hit:
            continue
        fv, cost, principal = _num(inv.fair_value), _num(inv.cost), _num(inv.principal_amount)
        out.append(Position(filing["bdc"], filing["cik"], filing["form"], filing["period"], ", ".join(hit),
                            borrower_label(inv.identifier, inv.company_name, terms), inv.investment_type or "",
                            _kind(inv.investment_type),
                            "" if inv.interest_rate is None else f"{inv.interest_rate:g}",
                            "" if inv.spread is None else f"{inv.spread:g}", principal, cost, fv,
                            _mark(fv, principal, cost, f"{inv.investment_type} {inv.identifier}"), "filing XBRL", filing["url"]))
    return out, recon


def unconfirmed(filing):
    """Data-set rows as positions, when the filing could not be parsed."""
    out = []
    for r in filing["rows"]:
        parts = [p.strip() for p in r["identifier"].split("|")]
        instrument = parts[1] if len(parts) > 1 else ""
        out.append(Position(filing["bdc"], filing["cik"], filing["form"], filing["period"], r["term"],
                            borrower_label(r["identifier"], parts[0], r["term"].split(", ")), instrument,
                            _kind(instrument), "" if _num(r["interest_rate"]) is None else f"{_num(r['interest_rate']):g}",
                            "" if _num(r["spread"]) is None else f"{_num(r['spread']):g}", r["principal"], r["cost"],
                            r["fair_value"], _mark(r["fair_value"], r["principal"], r["cost"], r["identifier"]), "SEC data set", filing["url"]))
    return out


def lenders(terms, n_months=3, reconcile=True):
    """Returns (positions, reconciliations, failures, months scanned)."""
    months = monthly_files(n_months)
    filings = discover(terms, months)
    positions, recons, failures = [], [], []
    for f in sorted(filings.values(), key=lambda f: f["bdc"]):
        if reconcile:
            try:
                found, recon = confirm(f, terms)
                recons.append(recon)
                positions += found
                continue
            except Exception as e:   # noqa: BLE001 - fall back to the data set rows, and say so
                failures.append(f"{f['bdc']} {f['period']}: filing not parsed ({type(e).__name__}: {str(e)[:120]}); data-set rows shown")
        positions += unconfirmed(f)
    return positions, recons, failures, months


def _money(v):
    return "" if v is None else f"{v / 1e6:,.1f}m"


def format_lenders(positions, recons, failures, months):
    lines = [f"BDC holdings, from SEC monthly data sets {', '.join(f'{y}-{m:02d}' for y, m in months)} "
             f"({len({p.bdc for p in positions})} BDCs, {len(positions)} positions)"]
    lines += [f"note: {f}" for f in failures]
    by_term = {}
    for p in positions:
        by_term.setdefault(p.term.split(", ")[0], []).append(p)
    for term, ps in sorted(by_term.items(), key=lambda kv: -sum(p.fair_value or 0 for p in kv[1])):
        total = sum(p.fair_value or 0 for p in ps)
        lines.append(f"\n## {term}: {len(ps)} position(s) at {len({p.bdc for p in ps})} BDC(s), fair value {_money(total)}")
        for p in sorted(ps, key=lambda p: (p.borrower.lower(), -(p.fair_value or 0))):
            terms = " ".join(x for x in (f"rate {p.interest_rate}" if p.interest_rate else "",
                                         f"spread {p.spread}" if p.spread else "") if x)
            lines.append(f"  - {p.borrower} | {p.bdc} [{p.form} {p.period}]: {p.instrument or '?'} ({p.kind}) "
                         f"principal {_money(p.principal) or '-'}, cost {_money(p.cost) or '-'}, fair value {_money(p.fair_value) or '-'}"
                         + (f", mark {p.mark}" if p.mark else "") + (f", {terms}" if terms else "")
                         + ("" if p.source == "filing XBRL" else "  [not confirmed against the filing]"))
    if recons:
        lines.append("\n## Reconciliation: parsed rows against each BDC's reported total investments at fair value")
        for r in recons:
            gap = r["gap"]
            status = ("no reported total" if gap is None else "ok" if abs(gap) <= GAP_OK
                      else "CHECK: rows sum above the total (holdings tagged twice)" if gap > 0
                      else "CHECK: rows sum below the total (holdings missing from the parse)")
            lines.append(f"  - {r['bdc']} {r['period']}: {r['positions']} positions, summed {_money(r['summed'])}, "
                         f"reported {_money(r['reported'])}, gap {'' if gap is None else f'{gap:+.1%}'} -> {status}")
        lines.append("  Above the total: some holdings are tagged twice; positions stand, but totals and shares from that filing "
                     "do not. Below: some holdings were not parsed, so a missing name there is not proof the BDC has no position.")
    return "\n".join(lines)


def write_csv(positions, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[x.name for x in fields(Position)])
        w.writeheader()
        for p in positions:
            w.writerow(asdict(p))
