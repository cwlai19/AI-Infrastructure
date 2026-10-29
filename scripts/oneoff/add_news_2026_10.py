"""One-off: Microsoft's Loughton termination and the reported second Anthropic deal (news, 17-20 Oct 2026)."""
import csv
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
OBS = "2026-10-29"
G = "group_nscale"
sources = [
    ("src_news_siliconangle_1018", "SiliconANGLE (citing The Telegraph)", "Nscale's IPO plans could be at risk after Microsoft cancels UK data center project",
     "https://siliconangle.com/2026/10/18/neocloud-operator-nscales-ipo-plans-could-be-at-risk-after-microsoft-pulls-the-plug-on-u-k-data-center-project/", "2026-10-18"),
    ("src_news_techtarget_1019", "TechTarget (citing The Guardian)", "Microsoft's Nscale exit exposes $103B AI contract pipeline risk",
     "https://www.techtarget.com/it-infrastructure/news/366652477/Microsofts-Nscale-exit-exposes-103B-AI-contract-pipeline-risk", "2026-10-19"),
    ("src_news_techtimes_1019", "Tech Times (citing Reuters)", "Microsoft Exits Nscale's UK Flagship as Grid Can't Supply Power Until 2030s",
     "https://www.techtimes.com/articles/329207/20261019/microsoft-exits-nscales-uk-flagship-grid-cant-supply-power-until-2030s-ipo-risk.htm", "2026-10-19"),
    ("src_news_fool_1020", "The Motley Fool (citing CNBC)", "Anthropic Is in Talks for Another $45 Billion AI Deal",
     "https://www.fool.com/investing/2026/10/20/anthropic-is-in-talks-for-another-45-billion-ai-deal-nvidia-could-be-a-big-winner/", "2026-10-20"),
]
entities = [
    ("site_loughton", "site", "Loughton, Essex (UK)", ""),
    ("ctr_msft_loughton", "contract", "Microsoft: Loughton (UK) GPU contract", ""),
    ("ctr_anthropic_2", "contract", "Anthropic: proposed second Monarch building (~$45B, in talks)", ""),
]
links = [("ctr_msft_loughton", "part_of", "ctr_msft_sows",
          "Loughton was announced in Sept 2025 as one of four sites under the Microsoft agreements (with Texas, Portugal, Norway), so it sits inside the S-1's 'up to $43.8B'. Its value is not disclosed.")]
rows = []


def add(entity, prop, value, source, unit="", effective="", method="reported", note=""):
    rows.append(dict(entity=entity, property=prop, value=value, unit=unit, source=source, locator="Article text",
                     effective_date=effective, observed_date=OBS, method=method, derived_from="",
                     extractor="manual:claude-news", note=note))


SA, TT, TM, FO = "src_news_siliconangle_1018", "src_news_techtarget_1019", "src_news_techtimes_1019", "src_news_fool_1020"
add("site_loughton", "group", G, SA)
add("site_loughton", "country", "United Kingdom", SA)
add("site_loughton", "location", "Loughton, Essex", SA)
add("site_loughton", "mw_contracted", "50", SA, "MW", "2025-09", note="Initial 50 MW, expandable to 90 MW.")
add("site_loughton", "energization_target_date", "2027-03", SA, note="Planned 23,040 GPUs by Q1 2027.")
add("site_loughton", "grid_connection_date", "2033", TM, method="estimated",
    note="UK Power Networks told Nscale capacity would not be available until the early-to-mid 2030s (Guardian/Telegraph via TechTarget, Tech Times).")
add("ctr_msft_loughton", "group", G, SA)
add("ctr_msft_loughton", "customer", "le_microsoft", SA)
add("ctr_msft_loughton", "provider", G, SA)
add("ctr_msft_loughton", "site", "site_loughton", SA)
add("ctr_msft_loughton", "gpu_count", "23040", TT, "GPUs")
add("ctr_msft_loughton", "gpu_type", "GB300", TT)
add("ctr_msft_loughton", "mw", "50", SA, "MW")
add("ctr_msft_loughton", "status", "signed", SA, effective="2025-09")
add("ctr_msft_loughton", "status", "terminated", TT, effective="2026-10-18",
    note="Microsoft terminated after the grid delay; confirmed by an Nscale spokesperson. Microsoft: 'This decision relates to a single site.' Nscale: no impact on other Microsoft contracts.")
add("ctr_msft_loughton", "value_total", "", TT, method="checked_absent", note="'The companies have not disclosed the financial consequences of the termination.'")
add("ctr_msft_sows", "status", "active", TT, effective="2026-10-18",
    note="Other Microsoft sites (Texas, Portugal, Norway) reported unaffected. The S-1's 'up to $43.8B' includes Loughton, so it is now overstated by an undisclosed amount.")
add("ctr_anthropic_2", "group", G, FO)
add("ctr_anthropic_2", "customer", "le_anthropic", FO)
add("ctr_anthropic_2", "provider", G, FO)
add("ctr_anthropic_2", "site", "site_monarch", FO)
add("ctr_anthropic_2", "mw", "460", FO, "MW", note="Second building at Monarch, Vera Rubin GPUs; right of first refusal on a planned third building.")
add("ctr_anthropic_2", "gpu_type", "NVIDIA Vera Rubin", FO)
add("ctr_anthropic_2", "value_total", "45B", FO, "USD", "2026-10-20", note="'roughly $45 billion' per CNBC's source; not signed; Anthropic declined to comment.")
add("ctr_anthropic_2", "status", "in_negotiation", FO, effective="2026-10-20")
add("ctr_anthropic_2", "financing_status", "not_secured", FO, method="estimated",
    note="No financing reported; financing for the first Anthropic agreement was itself not secured at the S-1 date.")
add("ctr_anthropic", "status", "signed", "src_anthropic_s1", effective="2026-08", method="disclosed")


def append(path, fieldnames, items):
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fieldnames).writerows(items)


append(REPO / "data/sources.csv", ["id", "type", "access", "publisher", "title", "url", "published_date", "retrieved_date", "note"],
       [dict(id=i, type="news", access="full_document", publisher=p, title=t, url=u, published_date=d, retrieved_date=OBS, note="")
        for i, p, t, u, d in sources])
append(REPO / "data/entities.csv", ["id", "type", "label", "note"], [dict(id=a, type=b, label=c, note=d) for a, b, c, d in entities])
append(REPO / "data/entity_links.csv", ["entity_a", "relation", "entity_b", "judged_by", "judged_date", "note"],
       [dict(entity_a=a, relation=r, entity_b=b, judged_by="claude (pending analyst review)", judged_date=OBS, note=n) for a, r, b, n in links])
fields = ["id", "entity", "property", "value", "unit", "source", "locator", "effective_date", "observed_date",
          "method", "derived_from", "extractor", "note"]
append(REPO / "data/statements.csv", fields, [dict(id=f"st{3800 + n:04d}", **r) for n, r in enumerate(rows)])
print(f"{len(rows)} statements")
