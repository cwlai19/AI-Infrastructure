# Decision log

Each decision states the problem from first principles, what we chose, and why the
alternatives lose. If a later decision overturns one, add a new entry; don't edit history.

---

## D1. The atomic unit of data is a *statement*, not a record

**Problem.** A credit view is a chain of claims. A reader can only trust the conclusion if
they can check every link: who said it, when, how, and whether anyone disagrees. For
private European neoclouds, facts arrive piecemeal, from sources of very different
reliability, at different times, often in conflict.

**Choice.** One row = one claim from one source:
`entity · property = value · source · effective date · observed date · method`.
What readers see (a debt ledger, a credit file) is *computed* from statements. Nothing is
ever overwritten; new information is a new row.

**Alternatives rejected.**
- *One row per deal (spreadsheet/Airtable).* Each overwrite deletes evidence: the old value,
  who said it, and the fact that two sources disagreed. Real example already in our data:
  CCIR says Ward County is up to $1.831B, the S-1 says $1.85B. In a spreadsheet one silently
  replaces the other.
- *Documents only, ask an LLM when needed.* Good for deep dives, but there is no running
  state to compare companies, track change over time, or alert on. Answers can differ each
  time you ask.
- *Event log only ("charge filed", "deal announced").* Events are coarse: one press release
  holds ten facts. Conflicts stay buried in prose. We keep events for monitoring (later) but
  turn them into statements.
- *Graph database.* Answers network questions well, but provenance has to be bolted on and
  it's heavy to run for a few thousand facts. A graph can be built *from* statements later.

**Analogy.** Accounting: you post journal entries and compute balances; you never edit a balance.

---

## D2. The master copy is plain CSV files in git; SQLite is a built copy

**Problem.** Data must be editable by a non-programmer, every change must be reviewable and
reversible, and history must be kept automatically.

**Choice.** `data/*.csv` is the master copy (opens in Excel). `git` records who changed what
and when. `python -m tracker build` produces `build/tracker.db` (SQLite) for querying. The
database can be deleted and rebuilt at any time.

**Alternatives rejected.**
- *Excel/Google Sheets as master.* No line-by-line history or review; formulas and merged
  cells hide errors; hard for automated feeds to write to safely.
- *A database (SQLite/Postgres) as master.* Edits are invisible unless you build an audit
  system; non-programmers can't easily review changes.
- *Airtable/Notion.* Pleasant UI, but history and export are limited, and the data lives in
  someone else's system.

**When to revisit.** Beyond ~50k statements, or when many people edit at once, move the
master copy into a database with an append-only statements table.

---

## D3. A fixed vocabulary, enforced by a validator

**Problem.** If each source (or each LLM run) invents its own field names, nothing joins:
"facility size", "commitment", "amount" become three different facts.

**Choice.** `schema/vocabulary.yaml` fixes the entity types, their properties, each property's
value type and unit, and the allowed values. `python -m tracker check` rejects anything else.

**Alternatives rejected.**
- *Free-form tags/fields.* Fast to start, but the data fragments and can't be aggregated.
- *A full industry standard (e.g. FollowTheMoney).* Well designed but too general: no
  properties for margin, DSCR or MW energised. We borrow its ideas, not its schema.

**Cost.** Adding a property means editing the vocabulary first. That is deliberate: it forces
a decision about what the property means.

---

## D4. Relationships are statements too

**Problem.** "Blue Owl lends to the UK DDTL" is a fact with a source, exactly like "the DDTL is $1.4B".

**Choice.** A relationship is a statement whose value is another entity's id (`lender = le_blue_owl_bdc`).
The validator checks the target exists and is the right type.

**Alternative rejected.** *A separate relationship table or graph.* Two storage systems means
two sets of provenance rules. One table keeps one rule set.

---

## D5. Two dates: when it was true, and when we learned it

**Problem.** "The revolver was $770M, then $900M" is history, not a contradiction. And we need
to know when we first knew something, to measure which sources are early and to avoid
hindsight in post-mortems.

**Choice.** `effective_date` = when the value was true (may be partial, `2026-06`, or
"before", `<2026-06`). `observed_date` = when we recorded it. A later effective date
supersedes an earlier one and the old value moves to *history*.

**Rule for undated values.** A statement with no effective date cannot supersede a dated one.
If it disagrees, it is flagged as a conflict. Otherwise an undated news story could silently
overwrite a filing.

---

## D6. Explicit rules for which value is shown

**Problem.** When sources disagree, someone has to choose what the reader sees, and the
choice must be predictable and visible.

**Choice.** (1) The latest effective date wins. (2) On the same date, the stronger source
wins, using the vocabulary's ranking (filing/registry > counterparty filing/rating agency >
company release > aggregator > news > expert > internal), then method (disclosed > derived
> reported > estimated). (3) Disagreements are shown as conflicts, never hidden. (4) If a
newer value rests only on weaker sources than the value it replaces, it is flagged for review.

**Alternative rejected.** *An analyst picks the value by hand each time.* That is not
reproducible, and it hides the disagreement from readers.

---

## D7. Grades come from the source, not typed per fact

**Problem.** Hand-typed confidence scores drift and are inconsistent between people.

**Choice.** Grade (A/B/C) comes from the source type. If we only saw an excerpt (e.g. a search
result), the grade is capped at B. A derived number takes the grade of its weakest input.

**Why the excerpt cap matters.** Our first Nscale data came from search-result excerpts of the
S-1, not the S-1 itself. Labelling those "A: S-1" would overstate what we have read.

---

## D8. "Undisclosed" and "not yet checked" are different answers

**Problem.** For opaque private companies most fields are empty. A reader must know which
blanks are findings ("we read the credit agreement and the rate is redacted") and which are
to-dos.

**Choice.** `method = checked_absent` records that a source was checked and does not state
the value. Key properties with no statements at all show as "not yet checked" in the gap list.

---

## D9. Entity matching is a separate, reversible judgement

**Problem.** The same company or loan appears under different names (SPV name in a registry,
parent name in press, a lender's label in a BDC filing). Merging wrongly corrupts data;
never merging double-counts.

**Choice.** Statements attach to the entity *as the source named it*. Matches live in
`data/entity_links.csv`: `same_as` (merge) or `part_of` (related, not merged), each with who
judged it, when, and why. Deleting a row undoes a merge with no data lost.

**Live example.** The S-1's $725M term loan + $65M VAT revolver probably make up CCIR's
"$790M Norway project financing". They are linked `part_of`, not merged, until the S-1 text
confirms it.

---

## D10. No personal data for now

Directors and individuals are not entities. Registry data includes personal details covered
by GDPR, and we don't need them for credit risk yet. Revisit if a person-level question
comes up (e.g. a shared director between a neocloud and its landlord).
