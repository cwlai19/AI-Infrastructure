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


class EntityReferences(unittest.TestCase):
    def test_references_to_merged_entities_agree(self):
        statements = [st("a", "borrower", "bank"), st("b", "borrower", "bank2", source="news")]
        link = {"entity_a": "bank", "relation": "same_as", "entity_b": "bank2"}
        self.assertEqual(resolve(make_store(statements, links=[link]), "fac", "borrower").conflicts, [])
        self.assertEqual(len(resolve(make_store(statements), "fac", "borrower").conflicts), 1)


class RefinementsAndReviews(unittest.TestCase):
    def test_partial_date_agrees_with_full_date(self):
        r = resolve(make_store([st("a", "signing_date", "2026-02"), st("b", "signing_date", "2026-02-11", source="news")]),
                    "fac", "signing_date")
        self.assertEqual(r.conflicts, [])

    def test_partial_effective_date_is_same_moment_not_history(self):
        r = resolve(make_store([st("a", "amount_max", "1.4B", effective="2026-02", source="news"),
                                st("b", "amount_max", "1.422B", effective="2026-02-11")]), "fac", "amount_max")
        self.assertEqual(r.history, [])
        self.assertEqual(r.current[0].id, "b")

    def test_before_date_is_never_the_same_moment(self):
        r = resolve(make_store([st("old", "amount_max", "770M", effective="<2026-06"),
                                st("new", "amount_max", "900M", effective="2026-06")]), "fac", "amount_max")
        self.assertEqual([s.id for s in r.history], ["old"])

    def test_text_wording_variant_agrees(self):
        r = resolve(make_store([st("a", "base_rate", "Term SOFR"), st("b", "base_rate", "SOFR", source="news")]),
                    "fac", "base_rate")
        self.assertEqual(r.conflicts, [])

    def test_jurisdiction_agrees_with_parent_country(self):
        r = resolve(make_store([st("a", "jurisdiction", "England and Wales", entity="bank"),
                                st("b", "jurisdiction", "United Kingdom", entity="bank", source="news")]), "bank", "jurisdiction")
        self.assertEqual(r.conflicts, [])

    def test_excerpt_loses_tie_to_full_document(self):
        r = resolve(make_store([st("ex", "amount_max", "2B", source="filing_excerpt"), st("full", "amount_max", "1B")]),
                    "fac", "amount_max")
        self.assertEqual(r.current[0].id, "full")

    def test_rejected_statement_is_kept_but_not_used(self):
        store = make_store([st("good", "amount_max", "1.85B"), st("bad", "amount_max", "1.831B", source="news")])
        store.reviews = {"bad": {"statement_id": "bad", "verdict": "rejected", "reason": "misread"}}
        r = resolve(store, "fac", "amount_max")
        self.assertEqual(r.conflicts, [])
        self.assertEqual([s.id for s in r.rejected], ["bad"])
        self.assertIn("bad", [s.id for s in store.statements])

    def test_explained_disagreement_is_not_an_open_conflict(self):
        store = make_store([st("filing", "amount_max", "137.4M"), st("press", "amount_max", "8B", source="news")])
        store.reviews = {"press": {"statement_id": "press", "verdict": "explained", "reason": "different measure"}}
        r = resolve(store, "fac", "amount_max")
        self.assertEqual(r.conflicts, [])
        self.assertEqual([s.id for s in r.explained], ["press"])

    def test_review_requires_reason(self):
        store = make_store([st("a", "amount_max", "1B")])
        store.reviews = {"a": {"statement_id": "a", "verdict": "rejected", "reason": ""}}
        self.assertTrue(any("reason" in e for e in validate(store)))

    def test_derived_value_is_as_strong_as_its_inputs(self):
        store = make_store([st("in1", "amount_drawn", "58.9M", effective="2026-03-31"),
                            st("flow", "drawdown", "329M", effective="2026-08"),
                            st("out", "amount_drawn", "387.9M", source="internal", method="derived",
                               effective="2026-08-31", derived_from=("in1", "flow"))])
        r = resolve(store, "fac", "amount_drawn")
        self.assertEqual(r.current[0].id, "out")
        self.assertFalse(any("weaker" in f for f in r.flags))


if __name__ == "__main__":
    unittest.main()
