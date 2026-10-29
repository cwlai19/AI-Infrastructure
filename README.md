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
| `tracker/` | Validator, resolution rules and report generator |
| `docs/decisions.md` | Design decisions with first-principles reasoning |

## Commands

Needs Python 3.11+ and PyYAML (`pip install pyyaml`).

```bash
python -m tracker check                 # validate all data against the vocabulary
python -m tracker report group_nscale   # print the Nscale credit file
python -m tracker build                 # write build/tracker.db (SQLite) for querying
python -m unittest discover -s tests -t .
```

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
4. Run `python -m tracker check`. It tells you exactly what's wrong.

Never edit or delete an old statement because a newer one disagrees. Add the new one; the
rules decide what's shown and the disagreement stays visible.

## Status

- Seed data for Nscale, built from **search excerpts only**, so everything is capped at grade B.
  Next step: read the full S-1 and credit agreements, and add grade-A statements alongside.
- Not built yet: document archive, live monitoring feeds, LLM extraction, credit metrics,
  the senior-facing view.
