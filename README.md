# AI-Infrastructure

A credit-risk tracker for European neoclouds: their debt, their offtake customers and their
landlords. Every number is traceable to a source.

## How it works (one paragraph)

Every fact is stored as a **statement**: one claim, from one source, with dates and how it was
obtained (`data/statements.csv`). Statements are never overwritten. The tracker computes what
readers see (a debt ledger, conflicts, history, gaps) from the statements using fixed rules.
See [`docs/decisions.md`](docs/decisions.md) for why it is built this way and what we rejected.

## Files

| Path | What it is |
|---|---|
| `schema/vocabulary.yaml` | What a statement may say: entity types, properties, units, source ranking |
| `data/sources.csv` | One row per document we used (with access level: full document or excerpt) |
| `data/entities.csv` | One row per company, SPV, site, facility or contract, as sources name them |
| `data/entity_links.csv` | Judgements that two entities are the same (`same_as`) or related (`part_of`) |
| `data/statements.csv` | The facts |
| `data/quotes.csv` | Verbatim quotes behind statements; `check` fails if a quote is not in the archived document |
| `data/source_directory.yaml` | Every free and paid source by jurisdiction (registers, security, insolvency, courts, markets, lenders) |
| `data/document_types.yaml` | Which document answers which question (org chart, guarantors, debt documents, security, financials, restructuring, lenders, contracts), how to recognise it in each feed, and sector presets |
| `data/archive/` | Downloaded documents, each folder with a `manifest.json` (URL, SHA-256, retrieval time) |
| `tracker/` | Validator, resolution rules, report generator, monitor, archive checks, jurisdiction search |
| `docs/decisions.md` | Design decisions with first-principles reasoning |

## Commands

Needs Python 3.11+ and PyYAML (`pip install pyyaml`).

```bash
python -m tracker check                 # validate data, archive hashes, quotes and the source directory
python -m tracker report group_nscale   # print the Nscale credit file
python -m tracker build                 # write build/tracker.db (SQLite) for querying
python -m tracker search uk "Nscale"    # live registry search for one jurisdiction (uk, ie, lu, nl, de, fr, ...)
python -m tracker search lu,ie "Nscale" # several at once; --links prints lookup links only
python -m tracker sources lu --paid     # the source directory for a jurisdiction (--free, --channel security)
python -m tracker company uk 16925886   # one company's filings sorted by question (registry no, SEC CIK or LEI)
python -m tracker sector data_centres --jur us,no,uk   # debt documents and debt totals across a sector
python -m tracker documents lu --need guarantors      # which document answers a question, and how to spot it
python scripts/build_source_directory.py   # reports/source_directory.html (shareable page) + .csv
python -m unittest discover -s tests -t .
```

`company` sorts a company's filings into credit questions: org chart, guarantors, debt documents, security,
financials, restructuring, lenders and contracts. It pulls GLEIF parents and subsidiaries for any country; Companies
House filings, charges, corporate PSCs and insolvency cases (UK, needs a key); every SEC filing plus the exhibits of
the filings that carry debt, with each Exhibit 10 sorted by its title (credit agreement vs customer contract);
Norwegian accounts debt figures; French accounts summaries; Finnish and Irish status. Under each question it then
lists the documents to read by hand in that jurisdiction, with what to look for in them.

`sector` finds debt across a sector: SEC debt documents that mention the sector (credit agreements, indentures,
8-Ks reporting new debt), Norwegian companies ranked by debt in their filed accounts, and UK lenders by registered
charges (needs a Companies House key).

`search` runs every source with a live adapter for that jurisdiction, plus GLEIF filtered to the country
(the LEI record gives the registry number), and prints one-click lookup links for the rest. Search hits
are leads: confirm in the register before recording a statement. Keys it uses when set:
`COMPANIES_HOUSE_API_KEY`, `KVK_API_KEY`; EDGAR needs `EDGAR_USER_AGENT="Name email"`.

## Adding a fact

1. If the document is new, add a row to `data/sources.csv`. Set `access` to `excerpt` if you
   only saw a quote or summary.
2. If the company, loan or site is new, add a row to `data/entities.csv`.
3. Add a row to `data/statements.csv`: entity, property (must exist in the vocabulary), value,
   unit (currency for money), source, where in the source (`locator`), the date the value was
   true (`effective_date`, optional), today's date (`observed_date`), and `method`.
   - The source states it: `disclosed`. It reports it second-hand: `reported`. You calculated it:
     `derived` (list input ids in `derived_from`). You estimated it: `estimated` (explain in `note`).
   - The source was checked and does not state it: `checked_absent`, with an empty value.
4. If the document is archived, add the exact words to `data/quotes.csv` (statement id, archived file,
   quote). `check` fails if the quote is not in the file, so a paraphrase or a misread cannot pass.
5. Run `python -m tracker check`. It tells you exactly what's wrong.

Never edit or delete an old statement because a newer one disagrees. Add the new one; the
rules decide what's shown and the disagreement stays visible.

## Status

- **Nscale:** ~1,000 statements from the full S-1 and its exhibits (debt agreements, customer
  contracts, subsidiary list), Companies House (profiles and registered charges for six key UK
  entities) and CCIR's issuer page, cross-checked against each other. Earlier excerpt-based
  statements are kept; misreadings are rejected in `data/reviews.csv` with reasons.
- `scripts/oneoff/` holds the scripts that loaded those statements (kept for reproducibility).
- Built: daily monitor (EDGAR, Companies House, news), document archive with hashes, verbatim-quote
  checks, per-jurisdiction registry search, and a directory of 108 European sources.
- Not built yet: LLM extraction, credit metrics, archive of every source document (only two exhibits
  are archived; `scripts/fetch_edgar.py` now archives with hashes), the senior-facing view.

## Secrets

The Companies House API key is read from `~/.config/ai-infrastructure/companies_house_api_key`
(or, later, a GitHub Actions secret). Never commit it.
