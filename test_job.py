#!/usr/bin/env python3
"""Self-contained tests for the HFDU errata-graveyard study.

Inline fixtures use the EXACT categorical strings that appear in the live data: the
errata status string "Held for Document Update" and the UPPERCASE publication-status
maturity levels in rfc-index.xml (the casing that caused the obsolescence-study P4 bug).
Run: python -m unittest -v
"""
import unittest

import job


# --- rfc-index.xml fixture (real UPPERCASE maturity levels + namespace) ---
INDEX_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rfc-index xmlns="http://www.rfc-editor.org/rfc-index">
  <rfc-entry>
    <doc-id>RFC0100</doc-id>
    <date><month>January</month><year>2000</year></date>
    <publication-status>INTERNET STANDARD</publication-status>
    <stream>IETF</stream>
    <updated-by><doc-id>RFC0900</doc-id></updated-by>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0200</doc-id>
    <date><year>2005</year></date>
    <publication-status>INFORMATIONAL</publication-status>
    <stream>IETF</stream>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0300</doc-id>
    <date><year>2006</year></date>
    <publication-status>PROPOSED STANDARD</publication-status>
    <stream>IETF</stream>
    <obsoleted-by><doc-id>RFC0950</doc-id></obsoleted-by>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0400</doc-id>
    <date><year>2007</year></date>
    <publication-status>INFORMATIONAL</publication-status>
    <stream>IETF</stream>
    <updated-by><doc-id>RFC0960</doc-id></updated-by>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0500</doc-id>
    <date><year>2008</year></date>
    <publication-status>PROPOSED STANDARD</publication-status>
    <stream>IETF</stream>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0600</doc-id>
    <date><year>2009</year></date>
    <publication-status>INFORMATIONAL</publication-status>
    <stream>IETF</stream>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0900</doc-id>
    <date><year>2015</year></date>
    <publication-status>PROPOSED STANDARD</publication-status>
    <stream>IETF</stream>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0950</doc-id>
    <date><year>2016</year></date>
    <publication-status>PROPOSED STANDARD</publication-status>
    <stream>IETF</stream>
  </rfc-entry>
  <rfc-entry>
    <doc-id>RFC0960</doc-id>
    <date><year>2010</year></date>
    <publication-status>PROPOSED STANDARD</publication-status>
    <stream>IETF</stream>
  </rfc-entry>
</rfc-index>
"""

ERRATA = [
    {"errata_id": 1, "doc-id": "RFC0100", "errata_status_code": "Verified",
     "errata_type_code": "Technical", "submit_date": "2012-01-01"},
    {"errata_id": 2, "doc-id": "RFC0100", "errata_status_code": "Verified",
     "errata_type_code": "Editorial", "submit_date": "2013-01-01"},
    {"errata_id": 3, "doc-id": "RFC0100", "errata_status_code": "Verified",
     "errata_type_code": "Technical", "submit_date": "2014-01-01"},
    {"errata_id": 4, "doc-id": "RFC0100", "errata_status_code": "Verified",
     "errata_type_code": "Technical", "submit_date": "2015-01-01"},
    {"errata_id": 5, "doc-id": "RFC0100", "errata_status_code": "Verified",
     "errata_type_code": "Technical", "submit_date": "2016-01-01"},
    {"errata_id": 6, "doc-id": "RFC0200", "errata_status_code": "Held for Document Update",
     "errata_type_code": "Technical", "submit_date": "2012-06-01"},
    {"errata_id": 7, "doc-id": "RFC0300", "errata_status_code": "Held for Document Update",
     "errata_type_code": "Editorial", "submit_date": "2013-06-01"},
    {"errata_id": 8, "doc-id": "RFC0400", "errata_status_code": "Held for Document Update",
     "errata_type_code": "Technical", "submit_date": "2008-06-01"},
    {"errata_id": 9, "doc-id": "RFC0500", "errata_status_code": "Held for Document Update",
     "errata_type_code": "Technical", "submit_date": "2014-06-01"},
    {"errata_id": 10, "doc-id": "RFC0600", "errata_status_code": "Rejected",
     "errata_type_code": "Technical", "submit_date": "2015-01-01"},
]


class TestHelpers(unittest.TestCase):
    def test_rfc_num(self):
        self.assertEqual(job.rfc_num("RFC0100"), 100)
        self.assertEqual(job.rfc_num("RFC2119"), 2119)
        self.assertIsNone(job.rfc_num("BCP14"))
        self.assertIsNone(job.rfc_num(None))

    def test_parse_date(self):
        self.assertAlmostEqual(job.parse_date("2008-06-01"), 2008 + 5.5 / 12.0, places=4)
        self.assertIsNone(job.parse_date(""))
        self.assertIsNone(job.parse_date("not-a-date"))

    def test_status_group_uppercase(self):
        self.assertEqual(job.status_group("INTERNET STANDARD"), "Standards Track")
        self.assertEqual(job.status_group("PROPOSED STANDARD"), "Standards Track")
        self.assertEqual(job.status_group("INFORMATIONAL"), "Informational")
        # the casing bug guard: "Standards Track" is NOT a raw index value
        self.assertEqual(job.status_group("Standards Track"), "Unknown")

    def test_km_median_not_reached(self):
        # a curve that never crosses 0.5 -> median None
        curve = job.km_survival([5.0, 6.0, 7.0], [1, 0, 0])
        self.assertIsNone(job.km_median(curve))

    def test_km_median_reached(self):
        curve = job.km_survival([2.0, 2.0, 3.0, 4.0], [1, 0, 1, 0])
        self.assertAlmostEqual(job.km_median(curve), 3.0, places=6)


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.entries = job.parse_index(INDEX_XML)
        self.s = job.analyze(ERRATA, self.entries)

    def test_index_parsed(self):
        self.assertEqual(self.s["n_rfc_index_entries"], 9)
        self.assertEqual(self.entries[100]["pub_status"], "Standards Track")
        self.assertEqual(self.entries[200]["pub_status"], "Informational")
        self.assertTrue(self.entries[100]["updated_by"] == [900])
        self.assertTrue(self.entries[300]["obsoleted_by"] == [950])

    def test_status_histogram(self):
        self.assertEqual(self.s["errata_status_histogram"],
                         {"Verified": 5, "Held for Document Update": 4, "Rejected": 1})
        self.assertEqual(self.s["n_errata_total"], 10)

    def test_hfdu_join_and_p1(self):
        h = self.s["hfdu"]
        self.assertEqual(h["n_hfdu_errata"], 4)
        self.assertEqual(h["n_distinct_rfcs_with_hfdu"], 4)
        self.assertEqual(h["n_hfdu_rfcs_in_index"], 4)
        # RFC300 (obsoleted) and RFC400 (updated) are revised; RFC200/500 are not
        self.assertEqual(h["n_hfdu_rfcs_revised"], 2)
        self.assertAlmostEqual(h["revised_fraction"], 0.5, places=6)
        self.assertTrue(self.s["predictions"]["P1_hfdu_revised_gt_40pct"]["result"])
        self.assertEqual(h["submit_date_parsed"], 4)
        self.assertEqual(h["submit_date_missing"], 0)

    def test_p2_by_status(self):
        bs = self.s["hfdu_revision_by_status"]
        self.assertEqual(bs["Standards Track"]["n"], 2)   # RFC300, RFC500
        self.assertAlmostEqual(bs["Standards Track"]["rate"], 0.5, places=6)
        self.assertEqual(bs["Informational"]["n"], 2)     # RFC200, RFC400
        self.assertAlmostEqual(bs["Informational"]["rate"], 0.5, places=6)
        # 0.5 > 0.5 is False
        self.assertFalse(self.s["predictions"]["P2_stdtrack_resolved_gt_informational"]["result"])

    def test_p3_km_path(self):
        km = self.s["hfdu_resolution_km"]
        self.assertEqual(km["n_events_total"], 4)
        self.assertEqual(km["n_resolved"], 2)             # RFC300, RFC400 resolved
        self.assertAlmostEqual(km["median_years_to_resolution_reached"], 3.0, places=6)
        # only 4 events (< 20) -> not gradable, so P3 result is False
        self.assertFalse(km["gradable"])
        self.assertFalse(self.s["predictions"]["P3_km_median_not_reached"]["result"])

    def test_p4_verified_most_common(self):
        p4 = self.s["predictions"]["P4_verified_most_common"]
        self.assertEqual(p4["most_common_status"], "Verified")
        self.assertTrue(p4["result"])

    def test_render_runs(self):
        txt = job.render(self.s)
        self.assertIn("Held for Document Update", txt)
        self.assertIn("PREDICTIONS", txt)


if __name__ == "__main__":
    unittest.main()
