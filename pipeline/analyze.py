"""
Turn the corpus into the numbers the site and the writeup both quote.

Everything here is descriptive statistics over completed stays. Two things are
deliberately careful:

  1. Medians, not means. Length of stay is heavily right-skewed (a handful of
     dogs sit for years), so a mean flatters the fast breeds and panics about
     the slow ones. Medians are quoted everywhere; means are kept alongside so
     the writeup can show both.

  2. The color finding is only meaningful controlled for breed. Reporting the
     raw color table alone reproduces the exact error the piece is debunking,
     so analyze() always emits the controlled split next to it.

Output: data/stats.json
"""

import csv
import json
import os
import statistics as st
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# Austin spells bully-type breeds several ways across the two eras.
BULLY_MARKERS = (
    "pit bull",
    "staffordshire",
    "american bulldog",
)

MIN_N = 400          # cohort floor for a headline table
# Controlled cells split an already-small color into two, so the floor has to be
# high enough that a 35-dog cell can't set the reported spread. At 30 the table
# was topped and tailed by Yellow Brindle (n=35) and Gray (n=62) and claimed a
# 28-day within-group spread; at 250 the same table shows 7.
MIN_N_CONTROL = 250


def is_bully(breed):
    b = (breed or "").lower()
    return any(m in b for m in BULLY_MARKERS)


def summarise(days):
    days = sorted(days)
    n = len(days)
    return {
        "n": n,
        "median": round(st.median(days), 1),
        "mean": round(sum(days) / n, 1),
        "p75": days[int(n * 0.75)] if n else 0,
        "p90": days[int(n * 0.90)] if n else 0,
    }


def pct_at_or_below(sorted_days, value):
    """Share of completed stays that finished in <= value days."""
    if not sorted_days:
        return 0.0
    lo, hi = 0, len(sorted_days)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_days[mid] <= value:
            lo = mid + 1
        else:
            hi = mid
    return round(100.0 * lo / len(sorted_days), 1)


def main():
    outcomes = list(csv.DictReader(open(os.path.join(DATA, "outcomes.csv"), encoding="utf-8")))
    waiting = list(csv.DictReader(open(os.path.join(DATA, "waiting.csv"), encoding="utf-8")))
    meta = json.load(open(os.path.join(DATA, "meta.json"), encoding="utf-8"))

    for r in outcomes:
        r["days"] = int(r["days_in_shelter"])
        r["bully"] = is_bully(r["breed"])
    adopted = [r for r in outcomes if r["adopted"] == "1"]

    stats = {
        "generated_from": meta,
        "corpus": {
            "stays_total": len(outcomes),
            "stays_adopted": len(adopted),
            "earliest": min(r["intake_date"] for r in outcomes if r["intake_date"]),
            "latest": max(r["outcome_date"] for r in outcomes if r["outcome_date"]),
            "overall": summarise([r["days"] for r in adopted]),
        },
    }

    # ---- headline: bully-type vs everyone else -------------------------------
    bully_days = [r["days"] for r in adopted if r["bully"]]
    other_days = [r["days"] for r in adopted if not r["bully"]]
    stats["headline"] = {
        "bully": summarise(bully_days),
        "other": summarise(other_days),
        "median_ratio": round(st.median(bully_days) / st.median(other_days), 1),
        "mean_ratio": round(
            (sum(bully_days) / len(bully_days)) / (sum(other_days) / len(other_days)), 1
        ),
    }

    # ---- the myth: raw color table -----------------------------------------
    by_color = defaultdict(list)
    for r in adopted:
        by_color[r["color"]].append(r)
    colors = []
    for c, rows in by_color.items():
        if len(rows) < MIN_N:
            continue
        s = summarise([r["days"] for r in rows])
        s["color"] = c
        s["pct_bully"] = round(100.0 * sum(r["bully"] for r in rows) / len(rows))
        colors.append(s)
    colors.sort(key=lambda d: -d["median"])
    stats["by_color"] = colors

    # ---- the answer: same colors, split by breed type ------------------------
    controlled = []
    for c, rows in by_color.items():
        b = [r["days"] for r in rows if r["bully"]]
        o = [r["days"] for r in rows if not r["bully"]]
        if len(b) < MIN_N_CONTROL or len(o) < MIN_N_CONTROL:
            continue
        controlled.append(
            {
                "color": c,
                "bully": summarise(b),
                "other": summarise(o),
            }
        )
    controlled.sort(key=lambda d: -d["bully"]["median"])
    stats["controlled"] = controlled

    # How flat is color once breed is held constant? Quote this, not a p-value.
    spread_raw = max(c["median"] for c in colors) - min(c["median"] for c in colors)
    spread_bully = max(c["bully"]["median"] for c in controlled) - min(
        c["bully"]["median"] for c in controlled
    )
    spread_other = max(c["other"]["median"] for c in controlled) - min(
        c["other"]["median"] for c in controlled
    )
    # The cleanest statement of the finding is not a single spread number, it is
    # that the two bands never touch: the fastest bully-type coat is still
    # slower than the slowest coat of every other breed.
    bully_band = (min(c["bully"]["median"] for c in controlled),
                  max(c["bully"]["median"] for c in controlled))
    other_band = (min(c["other"]["median"] for c in controlled),
                  max(c["other"]["median"] for c in controlled))
    stats["spread"] = {
        "raw_color_days": spread_raw,
        "within_bully_days": spread_bully,
        "within_other_days": spread_other,
        "within_worst_days": max(spread_bully, spread_other),
        "between_groups_days": st.median(bully_days) - st.median(other_days),
        "bully_band": list(bully_band),
        "other_band": list(other_band),
        "bands_overlap": bully_band[0] <= other_band[1],
        "worst_case_gap_days": bully_band[0] - other_band[1],
    }

    # ---- breeds --------------------------------------------------------------
    by_breed = defaultdict(list)
    for r in adopted:
        by_breed[r["breed"]].append(r["days"])
    breeds = []
    for b, days in by_breed.items():
        if len(days) < MIN_N:
            continue
        s = summarise(days)
        s["breed"] = b
        s["bully"] = is_bully(b)
        breeds.append(s)
    breeds.sort(key=lambda d: -d["median"])
    stats["by_breed"] = breeds

    # ---- the 531: how each waiting dog compares to its own cohort -------------
    cohort = {
        (True, True): sorted(r["days"] for r in adopted if r["bully"] and r["days"] <= 3650),
        (True, False): sorted(r["days"] for r in adopted if r["bully"]),
        (False, True): sorted(r["days"] for r in adopted if not r["bully"]),
        (False, False): sorted(r["days"] for r in adopted if not r["bully"]),
    }
    bully_sorted = sorted(bully_days)
    other_sorted = sorted(other_days)

    # Faces, if photos.py has run. Kept as a separate optional layer because it
    # comes from a different source (Austin's adoption platform) than everything
    # else here, and the site has to work without it.
    photos = {}
    ppath = os.path.join(DATA, "photos.json")
    if os.path.exists(ppath):
        photos = json.load(open(ppath, encoding="utf-8"))

    # Intake staff write "Unknown"/"Unknow" when a stray arrives with no name.
    # That is not a name, it is the absence of one, and it should not be printed
    # as though the dog were called Unknown.
    NON_NAMES = {"", "unknown", "unknow", "*", "-", "n/a", "none"}

    enriched = []
    for d in waiting:
        days = int(d["days_waiting"])
        b = is_bully(d["raw_breed"] or d["breed"])
        ref = bully_sorted if b else other_sorted
        p = photos.get(d["animal_id"], {})
        intake_name = (d["name"] or "").strip()
        if intake_name.strip("*").strip().lower() in NON_NAMES:
            intake_name = ""
        # If the shelter named the dog after intake, that later name is the one
        # a person would actually meet it under.
        given = (p.get("listed_name") or "").strip()
        if given.isdigit():          # some listings just repeat the animal id
            given = ""
        enriched.append(
            {
                "animal_id": d["animal_id"],
                "name": intake_name or given,
                "intake_name": intake_name,
                "given_name": given if given and given.lower() != intake_name.lower() else "",
                "photo": p.get("picture", ""),
                "adopt_url": p.get("adopt_url", ""),
                "kennel": p.get("kennel", ""),
                "breed": d["breed"],
                "raw_breed": d["raw_breed"],
                "color": d["color"],
                "secondary_color": d["secondary_color"],
                "sex": d["sex"],
                "is_puppy": d["is_puppy"] == "1",
                "intake_date": d["intake_date"],
                "days_waiting": days,
                "intake_reason": d["intake_reason"],
                "health": d["health"],
                "bully": b,
                "cohort_median": st.median(ref),
                "pct_of_cohort_home_by_now": pct_at_or_below(ref, days),
            }
        )
    enriched.sort(key=lambda d: -d["days_waiting"])
    stats["waiting"] = enriched

    listed = [d for d in enriched if d["photo"]]
    unlisted = [d for d in enriched if not d["photo"]]
    stats["photos"] = {
        "with_photo": len(listed),
        "without_photo": len(unlisted),
        "pct": round(100.0 * len(listed) / len(enriched)) if enriched else 0,
        # The gap is mostly stray hold, not neglect. Quote both medians so the
        # writeup cannot imply the unlisted dogs are being hidden.
        "median_wait_listed": st.median([d["days_waiting"] for d in listed]) if listed else 0,
        "median_wait_unlisted": st.median([d["days_waiting"] for d in unlisted]) if unlisted else 0,
        "renamed_by_shelter": sum(1 for d in enriched if d["given_name"]),
        "named_after_arriving_nameless": sum(
            1 for d in enriched if not d["intake_name"] and d["given_name"]),
        # Two different populations hide inside "no photo". Most are inside a
        # stray hold and will be listed shortly. A smaller group has been
        # waiting for months and is still not publicly visible anywhere.
        "unlisted_under_30d": sum(1 for d in unlisted if d["days_waiting"] < 30),
        "unlisted_over_100d": sum(1 for d in unlisted if d["days_waiting"] >= 100),
        "pct_unlisted_under_30d": round(
            100.0 * sum(1 for d in enriched if d["days_waiting"] < 30 and not d["photo"])
            / max(1, sum(1 for d in enriched if d["days_waiting"] < 30))),
    }

    stats["waiting_summary"] = {
        "count": len(enriched),
        "bully_count": sum(d["bully"] for d in enriched),
        "bully_pct": round(100.0 * sum(d["bully"] for d in enriched) / len(enriched)),
        "median_days_waiting": st.median([d["days_waiting"] for d in enriched]),
        "over_year": sum(d["days_waiting"] >= 365 for d in enriched),
        "over_100": sum(d["days_waiting"] >= 100 for d in enriched),
        "unnamed": sum(not d["name"] for d in enriched),
        "longest": enriched[0],
    }

    with open(os.path.join(DATA, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    h = stats["headline"]
    w = stats["waiting_summary"]
    print(f"corpus         {stats['corpus']['stays_total']:,} stays, {stats['corpus']['stays_adopted']:,} adopted")
    print(f"               {stats['corpus']['earliest']} -> {stats['corpus']['latest']}")
    print(f"bully-type     median {h['bully']['median']:.0f}d  n={h['bully']['n']:,}")
    print(f"everyone else  median {h['other']['median']:.0f}d  n={h['other']['n']:,}")
    print(f"ratio          {h['median_ratio']}x median")
    print(f"color spread  raw {stats['spread']['raw_color_days']:.0f}d -> within-bully {stats['spread']['within_bully_days']:.0f}d, within-other {stats['spread']['within_other_days']:.0f}d")
    print(f"waiting now    {w['count']} dogs, {w['bully_pct']}% bully-type, {w['over_year']} over a year")
    print(f"longest        {w['longest']['name']} {w['longest']['days_waiting']}d "
          f"({w['longest']['pct_of_cohort_home_by_now']}% of his cohort were home by now)")


if __name__ == "__main__":
    main()
