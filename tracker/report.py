"""Render a group's credit file (Markdown) from resolved statements."""

from .model import entities_of_group, format_value, resolve

LEDGER_COLUMNS = [
    ("amount_max", "Size (max)"),
    ("facility_type", "Type"),
    ("borrower", "Borrower"),
    ("signing_date", "Signed"),
    ("maturity_date", "Maturity"),
    ("margin_bps", "Margin (bps)"),
    ("collateral", "Collateral"),
    ("named_customer", "Customer"),
    ("lender", "Lenders"),
    ("rating_moodys", "Moody's"),
]

CONTRACT_COLUMNS = [
    ("customer", "Customer"),
    ("value_total", "Value"),
    ("term_months", "Term"),
    ("gpu_count", "GPUs"),
    ("gpu_type", "Chip"),
    ("site", "Site"),
    ("take_or_pay", "Take-or-pay"),
    ("implied_usd_per_gpu_hour", "Implied $/GPU-hr"),
]


def _label(store, entity_id):
    return store.entities.get(entity_id, {}).get("label", entity_id)


def _cell(store, r, kind):
    """One cell: value(s), each tagged with grade and statement ids, plus a ⚠ if disputed."""
    if r.status == "not_checked":
        return "—"
    if r.status == "undisclosed":
        return "undisclosed [" + ", ".join(s.id for s in r.absent) + "]"
    shown = r.current if r.status == "multi" else r.current[:1]
    parts = []
    for s in shown:
        value = _label(store, s.value) if kind == "entity" else format_value(s)
        backing = [s] if r.status == "multi" else r.current
        best = min((b.grade for b in backing), default="C")
        parts.append(f"{value} ({best}: {', '.join(b.id for b in backing)})")
    text = "; ".join(parts)
    return text + (" ⚠" if r.conflicts else "")


def credit_file(store, group_id):
    members = entities_of_group(store, group_id)
    types = store.vocab["entity_types"]
    by_type = {}
    for e in members:
        by_type.setdefault(store.entities[e]["type"], []).append(e)

    used = set()
    out = [f"# Credit file: {_label(store, group_id)}", ""]
    out.append("_Generated from statements. Every value shows its grade (A/B/C) and the statement ids "
               "behind it; ⚠ marks values that sources disagree on._")
    out.append("")

    # Headline numbers
    out += ["## Group", ""]
    for prop in types["group"]["properties"]:
        r = resolve(store, group_id, prop)
        if r.status == "not_checked":
            continue
        used.update(s.id for s in r.current + r.conflicts + r.history + r.absent)
        out.append(f"- **{prop}**: {_cell(store, r, types['group']['properties'][prop]['kind'])}")
    out.append("")

    # Debt ledger
    fac_props = types["facility"]["properties"]
    out += ["## Debt ledger", ""]
    out.append("| Facility | " + " | ".join(h for _, h in LEDGER_COLUMNS) + " |")
    out.append("|" + "---|" * (len(LEDGER_COLUMNS) + 1))
    for fac in by_type.get("facility", []):
        cells = []
        for prop, _ in LEDGER_COLUMNS:
            r = resolve(store, fac, prop)
            used.update(s.id for s in r.current + r.conflicts + r.history + r.absent)
            cells.append(_cell(store, r, fac_props[prop]["kind"]))
        out.append(f"| {_label(store, fac)} | " + " | ".join(cells) + " |")
    out.append("")
    links = [l for l in store.links if l["entity_a"] in members or l["entity_b"] in members]
    if links:
        out += ["**Entity-link judgements** (reversible; see `data/entity_links.csv`):", ""]
        for l in links:
            out.append(f"- {_label(store, l['entity_a'])} **{l['relation']}** {_label(store, l['entity_b'])}"
                       f" — {l['judged_by']}, {l['judged_date']}: {l['note']}")
        out.append("")

    # Offtake contracts
    ctr_props = types["contract"]["properties"]
    out += ["## Offtake contracts", ""]
    out.append("| Contract | " + " | ".join(h for _, h in CONTRACT_COLUMNS) + " |")
    out.append("|" + "---|" * (len(CONTRACT_COLUMNS) + 1))
    for ctr in by_type.get("contract", []):
        cells = []
        for prop, _ in CONTRACT_COLUMNS:
            r = resolve(store, ctr, prop)
            used.update(s.id for s in r.current + r.conflicts + r.history + r.absent)
            cells.append(_cell(store, r, ctr_props[prop]["kind"]))
        out.append(f"| {_label(store, ctr)} | " + " | ".join(cells) + " |")
    out.append("")

    # Conflicts, history, gaps across every member entity
    conflicts, history, undisclosed, not_checked = [], [], [], []
    for e in members:
        etype = store.entities[e]["type"]
        for prop, spec in types[etype]["properties"].items():
            r = resolve(store, e, prop)
            if r.conflicts:
                conflicts.append((e, prop, r))
            if r.history:
                history.append((e, prop, r))
            if r.status == "undisclosed":
                undisclosed.append((e, prop, r))
            if r.status == "not_checked" and spec.get("key"):
                not_checked.append((e, prop))

    out += ["## Conflicts (sources disagree)", ""]
    if not conflicts:
        out.append("None.")
    for e, prop, r in conflicts:
        cur = r.current[0]
        out.append(f"- **{_label(store, e)} · {prop}**: showing {format_value(cur)} from {cur.source} ({cur.grade}, {cur.id}).")
        for c in r.conflicts:
            out.append(f"  - disagrees: {format_value(c)} from {c.source} ({c.grade}, {c.id}) — {c.note}")
        for f in r.flags:
            out.append(f"  - rule: {f}")
    out.append("")

    out += ["## History (superseded values)", ""]
    if not history:
        out.append("None.")
    for e, prop, r in history:
        chain = " → ".join(f"{format_value(s)} ({s.effective_date}, {s.id})" for s in r.history)
        cur = r.current[0]
        out.append(f"- **{_label(store, e)} · {prop}**: {chain} → **{format_value(cur)}** ({cur.effective_date}, {cur.id})")
        for f in r.flags:
            out.append(f"  - rule: {f}")
    out.append("")

    out += ["## Gaps", "", "**Undisclosed** (a source was checked and does not state it):", ""]
    out += [f"- {_label(store, e)} · {p} (checked: {', '.join(s.source for s in r.absent)})"
            for e, p, r in undisclosed] or ["None."]
    out += ["", "**Not yet checked** (key properties with no statement — research to-do):", ""]
    grouped = {}
    for e, p in not_checked:
        grouped.setdefault(e, []).append(p)
    out += [f"- {_label(store, e)}: {', '.join(ps)}" for e, ps in grouped.items()] or ["None."]
    out.append("")

    # Estimates and excerpts the reader should know about
    caveats = [s for s in store.statements if s.id in used and s.method == "estimated"]
    if caveats:
        out += ["## Our estimates (not from any source)", ""]
        for s in caveats:
            kind = types[store.entities[s.entity]["type"]]["properties"][s.property]["kind"]
            value = _label(store, s.value) if kind == "entity" else format_value(s)
            out.append(f"- {s.id} {_label(store, s.entity)} · {s.property} = {value}: {s.note}")
        out.append("")

    out += ["## Sources", "", "| id | type | access | grade cap | title |", "|---|---|---|---|---|"]
    cited = {s.source for s in store.statements if s.id in used}
    for sid in sorted(cited):
        src = store.sources[sid]
        grade = store.vocab["source_types"][src["type"]]["grade"]
        if src["access"] == "excerpt" and grade == "A":
            grade = "B (excerpt only)"
        title = f"[{src['title']}]({src['url']})" if src.get("url") else src["title"]
        out.append(f"| {sid} | {src['type']} | {src['access']} | {grade} | {title} |")
    out.append("")
    return "\n".join(out)
