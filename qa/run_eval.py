import csv
import json
import os
import sys
import urllib.request
import urllib.error
import time

API_BASE = os.environ.get("MOHAR_API_URL", "http://127.0.0.1:8000").rstrip("/")
SAMPLES_PATH = os.path.join("qa", "test_samples.csv")
OUTPUT_PATH = os.path.join("qa", "test_results_live.csv")

def parse_ids(raw_str):
    if not raw_str or raw_str.strip().upper() == "NONE":
        return set()
    return {item.strip() for item in raw_str.split(";") if item.strip()}

def get_token():
    """Round 3: the API needs a sign-in. Use MOHAR_TOKEN if set, else sign in as the demo Creator."""
    token = os.environ.get("MOHAR_TOKEN", "").strip()
    if token:
        return token
    req = urllib.request.Request(
        f"{API_BASE}/api/auth/demo", data=json.dumps({"role": "Creator"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=70) as resp:
            return json.loads(resp.read().decode("utf-8"))["access_token"]
    except Exception:
        return ""  # older backend without sign-in


def post_with_retry(req, tries=6):
    """Waits and retries when the rate limiter answers 429."""
    for attempt in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=70)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                time.sleep(int(e.headers.get("Retry-After", "10")) + 1)
                continue
            raise


def run_evaluation():
    if not os.path.exists(SAMPLES_PATH):
        print(f"Error: {SAMPLES_PATH} not found.")
        sys.exit(1)

    print(f"Running Mohar QA Evaluation against: {API_BASE}/api/submissions")
    token = get_token()
    rows_out = []
    total_tp = 0
    total_fn = 0
    total_fp = 0
    total_valid_evidence = 0
    total_findings = 0
    clean_samples_total = 0
    clean_samples_with_fp = 0

    with open(SAMPLES_PATH, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sample_id = row["id"].strip()
            expected_set = parse_ids(row["planted_issues"])
            is_clean = row["type"].strip().lower() == "clean"

            payload = json.dumps({
                "title": f"QA Evaluation {sample_id}",
                "text": row["text"],
                "channel": row["channel"],
                "audience": row["audience"],
                "creator": "QA_Tester"
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{API_BASE}/api/submissions",
                data=payload,
                headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
                method="POST"
            )

            try:
                with post_with_retry(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                print(f"[{sample_id}] API Error: {e}")
                rows_out.append({
                    "sample_id": sample_id,
                    "expected_issues": row["planted_issues"],
                    "detected_issues": "API_ERROR",
                    "correct": 0,
                    "missed": len(expected_set),
                    "false_alarms": 0,
                    "evidence_valid_count": 0,
                    "notes": str(e)
                })
                continue

            findings = data.get("findings", [])
            detected_set = {
                str(f.get("rule_or_fact_id", "")).strip()
                for f in findings if f.get("rule_or_fact_id")
            }
            valid_ev_count = sum(1 for f in findings if f.get("evidence_valid") is True)

            tp = len(expected_set & detected_set)
            fn = len(expected_set - detected_set)
            fp = len(detected_set - expected_set)

            total_tp += tp
            total_fn += fn
            total_fp += fp
            total_valid_evidence += valid_ev_count
            total_findings += len(findings)

            if is_clean:
                clean_samples_total += 1
                if fp > 0:
                    clean_samples_with_fp += 1

            detected_str = ";".join(sorted(detected_set)) if detected_set else "NONE"
            print(f"[{sample_id}] Expected: {row['planted_issues']} | Detected: {detected_str} (TP={tp}, FN={fn}, FP={fp})")

            rows_out.append({
                "sample_id": sample_id,
                "expected_issues": row["planted_issues"],
                "detected_issues": detected_str,
                "correct": tp,
                "missed": fn,
                "false_alarms": fp,
                "evidence_valid_count": valid_ev_count,
                "notes": f"Status: {data.get('status', 'unknown')}"
            })

    with open(OUTPUT_PATH, mode="w", newline="", encoding="utf-8") as out_f:
        fieldnames = [
            "sample_id", "expected_issues", "detected_issues",
            "correct", "missed", "false_alarms", "evidence_valid_count", "notes"
        ]
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    precision = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 0.0
    recall = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 0.0
    clean_fpr = (clean_samples_with_fp / clean_samples_total) if clean_samples_total > 0 else 0.0
    ev_rate = (total_valid_evidence / total_findings) if total_findings > 0 else 0.0

    print("\n================ MOHAR QA SUMMARY ================")
    print(f"Results saved to      : {OUTPUT_PATH}")
    print(f"Total True Positives  : {total_tp}")
    print(f"Total Missed (FN)     : {total_fn}")
    print(f"Total False Alarms(FP): {total_fp}")
    print(f"Precision             : {precision:.2%}")
    print(f"Recall                : {recall:.2%}")
    print(f"Clean Sample FPR      : {clean_fpr:.2%} ({clean_samples_with_fp}/{clean_samples_total} clean posts flagged)")
    print(f"Evidence Valid Rate   : {ev_rate:.2%} ({total_valid_evidence}/{total_findings} findings)")
    print("==================================================")

if __name__ == "__main__":
    run_evaluation()
