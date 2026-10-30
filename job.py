#!/usr/bin/env python3
"""The "Held for Document Update" RFC-errata graveyard.

Does an RFC erratum marked "Held for Document Update" (HFDU) ever get folded into a
later revision of the RFC, and how long does it take? We join the public RFC Editor
errata database to the RFC index, re-measure McQuistin et al. (TMA 2023)'s single
cross-sectional "40% of HFDU RFCs were ever revised" fact on the live 2026 corpus,
break it down by publication status, and estimate the Kaplan-Meier survival curve of
"still-unresolved HFDU" with right-censoring at the snapshot date. Four pre-registered
predictions (P1-P4) are graded; see PREREG.md for the exact deltas vs prior art.

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


# ---------- errata.json helpers (robust to RFP key-name variants) ----------

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
    """'YYYY-MM-DD' -> fractional year (mid-month). Returns None if unparseable."""
    if not s:
        return None
    parts = str(s).strip().split("-")
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


# ---------- rfc-index.xml helpers (proven in the obsolescence study) ----------

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
            "stream": (child_text(elem, "stream") or "Unknown").strip(),
        }
    return entries


# ---------- Kaplan-Meier (proven) ----------

def km_survival(durations, events):
    pairs = sorted(zip(durations, events), key=lambda p: p[0])
    n = len(pairs)
    curve, s, i = [], 1.0, 0
    while i < n:
        t = pairs[i][0]
        at_risk = n - i
        d = 0
        j = i
        while j < n and pairs[j][0] == t:
            d += pairs[j][1]
            j += 1
        if d > 0:
            s *= (1.0 - d / at_risk)
            curve.append((t, s, at_risk, d))
        i = j
    return curve


def survival_at(curve, t):
    s = 1.0
    for (time, surv, _ar, _d) in curve:
        if time <= t:
            s = surv
        else:
            break
    return s


def km_median(curve):
    for (time, surv, _ar, _d) in curve:
        if surv <= 0.5:
            return time
    return None


def quantile(sorted_vals, q):
    if not sorted_vals:
        return None
    idx = q * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


# ---------- core analysis (importable for tests) ----------

def analyze(errata, entries):
    """errata: list of dicts; entries: {rfc_num: entry}. Returns summary dict."""
    snapshot = max((e["pub"] for e in entries.values() if e["pub"] is not None),
                   default=2026.5)

    # Raw histograms + manifest (methodology guard).
    status_hist, type_hist = {}, {}
    first_keys = sorted(errata[0].keys()) if errata else []
    # earliest HFDU submit date per RFC; and whether each RFC has any HFDU erratum
    hfdu_rfcs = set()
    hfdu_earliest = {}        # rfc_num -> earliest HFDU frac-year (if date parses)
    n_date_parsed = n_date_missing = 0
    for rec in errata:
        status = pick(rec, "errata_status_code", "status") or "UNKNOWN"
        etype = pick(rec, "errata_type_code", "type") or "UNKNOWN"
        status_hist[status] = status_hist.get(status, 0) + 1
        type_hist[etype] = type_hist.get(etype, 0) + 1
        if status != HFDU:
            continue
        num = rfc_num(pick(rec, "doc-id", "doc_id", "doc"))
        if num is None:
            continue
        hfdu_rfcs.add(num)
        d = parse_date(pick(rec, "submit_date", "submitted", "date"))
        if d is None:
            n_date_missing += 1
        else:
            n_date_parsed += 1
            if num not in hfdu_earliest or d < hfdu_earliest[num]:
                hfdu_earliest[num] = d

    def is_revised(entry):
        return bool(entry["obsoleted_by"] or entry["updated_by"])

    def revision_pub_dates(entry):
        out = []
        for o in entry["obsoleted_by"] + entry["updated_by"]:
            e2 = entries.get(o)
            if e2 and e2["pub"] is not None:
                out.append(e2["pub"])
        return out

    # P1: among HFDU RFCs present in the index, fraction ever revised.
    hfdu_in_index = [n for n in hfdu_rfcs if n in entries]
    n_hfdu_idx = len(hfdu_in_index)
    n_hfdu_revised = sum(1 for n in hfdu_in_index if is_revised(entries[n]))
    p1_rate = (n_hfdu_revised / n_hfdu_idx) if n_hfdu_idx else None
    p1 = (p1_rate is not None) and (p1_rate > 0.40)

    # P2: revision rate of HFDU RFCs by publication status.
    by_status = {}
    for grp in ["Standards Track", "Informational", "Experimental",
                "Best Current Practice", "Historic", "Unknown"]:
        members = [n for n in hfdu_in_index if entries[n]["pub_status"] == grp]
        rev = sum(1 for n in members if is_revised(entries[n]))
        by_status[grp] = {"n": len(members), "revised": rev,
                          "rate": (rev / len(members)) if members else None}
    st_rate = by_status["Standards Track"]["rate"]
    info_rate = by_status["Informational"]["rate"]
    p2 = (st_rate is not None and info_rate is not None and st_rate > info_rate)

    # P3: KM survival of time from earliest HFDU submit_date to first subsequent revision.
    durations, events, ttr = [], [], []
    for n, erratum_date in hfdu_earliest.items():
        entry = entries.get(n)
        if entry is None:
            continue
        later = [d for d in revision_pub_dates(entry) if d >= erratum_date]
        if later:
            dur = min(later) - erratum_date
            durations.append(max(dur, 0.0))
            events.append(1)
            ttr.append(max(dur, 0.0))
        else:
            durations.append(max(snapshot - erratum_date, 0.0))
            events.append(0)
    p3_gradable = len(events) >= 20 and n_date_parsed > 0
    curve = km_survival(durations, events) if durations else []
    km_med = km_median(curve) if curve else None
    final_surv = curve[-1][1] if curve else 1.0
    ttr_sorted = sorted(ttr)
    p3 = bool(p3_gradable and km_med is None)  # median not reached

    # P4: Verified is the single most common status, and > HFDU count.
    n_verified = status_hist.get("Verified", 0)
    n_hfdu_total = status_hist.get(HFDU, 0)
    most_common_status = max(status_hist, key=status_hist.get) if status_hist else None
    p4 = (most_common_status == "Verified") and (n_verified > n_hfdu_total)

    total_errata = len(errata)
    summary = {
        "snapshot_frac_year": round(snapshot, 3),
        "n_errata_total": total_errata,
        "errata_first_record_keys": first_keys,
        "errata_status_histogram": status_hist,
        "errata_type_histogram": type_hist,
        "n_rfc_index_entries": len(entries),
        "hfdu": {
            "n_hfdu_errata": n_hfdu_total,
            "n_distinct_rfcs_with_hfdu": len(hfdu_rfcs),
            "n_hfdu_rfcs_in_index": n_hfdu_idx,
            "n_hfdu_rfcs_revised": n_hfdu_revised,
            "revised_fraction": round(p1_rate, 4) if p1_rate is not None else None,
            "submit_date_parsed": n_date_parsed,
            "submit_date_missing": n_date_missing,
        },
        "hfdu_revision_by_status": by_status,
        "hfdu_resolution_km": {
            "gradable": p3_gradable,
            "n_events_total": len(events),
            "n_resolved": sum(events),
            "median_years_to_resolution_reached": km_med,
            "survival_at_2y": round(survival_at(curve, 2), 4) if curve else None,
            "survival_at_5y": round(survival_at(curve, 5), 4) if curve else None,
            "survival_at_10y": round(survival_at(curve, 10), 4) if curve else None,
            "final_survival": round(final_surv, 4) if curve else None,
            "time_to_resolution_years_median": round(quantile(ttr_sorted, 0.5), 2) if ttr_sorted else None,
        },
        "predictions": {
            "P1_hfdu_revised_gt_40pct": {
                "result": bool(p1),
                "revised_fraction": round(p1_rate, 4) if p1_rate is not None else None,
                "mcquistin_2022_baseline": 0.40,
            },
            "P2_stdtrack_resolved_gt_informational": {
                "result": bool(p2),
                "standards_track_rate": round(st_rate, 4) if st_rate is not None else None,
                "informational_rate": round(info_rate, 4) if info_rate is not None else None,
            },
            "P3_km_median_not_reached": {
                "result": bool(p3),
                "gradable": p3_gradable,
                "km_median_years": km_med,
                "final_survival": round(final_surv, 4) if curve else None,
            },
            "P4_verified_most_common": {
                "result": bool(p4),
                "most_common_status": most_common_status,
                "n_verified": n_verified,
                "n_hfdu": n_hfdu_total,
            },
        },
    }
    return summary


def render(summary):
    s = summary
    L = []
    L.append("RFC errata 'Held for Document Update' graveyard -- MV2 of Munim, Inc. (AI-produced)")
    L.append("Snapshot: %.2f  errata: %d  RFC index entries: %d"
             % (s["snapshot_frac_year"], s["n_errata_total"], s["n_rfc_index_entries"]))
    L.append("Status histogram: " + ", ".join("%s=%d" % (k, v)
             for k, v in sorted(s["errata_status_histogram"].items(), key=lambda kv: -kv[1])))
    h = s["hfdu"]
    L.append("")
    L.append("HFDU errata: %d  distinct RFCs with HFDU: %d  (in index: %d)"
             % (h["n_hfdu_errata"], h["n_distinct_rfcs_with_hfdu"], h["n_hfdu_rfcs_in_index"]))
    L.append("HFDU RFCs ever revised (updated/obsoleted): %d / %d = %s"
             % (h["n_hfdu_rfcs_revised"], h["n_hfdu_rfcs_in_index"],
                ("%.1f%%" % (100 * h["revised_fraction"])) if h["revised_fraction"] is not None else "n/a"))
    L.append("submit_date parsed: %d  missing: %d" % (h["submit_date_parsed"], h["submit_date_missing"]))
    L.append("")
    L.append("HFDU-RFC revision rate by publication status:")
    for grp, r in s["hfdu_revision_by_status"].items():
        if r["n"]:
            L.append("  %-22s n=%-4d revised=%-4d rate=%s"
                     % (grp, r["n"], r["revised"],
                        ("%.3f" % r["rate"]) if r["rate"] is not None else "n/a"))
    km = s["hfdu_resolution_km"]
    L.append("")
    L.append("HFDU resolution survival (time from erratum to subsequent revision):")
    L.append("  gradable=%s events=%d resolved=%d  S(2)=%s S(5)=%s S(10)=%s  median=%s"
             % (km["gradable"], km["n_events_total"], km["n_resolved"],
                km["survival_at_2y"], km["survival_at_5y"], km["survival_at_10y"],
                ("%.2fy" % km["median_years_to_resolution_reached"])
                if km["median_years_to_resolution_reached"] is not None else "not reached"))
    L.append("")
    L.append("PREDICTIONS:")
    p = s["predictions"]
    L.append("  P1 HFDU-revised fraction > 40%%: %s (%.1f%% vs 40%% baseline)"
             % (p["P1_hfdu_revised_gt_40pct"]["result"],
                100 * (p["P1_hfdu_revised_gt_40pct"]["revised_fraction"] or 0)))
    L.append("  P2 Std-Track resolved > Informational: %s (%s vs %s)"
             % (p["P2_stdtrack_resolved_gt_informational"]["result"],
                p["P2_stdtrack_resolved_gt_informational"]["standards_track_rate"],
                p["P2_stdtrack_resolved_gt_informational"]["informational_rate"]))
    L.append("  P3 KM median not reached (most HFDU never folded in): %s"
             % p["P3_km_median_not_reached"]["result"])
    L.append("  P4 Verified most common & > HFDU: %s (%s; verified=%d hfdu=%d)"
             % (p["P4_verified_most_common"]["result"],
                p["P4_verified_most_common"]["most_common_status"],
                p["P4_verified_most_common"]["n_verified"],
                p["P4_verified_most_common"]["n_hfdu"]))
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
