"""Tests for the disclosure map: validity, region logic and that every claim prints its citation."""
import unittest

from tracker import disclosure


class DisclosureMap(unittest.TestCase):
    def test_map_is_valid(self):
        self.assertEqual(disclosure.validate_map(), [])

    def test_every_mandatory_trace_cites_a_source(self):
        m = disclosure.disclosure_map()
        for ins in m["instruments"]:
            for t in ins["traces"]:
                if t["status"] == "mandatory" and t["evidence"] in ("law", "regulator"):
                    self.assertTrue(t.get("refs"), f"{ins['id']} {t['region']} is mandatory by {t['evidence']} but cites nothing")

    def test_region_coverage(self):
        self.assertTrue(disclosure.covers("nordics", "no"))
        self.assertFalse(disclosure.covers("nordics", "uk"))
        self.assertTrue(disclosure.covers("eu", "lu"))
        self.assertFalse(disclosure.covers("eu", "us"))
        self.assertTrue(disclosure.covers("all", "us"))
        self.assertFalse(disclosure.covers("uk", "ie"))

    def test_where_prints_basis_and_timing(self):
        text = disclosure.format_where(disclosure.instruments("secured_loan", "uk"))
        self.assertIn("Within 21 days of creation", text)
        self.assertIn("legislation.gov.uk/ukpga/2006/46/section/859A", text)

    def test_signals_by_stage(self):
        pre = disclosure.signals(stage="pre")
        self.assertTrue(pre and all(s["stage"] == "pre" for s in pre))
        self.assertIn("charge_registered", [s["id"] for s in disclosure.signals(region="uk", stage="closing")])


if __name__ == "__main__":
    unittest.main()
