"""
Attach faces to the dogs on the board.

Austin's open data has no photographs in it, but Austin's adoption listings run
on Adopets, and that platform's `code` field is the same animal_id the Socrata
feeds use. So the two join cleanly, and 382 of the 515 dogs currently without an
outcome turn out to have a picture somewhere.

What this does NOT do is copy anything. It records the URL of the photo and the
URL of that dog's real adoption page, and the site embeds the former and links
to the latter, so a visitor who wants the dog ends up on the shelter's own page
rather than on mine. Nothing is rehosted.

The remaining 133 have no listing. Mostly they are recent arrivals still inside
their mandatory stray hold (median wait 20 days against 84 for the listed ones),
which is worth knowing before drawing any conclusion from the gap. A few are not
recent at all: Pancho, the longest wait on the whole board, is one of them.

Usage:  python pipeline/photos.py
Writes: data/photos.json
Needs:  playwright (the API is session-authenticated, so a real browser gets the
        token; nothing here bypasses authentication that a visitor would not).
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

API = "https://service.api.prd.adopets.app/adopter/pet/find?lang=en"
SHELTER_PAGE = "https://adopt.adopets.com/shelter/austin-animal-center"
SHELTER_UUID = "8a047e71-c644-45e3-9a9c-e7b83d18c48f"
PET_URL = "https://adopt.adopets.com/pet/{uuid}"


def fetch_listing():
    from playwright.sync_api import sync_playwright

    token = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()

        def on_req(r):
            if "adopets.app" in r.url and "authorization" in r.headers:
                token["v"] = r.headers["authorization"]

        pg.on("request", on_req)
        pg.goto(SHELTER_PAGE, wait_until="networkidle", timeout=90000)
        pg.wait_for_timeout(6000)
        if not token:
            b.close()
            sys.exit("could not obtain a session token from the adoption site")

        pets = pg.evaluate(
            """async ({auth, api, shelter}) => {
                const out = [];
                for (let off = 0; off < 2000; off += 100) {
                  const r = await fetch(api, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'Authorization': auth},
                    body: JSON.stringify({
                      limit: 100,
                      organization_pet: {specie_uuid: [], breed_uuid: [], size_key: [],
                                         type_key: 'ADOPTION', sex_key: [], age_key: []},
                      user_interaction: false, offset: off,
                      shelter_uuid: shelter, origin_key: 'ORGANIZATION_PAGE'})
                  });
                  const j = await r.json();
                  const rs = (j.data && j.data.result) || [];
                  out.push(...rs.map(x => x.organization_pet));
                  if (rs.length < 100) break;
                }
                return out;
            }""",
            {"auth": token["v"], "api": API, "shelter": SHELTER_UUID},
        )
        b.close()
    return pets


def main():
    print("reading Austin's adoption listings…")
    pets = fetch_listing()
    dogs = [p for p in pets if p.get("specie_name") == "Dog"]
    print(f"  {len(pets)} animals listed, {len(dogs)} dogs")

    photos = {}
    for d in dogs:
        code = str(d.get("code") or "").strip()
        if not code:
            continue
        photos[code] = {
            "picture": d.get("picture") or "",
            "adopt_url": PET_URL.format(uuid=d["uuid"]) if d.get("uuid") else "",
            "listed_name": d.get("name") or "",
            "listed_breed": d.get("breed_primary_name") or "",
            "kennel": d.get("kennel_number") or "",
            "status": d.get("status_key") or "",
            "in_foster": bool(d.get("foster")),
        }

    with_pic = sum(1 for v in photos.values() if v["picture"])
    print(f"  {len(photos)} with an animal id, {with_pic} with a photo")

    # How many of the board can we actually face?
    wpath = os.path.join(DATA, "waiting.csv")
    if os.path.exists(wpath):
        import csv
        waiting = list(csv.DictReader(open(wpath, encoding="utf-8")))
        hit = [w for w in waiting if w["animal_id"] in photos]
        # A name mismatch means the join is wrong, and a wrong face on a real
        # animal is worse than no face. Check rather than assume.
        named = [w for w in hit if w["name"] and photos[w["animal_id"]]["listed_name"]]
        agree = [w for w in named
                 if w["name"].strip().lower() == photos[w["animal_id"]]["listed_name"].strip().lower()]
        print(f"  board: {len(waiting)} dogs, {len(hit)} matched ({100*len(hit)//max(1,len(waiting))}%)")
        if named:
            pct = 100 * len(agree) / len(named)
            print(f"  join check: {len(agree)}/{len(named)} matched names agree ({pct:.0f}%)")
            if pct < 90:
                sys.exit("names disagree too often; the join key is wrong, refusing to write")

    with open(os.path.join(DATA, "photos.json"), "w", encoding="utf-8") as f:
        json.dump(photos, f, indent=2)
    print(f"wrote {os.path.join(DATA, 'photos.json')}")


if __name__ == "__main__":
    main()
