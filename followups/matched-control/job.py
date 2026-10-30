#!/usr/bin/env python3
"""Does an RFC erratum "Held for Document Update" predict revision?

Follow-up to the HFDU graveyard study. A landmark analysis compares RFCs whose first
HFDU erratum is at time t0 with matched errata-free RFCs (same publication year and
status group, at risk at t0), and does the same for Verified-only RFCs. It also checks
whether the IESG's May 2021 errata statement shrank the share of reports that end up
held. Four pre-registered predictions (C1-C4) are graded; see PREREG.md.

Data (public): https://www.rfc-editor.org/errata.json and
https://www.rfc-editor.org/rfc-index.xml.
Pure standard library. By MV2 of Munim, Inc.; produced with AI agents in his name.
"""
import argparse
import glob
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

ERRATA_URL = "https://www.rfc-editor.org/errata.json"
INDEX_URL = "https://www.rfc-editor.org/rfc-index.xml"

HFDU = "Held for Document Update"  # exact errata_status_code string
VERIFIED = "Verified"
REJECTED = "Rejected"
REPORTED = "Reported"
PROCESSED = (VERIFIED, HFDU, REJECTED)

BOTH = ("obsoleted_by", "updated_by")
OBS_ONLY = ("obsoleted_by",)

# report-submission windows around the IESG statement of 2021-05-07 (May 2021 excluded)
EARLY = (2018.0, 2021.0 + 4.0 / 12)        # Jan 2018 .. Apr 2021
LATE = (2021.0 + 5.0 / 12, 2025.0)         # Jun 2021 .. Dec 2024

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}

# publication-status maturity levels (uppercase, as they appear in rfc-index.xml)
STATUS_GROUPS = {
    "Standards Track": {"PROPOSED STANDARD", "DRAFT STANDARD",
                        "INTERNET STANDARD", "STANDARD"},
    "Informational": {"INFORMATIONAL"},
    "Experimental": {"EXPERIMENTAL"},
    "Best Current Practice": {"BEST CURRENT PRACTICE"},
    "Historic": {"HISTORIC"},
}


def status_group(raw):
    key = (raw or "").strip().upper()
    for group, members in STATUS_GROUPS.items():
        if key in members:
            return group
    return "Unknown"


# ---------- errata.json helpers ----------

def pick(d, *keys):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def rfc_num(doc_id):
    """'RFC2119' -> 2119; non-RFC ids -> None."""
    if doc_id is None:
        return None
    s = str(doc_id).strip().upper()
    if not s.startswith("RFC"):
        return None
    digits = s[3:].lstrip("0") or "0"
    try:
        return int(digits)
    except ValueError:
        return None


def parse_date(s):
    """'YYYY-MM-DD[ hh:mm:ss]' -> fractional year (mid-month). None if unparseable."""
    if not s:
        return None
    parts = str(s).strip().split(" ")[0].split("-")
    try:
        y = int(parts[0])
    except (ValueError, IndexError):
        return None
    if y < 1960 or y > 2100:
        return None
    m = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 6
    if not (1 <= m <= 12):
        m = 6
    return y + (m - 0.5) / 12.0


def load_errata(data_dir):
    for pat in ("errata.json", "*.json"):
        for path in sorted(glob.glob(os.path.join(data_dir, pat))):
            with open(path, "rb") as fh:
                data = json.load(fh)
            if isinstance(data, list) and data:
                return data
    req = urllib.request.Request(ERRATA_URL, headers={"User-Agent": "mv2-munim-research/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.load(resp)


# ---------- rfc-index.xml helpers (same parser as the graveyard study) ----------

def local(tag):
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def child_text(elem, name):
    for c in elem:
        if local(c.tag) == name:
            return (c.text or "").strip()
    return ""


def child_elem(elem, name):
    for c in elem:
        if local(c.tag) == name:
            return c
    return None


def doc_ids_in(elem, container):
    out = []
    cont = child_elem(elem, container)
    if cont is None:
        return out
    for c in cont:
        if local(c.tag) == "doc-id":
            n = rfc_num((c.text or "").strip())
            if n is not None:
                out.append(n)
    return out


def frac_year(year, month):
    m = month if month else 6
    return year + (m - 0.5) / 12.0


def load_index_bytes(data_dir):
    for pat in ("rfc-index.xml", "*.xml"):
        for path in sorted(glob.glob(os.path.join(data_dir, pat))):
            with open(path, "rb") as fh:
                return fh.read()
    req = urllib.request.Request(INDEX_URL, headers={"User-Agent": "mv2-munim-research/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def parse_index(xml_bytes):
    root = ET.fromstring(xml_bytes)
    entries = {}
    for elem in root:
        if local(elem.tag) != "rfc-entry":
            continue
        num = rfc_num(child_text(elem, "doc-id"))
        if num is None:
            continue
        de = child_elem(elem, "date")
        year = month = None
        if de is not None:
            y = child_text(de, "year")
            if y.isdigit():
                year = int(y)
            month = MONTHS.get(child_text(de, "month").strip().lower())
        entries[num] = {
            "num": num,
            "pub": frac_year(year, month) if year else None,
            "obsoleted_by": doc_ids_in(elem, "obsoleted-by"),
            "updated_by": doc_ids_in(elem, "updated-by"),
            "pub_status_raw": (child_text(elem, "publication-status") or "UNKNOWN").strip(),
            "pub_status": status_group(child_text(elem, "publication-status")),
        }
    return entries


# ---------- weighted Kaplan-Meier ----------

def km_weighted(durations, events, weights=None):
    """Kaplan-Meier with case weights. Returns [(time, survival)] at event times."""
    if weights is None:
        weights = [1.0] * len(durations)
    recs = sorted(zip(durations, events, weights), key=lambda r: r[0])
    at_risk = float(sum(w for _d, _e, w in recs))
    curve, s, i, n = [], 1.0, 0, len(recs)
    while i < n:
        t = recs[i][0]
        died = leaving = 0.0
        j = i
        while j < n and recs[j][0] == t:
            if recs[j][1]:
                died += recs[j][2]
            leaving += recs[j][2]
            j += 1
        if died > 0 and at_risk > 0:
            s *= (1.0 - died / at_risk)
            curve.append((t, s))
        at_risk -= leaving
        i = j
    return curve


def survival_at(curve, t):
    s = 1.0
    for (time, surv) in curve:
        if time <= t:
            s = surv
        else:
            break
    return s


# ---------- landmark analysis ----------

def revision_dates(entry, entries, kinds):
    out = []
    for k in kinds:
        for o in entry[k]:
            e2 = entries.get(o)
            if e2 and e2["pub"] is not None:
                out.append(e2["pub"])
    return out


def landmark(entry, entries, t0, snapshot, kinds=BOTH):
    """(duration, event) from t0, or None if the RFC was already revised before t0."""
    dates = revision_dates(entry, entries, kinds)
    if any(d < t0 for d in dates):
        return None
    later = [d for d in dates if d >= t0]
    if later:
        return (min(later) - t0, 1)
    return (max(snapshot - t0, 0.0), 0)


def errata_maps(errata):
    """Histograms, the set of RFCs with any erratum, and first submit date per status."""
    status_hist, type_hist = {}, {}
    any_errata = set()
    has = {HFDU: set(), VERIFIED: set()}
    first = {HFDU: {}, VERIFIED: {}}
    for rec in errata:
        status = pick(rec, "errata_status_code", "status") or "UNKNOWN"
        etype = pick(rec, "errata_type_code", "type") or "UNKNOWN"
        status_hist[status] = status_hist.get(status, 0) + 1
        type_hist[etype] = type_hist.get(etype, 0) + 1
        num = rfc_num(pick(rec, "doc-id", "doc_id", "doc"))
        if num is None:
            continue
        any_errata.add(num)
        if status in has:
            has[status].add(num)
            d = parse_date(pick(rec, "submit_date", "submitted", "date"))
            if d is not None and (num not in first[status] or d < first[status][num]):
                first[status][num] = d
    return status_hist, type_hist, any_errata, has, first


def control_pool(entries, any_errata):
    """{(publication year, status group): [errata-free RFC numbers]}."""
    pool = {}
    for num, e in entries.items():
        if e["pub"] is None or num in any_errata:
            continue
        pool.setdefault((int(e["pub"]), e["pub_status"]), []).append(num)
    return pool


def build_arm(subject_t0, entries, snapshot, pool, kinds=BOTH):
    counts = {"subjects": len(subject_t0), "missing_from_index": 0,
              "revised_before_t0": 0, "eligible": 0, "matched": 0,
              "unmatched": 0, "control_records": 0}
    all_d, all_e = [], []
    m_d, m_e = [], []
    c_d, c_e, c_w = [], [], []
    for num in sorted(subject_t0):
        t0 = subject_t0[num]
        entry = entries.get(num)
        if entry is None or entry["pub"] is None:
            counts["missing_from_index"] += 1
            continue
        r = landmark(entry, entries, t0, snapshot, kinds)
        if r is None:
            counts["revised_before_t0"] += 1
            continue
        counts["eligible"] += 1
        all_d.append(r[0])
        all_e.append(r[1])
        ctrls = []
        for m in pool.get((int(entry["pub"]), entry["pub_status"]), []):
            ce = entries[m]
            if ce["pub"] > t0:
                continue
            cr = landmark(ce, entries, t0, snapshot, kinds)
            if cr is not None:
                ctrls.append(cr)
        if not ctrls:
            counts["unmatched"] += 1
            continue
        counts["matched"] += 1
        m_d.append(r[0])
        m_e.append(r[1])
        w = 1.0 / len(ctrls)
        for cr in ctrls:
            c_d.append(cr[0])
            c_e.append(cr[1])
            c_w.append(w)
    counts["control_records"] = len(c_d)

    def describe(curve):
        return {"S5": round(survival_at(curve, 5), 4),
                "S10": round(survival_at(curve, 10), 4),
                "F5": round(1.0 - survival_at(curve, 5), 4)}

    all_curve = km_weighted(all_d, all_e)
    m_curve = km_weighted(m_d, m_e)
    c_curve = km_weighted(c_d, c_e, c_w)
    f_m = 1.0 - survival_at(m_curve, 5)
    f_c = 1.0 - survival_at(c_curve, 5)
    return {
        "counts": counts,
        "all_eligible": describe(all_curve),
        "matched_subjects": describe(m_curve),
        "matched_controls": describe(c_curve),
        "lift_F5": round(f_m / f_c, 4) if f_c > 0 else None,
    }


def regime(errata):
    """HFDU share of processed errata, by submit window around the 2021 statement."""
    out = {}
    for name, (lo, hi) in (("early_2018_to_2021apr", EARLY), ("late_2021jun_to_2024", LATE)):
        by_status, by_type = {}, {}
        for rec in errata:
            d = parse_date(pick(rec, "submit_date", "submitted", "date"))
            if d is None or not (lo <= d < hi):
                continue
            status = pick(rec, "errata_status_code", "status") or "UNKNOWN"
            etype = pick(rec, "errata_type_code", "type") or "UNKNOWN"
            by_status[status] = by_status.get(status, 0) + 1
            t = by_type.setdefault(etype, {})
            t[status] = t.get(status, 0) + 1

        def share(h):
            processed = sum(h.get(s, 0) for s in PROCESSED)
            return round(h.get(HFDU, 0) / processed, 4) if processed else None

        total = sum(by_status.values())
        out[name] = {
            "n": total,
            "status": by_status,
            "hfdu_share_of_processed": share(by_status),
            "reported_share": round(by_status.get(REPORTED, 0) / total, 4) if total else None,
            "hfdu_share_by_type": {k: share(v) for k, v in sorted(by_type.items())},
        }
    return out


def update_year_hist(errata):
    h = {}
    for rec in errata:
        d = parse_date(pick(rec, "update_date"))
        if d is not None:
            y = str(int(d))
            h[y] = h.get(y, 0) + 1
    return dict(sorted(h.items()))


# ---------- core analysis (importable for tests) ----------

def analyze(errata, entries):
    snapshot = max((e["pub"] for e in entries.values() if e["pub"] is not None),
                   default=2026.5)
    status_hist, type_hist, any_errata, has, first = errata_maps(errata)
    pool = control_pool(entries, any_errata)

    h_t0 = dict(first[HFDU])
    v_t0 = {n: t for n, t in first[VERIFIED].items() if n not in has[HFDU]}

    arm_h = build_arm(h_t0, entries, snapshot, pool, BOTH)
    arm_v = build_arm(v_t0, entries, snapshot, pool, BOTH)
    arm_h_obs = build_arm(h_t0, entries, snapshot, pool, OBS_ONLY)
    reg = regime(errata)

    f_h = arm_h["matched_subjects"]["F5"]
    f_h0 = arm_h["matched_controls"]["F5"]
    c1_gradable = arm_h["counts"]["matched"] > 0
    c1 = c1_gradable and f_h > f_h0

    lift_h, lift_v = arm_h["lift_F5"], arm_v["lift_F5"]
    c2_gradable = lift_h is not None and lift_v is not None
    c2 = c2_gradable and lift_h <= lift_v

    c3_s10 = arm_h_obs["all_eligible"]["S10"]
    c3_gradable = arm_h_obs["counts"]["eligible"] > 0
    c3 = c3_gradable and c3_s10 > 0.75

    early = reg["early_2018_to_2021apr"]["hfdu_share_of_processed"]
    late = reg["late_2021jun_to_2024"]["hfdu_share_of_processed"]
    c4_gradable = early is not None and late is not None
    c4 = c4_gradable and late < early

    return {
        "snapshot_frac_year": round(snapshot, 3),
        "n_errata_total": len(errata),
        "n_rfc_index_entries": len(entries),
        "errata_status_histogram": status_hist,
        "errata_type_histogram": type_hist,
        "n_rfcs_with_any_errata": len(any_errata),
        "n_errata_free_rfcs": sum(len(v) for v in pool.values()),
        "update_date_year_histogram": update_year_hist(errata),
        "arm_hfdu": arm_h,
        "arm_verified_only": arm_v,
        "arm_hfdu_obsoleted_only": arm_h_obs,
        "regime_2021": reg,
        "predictions": {
            "C1_hfdu_revised_more_than_matched_controls": {
                "result": bool(c1), "gradable": c1_gradable,
                "F5_hfdu": f_h, "F5_controls": f_h0},
            "C2_hfdu_lift_not_above_verified_lift": {
                "result": bool(c2), "gradable": c2_gradable,
                "lift_hfdu": lift_h, "lift_verified_only": lift_v},
            "C3_hfdu_obsoleted_S10_above_0.75": {
                "result": bool(c3), "gradable": c3_gradable, "S10": c3_s10},
            "C4_hfdu_share_fell_after_2021_statement": {
                "result": bool(c4), "gradable": c4_gradable,
                "early_share": early, "late_share": late},
        },
    }


def render(s):
    L = ["Does an HFDU RFC erratum predict revision? -- MV2 of Munim, Inc. (AI-produced)",
         "Snapshot: %.2f  errata: %d  RFC index entries: %d  errata-free RFCs: %d"
         % (s["snapshot_frac_year"], s["n_errata_total"], s["n_rfc_index_entries"],
            s["n_errata_free_rfcs"]),
         "Status histogram: " + ", ".join("%s=%d" % kv for kv in sorted(
             s["errata_status_histogram"].items(), key=lambda kv: -kv[1])),
         "update_date years: " + ", ".join("%s=%d" % kv for kv in
                                          s["update_date_year_histogram"].items()),
         ""]
    for key, label in (("arm_hfdu", "HFDU arm (any revision)"),
                       ("arm_verified_only", "Verified-only arm (any revision)"),
                       ("arm_hfdu_obsoleted_only", "HFDU arm (obsoleted only)")):
        a = s[key]
        L.append("%s: %s" % (label, json.dumps(a["counts"])))
        L.append("  all eligible: %s" % json.dumps(a["all_eligible"]))
        L.append("  matched subjects: %s  controls: %s  lift F5: %s"
                 % (json.dumps(a["matched_subjects"]), json.dumps(a["matched_controls"]),
                    a["lift_F5"]))
    L.append("")
    for name, r in s["regime_2021"].items():
        L.append("%s: n=%d hfdu_share=%s reported_share=%s by_type=%s status=%s"
                 % (name, r["n"], r["hfdu_share_of_processed"], r["reported_share"],
                    json.dumps(r["hfdu_share_by_type"]), json.dumps(r["status"])))
    L.append("")
    L.append("PREDICTIONS:")
    for k, v in s["predictions"].items():
        L.append("  %s: %s" % (k, json.dumps(v)))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="/data")
    ap.add_argument("--out-dir", default="/out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    errata = load_errata(args.data_dir)
    entries = parse_index(load_index_bytes(args.data_dir))
    summary = analyze(errata, entries)

    with open(os.path.join(args.out_dir, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    report = render(summary)
    with open(os.path.join(args.out_dir, "report.txt"), "w") as fh:
        fh.write(report + "\n")
    print(report)


if __name__ == "__main__":
    sys.exit(main())
