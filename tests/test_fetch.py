"""Tests for the fixes to fetching: paging, feed isolation, polite HTTP, archive hashes, quotes, html2text."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tracker import archive, jurisdictions, monitor, net
from tracker.model import ROOT, load

sys.path.insert(0, str(ROOT / "scripts"))
import html2text  # noqa: E402


class Paging(unittest.TestCase):
    def test_edgar_follows_every_page(self):
        pages = [{"hits": {"total": {"value": 3}, "hits": [{"n": 1}, {"n": 2}]}},
                 {"hits": {"total": {"value": 3}, "hits": [{"n": 3}]}}]
        with mock.patch.object(net, "get_json", side_effect=pages) as get:
            hits = monitor.edgar_hits("Nscale", "2026-01-01", {})
        self.assertEqual([h["n"] for h in hits], [1, 2, 3])
        self.assertIn("from=2", get.call_args_list[1].args[0])

    def test_companies_house_follows_every_page(self):
        pages = [{"total_count": 150, "items": [{"i": n} for n in range(100)]},
                 {"total_count": 150, "items": [{"i": n} for n in range(100, 150)]}]
        with mock.patch.object(net, "get_json", side_effect=pages) as get:
            items = monitor._ch_items("https://x/company/1/charges", {})
        self.assertEqual(len(items), 150)
        self.assertIn("start_index=100", get.call_args_list[1].args[0])

    def test_empty_page_stops(self):
        with mock.patch.object(net, "get_json", return_value={}) as get:
            self.assertEqual(monitor._ch_items("https://x", {}), [])
        self.assertEqual(get.call_count, 1)


class FeedIsolation(unittest.TestCase):
    def test_a_failing_feed_does_not_hide_the_others(self):
        good = [dict(event_id="edgar:1", feed="edgar", group="g", subject="s", kind="8-K", event_date="2099-01-01",
                     title="t", url="u")]
        path = Path(tempfile.mkdtemp()) / "events.csv"
        with mock.patch.object(monitor, "EVENTS", path), \
             mock.patch.object(monitor, "edgar_events", return_value=good), \
             mock.patch.object(monitor, "news_events", side_effect=OSError("down")):
            new, failures = monitor.run(load(), feeds=("edgar", "news"))
        self.assertEqual([e["event_id"] for e in new], ["edgar:1"])
        self.assertEqual(len(failures), 1)
        self.assertIn("news", failures[0])


class PoliteHttp(unittest.TestCase):
    def test_edgar_requires_a_contact(self):
        with mock.patch.dict(os.environ, {"EDGAR_USER_AGENT": "anonymous"}):
            with self.assertRaises(RuntimeError):
                net.user_agent(require_contact=True)
        with mock.patch.dict(os.environ, {"EDGAR_USER_AGENT": "Jane Doe jane@example.com"}):
            self.assertEqual(net.user_agent(require_contact=True), "Jane Doe jane@example.com")


class Archive(unittest.TestCase):
    def test_changed_file_is_caught(self):
        root = Path(tempfile.mkdtemp())
        path = archive.record(root / "f", "a.txt", b"original", "https://example.com/a")
        manifest = json.loads((root / "f" / "manifest.json").read_text())
        self.assertEqual(manifest["a.txt"]["sha256"], archive.sha256(b"original"))
        with mock.patch.object(archive, "ROOT", root):
            self.assertEqual(archive.verify(root), [])
            path.write_bytes(b"edited")
            self.assertEqual(len(archive.verify(root)), 1)

    def test_quotes_must_be_verbatim(self):
        store = load()
        sid = store.statements[0].id
        tmp = Path(tempfile.mkdtemp())
        doc = tmp / "doc.txt"
        doc.write_text("The Borrower shall  repay the “Loans” in full.")
        quotes = tmp / "quotes.csv"
        quotes.write_text(f'statement_id,file,quote\n{sid},{doc},"repay the ""Loans"" in full"\n')
        with mock.patch.object(archive, "ROOT", Path("/")):
            self.assertEqual(archive.check_quotes(store, quotes), [])   # whitespace and curly quotes ignored
            quotes.write_text(f"statement_id,file,quote\n{sid},{doc},repay the loans early\n")
            self.assertEqual(len(archive.check_quotes(store, quotes)), 1)

    def test_repository_quotes_and_archive_are_clean(self):
        self.assertEqual(archive.check_quotes(load()) + archive.verify(), [])


class Html2Text(unittest.TestCase):
    def test_import_has_no_side_effects(self):
        cwd = tempfile.mkdtemp()
        code = f"import sys; sys.argv = ['x', 'CIK', 'ACC']; sys.path.insert(0, {str(ROOT / 'scripts')!r}); import html2text"
        subprocess.run([sys.executable, "-I", "-c", code], cwd=cwd, check=True)
        self.assertEqual(os.listdir(cwd), [])

    def test_hidden_xbrl_header_is_skipped(self):
        raw = ('<div style="display:none"><ix:header><ix:hidden>secret facts</ix:hidden></ix:header></div>'
               "<p>Credit&nbsp;Agreement</p><table><tr><td>A</td><td>B</td></tr></table>")
        self.assertEqual(html2text.to_text(raw), "Credit Agreement\n| A | B")


class Directory(unittest.TestCase):
    def test_directory_is_valid(self):
        self.assertEqual(jurisdictions.validate_directory(), [])

    def test_aliases(self):
        for alias, key in (("UK", "uk"), ("gb", "uk"), ("lux", "lu"), ("LU", "lu"), ("norway", "no"), ("sec", "us")):
            self.assertEqual(jurisdictions.jurisdiction_key(alias), key)
        with self.assertRaises(KeyError):
            jurisdictions.jurisdiction_key("atlantis")

    def test_every_country_has_registry_and_insolvency_sources(self):
        d = jurisdictions.directory()
        for key, j in d["jurisdictions"].items():
            if key in ("eu", "global", "us"):
                continue
            channels = {c for r in jurisdictions.resources(key) for c in r["channels"]}
            self.assertTrue({"registry", "insolvency"} <= channels, key)

    def test_search_links_fill_the_name(self):
        r = {"search_url": "https://example.com/?q={q}", "url": "https://example.com"}
        self.assertEqual(jurisdictions.link(r, "Nscale Ltd"), ("https://example.com/?q=Nscale%20Ltd", True))

    def test_offline_search_lists_links_and_runs_nothing(self):
        with mock.patch.object(net, "get") as get:
            results, failures, links = jurisdictions.search("lu", "Nscale", live=False)
        get.assert_not_called()
        self.assertEqual((results, failures), ([], []))
        self.assertTrue(any(r["id"] == "lu_lbr" for r, _, _ in links))

    def test_failing_adapter_is_reported_not_raised(self):
        with mock.patch.dict(jurisdictions.ADAPTERS, {"ie_cro": mock.Mock(side_effect=OSError("down"))}), \
             mock.patch.object(jurisdictions, "eu_gleif", return_value=[jurisdictions.Hit("X")]):
            results, failures, _ = jurisdictions.search("ie", "Nscale")
        self.assertEqual([f[0] for f in failures], ["CRO Open Data (company register)"])
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
