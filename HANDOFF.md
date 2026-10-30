# Handoff: European neocloud credit tracker (built on Nscale)

Compressed record of the build session (29 Oct 2026), so the tool can be replicated and extended in a new chat.
Owner: Christina W. Lai. Code: **https://github.com/cwlai19/AI-Infrastructure**, branch `statement-model`
(the repo is **public**; make it private before adding any paid-terminal data).

---

## 1. Goal and constraints (as agreed)

- **Goal:** a live tracker of European neoclouds' contracts: customers (offtake), upstream lessors and lenders, with a
  credit-risk view. Started with Nscale; extend to other European neoclouds and to a Europe-wide map of who lends to whom.
- **Design choices agreed:**
  - (G) Every fact is a sourced *statement*.
  - (B) Keep a document archive.
  - (C) Monitor events daily.
  - (F) Write credit files together.
  - (E) No paid data layer in the tool itself. Paid sources stay outside the public repo: LoanConnector, 9fin,
    Octus and Bloomberg (the user has access to all four).
- **Explanations:** first principles, with the case against each alternative (see `docs/decisions.md`, D1–D13).
- **Outputs for colleagues:**
  - No GitHub or back-end shown to them.
  - Emails to colleagues are drafts for the user to send.
  - Every output carries the watermark "Created by Christina W. Lai · as of <date> · Prepared with AI assistance",
    plus a no-liability disclaimer (`tracker/disclaimer.py`).
- **Display rules (latest):**
  - Dark theme, mobile-friendly, compact enough to read on one page.
  - No analyst commentary on outputs; the construction-risk ranking is the only judgement, and it is labelled as such.
  - Default source filter is "filings & company only" (grades A/B); news (C) is shown via a toggle.
  - Key stats are shown as value (% of base).
  - No power-cost modelling (dropped by the user as too assumption-heavy).

## 2. Architecture (how the tool works)

```
fetch (EDGAR, Companies House, news RSS) ──► archive text ──► read & extract ──► statements.csv
                                                                        │
                       vocabulary.yaml (what may be said) ──► validator ┘
                                                                        ▼
                         resolve() rules: latest date wins, then source strength; conflicts flagged, history kept
                                                                        ▼
         builds: credit file (md) · site map (HTML artifact) · contract write-up (HTML) · Excel/CSV export · SQLite
                                                                        ▲
                 monitor (daily GitHub Action): new EDGAR / Companies House / news events ──► events.csv
```

**Statement model.** Each row of `data/statements.csv` is one claim, with these fields:

| Field | Meaning |
|---|---|
| `entity`, `property`, `value`, `unit` | The claim itself |
| `source` | The document it came from |
| `locator` | Where in the document |
| `effective_date`, `observed_date` | When the fact was true; when we recorded it |
| `method` | `disclosed` / `derived` / `estimated` / `reported` / `checked_absent` |
| `derived_from`, `extractor`, `note` | Inputs to a derived value; who/what extracted it; free note |

**Grades** come from the source type:

| Grade | Source types |
|---|---|
| A | Filing, registry, counterparty filing, rating agency |
| B | Company release, aggregator such as CCIR (also an A-grade document seen only as an excerpt) |
| C | News, analyst, internal; estimated values are always C |

Derived values take the grade of their weakest input.

**Resolution.**
- Latest effective date wins, then source strength.
- Undated values cannot supersede dated ones.
- Wording variants and partial dates count as agreement.
- Real disagreements are flagged; earlier values become history.

**Analyst overrides.**
- `data/reviews.csv` holds verdicts on single statements: rejected or explained.
- `data/entity_links.csv` holds `same_as` / `part_of` links between entities.

## 3. Repository map

| Path | Purpose |
|---|---|
| `schema/vocabulary.yaml` | Entity types, properties, units, source ranking. Extend here first. |
| `data/statements.csv` · `sources.csv` · `entities.csv` · `entity_links.csv` · `reviews.csv` | The database (CSV master copy) |
| `data/events.csv`, `data/watchlist.yaml` | Monitor log and search terms |
| `data/site_overlay.yaml` | Map-only inputs: coordinates, region, risk ranking, facility-to-site mapping, customer headline contract |
| `data/contract_writeup.yaml` | Condensed contract points, each with start/end anchors for verbatim quotes |
| `data/archive/` | Archived exhibit text (Anthropic Ex-10.25, Microsoft SOW Ex-10.19); each folder has a `manifest.json` with SHA-256 hashes |
| `data/quotes.csv` | Verbatim quotes behind statements, checked against the archive by `check` |
| `data/source_directory.yaml` | 108 free and paid sources by jurisdiction; feeds `search`, `sources` and the directory page |
| `tracker/model.py` | Load, validate, resolve |
| `tracker/report.py` | Credit file |
| `tracker/monitor.py` | EDGAR / Companies House / news feeds (all pages; a failing feed is reported, not fatal) |
| `tracker/net.py` | Polite HTTP: per-host rate limits, retries with Retry-After, honest User-Agent |
| `tracker/archive.py` | Archive manifest (hashes) and verbatim-quote checks |
| `tracker/jurisdictions.py` | Live registry adapters by jurisdiction and the `search` / `sources` commands |
| `tracker/disclosure.py` + `data/disclosure_map.yaml` | Where each kind of debt leaves a public trace, signals, citations (`where`, `signals`, `refs`) |
| `docs/HOW_IT_WORKS.md`, `docs/related_tools.md` | What every command does; open-source tools surveyed |
| `tracker/lenders.py` | BDC holdings by name or sector, confirmed in each filing and reconciled (`lenders`) |
| `tracker/watch.py` | Pre-financing signals and likely financings (`watch`, `stream`; monitor feed `signal`) |
| `tracker/documents.py` | Document classification by credit question; `company`, `sector` and `documents` commands |
| `data/document_types.yaml` | Document types per jurisdiction, how to recognise them (CH filing codes, EDGAR form/exhibit types, 8-K items), Exhibit 10 title rules, sector presets |
| `tracker/disclaimer.py` | Watermark text |
| `tracker/__main__.py` | CLI: `check` / `build` / `report` / `monitor` / `search` / `sources` |
| `scripts/build_source_directory.py` | Source directory page (artifact `claude.ai/artifact/MzG1cGgaNfnTSqN7PQtYsf`) and CSV |
| `scripts/fetch_edgar.py` | **Download any EDGAR filing and all exhibits, as HTML, text and flattened text** |
| `scripts/clause_defs.py` | Print defined terms from a flattened agreement (fast reading of credit agreements) |
| `scripts/html2text.py` | EDGAR HTML to text |
| `scripts/oneoff/*.py` | The extraction passes used for Nscale. Pattern to copy: one script per reading pass, appending statements. |
| `scripts/build_site_map.py` + `reports/site_map_template.html` | Interactive map: one data object injected into the template; geo from `vendor/geo` |
| `scripts/build_contract_writeup.py` | Contract write-up; the build fails if any quote anchor is missing |
| `scripts/export_xlsx.py` (`--compact`) + `scripts/xlsx_compact.py` | Excel export, plus a small email-size copy |
| `tools/*.js` | Playwright screenshot and PDF helpers for checking outputs |
| `.github/workflows/monitor.yml` | Daily monitor (needs the `COMPANIES_HOUSE_API_KEY` secret and the `EDGAR_USER_AGENT` variable) |
| `tests/` | 78 tests on the model, monitor, fetching, archive, quotes, directory, documents, disclosure map, lenders and watch |
| `docs/decisions.md` | Design decisions D1–D13 with reasoning |

## 4. Run it

```bash
pip install pyyaml openpyxl xlsxwriter        # Python 3.11+
python -m tracker check                        # validate
python -m unittest discover -s tests -t .      # tests
python -m tracker report group_nscale          # credit file (markdown)
python scripts/build_site_map.py               # reports/site_map.html (artifact) + reports/Nscale_Site_Map.html (standalone)
python scripts/build_contract_writeup.py       # reports/contract_writeup.html + Nscale_Contract_Writeup.html
python scripts/export_xlsx.py reports/Nscale_tracker_data.xlsx
EDGAR_USER_AGENT="Name email" python scripts/fetch_edgar.py 2110365 0001193125-26-395475
COMPANIES_HOUSE_API_KEY=... python -m tracker monitor     # never commit the key
python -m tracker search uk,lu,ie "Nscale"     # live registry search by jurisdiction
python -m tracker sources de                   # every source for Germany, free and paid
python -m tracker company us 2110365           # Nscale's SEC documents sorted by question
python -m tracker sector data_centres --jur us,no,uk
python scripts/build_source_directory.py       # reports/source_directory.html + .csv
```

## 5. What was built for Nscale (state at handoff)

- **Data:** 1,411 statements, 265 entities, 75 sources. They cover:
  - the full S-1 and its exhibits: 7 credit agreements, the Anthropic and Microsoft contracts, and Ex-21 (138 subsidiaries);
  - UK Companies House charges, including the NSCALE PLC re-registration;
  - counterparty SEC filings: Ionic and KiNRG (Ward County landlord and supplier), WhiteFiber (NC-1), Blue Owl BDCs,
    PIMCO and Fidelity holdings;
  - CCIR, cross-checked against the filings;
  - news from October 2026: Microsoft's Loughton termination, Anthropic's second ~$45B deal in talks, site risks.
- **Site map** (artifact `claude.ai/artifact/F2g9XtvXgdeUaMarcTZVpC`):
  - **Layout:** key stats (value, % of base) that follow region and campus selection; collapsible group strips for
    customers and group-level debt; one US + Europe map with multi-select totals.
  - **Campus panel**, in six sections: Customer, Data centre provider, Build status, Debt, Cost structure,
    Termination and force majeure.
  - **Tabs:** Customers · Lessors & upstream obligations · Construction risk terms.
- **Contract write-up** (artifact `claude.ai/artifact/67s9PZ2s4onc6sc9JbhwLP`): key points, then each contract by
  section, with 49 verbatim clause quotes. Prints to about 3 pages. *Pending:* switch it to dark theme and the corner
  watermark.
- **Earlier outputs** (now superseded): credit snapshot PDF/HTML memo, credit file markdown, Excel/CSV exports, emails.

**Key findings worth carrying forward (all sourced in the data):**
- Neither big customer pays before acceptance; lateness brings credits or discounts, then the right to cancel a tranche
  (Microsoft: 60 days late, with the upfront payment refunded).
- Anthropic's contract (Monarch, $44.6B) is conditional on Nscale securing financing by a redacted longstop date.
- Customer termination is a loan default at Ward County and North Carolina. The UK GPU loan allows 90 days to replace a
  contract, Iceland 60 days, Glomfjord two months. Kvandal South traps cash, then defaults after one year.
- Hard dates:
  - Borealis: service must start by 27 Jan 2027.
  - Kvandal South: target completion 5 Apr 2027; default if not complete by 5 Apr 2028.
  - Glomfjord: service-start test of 30 Nov 2025 (whether met or waived is not filed).
- **Group links:**
  - The $900M group revolver cross-defaults on other debt over $50M; this appears to include campus borrowers.
  - The Iceland and Glomfjord loans cross-default on parent-level debt.
  - US campus loans have no claim on European assets.
- **Corrections made:**
  - Microsoft is *not* take-or-pay before delivery.
  - Kvandal North is a separate Microsoft campus (Ex-10.19).
  - The $500M power-contract guarantee and $2.5B escrow belong to Anthropic's S-1, not Nscale's.

## 6. Replicate for another company: checklist

1. **Find the filings.**
   - EDGAR: search the company and its counterparties, using full-text search for the name in exhibits.
   - Then run `scripts/fetch_edgar.py <CIK> <accession>`.
   - Non-US companies: national registry accounts and charges (section 7).
2. **Create the core entities** in `data/entities.csv`: the group, legal entities (from the subsidiary list), sites,
   facilities, contracts, leases. Register each document in `sources.csv`.
3. **Extract in passes, one `scripts/oneoff/add_<pass>.py` each.** Order:
   1. debt;
   2. customers and contracts;
   3. sites;
   4. leases and landlords;
   5. lender holdings (BDC and N-PORT);
   6. registry charges;
   7. news.

   Put a clause reference in `locator` for every value. Use `checked_absent` when you read a document and it is silent.
4. `python -m tracker check` → fix the validator's flags. Add `reviews.csv` verdicts for misreadings.
5. **Map:** fill `data/site_overlay.yaml` for the new group (coordinates, region, facilities per site, headline
   contract per customer). Point `GROUP` in `build_site_map.py` at the new group id; it is hard-coded for Nscale
   today, so make it a CLI argument for multi-company use.
6. **Contract write-up:** add the company's filed contracts to `data/contract_writeup.yaml`, with anchors copied
   from the `.flat.txt`.
7. **Monitor:** add names to `data/watchlist.yaml` and the UK company numbers. The daily Action logs new filings.

**To generalise for many companies (suggested next refactor):**
- Parameterise the group in all builds.
- Make the overlay a per-group file.
- Add a group selector to the map.
- Move `site_overlay` judgement fields (risk ranking) into `reviews`-style analyst files.

## 7. Expansion: Europe-wide debt map (who lends to whom, on what terms, against which asset)

**Data sources, by role:**
- **Security registers (lender + asset):**
  - UK Companies House charges (free API; the MR01 filing often includes the full instrument).
  - HM Land Registry company-ownership lists (free) and title registers (£3 each).
  - Ireland CRO charges.
  - Norway: Løsøreregisteret (pledge register) and the land register.
  - Denmark: tinglysning.dk.
  - Sweden and Finland: business mortgage registers.
  - France: the security-interest register via Infogreffe.
  - Iceland, Portugal, Spain: land registers.
  - Germany and the Netherlands have no public pledge register; use filed accounts instead.
- **Lender disclosures (terms):**
  - US BDC schedules of investments (Blue Owl, Ares, Blackstone, HPS, Golub, Oaktree, Sixth Street, FS KKR, MS Direct
    Lending).
  - SEC N-PORT fund holdings.
  - European listed credit and infrastructure funds' reports, e.g. SEQI.
  - Luxembourg/EU fund annual reports.
- **Public lenders and capital markets:**
  - EIB, EBRD and NIB project lists.
  - Export credit agencies: Eksfin, UKEF, EKN/SEK, Finnvera, EIFO, Bpifrance, Euler Hermes.
  - EU state aid register and UK subsidy database.
  - FCA National Storage Mechanism, ESMA prospectuses, Euronext Dublin and LuxSE.
  - Rating agency releases.
  - EDGAR full-text search.
- **Ownership and location:**
  - GLEIF LEI with parent links; UK PSC data; OpenCorporates; EU business-register search.
  - Planning portals, permits, grid connection lists; datacentermap and Baxtel.
- **Paid, kept outside the public repo:** Bloomberg, LoanConnector, 9fin, Octus, IJGlobal/Inframation.

**Pilot proposed (not started):**
1. List ~40 European data-centre and neocloud groups (Nscale, Nebius, Fluidstack, Northern Data, atNorth,
   Green Mountain, Bulk, Start Campus, Kao, Ark, Pure DC, Yondr, Verda, Evroc, …).
2. Pull their subsidiaries from GLEIF.
3. Scrape Companies House charges for all UK subsidiaries.
4. Match the names against BDC and N-PORT holdings, EDGAR and the EIB/export-credit-agency lists.
5. Load everything as statements: facility → lender, borrower, secured site (with coordinates), owner.
6. Build a "capital map" of concentration by asset, owner and lender.

**Built (29 Oct 2026, second session):** `python -m tracker search <jurisdiction> "<name>"` with live adapters for
Companies House, The Gazette, Find Case Law, CRO open data, Annuaire des Entreprises, BODACC (untested: blocked from the
build sandbox), KVK (needs a paid key; untested), Brønnøysund, PRH, GLEIF (every country), ESEF filings and EDGAR; the
directory of 108 sources (`data/source_directory.yaml`, page and CSV). Next adapters worth adding: Companies House
Document API (MR01 PDFs), Rechtspraak open data (WHOA), BORME, ESMA FIRDS (bonds by LEI), Nordic Trustee notices.

## 8. Open items

- Contract write-up: dark theme and corner watermark.
- Load the October 2026 site-risk news fully into the memo; the second follow-up email draft was never sent.
- Analyst review of the construction-risk rankings (the only judgement left on the map).
- Make the GitHub repo private before any Bloomberg or paid data goes in.
- GitHub Actions secrets for the monitor.
- Investor question list (delivery dates, Monarch financing longstop, backlog by site, prepayment refund exposure,
  funding plan, Dell takeout, guarantees, cross-default, Loughton/SOW #3, landlords, live MW, GPU allocations, Asia),
  plus forecast-assumption questions (ramp, GPUs per MW, price per GPU-hour, re-contracting, opex per MW, capex per MW,
  GPU useful life and residual value, financing assumptions, downside cases). See the chat summary in `NEW_CHAT_PROMPT.md`.
