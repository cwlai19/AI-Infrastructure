# Paste this into a new chat (and attach this zip or connect the GitHub repo)

I'm continuing a project: a credit tracker for European neoclouds and data centres, which I'll extend to more
companies and to a Europe-wide map of who lends to whom.
Read `HANDOFF.md` first, then `docs/decisions.md`. The repo is https://github.com/cwlai19/AI-Infrastructure
(branch `statement-model`); this zip is a snapshot of it.

**How I want you to work**
- Explain from first principles, and argue against alternatives, before asking me to accept a design choice.
- Every fact goes in as a sourced statement (`data/statements.csv`) with a clause-level `locator`. Never overwrite;
  conflicts are flagged, not resolved silently. Run `python -m tracker check` and the tests after every data change.
- Outputs:
  - Dark theme, mobile-friendly, compact.
  - Watermark "Created by Christina W. Lai · as of <date> · Prepared with AI assistance", pinned in the top corner,
    plus the disclaimer.
  - No analyst commentary on outputs unless I ask.
  - Default to filings and company sources; news behind a toggle.
- Colleagues never see GitHub or the back-end. Emails to colleagues are drafts for me to send.
- Keep paid-terminal data (Bloomberg, LoanConnector, 9fin, Octus) out of the public repo.

**Next tasks (pick up in this order unless I say otherwise)**
1. Make the builds take a group id, so the same map, credit file and contract write-up work for any company.
2. Pilot the Europe debt map (HANDOFF §7): an entity list, GLEIF subsidiaries, Companies House charges, BDC and N-PORT
   holdings, EIB and export credit agency lists, loaded as statements and shown on a capital-concentration map.
3. Contract write-up: dark theme and corner watermark.

**Questions I'm asking Nscale's investors** (keep and update as answers come in)
- **Delivery:** tranche dates and status; Monarch's financing longstop and permits; Kvandal South vs 5 Apr 2027;
  Borealis vs 27 Jan 2027; Glomfjord's 30 Nov 2025 test.
- **Backlog:** Microsoft $43.8B by site and accepted vs pending; prepayment refund exposure; the redacted delay
  thresholds; who the North Carolina and Iceland customers are; terms of the second Anthropic building.
- **Funding:** sources and uses for $24B of GPUs and $3.5B of construction; Dell takeout; total parent guarantees;
  revolver cross-default and covenant headroom; campus coverage ratios and trapped cash; Loughton as SOW #3.
- **Upstream:** landlords at Sines, Borealis and Kvandal; the $1.4B of leases not yet started; the SIN02 seller
  payable; live MW by site; NVIDIA allocations; Asia-Pacific plans.
- **Forecast assumptions:** ramp by quarter; GPUs per MW; price per GPU-hour by tranche; re-contracting; opex per
  MW; capex per MW; GPU life and residual value; financing assumptions; downside cases (3/6/12-month delays, no
  Monarch financing); track record against budget.
