"""Tests for document classification, company dossiers and sector helpers."""
import unittest
from unittest import mock

from tracker import documents


def needs(docs):
    return sorted({n for d in docs for n in d["needs"]})


class Classify(unittest.TestCase):
    def test_companies_house_types(self):
        self.assertIn("security", needs(documents.classify(ch="MR01")))
        self.assertIn("guarantors", needs(documents.classify(ch="GUARANTEE2")))
        self.assertEqual(needs(documents.classify(ch="PSC02")), ["structure"])        # prefix match
        self.assertIn("restructuring", needs(documents.classify(ch="AM03")))
        self.assertIn("financials", needs(documents.classify(ch="AA")))
        self.assertEqual(documents.classify(ch="AD01"), [])                           # change of address: no question
        self.assertEqual(documents.classify(ch="AA01"), [])                           # exact codes are exact

    def test_edgar_types_forms_and_items(self):
        self.assertIn("guarantors", needs(documents.classify(edgar_type="EX-22.1")))
        self.assertEqual(needs(documents.classify(edgar_type="EX-21.1")), ["structure"])
        self.assertIn("debt_docs", needs(documents.classify(edgar_type="EX-10.25")))
        self.assertIn("debt_docs", needs(documents.classify(edgar_type="EX-4.1")))
        self.assertIn("debt_docs", needs(documents.classify(edgar_form="424B5")))
        self.assertIn("debt_docs", needs(documents.classify(edgar_items=["2.03", "9.01"])))
        self.assertIn("restructuring", needs(documents.classify(edgar_items=["1.03"])))
        self.assertEqual(documents.classify(edgar_items=["7.01"]), [])

    def test_monitor_events_get_needs(self):
        charge = dict(feed="ch", kind="charge-outstanding")
        self.assertIn("security", documents.event_needs(charge))
        self.assertEqual(documents.event_needs(dict(feed="news", kind="news")), [])


class Parsing(unittest.TestCase):
    def test_filing_index_rows(self):
        html = (b"<table><tr><th>Seq</th></tr><tr><td>1</td><td>Credit Agreement</td><td><a>d1ex101.htm</a> iXBRL</td>"
                b"<td>EX-10.1</td><td>100</td></tr><tr><td>2</td><td></td><td>x.jpg</td><td></td><td>5</td></tr></table>")
        self.assertEqual(documents.filing_index(html), [("EX-10.1", "d1ex101.htm", "Credit Agreement")])
        self.assertEqual(documents.filing_index(None), [])

    def test_norway_figures(self):
        r = {"regnskapsperiode": {"tilDato": "2023-12-31"}, "valuta": "NOK",
             "eiendeler": {"sumEiendeler": 9.8e9},
             "egenkapitalGjeld": {"egenkapital": {"sumEgenkapital": 4.0e9},
                                  "gjeldOversikt": {"sumGjeld": 5.79e9, "langsiktigGjeld": {"sumLangsiktigGjeld": 3.6e9},
                                                    "kortsiktigGjeld": {"sumKortsiktigGjeld": 2.19e9}}}}
        self.assertEqual(documents.norway_figures(r), "FY to 2023-12-31: total debt NOK 5,790m (long-term 3,600m, "
                                                      "short-term 2,190m), equity 4,000m, assets 9,800m")


class CompaniesHouseText(unittest.TestCase):
    def test_filing_titles_are_plain_english(self):
        f = {"type": "MR04", "description": "mortgage-satisfy-charge-full", "description_values": {"charge_number": "157494080003"}}
        self.assertEqual(documents.ch_title(f), "MR04: charge 157494080003 fully satisfied")
        f = {"type": "XX01", "description": "some-new-form", "description_values": {"date": "2026-01-01"}}
        self.assertEqual(documents.ch_title(f), "XX01: some new form (2026-01-01)")

    def test_charge_title_lists_terms(self):
        c = {"charge_code": "157494080008", "status": "outstanding",
             "particulars": {"contains_fixed_charge": True, "contains_negative_pledge": True, "description": "Shares in X Ltd"}}
        self.assertEqual(documents.charge_title(c),
                         "Charge 157494080008 (outstanding), fixed charge, negative pledge: Shares in X Ltd")


class Dossier(unittest.TestCase):
    def test_failing_registry_is_noted_and_guidance_still_printed(self):
        with mock.patch.dict(documents.PULLS, {"uk": mock.Mock(side_effect=RuntimeError("No Companies House key"))}), \
             mock.patch.object(documents, "find_lei", return_value=None):
            d = documents.company("uk", "12345678", name="Example Ltd")
        self.assertEqual(len(d.failures), 1)
        text = documents.format_company(d)
        self.assertIn("## Guarantors", text)
        self.assertIn("look for: Parent guarantee for audit exemption", text)
        self.assertIn("not searched: registry", text)

    def test_lei_goes_straight_to_gleif(self):
        with mock.patch.object(documents, "gleif_structure") as g, mock.patch.object(documents, "esef_financials"):
            d = documents.company("eu", "5493001ezooa66ptbr68")
        g.assert_called_once()
        self.assertEqual(d.ids["lei"], "5493001EZOOA66PTBR68")

    def test_guidance_includes_pan_eu_and_paid(self):
        scopes = {doc["jurisdiction"] for doc in documents.guidance("lu", "debt_docs")}
        self.assertEqual(scopes, {"lu", "eu", "global"})


class Taxonomy(unittest.TestCase):
    def test_taxonomy_is_valid(self):
        self.assertEqual(documents.validate_taxonomy(), [])

    def test_every_need_has_a_document_in_every_main_jurisdiction(self):
        for jur in ("uk", "us"):
            covered = {n for d in documents.guidance(jur) for n in d["needs"]}
            self.assertEqual(covered, set(documents.taxonomy()["needs"]) - ({"contracts"} if jur == "uk" else set()), jur)

    def test_exhibit_titles_sort_debt_from_contracts(self):
        raw = (b"<p>EX-10.3</p><p>ck0002110365-ex10_3.htm</p><p>Exhibit 10.3</p><p>SENIOR SECURED CREDIT AGREEMENT</p>"
               b"<p>dated as of 1 May 2026 among ...</p>")
        self.assertEqual(documents.exhibit_title(raw), "SENIOR SECURED CREDIT AGREEMENT")
        self.assertEqual(documents.title_needs("SENIOR SECURED CREDIT AGREEMENT"), ["debt_docs"])
        self.assertEqual(documents.title_needs("Guarantee and Collateral Agreement"), ["debt_docs", "guarantors", "security"])
        self.assertEqual(documents.title_needs("GPU SERVICES AGREEMENT"), ["contracts"])
        self.assertEqual(documents.title_needs("INDEMNIFICATION AGREEMENT"), ["contracts"])

    def test_uninformative_title_falls_back_to_opening_text(self):
        loan = (b"<p>Exhibit 10.12</p><p>AMENDMENT AND RESTATEMENT AGREEMENT</p><p>between Nscale AS as borrower, "
                b"the Lenders and DNB Bank ASA as facility agent and security agent</p>")
        title, needs, how = documents.exhibit_needs(loan)
        self.assertEqual((title, how), ("AMENDMENT AND RESTATEMENT AGREEMENT", "opening text"))
        self.assertEqual(needs, ["debt_docs", "security"])
        gpu = b"<p>GPU SERVICES AGREEMENT</p><p>Provider will deliver GPU capacity at the data center facility.</p>"
        self.assertEqual(documents.exhibit_needs(gpu)[1], ["contracts"])


if __name__ == "__main__":
    unittest.main()
