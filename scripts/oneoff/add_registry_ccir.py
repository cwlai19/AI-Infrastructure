"""One-off: append Companies House registry facts, S-1-verified draws, CCIR full-page facts and analyst reviews."""
import csv
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
OBS = "2026-10-29"
D = "disclosed"
CH = "https://find-and-update.company-information.service.gov.uk/company/"

sources = [
    ("src_ch_16925886", "registry", "full_document", "Companies House", "NSCALE PLC (16925886): profile, charges, filing history", CH + "16925886"),
    ("src_ch_15749408", "registry", "full_document", "Companies House", "NSCALE GLOBAL HOLDINGS LIMITED (15749408): profile and charges", CH + "15749408"),
    ("src_ch_16445102", "registry", "full_document", "Companies House", "NSCALE SERVICES UK LTD (16445102): profile and charges", CH + "16445102"),
    ("src_ch_16408148", "registry", "full_document", "Companies House", "NSCALE DRIFT II HOLDINGS LTD (16408148): profile and charges", CH + "16408148"),
    ("src_ch_16890967", "registry", "full_document", "Companies House", "NSCALE SERVICES UK III LIMITED (16890967): profile and charges", CH + "16890967"),
    ("src_ch_16890339", "registry", "full_document", "Companies House", "NSCALE SERVICES INTERMEDIATE HOLDINGS III LIMITED (16890339): profile and charges", CH + "16890339"),
    ("src_ccir_nscale_full", "aggregator", "full_document", "CCIR (Compute Credit Index Research)", "Nscale Debt & Credit Facilities: As Filed (full page, as of 2026-10-27)", "https://ccir.io/credit/issuer/nscale"),
]

entities = [("le_af_realizations", "legal_entity", "Af Realizations Sàrl", "Security agent on a satisfied 2025 charge.")]
rows = []


def add(entity, prop, value, source, locator, effective="", method=D, unit="", note="", derived_from=""):
    rows.append(dict(entity=entity, property=prop, value=value, unit=unit, source=source, locator=locator,
                     effective_date=effective, observed_date=OBS, method=method, derived_from=derived_from,
                     extractor="manual:claude-registry-and-ccir", note=note))


# ---- registry profiles ----
profiles = {
    "le_nscale_ltd": ("16925886", "2025-12-22"),
    "le_nscale_global_holdings": ("15749408", "2024-05-29"),
    "le_nscale_services_uk": ("16445102", "2025-05-12"),
    "le_drift_ii_holdings": ("16408148", "2025-04-25"),
    "le_services_uk_iii": ("16890967", "2025-12-04"),
    "le_services_intermediate_iii": ("16890339", "2025-12-04"),
}
for eid, (num, created) in profiles.items():
    src = f"src_ch_{num}"
    add(eid, "registry_id", num, src, "Company profile")
    add(eid, "jurisdiction", "England and Wales", src, "Company profile")
    add(eid, "incorporated_date", created, src, "Company profile")
    add(eid, "status", "active", src, "Company profile", OBS)
add("le_nscale_ltd", "name", "NSCALE PLC", "src_ch_16925886", "Company profile; RR01 re-registration 2026-10-09", "2026-10-09",
    note="Re-registered private to public on 9 Oct 2026, after the S-1 (which still says Ltd).")
add("le_nscale_ltd", "name", "NSCALE LIMITED", "src_ch_16925886", "Previous company names", "2026-04-16")
add("le_nscale_ltd", "name", "DSNS HOLDINGS LIMITED", "src_ch_16925886", "Previous company names", "2025-12-22")
add("le_drift_ii_holdings", "name", "NSCALE JV 25-1 HOLDINGS LTD", "src_ch_16408148", "Previous company names")

# ---- registered charges (security interests) ----
charges = [
    # id, chargor, chargee, created, code, status, source, secures, secures_note
    ("chg_16925886_a", "le_nscale_ltd", "le_glas", "2026-07-23", "", "outstanding", "src_ch_16925886", "fac_parent_rcf", "GLAS Americas is RCF collateral agent; Nscale Limited became successor borrower in July 2026."),
    ("chg_16925886_b", "le_nscale_ltd", "le_glas", "2026-07-23", "", "satisfied", "src_ch_16925886", "fac_parent_rcf", "Satisfied in full; MR04 filed 2026-10-11."),
    ("chg_157494080005", "le_nscale_global_holdings", "le_glas", "2026-05-08", "157494080005", "outstanding", "src_ch_15749408", "fac_parent_rcf", "Created on the RCF signing date; GLAS Americas is RCF collateral agent."),
    ("chg_157494080006", "le_nscale_global_holdings", "le_glas", "2026-05-08", "157494080006", "outstanding", "src_ch_15749408", "fac_parent_rcf", "As above."),
    ("chg_157494080007", "le_nscale_global_holdings", "le_glas", "2026-05-08", "157494080007", "outstanding", "src_ch_15749408", "fac_parent_rcf", "As above."),
    ("chg_157494080008", "le_nscale_global_holdings", "le_glas", "2026-05-08", "157494080008", "outstanding", "src_ch_15749408", "fac_parent_rcf", "As above."),
    ("chg_157494080003", "le_nscale_global_holdings", "le_macquarie", "2025-06-12", "157494080003", "satisfied", "src_ch_15749408", "fac_macquarie_glomfjord", "Created on the Macquarie SFA date; now satisfied, consistent with the borrower moving to Drift II Holdings."),
    ("chg_157494080004", "le_nscale_global_holdings", "le_sandton", "2025-08-01", "157494080004", "satisfied", "src_ch_15749408", "fac_sandton", ""),
    ("chg_157494080002", "le_nscale_global_holdings", "le_sandton", "2025-05-12", "157494080002", "satisfied", "src_ch_15749408", "fac_sandton", "Intellectual property charge."),
    ("chg_157494080001", "le_nscale_global_holdings", "le_af_realizations", "2025-05-12", "157494080001", "satisfied", "src_ch_15749408", "", "Intellectual property charge; facility not identified."),
    ("chg_164451020007", "le_nscale_services_uk", "le_glas", "2026-08-28", "164451020007", "outstanding", "src_ch_16445102", "fac_uk_gpu_ddtl", "GLAS Trust is GPU Financing Facility collateral agent; dated around the August 2026 $329M draw."),
] + [
    (f"chg_16445102000{i}", "le_nscale_services_uk", "le_glas", "2026-03-31", f"16445102000{i}", "outstanding", "src_ch_16445102", "fac_uk_gpu_ddtl", "GLAS Trust is GPU Financing Facility collateral agent.")
    for i in range(1, 7)
] + [
    ("chg_164081480001", "le_drift_ii_holdings", "le_macquarie", "2025-06-12", "164081480001", "outstanding", "src_ch_16408148", "fac_macquarie_glomfjord", "Created on the Macquarie SFA date (12 June 2025)."),
    ("chg_164081480003", "le_drift_ii_holdings", "le_macquarie", "2026-08-10", "164081480003", "outstanding", "src_ch_16408148", "fac_macquarie_glomfjord", "Additional Macquarie security, August 2026."),
    ("chg_164081480002", "le_drift_ii_holdings", "le_sandton", "2025-08-01", "164081480002", "satisfied", "src_ch_16408148", "fac_sandton", "Second-ranking Sandton security, released on repayment."),
    ("chg_168909670001", "le_services_uk_iii", "le_macquarie", "2026-07-29", "168909670001", "outstanding", "src_ch_16890967", "fac_macquarie_iceland", "Created on the Macquarie Iceland SFA date."),
    ("chg_168909670002", "le_services_uk_iii", "le_macquarie", "2026-09-14", "168909670002", "outstanding", "src_ch_16890967", "fac_macquarie_iceland", ""),
    ("chg_168903390001", "le_services_intermediate_iii", "le_macquarie", "2026-07-29", "168903390001", "outstanding", "src_ch_16890339", "fac_macquarie_iceland", "Created on the Macquarie Iceland SFA date."),
]
for cid, chargor, chargee, created, code, status, src, secures, note in charges:
    entities.append((cid, "charge", f"Charge {code or cid} over {chargor}", ""))
    add(cid, "chargor", chargor, src, "Charges register")
    add(cid, "chargee", chargee, src, "Charges register")
    add(cid, "created_date", created, src, "Charges register")
    add(cid, "status", status, src, "Charges register", OBS)
    if code:
        add(cid, "registry_charge_id", code, src, "Charges register")
    if secures:
        add(cid, "secures_facility", secures, "src_internal", "", method="estimated", note=note or "Matched on chargee and date.")

# ---- S-1-verified draws and dates (found via CCIR, checked in the S-1) ----
S1, SE = "src_s1_full", "Subsequent events / MD&A"
draw_rcf = len(rows)
add("fac_parent_rcf", "amount_drawn", "830.0M", S1, SE, "2026-09-18", unit="USD", note="'Since June 30, 2026, we have utilized an aggregate of $830.0 million of commitments under the Revolving Credit Facility.'")
add("fac_parent_rcf", "status", "partly_drawn", S1, SE, "2026-09-18", note="$830M of $900M utilised.")
add("fac_uk_gpu_ddtl", "amount_drawn", "58.9M", S1, "Description of Certain Indebtedness", "2026-03-31", unit="USD")
add("fac_uk_gpu_ddtl", "amount_drawn", "329.0M", S1, SE, "2026-08", unit="USD", method="disclosed",
    note="Additional draw in August 2026 (a flow, not a balance) - see the derived cumulative figure.")
add("fac_norway_term_loan", "amount_drawn", "88.1M", S1, SE, "2026-08", unit="USD")
add("fac_norway_term_loan", "status", "partly_drawn", S1, SE, "2026-08")
add("fac_norway_vat_rcf", "amount_drawn", "19.1M", S1, SE, "2026-08", unit="USD")
add("fac_norway_vat_rcf", "status", "partly_drawn", S1, SE, "2026-08")
add("fac_convertible_2026", "maturity_date", "2028-06-15", S1, "Prospectus summary / MD&A", note="Unless earlier converted; converts automatically on IPO completion.")
add("fac_macquarie_glomfjord", "maturity_date", "2029-06-12", S1, "Notes to financial statements")
add("fac_uk_gpu_ddtl", "amount_max", "1.422B", "src_ex10_14", "Section 2.01: commitments on the Signing Date", "2026-02-11", unit="USD", note="$1,422,000,000 exactly; the prospectus rounds to ~$1.4B.")
add("fac_parent_rcf", "financial_covenants", "Total net leverage <= 6.00x tested quarterly (step-up allowed after a material acquisition)", "src_ex10_18", "Financial covenant section")
add("fac_macquarie_glomfjord", "named_customer", "le_spring_sg", "src_ex10_12", "Definitions: 'Spring Singapore'", note="Spring (SG) Pte. Ltd., Singapore company no. 202325236K; cloud services agreement dated 2025-05-15 per CCIR.")
add("fac_macquarie_iceland", "secured_on_site", "site_borealis", "src_ex10_22", "Definitions: 'Data Centre'")
add("fac_uk_gpu_ddtl", "lender", "le_pimco_funds", "src_ex10_15", "Signature pages (amendments 10.15-10.17)")
add("fac_uk_gpu_ddtl", "lender", "le_blue_owl_bdc", "src_ex10_15", "Signature pages: 'By: Blue Owl Credit Advisors LLC'")
entities += [
    ("le_spring_sg", "legal_entity", "Spring (SG) Pte. Ltd.", "Glomfjord customer."),
    ("le_pimco_funds", "legal_entity", "PIMCO-managed funds", "Pacific Investment Management Company LLC as investment manager; CCIR counts 29 funds/vehicles."),
    ("site_borealis", "site", "Borealis Data Centre, Blönduós, Iceland", "Third-party colocation."),
    ("le_stonepeak", "legal_entity", "Stonepeak Infrastructure Credit Fund I", ""),
    ("le_bofa", "legal_entity", "Bank of America", ""),
    ("le_morgan_stanley_mufg", "legal_entity", "Morgan Stanley MUFG Loan Partners, LLC", "RCF syndication agent."),
]
add("le_spring_sg", "registry_id", "202325236K", "src_ex10_12", "Definitions: 'Spring Singapore'")
add("le_spring_sg", "jurisdiction", "Singapore", "src_ex10_12", "Definitions: 'Spring Singapore'")
add("site_borealis", "country", "Iceland", "src_ex10_22", "Definitions: 'Data Centre'")
add("site_borealis", "group", "group_nscale", "src_ex10_22", "Definitions: 'Data Centre'")
add("site_borealis", "ownership", "colocation", "src_ex10_22", "Definitions: 'Data Centre Operator'")
add("site_borealis", "location", "Blönduós Campus, Iceland", "src_ex10_22", "Definitions: 'Data Centre'")

# ---- derived ----
first_draw, aug_draw = f"st{2000 + draw_rcf + 2:04d}", f"st{2000 + draw_rcf + 3:04d}"
add("fac_uk_gpu_ddtl", "amount_drawn", "387.9M", "src_internal", "", "2026-08-31", method="derived", unit="USD",
    derived_from=f"{first_draw};{aug_draw}",
    note="Cumulative drawn = 58.9M (by 31 Mar) + 329.0M (Aug). Assumes no repayments in between; the 30 June carrying value was 48.2M, so some amortisation may have occurred.")

# ---- CCIR full-page facts not in the S-1 passages we read (grade B) ----
C, CL = "src_ccir_nscale_full", "Instrument card"
add("fac_ward_county", "amount_max", "1.85B", C, CL + ": Ward County", "2026-08-27", unit="USD")
add("fac_ward_county", "rating_moodys", "Baa1", C, CL + ": Ward County", "2026-08-12", method="reported", note="Moody's first-time rating, stable, 12 Aug 2026; Moody's sized the facility at $1.831B.")
add("fac_ward_county", "financial_covenants", "Historical DSCR >= 1.05x; cash trap below 1.10x; loans sized at the lesser of 90% of GPU capex and a 1.30x sizing ratio", C, CL + ": Ward County", method="reported")
add("site_ward_county", "mw_contracted", "275", C, CL + ": Ward County", "2026-08-12", unit="MW", method="reported", note="Moody's rating action: ~275 MW IT load.")
add("site_ward_county", "mw_contracted", "200", C, CL + ": Ward County", "2026-08-31", unit="MW", method="reported", note="Nscale release 31 Aug 2026: ~200 MW IT load.")
add("site_ward_county", "landlord", "le_ward_county_landlord", C, CL + ": Ward County", method="reported", note="'land owned by third-party DC operator'; Nscale Ward County LLC is the data centre tenant.")
add("fac_north_carolina", "financial_covenants", "Historical DSCR >= 1.05x; cash trap below 1.10x; loans sized at the lesser of 90% of GPU capex and a 1.30x sizing ratio", C, CL + ": North Carolina", method="reported")
add("site_north_carolina", "location", "Madison County, North Carolina (96 acres)", C, CL + ": North Carolina", method="reported")
add("site_north_carolina", "ownership", "colocation", C, CL + ": North Carolina", method="reported")
add("site_north_carolina", "mw_contracted", "40", C, CL + ": North Carolina", "2026-08-31", unit="MW", method="reported", note="'up to 40 MW of IT load' per Nscale release.")
add("site_kvandal_south", "mw_contracted", "108", C, CL + ": Norway", unit="MW", method="reported", note="108 MW overall capacity.")
add("fac_norway_term_loan", "collateral", "site", C, CL + ": Norway", method="reported", note="Finances the DC building; GPUs and GPU servers are excluded from the financed asset.")
add("fac_norway_term_loan", "financial_covenants", "Historic DSCR >= 1.05x; net leverage within 30% of base case; cash trap below 1.15x; 6-month DSRA", C, CL + ": Norway", method="reported")
add("fac_norway_term_loan", "named_customer", "", C, CL + ": Norway", method="checked_absent", note="Revenue is a DC services agreement with an affiliated GPU company; counterparty redacted.")
add("fac_macquarie_iceland", "amortization", "Monthly; lenders must receive at least 1.18x their commitment (MOIC), including on voluntary prepayment", C, CL + ": Iceland", method="reported")
add("fac_macquarie_iceland", "availability_end_date", "2026-12-31", C, CL + ": Iceland", method="reported")
add("fac_macquarie_iceland", "named_customer", "", C, CL + ": Iceland", method="checked_absent", note="Customer, its guarantors and minimum fee per GPU-hour redacted.")
add("fac_macquarie_glomfjord", "collateral", "gpus", C, CL + ": Glomfjord", method="reported", note="2,304 NVIDIA B200 GPUs and 32 GB200 NVL72 servers at Glomfjord, plus a share charge.")
add("fac_macquarie_glomfjord", "amortization", "Monthly, cash sweep of free cash flow; MOIC 1.15x rising to 1.40x after month 37 (coefficients later amended, amendment not filed)", C, CL + ": Glomfjord", method="reported")
add("fac_uk_gpu_ddtl", "maturity_date", "2031-02", C, CL + ": GPU-backed DDTL", method="reported", note="As reported in Blue Owl BDC Q1-2026 10-Qs (holder filing).")
add("fac_uk_gpu_ddtl", "maturity_date", "2032-08-11", C, CL + ": GPU-backed DDTL", method="reported", note="As reported in 18 PIMCO NPORT-P filings, period 2026-03-31 (CUSIP BA000WQD0).")
add("fac_uk_gpu_ddtl", "financial_covenants", "Historical DSCR >= 1.05x; cash trap below 1.15x; only investment-grade customer contracts; advance up to 80% of cost capped by 1.20x sizing DSCR; 100% sweep if <85% of servers online", C, CL + ": GPU-backed DDTL", method="reported")
for le in ("le_stonepeak",):
    add("fac_uk_gpu_ddtl", "lender", le, C, CL + ": GPU-backed DDTL", method="reported", note="Not found in the exhibit text we searched.")
add("fac_parent_rcf", "maturity_date", "2029-05", C, CL + ": Revolving Credit Facility", method="reported", note="Third anniversary of an effective date within 60 days of 8 May 2026; two 1-year extensions at lenders' option.")
add("fac_parent_rcf", "lender", "le_bofa", C, CL + ": Revolving Credit Facility", method="reported", note="From the issuer release 2026-07-07 lender list.")
add("fac_parent_rcf", "lender", "le_deutsche_ny", C, CL + ": Revolving Credit Facility", method="reported")
add("fac_parent_rcf", "lender", "le_morgan_stanley_mufg", "src_s1_full", "Description of Certain Indebtedness", note="Syndication agent.")
add("fac_dell_vendor", "maturity_date", "2026-12-31", C, CL + ": Dell", method="estimated", note="CCIR's approximate date; schedules run 3-4 months from Aug/Sep 2026 plus 1-2 month extensions.")

reviews = [
    ("st0054", "rejected", "Misread from a search excerpt: CCIR's full page shows $1.831B is Moody's sizing in its 12 Aug 2026 rating action; the commitment is $1.85B (Ex-10.23 and CCIR card)."),
    ("st0086", "rejected", "Misread from a search excerpt: 7 July 2026 is the issuer release date; the RCF agreement is dated 8 May 2026 (Ex-10.18; CCIR full page agrees)."),
    ("st0123", "rejected", "11 May 2026 is the issuer release announcing the Norway financing; the Senior Facilities Agreement is dated 7 July 2026 (S-1; CCIR full page agrees)."),
    ("st0007", "explained", "'More than $8B of debt' in press coverage likely sums facility commitments (~$8-10B incl. Dell and convertibles). Borrowed debt on the balance sheet at 30 June 2026 was $137.4M; the large obligations are deferred revenue ($6.5B) and leases ($2.6B)."),
    ("st1216", "rejected", "The S-1 summary names Nscale Global Holdings, but Companies House shows Macquarie's June 2025 charge over Global Holdings satisfied and the same-date charge over Nscale Drift II Holdings outstanding; Ex-10.12 and CCIR also name Drift II Holdings."),
]

# ---- write ----
def append(path, fieldnames, items):
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        for it in items:
            w.writerow(it)

append(REPO / "data/sources.csv", ["id", "type", "access", "publisher", "title", "url", "published_date", "retrieved_date", "note"],
       [dict(id=i, type=t, access=a, publisher=p, title=ti, url=u, published_date="", retrieved_date=OBS, note="") for i, t, a, p, ti, u in sources])
append(REPO / "data/entities.csv", ["id", "type", "label", "note"], [dict(id=a, type=b, label=c, note=d) for a, b, c, d in entities])
fields = ["id", "entity", "property", "value", "unit", "source", "locator", "effective_date", "observed_date",
          "method", "derived_from", "extractor", "note"]
append(REPO / "data/statements.csv", fields, [dict(id=f"st{2000 + n:04d}", **r) for n, r in enumerate(rows)])
append(REPO / "data/reviews.csv", ["statement_id", "verdict", "reason", "reviewer", "date"],
       [dict(statement_id=s, verdict=v, reason=r, reviewer="claude (pending analyst review)", date=OBS) for s, v, r in reviews])
print(f"{len(rows)} statements, {len(entities)} entities, {len(sources)} sources, {len(reviews)} reviews")
