import unittest

import yaml

from tracker.model import VOCAB_PATH, Statement, Store, _canonical_ids, _grade, load, resolve, validate

VOCAB = yaml.safe_load(VOCAB_PATH.read_text())


def make_store(statements, sources=None, entities=None, links=None):
    sources = sources or {
        "filing": {"id": "filing", "type": "filing", "access": "full_document"},
        "filing_excerpt": {"id": "filing_excerpt", "type": "filing", "access": "excerpt"},
        "news": {"id": "news", "type": "news", "access": "full_document"},
        "internal": {"id": "internal", "type": "internal", "access": "full_document"},
    }
    entities = entities or {
        "fac": {"id": "fac", "type": "facility", "label": "Facility"},
        "fac2": {"id": "fac2", "type": "facility", "label": "Facility (other name)"},
        "bank": {"id": "bank", "type": "legal_entity", "label": "Bank"},
        "bank2": {"id": "bank2", "type": "legal_entity", "label": "Bank 2"},
        "site": {"id": "site", "type": "site", "label": "Site"},
    }
    store = Store(VOCAB, sources, entities, links or [], statements)
    store.canonical = _canonical_ids(store)
    for st in statements:
        st.grade = _grade(store, st)
    return store


def st(id, prop, value, source="filing", effective="", method="disclosed", unit="", entity="fac", derived_from=()):
    if unit == "" and prop in ("amount_max", "amount_drawn"):
        unit = "USD"
    return Statement(id=id, entity=entity, property=prop, value=value, unit=unit, source=source, locator="",
                     effective_date=effective, observed_date="2026-10-29", method=method,
                     derived_from=list(derived_from), extractor="test", note="")


class SeedData(unittest.TestCase):
    def test_repository_data_is_valid(self):
        self.assertEqual(validate(load()), [])


class Validation(unittest.TestCase):
    def errors(self, *statements):
        return validate(make_store(list(statements)))

    def test_rejects_property_not_in_vocabulary(self):
        self.assertIn("not a property", self.errors(st("a", "favourite_colour", "blue"))[0])

    def test_rejects_enum_value_outside_list(self):
        self.assertTrue(self.errors(st("a", "facility_type", "magic_loan")))

    def test_rejects_reference_to_wrong_entity_type(self):
        self.assertIn("expected", self.errors(st("a", "lender", "site"))[0])

    def test_rejects_money_without_currency(self):
        self.assertIn("currency", self.errors(st("a", "amount_max", "1B", unit="dollars"))[0])

    def test_checked_absent_must_be_empty(self):
        self.assertTrue(self.errors(st("a", "margin_bps", "500", method="checked_absent")))

    def test_derived_must_name_inputs(self):
        self.assertTrue(self.errors(st("a", "margin_bps", "500", method="derived")))

    def test_accepts_before_dates(self):
        self.assertEqual(self.errors(st("a", "amount_max", "770M", effective="<2026-06")), [])


class Resolution(unittest.TestCase):
    def test_later_effective_date_is_history_not_conflict(self):
        r = resolve(make_store([st("old", "amount_max", "770M", effective="<2026-06"),
                                st("new", "amount_max", "900M", effective="2026-06")]), "fac", "amount_max")
        self.assertEqual(r.current[0].id, "new")
        self.assertEqual([s.id for s in r.history], ["old"])
        self.assertEqual(r.conflicts, [])

    def test_same_date_disagreement_is_conflict_and_stronger_source_shows(self):
        r = resolve(make_store([st("news", "amount_max", "2B", source="news", effective="2026-08"),
                                st("filing", "amount_max", "1.85B", effective="2026-08")]), "fac", "amount_max")
        self.assertEqual(r.current[0].id, "filing")
        self.assertEqual([s.id for s in r.conflicts], ["news"])

    def test_undated_value_cannot_supersede_but_is_flagged(self):
        r = resolve(make_store([st("dated", "amount_max", "1.85B", effective="2026-08-27"),
                                st("undated", "amount_max", "1.831B", source="news")]), "fac", "amount_max")
        self.assertEqual(r.current[0].id, "dated")
        self.assertEqual([s.id for s in r.conflicts], ["undated"])

    def test_numbers_within_tolerance_agree(self):
        r = resolve(make_store([st("a", "amount_max", "1.4B"), st("b", "amount_max", "1400000000", source="news")]),
                    "fac", "amount_max")
        self.assertEqual(r.conflicts, [])
        self.assertEqual(len(r.current), 2)

    def test_newer_value_from_weaker_source_is_flagged(self):
        r = resolve(make_store([st("filing", "amount_max", "900M", effective="2026-06"),
                                st("news", "amount_max", "1B", source="news", effective="2026-09")]), "fac", "amount_max")
        self.assertEqual(r.current[0].id, "news")
        self.assertTrue(any("weaker" in f for f in r.flags))

    def test_multi_valued_property_lists_every_value(self):
        r = resolve(make_store([st("a", "lender", "bank"), st("b", "lender", "bank2", source="news"),
                                st("c", "lender", "bank", source="news")]), "fac", "lender")
        self.assertEqual(r.status, "multi")
        self.assertEqual(sorted(s.value for s in r.current), ["bank", "bank2"])

    def test_undisclosed_differs_from_not_checked(self):
        store = make_store([st("a", "margin_bps", "", method="checked_absent")])
        self.assertEqual(resolve(store, "fac", "margin_bps").status, "undisclosed")
        self.assertEqual(resolve(store, "fac", "maturity_date").status, "not_checked")

    def test_excerpt_caps_grade_at_b(self):
        store = make_store([st("full", "amount_max", "1B"), st("ex", "amount_max", "1B", source="filing_excerpt")])
        grades = {s.id: s.grade for s in store.statements}
        self.assertEqual(grades, {"full": "A", "ex": "B"})

    def test_derived_grade_is_weakest_input(self):
        store = make_store([st("in1", "amount_max", "1B"), st("in2", "margin_bps", "500", source="news"),
                            st("out", "dscr_covenant", "1.3", unit="x", source="internal", method="derived",
                               derived_from=("in1", "in2"))])
        self.assertEqual({s.id: s.grade for s in store.statements}["out"], "C")

    def test_same_as_link_merges_statements_and_can_be_removed(self):
        statements = [st("a", "amount_max", "1B", entity="fac"), st("b", "amount_max", "1B", entity="fac2", source="news")]
        link = {"entity_a": "fac", "relation": "same_as", "entity_b": "fac2"}
        merged = resolve(make_store(statements, links=[link]), "fac2", "amount_max")
        self.assertEqual(sorted(s.id for s in merged.current), ["a", "b"])
        unmerged = resolve(make_store(statements), "fac", "amount_max")
        self.assertEqual([s.id for s in unmerged.current], ["a"])


if __name__ == "__main__":
    unittest.main()
