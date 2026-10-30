"""Build reports/source_directory.html (shareable page) and reports/source_directory.csv from data/source_directory.yaml.

    python scripts/build_source_directory.py

The page lists every source by jurisdiction with access, machine access and what it gives a credit analyst,
a coverage grid (jurisdiction x what you can learn), and a company-name box that fills every search link.
The YAML is the master copy: edit it, re-run this script, republish the page.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tracker.disclaimer import AS_OF, DETAIL, SHORT  # noqa: E402
from tracker.documents import taxonomy, validate_taxonomy  # noqa: E402
from tracker.jurisdictions import ADAPTERS, UNTESTED, directory, validate_directory  # noqa: E402

problems = validate_directory() + validate_taxonomy()
if problems:
    raise SystemExit("\n".join(problems))
d = directory()
t = taxonomy()
for r in d["resources"]:
    r["live"] = "untested" if r.get("adapter") in UNTESTED else "yes" if r.get("adapter") in ADAPTERS else ""

# ---- CSV (one row per source; opens in Excel) ----
cols = ["jurisdiction", "name", "channels", "access", "api", "automation", "live", "url", "search_url", "what", "notes"]
with (ROOT / "reports" / "source_directory.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in d["resources"]:
        w.writerow({c: ", ".join(r[c]) if c == "channels" else r.get(c, "") for c in cols}
                   | {"jurisdiction": d["jurisdictions"][r["jurisdiction"]]["name"]})

payload = json.dumps({"jurisdictions": d["jurisdictions"], "channels": d["channels"], "access": d["access_levels"],
                      "resources": d["resources"], "needs": t["needs"], "documents": t["documents"],
                      "short": SHORT, "detail": DETAIL, "asOf": AS_OF},
                     ensure_ascii=False).replace("</", "<\\/")

page = """<title>European Credit Source Directory</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap">
<style>
/* Layout: one working column. Lookup box and filters first, coverage grid as the summary, then the sources by jurisdiction. */
:root {
  --bg: #11151b; --panel: #171c24; --raise: #1e2530; --line: #2a323e; --ink: #dde3ea; --ink-2: #9ba6b3; --ink-3: #6f7a88;
  --accent: #86b4e3; --accent-ink: #0d1726;
  --free: #74c69d; --free-bg: #173226; --paid: #e6b566; --paid-bg: #3a2c14; --sub: #e58f9a; --sub-bg: #3d1d23;
  --gap-bg: repeating-linear-gradient(135deg, #2a323e 0 4px, transparent 4px 8px);
  --display: "IBM Plex Sans Condensed", "Arial Narrow", system-ui, sans-serif;
  --body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
  color-scheme: dark;
}
@media (prefers-color-scheme: light) { :root:not([data-theme="dark"]) {
  --bg: #f6f7f9; --panel: #ffffff; --raise: #eef1f5; --line: #d9dee5; --ink: #1c2430; --ink-2: #4f5b69; --ink-3: #7a8592;
  --accent: #1f5f9e; --accent-ink: #ffffff;
  --free: #1d7a4b; --free-bg: #dff3e7; --paid: #8a5a0b; --paid-bg: #fbecd2; --sub: #a3283a; --sub-bg: #f9dfe3;
  --gap-bg: repeating-linear-gradient(135deg, #d9dee5 0 4px, transparent 4px 8px); color-scheme: light; } }
:root[data-theme="light"] {
  --bg: #f6f7f9; --panel: #ffffff; --raise: #eef1f5; --line: #d9dee5; --ink: #1c2430; --ink-2: #4f5b69; --ink-3: #7a8592;
  --accent: #1f5f9e; --accent-ink: #ffffff;
  --free: #1d7a4b; --free-bg: #dff3e7; --paid: #8a5a0b; --paid-bg: #fbecd2; --sub: #a3283a; --sub-bg: #f9dfe3;
  --gap-bg: repeating-linear-gradient(135deg, #d9dee5 0 4px, transparent 4px 8px); color-scheme: light; }
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--ink); font: 14px/1.5 var(--body); margin: 0; }
.page { max-width: 1120px; margin: 0 auto; padding-block: 22px 48px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 22px; }
.page > *, .panel > *, .filters > *, .needs > *, .dj > *, .doc > *, .src > *, .jur > * { min-width: 0; }
.codes, .tip, .what, .notes { overflow-wrap: anywhere; }
h1, h2, h3 { font-family: var(--display); font-weight: 600; margin: 0; text-wrap: balance; letter-spacing: 0.005em; }
h1 { font-size: 28px; line-height: 1.15; }
h2 { font-size: 15px; text-transform: uppercase; letter-spacing: 0.07em; color: var(--ink-2); }
a { color: var(--accent); }
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.sub { color: var(--ink-2); margin-top: 4px; max-width: 70ch; }
.wm { font-size: 12px; color: var(--ink-2); border-left: 3px solid var(--sub); padding: 2px 10px; margin-top: 10px; }
.wm details { margin-top: 2px; } .wm summary { cursor: pointer; color: var(--ink-3); }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; }
.lookup { display: grid; gap: 8px; }
.lookup label { font-family: var(--display); font-weight: 600; font-size: 15px; }
.lookup .row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
input[type="search"], select { font: inherit; color: var(--ink); background: var(--raise); border: 1px solid var(--line);
  border-radius: 6px; padding: 8px 10px; min-width: 0; }
#name { flex: 1 1 260px; font-size: 16px; }
.hint { color: var(--ink-2); font-size: 13px; }
.filters { display: grid; gap: 10px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font: 500 13px var(--body); color: var(--ink-2); background: transparent; border: 1px solid var(--line);
  border-radius: 999px; padding: 4px 11px; cursor: pointer; }
.chip[aria-pressed="true"] { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
.chip .code { font-family: var(--mono); font-size: 11.5px; opacity: 0.8; margin-left: 4px; }
.frow { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.seg { display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
.seg button { font: 500 13px var(--body); color: var(--ink-2); background: transparent; border: 0; padding: 6px 12px; cursor: pointer; }
.seg button + button { border-left: 1px solid var(--line); }
.seg button[aria-pressed="true"] { background: var(--raise); color: var(--ink); }
#filter { flex: 1 1 200px; }
#channel { flex: 1 1 220px; max-width: 100%; }
.count { color: var(--ink-2); font-size: 13px; font-variant-numeric: tabular-nums; }
.matrix-wrap { overflow-x: auto; }
table.matrix { border-collapse: separate; border-spacing: 3px; font-size: 12.5px; font-variant-numeric: tabular-nums; }
.matrix th { font: 500 11px var(--mono); color: var(--ink-3); text-transform: uppercase; letter-spacing: 0.04em; padding: 2px 4px;
  white-space: nowrap; text-align: center; }
.matrix th.j { text-align: left; color: var(--ink-2); font: 500 12.5px var(--body); text-transform: none; letter-spacing: 0; }
.matrix td { min-width: 42px; height: 28px; text-align: center; border-radius: 4px; cursor: pointer; border: 1px solid transparent; }
.matrix td.free { background: var(--free-bg); color: var(--free); font-weight: 600; }
.matrix td.paid { background: var(--paid-bg); color: var(--paid); font-weight: 600; }
.matrix td.gap { background: var(--gap-bg); color: var(--ink-3); font-size: 11px; }
.matrix td.none { color: var(--ink-3); }
.matrix td.on { border-color: var(--accent); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 12.5px; color: var(--ink-2); margin-top: 8px; }
.sw { display: inline-block; width: 12px; height: 12px; border-radius: 3px; vertical-align: -2px; margin-right: 5px; }
.jur { display: grid; gap: 8px; }
.jur header { display: grid; gap: 2px; border-bottom: 1px solid var(--line); padding-bottom: 6px; }
.jur h3 { font-size: 20px; }
.regimes { color: var(--ink-2); font-size: 13px; }
.regimes b { color: var(--ink); font-weight: 500; }
.src { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 16px; padding: 10px 0; border-bottom: 1px solid var(--line); }
.src:last-child { border-bottom: 0; }
.src .name { font-weight: 600; font-size: 14.5px; }
.src .name a { color: var(--ink); text-decoration: none; } .src .name a:hover { color: var(--accent); text-decoration: underline; }
.src .what { color: var(--ink); min-width: 0; }
.src .notes { color: var(--ink-2); font-size: 13px; font-style: italic; }
.src .meta { display: flex; flex-wrap: wrap; gap: 5px; align-items: center; }
.src .act { grid-column: 2; grid-row: 1 / span 3; display: flex; flex-direction: column; gap: 6px; align-items: flex-end; }
.src.isgap { background: var(--gap-bg); border-radius: 6px; padding: 10px; }
.pill { font: 500 11.5px var(--mono); border-radius: 4px; padding: 1px 7px; white-space: nowrap; border: 1px solid var(--line); color: var(--ink-2); }
.pill.free { color: var(--free); background: var(--free-bg); border-color: transparent; }
.pill.paid { color: var(--paid); background: var(--paid-bg); border-color: transparent; }
.pill.sub { color: var(--sub); background: var(--sub-bg); border-color: transparent; }
.pill.live { color: var(--accent); border-color: var(--accent); }
.tag { font-size: 12px; color: var(--ink-2); }
.btn { font: 500 13px var(--body); color: var(--accent-ink); background: var(--accent); border-radius: 6px; padding: 5px 11px;
  text-decoration: none; white-space: nowrap; }
.btn.ghost { background: transparent; color: var(--accent); border: 1px solid var(--line); }
.empty { color: var(--ink-2); padding: 20px 0; }
.needs { display: grid; gap: 12px; }
.needs .intro { color: var(--ink-2); margin: 0; max-width: 75ch; }
.dj { display: grid; gap: 4px; }
.dj h3 { font-size: 16px; color: var(--ink-2); }
.doc { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 2px 16px; padding: 8px 0; border-top: 1px solid var(--line); }
.doc .dn { font-weight: 600; }
.doc .tip { color: var(--ink); min-width: 0; }
.doc .where { color: var(--ink-2); font-size: 13px; }
.doc .codes { font: 12px var(--mono); color: var(--ink-3); }
.doc .act { grid-column: 2; grid-row: 1 / span 3; align-self: start; }
@media (max-width: 640px) { .doc { grid-template-columns: minmax(0, 1fr); } .doc .act { grid-column: 1; grid-row: auto; } }
.howto { display: grid; gap: 10px; }
.howto p { margin: 0; color: var(--ink-2); max-width: 75ch; }
.code { position: relative; }
.code pre { margin: 0; background: var(--raise); border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; overflow-x: auto;
  font: 13px/1.6 var(--mono); }
.code button { position: absolute; top: 6px; right: 6px; font: 500 12px var(--body); color: var(--ink-2); background: var(--panel);
  border: 1px solid var(--line); border-radius: 5px; padding: 3px 8px; cursor: pointer; }
@media (max-width: 640px) {
  h1 { font-size: 23px; }
  .src { grid-template-columns: minmax(0, 1fr); }
  .src .act { grid-column: 1; grid-row: auto; flex-direction: row; align-items: center; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>

<div class="page">
  <header>
    <h1>European Credit Source Directory</h1>
    <p class="sub" id="sub"></p>
    <div class="wm"><b id="short"></b><details><summary>Disclaimer</summary><span id="detail"></span></details></div>
  </header>

  <section class="panel lookup" aria-labelledby="name-label">
    <label id="name-label" for="name">Company name</label>
    <div class="row">
      <input id="name" type="search" placeholder="e.g. Nscale" autocomplete="off" spellcheck="false">
      <span class="hint" id="name-hint"></span>
    </div>
  </section>

  <section class="filters" aria-label="Filters">
    <div class="chips" id="jur-chips" role="group" aria-label="Jurisdiction"></div>
    <div class="frow">
      <div class="seg" id="access-seg" role="group" aria-label="Access">
        <button type="button" data-v="all" aria-pressed="true">All</button>
        <button type="button" data-v="free">Free</button>
        <button type="button" data-v="paid">Paid</button>
      </div>
      <select id="channel" aria-label="What you can learn"></select>
      <input id="filter" type="search" placeholder="Filter by keyword (e.g. charges, WHOA, bonds)" aria-label="Keyword filter">
      <span class="count" id="count"></span>
    </div>
  </section>

  <section class="panel" aria-labelledby="cov-h">
    <h2 id="cov-h">Coverage: what you can learn, where</h2>
    <div class="matrix-wrap"><table class="matrix" id="matrix"></table></div>
    <div class="legend">
      <span><i class="sw" style="background:var(--free-bg);outline:1px solid var(--free)"></i>number of sources, at least one free</span>
      <span><i class="sw" style="background:var(--paid-bg);outline:1px solid var(--paid)"></i>paid only</span>
      <span><i class="sw" style="background:var(--gap-bg)"></i>no public register exists</span>
      <span>Click a cell to filter.</span>
    </div>
  </section>

  <section class="panel needs" aria-labelledby="need-h">
    <h2 id="need-h">Find by need: which document answers the question</h2>
    <p class="intro">Pick a question. Each row is a document type, where to get it, and what to read in it. Codes show how the
      tracker recognises it in a feed, so <code>python -m tracker company</code> can sort a company's filings the same way.
      The jurisdiction chips above narrow this list too.</p>
    <div class="chips" id="need-chips" role="group" aria-label="Question"></div>
    <div id="need-list"></div>
  </section>

  <section id="list" aria-live="polite"></section>

  <section class="panel howto" aria-labelledby="cli-h">
    <h2 id="cli-h">Search from the tracker</h2>
    <p>Sources marked <span class="pill live">live search</span> are queried directly by the tracker. One command runs every live
      source for a jurisdiction and prints lookup links for the rest. Jurisdictions take codes or names (uk, lux, ie, nl, de, fr, es,
      it, no, se, dk, fi, eu, us) and can be combined with commas.</p>
    <div class="code"><pre id="cli1">python -m tracker search uk,lu "Nscale"</pre><button type="button" data-copy="cli1">Copy</button></div>
    <div class="code"><pre id="cli2">python -m tracker sources lu --paid</pre><button type="button" data-copy="cli2">Copy</button></div>
    <p>One company's filings sorted by question (org chart, guarantors, debt documents, security, financials, restructuring,
      lenders), by registry number, SEC CIK or LEI; and debt across a sector.</p>
    <div class="code"><pre id="cli3">python -m tracker company uk 16925886</pre><button type="button" data-copy="cli3">Copy</button></div>
    <div class="code"><pre id="cli4">python -m tracker sector data_centres --jur us,no,uk</pre><button type="button" data-copy="cli4">Copy</button></div>
  </section>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(() => {
  const D = JSON.parse(document.getElementById("data").textContent);
  const FREE = new Set(["free", "free_key", "free_limited"]);
  const ACCESS_LABEL = { free: "free", free_key: "free · key", free_limited: "free · limited", pay_per_doc: "pay per doc",
    freemium: "freemium", subscription: "subscription" };
  const AUTO_LABEL = { ok: "automatable", limited: "automate within limits", manual: "browse only" };
  const MATRIX_CH = ["registry", "accounts", "security", "land", "insolvency", "judgments", "markets", "bonds", "lenders", "state", "ownership"];
  const SHORT_CODE = { uk: "UK", ie: "IE", lu: "LU", nl: "NL", de: "DE", fr: "FR", es: "ES", it: "IT", no: "NO", se: "SE", dk: "DK",
    fi: "FI", eu: "EU", us: "US", global: "Paid & sector" };
  const jurKeys = Object.keys(D.jurisdictions);
  const state = { jur: new Set(), access: "all", channel: "", text: "", name: "", need: "guarantors" };
  const SRC = Object.fromEntries(D.resources.map((r) => [r.id, r]));
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const store = { get(k) { try { return localStorage.getItem(k) || ""; } catch { return ""; } },
                  set(k, v) { try { localStorage.setItem(k, v); } catch {} } };

  $("short").textContent = D.short;
  $("detail").textContent = D.detail;
  const nFree = D.resources.filter((r) => FREE.has(r.access) && !r.gap).length;
  const nLive = D.resources.filter((r) => r.live).length;
  $("sub").textContent = `${D.resources.filter((r) => !r.gap).length} public and paid sources for credit and restructuring work across ` +
    `${jurKeys.length - 1} jurisdictions: registers, security and land registers, insolvency notices, judgments, markets, bonds, ` +
    `lenders and state money. ${nFree} are free; ${nLive} can be searched live from the tracker. As of ${D.asOf}.`;

  // jurisdiction chips
  $("jur-chips").innerHTML = `<button type="button" class="chip" data-j="" aria-pressed="true">All</button>` +
    jurKeys.map((k) => `<button type="button" class="chip" data-j="${k}" aria-pressed="false" title="${esc(D.jurisdictions[k].name)}">` +
      `${esc(k === "global" ? "Paid & sector" : D.jurisdictions[k].name.split(" (")[0])}<span class="code">${k === "global" ? "" : esc(SHORT_CODE[k])}</span></button>`).join("");
  $("jur-chips").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    const j = b.dataset.j;
    if (!j) state.jur.clear(); else state.jur.has(j) ? state.jur.delete(j) : state.jur.add(j);
    render();
  });
  $("access-seg").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    state.access = b.dataset.v; render();
  });
  $("channel").innerHTML = `<option value="">Everything you can learn</option>` +
    Object.entries(D.channels).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join("");
  $("channel").addEventListener("change", (e) => { state.channel = e.target.value; render(); });
  $("filter").addEventListener("input", (e) => { state.text = e.target.value.trim().toLowerCase(); render(); });
  state.name = store.get("csd-name");
  $("name").value = state.name;
  $("name").addEventListener("input", (e) => { state.name = e.target.value.trim(); store.set("csd-name", state.name); renderList(); renderNeeds(); hint(); });

  const isPaid = (r) => !FREE.has(r.access);
  const pillClass = (r) => r.access === "subscription" ? "sub" : isPaid(r) ? "paid" : "free";
  const matches = (r, ignoreChannel) =>
    (!state.jur.size || state.jur.has(r.jurisdiction)) &&
    (state.access === "all" || (state.access === "free" ? !isPaid(r) : isPaid(r))) &&
    (ignoreChannel || !state.channel || r.channels.includes(state.channel)) &&
    (!state.text || [r.name, r.what, r.notes, r.channels.join(" "), D.jurisdictions[r.jurisdiction].regimes].join(" ").toLowerCase().includes(state.text));
  const searchUrl = (r) => r.search_url && state.name ? r.search_url.replace("{q}", encodeURIComponent(state.name)) : "";

  function hint() {
    const n = D.resources.filter((r) => r.search_url).length;
    $("name-hint").textContent = state.name
      ? `Search links below now look up "${state.name}" (${n} sources take a name directly).`
      : `Type a name to turn ${n} sources into one-click searches.`;
  }

  function renderMatrix() {
    const rows = jurKeys.filter((k) => k !== "global");
    let h = `<thead><tr><th class="j" scope="col">Jurisdiction</th>${MATRIX_CH.map((c) => `<th scope="col" title="${esc(D.channels[c])}">${c}</th>`).join("")}</tr></thead><tbody>`;
    for (const k of rows) {
      h += `<tr><th class="j" scope="row">${esc(D.jurisdictions[k].name.split(" (")[0])}</th>`;
      for (const c of MATRIX_CH) {
        const rs = D.resources.filter((r) => r.jurisdiction === k && r.channels.includes(c));
        const real = rs.filter((r) => !r.gap);
        const cls = real.length ? (real.some((r) => !isPaid(r)) ? "free" : "paid") : rs.length ? "gap" : "none";
        const label = real.length ? real.length : rs.length ? "none" : "·";
        const on = state.jur.size === 1 && state.jur.has(k) && state.channel === c ? " on" : "";
        h += `<td class="${cls}${on}" data-j="${k}" data-c="${c}" title="${esc(D.jurisdictions[k].name)}: ${esc(D.channels[c])}">${label}</td>`;
      }
      h += "</tr>";
    }
    $("matrix").innerHTML = h + "</tbody>";
  }
  $("matrix").addEventListener("click", (e) => {
    const td = e.target.closest("td"); if (!td) return;
    state.jur = new Set([td.dataset.j]); state.channel = td.dataset.c; $("channel").value = td.dataset.c;
    render();
    $("list").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  });

  function srcHtml(r) {
    const s = searchUrl(r);
    const act = [
      s ? `<a class="btn" href="${esc(s)}" target="_blank" rel="noopener">Search “${esc(state.name)}” ↗</a>` : "",
      `<a class="btn ghost" href="${esc(r.url)}" target="_blank" rel="noopener">Open ↗</a>`,
    ].join("");
    const meta = r.gap ? "" : [
      `<span class="pill ${pillClass(r)}">${esc(ACCESS_LABEL[r.access])}</span>`,
      `<span class="pill">${esc(r.api)}</span>`,
      `<span class="pill">${esc(AUTO_LABEL[r.automation])}</span>`,
      r.live ? `<span class="pill live">${r.live === "untested" ? "live search (untested)" : "live search"}</span>` : "",
      `<span class="tag">${r.channels.map(esc).join(" · ")}</span>`,
    ].join("");
    return `<div class="src${r.gap ? " isgap" : ""}">
      <div class="name"><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.name)}</a></div>
      <div class="act">${act}</div>
      <div class="what">${esc(r.what)}</div>
      ${meta ? `<div class="meta">${meta}</div>` : ""}
      ${r.notes ? `<div class="notes">${esc(r.notes)}</div>` : ""}
    </div>`;
  }

  function renderList() {
    const shown = D.resources.filter((r) => matches(r));
    $("count").textContent = `${shown.filter((r) => !r.gap).length} of ${D.resources.filter((r) => !r.gap).length} sources`;
    if (!shown.length) { $("list").innerHTML = `<p class="empty">No source matches these filters. Clear a filter or pick another jurisdiction.</p>`; return; }
    $("list").innerHTML = jurKeys.filter((k) => shown.some((r) => r.jurisdiction === k)).map((k) => {
      const j = D.jurisdictions[k];
      return `<section class="jur panel" aria-labelledby="j-${k}"><header><h3 id="j-${k}">${esc(j.name)}</h3>
        ${j.regimes ? `<div class="regimes"><b>Restructuring regimes:</b> ${esc(j.regimes)}</div>` : ""}</header>
        <div>${shown.filter((r) => r.jurisdiction === k).map(srcHtml).join("")}</div></section>`;
    }).join("");
  }

  $("need-chips").innerHTML = Object.entries(D.needs).map(([k, v]) =>
    `<button type="button" class="chip" data-n="${k}" aria-pressed="false" title="${esc(v)}">${esc(v.split(" (")[0])}</button>`).join("");
  $("need-chips").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    state.need = b.dataset.n; renderNeeds();
  });

  function renderNeeds() {
    document.querySelectorAll("#need-chips .chip").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.n === state.need)));
    const docs = D.documents.filter((d) => d.needs.includes(state.need) && (!state.jur.size || state.jur.has(d.jurisdiction)));
    if (!docs.length) { $("need-list").innerHTML = `<p class="empty">No document type for this question in the chosen jurisdictions yet.</p>`; return; }
    $("need-list").innerHTML = `<p class="intro">${esc(D.needs[state.need])}</p>` + jurKeys.filter((k) => docs.some((d) => d.jurisdiction === k)).map((k) =>
      `<div class="dj"><h3>${esc(D.jurisdictions[k].name.split(" (")[0])}</h3>${docs.filter((d) => d.jurisdiction === k).map((d) => {
        const r = SRC[d.source] || { name: d.source, url: "#", access: "" };
        const s = searchUrl(r);
        const codes = Object.entries(d.match || {}).map(([kk, v]) => `${kk.replace("_", " ")}: ${v.join(", ")}`).join(" · ");
        return `<div class="doc"><div class="dn">${esc(d.name)}</div>
          <div class="act"><a class="btn ${s ? "" : "ghost"}" href="${esc(s || r.url)}" target="_blank" rel="noopener">${s ? `Search “${esc(state.name)}”` : "Open"} ↗</a></div>
          <div class="tip">${esc(d.tip)}</div>
          <div class="where">From ${esc(r.name)} <span class="pill ${pillClass(r)}">${esc(ACCESS_LABEL[r.access] || "")}</span></div>
          ${codes ? `<div class="codes">${esc(codes)}</div>` : ""}</div>`;
      }).join("")}</div>`).join("");
  }

  function render() {
    document.querySelectorAll("#jur-chips .chip").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.j ? state.jur.has(b.dataset.j) : state.jur.size === 0)));
    document.querySelectorAll("#access-seg button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === state.access)));
    renderMatrix(); renderList(); renderNeeds();
  }

  document.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", () => {
    const pre = $(b.dataset.copy);
    const done = () => { b.textContent = "Copied"; setTimeout(() => (b.textContent = "Copy"), 1500); };
    navigator.clipboard?.writeText(pre.textContent).then(done, () => {
      const range = document.createRange(); range.selectNodeContents(pre);
      const sel = getSelection(); sel.removeAllRanges(); sel.addRange(range); b.textContent = "Selected: press Ctrl/Cmd+C";
    });
  }));

  hint(); render();
})();
</script>
"""
out = ROOT / "reports" / "source_directory.html"
out.write_text(page.replace("__DATA__", payload))
print(f"wrote {out.relative_to(ROOT)} and reports/source_directory.csv ({len(d['resources'])} sources)")
