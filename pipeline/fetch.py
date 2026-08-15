"""
Build the Still Here corpus from Austin Animal Center open data.

Two eras of data, two different schemas:
  archive (2013-10-01 .. 2025-05-05)  intakes wter-evkm   outcomes 9t4d-g238
  live    (2025-05-05 .. today)       intakes pyqf-r2dc   outcomes gsvs-ypi7

The archive has no length-of-stay column, so it is reconstructed by pairing each
outcome with the most recent intake for that animal that precedes it. Animals
cycle through the shelter more than once, so pairing on animal_id alone would
silently attribute a repeat stray's whole history to one stay.

The live feed ships days_in_shelter natively and is used as-is.

Outputs (data/):
  outcomes.csv   one row per completed stay, both eras, normalized
  waiting.csv    dogs with an intake and no recorded outcome
  meta.json      row counts and the exact fetch timestamp, for the writeup
"""

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from bisect import bisect_left
from datetime import datetime, timezone

BASE = "https://data.austintexas.gov/resource"
PAGE = 50000

ARCHIVE_INTAKES = "wter-evkm"
ARCHIVE_OUTCOMES = "9t4d-g238"
LIVE_INTAKES = "pyqf-r2dc"
LIVE_OUTCOMES = "gsvs-ypi7"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# Austin records "Dog" and "Puppy" as separate types in the live feed.
LIVE_DOG_TYPES = {"Dog", "Puppy"}


def fetch(dataset, select=None, where=None):
    """Page through a Socrata dataset. No auth; the portal allows anonymous reads."""
    rows = []
    offset = 0
    while True:
        params = {"$limit": PAGE, "$offset": offset, "$order": ":id"}
        if select:
            params["$select"] = select
        if where:
            params["$where"] = where
        url = f"{BASE}/{dataset}.json?" + urllib.parse.urlencode(params)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    batch = json.load(r)
                break
            except Exception as e:
                if attempt == 3:
                    raise
                print(f"    retry {attempt + 1} after {e}", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
        rows.extend(batch)
        print(f"    {dataset}: {len(rows)}", flush=True)
        if len(batch) < PAGE:
            return rows
        offset += PAGE


def parse_dt(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v)[:19])
    except ValueError:
        return None


def norm_breed(b):
    """Trim Austin's ' Mix' suffix and coat qualifiers so breeds group sanely."""
    if not b:
        return "Unknown"
    b = str(b).strip()
    for suffix in (" Mix",):
        if b.endswith(suffix):
            b = b[: -len(suffix)]
    # 'Chihuahua - Smooth' / 'Chihuahua Shorthair' -> 'Chihuahua'
    b = b.split(" - ")[0].strip()
    return b or "Unknown"


def norm_color(c):
    if not c:
        return "Unknown"
    # Archive packs both coats into one field as 'Black/White'; keep the primary.
    return str(c).split("/")[0].strip() or "Unknown"


def is_adopted_archive(outcome_type):
    return str(outcome_type or "").strip() in {"Adoption", "Rto-Adopt"}


def is_adopted_live(status):
    return str(status or "").strip().startswith("Adopted")


def build_archive(rows_out, seen_ids):
    """Reconstruct length of stay by pairing outcomes with the latest prior intake."""
    print("  archive intakes...")
    intakes = fetch(
        ARCHIVE_INTAKES,
        select="animal_id,datetime,animal_type,intake_type,intake_condition",
        where="animal_type='Dog'",
    )
    print("  archive outcomes...")
    outcomes = fetch(
        ARCHIVE_OUTCOMES,
        select="animal_id,datetime,outcome_type,animal_type,breed,color,date_of_birth",
        where="animal_type='Dog'",
    )

    # animal_id -> sorted list of intake datetimes, plus the record at each
    by_animal = {}
    for r in intakes:
        dt = parse_dt(r.get("datetime"))
        aid = r.get("animal_id")
        if dt and aid:
            by_animal.setdefault(aid, []).append((dt, r))
    for aid in by_animal:
        by_animal[aid].sort(key=lambda t: t[0])

    paired = unpaired = 0
    for r in outcomes:
        aid = r.get("animal_id")
        odt = parse_dt(r.get("datetime"))
        if not aid or not odt or aid not in by_animal:
            unpaired += 1
            continue
        stays = by_animal[aid]
        times = [t for t, _ in stays]
        # rightmost intake strictly before this outcome
        idx = bisect_left(times, odt) - 1
        if idx < 0:
            unpaired += 1
            continue
        idt, irec = stays[idx]
        days = (odt - idt).days
        if days < 0 or days > 3650:
            unpaired += 1
            continue
        paired += 1
        rows_out.append(
            {
                "era": "archive",
                "animal_id": aid,
                "name": "",
                "breed": norm_breed(r.get("breed")),
                "color": norm_color(r.get("color")),
                "intake_date": idt.date().isoformat(),
                "outcome_date": odt.date().isoformat(),
                "days_in_shelter": days,
                "outcome_status": str(r.get("outcome_type") or "Unknown").strip(),
                "adopted": int(is_adopted_archive(r.get("outcome_type"))),
                "intake_type": str(irec.get("intake_type") or "").strip(),
                "intake_condition": str(irec.get("intake_condition") or "").strip(),
            }
        )
        seen_ids.add(("archive", aid))
    print(f"  archive: paired {paired}, dropped {unpaired}")
    return paired, unpaired


def build_live(rows_out):
    print("  live outcomes...")
    outcomes = fetch(LIVE_OUTCOMES)
    kept = 0
    for r in outcomes:
        if r.get("type") not in LIVE_DOG_TYPES:
            continue
        days = r.get("days_in_shelter")
        try:
            days = int(float(days))
        except (TypeError, ValueError):
            continue
        if days < 0 or days > 3650:
            continue
        odt = parse_dt(r.get("outcome_date"))
        idt = parse_dt(r.get("intake_date"))
        kept += 1
        rows_out.append(
            {
                "era": "live",
                "animal_id": r.get("animal_id") or "",
                "name": (r.get("name") or "").strip(),
                "breed": norm_breed(r.get("primary_breed")),
                "color": norm_color(r.get("primary_color")),
                "intake_date": idt.date().isoformat() if idt else "",
                "outcome_date": odt.date().isoformat() if odt else "",
                "days_in_shelter": days,
                "outcome_status": str(r.get("outcome_status") or "Unknown").strip(),
                "adopted": int(is_adopted_live(r.get("outcome_status"))),
                "intake_type": "",
                "intake_condition": "",
            }
        )
    print(f"  live: kept {kept} dog outcomes")
    return kept


def build_waiting():
    """Dogs with an intake and no recorded outcome: the ones still waiting."""
    print("  live intakes...")
    intakes = fetch(LIVE_INTAKES)
    print("  live outcome ids...")
    outs = fetch(LIVE_OUTCOMES, select="animal_id")
    done = {o.get("animal_id") for o in outs if o.get("animal_id")}

    today = datetime.now()
    waiting = []
    excluded_dead = 0
    for r in intakes:
        if r.get("type") not in LIVE_DOG_TYPES:
            continue
        aid = r.get("animal_id")
        if not aid or aid in done:
            continue
        # An animal recorded dead on arrival never gets an outcome row, so the
        # anti-join leaves it looking like it is still waiting for a home. It is
        # not. Fifteen of these were on the board before this filter existed.
        if str(r.get("intake_health_condition") or "").strip().lower() == "dead":
            excluded_dead += 1
            continue
        idt = parse_dt(r.get("source_date"))
        if not idt:
            continue
        waiting.append(
            {
                "animal_id": aid,
                "name": (r.get("name_at_intake") or "").strip(),
                "breed": norm_breed(r.get("primary_breed")),
                "raw_breed": (r.get("primary_breed") or "").strip(),
                "color": norm_color(r.get("primary_color")),
                "secondary_color": (r.get("secondary_color") or "").strip(),
                "sex": (r.get("sex") or "").strip(),
                "is_puppy": int(r.get("type") == "Puppy"),
                "intake_date": idt.date().isoformat(),
                "days_waiting": (today - idt).days,
                "intake_reason": (r.get("source_name") or "").strip(),
                "health": (r.get("intake_health_condition") or "").strip(),
                "date_of_birth": (r.get("date_of_birth") or "")[:10],
            }
        )
    # One row per intake, so a dog booked in twice without an outcome between
    # (Princess, 22830, arrived 2026-04-06 and again on the 07th) appears twice
    # and inflates the count. Keep the most recent intake per animal.
    waiting.sort(key=lambda d: d["intake_date"], reverse=True)
    seen, deduped = set(), []
    for d in waiting:
        if d["animal_id"] in seen:
            continue
        seen.add(d["animal_id"])
        deduped.append(d)
    dupes = len(waiting) - len(deduped)
    waiting = deduped

    waiting.sort(key=lambda d: d["days_waiting"], reverse=True)
    print(f"  waiting: {len(waiting)} dogs with no recorded outcome "
          f"({excluded_dead} dead-on-intake excluded, {dupes} duplicate intake(s) merged)")
    return waiting, excluded_dead


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {path} ({len(rows)} rows)")


def main():
    os.makedirs(DATA, exist_ok=True)
    fetched_at = datetime.now(timezone.utc)

    outcomes = []
    seen = set()
    print("Building outcome corpus")
    a_paired, a_dropped = build_archive(outcomes, seen)
    live_kept = build_live(outcomes)

    print("Building waiting list")
    waiting, excluded_dead = build_waiting()

    write_csv(
        os.path.join(DATA, "outcomes.csv"),
        outcomes,
        [
            "era", "animal_id", "name", "breed", "color", "intake_date",
            "outcome_date", "days_in_shelter", "outcome_status", "adopted",
            "intake_type", "intake_condition",
        ],
    )
    write_csv(
        os.path.join(DATA, "waiting.csv"),
        waiting,
        [
            "animal_id", "name", "breed", "raw_breed", "color", "secondary_color",
            "sex", "is_puppy", "intake_date", "days_waiting", "intake_reason",
            "health", "date_of_birth",
        ],
    )

    meta = {
        "fetched_at_utc": fetched_at.isoformat(),
        "outcomes_total": len(outcomes),
        "outcomes_archive": a_paired,
        "outcomes_archive_dropped": a_dropped,
        "outcomes_live": live_kept,
        "waiting_now": len(waiting),
        "excluded_dead_on_intake": excluded_dead,
        "longest_wait_days": waiting[0]["days_waiting"] if waiting else 0,
        "longest_wait_name": waiting[0]["name"] if waiting else "",
        "sources": {
            "archive_intakes": f"{BASE}/{ARCHIVE_INTAKES}.json",
            "archive_outcomes": f"{BASE}/{ARCHIVE_OUTCOMES}.json",
            "live_intakes": f"{BASE}/{LIVE_INTAKES}.json",
            "live_outcomes": f"{BASE}/{LIVE_OUTCOMES}.json",
        },
    }
    with open(os.path.join(DATA, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
