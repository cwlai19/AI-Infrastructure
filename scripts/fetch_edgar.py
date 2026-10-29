"""Download one SEC EDGAR filing (main document and every exhibit) and convert each to plain text.

    python scripts/fetch_edgar.py <CIK> <ACCESSION> [out_dir]
    e.g. python scripts/fetch_edgar.py 2110365 0001193125-26-395475

Writes <out_dir>/<accession>/{name}.htm, {name}.txt (one line per block) and {name}.flat.txt (one line,
whitespace collapsed: the form the clause anchors in data/contract_writeup.yaml and the reading helpers expect).
Every downloaded file is logged in <out_dir>/<accession>/manifest.json (URL, SHA-256, size, retrieval time);
`python -m tracker check` re-hashes them. Skips the full-submission .txt and index pages, which only repeat the
documents. SEC requires a descriptive User-Agent: set EDGAR_USER_AGENT="Your Name your@email".
Requests go through tracker.net, which keeps to SEC's 10 requests/second and retries rate-limit errors.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from html2text import to_text  # noqa: E402
from tracker import archive, net  # noqa: E402


def documents(index, acc):
    """Names of the filing's own documents: the main document and exhibits, not indexes or the full submission."""
    skip = {f"{acc}.txt", f"{acc}-index.htm", f"{acc}-index.html", f"{acc}-index-headers.html"}
    return [i["name"] for i in index["directory"]["item"]
            if i["name"].lower().endswith((".htm", ".html", ".txt")) and i["name"] not in skip]


def main(cik, acc, out_dir="data/archive/edgar"):
    net.user_agent(require_contact=True)
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/"
    body, _ = net.get(base + "index.json")
    if body is None:
        raise SystemExit(f"no such filing: {base}")
    out = Path(out_dir) / acc
    docs = documents(json.loads(body), acc)
    for name in docs:
        raw, ctype = net.get(base + name)
        archive.record(out, name, raw, base + name, ctype)
        decoded = raw.decode("utf-8", errors="replace")
        text = to_text(decoded) if name.lower().endswith((".htm", ".html")) else decoded
        stem = Path(name).stem
        (out / f"{stem}.txt").write_text(text)
        (out / f"{stem}.flat.txt").write_text(re.sub(r"\s+", " ", text))
        print(f"{name}: {len(text):,} chars")
    print(f"saved {len(docs)} documents to {out}  (source URL base: {base})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    try:
        main(*sys.argv[1:])
    except RuntimeError as e:
        raise SystemExit(str(e))
