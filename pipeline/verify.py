"""
Cross-check Snowflake's answers against the local Python pipeline.

Two independent implementations of the same questions, one in SQL and one in
Python, over the same corpus. If they disagree, one of them is wrong and the
number does not go in the writeup.

This is a build-time check, not a feature. Run it after load_snowflake.py.

Usage:  python pipeline/verify.py
Exit:   0 if everything agrees, 1 otherwise.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

TOL = 0.51  # medians of even-sized integer samples land on .5


def load(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        sys.exit(f"missing {name}. Run fetch.py, analyze.py and load_snowflake.py first.")
    return json.load(open(p, encoding="utf-8"))


def num(v):
    return float(v) if v is not None else None


def main():
    py = load("stats.json")
    sf = load("snowflake_results.json")

    checks = []

    def cmp(label, a, b):
        ok = a is not None and b is not None and abs(float(a) - float(b)) <= TOL
        checks.append((ok, label, a, b))

    # 1. headline
    sf_head = {r["GROUP_NAME"]: r for r in sf["headline"]}
    cmp("bully median", py["headline"]["bully"]["median"],
        num(sf_head["Bully-type"]["MEDIAN_DAYS"]))
    cmp("bully n", py["headline"]["bully"]["n"], num(sf_head["Bully-type"]["N"]))
    cmp("other median", py["headline"]["other"]["median"],
        num(sf_head["Everyone else"]["MEDIAN_DAYS"]))
    cmp("other n", py["headline"]["other"]["n"], num(sf_head["Everyone else"]["N"]))

    # 2. colour table
    sf_col = {r["COLOR"]: r for r in sf["by_color"]}
    for c in py["by_color"]:
        if c["color"] in sf_col:
            cmp(f"colour {c['color']} median", c["median"], num(sf_col[c["color"]]["MEDIAN_DAYS"]))
            cmp(f"colour {c['color']} n", c["n"], num(sf_col[c["color"]]["N"]))

    # 3. controlled split, the finding itself
    sf_ctl = {r["COLOR"]: r for r in sf["by_color_controlled"]}
    for c in py["controlled"]:
        if c["color"] in sf_ctl:
            cmp(f"controlled {c['color']} bully", c["bully"]["median"],
                num(sf_ctl[c["color"]]["BULLY_MEDIAN"]))
            cmp(f"controlled {c['color']} other", c["other"]["median"],
                num(sf_ctl[c["color"]]["OTHER_MEDIAN"]))

    # 4. spread
    if sf.get("spread"):
        s = sf["spread"][0]
        cmp("spread within bully", py["spread"]["within_bully_days"],
            num(s["COLOUR_SPREAD_WITHIN_BULLY"]))
        cmp("spread within other", py["spread"]["within_other_days"],
            num(s["COLOUR_SPREAD_WITHIN_OTHER"]))

    # 5. the per-dog percentile that appears on every card
    sf_wait = {str(r["ANIMAL_ID"]): r for r in sf.get("waiting_ranked", [])}
    for d in py["waiting"][:25]:
        r = sf_wait.get(str(d["animal_id"]))
        if r:
            cmp(f"dog {d['name'] or d['animal_id']} days", d["days_waiting"],
                num(r["DAYS_WAITING"]))
            cmp(f"dog {d['name'] or d['animal_id']} pctile",
                d["pct_of_cohort_home_by_now"], num(r["PCT_OF_COHORT_HOME_BY_NOW"]))

    bad = [c for c in checks if not c[0]]
    for ok, label, a, b in checks:
        if not ok:
            print(f"  MISMATCH  {label}: python={a} snowflake={b}")
    print(f"\n{len(checks) - len(bad)}/{len(checks)} checks agree")
    if bad:
        print("Snowflake and Python disagree. Do not quote these numbers.")
        return 1
    print("Snowflake and the local pipeline agree on every number quoted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
