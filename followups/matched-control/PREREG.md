# Pre-registration: does an HFDU erratum predict revision? (matched controls + the 2021 rule change)

**By MV2 of Munim, Inc. Produced with AI agents working in his name. 2026-10-29.**
Pre-registered BEFORE running job.py on the live data. License: Apache-2.0 (code),
CC BY 4.0 (prose/data).

## Why this follow-up
The graded HFDU study (github.com/munimtechnologies/rfc-errata-hfdu-graveyard) found
that 40.9% of RFCs with a "Held for Document Update" (HFDU) erratum were ever revised,
48% for Standards Track vs 21.5% for Informational. It had **no control group**: RFCs
of different status and era are revised at different base rates, and errata of any
kind mark a document that people read closely. This study asks whether an HFDU erratum
is followed by revision **more often than for comparable RFCs**, and whether the IESG's
May 2021 errata statement (which moved typo-like reports from HFDU to Verified) changed
how often reports end up held.

## Data
Same two public files and the same cached volume as the graded study:
`https://www.rfc-editor.org/errata.json` and `https://www.rfc-editor.org/rfc-index.xml`.

## Design (landmark analysis)
- **Arm H (HFDU):** RFCs with >=1 HFDU erratum. Landmark t0 = earliest HFDU
  `submit_date`. Eligible only if the RFC had **no** revision (updated-by or
  obsoleted-by RFC published) before t0.
- **Arm V (Verified-only):** RFCs with >=1 Verified erratum and no HFDU erratum.
  t0 = earliest Verified `submit_date`. Same eligibility rule.
- **Matched errata-free controls (H0 for H, V0 for V):** for each subject, every RFC
  with **no errata record at all**, the same publication year and the same status group
  (Standards Track / Informational / Experimental / BCP / Historic / Unknown),
  published on or before t0 and not revised before t0. Each control inherits the
  subject's t0. If a subject has k controls, each gets weight 1/k, so every subject
  contributes total weight 1 (deterministic, no random sampling). Subjects with no
  eligible control are dropped from the matched comparison (count reported).
- Event = publication of the first revising RFC on or after t0; censored at the
  snapshot (latest publication date in the index). Weighted Kaplan-Meier per arm.
  F(5) = 1 - S(5 years). Lift = F_arm(5) / F_control(5).

## Prior art (checked 2026-10-29)
- McQuistin et al., TMA 2023: one cross-sectional HFDU figure ("of the 930 RFCs that
  have hold for document update errata ... only 40% have been updated or obsoleted");
  no control group, no status breakdown, no time-to-event, data ends 2022, so nothing
  on the 2021 statement's effect.
- draft-rpc-errata-process-04 (2025) describes the 2021 change (three of HFDU's five
  categories moved to Verified) but gives no statistics.
- No published before/after analysis of the 2021 IESG statement found (2 searches).

## Pre-registered predictions (set before running)
- **C1 (errata as attention):** among matched subjects, F_H(5) > F_H0(5): RFCs with an
  HFDU erratum are revised within 5 years more often than matched errata-free RFCs.
  FALSIFIED if F_H(5) <= F_H0(5).
- **C2 (HFDU is no stronger a signal than Verified):** lift_H <= lift_V. A held
  erratum, judged not urgent, should not predict revision more than a verified one.
  FALSIFIED if lift_H > lift_V.
- **C3 (full replacement is rare):** in arm H, counting only `obsoleted-by` as the
  event (the only revision type that re-issues the whole text), S(10 years) > 0.75.
  FALSIFIED if S(10) <= 0.75.
- **C4 (the 2021 statement shrank HFDU):** among processed errata (Verified, HFDU or
  Rejected), the HFDU share for reports submitted June 2021 - Dec 2024 is lower than
  for reports submitted Jan 2018 - Apr 2021. FALSIFIED if the later share >= the
  earlier share. Reported alongside: the same split by type (Technical / Editorial),
  the still-Reported share per window (a processing-lag check), and a histogram of
  `update_date` years (to show whether a system migration rewrote that field).

## Integrity guards
- Raw histograms of every bucketed field are emitted; counts of eligible subjects,
  matched subjects and dropped subjects per arm.
- Pure standard library; self-contained `test_job.py` with hand-computed fixtures.
- Negative or reversed results are reported as they come out.
