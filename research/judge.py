#!/usr/bin/env python3
"""
Judge for UDN scraper experiments.
Compares scraped output against reference text using line-level matching.
"""
import json
import sys
import os

def load_lines(filepath):
    """Load non-empty lines from a file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def normalize(text):
    """Normalize whitespace for comparison."""
    return "".join(text.split())

def compute_score(result_file, expected_file):
    """
    Score a result against expected output.
    Returns dict with:
      - recall: fraction of expected lines found in result
      - precision: fraction of result lines that match expected
      - matched_lines: list of matched expected lines
      - missing_lines: list of missing expected lines
      - extra_lines: list of extra lines in result (potential junk)
    """
    expected_lines = load_lines(expected_file)
    result_lines = load_lines(result_file)

    expected_normalized = [normalize(l) for l in expected_lines]
    result_normalized = [normalize(l) for l in result_lines]

    # Check which expected lines appear in result (substring match)
    matched = []
    missing = []
    for i, exp_norm in enumerate(expected_normalized):
        found = False
        for res_norm in result_normalized:
            if exp_norm in res_norm or res_norm in exp_norm:
                found = True
                break
        if found:
            matched.append(expected_lines[i])
        else:
            missing.append(expected_lines[i])

    # Check which result lines are extra (not matching any expected)
    extra = []
    for i, res_norm in enumerate(result_normalized):
        found = False
        for exp_norm in expected_normalized:
            if exp_norm in res_norm or res_norm in exp_norm:
                found = True
                break
        if not found:
            extra.append(result_lines[i])

    recall = len(matched) / len(expected_lines) if expected_lines else 0
    precision = (len(result_lines) - len(extra)) / len(result_lines) if result_lines else 0

    return {
        "recall": recall,
        "precision": precision,
        "matched_count": len(matched),
        "expected_count": len(expected_lines),
        "extra_count": len(extra),
        "matched_lines": matched,
        "missing_lines": missing,
        "extra_lines": extra[:20],  # cap at 20 for readability
    }

def compare(results_a_file, results_b_file, expected_file):
    """
    Compare two results. B wins if it has higher recall,
    or same recall but fewer extra lines.
    Returns (winner, report).
    """
    score_a = compute_score(results_a_file, expected_file)
    score_b = compute_score(results_b_file, expected_file)

    report = {
        "A": {"recall": score_a["recall"], "precision": score_a["precision"],
               "matched": score_a["matched_count"], "expected": score_a["expected_count"],
               "extra": score_a["extra_count"]},
        "B": {"recall": score_b["recall"], "precision": score_b["precision"],
               "matched": score_b["matched_count"], "expected": score_b["expected_count"],
               "extra": score_b["extra_count"]},
    }

    if score_b["recall"] > score_a["recall"]:
        winner = "B"
    elif score_b["recall"] < score_a["recall"]:
        winner = "A"
    elif score_b["extra_count"] < score_a["extra_count"]:
        winner = "B"
    elif score_b["extra_count"] > score_a["extra_count"]:
        winner = "A"
    else:
        winner = "tie"

    return winner, report

def evaluate_single(result_file, expected_file):
    """Evaluate a single result against expected."""
    score = compute_score(result_file, expected_file)
    print(f"Recall:    {score['recall']:.1%} ({score['matched_count']}/{score['expected_count']} lines)")
    print(f"Precision: {score['precision']:.1%}")
    print(f"Extra lines: {score['extra_count']}")
    if score["missing_lines"]:
        print(f"\nMissing lines:")
        for l in score["missing_lines"]:
            print(f"  - {l[:80]}")
    if score["extra_lines"]:
        print(f"\nExtra lines (first 20):")
        for l in score["extra_lines"][:10]:
            print(f"  + {l[:80]}")
    return score

if __name__ == "__main__":
    if len(sys.argv) == 3:
        evaluate_single(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 4:
        winner, report = compare(sys.argv[1], sys.argv[2], sys.argv[3])
        print(f"Winner: {winner}")
        print(json.dumps(report, indent=2))
    else:
        print("Usage: judge.py <result> <expected>")
        print("       judge.py <result_a> <result_b> <expected>")
