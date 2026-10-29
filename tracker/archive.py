"""The document archive: what we downloaded, from where, when, and proof it has not changed since.

Every archive folder holds a manifest.json: file name -> {url, sha256, bytes, content_type, retrieved_at}.
`verify()` re-hashes each file, so an edited or truncated document is caught before anyone quotes it.

data/quotes.csv ties a statement to the exact words behind it: statement_id, file, quote.
`check_quotes()` fails if the quote is not in the archived file (whitespace and curly quotes ignored),
which is the same guarantee the contract write-up's anchors give, extended to any statement.
"""

import hashlib
import json
import re
from datetime import datetime, timezone

from .model import DATA_DIR, ROOT, _read_csv

ARCHIVE_DIR = DATA_DIR / "archive"
QUOTES = DATA_DIR / "quotes.csv"
MANIFEST = "manifest.json"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def record(folder, name, data, url, content_type="", retrieved_at=None):
    """Write `data` to folder/name and log it in the folder's manifest. Returns the file path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    manifest_path = folder / MANIFEST
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest[name] = dict(url=url, sha256=sha256(data), bytes=len(data), content_type=content_type,
                          retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat(timespec="seconds"))
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return path


def verify(root=ARCHIVE_DIR):
    """Problems with archived files: missing, or changed since they were recorded."""
    problems = []
    for manifest_path in sorted(root.rglob(MANIFEST)):
        for name, meta in json.loads(manifest_path.read_text()).items():
            path = manifest_path.parent / name
            if not path.exists():
                problems.append(f"archive {path.relative_to(ROOT)}: listed in manifest but missing")
            elif sha256(path.read_bytes()) != meta["sha256"]:
                problems.append(f"archive {path.relative_to(ROOT)}: content changed since it was retrieved")
    return problems


def normalise(text):
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def check_quotes(store, quotes_path=QUOTES):
    """Problems with data/quotes.csv: unknown statements, missing files, or quotes not found verbatim."""
    problems, texts = [], {}
    ids = {s.id for s in store.statements}
    for row in _read_csv(quotes_path):
        where = f"quote for {row['statement_id']}"
        if row["statement_id"] not in ids:
            problems.append(f"{where}: unknown statement")
        if not row.get("quote"):
            problems.append(f"{where}: empty quote")
            continue
        path = ROOT / row["file"]
        if not path.exists():
            problems.append(f"{where}: archived file {row['file']} not found")
            continue
        if path not in texts:
            texts[path] = normalise(path.read_text(errors="replace"))
        if normalise(row["quote"]) not in texts[path]:
            problems.append(f"{where}: not found verbatim in {row['file']}: {row['quote'][:80]!r}")
    return problems
