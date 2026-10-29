"""One-off: append statements read from the full Nscale S-1 and exhibits (read 2026-10-29)."""
import csv
import json
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
SUBS = json.load(open(sys.argv[2]))
OBS = "2026-10-29"
EXT = "manual:claude-full-read"
S1 = "https://www.sec.gov/Archives/edgar/data/2110365/000119312526395475/"

sources = [
    ("src_s1_full", "S-1 registration statement (full document)", "ck0002110365-20260918.htm"),
    ("src_ex10_12", "Ex-10.12 Amendment and restatement of Macquarie senior facility agreement (Nscale Drift II Holdings)", "ck0002110365-ex10_12.htm"),
    ("src_ex10_14", "Ex-10.14 GPU Credit Agreement (Nscale Services UK Ltd), 11 Feb 2026", "ck0002110365-ex10_14.htm"),
    ("src_ex10_18", "Ex-10.18 Revolving Credit and Guaranty Agreement, 8 May 2026", "ck0002110365-ex10_18.htm"),
    ("src_ex10_21", "Ex-10.21 Kvandal South DC Senior Facilities Agreement (DNB agent)", "ck0002110365-ex10_21.htm"),
    ("src_ex10_22", "Ex-10.22 Macquarie Iceland Senior Facility Agreement, 29 Jul 2026", "ck0002110365-ex10_22.htm"),
    ("src_ex10_23", "Ex-10.23 Ward County GPU Credit Agreement, 27 Aug 2026", "ck0002110365-ex10_23.htm"),
    ("src_ex10_24", "Ex-10.24 North Carolina GPU Credit Agreement, Aug 2026", "ck0002110365-ex10_24.htm"),
    ("src_ex10_25", "Ex-10.25 GPU Services Agreement with Anthropic PBC", "ck0002110365-ex10_25.htm"),
    ("src_ex21", "Ex-21.1 Subsidiaries of Nscale Limited", "ck0002110365-ex21_1.htm"),
]

entities = [
    # legal entities
    ("le_nscale_global_holdings", "legal_entity", "Nscale Global Holdings Limited", ""),
    ("le_nc_spv", "legal_entity", "Nscale NC Borrower SPV, LLC", ""),
    ("le_nscale_ward_county_llc", "legal_entity", "Nscale Ward County, LLC", "Affiliate guarantor of the Ward County facility."),
    ("le_nscale_services_us", "legal_entity", "Nscale Services US Inc.", ""),
    ("le_nscale_us_holdings", "legal_entity", "Nscale US Holdings Inc.", "Contract counterparty to Microsoft (Ward County) and the NC customer."),
    ("le_iceland_iii", "legal_entity", "Nscale Services Iceland III ehf", ""),
    ("le_norway_dc_da", "legal_entity", "Nscale Norway DC DA", ""),
    ("le_drift_ii_holdings", "legal_entity", "Nscale Drift II Holdings Ltd", ""),
    ("le_services_intermediate_iii", "legal_entity", "Nscale Services Intermediate Holdings III Limited", ""),
    ("le_services_uk_iii", "legal_entity", "Nscale Services UK III Limited", ""),
    ("le_gpu_mcc_b11", "legal_entity", "Nscale GPU MCC B1.1 LLC", "Provider named in the Anthropic agreement (Ex-10.25). Not in the Ex-21.1 list."),
    ("le_dfs", "legal_entity", "DFS (Dell Financial Services)", "Exact DFS legal entity not yet read."),
    ("le_macquarie", "legal_entity", "Macquarie Bank Limited (London Branch)", ""),
    ("le_dnb", "legal_entity", "DNB Bank ASA", ""),
    ("le_abn_amro", "legal_entity", "ABN AMRO Bank N.V.", ""),
    ("le_nordea", "legal_entity", "Nordea Bank Abp NUF", ""),
    ("le_efn", "legal_entity", "Export Finance Norway (Eksportfinansiering Norge)", ""),
    ("le_seb", "legal_entity", "Skandinaviska Enskilda Banken AB", ""),
    ("le_us_bank_trust", "legal_entity", "U.S. Bank Trust Company, National Association", ""),
    ("le_glas", "legal_entity", "Global Loan Agency Services (GLAS)", "GLAS Ltd / GLAS Trust Corporation / GLAS Americas acting as agents."),
    ("le_jpmorgan_chase", "legal_entity", "JPMorgan Chase Bank, N.A.", ""),
    ("le_goldman_bank_usa", "legal_entity", "Goldman Sachs Bank USA", ""),
    ("le_ca_cib", "legal_entity", "Crédit Agricole Corporate and Investment Bank", ""),
    ("le_deutsche_ny", "legal_entity", "Deutsche Bank AG, New York Branch", ""),
    ("le_mizuho", "legal_entity", "Mizuho Bank, Ltd.", ""),
    ("le_mufg", "legal_entity", "MUFG Bank, Ltd.", ""),
    ("le_rbc", "legal_entity", "Royal Bank of Canada", ""),
    ("le_smbc", "legal_entity", "Sumitomo Mitsui Banking Corporation", ""),
    ("le_smbc_bi", "legal_entity", "SMBC Bank International plc", ""),
    ("le_bbva_ny", "legal_entity", "Banco Bilbao Vizcaya Argentaria, S.A. New York Branch", ""),
    ("le_ocbc_ny", "legal_entity", "Oversea-Chinese Banking Corporation Limited, New York Agency", ""),
    ("le_keybank", "legal_entity", "KeyBank National Association", ""),
    ("le_td_ny", "legal_entity", "The Toronto-Dominion Bank, New York Branch", ""),
    ("le_anthropic", "legal_entity", "Anthropic PBC", ""),
    ("le_nvidia", "legal_entity", "NVIDIA Corporation", ""),
    ("le_figure", "legal_entity", "Figure (Figure AI)", "Exact legal entity not stated in the passages read."),
    ("le_aker", "legal_entity", "Aker (Aker Narvik DC AS, Aker Narvik GPU AS, Aker Holdco AS)", ""),
    ("le_sandton", "legal_entity", "Sandton Capital Solutions Master Fund V, L.P.", ""),
    ("le_ward_county_landlord", "legal_entity", "Ward County landlord (not named in S-1)", ""),
    # sites
    ("site_kvandal_south", "site", "Kvandal South (Stargate Norway)", "As the S-1 names it."),
    ("site_glomfjord", "site", "Glomfjord, Norway", ""),
    ("site_monarch", "site", "Monarch Compute Campus, Mason County WV", ""),
    ("site_sin02", "site", "SIN02, SINES Data Campus, Portugal", ""),
    # facilities
    ("fac_macquarie_iceland", "facility", "Macquarie Iceland Facility ($331.9M)", ""),
    ("fac_macquarie_glomfjord", "facility", "Macquarie Senior Facility, Glomfjord ($105M)", ""),
    ("fac_dell_vendor", "facility", "Dell (DFS) vendor financing (~$2.54B rent)", ""),
    ("fac_convertible_2026", "facility", "Convertible Loan Notes, Sept 2026 (min $3.1B incl. NVIDIA)", ""),
    ("fac_committed_2_35b", "facility", "Committed bank delayed-draw financings (~$2.35B, undocumented)", ""),
    ("fac_sandton", "facility", "Sandton term loans ($76.6M)", ""),
    ("fac_series_a_notes", "facility", "Series A Convertible Notes ($160M)", ""),
    # contracts and lease
    ("ctr_msft_sows", "contract", "Microsoft statements of work (aggregate, up to $43.8B)", ""),
    ("ctr_msft_sow1_ward", "contract", "Microsoft Partner SOW #1 (Ward County)", ""),
    ("ctr_nc_customer", "contract", "North Carolina Cloud Services Agreement (customer redacted)", ""),
    ("ctr_anthropic", "contract", "Anthropic Services Agreements (4 agreements, up to $44.6B)", ""),
    ("ctr_figure", "contract", "Figure Services Agreement", ""),
    ("ctr_nvidia_msa", "contract", "NVIDIA master cloud services agreement ($1.2B)", ""),
    ("lease_ward_county", "lease", "Ward County, Texas net lease", ""),
]

links = [
    ("site_narvik", "same_as", "site_kvandal_south", "CCIR calls the Kvandal South DC facility collateral the 'Narvik campus'; the S-1 puts Stargate Norway in Kvandal with Aker Narvik entities. Kvandal North is a separate site; confirm CCIR did not mean Kvandal North."),
    ("ctr_msft_narvik", "part_of", "ctr_msft_sows", "CCIR's $6.2B Narvik deal should be one of the Microsoft SOWs (Sept 2025 - Apr 2026); the S-1 gives only the aggregate."),
    ("ctr_msft_sow1_ward", "part_of", "ctr_msft_sows", "Named as the Customer Contract in the Ward County credit agreement."),
]

D = "disclosed"
rows = []


def add(entity, prop, value, source, locator, effective="", method=D, unit="", note="", derived_from=""):
    rows.append(dict(entity=entity, property=prop, value=value, unit=unit, source=source, locator=locator,
                     effective_date=effective, observed_date=OBS, method=method, derived_from=derived_from,
                     extractor=EXT, note=note))


G = "group_nscale"
IND = "MD&A, Indebtedness (pp. 96-98)"
DCI = "Description of Certain Indebtedness (pp. 149-152)"
BS = "Interim condensed balance sheet, June 30 2026"

# ---- group ----
add(G, "total_assets", "17252.0M", "src_s1_full", BS, "2026-06-30", unit="USD")
add(G, "total_liabilities", "12359.8M", "src_s1_full", BS, "2026-06-30", unit="USD")
add(G, "total_equity", "4792.2M", "src_s1_full", "Summary financial data (p. ~18)", "2026-06-30", unit="USD")
add(G, "total_debt", "137.4M", "src_s1_full", "Interim note 8, Debt and other financing", "2026-06-30", unit="USD",
    note="Borrowed debt only: GPU Financing Facility 48.2M + Macquarie Senior 89.2M; RCF undrawn. Excludes leases, Dell vendor financing and deferred revenue.")
add(G, "cash_and_equivalents", "1478.4M", "src_s1_full", "Liquidity and Capital Resources (p. 94)", "2026-06-30", unit="USD")
add(G, "restricted_cash", "570.3M", "src_s1_full", BS, "2026-06-30", unit="USD", note="Noncurrent restricted cash; includes the $470M NVIDIA lease-guarantee escrow.")
add(G, "deferred_revenue", "6492.6M", "src_s1_full", BS, "2026-06-30", unit="USD",
    note="Current 1,217.9M + noncurrent 5,274.7M. Mostly customer prepayments to be repaid in delivered service.")
add(G, "operating_lease_liabilities", "2625.4M", "src_s1_full", BS, "2026-06-30", unit="USD", note="Current 225.7M + noncurrent 2,399.7M.")
add(G, "leases_not_commenced", "1.4B", "src_s1_full", "Commitments: Colocation Agreements (p. 98)", "2026-06-30", unit="USD", note="Aggregate undiscounted payments for colocation leases not yet commenced.")
add(G, "construction_commitments", "3.5B", "src_s1_full", "Commitments: Data Center Build (p. 98)", "2026-06-30", unit="USD", note="Payable primarily 2026-2027.")
add(G, "equipment_purchase_commitments", "24.0B", "src_s1_full", "Commitments: Technology Equipment (p. 98)", "2026-06-30", unit="USD", note="Technology equipment not yet delivered, payable primarily 2026-2027.")
add(G, "revenue_6m", "140.6M", "src_s1_full", "Business overview (p. 105)", "2026-06-30", unit="USD")
add(G, "revenue_12m", "33.0M", "src_s1_full", "Business overview (p. 105)", "2025-12-31", unit="USD")
add(G, "net_loss_6m", "1020.1M", "src_s1_full", "Summary: key metrics (p. ~13)", "2026-06-30", unit="USD", note="Six months to 30 June 2026; net loss margin (726)%.")
add(G, "net_loss_12m", "761.8M", "src_s1_full", "Summary: key metrics (p. ~13)", "2025-12-31", unit="USD")
add(G, "tcv_active", "2.6B", "src_s1_full", "Customers and Business Model (p. 114)", "2026-08-31", unit="USD")
add(G, "tcv_active_and_contracted", "103.4B", "src_s1_full", "Customers and Business Model (p. 114)", "2026-08-31", unit="USD", note="Take-or-pay TCV, active + contracted. Includes Microsoft up to $43.8B and Anthropic up to $44.6B.")
add(G, "weighted_avg_contract_years", "5.7", "src_s1_full", "Customers and Business Model (p. 114)", "2026-08-31", unit="years")
add(G, "gpus_active", "25000", "src_s1_full", "Business overview (p. 104)", "2026-08-31", unit="GPUs")
add(G, "gpus_active_and_contracted", "461000", "src_s1_full", "Business overview (p. 104)", "2026-08-31", unit="GPUs")
add(G, "sites_active", "5", "src_s1_full", "Business overview (p. 104)", "2026-08-31", unit="sites")
add(G, "sites_contracted", "12", "src_s1_full", "Business overview (p. 104)", "2026-08-31", unit="sites", note="7 owned, 9 colocation, 1 leased across active + contracted.")
add(G, "mw_contracted_total", "1370", "src_s1_full", "Business overview (p. 104)", "2026-08-31", unit="MW", note="1.37 GW active + contracted: 1 GW owned, 200 MW leased, 165 MW colocation.")
add(G, "mw_energized_total", "", "src_s1_full", "Business overview (p. 104)", method="checked_absent", note="S-1 gives active GPUs and sites but no active MW figure in the passages read.")
add(G, "largest_customer_revenue_share", "52", "src_s1_full", "Risk factors: customer concentration", "2026-06-30", unit="pct", note="Largest customer = 52% of H1 2026 revenue; 73% in FY2025; ~all in FY2024.")
add(G, "largest_customer_revenue_share", "73", "src_s1_full", "Risk factors: customer concentration", "2025-12-31", unit="pct")
add(G, "ticker", "NSCL", "src_s1_full", "Prospectus cover")
add(G, "listing_venue", "NYSE (applied)", "src_s1_full", "Prospectus cover", "2026-09-18")
add(G, "subsidiary_count", str(len(SUBS)), "src_ex21", "Ex-21.1 table", "2026-09-18", unit="entities")

# ---- legal entities ----
ent_names = {
    "le_nscale_ltd": ("NSCALE Ltd", "England and Wales"),
    "le_nscale_global_holdings": ("Nscale Global Holdings Limited", "United Kingdom"),
    "le_nscale_services_uk": ("Nscale Services UK Ltd", "United Kingdom"),
    "le_ward_county_spv": ("Nscale Ward County Borrower SPV, LLC", "United States (Delaware)"),
    "le_nc_spv": ("Nscale NC Borrower SPV, LLC", "United States (Delaware)"),
    "le_nscale_ward_county_llc": ("Nscale Ward County LLC", "United States (Delaware)"),
    "le_nscale_services_us": ("Nscale Services US Inc", "United States (Delaware)"),
    "le_nscale_us_holdings": ("Nscale US Holdings Inc. (US)", "United States (Delaware)"),
    "le_iceland_iii": ("Nscale Services Iceland III ehf", "Iceland"),
    "le_norway_dc_da": ("Nscale Norway DC DA", "Norway"),
    "le_drift_ii_holdings": ("Nscale Drift II Holdings Ltd", "United Kingdom"),
    "le_services_intermediate_iii": ("Nscale Services Intermediate Holdings III Limited", "United Kingdom"),
    "le_services_uk_iii": ("Nscale Services UK III Limited", "United Kingdom"),
}
for eid, (name, jur) in ent_names.items():
    if eid != "le_nscale_ltd":
        add(eid, "name", name, "src_ex21", "Ex-21.1 table")
    add(eid, "jurisdiction", jur, "src_ex21" if eid != "le_nscale_ltd" else "src_ex21", "Ex-21.1 table" if eid != "le_nscale_ltd" else "Ex-21.1 footnote")
    add(eid, "group", G, "src_ex21", "Ex-21.1 table")
add("le_gpu_mcc_b11", "group", G, "src_ex10_25", "Order form: Provider Name")
add("le_gpu_mcc_b11", "name", "Nscale GPU MCC B1.1 LLC", "src_ex10_25", "Order form: Provider Name")
add("le_ward_county_spv", "role", "spv", "src_ex10_23", "Cover page")
add("le_ward_county_spv", "role", "borrower", "src_ex10_23", "Cover page")
add("le_nc_spv", "role", "spv", "src_ex10_24", "Cover page")
add("le_nc_spv", "role", "borrower", "src_ex10_24", "Cover page")
add("le_nscale_global_holdings", "role", "holdco", "src_s1_full", DCI)
add("le_nscale_ltd", "role", "borrower", "src_s1_full", DCI, note="Successor borrower under the RCF from July 2026.")
add("le_ward_county_landlord", "name", "", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)", method="checked_absent", note="S-1 refers only to 'the Landlord'.")
add("le_ward_county_landlord", "role", "landlord", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)")

# ---- facilities ----
def fac(fid, **props):
    for prop, spec in props.items():
        if isinstance(spec, list):
            for item in spec:
                add(fid, prop, *item)
        else:
            add(fid, prop, *spec)

fac("fac_uk_gpu_ddtl",
    name=("GPU Financing Facility", "src_s1_full", DCI),
    borrower=("le_nscale_services_uk", "src_ex10_14", "Cover page", "2026-02-11"),
    amount_max=("1.4B", "src_s1_full", DCI, "2026-02-11", D, "USD", "'approximately $1.4 billion'; incremental capacity up to $350M."),
    signing_date=("2026-02-11", "src_ex10_14", "Cover page"),
    base_rate=("Term SOFR", "src_s1_full", DCI),
    margin_bps=("500", "src_s1_full", DCI, "", D, "bps", "Subject to a 25bp step-up in certain circumstances; 0% floor."),
    maturity_date=("2032-09-30", "src_s1_full", DCI, "", "estimated", "", "Latest possible date: each loan matures at the earlier of its final scheduled amortization date and 5 years after the availability period ends (30 Sept 2027)."),
    availability_end_date=("2027-09-30", "src_s1_full", DCI),
    collateral=("all_assets", "src_s1_full", DCI, "", D, "", "First-priority security over substantially all assets of the borrower and subsidiary guarantors."),
    agent=[("le_glas", "src_s1_full", DCI, "", D, "", "GLAS Ltd administrative agent; GLAS Trust Corporation collateral agent.")],
    financial_covenants=("Debt service coverage ratio; cash trap tied to DSCR levels", "src_s1_full", DCI),
    mandatory_prepayment=("Asset dispositions, casualty events, concentration limit breaches, customer contract terminations, DSCR cash-trap events, change of control", "src_s1_full", DCI),
    carrying_value=("48.2M", "src_s1_full", "Interim note 8", "2026-06-30", D, "USD"),
    unused_capacity=("1363.1M", "src_s1_full", "Interim note 8", "2026-06-30", D, "USD"),
    effective_interest_rate=("11.30", "src_s1_full", "Interim note 8", "2026-06-30", D, "pct"),
    status=("partly_drawn", "src_s1_full", "Interim note 8", "2026-06-30"),
    accordion=("350M", "src_s1_full", DCI, "", D, "USD"),
    named_customer=("", "src_ex10_14", "Definitions: Customer", "", "checked_absent", "", "Defined generically as the counterparty to any Customer Contract."),
)
fac("fac_ward_county",
    name=("Ward County GPU Facility", "src_s1_full", DCI),
    borrower=("le_ward_county_spv", "src_ex10_23", "Cover page", "2026-08-27"),
    amount_max=("1.85B", "src_s1_full", DCI, "2026-08-27", D, "USD", "$630M fixed-rate + $1.22B floating-rate delayed-draw commitments."),
    signing_date=("2026-08-27", "src_ex10_23", "Cover page"),
    base_rate=("3-month Term SOFR (floating tranche); SOFR swap rate (fixed tranche)", "src_s1_full", DCI),
    margin_bps=("237.5", "src_s1_full", DCI, "", D, "bps", "Floating: SOFR + 2.375% (or base + 1.375%). Fixed: 2.375% + SOFR swap rate."),
    maturity_date=("2033-02-27", "src_s1_full", DCI, "", D, "", "Earlier of the customer's final scheduled payment and 27 Feb 2033."),
    amortization=("Quarterly, tranche by tranche, starting when customer payments for that tranche begin", "src_s1_full", DCI),
    collateral=[("all_assets", "src_s1_full", DCI), ("shares", "src_s1_full", DCI, "", D, "", "Equity interests of the borrower and affiliate guarantor.")],
    named_customer=[("le_microsoft", "src_ex10_23", "Definitions: Customer", "", D, "", "'Customer' shall mean Microsoft Corporation; contract = Partner SOW #1 with Nscale US Holdings Inc.")],
    lender=[("le_jpmorgan_chase", "src_s1_full", DCI, "", D, "", "'among others, as arrangers and lenders'"), ("le_goldman_bank_usa", "src_s1_full", DCI)],
    arranger=[("le_jpmorgan_chase", "src_ex10_23", "Section 8.15"), ("le_goldman_bank_usa", "src_ex10_23", "Section 8.15"),
              ("le_ca_cib", "src_ex10_23", "Section 8.15 (MLA)"), ("le_deutsche_ny", "src_ex10_23", "Section 8.15 (MLA)"),
              ("le_mizuho", "src_ex10_23", "Section 8.15 (MLA)"), ("le_mufg", "src_ex10_23", "Section 8.15 (MLA)"),
              ("le_rbc", "src_ex10_23", "Section 8.15 (MLA)"), ("le_smbc", "src_ex10_23", "Section 8.15 (MLA)"),
              ("le_bbva_ny", "src_ex10_23", "Section 8.15 (MLA)"), ("le_ocbc_ny", "src_ex10_23", "Section 8.15 (MLA)")],
    guarantor=[("le_nscale_ward_county_llc", "src_s1_full", DCI), ("le_nscale_ltd", "src_s1_full", DCI, "", D, "", "Limited guarantee only.")],
    agent=[("le_us_bank_trust", "src_s1_full", DCI)],
    rating_moodys=("", "src_s1_full", DCI, "", "checked_absent", "", "S-1 says 'investment-grade ratings with a stable outlook' without naming agencies."),
    financial_covenants=("Historical debt service coverage ratio", "src_s1_full", DCI),
    purpose=("GPU servers and infrastructure at Ward County; repay specified vendor financing (Dell); fund collateral accounts", "src_s1_full", DCI),
    status=("signed_undrawn", "src_s1_full", DCI, "2026-08-27", "estimated", "", "Signed 27 Aug 2026; no drawn balance disclosed after signing."),
)
fac("fac_north_carolina",
    group=("group_nscale", "src_s1_full", IND),
    borrower=("le_nc_spv", "src_ex10_24", "Cover page", "2026-08"),
    facility_type=("delayed_draw_term_loan", "src_s1_full", DCI),
    amount_max=("1.2B", "src_s1_full", DCI, "2026-08-27", D, "USD", "$370M fixed-rate + $830M floating-rate commitments."),
    signing_date=("2026-08-27", "src_s1_full", DCI, "", D, "", "Ex-10.24 cover leaves the day blank ('August , 2026')."),
    margin_bps=("237.5", "src_s1_full", DCI, "", D, "bps", "Same pricing structure as Ward County."),
    maturity_date=("2031-12-27", "src_s1_full", DCI, "", D, "", "Earlier of the customer's final scheduled payment and 27 Dec 2031."),
    amortization=("Quarterly instalments", "src_s1_full", DCI),
    collateral=[("all_assets", "src_s1_full", DCI), ("shares", "src_s1_full", DCI)],
    named_customer=("", "src_ex10_24", "Definitions: Customer", "", "checked_absent", "", "'Customer' shall mean [***] (redacted). Contract is a Cloud Services Agreement with Nscale US Holdings Inc."),
    lender=[("le_goldman_bank_usa", "src_s1_full", DCI), ("le_jpmorgan_chase", "src_s1_full", DCI)],
    arranger=[("le_goldman_bank_usa", "src_ex10_24", "Lead arrangers section"), ("le_jpmorgan_chase", "src_ex10_24", "Lead arrangers section")],
    guarantor=[("le_nscale_services_us", "src_s1_full", DCI), ("le_nscale_ltd", "src_s1_full", DCI, "", D, "", "Limited guarantee only.")],
    agent=[("le_us_bank_trust", "src_s1_full", DCI)],
    financial_covenants=("Historical debt service coverage ratio", "src_s1_full", DCI),
    status=("signed_undrawn", "src_s1_full", DCI, "2026-08-27", "estimated", "", "No drawn balance disclosed after signing."),
)
fac("fac_parent_rcf",
    name=("Revolving Credit Facility", "src_s1_full", DCI),
    borrower=[("le_nscale_global_holdings", "src_s1_full", DCI, "2026-05-08", D, "", "Original borrower."),
              ("le_nscale_ltd", "src_s1_full", DCI, "2026-07", D, "", "Nscale Limited became successor borrower via a Borrower Assignment and Assumption Agreement in July 2026.")],
    amount_max=[("770M", "src_s1_full", DCI, "2026-05-08", D, "USD", "Initial commitment."),
                ("900M", "src_s1_full", DCI, "2026-06", D, "USD", "Upsized in June 2026 (amendments dated 17 and 30 June 2026).")],
    signing_date=("2026-05-08", "src_ex10_18", "Cover page"),
    base_rate=("Term SOFR", "src_s1_full", DCI),
    margin_bps=("175", "src_s1_full", DCI, "", D, "bps", "Or alternate base rate + 0.75%. Commitment fee 0.25% on undrawn."),
    maturity_date=("", "src_s1_full", DCI, "", "checked_absent", "", "Third anniversary of the effective date (not stated as a date), plus two 1-year lender extension options."),
    collateral=("all_assets", "src_s1_full", DCI, "", D, "", "First-priority security over substantially all personal property of borrower and guarantors."),
    lender=[("le_keybank", "src_ex10_18", "Signature pages"), ("le_mizuho", "src_ex10_18", "Signature pages"),
            ("le_mufg", "src_ex10_18", "Signature pages"), ("le_rbc", "src_ex10_18", "Signature pages"),
            ("le_smbc_bi", "src_ex10_18", "Signature pages"), ("le_td_ny", "src_ex10_18", "Signature pages"),
            ("le_ca_cib", "src_ex10_18", "Signature pages")],
    agent=[("le_jpmorgan_chase", "src_s1_full", DCI, "", D, "", "Administrative agent."), ("le_glas", "src_s1_full", DCI, "", D, "", "GLAS Americas collateral agent.")],
    accordion=("500M", "src_s1_full", DCI, "", D, "USD", "Plus unlimited amount subject to leverage ratios."),
    carrying_value=("0", "src_s1_full", "Interim note 8", "2026-06-30", D, "USD"),
    status=("signed_undrawn", "src_s1_full", "Interim note 8", "2026-06-30"),
)
fac("fac_norway_term_loan",
    name=("Kvandal South DC Term Loan Facility", "src_s1_full", DCI),
    borrower=("le_norway_dc_da", "src_s1_full", DCI, "2026-07-07"),
    amount_max=("725M", "src_s1_full", DCI, "2026-07-07", D, "USD", "Accordion up to a further $725M."),
    signing_date=("2026-07-07", "src_s1_full", DCI),
    base_rate=("Term SOFR", "src_s1_full", DCI),
    margin_bps=("300", "src_s1_full", DCI, "", D, "bps", "Ranges 3.00%-3.75% depending on period; commitment fee 35% of margin."),
    maturity_date=("2033-04-05", "src_s1_full", DCI, "", D, "", "Stated as six years from the target completion date of 5 April 2027; moves if completion slips."),
    amortization=("Quarterly from 30 June 2027", "src_s1_full", DCI),
    secured_on_site=("site_kvandal_south", "src_s1_full", DCI),
    collateral=("site", "src_s1_full", DCI, "", D, "", "Transaction security; parent company guarantee."),
    lender=[("le_abn_amro", "src_s1_full", DCI), ("le_dnb", "src_s1_full", DCI), ("le_nordea", "src_s1_full", DCI),
            ("le_efn", "src_s1_full", DCI), ("le_seb", "src_s1_full", DCI)],
    agent=[("le_dnb", "src_s1_full", DCI)],
    financial_covenants=("Historic DSCR >= 1.05x; historic net leverage not more than 30% above base case; equity cure rights", "src_s1_full", DCI),
    accordion=("725M", "src_s1_full", DCI, "", D, "USD"),
    named_customer=("", "src_s1_full", DCI, "", "checked_absent", "", "Customer not named in the S-1 description."),
)
fac("fac_norway_vat_rcf",
    name=("Kvandal South DC VAT Facility", "src_s1_full", DCI),
    borrower=("le_norway_dc_da", "src_s1_full", DCI, "2026-07-07"),
    signing_date=("2026-07-07", "src_s1_full", DCI),
    margin_bps=("200", "src_s1_full", DCI, "", D, "bps"),
    maturity_date=("2027-06-30", "src_s1_full", DCI, "", D, "", "Completion long-stop date; extendable up to 6 months for force majeure."),
    lender=[("le_abn_amro", "src_s1_full", DCI), ("le_dnb", "src_s1_full", DCI), ("le_nordea", "src_s1_full", DCI),
            ("le_efn", "src_s1_full", DCI), ("le_seb", "src_s1_full", DCI)],
    accordion=("65M", "src_s1_full", DCI, "", D, "USD"),
)
fac("fac_macquarie_iceland",
    group=("group_nscale", "src_s1_full", IND),
    name=("Macquarie Iceland Facility", "src_s1_full", DCI),
    borrower=("le_iceland_iii", "src_ex10_22", "Cover page", "2026-07-29"),
    facility_type=("delayed_draw_term_loan", "src_s1_full", IND),
    amount_max=("331.9M", "src_ex10_22", "Cover page", "2026-07-29", D, "USD", "$331,893,517."),
    signing_date=("2026-07-29", "src_ex10_22", "Cover page"),
    base_rate=("Term SOFR", "src_s1_full", DCI),
    margin_bps=("550", "src_s1_full", DCI, "", D, "bps"),
    maturity_date=("", "src_s1_full", DCI, "", "checked_absent", "", "46 months from first utilisation (date not disclosed)."),
    amortization=("Monthly from January 2027, plus payments so lenders reach a specified multiple (MOIC) of commitment", "src_s1_full", DCI),
    collateral=("gpus", "src_s1_full", DCI, "", "estimated", "", "Proceeds fund GPU purchases; S-1 says 'transaction security' without listing assets."),
    lender=[("le_macquarie", "src_s1_full", DCI)],
    agent=[("le_macquarie", "src_s1_full", DCI)],
    guarantor=[("le_nscale_ltd", "src_s1_full", DCI), ("le_services_intermediate_iii", "src_s1_full", DCI), ("le_services_uk_iii", "src_s1_full", DCI)],
    financial_covenants=("Financial covenant (not specified in summary)", "src_s1_full", DCI),
)
fac("fac_macquarie_glomfjord",
    group=("group_nscale", "src_s1_full", IND),
    name=("Macquarie Senior Facility", "src_s1_full", DCI),
    borrower=[("le_nscale_global_holdings", "src_s1_full", DCI, "2025-06", D, "", "S-1 summary names Nscale Global Holdings Limited."),
              ("le_drift_ii_holdings", "src_ex10_12", "Cover page", "2025-06", D, "", "Exhibit cover: 'for Nscale Drift II Holdings Ltd as Borrower' (A&R dated 22 Sept 2025 of SFA dated 12 June 2025).")],
    facility_type=("term_loan", "src_s1_full", DCI),
    amount_max=("105M", "src_s1_full", DCI, "2025-06", D, "USD", "Term loan + letter of credit facility."),
    signing_date=("2025-06-12", "src_ex10_12", "Cover page"),
    base_rate=("Monthly SOFR", "src_s1_full", DCI),
    margin_bps=("750", "src_s1_full", DCI, "", D, "bps"),
    amortization=("Monthly, linked to project cash flows, plus payments to reach a specified MOIC", "src_s1_full", DCI),
    effective_interest_rate=("22.74", "src_s1_full", "Interim note 8", "2026-06-30", D, "pct"),
    carrying_value=("89.2M", "src_s1_full", "Interim note 8", "2026-06-30", D, "USD"),
    status=("fully_drawn", "src_s1_full", DCI, "2026-01-30", D, "", "$70.1M drawn 1 Aug 2025; remaining $34.9M drawn 30 Jan 2026."),
    secured_on_site=("site_glomfjord", "src_s1_full", DCI, "", "estimated", "", "Funds a GPU cluster at Glomfjord; security package not read."),
    lender=[("le_macquarie", "src_ex10_12", "Cover page")],
    maturity_date=("", "src_s1_full", DCI, "", "checked_absent", "", "Matures on payment in full of the MOIC amount."),
)
fac("fac_dell_vendor",
    group=("group_nscale", "src_s1_full", IND),
    name=("DFS Framework Agreements", "src_s1_full", DCI),
    borrower=[("le_ward_county_spv", "src_s1_full", DCI), ("le_nc_spv", "src_s1_full", DCI)],
    facility_type=("vendor_financing", "src_s1_full", DCI),
    amount_max=("2.54B", "src_s1_full", DCI, "2026-09-04", D, "USD", "Aggregate initial-term rent across 40 payment schedules, incl. $34.8M financing charges."),
    signing_date=("2026-04", "src_s1_full", DCI),
    maturity_date=("", "src_s1_full", DCI, "", "checked_absent", "", "Schedules run 3-4 months from 1 Aug or 1 Sep 2026 (+1-2 month extension): roughly Nov 2026 - Feb 2027. To be repaid from the Ward County and NC facilities."),
    collateral=("gpus", "src_s1_full", DCI, "", D, "", "Security interest in the Products (computing and data center equipment) and proceeds."),
    lender=[("le_dfs", "src_s1_full", DCI)],
    guarantor=[("le_nscale_global_holdings", "src_s1_full", DCI, "", D, "", "Corporate guaranty dated 18 April 2026.")],
    status=("fully_drawn", "src_s1_full", DCI, "2026-09-04", "estimated", "", "40 of 40 payment schedules fully executed."),
)
fac("fac_convertible_2026",
    group=("group_nscale", "src_s1_full", IND),
    facility_type=("other", "src_s1_full", IND, "", D, "", "Unsecured convertible loan notes."),
    amount_max=("3.1B", "src_s1_full", IND, "2026-09-15", D, "USD", "Minimum: $2.1B notes + $1.0B to NVIDIA (notes or non-voting shares)."),
    signing_date=("2026-09-15", "src_s1_full", IND),
    collateral=("other", "src_s1_full", IND, "", D, "", "Unsecured."),
    lender=[("le_nvidia", "src_s1_full", IND, "", D, "", "$1.0B NVIDIA Sale, closing on or around 16 Nov 2026.")],
    purpose=("Convert automatically into ordinary shares on IPO completion", "src_s1_full", IND),
)
fac("fac_committed_2_35b",
    group=("group_nscale", "src_s1_full", DCI),
    facility_type=("delayed_draw_term_loan", "src_s1_full", DCI),
    amount_max=("2.35B", "src_s1_full", DCI, "2026-08", D, "USD", "'approximately $2.35 billion delayed-draw financing facilities' committed by banks."),
    status=("committed_undocumented", "src_s1_full", DCI, "2026-08", D, "", "Subject to definitive documentation and closing conditions."),
    lender=[("", "src_s1_full", DCI, "", "checked_absent", "", "'leading banks', not named.")],
)
fac("fac_sandton",
    group=("group_nscale", "src_s1_full", IND),
    facility_type=("term_loan", "src_s1_full", IND),
    amount_max=("76.6M", "src_s1_full", IND, "2025-05", D, "USD", "Four tranches Dec 2023 - May 2025."),
    coupon_pct=("13.0", "src_s1_full", IND, "", D, "pct", "13.0%-15.0%, initially PIK."),
    lender=[("le_sandton", "src_s1_full", IND)],
    status=("repaid", "src_s1_full", IND, "2025-10", D, "", "Repaid in full from Series B proceeds, October 2025."),
)
fac("fac_series_a_notes",
    group=("group_nscale", "src_s1_full", IND),
    facility_type=("other", "src_s1_full", IND, "", D, "", "Secured subordinated convertible notes."),
    amount_max=("160M", "src_s1_full", IND, "2024-11-18", D, "USD"),
    coupon_pct=("12.0", "src_s1_full", IND, "", D, "pct", "PIK initially."),
    status=("converted", "src_s1_full", "Notes to financial statements", "2025-10-08", D, "", "Fully converted into Series B preferred shares."),
)

# ---- sites ----
add("site_kvandal_south", "group", G, "src_s1_full", DCI)
add("site_kvandal_south", "name", "Kvandal South", "src_s1_full", DCI)
add("site_kvandal_south", "country", "Norway", "src_s1_full", "Related party: Aker joint venture")
add("site_kvandal_south", "operator", "le_norway_dc_da", "src_s1_full", DCI, method="estimated", note="Borrower of the site financing; assumed to own/operate the data centre.")
add("site_glomfjord", "group", G, "src_s1_full", "Cash flows: investing activities (p. 95)")
add("site_glomfjord", "country", "Norway", "src_s1_full", "Cash flows: investing activities (p. 95)")
add("site_monarch", "group", G, "src_s1_full", "Business: acquisitions (p. ~10)")
add("site_monarch", "name", "Monarch Compute Campus", "src_s1_full", "Business: acquisitions")
add("site_monarch", "country", "United States", "src_s1_full", "Business: acquisitions")
add("site_monarch", "location", "Mason County, West Virginia (~2,250 acres)", "src_s1_full", "Business: acquisitions")
add("site_monarch", "ownership", "owned", "src_s1_full", "Business: acquisitions", note="Acquired via AIPCorp, 31 March 2026.")
add("site_monarch", "acquisition_cost", "792.6M", "src_s1_full", "Interim notes: acquisitions", "2026-03-31", unit="USD", note="Net cash $99.6M + 36,778,740 Series C shares valued at $693.0M.")
add("site_monarch", "mw_energized", "0", "src_s1_full", "Interim notes: acquisitions", "2026-03-31", unit="MW", method="estimated", note="Described as a 'prospective data center site'; runway to 6.5 GW IT load.")
add("site_sin02", "group", G, "src_s1_full", "Business: acquisitions")
add("site_sin02", "name", "SIN02 (SINES Data Campus)", "src_s1_full", "Business: acquisitions")
add("site_sin02", "country", "Portugal", "src_s1_full", "Business: acquisitions")
add("site_sin02", "ownership", "owned", "src_s1_full", "Business: acquisitions")
add("site_sin02", "mw_contracted", "200", "src_s1_full", "Business: acquisitions", "2026-04-24", unit="MW")
add("site_sin02", "acquisition_cost", "548.1M", "src_s1_full", "Interim notes: acquisitions", "2026-04-24", unit="USD", note="EUR 469.3M at transaction date.")
add("site_sin02", "deferred_consideration_outstanding", "430.7M", "src_s1_full", "Interim notes: acquisitions", "2026-06-30", unit="USD", note="EUR 377.8M still owed to the seller; mostly due H2 2026.")
add("site_ward_county", "name", "Ward County, Texas", "src_s1_full", "Related party: NVIDIA")
add("site_ward_county", "ownership", "leased", "src_s1_full", "Related party: NVIDIA", note="Net lease.")
add("site_ward_county", "landlord", "le_ward_county_landlord", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)")
add("site_north_carolina", "operator", "le_nc_spv", "src_s1_full", DCI, method="estimated", note="Facility borrower; actual operator/landlord not read.")

# ---- lease ----
add("lease_ward_county", "group", G, "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)")
add("lease_ward_county", "site", "site_ward_county", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)")
add("lease_ward_county", "landlord", "le_ward_county_landlord", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)")
add("lease_ward_county", "lease_type", "Net lease", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)")
add("lease_ward_county", "guarantor", "le_nvidia", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)", "2025-10-14")
add("lease_ward_county", "guarantee_amount", "860.3M", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)", "2025-10-14", unit="USD")
add("lease_ward_county", "guarantee_term", "First five years of the lease", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)")
add("lease_ward_county", "escrow_amount", "470.0M", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)", unit="USD", note="Escrow held as recourse for NVIDIA; in restricted cash.")
add("lease_ward_county", "term_months", "", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)", method="checked_absent")
add("lease_ward_county", "tenant", "", "src_s1_full", "Note: Guarantee of Lease Agreement (p. F-26)", method="checked_absent", note="'the Company'; tenant entity not named.")

# ---- contracts ----
add("ctr_msft_sows", "group", G, "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_msft_sows", "customer", "le_microsoft", "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_msft_sows", "provider", G, "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_msft_sows", "value_total", "43.8B", "src_s1_full", "Customers and Business Model (p. 114)", "2026-04", unit="USD", note="'up to approximately $43.8 billion through December 2033', excl. optional extensions; subject to delivery and availability requirements.")
add("ctr_msft_sows", "start_date", "2025-09", "src_s1_full", "Customers and Business Model (p. 114)", note="SOWs signed Sept 2025 - April 2026.")
add("ctr_msft_sows", "end_date", "2033-12", "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_msft_sows", "take_or_pay", "true", "src_s1_full", "Customers and Business Model (p. 114)", method="estimated", note="S-1 says commercial arrangements are 'primarily' take-or-pay; not stated per SOW.")
add("ctr_msft_sows", "termination_rights", "For cause on 60 days' notice of breach, or insolvency/cessation of business of the other party", "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_msft_sows", "extension_rights", "Optional 6-month extension at Microsoft's election", "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_msft_sows", "term_months", "60", "src_s1_full", "Customers and Business Model (p. 114)", note="GPU service terms 5-6 years from acceptance of each tranche (lower bound shown).")
add("ctr_msft_sow1_ward", "group", G, "src_ex10_23", "Definitions: Customer Contract")
add("ctr_msft_sow1_ward", "customer", "le_microsoft", "src_ex10_23", "Definitions: Customer")
add("ctr_msft_sow1_ward", "provider", "le_nscale_us_holdings", "src_ex10_23", "Definitions: Customer Contract")
add("ctr_msft_sow1_ward", "site", "site_ward_county", "src_ex10_23", "Purpose of facility")
add("ctr_nc_customer", "group", G, "src_ex10_24", "Definitions: Customer Contract")
add("ctr_nc_customer", "customer", "", "src_ex10_24", "Definitions: Customer", method="checked_absent", note="Redacted [***].")
add("ctr_nc_customer", "provider", "le_nscale_us_holdings", "src_ex10_24", "Definitions: Customer Contract")
add("ctr_nc_customer", "site", "site_north_carolina", "src_ex10_24", "Purpose of facility")
add("ctr_anthropic", "group", G, "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_anthropic", "customer", "le_anthropic", "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_anthropic", "provider", "le_gpu_mcc_b11", "src_ex10_25", "Order form: Provider Name", note="One of four agreements, each with a different wholly owned subsidiary.")
add("ctr_anthropic", "site", "site_monarch", "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_anthropic", "value_total", "44.6B", "src_s1_full", "Customers and Business Model (p. 114)", "2026-08-25", unit="USD", note="'up to approximately $44.6 billion' across four agreements; subject to delivery and availability requirements.")
add("ctr_anthropic", "start_date", "2026-08-25", "src_s1_full", "Customers and Business Model (p. 114)", note="Effective date; service terms start on acceptance of each tranche.")
add("ctr_anthropic", "gpu_type", "NVIDIA Vera Rubin NVL72", "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_anthropic", "financing_status", "not_secured", "src_s1_full", "Customers and Business Model (p. 114)", "2026-09-18", note="'we have not obtained binding commitments for any of the financings required'; best-efforts obligation to obtain qualifying financing within a specified period.")
add("ctr_anthropic", "termination_rights", "Anthropic may terminate a tranche if not delivered within a specified period after expected delivery, if excused supply delays exceed a threshold, or if monthly uptime falls below thresholds; for cause on uncured material breach, insolvency, or change of control to a disqualified person", "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_anthropic", "extension_rights", "Extension options at Anthropic's election", "src_s1_full", "Customers and Business Model (p. 114)")
add("ctr_figure", "group", G, "src_s1_full", "Customers and Business Model (p. 115)")
add("ctr_figure", "customer", "le_figure", "src_s1_full", "Customers and Business Model (p. 115)")
add("ctr_figure", "start_date", "2026-08-24", "src_s1_full", "Customers and Business Model (p. 115)")
add("ctr_figure", "gpu_count", "100000", "src_s1_full", "Customers and Business Model (p. 115)", unit="GPUs", note="'potential to deploy up to 100,000' Vera Rubin GPUs from H2 2027. Nscale is also investing in Figure.")
add("ctr_figure", "value_total", "", "src_s1_full", "Customers and Business Model (p. 115)", method="checked_absent")
add("ctr_nvidia_msa", "group", G, "src_s1_full", "Related party: NVIDIA (p. 144)")
add("ctr_nvidia_msa", "customer", "le_nvidia", "src_s1_full", "Related party: NVIDIA (p. 144)")
add("ctr_nvidia_msa", "value_total", "1.2B", "src_s1_full", "Related party: NVIDIA (p. 144)", "2025-07", unit="USD", note="Reserved GPU capacity in Iceland, UK and Norway; terms 12-48 months.")
add("ctr_nvidia_msa", "start_date", "2025-07", "src_s1_full", "Related party: NVIDIA (p. 144)")

# ---- subsidiaries from Ex-21.1 (for registry monitoring) ----
known = {v[0].lower().replace(",", "").replace(".", ""): k for k, v in ent_names.items()}
sub_rows = []
for i, s in enumerate(SUBS, 1):
    key = s["name"].lower().replace(",", "").replace(".", "")
    if key in known:
        continue
    eid = f"le_sub_{i:03d}"
    sub_rows.append((eid, "legal_entity", s["name"], "From Ex-21.1"))
    add(eid, "name", s["name"], "src_ex21", f"Ex-21.1 row {i}")
    add(eid, "jurisdiction", s["jurisdiction"], "src_ex21", f"Ex-21.1 row {i}")
    add(eid, "group", G, "src_ex21", f"Ex-21.1 row {i}")

# ---- write ----
def append(path, fieldnames, items):
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        for it in items:
            w.writerow(it)

append(REPO / "data/sources.csv", ["id", "type", "access", "publisher", "title", "url", "published_date", "retrieved_date", "note"],
       [dict(id=i, type="filing", access="full_document", publisher="NSCALE Ltd (SEC EDGAR)", title=t, url=S1 + f,
             published_date="2026-09-18", retrieved_date=OBS, note="") for i, t, f in sources])
append(REPO / "data/entities.csv", ["id", "type", "label", "note"],
       [dict(id=a, type=b, label=c, note=d) for a, b, c, d in entities + sub_rows])
append(REPO / "data/entity_links.csv", ["entity_a", "relation", "entity_b", "judged_by", "judged_date", "note"],
       [dict(entity_a=a, relation=r, entity_b=b, judged_by="claude (pending analyst review)", judged_date=OBS, note=n) for a, r, b, n in links])
start = 1000
fields = ["id", "entity", "property", "value", "unit", "source", "locator", "effective_date", "observed_date",
          "method", "derived_from", "extractor", "note"]
append(REPO / "data/statements.csv", fields, [dict(id=f"st{start + n:04d}", **r) for n, r in enumerate(rows)])
print(f"{len(rows)} statements, {len(entities) + len(sub_rows)} entities, {len(sources)} sources, {len(links)} links")
