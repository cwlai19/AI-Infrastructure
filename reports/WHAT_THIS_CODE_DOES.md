# What this code does (plain English)

## Purpose
A credit-risk tracker for European neoclouds, starting with Nscale: who it owes (lenders),
who pays it (customers / offtakers), who it rents from (landlords), and where those
relationships could break. Every number is traceable to a public source document.

## The core idea: every fact is a "statement"
One row = one claim from one source: *entity · property = value · source · where in the source ·
date it was true · date we recorded it · how we got it (disclosed / derived / estimated / reported)*.
Nothing is overwritten. When sources disagree, both stay on file and the disagreement is shown.
What readers see (the debt ledger, the credit file, the memo) is computed from the statements
by fixed, tested rules: latest date wins, then the strongest source (filing > registry >
lender filing > company press > aggregator > news). See `docs/decisions.md` for why.

## What it did for Nscale (29 Oct 2026)
1. **Read the S-1 and its exhibits** (SEC EDGAR): debt agreements, customer contracts, the list of 138 subsidiaries.
2. **Checked the UK registry** (Companies House API): registration numbers for 32 UK entities, and every
   registered charge (security held by lenders). This settled a contradiction inside the S-1 and showed the
   company re-registered as NSCALE PLC on 9 Oct 2026, after the S-1.
3. **Read lenders' and counterparties' own filings**: Blue Owl fund 10-Qs and PIMCO / Fidelity N-PORTs
   (holdings, marks), and the 10-Qs of Ionic Digital (Ward County landlord), WhiteFiber (NC colocation)
   and KiNRG (supplier). Found the landlord the S-1 doesn't name.
4. **Cross-checked against CCIR** (ccir.io): its claims were verified in the filings where possible; the rest are graded B.
5. **Logged reviews**: where an earlier reading was wrong, the statement was kept but marked rejected, with a reason.
6. **Built a monitor**: daily search of SEC full text and Companies House for anything new about Nscale
   (it found Anthropic's S-1 on its first run). New items go to `data/events.csv` for triage.

## Files
| File | What it is |
|---|---|
| `reports/Nscale_tracker_data.xlsx` | **Everything in one workbook**: all 1,265 statements with source titles and links, the resolved debt ledger, sources, entities, links, reviews, monitor events |
| `reports/Nscale_Credit_Snapshot_2026-10-29.pdf` / `.html` | 4-page senior-readable memo |
| `reports/nscale_credit_file.md` | Full generated credit file (ledger, conflicts, history, gaps) |
| `data/*.csv` | The master data (statements, sources, entities, entity_links, reviews, events) |
| `schema/vocabulary.yaml` | What a statement is allowed to say |
| `tracker/` | Validator, resolution rules, report and monitor code; `tests/` has 32 tests |
| `.github/workflows/monitor.yml` | Daily monitor (needs a COMPANIES_HOUSE_API_KEY secret and an EDGAR_USER_AGENT variable) |

## Commands
```
python -m tracker check                 # validate all data
python -m tracker report group_nscale   # regenerate the credit file
python -m tracker monitor               # log new SEC / Companies House filings
python scripts/export_xlsx.py           # regenerate the Excel workbook
```

## Caveats
Extraction was AI-assisted and is marked "pending analyst review". Figures tagged "per CCIR"
were not independently verified. Public-source research, not investment advice.
