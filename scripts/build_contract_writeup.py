"""Build reports/contract_writeup.html: a condensed, clause-by-clause write-up of Nscale's filed customer contracts.

Summaries come from data/contract_writeup.yaml. The exact wording behind each point is cut from the archived exhibit
text using that point's start/end anchors, so every quote is verbatim from the filing; a missing anchor stops the build.
"""
import html
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tracker.disclaimer import DETAIL, SHORT  # noqa: E402

MAX_QUOTE = 3000
spec = yaml.safe_load((ROOT / "data" / "contract_writeup.yaml").read_text())


def quote(text, start, end):
    i = text.find(start)
    if i < 0:
        raise SystemExit(f"anchor not found: {start!r}")
    j = text.find(end, i)
    if j < 0:
        raise SystemExit(f"end anchor not found after {start!r}: {end!r}")
    q = text[i:j + len(end)]
    return q if len(q) <= MAX_QUOTE else q[:MAX_QUOTE].rsplit(" ", 1)[0] + " …"


def md(s):
    """**bold** only; everything else escaped."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(s))


toc, body, n_quotes = [], [], 0
for c in spec["contracts"]:
    text = (ROOT / c["text"]).read_text()
    toc.append(f'<a href="#{c["id"]}">{html.escape(c["title"])}</a>')
    secs = []
    for si, s in enumerate(c["sections"], 1):
        items = []
        for p in s["points"]:
            q = quote(text, *p["q"])
            n_quotes += 1
            items.append(f'<li>{html.escape(p["t"])} <details><summary>Exact wording</summary>'
                         f'<blockquote>{html.escape(q)}</blockquote>'
                         f'<a class="src" href="{c["url"]}" target="_blank" rel="noopener">{c["exhibit"]} on SEC EDGAR ↗</a></details></li>')
        secs.append(f'<section class="clause"><h3><span class="n">{si}.</span> {html.escape(s["name"])}</h3><ul>{"".join(items)}</ul></section>')
    body.append(f'<article id="{c["id"]}"><h2>{html.escape(c["title"])}</h2>'
                f'<p class="meta">{html.escape(c["parties"])} <a href="{c["url"]}" target="_blank" rel="noopener">{c["exhibit"]} ↗</a></p>'
                f'<div class="cols">{"".join(secs)}</div></article>')

page = f"""<title>Nscale Contract Write-up</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>
:root {{ --bg: #ffffff; --ink: #37352f; --ink-2: #787774; --ink-3: #9b9a97; --line: #e9e9e7; --panel: #f7f7f5; --accent: #2383e2;
  --red-bg: #ffe2dd; --red-fg: #5d1715; --font: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --bg: #191919; --ink: #d4d4d4; --ink-2: #9b9b9b; --ink-3: #7f7f7f;
  --line: #2f2f2f; --panel: #222; --accent: #529cca; --red-bg: #522e2a; --red-fg: #f4b7ad; color-scheme: dark; }} }}
:root[data-theme="dark"] {{ --bg: #191919; --ink: #d4d4d4; --ink-2: #9b9b9b; --ink-3: #7f7f7f; --line: #2f2f2f; --panel: #222; --accent: #529cca;
  --red-bg: #522e2a; --red-fg: #f4b7ad; color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--font); font-size: 13.5px; line-height: 1.5; margin: 0;
  padding: 22px max(16px, env(safe-area-inset-right, 0px)) 40px max(16px, env(safe-area-inset-left, 0px)); }}
.page {{ max-width: 1080px; margin: 0 auto; }}
h1 {{ font-size: 24px; margin: 0; }} .sub {{ color: var(--ink-2); margin: 2px 0 8px; }}
.wm {{ font-size: 11.5px; color: var(--ink-2); border-left: 3px solid var(--red-bg); padding: 2px 8px; margin-bottom: 12px; }}
.wm b {{ color: var(--red-fg); }}
.wm-overlay {{ position: fixed; inset: 0; pointer-events: none; display: flex; align-items: center; justify-content: center; overflow: hidden; z-index: 40; }}
.wm-overlay span {{ transform: rotate(-30deg); font-size: clamp(18px, 3.2vw, 40px); font-weight: 700; opacity: 0.045; white-space: nowrap; }}
.hl {{ background: var(--panel); border-radius: 6px; padding: 10px 14px; }}
.hl h2 {{ font-size: 14px; margin: 0 0 4px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink-2); }}
.hl ul {{ margin: 0; padding-left: 18px; display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); column-gap: 28px; row-gap: 3px; }}
@media (max-width: 640px) {{ .hl ul {{ grid-template-columns: minmax(0, 1fr); }} }}
.toc {{ display: flex; flex-wrap: wrap; gap: 6px 16px; margin: 12px 0 4px; font-size: 13px; }}
.toc a {{ color: var(--accent); text-decoration: none; }}
article {{ border-top: 2px solid var(--ink); margin-top: 18px; padding-top: 6px; }}
article h2 {{ font-size: 18px; margin: 0; }}
.meta {{ color: var(--ink-2); margin: 2px 0 8px; font-size: 12.5px; }}
.meta a, a.src {{ color: var(--accent); }}
.cols {{ columns: 2 420px; column-gap: 28px; }}
.clause {{ break-inside: avoid; margin-bottom: 8px; }}
.clause h3 {{ font-size: 13px; margin: 6px 0 2px; border-bottom: 1px solid var(--line); padding-bottom: 2px; }}
.clause .n {{ color: var(--ink-3); font-weight: 400; }}
.clause ul {{ margin: 0; padding-left: 16px; }} .clause li {{ margin: 2px 0; }}
details {{ display: inline; }}
details summary {{ display: inline; cursor: pointer; color: var(--accent); font-size: 11.5px; list-style: none; white-space: nowrap; }}
details summary::-webkit-details-marker {{ display: none; }}
details summary::before {{ content: "§ "; }}
details[open] {{ display: block; }}
blockquote {{ margin: 4px 0; padding: 6px 10px; background: var(--panel); border-left: 3px solid var(--line); font-family: Georgia, "Times New Roman", serif;
  font-size: 12.5px; color: var(--ink); white-space: pre-wrap; }}
.note {{ color: var(--ink-2); font-size: 12px; margin-top: 18px; border-top: 1px solid var(--line); padding-top: 8px; }}
:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
@media print {{ .toc, details summary {{ display: none; }} body {{ font-size: 11px; padding: 0; }} .cols {{ columns: 2; }} }}
</style>
<div class="page">
  <div class="wm-overlay" aria-hidden="true"><span>{html.escape(SHORT)}</span></div>
  <h1>Nscale customer contracts: condensed</h1>
  <p class="sub">The two customer contracts Nscale has filed in full, summarised clause by clause. Click <b>§ Exact wording</b> beside any point for the verbatim text.</p>
  <div class="wm"><b>{html.escape(SHORT)}.</b> {html.escape(DETAIL)}</div>
  <section class="hl"><h2>Key points</h2><ul>{"".join(f"<li>{md(h)}</li>" for h in spec["highlights"])}</ul></section>
  <nav class="toc" aria-label="Contracts">{"".join(toc)}</nav>
  {"".join(body)}
  <p class="note">Summaries are condensed paraphrases; the exact wording (§) is cut directly from the exhibit as filed with the IPO registration statement (18 Sep 2026) and is authoritative. [***] marks text redacted in the filing.
  Other Nscale customer contracts (Microsoft SOWs for Ward County, Kvandal South and Sines; the North Carolina and Iceland customers; Spring; Figure; NVIDIA) are not public.
  The page is rebuilt from the tracker whenever a new filing adds or amends a contract.</p>
</div>
"""
out = ROOT / "reports" / "contract_writeup.html"
out.write_text(page)
(ROOT / "reports" / "Nscale_Contract_Writeup.html").write_text(
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n' + page)
print(f"wrote {out}: {len(spec['contracts'])} contracts, {n_quotes} verbatim quotes")
