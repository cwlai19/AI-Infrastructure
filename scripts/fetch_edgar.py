"""Download one SEC EDGAR filing (main document and every exhibit) and convert each to plain text.

    python scripts/fetch_edgar.py <CIK> <ACCESSION> [out_dir]
    e.g. python scripts/fetch_edgar.py 2110365 0001193125-26-395475

Writes <out_dir>/<accession>/{name}.htm, {name}.txt (one line per block) and {name}.flat.txt (one line,
whitespace collapsed: the form the clause anchors in data/contract_writeup.yaml and the reading helpers expect).
SEC requires a descriptive User-Agent: set EDGAR_USER_AGENT="Your Name your@email". Keeps to SEC's 10 requests/second.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from html2text import P  # noqa: E402

UA = os.environ.get("EDGAR_USER_AGENT")
if not UA:
    raise SystemExit("Set EDGAR_USER_AGENT, e.g. 'Jane Doe jane@example.com' (SEC requirement)")


def get(url):
    time.sleep(0.15)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def to_text(raw):
    p = P()
    p.feed(raw.decode("utf-8", errors="replace"))
    text = "".join(p.out)
    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def main(cik, acc, out_dir="data/archive/edgar"):
    nodash = acc.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{nodash}/"
    index = json.loads(get(base + "index.json"))
    out = Path(out_dir) / acc
    out.mkdir(parents=True, exist_ok=True)
    docs = [i["name"] for i in index["directory"]["item"] if i["name"].lower().endswith((".htm", ".html", ".txt"))
            and not i["name"].endswith("-index.htm")]
    for name in docs:
        raw = get(base + name)
        (out / name).write_bytes(raw)
        text = to_text(raw) if name.lower().endswith((".htm", ".html")) else raw.decode("utf-8", errors="replace")
        stem = Path(name).stem
        (out / f"{stem}.txt").write_text(text)
        (out / f"{stem}.flat.txt").write_text(re.sub(r"\s+", " ", text))
        print(f"{name}: {len(text):,} chars")
    print(f"saved {len(docs)} documents to {out}  (source URL base: {base})")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
