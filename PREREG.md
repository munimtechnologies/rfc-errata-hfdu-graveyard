# Pre-registration: the "Held for Document Update" RFC-errata graveyard

**By MV2 of Munim, Inc. Produced with AI agents working in his name. 2026-10-29.**
Pre-registered BEFORE running job.py on the live data. License: Apache-2.0 (code),
CC BY 4.0 (prose/data).

## Question
When an RFC erratum is filed and the stream's leadership marks it **"Held for Document
Update" (HFDU)** -- meaning "not a necessary correction now, but a future revision of
the RFC should consider folding it in" -- does that future revision ever actually happen?
And if it does, how long does it take?

## Data (two public files, one join)
1. `https://www.rfc-editor.org/errata.json` -- the full RFC Editor errata database.
   Confirmed fields (IETF "RFC Errata Merge Tool" RFP, 2019): an array of objects with
   `errata_id`, `doc-id` (the RFC, e.g. "RFC2119"), `errata_status_code` in
   {`Reported`, `Verified`, `Rejected`, `Held for Document Update`}, `errata_type_code`
   in {`Technical`, `Editorial`}, `submit_date` ("YYYY-MM-DD"), `update_date`.
2. `https://www.rfc-editor.org/rfc-index.xml` -- the RFC Editor index (already used and
   cached by this field's obsolescence study). Gives each RFC its publication date,
   `publication-status` (UPPERCASE maturity levels), `stream`, `obsoleted-by` and
   `updated-by`.
**Join:** an RFC is "revised" if its `obsoleted-by` OR `updated-by` list is non-empty.
A revision "resolves" an HFDU erratum only if the revising RFC's publication date is on
or after the erratum's `submit_date` (HFDU is explicitly about *future* revisions).

## Prior art and the exact delta (hard check, 2026-10-29)
- **McQuistin et al., "Errare humanum est: What do RFC Errata say about Internet
  Standards?", TMA 2023** (Glasgow). First statistical study of RFC errata: 6,759 reports
  Jan-2001..Dec-2022 over 2,240 RFCs; status shares (42.5% Verified, 30.3% HFDU, 13%
  Rejected, 14.2% unprocessed); submitter patterns; errata-per-RFC by type (Proposed Std
  1.01, Internet Std 2.17, Informational 0.52). Their one HFDU-resolution fact: **"for
  HFDU errata, only 40% of the RFCs they were filed against have been updated or
  obsoleted by a subsequent RFC"** -- a single cross-sectional number as of ~Dec 2022.
- **What they did NOT do, and this study does:**
  (a) **re-measure** that HFDU-resolution fraction on the live 2026 corpus (does it move
      with ~4 more years of revisions?);
  (b) break the HFDU-resolution rate down **by the RFC's publication status**
      (Standards Track vs Informational), which they never report;
  (c) treat HFDU resolution as a **time-to-event** and estimate the Kaplan-Meier
      survival curve of "still-unresolved HFDU" with right-censoring at the snapshot --
      i.e. *how long* the backlog takes to clear, not just a point fraction.
- No other RFC-errata survival or per-status-resolution analysis found (4 searches +
  the TMA paper + the RFC Editor errata-definitions page). RFCs/errata are not worked by
  any sibling field.

## Pre-registered predictions (falsifiable; set before running)
- **P1 (replication + extension, directional):** among RFCs that carry >=1 HFDU erratum,
  the fraction that have since been updated or obsoleted by a later RFC is **> 0.40**
  (McQuistin's Dec-2022 figure), because ~4 more years have passed. FALSIFIED if <= 0.40.
- **P2 (novel, reversal candidate):** Standards-Track RFCs with an HFDU erratum are
  revised at a **higher** rate than Informational RFCs with an HFDU erratum
  (Standards-Track docs are revised more actively). FALSIFIED if Std-Track rate <=
  Informational rate.
- **P3 (novel, directional):** the Kaplan-Meier **median time-to-resolution is NOT
  reached** -- most HFDU errata are never folded in by a subsequent revision (survival
  curve stays above 0.5). FALSIFIED if the KM curve crosses 0.5. Graded only if
  `submit_date` parses for the HFDU errata; otherwise reported as "unparsed" with the
  raw field manifest.
- **P4 (replication / parse check, directional):** across all errata, **`Verified` is
  the single most common status** and its count exceeds `Held for Document Update`
  (McQuistin: 42.5% vs 30.3%). FALSIFIED if HFDU >= Verified. This doubles as a check
  that the status field parsed correctly.

## Method / integrity guards
- Pure Python standard library; one sealed container; outputs to /out/summary.json +
  report.txt. A self-contained `test_job.py` (inline fixtures with the real UPPERCASE
  maturity strings and the exact `Held for Document Update` status) guards the logic.
- **Methodology lesson carried from the obsolescence P4 bug:** emit a RAW histogram of
  every categorical field I bucket (`errata_status_code`, `errata_type_code`,
  `publication-status`) and the first errata record's key names, so a key-name or
  value-casing mismatch is visible, not silent. Any prediction whose field fails to
  parse is reported "unparsed", never silently 0.
- Report a NEGATIVE or reversed result honestly. A reversal of P2 (Informational
  resolved faster) or a surprising P1/P3 is the most interesting outcome, not a failure.
