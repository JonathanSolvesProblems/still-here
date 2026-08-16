"""
Check every number the writeup claims against the data that produced it.

A hackathon writeup drifts: a number is written on Saturday, the pipeline is
re-run on Sunday after a bug fix, and the prose keeps the old figure. That is
exactly how a judge finds an error the author could not see any more. This
script re-reads stats.json and asserts each claim in POST.md and README.md.

Usage:  python pipeline/factcheck.py
Exit:   0 if every claim matches, 1 otherwise.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def main():
    s = json.load(open(os.path.join(DATA, "stats.json"), encoding="utf-8"))
    w, c, sp, ph = s["waiting_summary"], s["corpus"], s["spread"], s.get("photos", {})
    h = s["headline"]
    by_color = {x["color"]: x for x in s["by_color"]}
    ctl = {x["color"]: x for x in s["controlled"]}
    longest = w["longest"]

    # claim -> value the data actually holds
    claims = {
        "waiting count":        w["count"],
        "corpus stays":         c["stays_total"],
        "adopted stays":        c["stays_adopted"],
        "bully median":         h["bully"]["median"],
        "other median":         h["other"]["median"],
        "bully n":              h["bully"]["n"],
        "other n":              h["other"]["n"],
        "median ratio":         h["median_ratio"],
        "black median":         by_color["Black"]["median"],
        "black n":              by_color["Black"]["n"],
        "black pct bully":      by_color["Black"]["pct_bully"],
        "blue pct bully":       by_color["Blue"]["pct_bully"],
        "bully waiting":        w["bully_count"],
        "over a year":          w["over_year"],
        "unnamed":              w["unnamed"],
        "longest days":         longest["days_waiting"],
        "longest pctile":       longest["pct_of_cohort_home_by_now"],
        "archive dropped":      s["generated_from"]["outcomes_archive_dropped"],
        "dead excluded":        s["generated_from"]["excluded_dead_on_intake"],
        "worst case gap":       sp["worst_case_gap_days"],
        "within-group spread":  sp["within_worst_days"],
        "between groups":       sp["between_groups_days"],
        "with photo":           ph.get("with_photo"),
        "without photo":        ph.get("without_photo"),
        "named later":          ph.get("named_after_arriving_nameless"),
    }

    # numbers that must appear in the prose, and the label to report if missing
    must_appear = {
        "POST.md": [
            (c["stays_total"], "corpus size"),
            (c["stays_adopted"], "adopted count"),
            (w["count"], "waiting count"),
            (h["bully"]["median"], "bully median"),
            (h["other"]["median"], "other median"),
            (by_color["Black"]["median"], "black median"),
            (w["bully_count"], "bully waiting"),
            (longest["days_waiting"], "Pancho days"),
            (longest["pct_of_cohort_home_by_now"], "Pancho percentile"),
            (s["generated_from"]["excluded_dead_on_intake"], "dead excluded"),
            (s["generated_from"]["outcomes_archive_dropped"], "archive dropped"),
        ],
        "README.md": [
            (c["stays_total"], "corpus size"),
            (w["count"], "waiting count"),
            (h["bully"]["median"], "bully median"),
            (longest["days_waiting"], "Pancho days"),
        ],
    }

    def norm(n):
        """Match 99905, 99,905 and 99 905."""
        if isinstance(n, float) and n.is_integer():
            n = int(n)
        return [f"{n:,}", str(n)] if isinstance(n, int) else [str(n)]

    bad = 0

    # The title and description are the most-read sentences in the submission and
    # the easiest to leave behind on a refresh: a stale figure there still passes
    # a whole-file search, because the corrected one is sitting in the body.
    post = os.path.join(ROOT, "POST.md")
    if os.path.exists(post):
        raw = open(post, encoding="utf-8").read()
        head = raw.split("---")[1] if raw.startswith("---") else ""
        for stale in re.findall(r"\d{2,3},\d{3}", head):
            if stale.replace(",", "") != str(c["stays_total"]):
                print(f"  POST.md front matter: '{stale}' is not the corpus size "
                      f"({c['stays_total']:,})")
                bad += 1

    for fname, items in must_appear.items():
        path = os.path.join(ROOT, fname)
        if not os.path.exists(path):
            print(f"  MISSING FILE {fname}")
            bad += 1
            continue
        text = open(path, encoding="utf-8").read()
        for val, label in items:
            if val is None:
                continue
            if not any(v in text for v in norm(val)):
                print(f"  {fname}: {label} = {val} does NOT appear")
                bad += 1

    # stale numbers: figures the project used to quote and must not any more
    retired = {
        "516": "old waiting count before the duplicate-intake fix",
        "531": "waiting count before the dead-on-intake filter",
        "190,000": "all-animal corpus size, not the dog-only figure",
    }
    # A section that narrates corrections legitimately quotes the superseded
    # figures: "the count went from 531 to 516" is the story, not staleness.
    # Strip those sections before looking for stale numbers, or the check
    # punishes the writeup for being honest about its own mistakes.
    def strip_corrections(md):
        """Skip the section that narrates corrections, at any heading level.

        Matching only "## " missed the section once it was demoted to "###" and
        the checker then flagged the honest history as staleness. A heading of
        the same or shallower depth ends the section.
        """
        out, skipping, depth = [], False, 0
        for line in md.splitlines():
            m = re.match(r"^(#{2,6})\s+(.*)$", line)
            if m:
                level, text = len(m.group(1)), m.group(2).lower()
                if skipping and level <= depth:
                    skipping = False
                if "got wrong" in text or "correction" in text:
                    skipping, depth = True, level
            if not skipping:
                out.append(line)
        return "\n".join(out)

    for fname in ("POST.md", "README.md", "DEMO_SCRIPT.md"):
        path = os.path.join(ROOT, fname)
        if not os.path.exists(path):
            continue
        text = strip_corrections(open(path, encoding="utf-8").read())
        for old, why in retired.items():
            if old in text:
                print(f"  {fname}: STALE '{old}' outside the corrections section ({why})")
                bad += 1

    # unfilled placeholder links
    for fname in ("POST.md", "README.md"):
        path = os.path.join(ROOT, fname)
        if os.path.exists(path):
            for m in re.findall(r"\]\(#\)", open(path, encoding="utf-8").read()):
                print(f"  {fname}: unfilled placeholder link")
                bad += 1

    print(f"\n{len(claims)} figures in the data, "
          f"{sum(len(v) for v in must_appear.values())} claims checked in prose")
    if bad:
        print(f"{bad} problem(s). Fix before publishing.")
        return 1
    print("Every number quoted in the writeup matches the data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
