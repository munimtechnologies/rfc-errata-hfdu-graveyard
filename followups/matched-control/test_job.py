#!/usr/bin/env python3
"""Self-contained tests for the HFDU matched-control study.

Inline fixtures use the exact live strings: "Held for Document Update" and the
UPPERCASE publication-status maturity levels of rfc-index.xml. Expected values are
computed by hand in the comments. Run: python -m unittest -v
"""
import unittest

import job

# An entry with only a year is dated at mid-year: Y + 5.5/12.
INDEX_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rfc-index xmlns="http://www.rfc-editor.org/rfc-index">
  <rfc-entry><doc-id>RFC0010</doc-id><date><year>2010</year></date>
    <publication-status>PROPOSED STANDARD</publication-status>
    <updated-by><doc-id>RFC0090</doc-id></updated-by></rfc-entry>
  <rfc-entry><doc-id>RFC0020</doc-id><date><year>2010</year></date>
    <publication-status>PROPOSED STANDARD</publication-status></rfc-entry>
  <rfc-entry><doc-id>RFC0030</doc-id><date><year>2010</year></date>
    <publication-status>PROPOSED STANDARD</publication-status>
    <obsoleted-by><doc-id>RFC0095</doc-id></obsoleted-by></rfc-entry>
  <rfc-entry><doc-id>RFC0040</doc-id><date><year>2010</year></date>
    <publication-status>PROPOSED STANDARD</publication-status>
    <updated-by><doc-id>RFC0096</doc-id></updated-by></rfc-entry>
  <rfc-entry><doc-id>RFC0050</doc-id><date><year>2010</year></date>
    <publication-status>INFORMATIONAL</publication-status></rfc-entry>
  <rfc-entry><doc-id>RFC0060</doc-id><date><year>2010</year></date>
    <publication-status>INFORMATIONAL</publication-status>
    <updated-by><doc-id>RFC0097</doc-id></updated-by></rfc-entry>
  <rfc-entry><doc-id>RFC0070</doc-id><date><year>2010</year></date>
    <publication-status>PROPOSED STANDARD</publication-status>
    <obsoleted-by><doc-id>RFC0095</doc-id></obsoleted-by></rfc-entry>
  <rfc-entry><doc-id>RFC0090</doc-id><date><year>2014</year></date>
    <publication-status>PROPOSED STANDARD</publication-status></rfc-entry>
  <rfc-entry><doc-id>RFC0095</doc-id><date><year>2011</year></date>
    <publication-status>PROPOSED STANDARD</publication-status></rfc-entry>
  <rfc-entry><doc-id>RFC0096</doc-id><date><year>2016</year></date>
    <publication-status>PROPOSED STANDARD</publication-status></rfc-entry>
  <rfc-entry><doc-id>RFC0097</doc-id><date><year>2013</year></date>
    <publication-status>PROPOSED STANDARD</publication-status></rfc-entry>
  <rfc-entry><doc-id>RFC0099</doc-id><date><year>2026</year></date>
    <publication-status>INFORMATIONAL</publication-status></rfc-entry>
</rfc-index>
"""

H = "Held for Document Update"


def rec(doc, status, etype, submit, update=None):
    r = {"doc-id": doc, "errata_status_code": status, "errata_type_code": etype,
         "submit_date": submit}
    if update:
        r["update_date"] = update
    return r


ERRATA = [
    # landmark subjects
    rec("RFC0010", H, "Technical", "2012-06-01"),           # t0 = 2012.458
    rec("RFC0010", "Verified", "Editorial", "2011-01-01"),  # RFC10 has HFDU -> not in V arm
    rec("RFC0070", H, "Technical", "2015-01-01"),           # obsoleted 2011 -> revised before t0
    rec("RFC0050", "Verified", "Technical", "2011-06-01", "2024-06-30 12:00:00"),
    # 2021-regime records on an RFC that is not in the index
    rec("RFC0999", H, "Editorial", "2019-03-01"),
    rec("RFC0999", "Verified", "Editorial", "2020-03-01"),
    rec("RFC0999", "Rejected", "Technical", "2018-05-01"),
    rec("RFC0999", H, "Technical", "2019-07-01"),
    rec("RFC0999", "Verified", "Editorial", "2022-01-01"),
    rec("RFC0999", H, "Technical", "2023-01-01"),
    rec("RFC0999", "Verified", "Technical", "2024-01-01"),
    rec("RFC0999", "Reported", "Technical", "2024-06-01"),
    rec("RFC0999", H, "Editorial", "2021-05-15"),           # May 2021: in neither window
]


class TestHelpers(unittest.TestCase):
    def test_parse_date_with_time(self):
        self.assertAlmostEqual(job.parse_date("2024-06-30 12:00:00"),
                               2024 + 5.5 / 12, places=6)
        self.assertIsNone(job.parse_date("n/a"))

    def test_status_group_uppercase(self):
        self.assertEqual(job.status_group("PROPOSED STANDARD"), "Standards Track")
        self.assertEqual(job.status_group("Standards Track"), "Unknown")

    def test_km_weighted(self):
        # at risk 4: t=1 one event (w1) -> 0.75; t=2 censored w1 leaves; t=3 w2 event of 2 -> 0
        curve = job.km_weighted([1.0, 2.0, 3.0], [1, 0, 1], [1.0, 1.0, 2.0])
        self.assertEqual(len(curve), 2)
        self.assertAlmostEqual(curve[0][1], 0.75, places=9)
        self.assertAlmostEqual(curve[1][1], 0.0, places=9)
        self.assertAlmostEqual(job.survival_at(curve, 2.5), 0.75, places=9)
        self.assertAlmostEqual(job.survival_at(curve, 0.5), 1.0, places=9)

    def test_landmark(self):
        entries = job.parse_index(INDEX_XML)
        t0 = job.parse_date("2012-06-01")
        snap = 2026 + 5.5 / 12
        d, e = job.landmark(entries[10], entries, t0, snap)
        self.assertAlmostEqual(d, 2.0, places=6)
        self.assertEqual(e, 1)
        self.assertIsNone(job.landmark(entries[30], entries, t0, snap))   # revised 2011
        d, e = job.landmark(entries[20], entries, t0, snap)
        self.assertAlmostEqual(d, 14.0, places=6)
        self.assertEqual(e, 0)


class TestAnalyze(unittest.TestCase):
    def setUp(self):
        self.entries = job.parse_index(INDEX_XML)
        self.s = job.analyze(ERRATA, self.entries)

    def test_counts(self):
        self.assertEqual(self.s["n_errata_total"], 13)
        self.assertEqual(self.s["n_rfc_index_entries"], 12)
        # RFCs with errata: 10, 70, 50, 999
        self.assertEqual(self.s["n_rfcs_with_any_errata"], 4)
        # errata-free and in the index: 20,30,40,60,90,95,96,97,99
        self.assertEqual(self.s["n_errata_free_rfcs"], 9)
        self.assertEqual(self.s["update_date_year_histogram"], {"2024": 1})

    def test_hfdu_arm(self):
        a = self.s["arm_hfdu"]
        c = a["counts"]
        self.assertEqual(c["subjects"], 3)            # 10, 70, 999
        self.assertEqual(c["missing_from_index"], 1)  # 999
        self.assertEqual(c["revised_before_t0"], 1)   # 70
        self.assertEqual(c["eligible"], 1)            # 10
        self.assertEqual(c["matched"], 1)
        self.assertEqual(c["control_records"], 2)     # 20 (censored 14y), 40 (event 4y); 30 excluded
        self.assertAlmostEqual(a["matched_subjects"]["F5"], 1.0, places=4)
        self.assertAlmostEqual(a["matched_controls"]["F5"], 0.5, places=4)
        self.assertAlmostEqual(a["lift_F5"], 2.0, places=4)

    def test_verified_arm(self):
        a = self.s["arm_verified_only"]
        c = a["counts"]
        self.assertEqual(c["subjects"], 1)            # only 50 (10 and 999 have HFDU)
        self.assertEqual(c["eligible"], 1)
        self.assertEqual(c["matched"], 1)             # control 60, event 2y
        self.assertAlmostEqual(a["matched_subjects"]["F5"], 0.0, places=4)
        self.assertAlmostEqual(a["matched_controls"]["F5"], 1.0, places=4)
        self.assertAlmostEqual(a["lift_F5"], 0.0, places=4)

    def test_obsoleted_only_arm(self):
        a = self.s["arm_hfdu_obsoleted_only"]
        self.assertEqual(a["counts"]["eligible"], 1)  # 10 (never obsoleted); 70 obsoleted pre-t0
        self.assertAlmostEqual(a["all_eligible"]["S10"], 1.0, places=4)

    def test_regime(self):
        r = self.s["regime_2021"]
        early, late = r["early_2018_to_2021apr"], r["late_2021jun_to_2024"]
        self.assertEqual(early["n"], 4)
        self.assertAlmostEqual(early["hfdu_share_of_processed"], 0.5, places=4)
        self.assertEqual(late["n"], 4)
        self.assertAlmostEqual(late["hfdu_share_of_processed"], 0.3333, places=4)
        self.assertAlmostEqual(late["reported_share"], 0.25, places=4)
        self.assertAlmostEqual(early["hfdu_share_by_type"]["Editorial"], 0.5, places=4)

    def test_predictions(self):
        p = self.s["predictions"]
        self.assertTrue(p["C1_hfdu_revised_more_than_matched_controls"]["result"])
        self.assertFalse(p["C2_hfdu_lift_not_above_verified_lift"]["result"])  # 2.0 > 0.0
        self.assertTrue(p["C3_hfdu_obsoleted_S10_above_0.75"]["result"])
        self.assertTrue(p["C4_hfdu_share_fell_after_2021_statement"]["result"])

    def test_render_runs(self):
        txt = job.render(self.s)
        self.assertIn("PREDICTIONS", txt)


if __name__ == "__main__":
    unittest.main()
