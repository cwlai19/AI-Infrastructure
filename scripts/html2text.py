"""Convert EDGAR HTML to plain text, one line per block element; table cells joined with ' | '.

    python scripts/html2text.py <folder of .htm> <output folder>

Also imported by fetch_edgar.py (to_text). Skips scripts, styles and the hidden inline-XBRL header
(<ix:header>), whose tagged facts otherwise appear as noise at the top of every filing.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"}
CELL = {"td", "th"}
SKIP = {"script", "style", "ix:header"}


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        elif tag in BLOCK:
            self.out.append("\n")
        elif tag in CELL:
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def to_text(raw):
    """HTML string -> text with one line per block and whitespace collapsed within lines."""
    p = P()
    p.feed(raw)
    lines = [re.sub(r"[ \t\xa0]+", " ", ln).strip() for ln in "".join(p.out).splitlines()]
    return "\n".join(ln for ln in lines if ln)


def main(src, dst):
    dst.mkdir(exist_ok=True)
    for f in sorted(src.glob("*.htm")):
        lines = [ln.strip(" |").strip() for ln in to_text(f.read_text(errors="replace")).split("\n")]
        lines = [ln for ln in lines if ln]
        (dst / (f.stem + ".txt")).write_text("\n".join(lines))
        print(f.stem, len(lines))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
