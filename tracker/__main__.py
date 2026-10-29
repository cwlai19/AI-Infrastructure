"""Command line.

    python -m tracker check              validate every data file against the vocabulary
    python -m tracker build              validate, then write build/tracker.db (SQLite) for querying
    python -m tracker report <group_id>  print a credit file, e.g. group_nscale
    python -m tracker monitor [edgar|ch|news]  log new filings about watched groups to data/events.csv
"""

import sqlite3
import sys
from dataclasses import asdict

from .model import ROOT, load, validate
from .report import credit_file


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


def main(argv):
    if not argv or argv[0] not in ("check", "build", "report", "monitor"):
        print(__doc__)
        return 2
    store = load()
    errors = validate(store)
    if errors:
        print(f"{len(errors)} problem(s):")
        print("\n".join(f"  - {e}" for e in errors))
        return 1
    cmd = argv[0]
    if cmd == "check":
        print(f"OK: {len(store.statements)} statements, {len(store.entities)} entities, {len(store.sources)} sources.")
    elif cmd == "build":
        path = ROOT / "build" / "tracker.db"
        build_db(store, path)
        print(f"Wrote {path}")
    elif cmd == "monitor":
        from .monitor import run
        feeds = tuple(argv[1:]) or ("edgar", "ch", "news")
        new = run(store, feeds)
        print(f"{len(new)} new event(s)")
        out = ROOT / "build" / "new_events.md"
        out.parent.mkdir(exist_ok=True)
        lines = [f"{len(new)} new filing(s) to triage:", ""]
        lines += [f"- {e['event_date']} [{e['feed']}] [{e['title']}]({e['url']})"
                  for e in sorted(new, key=lambda e: e["event_date"], reverse=True)]
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
