# How the tracker works

The code runs the rules; the rules and the knowledge behind them live in data files you can read and edit. Nothing is
decided inside the code that is not written down in one of the files below or in `docs/decisions.md`.

## 1. What lives where

| File | What it holds | Who changes it |
|---|---|---|
| `data/statements.csv`, `sources.csv`, `entities.csv`, `entity_links.csv`, `reviews.csv` | The facts, their sources, and analyst judgements | Analyst (via one-off scripts or by hand) |
| `schema/vocabulary.yaml` | What a fact may say: entity types, properties, units, source ranking, grades | Analyst, rarely |
| `data/quotes.csv` | Exact words behind a statement, checked against the archived document | Analyst |
| `data/archive/**/manifest.json` | URL, SHA-256 hash, size and time of every downloaded document | Written by `fetch_edgar.py` |
| `data/source_directory.yaml` | Every source by jurisdiction: access, cost, machine access, whether automation is allowed | Analyst |
| `data/document_types.yaml` | Which document answers which credit question, how each register labels it, Exhibit 10 title and text rules, sector presets | Analyst |
| `data/disclosure_map.yaml` | Which kinds of debt leave public traces, where, when and why, with citations; signals before, at and after closing | Analyst |
| `data/watchlist.yaml` | Names the daily monitor searches for | Analyst |
| `data/events.csv` | Everything the monitor has seen (append-only) | Written by the monitor |

Code (`tracker/`): `model.py` loads, validates and resolves facts; `net.py` makes every web request; `monitor.py`
runs the daily feeds; `jurisdictions.py` searches registers by country; `documents.py` sorts documents by question;
`disclosure.py` queries the disclosure map; `archive.py` checks hashes and quotes; `__main__.py` is the command line.

## 2. Rules that apply everywhere

**Web requests (`tracker/net.py`).**
- Every request identifies itself with `EDGAR_USER_AGENT` ("Name email"). SEC calls refuse to run without an email.
- Per-site minimum gaps: SEC 0.12 s (limit 10/s), Companies House 0.5 s (limit 600 per 5 minutes), French register
  0.2 s (7/s), GLEIF 1 s, anything else 1 s.
- Retries: up to 4 tries on rate-limit and server errors (429, 500, 502, 503, 504) and network errors, waiting
  2, 4, 8 s or the site's `Retry-After`. A 404 means "nothing there", not an error.
- Every paged API is read to the end (EDGAR pages of 100, Companies House pages of 100), with a safety stop of 50 pages.

**Failure isolation.** Each feed, register adapter and data source runs on its own. If one fails, the others still
run and the failure is printed (and put in the daily GitHub issue) as "not searched: <source>: <reason>".

**Where automation is not allowed** (German Handelsregister: 60 views an hour; session-based sites such as LBR and
LuxSE; CAPTCHA sites), the tool prints a link for a person to open. It never scrapes them. See `automation` in the
source directory.

**No personal data.** People are never stored. From Companies House it reads corporate PSCs only; from the French
register, corporate officers only.

**No AI calls in the code.** Classification uses fixed rules from the data files. AI is used by the analyst to read
documents; anything it extracts must pass the validator and, where archived, the quote check.

**Search results are leads, not facts.** Nothing from `search`, `company`, `sector` or the monitor becomes a
statement until someone reads the document and records it in `statements.csv`.

## 3. Commands

### `python -m tracker check`
Reads all data files. Fails (and lists every problem) if: a statement breaks the vocabulary; an archived file's hash
has changed; a quote in `quotes.csv` is not in its file (spacing and curly quotes ignored, nothing else); a source,
document type, signal or trace refers to something that does not exist; a citation is missing. Calls no website.

### `python -m tracker report <group>` and `build`
Builds the credit file and SQLite copy from statements using the resolution rules in `model.py`: latest effective
date wins, then stronger source (vocabulary ranking), then method; disagreements are shown, never hidden (decisions
D5, D6, D13). Calls no website.

### `python -m tracker monitor [edgar|ch|news]`
Daily via GitHub Actions. For each group in `watchlist.yaml`:
- **edgar**: SEC full-text search for each term, last 45 days, all pages; one event per filing.
- **ch**: for every UK entity of the group with a registry number: full filing history and all charges.
- **news**: Google News RSS for each term.

New events (ids never seen) are appended to `events.csv`. On a feed's first run, items older than 21 days are marked
`baseline`; form types in `ignore_kinds` (fund registration noise) are `ignored`. The issue lists new events tagged
with the question each answers (from `document_types.yaml`) and any feed that failed.

### `python -m tracker search <jurisdiction> "<name>"`
Runs every live adapter for that country (listed in `source_directory.yaml` under `adapter`), plus GLEIF filtered
to the country, then prints one-click links for every other source. Adapters and what they call:

| Adapter | Calls | Key |
|---|---|---|
| `uk_ch` | Companies House `/search/companies` | `COMPANIES_HOUSE_API_KEY` |
| `uk_gazette` | The Gazette insolvency notice feed | none |
| `uk_caselaw` | Find Case Law Atom search (relevance order) | none |
| `ie_cro` | CRO open data (CKAN datastore) | none |
| `fr_entreprises` | API Recherche d'entreprises | none |
| `fr_bodacc` | BODACC open data (untested: blocked from the build sandbox) | none |
| `nl_kvk` | KVK search API (untested) | `KVK_API_KEY` (paid) |
| `no_brreg` | Brønnøysund Enhetsregisteret | none |
| `fi_prh` | PRH YTJ open data | none |
| `eu_gleif` | GLEIF LEI records (full-text, country filter) | none |
| `eu_esef` | filings.xbrl.org entities | none |
| `us_edgar` | SEC full-text search, all pages, minus `ignore_kinds` | `EDGAR_USER_AGENT` |

### `python -m tracker company <jurisdiction> <registry no | CIK | LEI>`
Gathers one company's documents and sorts each into the questions in `document_types.yaml` (org chart, guarantors,
debt documents, security, financials, restructuring, lenders, contracts):
1. Country pull (if a registry number or CIK is given):
   - **UK**: full filing history (each filing classified by its Companies House type code; links go to the PDF),
     all charges (terms, chargee, link to the MR01 instrument), corporate PSCs, insolvency cases.
   - **US**: every recent filing from `data.sec.gov` (classified by form and 8-K item), then the index pages of the
     filings most likely to hold debt documents (latest 10-K, latest registration statement, latest 10-Q, three latest
     424Bs, five latest 8-Ks with items 1.01 or 2.03). Exhibits are classified by type; each Exhibit 10 is sorted by its
     title (first 20 KB), and where the title says nothing about debt, by strict phrases in its opening text
     (`title_rules`, `body_rules`).
   - **Norway**: register flags and every year of filed accounts (group and company), with total, long- and
     short-term debt. **France**: accounts summaries and corporate officers. **Finland**: company situations.
     **Ireland**: CRO status.
2. GLEIF: the LEI (given, or found from the registry number), direct and ultimate parent (or the stated reason none
   is reported), up to 500 direct subsidiaries, the count of all subsidiaries with LEIs; ESEF annual reports.
3. Under each question, the documents to read by hand in that jurisdiction (plus pan-EU and paid ones), with what to
   look for.

### `python -m tracker sector <preset> [--jur us,no,uk]`
Presets live in `document_types.yaml` (`sectors`). Each combines industry codes, name keywords and known groups,
because industry codes miss many companies (data-centre property SPVs are often coded as real estate; NACE Rev. 2.1
moved hosting from 63.11 to 63.10).
- **us**: SEC full-text search for each sector term with each debt phrase, up to 3 pages each; keeps credit
  agreements, indentures, guarantor lists and 8-Ks reporting new debt; an Exhibit 10 counts only if its title or
  opening text is a debt document.
- **no**: companies by known group, then keyword, then industry code (at least 10 staff); ranked by total debt in
  the latest filed accounts (group accounts where filed).
- **uk**: companies by known group, keyword, then SIC code; outstanding charges for each; chargees ranked by how
  many sector companies they hold security over. Each borrower shows how it was matched and its SIC codes, because a
  name match can be an unrelated company.

### `python -m tracker documents | sources | where | signals | refs`
Print the data files, filtered: document types by jurisdiction and question; sources by jurisdiction, channel and
cost; the disclosure map by instrument and region; signals by stage and region; citations.

### Scripts
`scripts/fetch_edgar.py` downloads a filing and all exhibits, records hashes, writes text and flattened text.
`scripts/build_source_directory.py` builds the shareable page and CSV from the three data files.
`scripts/build_contract_writeup.py` fails if any quote anchor is missing from the archived exhibit.

## 4. Deciding where to look

1. **What kind of debt is it, and where is the borrower?** `python -m tracker where <instrument> --region <country>`
   says what must be public, when, and the legal basis. If the answer is "none", go straight to paid services.
2. **Has it happened yet?** `python -m tracker signals --stage pre` lists early signs (new SPVs, parent links, LEIs,
   articles changes, bond mandates) and where to watch.
3. **One company:** `company`. **A whole sector:** `sector`. **Not sure of the company number:** `search`.
4. **Confirm before recording:** match a reported deal to a hard trace (a charge within about 30 days naming the same
   agent, a BDC position, an ISIN, a filed exhibit). Record it with the source that proves it.

## 5. Keys and settings

| Variable | Used by | Notes |
|---|---|---|
| `EDGAR_USER_AGENT` | All SEC calls | "Name email"; SEC requires a contact |
| `COMPANIES_HOUSE_API_KEY` | UK search, company, sector, monitor | Free key; or the file `~/.config/ai-infrastructure/companies_house_api_key`. Never commit it |
| `KVK_API_KEY` | Dutch register search | Paid |
