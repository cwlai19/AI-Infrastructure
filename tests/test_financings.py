"""Tests for the financing table, wave matching, FX and intake."""
import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from tracker import financings, intake
from tracker.model import DATA_DIR, load


class Table(unittest.TestCase):
    def setUp(self):
        self.rows = {r["id"]: r for r in financings.facilities(load())}

    def test_umbrella_listed_but_not_counted(self):
        self.assertTrue(self.rows["fac_ccir_norway_pf"]["umbrella"])
        self.assertFalse(self.rows["fac_ccir_norway_pf"]["counted"])
        self.assertTrue(self.rows["fac_norway_term_loan"]["counted"])

    def test_region_from_asset_then_borrower_then_hq(self):
        self.assertEqual(self.rows["fac_ward_county"]["region"], "United States")         # site in the US
        self.assertEqual(self.rows["fac_macquarie_iceland"]["region"], "Nordics")         # site in Iceland
        self.assertEqual(self.rows["fac_uk_gpu_ddtl"]["region"], "UK & Ireland")          # borrower in England
        self.assertEqual(self.rows["fac_convertible_2026"]["region"], "UK & Ireland")     # no borrower: group HQ

    def test_convertibles_typed_after_vocabulary_change(self):
        self.assertEqual(self.rows["fac_convertible_2026"]["instrument_label"], "Convertible notes")

    def test_fx(self):
        self.assertAlmostEqual(financings.fx_to_usd(100, "USD"), 100)
        self.assertAlmostEqual(financings.fx_to_usd(1.0, "EUR"), 1.113, places=3)
        self.assertIsNone(financings.fx_to_usd(100, "XYZ"))

    def test_region_mapping(self):
        self.assertEqual(financings.region_of("United States (Delaware)"), "United States")
        self.assertEqual(financings.region_of("Jersey"), "UK & Ireland")
        self.assertEqual(financings.region_of("Luxembourg"), "Continental Europe")
        self.assertEqual(financings.region_of(""), "Unknown")


class Waves(unittest.TestCase):
    def test_date_match_within_three_days_only(self):
        fac = [dict(group="g", date="2026-05-08", name="RCF"), dict(group="g", date="2026-07-29", name="Iceland")]
        ws = financings.match_waves([dict(group="g", date="2026-05-08"), dict(group="g", date="2026-08-06"),
                                     dict(group="h", date="2026-05-08")], fac)
        self.assertEqual([w["matched"] for w in ws], [["RCF"], [], []])

    def test_quarter(self):
        self.assertEqual(financings.quarter("2026-08-27"), "2026-Q3")
        self.assertEqual(financings.quarter("2026-04"), "2026-Q2")


class Intake(unittest.TestCase):
    def test_template_validates_and_is_idempotent(self):
        tmp = Path(tempfile.mkdtemp())
        for p in DATA_DIR.glob("*.csv"):
            shutil.copy(p, tmp / p.name)
        template = DATA_DIR / "intake" / "financings_template.csv"
        counts, problems = intake.run(template, data_dir=tmp)
        self.assertEqual(problems, [])
        self.assertGreater(counts["statements"], 10)
        again, problems = intake.run(template, data_dir=tmp)
        self.assertEqual((again["statements"], problems), (0, []))
        fin = [r for r in financings.facilities(load(data_dir=tmp)) if r["group_name"].startswith("Example Group")]
        self.assertEqual(fin[0]["region"], "Nordics")
        self.assertAlmostEqual(fin[0]["amount_usd"], 500e6 * 1.113, delta=1)

    def test_bad_row_writes_nothing(self):
        tmp = Path(tempfile.mkdtemp())
        for p in DATA_DIR.glob("*.csv"):
            shutil.copy(p, tmp / p.name)
        bad = tmp / "bad.csv"
        with bad.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["group_name", "instrument", "amount", "currency", "source_title"])
            w.writerow(["Bad Co", "not_an_instrument", "10M", "USD", "Some note"])
        before = (tmp / "statements.csv").read_text()
        counts, problems = intake.run(bad, data_dir=tmp)
        self.assertTrue(problems)
        self.assertEqual((tmp / "statements.csv").read_text(), before)


if __name__ == "__main__":
    unittest.main()
