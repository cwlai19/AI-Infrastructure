# Related open-source tools, and what we take from them

Surveyed 30 Oct 2026. Python packages were checked on PyPI (latest version and release date below). Projects only on
GitHub were found by web search; their code has not been reviewed here. No tool found does the whole job (a sourced
credit tracker for European private debt); several do parts of it well.

## Do the same job as part of this tool

| Tool | What it does | Overlap | Decision |
|---|---|---|---|
| [edgartools](https://github.com/dgunning/edgartools) (PyPI 5.62.1, 23 Oct 2026) | Python library for EDGAR filings, exhibits and XBRL financials, including BDC schedules of investments (`PortfolioInvestments`) | Our `fetch_edgar.py`, US company pulls, and the planned lender layer | **Use it for BDC holdings and XBRL financials** instead of writing our own parser. Its open issues show the hard cases: picking the right period, and identifiers that end in a coupon being dropped ([#1584](https://github.com/dgunning/edgartools/issues/1584), [#1504](https://github.com/dgunning/edgartools/issues/1504)). Keep our fetcher for the archive and quote checks |
| [tpmkuehn/bdc-soi](https://github.com/tpmkuehn/bdc-soi) | Extracts BDC schedules of investments from 10-Qs (XBRL, Inline XBRL, HTML), no LLM, reconciles to reported totals | Lender layer | **Borrow the reconciliation idea:** check extracted positions add up to the filed total before trusting them |
| [Lakshya5Jain/bdc-loan-quality](https://github.com/Lakshya5Jain/bdc-loan-quality) | Every BDC loan quarter over quarter from SEC XBRL into DuckDB, with a stable loan id across quarters | Lender layer, history | **Borrow the stable loan id** (identifier parsing plus fuzzy matching) for tracking a loan's marks over time |
| [kennypang41-hub/BDC](https://github.com/kennypang41-hub/BDC) | BDC tracker built on SEC's bulk financial statement data sets, with per-filing XBRL as fallback | Lender layer | **Borrow the bulk-first approach:** one bulk download instead of hundreds of filing requests |
| [vandiwork/bdc-researcher](https://github.com/vandiwork/bdc-researcher) | Schedule of investments for 18 BDCs, XBRL joined to HTML | Lender layer | Reference only |
| [OpenSanctions FollowTheMoney](https://github.com/opensanctions/followthemoney) (PyPI 4.11.2, 26 Oct 2026) | Entity data model for companies, ownership, debt, people | Our vocabulary | **Export to it later** so our data can join other investigative datasets; keep our own vocabulary for credit properties it lacks (D3) |
| [nomenklatura](https://github.com/opensanctions/nomenklatura) (PyPI 4.17.5, 27 Oct 2026) | Stores data as statements with full lineage; entity matching and a review tool for merges | Our statement model (D1) and `entity_links.csv` (D9) | Same design as ours, which supports it. **Consider its matching** when entity counts grow |
| [OpenSanctions crawlers / zavod](https://zavod.opensanctions.org/metadata/) | One YAML metadata file per source plus one crawler per source | Our source directory and adapters | **Borrow metadata fields:** update frequency, licence, terms URL, disabled flag, last successful run |
| [companies-house](https://github.com/RegistrumUK/companies-house-python) (PyPI 0.2.1, 21 Oct 2026) | Companies House API client that handles the rate limit | `net.py`, UK adapters | Not needed: `net.py` already paces requests. Keep in mind if UK calls grow |
| [pygleif](https://github.com/ggravlingen/pygleif) (PyPI 2026.7.3) | GLEIF API client | GLEIF calls | Not needed: our calls are few and simple |

**Companies House charges by lender.** No open-source tool or dataset was found that lists charges by lender. The
Companies House forum has open requests for exactly this ([1](https://forum.companieshouse.gov.uk/t/bulk-charges-dataset-request-for-chargee-keyed-extract-persons-entitled/12767),
[2](https://forum.companieshouse.gov.uk/t/filter-company-profiles-charges-by-persons-entitled/1533)); the paid and gated
options are an [Apify actor](https://apify.com/devon_gtme/uk-company-charges-lookup.md) and a
[Hugging Face dataset](https://huggingface.co/datasets/dacheah/uk-securitisation-spv-charges). The forum's suggested
route is ours: start from a list of companies, then read each one's charges. The
[charges stream](https://developer-specs.company-information.service.gov.uk/streaming-api/resources/chargesstream)
pushes every new charge and is the right next step for monitoring at scale.

## Building blocks worth adopting

| Tool | Use | When |
|---|---|---|
| [Git scraping](https://simonwillison.net/tags/git-scraping/) (Simon Willison) | Scheduled GitHub Action fetches data and commits it, so git history records every change | Already our monitor's pattern |
| [datasette](https://github.com/simonw/datasette) (0.65.5) + [sqlite-utils](https://github.com/simonw/sqlite-utils) (4.2.1) | Browse and query `build/tracker.db` in a browser, no code | Now: `pip install datasette && datasette build/tracker.db` |
| [vcrpy](https://github.com/kevin1024/vcrpy) (9.2.0) | Record real API responses once, replay them in tests | Next: test adapters against recorded responses instead of hand-written mocks |
| [requests-cache](https://github.com/requests-cache/requests-cache) (1.3.3) | Cache responses so re-runs do not hit sites again | If `sector` runs become frequent |
| [dlt](https://github.com/dlt-hub) (1.32.0) | Incremental loading with saved cursors and schema checks | If feeds grow beyond a few dozen |
| [frictionless](https://github.com/frictionlessdata/framework) (5.21.0) or pydantic (2.14.2) | Declarative table and record validation | Optional: our validator already does this for our files |
| [DuckDB](https://github.com/duckdb/duckdb-python) (2.0.0) | Fast queries over CSV and Parquet, including SEC bulk data sets | For the BDC bulk data |
| [docling](https://github.com/docling-project/docling) (2.145.0), [pdfplumber](https://github.com/jsvine/pdfplumber) (0.11.10), [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) (17.13.0) | Turn MR01 instruments, accounts and prospectuses (PDF, often scanned) into text for quote checks | Next, for Companies House PDFs |
| [trafilatura](https://github.com/adbar/trafilatura) (2.3.1) | Extract article text from news pages | When news events need reading |
| [Arelle](https://github.com/Arelle/Arelle) (2.47.3) | XBRL processor for ESEF and iXBRL accounts | For European listed and UK iXBRL accounts |
| Dagster (1.13.27) / Prefect (3.9.0) | Workflow orchestration | Not yet: GitHub Actions is enough |

## Practices to take, in order

1. **Use edgartools for BDC holdings**, and check every extraction against reported totals (bdc-soi). This gives the
   lender layer (who holds which neocloud loan, at what mark) without a new parser.
2. **Record real responses for tests** (vcrpy), so adapter changes are tested against what sites actually return.
3. **Per-source metadata** (zavod): add update frequency, licence, terms URL and last successful run to
   `source_directory.yaml`, and show stale sources in `check`.
4. **Companies House charges stream** for monitoring hundreds of SPVs without polling each one.
5. **Stable ids for loans** across quarters and sources (bdc-loan-quality), which is also what reconciling a reported
   deal to an MR01 needs.
6. **Browse with datasette** instead of building more custom pages for internal use.
