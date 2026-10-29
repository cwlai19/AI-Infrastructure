"""One-off: site-level facts needed for the site map (capacity, activity, revenue location)."""
import csv
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
OBS = "2026-10-29"
G = "group_nscale"
sources = [
    ("src_news_kaiku_glomfjord", "news", "Kaiku (summarising Bloomberg, 15 Oct 2026)", "Nscale's AI data center in Glomfjord, Norway, is six months late",
     "https://kaiku.news/en/tech/nscale-glomfjord-data-center-delay", "2026-10-16"),
    ("src_news_whitefiber_q2call", "news", "Nasdaq (WhiteFiber Q2 2026 earnings call highlights)", "WhiteFiber Q2 earnings call highlights",
     "https://www.nasdaq.com/articles/whitefiber-q2-earnings-call-highlights", "2026-08-12"),
    ("src_news_certifiedstrategic", "news", "Certified Strategic", "Anthropic in talks for a second US$45bn Nscale deal",
     "https://certifiedstrategic.com/insights/anthropic-second-45bn-nscale-deal-microsoft-loughton", "2026-10-20"),
    ("src_news_tu_nve", "news", "Teknisk Ukeblad (TU.no)", "NVE gir Nscale varsel om tvangsmulkt",
     "https://www.tu.no/energi/nve-gir-nscale-varsel-om-tvangsmulkt/7141373", "2026-09-29"),
    ("src_news_wchs_dep", "news", "WCHS", "DEP issues enforcement order for Mason County data center site over stormwater violations",
     "https://wchstv.com/news/local/dep-issues-enforcement-order-for-mason-county-data-center-site-for-stormwater-violations", "2026-07"),
    ("src_news_echelon_monarch", "news", "Echelon Reports", "Monarch Compute Campus: phase-one contractors and job routes",
     "https://echelonreports.com/monarch-compute-campus-phase-one-contractors-jobs/", "2026-10"),
    ("src_news_powermag_texas", "news", "Power Magazine", "Abbott orders full audit of Texas data center interconnection queue",
     "https://powermag.com/abbott-orders-full-audit-of-texas-data-center-interconnection-queue-threatens-to-deny-grid-access/", "2026-08"),
]
entities = [("site_sin01", "site", "SINES Data Campus, first building (Portugal)", "Colocation at Start Campus.")]
rows = []


def add(entity, prop, value, source, unit="", effective="", method="reported", note="", locator="Article text"):
    rows.append(dict(entity=entity, property=prop, value=value, unit=unit, source=source, locator=locator,
                     effective_date=effective, observed_date=OBS, method=method, derived_from="",
                     extractor="manual:claude-site-facts", note=note))


S1 = "src_s1_full"
add(G, "revenue_share_by_country_6m", "Portugal 52%; Norway 45% (six months to 30 June 2026)", S1, method="disclosed",
    locator="Risk factors: international operations", effective="2026-06-30")
add("site_sin01", "group", G, S1, method="disclosed", locator="Business: acquisitions (SIN02)")
add("site_sin01", "name", "SINES Data Campus, first building", S1, method="disclosed", locator="Business: acquisitions (SIN02)")
add("site_sin01", "country", "Portugal", S1, method="disclosed", locator="Business: acquisitions (SIN02)")
add("site_sin01", "ownership", "colocation", S1, method="estimated", locator="Business: acquisitions (SIN02)",
    note="SIN02 is described as owned; the first building is Start Campus's, so Nscale's deployment there is assumed to be colocation.")
add("site_sin01", "gpus_deployed", "12600", S1, "GPUs", method="disclosed", locator="Business: acquisitions (SIN02)",
    note="'deployment of over 12,600 NVIDIA Grace Blackwell Ultra GPUs at the first building of the SINES Data Campus for Microsoft'.")
add("site_sin01", "construction_status", "Active: GPUs deployed for Microsoft; Portugal was 52% of H1 2026 revenue", S1, method="disclosed",
    locator="Business; risk factors")
add("site_sin02", "construction_status", "Development: Microsoft deployment of 66,000+ Vera Rubin NVL72 GPUs starting late 2027", S1,
    method="disclosed", locator="Business: acquisitions")
add("site_sin02", "gpus_deployed", "0", S1, "GPUs", method="estimated", locator="Business: acquisitions", note="Deployment starts late 2027.")
GL = "src_news_kaiku_glomfjord"
add("site_glomfjord", "mw_contracted", "30", GL, "MW", "2026-10-15")
add("site_glomfjord", "mw_energized", "6.4", GL, "MW", "2026-10-15", note="About six months behind schedule (Bloomberg).")
add("site_glomfjord", "construction_status", "Live but ~6 months late: repeated liquid-cooling leaks, Dec 2025 transformer fire (10 safety violations, case closed Sept 2026), diesel generators until May; delay penalties reportedly owed", GL, effective="2026-10-15")
add("site_glomfjord", "ownership", "owned", S1, method="estimated", locator="Cash flows: refurbishment of our data center in Glomfjord", note="'our data center in Glomfjord'.")
add("site_north_carolina", "mw_energized", "20", "src_news_whitefiber_q2call", "MW", "2026-08-12",
    note="~20 MW available for Nscale to install and test; full 40 MW at run-rate billing targeted for end-August (not confirmed).")
add("site_north_carolina", "construction_status", "Ramp delayed by switchgear delivery and commissioning; WhiteFiber says resolved, full 40 MW billing targeted end-Aug 2026", "src_news_whitefiber_q2call", effective="2026-08-12")
add("site_monarch", "mw_contracted", "460", "src_news_certifiedstrategic", "MW", "2026-08-25", note="First Anthropic building; a second 460 MW building is in talks.")
add("site_monarch", "energization_target_date", "2028-03", "src_news_echelon_monarch", note="Phase one 'early 2028'; an earlier report said January 2027.")
add("site_monarch", "construction_status", "Pre-construction / early works: DEP stormwater enforcement order (July 2026); air permits for the on-site 2,160 MW gas plant refiled; public hearings and preservation dispute (Oct 2026)", "src_news_wchs_dep", effective="2026-10")
add("site_kvandal_south", "construction_status", "Under construction; NVE notice of coercive fine unless waste-heat analysis delivered by 15 Nov 2026; target completion 5 Apr 2027", "src_news_tu_nve", effective="2026-09-29")
add("site_ward_county", "construction_status", "Leased powered site (234 MW); Texas audit of ERCOT large-load queue affects Ionic's 466 MW expansion and Nscale's +89 MW option", "src_news_powermag_texas", effective="2026-08")
add("site_borealis", "construction_status", "Colocation; service must commence by 27 Jan 2027 under the Macquarie facility (per CCIR)", "src_ccir_nscale_full", locator="Instrument card: Iceland")
add("site_loughton", "construction_status", "Microsoft terminated (Oct 2026); grid capacity not until early-to-mid 2030s", "src_news_techtarget_1019", effective="2026-10-18")


def append(path, fieldnames, items):
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fieldnames).writerows(items)


append(REPO / "data/sources.csv", ["id", "type", "access", "publisher", "title", "url", "published_date", "retrieved_date", "note"],
       [dict(id=i, type=t, access="excerpt", publisher=p, title=ti, url=u, published_date=d, retrieved_date=OBS,
             note="Read via search excerpt or summary of the original.") for i, t, p, ti, u, d in sources])
append(REPO / "data/entities.csv", ["id", "type", "label", "note"], [dict(id=a, type=b, label=c, note=d) for a, b, c, d in entities])
fields = ["id", "entity", "property", "value", "unit", "source", "locator", "effective_date", "observed_date",
          "method", "derived_from", "extractor", "note"]
append(REPO / "data/statements.csv", fields, [dict(id=f"st{3900 + n:04d}", **r) for n, r in enumerate(rows)])
print(len(rows), "statements")
