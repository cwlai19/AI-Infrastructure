"""Command line.

    python -m tracker check              validate data, archived-file hashes, quotes and the source directory
    python -m tracker build              validate, then write build/tracker.db (SQLite) for querying
    python -m tracker report <group_id>  print a credit file, e.g. group_nscale
    python -m tracker monitor [edgar|ch|news]  log new filings about watched groups to data/events.csv
    python -m tracker search <jurisdiction[,jurisdiction]> "<name>" [--links]
                                         search a country's registers live (uk, ie, lu, nl, de, fr, es, it,
                                         no, se, dk, fi, eu, us); --links prints the lookup links only
    python -m tracker sources [<jurisdiction>] [--channel <c>] [--paid | --free]
                                         list the source directory (data/source_directory.yaml)
    python -m tracker company <jurisdiction> <registry no | CIK | LEI> [--all]
                                         one company's documents sorted by question: org chart, guarantors,
                                         debt documents, security, financials, restructuring, lenders
    python -m tracker sector <preset> [--jur us,no,uk] [--since YYYY-MM-DD] [--max N]
                                         debt documents and debt totals across a sector (presets in
                                         data/document_types.yaml, e.g. data_centres)
    python -m tracker documents [<jurisdiction>] [--need <need>]
                                         which document answers which question, and how to recognise it
    python -m tracker where [<instrument>] [--region <jurisdiction>]
                                         where a kind of debt leaves a public trace, when, and the legal basis
    python -m tracker signals [--region <jurisdiction>] [--stage pre|closing|after]
                                         signs that a financing is coming, closing or done, and where to watch
    python -m tracker refs [<reference id>]   the citations behind the disclosure map
    python -m tracker lenders [<preset>] [--terms "A,B"] [--months 3] [--no-reconcile] [--csv <path>]
                                         which BDCs hold a group's or sector's debt or equity, cost and mark,
                                         checked against each BDC's reported total (needs edgartools)
    python -m tracker watch [--names "A,B"] [--since <days>] [--record]
                                         pre-financing signals: new SPVs, parent links, LEIs, articles, charges
    python -m tracker stream [--seconds 300]  Companies House charges stream (needs a stream key)
    python -m tracker financings [--group <id>] [--csv <path>] [--json <path>] [--dashboard <dir>]
                                         financing table and timeline data (facilities, detected waves, lender holdings)
    python -m tracker intake <file.csv> [--dry-run]
                                         add financings from a simple CSV (template: data/intake/financings_template.csv)
"""

import sqlite3
from pathlib import Path
import sys
from dataclasses import asdict

from . import archive, disclosure, documents, financings, intake, jurisdictions, lenders, watch
from .model import ROOT, load, validate
from .report import credit_file

PAID = {"pay_per_doc", "freemium", "subscription"}
FREE = {"free", "free_key", "free_limited"}


def build_db(store, path):
    path.parent.mkdir(exist_ok=True)
    path.unlink(missing_ok=True)
    db = sqlite3.connect(path)
    tables = {
        "sources": list(store.sources.values()),
        "entities": list(store.entities.values()),
        "entity_links": store.links,
        "statements": [{**asdict(s), "derived_from": ";".join(s.derived_from)} for s in store.statements],
    }
    for name, rows in tables.items():
        if not rows:
            continue
        cols = list(rows[0])
        db.execute(f"CREATE TABLE {name} ({', '.join(c + ' TEXT' for c in cols)})")
        db.executemany(f"INSERT INTO {name} VALUES ({', '.join('?' * len(cols))})",
                       [[r.get(c, "") for c in cols] for r in rows])
    db.commit()
    db.close()


def _option(argv, name):
    return argv[argv.index(name) + 1] if name in argv and argv.index(name) + 1 < len(argv) else None


def search_cmd(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 2:
        print('usage: python -m tracker search <jurisdiction[,jurisdiction]|all> "<name>" [--links]')
        return 2
    d = jurisdictions.directory()
    try:
        keys = list(d["jurisdictions"]) if args[0] == "all" else [jurisdictions.jurisdiction_key(k) for k in args[0].split(",")]
    except KeyError as e:
        print(e.args[0])
        return 2
    term = " ".join(args[1:])
    for key in keys:
        results, failures, links = jurisdictions.search(key, term, live="--links" not in argv)
        print(jurisdictions.format_search(key, term, results, failures, links) + "\n")
    return 0


def sources_cmd(argv):
    d = jurisdictions.directory()
    jur = next((a for a in argv if not a.startswith("--") and a != _option(argv, "--channel")), None)
    try:
        jur = jurisdictions.jurisdiction_key(jur) if jur else None
    except KeyError as e:
        print(e.args[0])
        return 2
    access = PAID if "--paid" in argv else FREE if "--free" in argv else None
    rows = jurisdictions.resources(jur, _option(argv, "--channel"), access)
    print(jurisdictions.format_sources(rows, d))
    print(f"\n{len(rows)} source(s). Channels: {', '.join(d['channels'])}")
    return 0


def company_cmd(argv):
    args = [a for a in argv if not a.startswith("--")]
    if len(args) < 2:
        print("usage: python -m tracker company <jurisdiction> <registry no | CIK | LEI> [--all]")
        return 2
    try:
        jur = jurisdictions.jurisdiction_key(args[0])
    except KeyError as e:
        print(e.args[0])
        return 2
    d = documents.company(jur, args[1])
    print(documents.format_company(d, show=10_000 if "--all" in argv else 12))
    return 0


def sector_cmd(argv):
    t = documents.taxonomy()
    preset = next((a for a in argv if not a.startswith("--") and a not in
                   (_option(argv, "--jur"), _option(argv, "--since"), _option(argv, "--max"))), None)
    if preset not in t["sectors"]:
        print(f"usage: python -m tracker sector <preset> [--jur us,no,uk] [--since YYYY-MM-DD] [--max N]\n"
              f"presets: {', '.join(t['sectors'])} (add more in data/document_types.yaml)")
        return 2
    jurs = tuple((_option(argv, "--jur") or "us,no,uk").split(","))
    preset_spec, out, failures = documents.sector(preset, jurs, _option(argv, "--since") or "2024-01-01",
                                                  int(_option(argv, "--max") or 60))
    print(documents.format_sector(preset_spec, out, failures))
    return 0


def documents_cmd(argv):
    jur = next((a for a in argv if not a.startswith("--") and a != _option(argv, "--need")), None)
    try:
        jur = jurisdictions.jurisdiction_key(jur) if jur else None
    except KeyError as e:
        print(e.args[0])
        return 2
    print(documents.format_guidance(jur, _option(argv, "--need")))
    print(f"\nNeeds: {', '.join(documents.taxonomy()['needs'])}")
    return 0


def _region(argv):
    r = _option(argv, "--region")
    if r in (None, "all", "nordics", "eu"):
        return r
    return jurisdictions.jurisdiction_key(r)


def where_cmd(argv):
    instrument = next((a for a in argv if not a.startswith("--") and a != _option(argv, "--region")), None)
    try:
        region = _region(argv)
    except KeyError as e:
        print(e.args[0])
        return 2
    print(disclosure.format_where(disclosure.instruments(instrument, region)))
    if region:
        rows = [t for t in disclosure.disclosure_map().get("borrower_traces", []) if disclosure.covers(t["region"], region)]
        if rows and not instrument:
            print("=== Disclosure by the borrower, whatever the instrument")
            for t in rows:
                print(f"  [{t['region']}] {t['status'].upper()} ({t['evidence'].replace('_', ' ')}): {t['trace']}"
                      + (f"; {t['timing']}" if t.get("timing") else ""))
    return 0


def signals_cmd(argv):
    try:
        region = _region(argv)
    except KeyError as e:
        print(e.args[0])
        return 2
    print(disclosure.format_signals(disclosure.signals(region, _option(argv, "--stage"))))
    return 0


def refs_cmd(argv):
    print(disclosure.format_refs(next((a for a in argv if not a.startswith("--")), None)))
    return 0


def lenders_cmd(argv):
    import warnings
    warnings.filterwarnings("ignore")    # edgartools warns on every unusual row; the reconciliation reports what matters
    preset = next((a for a in argv if not a.startswith("--") and a not in
                   (_option(argv, "--terms"), _option(argv, "--months"), _option(argv, "--csv"))), None)
    if _option(argv, "--terms"):
        terms = [t.strip() for t in _option(argv, "--terms").split(",") if t.strip()]
    elif preset in documents.taxonomy()["sectors"]:
        terms = documents.taxonomy()["sectors"][preset].get("lender_terms") or []
    else:
        print('usage: python -m tracker lenders <preset> | --terms "Name A,Name B" [--months 3] [--no-reconcile] [--csv <path>]')
        return 2
    positions, recons, failures, months = lenders.lenders(terms, int(_option(argv, "--months") or 3), "--no-reconcile" not in argv)
    print(lenders.format_lenders(positions, recons, failures, months))
    if _option(argv, "--csv"):
        lenders.write_csv(positions, _option(argv, "--csv"))
        print(f"\nwrote {_option(argv, '--csv')}")
    return 0


def watch_cmd(argv):
    groups = ({"names": [n.strip() for n in _option(argv, "--names").split(",") if n.strip()]}
              if _option(argv, "--names") else watch.watch_groups())
    signals, failures = watch.watch(groups, int(_option(argv, "--since") or 90))
    print(watch.format_watch(signals, failures))
    if "--record" in argv:
        from .monitor import append_new
        new = append_new(watch.to_events(signals))
        print(f"\nrecorded {len(new)} new signal(s) in data/events.csv (older ones are marked baseline on a first run)")
    return 0


def stream_cmd(store, argv):
    from .monitor import append_new, uk_companies
    numbers = {n for g in store.entities if store.entities[g]["type"] == "group" for _, n in uk_companies(store, g)}
    try:
        events = watch.stream_charges(int(_option(argv, "--seconds") or 300), numbers or None)
    except RuntimeError as e:
        print(e)
        return 2
    new = append_new(events)
    print(f"{len(events)} charge event(s) for watched companies; {len(new)} new")
    return 0


def financings_cmd(argv):
    data = financings.build()
    print(financings.format_table(data, _option(argv, "--group")))
    if _option(argv, "--csv"):
        financings.write_csv(data["financings"], _option(argv, "--csv"))
        print(f"wrote {_option(argv, '--csv')}")
    if _option(argv, "--dashboard"):
        import json
        out = Path(_option(argv, "--dashboard"))
        out.mkdir(parents=True, exist_ok=True)
        for name, rows in financings.dashboard_rows(data).items():
            (out / f"{name}.json").write_text(json.dumps(rows, indent=1, default=str))
        print(f"wrote financings.json, waves.json, holdings.json to {out}")
    if _option(argv, "--json"):
        import json
        Path(_option(argv, "--json")).parent.mkdir(parents=True, exist_ok=True)
        Path(_option(argv, "--json")).write_text(json.dumps(data, indent=1, default=str))
        print(f"wrote {_option(argv, '--json')}")
    return 0


def intake_cmd(argv):
    path = next((a for a in argv if not a.startswith("--")), None)
    if not path:
        print("usage: python -m tracker intake <file.csv> [--dry-run]   (template: data/intake/financings_template.csv)")
        return 2
    try:
        counts, problems = intake.run(path, dry_run="--dry-run" in argv)
    except ValueError as e:
        print(e)
        return 2
    if problems:
        print(f"Nothing written: {len(problems)} problem(s):")
        print("\n".join(f"  - {p}" for p in problems))
        return 1
    verb = "Would add" if "--dry-run" in argv else "Added"
    print(f"{verb} {counts['statements']} statements, {counts['entities']} entities, {counts['sources']} sources.")
    return 0


def main(argv):
    commands = ("check", "build", "report", "monitor", "search", "sources", "company", "sector", "documents",
                "where", "signals", "refs", "lenders", "watch", "stream", "financings", "intake")
    if not argv or argv[0] not in commands:
        print(__doc__)
        return 2
    if argv[0] == "search":
        return search_cmd(argv[1:])
    if argv[0] == "sources":
        return sources_cmd(argv[1:])
    handlers = {"company": company_cmd, "sector": sector_cmd, "documents": documents_cmd, "where": where_cmd,
                "signals": signals_cmd, "refs": refs_cmd, "lenders": lenders_cmd, "watch": watch_cmd,
                "financings": financings_cmd, "intake": intake_cmd}
    if argv[0] in handlers:
        return handlers[argv[0]](argv[1:])
    store = load()
    errors = validate(store)
    if argv[0] == "check":
        errors += (archive.verify() + archive.check_quotes(store) + jurisdictions.validate_directory()
                   + documents.validate_taxonomy() + disclosure.validate_map())
    if errors:
        print(f"{len(errors)} problem(s):")
        print("\n".join(f"  - {e}" for e in errors))
        return 1
    cmd = argv[0]
    if cmd == "check":
        n_quotes = len(archive._read_csv(archive.QUOTES))
        print(f"OK: {len(store.statements)} statements, {len(store.entities)} entities, {len(store.sources)} sources, "
              f"{n_quotes} verbatim quotes, {len(jurisdictions.directory()['resources'])} directory sources, "
              f"{len(disclosure.disclosure_map()['references'])} disclosure-map references.")
    elif cmd == "build":
        path = ROOT / "build" / "tracker.db"
        build_db(store, path)
        print(f"Wrote {path}")
    elif cmd == "stream":
        return stream_cmd(store, argv[1:])
    elif cmd == "monitor":
        from .monitor import run
        feeds = tuple(argv[1:]) or ("edgar", "ch", "news", "signal")
        new, failures = run(store, feeds)
        print(f"{len(new)} new event(s), {len(failures)} feed failure(s)")
        for f in failures:
            print(f"  FEED FAILED: {f}")
        out = ROOT / "build" / "new_events.md"
        out.parent.mkdir(exist_ok=True)
        lines = [f"{len(new)} new filing(s) to triage:", ""]
        lines += [f"- {e['event_date']} [{e['feed']}] [{e['title']}]({e['url']})"
                  + (f" ({', '.join(documents.event_needs(e))})" if documents.event_needs(e) else "")
                  for e in sorted(new, key=lambda e: e["event_date"], reverse=True)]
        if failures:
            lines += ["", "**Feeds that failed this run (their filings were not checked):**", ""]
            lines += [f"- {f}" for f in failures]
        out.write_text("\n".join(lines) + "\n")
        for e in sorted(new, key=lambda e: e["event_date"], reverse=True)[:40]:
            print(f"  {e['event_date']}  [{e['feed']}] {e['title'][:110]}")
    elif cmd == "report":
        if len(argv) < 2 or argv[1] not in store.entities:
            print("usage: python -m tracker report <group_id>")
            return 2
        print(credit_file(store, argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
