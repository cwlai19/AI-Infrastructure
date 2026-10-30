"""Tests for the lender layer and the pre-financing watcher (no network: sources are mocked)."""
import unittest
from unittest import mock

import pandas as pd

from tracker import lenders, net, watch


class Matching(unittest.TestCase):
    def test_whole_words_only(self):
        self.assertEqual(lenders.matches("IREN Ltd | First lien", ["IREN"]), ["IREN"])
        self.assertEqual(lenders.matches("Firenze Holdings", ["IREN"]), [])
        self.assertEqual(lenders.matches("NSCALE SERVICES UK LTD", ["Nscale"]), ["Nscale"])

    def test_borrower_from_identifier_segment(self):
        self.assertEqual(lenders.borrower_label("Technology | CoreWeave Inc. | Unsecured Bond", "Technology", ["CoreWeave"]),
                         "CoreWeave Inc.")
        self.assertEqual(lenders.borrower_label("Something else", "Parsed Co", ["Nscale"]), "Parsed Co")

    def test_marks_and_unit_flag(self):
        self.assertEqual(lenders._mark(900_000, None, 831_000), "108.3 (of cost)")
        self.assertEqual(lenders._mark(98.7, 100, 100), "98.7 (of principal)")
        self.assertIn("check units", lenders._mark(506_000, 479_468_000, 506_000))
        self.assertEqual(lenders._kind("First lien senior secured delayed draw term loan"), "debt")
        self.assertEqual(lenders._kind("Series B Preferred Shares"), "equity")


class Discovery(unittest.TestCase):
    def test_current_period_only_and_newest_filing_per_bdc(self):
        rows = pd.DataFrame([
            dict(adsh="a1", cik=1, name="BDC ONE", form="10-Q", period="2026-06-30", filed="2026-08-05", data_date="2026-06-30",
                 company=None, investment_id="Nscale Limited | Preferred equity", investment_name=None, interest_rate=None,
                 spread=None, principal=None, cost=5.0, fair_value=6.0, filing_url="u1"),
            dict(adsh="a1", cik=1, name="BDC ONE", form="10-Q", period="2026-06-30", filed="2026-08-05", data_date="2025-12-31",
                 company=None, investment_id="Nscale Global Holdings | Preferred equity", investment_name=None, interest_rate=None,
                 spread=None, principal=None, cost=5.0, fair_value=5.0, filing_url="u1"),
            dict(adsh="a0", cik=1, name="BDC ONE", form="10-K", period="2025-12-31", filed="2026-03-01", data_date="2025-12-31",
                 company=None, investment_id="Nscale Global Holdings | Preferred equity", investment_name=None, interest_rate=None,
                 spread=None, principal=None, cost=5.0, fair_value=5.0, filing_url="u0"),
        ])
        ds = mock.Mock()
        ds.schedule_of_investments.to_dataframe.return_value = rows
        with mock.patch.object(lenders, "load_month", return_value=ds):
            found = lenders.discover(["Nscale"], [(2026, 8)])
        self.assertEqual(list(found), ["a1"])                       # newest filing for the BDC
        self.assertEqual(len(found["a1"]["rows"]), 1)                # the prior-period comparative is dropped
        self.assertEqual(found["a1"]["rows"][0]["fair_value"], 6.0)

    def test_failed_parse_falls_back_to_data_set_rows_and_says_so(self):
        filing = dict(adsh="a1", bdc="BDC ONE", cik="1", form="10-Q", period="2026-06-30", filed="", url="u",
                      rows=[dict(term="Nscale", identifier="Nscale Limited | Preferred equity", interest_rate=None, spread=None,
                                 principal=None, cost=5.0, fair_value=6.0)])
        with mock.patch.object(lenders, "monthly_files", return_value=[(2026, 8)]), \
             mock.patch.object(lenders, "discover", return_value={"a1": filing}), \
             mock.patch.object(lenders, "confirm", side_effect=OSError("down")):
            positions, recons, failures, _ = lenders.lenders(["Nscale"])
        self.assertEqual(positions[0].source, "SEC data set")
        self.assertEqual(len(failures), 1)
        self.assertIn("not confirmed", lenders.format_lenders(positions, recons, failures, [(2026, 8)]))


class Watch(unittest.TestCase):
    def test_financing_name(self):
        self.assertTrue(watch.financing_name("NSCALE MIDCO 1 LIMITED"))
        self.assertTrue(watch.financing_name("NSCALE WARD COUNTY BORROWER SPV, LLC"))
        self.assertFalse(watch.financing_name("NSCALE LIMITED"))

    def test_whole_name_required(self):
        self.assertTrue(watch.has_name("GREEN MOUNTAIN DC HOLDING AS", "Green Mountain DC"))
        self.assertFalse(watch.has_name("ACCRESCO AS", "Green Mountain"))
        self.assertFalse(watch.has_name("KAO MEN STUDIO", "Kao Data"))
        self.assertTrue(watch.has_name("NSCALE GPU SAUDA AS", "Nscale"))

    def test_financing_waves(self):
        S = watch.Signal
        sig = [S("g", "charge_registered", "2026-08-10", "A", "1", "MR01: charge 1 created 2026-08-06", "", ""),
               S("g", "charge_registered", "2026-08-10", "B", "2", "MR01: charge 2 created 2026-08-07", "", ""),
               S("g", "charge_registered", "2026-09-01", "C", "3", "MR01: charge 3 created 2026-08-28", "", ""),
               S("g", "articles_changed", "2026-08-25", "A", "1", "MA", "", "")]
        waves = watch.financing_waves(sig)
        self.assertEqual(len(waves), 1)                                    # C alone is not a wave
        self.assertEqual([c for c, _ in waves[0][2]], ["A", "B"])
        self.assertEqual(waves[0][3], ["A"])                              # articles changed after the charges count too

    def test_lei_signals_drop_funds_and_name_misses(self):
        recs = {"data": [
            {"id": "L1", "attributes": {"entity": {"legalName": {"name": "NSCALE WARD COUNTY BORROWER SPV, LLC"}, "category": "GENERAL",
                                                   "legalAddress": {"region": "US-DE", "country": "US"}},
                                        "registration": {"initialRegistrationDate": "2026-07-31T13:16:29Z"}}},
            {"id": "L2", "attributes": {"entity": {"legalName": {"name": "ProShares Ultra Nscale"}, "category": "FUND",
                                                   "legalAddress": {"country": "US"}},
                                        "registration": {"initialRegistrationDate": "2026-07-17T00:00:00Z"}}}]}
        with mock.patch.object(net, "get_json", side_effect=[recs, {}]):
            out = watch.lei_signals("g", "Nscale", "2026-01-01")
        self.assertEqual([s.ident for s in out], ["L1"])
        self.assertIn("financing-style name", out[0].detail)

    def test_one_failing_source_does_not_stop_the_others(self):
        with mock.patch.object(watch, "uk_signals", side_effect=RuntimeError("no key")), \
             mock.patch.object(watch, "no_signals", return_value=[]), \
             mock.patch.object(watch, "lei_signals", return_value=[watch.Signal("g", "new_lei", "2026-08-01", "X", "L", "", "", "GLEIF")]):
            signals, failures = watch.watch({"g": ["Nscale"]}, 30)
        self.assertEqual(len(signals), 1)
        self.assertIn("Companies House", failures[0])

    def test_events_have_stable_ids(self):
        s = watch.Signal("g", "new_lei", "2026-08-01", "X", "L1", "detail", "u", "GLEIF")
        self.assertEqual(watch.to_events([s])[0]["event_id"], watch.to_events([s])[0]["event_id"])
        self.assertEqual(watch.to_events([s])[0]["feed"], "signal")


if __name__ == "__main__":
    unittest.main()
