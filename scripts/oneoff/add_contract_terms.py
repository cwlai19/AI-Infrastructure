"""One-off: what happens if a campus is late or a customer walks. Read from the customer contracts (Ex-10.19, Ex-10.25)
and the credit agreements (Ex-10.12, 10.14, 10.18, 10.21, 10.22, 10.23, 10.24). Locators are clause numbers."""
import csv
import sys
from pathlib import Path

REPO = Path(sys.argv[1])
OBS = "2026-10-29"
EDGAR = "https://www.sec.gov/Archives/edgar/data/2110365/000119312526395475/"
sources = [("src_ex10_19", "Ex-10.19 Microsoft Partner Statement of Work (Kvandal North, Narvik; Nscale Ventures Holdings Norway AS)",
            EDGAR + "ck0002110365-ex10_19.htm")]
entities = [
    ("site_kvandal_north", "site", "Kvandal North, Narvik (Norway)", "Microsoft SOW site (Ex-10.19); separate from Kvandal South."),
    ("ctr_msft_kvandal_north", "contract", "Microsoft SOW: Kvandal North (VR200, 6 years)", "Filed as Ex-10.19; tranche sizes and prices redacted."),
]
rows = []


def add(entity, prop, value, source, locator, method="disclosed", unit="", effective="", note=""):
    rows.append(dict(entity=entity, property=prop, value=value, unit=unit, source=source, locator=locator,
                     effective_date=effective, observed_date=OBS, method=method, derived_from="",
                     extractor="manual:claude-contract-terms", note=note))


# ---- Kvandal North site and its Microsoft SOW (Ex-10.19) ----
M = "src_ex10_19"
add("site_kvandal_north", "group", "group_nscale", M, "§1.1 GPU Services")
add("site_kvandal_north", "name", "Kvandal North", M, "§1.1 GPU Services")
add("site_kvandal_north", "country", "Norway", M, "§1.1 GPU Services")
add("site_kvandal_north", "location", "Nordmoveien 301, 8530 Bjerkvik, Narvik", M, "§1.1 GPU Services")
K = "ctr_msft_kvandal_north"
add(K, "group", "group_nscale", M, "Cover page")
add(K, "name", "Microsoft SOW: Kvandal North (VR200, 6 years)", M, "Cover page")
add(K, "customer", "le_microsoft", M, "Cover page", note="Signed by Microsoft Ireland Operations Limited.")
add(K, "site", "site_kvandal_north", M, "§1.1 GPU Services")
add(K, "gpu_type", "NVIDIA VR200 (Vera Rubin)", M, "Table 1")
add(K, "term_months", "72", M, "Table 1", unit="months", note="Six years per tranche from Acceptance.")
add(K, "status", "signed", M, "Cover page")
add(K, "extension_rights", "Microsoft may extend each tranche by up to 6 months at Year-6 pricing", M, "§1.1(b)")
add(K, "payment_start", "Billing starts the day after Microsoft accepts each tranche", M, "§3.4(b)(iii); §2 Acceptance")
add(K, "upfront_payment", "Upfront payment of a redacted share of each tranche's value: part 15 days after signing, the rest up to 90 days before delivery", M, "§3.2 Upfront Payment")
add(K, "delay_remedy", "Credit of 100% of the daily bill for every day late, set off against the first invoices after acceptance", M, "§3.3(a)")
add(K, "delay_remedy", "No delay credits for delays caused directly by NVIDIA, if Nscale showed binding orders within 60 days of signing and gave 45 days' notice; the term is then extended", M, "§3.3(h)")
add(K, "delay_termination", "If a tranche is not accepted within 60 days of its delivery date, Microsoft may terminate that tranche or set a new date; missing the new date terminates it automatically", M, "§3.3(b)-(c)")
add(K, "delay_termination", "On a late-delivery termination Nscale refunds that tranche's share of the upfront payment within 60 days; this is Microsoft's sole remedy", M, "§3.3(d)")
add(K, "termination_rights", "For cause: material breach not cured within 60 days, or insolvency/cessation of business", M, "§6.10 (Clause 14)")
add(K, "termination_rights", "Change of control to Amazon, Google, Tencent or Alibaba: Microsoft may terminate within 30 days", M, "§26.c")
add(K, "force_majeure", "Neither party liable during force majeure; hardware failures and hardware-supplier delays are not force majeure", M, "Clause 27A")
add(K, "lender_step_in", "Nscale must give Microsoft step-in rights when financing or colocation for the site closes", M, "§2(c) Step-in right")
add("ctr_msft_sows", "take_or_pay", "false", M, "§3.3; §3.4(b)(iii)", method="estimated",
    note="Read from the one Microsoft SOW filed (Kvandal North): fees start only after acceptance and late tranches can be cancelled. Once accepted, fees are fixed for 6 years and terminable only for cause. Other SOWs not filed.")

# ---- Anthropic Services Agreement, tranche 1 at Monarch (Ex-10.25) ----
A, C = "src_ex10_25", "ctr_anthropic"
add(C, "payment_start", "No fees until Anthropic accepts the whole tranche; then GPU-hours x price, less credits and discounts", A, "Order §5; Terms §3.2")
add(C, "delay_remedy", "Late tranche: no fees during the delay; after a grace period, a late-delivery discount on fees for as many days as the delay (rates redacted)", A, "Order §6(a)-(c)")
add(C, "delay_remedy", "Anthropic may also shorten the tranche term by delay beyond a redacted threshold", A, "Order §5 (Tranche Term)")
add(C, "delay_termination", "After a further redacted delay Anthropic may terminate the tranche with no payment or liability", A, "Order §6(d)")
add(C, "delay_termination", "Supply-chain (component) delays are excused only if Nscale showed binding GPU orders early and gave notice; excused delay beyond a cap counts again", A, "Order §6 Excused Delays")
add(C, "financing_condition", "Nscale must secure GPU and data-centre financing by a redacted longstop date; if not, either party may cancel with no liability. Until then Nscale may not offer the site's capacity to anyone else", A, "Order §9(a), (c), (d)")
add(C, "force_majeure", "Force majeure excuses performance but not Anthropic's payment for services received; Anthropic stops paying for affected services and may terminate them if it lasts beyond a redacted period", A, "Terms §12.7")
add(C, "force_majeure", "A government order suspending the service also suspends Anthropic's payments", A, "Terms §5.2(c)")
add(C, "termination_rights", "Anthropic may terminate immediately if the provider stops being controlled by Nscale", A, "Order §1(c); Terms §5.3(c)")
add(C, "lender_step_in", "Anthropic will negotiate direct agreements with Nscale's lenders (notice, cure, standstill, step-in, payment direction) only as mutually agreed; all four tranches must stay operated together", A, "Terms §12.18; Order §1(c)")

# ---- Credit agreements ----
W = "src_ex10_23"
add("fac_ward_county", "if_customer_terminates", "Whole Microsoft contract terminated, suspended or in terminable default = event of default", W, "§7.01(m)")
add("fac_ward_county", "if_customer_terminates", "One tranche cancelled for non-acceptance: repay that tranche's loans within 60 days (or more to restore 1.30x sizing DSCR), deferred while the residual value guarantee runs", W, "§2.09(b)(iii)")
add("fac_ward_county", "sponsor_support", "Residual value guarantee: Nscale (parent) has first offer to buy a cancelled tranche's assets at loan + Microsoft prepayment; else sale, reallocation or re-contracting", W, "Definition: RVG Triggering Event")
add("fac_ward_county", "sponsor_support", "Limited parent guarantees only: bad acts, management services agreement, residual value", W, "Definition: Limited Parent Guarantees")
add("fac_ward_county", "cash_trap", "Cash trapped if historical DSCR < 1.10x; after 6 months, trapped cash prepays the loan", W, "Definitions: Cash Trap Event, Cash Trap Prepayment Event; §2.09(b)(v)")
add("fac_ward_county", "reserves", "Debt service reserve = 67% of the highest 3-month debt service; also opex, annual expense and GPU spares reserves", W, "Definitions: reserve requirements")
add("fac_ward_county", "reserves", "Microsoft's upfront payments are held in a prepayment account until the tranche is accepted", W, "Definitions: Customer Contract Prepayment Account / Amount")
N = "src_ex10_24"
add("fac_north_carolina", "if_customer_terminates", "Customer contract terminated, suspended or in terminable default = event of default", N, "§7.01(m)")
add("fac_north_carolina", "sponsor_support", "Limited parent guarantees only: bad acts and management services agreement (no residual value guarantee)", N, "Definition: Limited Parent Guarantees")
add("fac_north_carolina", "cash_trap", "Cash trapped if historical DSCR < 1.10x; after 6 months, trapped cash prepays the loan", N, "Definitions: Cash Trap Event, Cash Trap Prepayment Event")
add("fac_north_carolina", "reserves", "Debt service reserve = 100% of the next payment; opex and GPU spares reserves", N, "Definitions: reserve requirements")
add("fac_north_carolina", "completion_test", "Customer contract amended so force majeure must last 45 days before either side can terminate", N, "Definition: Customer Contract Amendment")
U = "src_ex10_14"
add("fac_uk_gpu_ddtl", "if_customer_terminates", "Contract terminated: 90 days to sign a replacement with a comparable customer; otherwise event of default, and loans against that contract are prepaid down to its advance amount", U, "§2.09(b)(vii); §7.01(m)")
add("fac_uk_gpu_ddtl", "cash_trap", "Cash trapped if DSCR < 1.15x or GPUs are not earning revenue within 90 days of delivery; trap for 4 straight test dates becomes a prepayment", U, "Definitions: Cash Trap Event, Cash Trap Prepayment Event")
add("fac_uk_gpu_ddtl", "cash_trap", "100% cash sweep if fewer than 85% of GPUs are online or a material customer misses payments", U, "§2.09(b)(x)")
add("fac_uk_gpu_ddtl", "completion_test", "At most $425M may be lent against contracts not yet accepted by the customer", U, "Definition: Pre-Acceptance Concentration Limit")
add("fac_uk_gpu_ddtl", "reserves", "Deployment ramp reserve covers site costs and interest until each contract earns revenue; 3-month interest reserve; opex reserve", U, "Definitions: reserve requirements")
add("fac_uk_gpu_ddtl", "sponsor_support", "Parent guarantee from Nscale Intermediate Holdings Limited (Jersey)", U, "Definitions: Parent Guarantee, Parent Guarantor")
D = "src_ex10_21"
add("fac_norway_term_loan", "completion_test", "Target completion 5 Apr 2027; event of default if not complete within one year of that (5 Apr 2028)", D, "Definition: Target Completion Date; §23.21")
add("fac_norway_term_loan", "completion_test", "Completion longstop 30 Jun 2027 (extendable 6 months for force majeure) gates drawdowns and is the VAT facility's maturity", D, "Definition: Completion Long-Stop Date; §4.2; Final Maturity Date")
add("fac_norway_term_loan", "completion_test", "Construction suspended for 60 days in a row, or abandoned = event of default", D, "§23.18")
add("fac_norway_term_loan", "cost_overrun_funding", "Overruns above $0.5M must be funded with subordinated debt or equity within 15 business days; loan proceeds cannot be used", D, "§22.3")
add("fac_norway_term_loan", "if_customer_terminates", "Microsoft offtake terminated: all cash trapped; after 1 year 100% of trapped cash prepays the loan, and it becomes an event of default (18 months if replacement talks are under way)", D, "§8.8; §20.26; §23.14")
add("fac_norway_term_loan", "if_customer_terminates", "Cash also trapped from 24 months before the offtake expires unless it is extended or replaced", D, "Definition: Offtake Expiry Event")
add("fac_norway_term_loan", "cash_trap", "Ratio cash trap if historic or projected DSCR < 1.15x or net leverage > 20% above base case; 50% of trapped cash prepays", D, "Definition: Ratio Cash Trap Test; §8.7")
add("fac_norway_term_loan", "sponsor_support", "Parent company guarantee from Nscale Limited", D, "Definitions: Parent Company Guarantee, Parent Guarantor")
I = "src_ex10_22"
add("fac_macquarie_iceland", "completion_test", "Service scheduled to start by 17 Nov 2026; event of default if not started by 27 Jan 2027", I, "Definition: Service Commencement Date; §23.19")
add("fac_macquarie_iceland", "if_customer_terminates", "Customer contract terminated: 60 days to sign a replacement for at least the remaining tenor; termination proceeds prepay the loan", I, "§22.30; §7.2")
add("fac_macquarie_iceland", "sponsor_support", "The (redacted) customer's obligations are guaranteed by two redacted guarantors", I, "Definition: Customer Guarantor")
G = "src_ex10_12"
add("fac_macquarie_glomfjord", "completion_test", "Event of default if Spring service had not started by 30 Nov 2025 (scheduled 30 Aug 2025)", G, "Definition: Service Commencement Date; §25.16",
    note="Glomfjord was reported about six months late; whether this test was met or waived is not filed.")
add("fac_macquarie_glomfjord", "if_customer_terminates", "Spring contract terminated: two months to sign a replacement customer; termination proceeds prepay the loan", G, "Spring Singapore Customer Contract clause; §7.2")
R = "src_ex10_18"
add("fac_parent_rcf", "cross_default", "Event of default if any debt over $50M of the borrower or any restricted subsidiary is unpaid, or can be accelerated", R, "Events of Default (f); Definition: Material Indebtedness")
add("fac_parent_rcf", "cross_default", "Project borrowers are designated 'SPV Entities', which are restricted subsidiaries, so a campus loan default over $50M appears to reach the revolver; no carve-out found", R, "Definition: SPV Entity", method="estimated",
    note="Our reading; confirm with counsel.")


def append(path, fieldnames, items):
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=fieldnames).writerows(items)


append(REPO / "data/sources.csv", ["id", "type", "access", "publisher", "title", "url", "published_date", "retrieved_date", "note"],
       [dict(id=i, type="filing", access="full_document", publisher="NSCALE Ltd (SEC EDGAR)", title=t, url=u, published_date="2026-09-18",
             retrieved_date=OBS, note="") for i, t, u in sources])
append(REPO / "data/entities.csv", ["id", "type", "label", "note"], [dict(id=a, type=b, label=c, note=d) for a, b, c, d in entities])
fields = ["id", "entity", "property", "value", "unit", "source", "locator", "effective_date", "observed_date",
          "method", "derived_from", "extractor", "note"]
append(REPO / "data/statements.csv", fields, [dict(id=f"st{4000 + n:04d}", **r) for n, r in enumerate(rows)])
print(len(rows), "statements")
