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
[`PREREG.md`](PREREG.md) were fixed *before* the data were analysed.

## Prior art and what is new here

McQuistin et al., *"Errare humanum est: What do RFC Errata say about Internet
Standards?"* (TMA 2023) is the first statistical study of RFC errata. On HFDU it
reports one cross-sectional number: of the **930** RFCs with HFDU errata, "only
**40%** have been updated or obsoleted by a subsequent RFC" (data to late 2022).
This repo adds three things that paper does not have:

1. a **re-measurement** of that fraction on the 2026 corpus;
2. a breakdown **by publication status** (Standards Track vs Informational and
   others);
3. a **survival curve** for time from the HFDU erratum to the RFC's next
   revision, so the question becomes "how fast, if ever", not only "what share".

No other HFDU-resolution or errata-survival analysis turned up in searches on
2026-10-29 (including the RFC Production Center's errata-process draft, which
gives no such statistics). If you know of one, please open an issue.

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
document is revised in general. A follow-up with a matched errata-free control
group is pre-registered to test exactly this.

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

## Reproduce it

```
python job.py --data-dir <folder with errata.json and rfc-index.xml> --out-dir out
python -m unittest -v
```

Without local copies, `job.py` downloads both files. Pure Python standard
library, no dependencies. `results/run1-summary.json` and
`results/run1-report.txt` are the outputs of the graded run, produced in a sealed
container with network access to the RFC Editor only.

## Limits

- "Revised" is metadata-level (`updated-by` / `obsoleted-by`), not a check that
  the erratum text was incorporated; see the spot-checks.
- The unit is the RFC (its earliest HFDU erratum), not the individual erratum.
- No control group yet: the status comparison is descriptive.
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
