"""One-off: append creditor (BDC 10-Q, N-PORT) and counterparty (landlord / colocation / supplier 10-Q) statements."""
import csv
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
OBS = "2026-10-29"
D = "disclosed"
G = "group_nscale"
E = "https://www.sec.gov/Archives/edgar/data/"

sources = [
    ("src_obdc_10q", "counterparty_filing", "Blue Owl Capital Corp (OBDC)", "10-Q for quarter ended 30 June 2026: schedule of investments", E + "1655888/000165588826000056/obdc-20260630.htm", "2026-08-05"),
    ("src_ocic_10q", "counterparty_filing", "Blue Owl Credit Income Corp. (OCIC)", "10-Q for quarter ended 30 June 2026: schedule of investments", E + "1812554/000181255426000047/orcic-20260630.htm", "2026-08-06"),
    ("src_otf_10q", "counterparty_filing", "Blue Owl Technology Finance Corp. (OTF)", "10-Q for quarter ended 30 June 2026: schedule of investments", E + "1747777/000174777726000028/ortf-20260630.htm", "2026-08-05"),
    ("src_otic_10q", "counterparty_filing", "Blue Owl Technology Income Corp. (OTIC)", "10-Q for quarter ended 30 June 2026: schedule of investments", E + "1869453/000186945326000053/ortic-20260630.htm", "2026-08-06"),
    ("src_obdc2_10q", "counterparty_filing", "Blue Owl Capital Corp II", "10-Q for quarter ended 30 June 2026: schedule of investments", E + "1655887/000165588726000016/obdc-20260630.htm", "2026-08-07"),
    ("src_pimco_pdi_nport", "counterparty_filing", "PIMCO Dynamic Income Fund (PDI)", "N-PORT-P holdings, period 30 June 2026", E + "1510599/000141036826090256/primary_doc.xml", "2026-08-31"),
    ("src_fidelity_bcg_nport", "counterparty_filing", "Fidelity Series Blue Chip Growth Fund", "N-PORT-P holdings, period 31 July 2026", E + "754510/000003540226006272/primary_doc.xml", "2026-09-23"),
    ("src_ionic_10q", "counterparty_filing", "Ionic Digital Inc. (IOND)", "10-Q for quarter ended 30 June 2026", E + "2007691/000200769126000012/ioni-20260630.htm", "2026-09-01"),
    ("src_whitefiber_10q", "counterparty_filing", "WhiteFiber, Inc. (WYFI)", "10-Q for quarter ended 30 June 2026", E + "2042022/000121390026088026/ea0300877-10q_whitefiber.htm", "2026-08-12"),
    ("src_kinrg_10q", "counterparty_filing", "KiNRG, Inc.", "10-Q for quarter ended 30 June 2026", E + "95572/000121390026091673/ea0300829-10q_kinrg.htm", "2026-08-19"),
]

entities = [
    ("le_ionic", "legal_entity", "Ionic Digital Inc.", "Owner of the Ward County, TX property; Nscale's landlord there."),
    ("le_whitefiber", "legal_entity", "WhiteFiber, Inc.", "Parent of the NC-1 colocation provider (majority-owned by Bit Digital)."),
    ("le_enovum_nc1", "legal_entity", "Enovum NC-1 Bidco, LLC", "WhiteFiber subsidiary providing colocation at NC-1."),
    ("le_kinrg", "legal_entity", "KiNRG, Inc.", "Supplier at Ward County; nature of service not yet read."),
    ("le_obdc", "legal_entity", "Blue Owl Capital Corp (OBDC)", ""),
    ("le_ocic", "legal_entity", "Blue Owl Credit Income Corp. (OCIC)", ""),
    ("le_otf", "legal_entity", "Blue Owl Technology Finance Corp. (OTF)", ""),
    ("le_otic", "legal_entity", "Blue Owl Technology Income Corp. (OTIC)", ""),
    ("le_obdc2", "legal_entity", "Blue Owl Capital Corp II", ""),
    ("le_pimco_pdi", "legal_entity", "PIMCO Dynamic Income Fund (PDI)", ""),
    ("le_fidelity_bcg", "legal_entity", "Fidelity Series Blue Chip Growth Fund", ""),
    ("lease_nc1", "lease", "NC-1 colocation services agreement (WhiteFiber)", ""),
]
links = [
    ("le_ward_county_landlord", "same_as", "le_ionic", "Ionic's 10-Q describes a 126-month triple-net lease of its owned Ward County property to Nscale Ward County LLC; the S-1 calls this counterparty 'the Landlord'."),
    ("le_obdc", "part_of", "le_blue_owl_bdc", "Individual Blue Owl fund within the Blue Owl BDC family."),
    ("le_ocic", "part_of", "le_blue_owl_bdc", "As above."),
    ("le_otf", "part_of", "le_blue_owl_bdc", "As above."),
    ("le_enovum_nc1", "part_of", "le_whitefiber", "Wholly owned subsidiary per WhiteFiber 10-Q."),
]

rows = []


def add(entity, prop, value, source, locator, effective="", method=D, unit="", note="", derived_from=""):
    rows.append(dict(entity=entity, property=prop, value=value, unit=unit, source=source, locator=locator,
                     effective_date=effective, observed_date=OBS, method=method, derived_from=derived_from,
                     extractor="manual:claude-creditor-filings", note=note))


Q2 = "2026-06-30"
SOI = "Consolidated schedule of investments"
UNF = "Unfunded commitments table"

# ---- Blue Owl loan holdings (amounts reported in $ thousands) ----
for fund, src, par, cost, fv, unfunded in [
    ("obdc", "src_obdc_10q", "1397K", "831K", "900K", "38344K"),
    ("ocic", "src_ocic_10q", "5587K", "3325K", "3600K", "153377K"),
    ("otf", "src_otf_10q", "6984K", "4003K", "4500K", "191722K"),
]:
    h = f"hold_{fund}_gpu_ddtl"
    entities.append((h, "holding", f"Blue Owl {fund.upper()}: NSCALE SERVICES UK LTD first-lien DDTL", ""))
    add(h, "group", G, src, SOI)
    add(h, "holder", f"le_{fund}", src, SOI)
    add(h, "facility", "fac_uk_gpu_ddtl", src, SOI, note="Borrower 'NSCALE SERVICES UK LTD', S+5.00%, first lien DDTL: matches the GPU Financing Facility.")
    add(h, "borrower_as_named", "NSCALE SERVICES UK LTD", src, SOI)
    add(h, "instrument", "First lien senior secured delayed draw term loan", src, SOI)
    add(h, "margin_bps", "500", src, SOI, Q2, unit="bps")
    add(h, "maturity_date", "2031-02", src, SOI)
    add(h, "par_funded", par, src, SOI, Q2, unit="USD")
    add(h, "amortized_cost", cost, src, SOI, Q2, unit="USD", note="Below par because fees/discount on the large unfunded commitment are netted in; not a price signal.")
    add(h, "fair_value", fv, src, SOI, Q2, unit="USD")
    add(h, "unfunded_commitment", unfunded, src, UNF, Q2, unit="USD")
    add(h, "commitment_expiry", "2027-08", src, UNF)
    add("fac_uk_gpu_ddtl", "lender", f"le_{fund}", src, SOI)
    add("fac_uk_gpu_ddtl", "maturity_date", "2031-02", src, SOI, note="Holder-reported maturity.")

# ---- Equity holdings: Series B preferred shares (same class, different holders and dates) ----
for fund, src, units, fv, as_of in [
    ("obdc", "src_obdc_10q", "579420", "9299K", Q2),
    ("ocic", "src_ocic_10q", "1372740", "22031K", Q2),
    ("otf", "src_otf_10q", "790440", "12686K", Q2),
    ("otic", "src_otic_10q", "352260", "5653K", Q2),
    ("obdc2", "src_obdc2_10q", "64020", "1027K", Q2),
    ("fidelity_bcg", "src_fidelity_bcg_nport", "60000", "1256400", "2026-07-31"),
]:
    h = f"hold_{fund}_series_b"
    entities.append((h, "holding", f"{fund.upper()}: Nscale Limited Series B preferred shares", ""))
    fv_row = len(rows) + 6
    units_row = len(rows) + 5
    add(h, "group", G, src, SOI)
    add(h, "holder", f"le_{fund}", src, SOI)
    add(h, "issuer", "le_nscale_ltd", src, SOI)
    add(h, "instrument", "Series B Preferred Shares", src, SOI)
    add(h, "fair_value_level", "3", src, SOI if fund != "fidelity_bcg" else "fairValLevel")
    add(h, "units_held", units, src, SOI, as_of, unit="shares")
    add(h, "fair_value", fv, src, SOI, as_of, unit="USD")
    rows_ids = (units_row, fv_row)
    add(h, "price_per_unit", "", "src_internal", "", as_of, method="derived", unit="USD",
        derived_from=f"__ROW{fv_row}__;__ROW{units_row}__", note="Fair value / shares held.")

# ---- PIMCO loan holding (N-PORT, structured fields) ----
h = "hold_pimco_pdi_loan"
entities.append((h, "holding", "PIMCO PDI: 'Nscale AS' floating-rate loan", ""))
P = "src_pimco_pdi_nport"
add(h, "group", G, P, "invstOrSec")
add(h, "holder", "le_pimco_pdi", P, "invstOrSec")
add(h, "borrower_as_named", "Nscale AS", P, "invstOrSec: title")
add(h, "instrument", "Loan (assetCat LON), floating", P, "invstOrSec: assetCat, couponKind")
add(h, "facility", "fac_uk_gpu_ddtl", "src_internal", "", method="estimated",
    note="8.66% is about SOFR + 5.00% and PIMCO funds sign the GPU Financing Facility amendments; but PIMCO labels the borrower 'Nscale AS' (a Norwegian entity), not Nscale Services UK Ltd. Confirm.")
add(h, "par_funded", "18877004.78", P, "invstOrSec: balance", Q2, unit="USD")
add(h, "fair_value", "18880339.97", P, "invstOrSec: valUSD", Q2, unit="USD")
add(h, "mark_pct_par", "100.02", "src_internal", "", Q2, method="derived", unit="pct",
    derived_from=f"__ROW{len(rows) - 1}__;__ROW{len(rows) - 2}__", note="Fair value / par.")
add(h, "rate", "8.66", P, "invstOrSec: annualizedRt", Q2, unit="pct")
add(h, "maturity_date", "2032-08-23", P, "invstOrSec: maturityDt")
add(h, "fair_value_level", "3", P, "invstOrSec: fairValLevel")

# ---- Landlord: Ionic Digital (Ward County) ----
I = "src_ionic_10q"
MD = "MD&A: overview and trends"
add("le_ionic", "name", "Ionic Digital Inc.", I, "Cover page")
add("le_ionic", "role", "landlord", I, MD)
add("le_ionic", "sec_cik", "2007691", I, "EDGAR")
add("le_ionic", "dependency", "Digital infrastructure leasing revenue (from the Nscale lease) is its strategic growth business; seeking to expand Ward County to 700 MW", I, MD)
add("lease_ward_county", "landlord", "le_ionic", I, MD, note="'126-month triple net lease with Nscale Ward County LLC'.")
add("lease_ward_county", "tenant", "le_nscale_ward_county_llc", I, MD)
add("lease_ward_county", "term_months", "126", I, MD, unit="months")
add("lease_ward_county", "lease_type", "Triple net lease", I, MD)
add("lease_ward_county", "mw", "234", I, MD, Q2, unit="MW", note="'234 MW currently leased to Nscale'.")
add("lease_ward_county", "expansion_obligation", "Nscale contractually obliged to lease a further 89 MW when available; no penalty to Ionic if it cannot provide it", I, MD)
add("lease_ward_county", "start_date", "2025-10", I, MD, note="Lease announced October 2025.")
add("lease_ward_county", "landlord_revenue_6m", "87.9M", I, "Results: six months", Q2, unit="USD", note="Ionic's digital infrastructure leasing revenue, H1 2026 (Q2: $43.8M).")
add("site_ward_county", "landlord", "le_ionic", I, MD)
add("site_ward_county", "ownership", "leased", I, MD)

# ---- Colocation provider: WhiteFiber (North Carolina NC-1) ----
W = "src_whitefiber_10q"
add("le_whitefiber", "name", "WhiteFiber, Inc.", W, "Cover page")
add("le_whitefiber", "sec_cik", "2042022", W, "EDGAR")
add("le_whitefiber", "dependency", "Nscale is the sole contracted tenant at its NC-1 campus (risk factor)", W, "Forward-looking statements / risk factors")
add("le_enovum_nc1", "name", "Enovum NC-1 Bidco, LLC", W, "Nscale Services Agreement")
add("le_enovum_nc1", "role", "landlord", W, "Nscale Services Agreement")
add("lease_nc1", "group", G, W, "Nscale Services Agreement")
add("lease_nc1", "landlord", "le_enovum_nc1", W, "Nscale Services Agreement")
add("lease_nc1", "tenant", "le_nscale_services_us", W, "Nscale Services Agreement", note="Counterparties: Nscale Services US Inc. and Nscale Global Holdings Limited.")
add("lease_nc1", "guarantor", "le_nscale_global_holdings", W, "Nscale Services Agreement", method="estimated", note="Named as a party with Nscale Services US; guarantee role not confirmed.")
add("lease_nc1", "site", "site_north_carolina", W, "Nscale Services Agreement")
add("lease_nc1", "lease_type", "Colocation and related services agreement", W, "Nscale Services Agreement")
add("lease_nc1", "start_date", "2025-11", W, "Nscale Services Agreement")
add("lease_nc1", "term_months", "", W, "Nscale Services Agreement", method="checked_absent")
add("site_north_carolina", "name", "NC-1 campus (WhiteFiber)", W, "Nscale Services Agreement")
add("site_north_carolina", "landlord", "le_enovum_nc1", W, "Nscale Services Agreement")
add("site_north_carolina", "energization_target_date", "2026-09", W, "MD&A: outlook", method="reported", note="'expects to begin delivering capacity to Nscale during the third quarter' of 2026; revenue starts 30 days after completion.")

# ---- Supplier: KiNRG ----
K = "src_kinrg_10q"
add("le_kinrg", "name", "KiNRG, Inc.", K, "Cover page")
add("le_kinrg", "largest_customer", "le_nscale_ward_county_llc", K, "Note 19: Major customers", Q2)
add("le_kinrg", "largest_customer_revenue_share", "86", K, "Note 19: Major customers", Q2, unit="pct", note="86% of revenue in the three and six months to 30 June 2026.")
add("le_kinrg", "dependency", "One major customer (Nscale Ward County LLC) = 86% of revenue", K, "Note 19: Major customers")

# ---- resolve row placeholders into statement ids ----
start = 3000
for r in rows:
    if r["derived_from"].startswith("__ROW"):
        r["derived_from"] = ";".join(f"st{start + int(x.strip('_ROW')):04d}" for x in r["derived_from"].split(";"))
for r in rows:
    if r["property"] == "price_per_unit":
        a, b = r["derived_from"].split(";")
        fv = next(x for i, x in enumerate(rows) if f"st{start + i:04d}" == a)
        units = next(x for i, x in enumerate(rows) if f"st{start + i:04d}" == b)
        def num(v):
            return float(v[:-1]) * 1000 if v.endswith("K") else float(v)
        r["value"] = f"{num(fv['value']) / num(units['value']):.2f}"


def append(path, fieldnames, items):
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fieldnames).writerows(items)


append(REPO / "data/sources.csv", ["id", "type", "access", "publisher", "title", "url", "published_date", "retrieved_date", "note"],
       [dict(id=i, type=t, access="full_document", publisher=p, title=ti, url=u, published_date=d, retrieved_date=OBS, note="")
        for i, t, p, ti, u, d in sources])
append(REPO / "data/entities.csv", ["id", "type", "label", "note"], [dict(id=a, type=b, label=c, note=d) for a, b, c, d in entities])
append(REPO / "data/entity_links.csv", ["entity_a", "relation", "entity_b", "judged_by", "judged_date", "note"],
       [dict(entity_a=a, relation=r, entity_b=b, judged_by="claude (pending analyst review)", judged_date=OBS, note=n) for a, r, b, n in links])
fields = ["id", "entity", "property", "value", "unit", "source", "locator", "effective_date", "observed_date",
          "method", "derived_from", "extractor", "note"]
append(REPO / "data/statements.csv", fields, [dict(id=f"st{start + n:04d}", **r) for n, r in enumerate(rows)])
print(f"{len(rows)} statements, {len(entities)} entities, {len(sources)} sources, {len(links)} links")
