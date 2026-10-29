"""Build reports/site_map.html: an interactive map of a group's sites from the tracker.

Every number comes from resolve() on the statements, so it carries its grade and source.
Coordinates, loan-to-site mapping and construction-risk ratings come from data/site_overlay.yaml.
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tracker.model import load, parse_number, resolve  # noqa: E402
from tracker.report import _label, _value  # noqa: E402

GROUP = "group_nscale"
store = load()
overlay = yaml.safe_load((ROOT / "data" / "site_overlay.yaml").read_text())


def src_of(st):
    s = store.sources[st.source]
    return {"id": st.id, "grade": st.grade, "source": s["title"], "publisher": s.get("publisher", ""),
            "url": s.get("url", ""), "date": st.effective_date, "method": st.method, "note": st.note}


def fact(entity, prop):
    """Resolved value of one property: {status, value, number, ...source}."""
    r = resolve(store, entity, prop)
    if r.status in ("not_checked", "undisclosed"):
        return {"status": r.status}
    shown = r.current if r.status == "multi" else r.current[:1]
    out = {"status": r.status, "disputed": bool(r.conflicts),
           "values": [dict(text=_value(store, s), number=parse_number(s.value) if s.unit else None, unit=s.unit, **src_of(s))
                      for s in shown]}
    out["text"] = "; ".join(v["text"] for v in out["values"])
    out["number"] = out["values"][0]["number"]
    out["grade"] = min(v["grade"] for v in out["values"])
    return out


def facility(fid):
    return {"id": fid, "name": _label(store, fid),
            **{k: fact(fid, k) for k in ("amount_max", "amount_drawn", "carrying_value", "margin_bps", "maturity_date",
                                          "status", "lender", "named_customer", "borrower", "facility_type")}}


def contracts_for(site_id):
    out = []
    for e, ent in store.entities.items():
        if ent["type"] != "contract":
            continue
        sites = resolve(store, e, "site")
        if any(s.value == site_id or store.canonical.get(s.value) == store.canonical.get(site_id) for s in sites.current):
            out.append({"id": e, "name": _label(store, e),
                        **{k: fact(e, k) for k in ("customer", "value_total", "status", "gpu_count", "gpu_type", "mw",
                                                    "take_or_pay", "financing_status")}})
    return out


sites = []
for sid, ov in overlay["sites"].items():
    sites.append({
        "id": sid, "label": ov["label"], "lat": ov["lat"], "lon": ov["lon"], "region": ov["region"],
        "risk": ov["risk"], "drivers": ov["drivers"], "label_dy": ov.get("label_dy", 4),
        **{k: fact(sid, k) for k in ("country", "ownership", "landlord", "operator", "mw_contracted", "mw_energized",
                                      "gpus_deployed", "energization_target_date", "construction_status", "location")},
        "facilities": [facility(f) for f in ov.get("facilities", [])],
        "contracts": contracts_for(sid),
    })

group = {k: fact(GROUP, k) for k in ("mw_contracted_total", "tcv_active", "tcv_active_and_contracted", "gpus_active",
                                     "gpus_active_and_contracted", "sites_active", "sites_contracted", "revenue_6m",
                                     "revenue_share_by_country_6m", "total_debt", "cash_and_equivalents")}
corporate = [dict(facility(f), why=why) for f, why in overlay["corporate_facilities"].items()]


def sites_of(contract):
    canon = {store.canonical.get(sid, sid): sid for sid in overlay["sites"]}
    return sorted({canon[store.canonical.get(x.value, x.value)] for x in resolve(store, contract, "site").current
                   if store.canonical.get(x.value, x.value) in canon})


CONTRACT_PROPS = ("value_total", "status", "take_or_pay", "start_date", "end_date", "term_months", "termination_rights",
                  "extension_rights", "financing_status", "gpu_count", "gpu_type")
customers = []
for cid, ov in overlay["customers"].items():
    ctrs = [e for e, ent in store.entities.items() if ent["type"] == "contract"
            and any(store.canonical.get(x.value, x.value) == store.canonical.get(cid, cid) for x in resolve(store, e, "customer").current)]
    customers.append({"id": cid, "name": _label(store, cid), "read": ov["read"], "headline": ov["headline"],
                      "sites": sorted({x for c in ctrs for x in sites_of(c)}),
                      "contracts": [{"id": c, "name": _label(store, c), "sites": sites_of(c), **{k: fact(c, k) for k in CONTRACT_PROPS}}
                                    for c in ctrs]})

LEASE_PROPS = ("lease_type", "mw", "start_date", "term_months", "guarantor", "guarantee_amount", "guarantee_term",
               "escrow_amount", "expansion_obligation", "landlord_revenue_6m")
upstream = []
for sid, ov in overlay["upstream"].items():
    cp = ov.get("counterparty")
    upstream.append({"site": sid, "read": ov["read"],
                     **{k: fact(sid, k) for k in ("ownership", "landlord", "acquisition_cost", "deferred_consideration_outstanding")},
                     "counterparty": cp and {"id": cp, "name": _label(store, cp), "dependency": fact(cp, "dependency")},
                     "lease": ov.get("lease") and {"id": ov["lease"], "name": _label(store, ov["lease"]),
                                                   **{k: fact(ov["lease"], k) for k in LEASE_PROPS}}})
# Landlord-side subsidiaries whose revenue depends on Nscale (e.g. KiNRG at Ward County).
for e in ("le_kinrg",):
    for u in upstream:
        if u["site"] == "site_ward_county":
            u["supplier"] = {"id": e, "name": _label(store, e), "dependency": fact(e, "dependency")}
group_lease = {k: fact(GROUP, k) for k in ("operating_lease_liabilities", "leases_not_commenced", "largest_customer_revenue_share",
                                          "deferred_revenue", "weighted_avg_contract_years")}

APAC = ("Singapore", "Malaysia", "Japan", "Indonesia", "South Korea")
apac = {}
for st in store.statements:
    if st.property == "jurisdiction" and st.source == "src_ex21" and st.value in APAC:
        apac[st.value] = apac.get(st.value, 0) + 1
asia = {"entities": sum(apac.values()),
        "breakdown": ", ".join(f"{k} {v}" for k, v in sorted(apac.items(), key=lambda kv: -kv[1])),
        "grade": "A", "source": store.sources["src_ex21"]["title"]}

geo_dir = Path(sys.argv[1])
data = {"as_of": "2026-10-29", "rated_by": overlay["rated_by"], "rated_date": overlay["rated_date"],
        "group": group, "asia": asia, "sites": sites, "corporate": corporate,
        "customers": customers, "upstream": upstream, "group_lease": group_lease}
template = (ROOT / "reports" / "site_map_template.html").read_text()
# Email copy: map outlines load from the web when opened, so the file stays small.
lite = ROOT / "reports" / "Nscale_Site_Map.html"
lite.write_text("<!doctype html><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
                + template.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"))))
# Published copy: outlines embedded (the artifact page cannot fetch them).
data["geo"] = {"world": json.loads((geo_dir / "countries-50m.json").read_text()),
               "us": json.loads((geo_dir / "states-10m.json").read_text())}
out = ROOT / "reports" / "site_map.html"
out.write_text(template.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"))))
print(f"wrote {out} ({out.stat().st_size // 1024} KB) and {lite.name} ({lite.stat().st_size // 1024} KB): "
      f"{len(sites)} sites, {len(customers)} customers, {len(corporate)} corporate facilities")
