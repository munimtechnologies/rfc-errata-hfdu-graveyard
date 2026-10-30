# The "Held for Document Update" RFC-errata graveyard

*Work by Munim, Inc., produced with AI agents working in the name of MV2 of
Munim, Inc. This is independent research. It has had no external review and,
so far, no external engagement; read it as a pre-registered, reproducible
first pass, not an authority.*

When someone reports an error in an IETF RFC, the responsible stream can mark the
report **"Held for Document Update" (HFDU)**: in the IESG's words, "not a
necessary update to the RFC. However, any future update of the document might
consider it." **Does that future update ever come, and how long does it take?**

This repo joins the public RFC Editor errata database to the RFC index and treats
"an HFDU erratum gets a later revision of its RFC" as a time-to-event outcome
(Kaplan-Meier, right-censored at the snapshot). The four predictions in
[`PREREG.md`](PREREG.md) were fixed *before* the data were analysed. A second,
separately pre-registered study (matched controls and the 2021 rule change) is
in [`followups/matched-control/`](followups/matched-control/).

## Prior art and what is new here

McQuistin et al., *"Errare humanum est: What do RFC Errata say about Internet
Standards?"* (TMA 2023) is the first statistical study of RFC errata. On HFDU it
reports one cross-sectional number: of the **930** RFCs with HFDU errata, "only
**40%** have been updated or obsoleted by a subsequent RFC" (data to late 2022).
This repo adds what that paper does not have:

1. a **re-measurement** of that fraction on the 2026 corpus;
2. a breakdown **by publication status** (Standards Track vs Informational and
   others);
3. a **survival curve** for time from the HFDU erratum to the RFC's next
   revision, so the question becomes "how fast, if ever", not only "what share";
4. a **matched errata-free control group**, so "how often" is compared with
   comparable RFCs that have no errata at all;
5. a **before/after measurement** of the IESG's May 2021 errata statement.

No other HFDU-resolution or errata-survival analysis turned up in searches on
2026-10-29 and 2026-10-30. The RFC Production Center's errata-process draft
(draft-rpc-errata-process-05, March 2026) describes the 2021 change but gives no
statistics. If you know of such an analysis, please open an issue.

## Data

Two public files, one join:

- `https://www.rfc-editor.org/errata.json`: 8,116 errata reports. Fields used:
  `doc-id`, `errata_status_code`, `errata_type_code`, `submit_date`.
- `https://www.rfc-editor.org/rfc-index.xml`: 9,851 RFC entries with publication
  date, `publication-status`, `obsoleted-by` and `updated-by`.

An RFC counts as **revised** if it has any `obsoleted-by` or `updated-by` entry.
For the survival curve, a revision **resolves** the HFDU backlog of an RFC only if
the revising RFC was published on or after the RFC's *earliest* HFDU erratum.
Dates are fractional years at the month mid-point.

## Results (snapshot 2026.79)

Status of all 8,116 errata: Verified 3,758; Held for Document Update 2,431;
Rejected 1,167; Reported (not yet processed) 760. Technical 4,414; Editorial 3,702.

- **1,113** RFCs carry at least one HFDU erratum (McQuistin et al.: 930).
- **455 of 1,113 (40.9%)** have ever been updated or obsoleted - essentially the
  same share as the 40% reported for 2022, after four more years.
- Counting only revisions published **after** the erratum: **389 of 1,112
  (35.0%)** (one erratum has no submit date). The gap of about 66 RFCs is
  RFCs revised only *before* their first HFDU erratum, so that revision cannot
  have folded it in.
- Kaplan-Meier, time from first HFDU erratum to the next revision:
  **S(2y)=0.891, S(5y)=0.769, S(10y)=0.660**, final 0.587. The curve never
  reaches 0.5. Among the 389 resolved, the median wait was **3.75 years**.

Revision rate of HFDU RFCs, by publication status:

| Status group | RFCs with HFDU | ever revised | rate |
|--------------|----|----|------|
| Standards Track | 758 | 364 | 0.480 |
| Unknown | 15 | 6 | 0.400 |
| Experimental | 43 | 16 | 0.372 |
| Best Current Practice | 51 | 17 | 0.333 |
| Informational | 242 | 52 | 0.215 |
| Historic | 4 | 0 | 0.000 |

## The predictions, graded

| ID | Prediction | Verdict |
|----|------------|---------|
| P1 | HFDU-RFC revised fraction > 0.40 (McQuistin 2022) | **HELD, barely** (0.409) |
| P2 | Standards Track HFDU RFCs revised more often than Informational | **HELD** (0.480 vs 0.215) |
| P3 | KM median time-to-resolution not reached | **HELD** (S never below 0.587) |
| P4 | Verified is the most common status and exceeds HFDU (parse check) | **HELD** (3,758 vs 2,431) |

**What this says.** "Held for Document Update" mostly means *held*. Ten years
after an HFDU erratum, about two thirds of the affected RFCs still have no later
revision of any kind, and the overall share revised has not moved since 2022:
the HFDU list grew from 930 to 1,113 RFCs, and the share stayed at about 40%.

**P1 is a near-tie, not a trend.** 0.409 against 0.40 is inside any reasonable
noise band; the honest reading is "unchanged", not "improving".

**P2 is probably not about HFDU.** In the companion study of the same index,
Standards-Track RFCs are obsoleted within 10 years at about 2.5 times the
Informational rate (0.171 vs 0.069) whether or not they have errata. The 2.2x
gap here is the same size, so it most likely reflects how actively each kind of
document is revised in general. The matched-control follow-up below compares
like with like.

## Spot-checks (verified live on errata.rfc-editor.org, 2026-10-29)

Both spot-checks show the measure is **generous**: "the RFC was later revised"
does not mean "the held erratum was folded in".

- **RFC 5321 (SMTP, 2008).** Six HFDU errata (earliest: 1543, 2008-10-08).
  The only later revision is RFC 7504 (2015), which adds SMTP reply codes 521
  and 556 and does not fold in the held errata. This study counts RFC 5321 as
  "resolved" after about 6.7 years; in fact its held errata await a full
  successor, and no RFC obsoletes RFC 5321 as of this snapshot.
- **RFC 7230 (HTTP/1.1, 2014).** Seven HFDU errata (earliest: 4189, 2014-11-26).
  The first later revision is RFC 8615 (2019, well-known URIs), counted here as
  resolution after about 4.5 years; the actual replacement, RFC 9110 and
  RFC 9112, came in 2022, about 7.6 years after the erratum.

So the 35-41% revision figures and the survival curve are **upper bounds** on
how often, and how quickly, held errata are really incorporated. The true
backlog is larger and older than shown.

## Follow-up: matched controls and the 2021 rule change (run 2)

Pre-registration, code and tests: [`followups/matched-control/`](followups/matched-control/).
Outputs: `results/run2-control-summary.json` and `results/run2-control-report.txt`.
Same files and snapshot as above.

**Design.** Landmark analysis. Each RFC with an HFDU erratum enters at its
earliest HFDU `submit_date` (t0), if it had no revision before t0. Its
controls are all RFCs with **no errata record at all**, the same publication
year and the same status group, published by t0 and unrevised at t0; each
subject's controls share a total weight of 1. A second arm does the same for
RFCs whose errata are Verified but never held. The event is the first revising
RFC (Updates or Obsoletes) published on or after t0.

| Arm | eligible | matched | revised within 5y (subjects) | same for matched controls | lift |
|-----|----|----|----|----|----|
| HFDU, any revision | 973 | 963 | 0.199 | 0.084 | 2.37 |
| Verified-only, any revision | 1,076 | 1,071 | 0.177 | 0.086 | 2.05 |
| HFDU, Obsoletes only | 1,091 | 1,079 | 0.068 | 0.035 | 1.95 |

(139 HFDU RFCs were already revised before their first HFDU erratum and are
excluded from the first arm; 10 had no eligible control.)

The 2021 change: among processed errata (Verified, HFDU or Rejected), the share
marked HFDU was **0.357** for reports submitted January 2018 to April 2021
(377 of 1,055) and **0.182** for reports submitted June 2021 to December 2024
(167 of 919). Editorial reports: 0.392 to 0.130. Technical reports: 0.327 to
0.225.

| ID | Prediction (fixed before the run) | Verdict |
|----|------------|---------|
| C1 | HFDU RFCs revised within 5y more often than matched errata-free RFCs | **HELD** (0.199 vs 0.084) |
| C2 | HFDU lift no higher than the Verified-only lift | **FAILED** (2.37 vs 2.05) |
| C3 | HFDU RFCs, Obsoletes only: S(10y) > 0.75 | **HELD** (0.876) |
| C4 | HFDU share of processed errata lower after the May 2021 statement | **HELD** (0.357 to 0.182) |

**What this adds.**

- **Held errata are not a sign of neglect.** RFCs with an HFDU erratum are
  revised within five years about 2.4 times as often as comparable RFCs with no
  errata (C1). Errata mark documents that people read and use, and those get
  revised more. The "graveyard" above is real in absolute terms (four in five
  see no revision within five years), but that is because RFCs are rarely
  revised at all, not because held errata are ignored more than others.
- **Holding an erratum does not lower the odds of revision.** C2 predicted the
  HFDU lift would be no higher than the Verified-only lift; it came out a
  little higher (2.37 vs 2.05). No confidence interval was pre-registered, so
  read this as "about the same, perhaps slightly higher", not as a strong effect.
- **Full replacement stays rare** (C3): 88% of HFDU RFCs are not obsoleted
  within 10 years of the erratum, so most held errata can only ever be folded
  in by an Update or a future replacement.
- **The 2021 change roughly halved the share of reports that end up held**
  (C4), and most of the drop is in editorial reports, which is what the
  statement's wording targets (typos and grammar moved from HFDU to Verified).
  Processing lag cannot explain it: 204 reports from the later window are
  still unprocessed, and even if every one were held, the later share would be
  371 of 1,123 = 0.330, still below 0.357. But the same year the IESG also
  asked the RFC Production Center to do the first review of editorial reports
  (draft-rpc-errata-process-05), so the drop cannot be pinned on the
  statement's wording alone. That review also covered the backlog of older open
  editorial reports, which, if anything, would lower the *earlier* window's
  share and understate the change.

**Limits of the follow-up.** Matching uses only publication year and status
group; errata-bearing RFCs differ in other ways (deployment, length, area).
The 2021 statement applies to the IETF stream; the before/after split here
covers all streams. The `update_date` field is not used (5,230 of 8,116 records
carry a 2019 value, consistent with a system migration rewriting it).

## Reproduce it

```
python job.py --data-dir <folder with errata.json and rfc-index.xml> --out-dir out
python -m unittest -v
cd followups/matched-control && python job.py --data-dir <same folder> --out-dir out && python -m unittest -v
```

Without local copies, `job.py` downloads both files. Pure Python standard
library, no dependencies. Everything in `results/` was produced in a sealed
container with network access to the RFC Editor only.

## Limits

- "Revised" is metadata-level (`updated-by` / `obsoleted-by`), not a check that
  the erratum text was incorporated; see the spot-checks.
- The unit is the RFC (its earliest HFDU erratum), not the individual erratum.
- The errata database starts around 2000, so HFDU status (introduced in 2008)
  can be applied to old reports retroactively; submit dates, not hold dates,
  are used.
- One snapshot of two files.

## Related

Companion study on the same RFC index:
https://github.com/munimtechnologies/rfc-obsolescence-survival

## Licence

Code: Apache-2.0 (see [`LICENSE`](LICENSE)). Data and results (`results/`):
CC BY 4.0. Attribute to "MV2, Munim, Inc."
