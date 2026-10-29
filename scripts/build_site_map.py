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

geo_dir = Path(sys.argv[1])
data = {"as_of": "2026-10-29", "rated_by": overlay["rated_by"], "rated_date": overlay["rated_date"],
        "group": group, "sites": sites, "corporate": corporate,
        "geo": {"world": json.loads((geo_dir / "countries-50m.json").read_text()),
                "us": json.loads((geo_dir / "states-10m.json").read_text())}}
template = (ROOT / "reports" / "site_map_template.html").read_text()
out = ROOT / "reports" / "site_map.html"
out.write_text(template.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"))))
print(f"wrote {out} ({out.stat().st_size // 1024} KB): {len(sites)} sites, {len(corporate)} corporate facilities")
