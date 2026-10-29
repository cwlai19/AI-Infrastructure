"""Convert EDGAR HTML files to plain text, one line per block element; table cells joined with ' | '."""
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

BLOCK = {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"}
CELL = {"td", "th"}


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in BLOCK:
            self.out.append("\n")
        elif tag in CELL:
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        elif tag in BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(exist_ok=True)
for f in sorted(src.glob("*.htm")):
    p = P()
    p.feed(f.read_text(errors="replace"))
    text = html.unescape("".join(p.out)).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", l).strip(" |") for l in text.split("\n")]
    lines = [l.strip() for l in lines if l.strip()]
    (dst / (f.stem + ".txt")).write_text("\n".join(lines))
    print(f.stem, len(lines))
