"""
Give the longest-waiting dogs a voice, using ElevenLabs.

The hard rule here: nothing a dog says is invented. Every clause maps to a
column in Austin's published record (name, breed, coat, intake date, intake
reason, days waited, and the cohort percentile computed from 51,404 completed
adoptions). No personality, no backstory, no "loves long walks". These are real
animals and the record is all anyone actually knows about them, so the record is
all they get to say.

Phrasing variants are chosen by a hash of the animal ID rather than at random,
so re-running produces byte-identical scripts and the demo is reproducible.

Usage:  python pipeline/voices.py [count]
Needs:  ELEVENLABS_API_KEY in .env
Writes: web/audio/<animal_id>.mp3 and web/audio/manifest.json
        data/scripts.json (the text, so the writeup can quote it verbatim)
"""

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
AUDIO = os.path.join(ROOT, "web", "audio")

API = "https://api.elevenlabs.io/v1"
MODEL = "eleven_multilingual_v2"
DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # Rachel, calm and unperformed

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def pick(options, seed, salt):
    h = int(hashlib.sha256((str(seed) + salt).encode()).hexdigest()[:8], 16)
    return options[h % len(options)]


def pretty_date(iso):
    try:
        y, m, d = iso.split("-")
        return f"{MONTHS[int(m) - 1]} {int(d)}, {y}"
    except Exception:
        return iso


def how_they_came(reason):
    r = (reason or "").lower()
    if "stray" in r:
        return "I was picked up as a stray"
    if "owner surrender" in r or "surrender" in r:
        return "I was handed in by the people I lived with"
    if "impound" in r:
        return "an officer brought me in"
    if "abandoned" in r:
        return "I was found abandoned"
    if "return" in r:
        return "I was adopted once and brought back"
    return "I was brought in"


def script_for(d):
    """Compose from the record only. Each sentence is traceable to a field."""
    name = d["name"] or None
    days = d["days_waiting"]
    pct = d["pct_of_cohort_home_by_now"]
    coat = d["color"].lower()
    breed = (d["raw_breed"] or d["breed"]).replace(" - ", " ")

    # 1. who
    if name:
        opener = pick([
            f"My name is {name}.",
            f"They called me {name}.",
            f"I'm {name}.",
        ], d["animal_id"], "open")
    else:
        opener = pick([
            "Nobody gave me a name.",
            "I came in without a name.",
            "There is no name on my card.",
        ], d["animal_id"], "open")

    # 2. what the record says I am
    what = f"I'm a {coat} {breed}."

    # 3. how and when I arrived. how_they_came() returns a mid-sentence clause,
    #    so it has to be lifted to sentence case here.
    clause = how_they_came(d["intake_reason"])
    arrival = f"{clause[0].upper()}{clause[1:]} on {pretty_date(d['intake_date'])}."

    # 4. how long, said plainly
    if days >= 365:
        yrs = int(days / 365)
        span = "more than a year" if yrs < 2 else f"more than {yrs} years"
        length = pick([
            f"That was {days} days ago, {span}.",
            f"I have been here {days} days, {span}.",
        ], d["animal_id"], "len")
    else:
        length = pick([
            f"That was {days} days ago.",
            f"I have been here {days} days.",
        ], d["animal_id"], "len")

    # 5. the comparison, which is the only claim that comes from the analysis
    group = "dogs like me" if d["bully"] else "dogs like me"
    compare = (f"{pct} percent of {group} were already home by now. "
               f"The usual wait is {int(d['cohort_median'])} days.")

    # 6. no plea, no sentiment the record cannot support
    close = pick([
        "I am still here.",
        "I am still in the building.",
        "Nobody has come for me yet.",
    ], d["animal_id"], "close")

    return " ".join([opener, what, arrival, length, compare, close])


def tts(text, voice, key):
    req = urllib.request.Request(
        f"{API}/text-to-speech/{voice}",
        data=json.dumps({
            "text": text,
            "model_id": MODEL,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.75,
                               "style": 0.0, "use_speaker_boost": True},
        }).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json",
                 "Accept": "audio/mpeg"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    load_env()
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        sys.exit("Missing ELEVENLABS_API_KEY in .env")
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "").strip() or DEFAULT_VOICE
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 16

    stats = json.load(open(os.path.join(DATA, "stats.json"), encoding="utf-8"))
    dogs = stats["waiting"][:count]
    os.makedirs(AUDIO, exist_ok=True)

    scripts, made = {}, []
    total_chars = 0
    for i, d in enumerate(dogs, 1):
        text = script_for(d)
        scripts[d["animal_id"]] = {"name": d["name"], "days": d["days_waiting"], "text": text}
        total_chars += len(text)
        dest = os.path.join(AUDIO, f"{d['animal_id']}.mp3")
        label = d["name"] or f"#{d['animal_id']}"
        if os.path.exists(dest) and os.path.getsize(dest) > 2000:
            print(f"  [{i}/{len(dogs)}] {label}: cached")
            made.append(d["animal_id"])
            continue
        try:
            audio = tts(text, voice, key)
            open(dest, "wb").write(audio)
            made.append(d["animal_id"])
            print(f"  [{i}/{len(dogs)}] {label}: {len(audio)//1024} KB — {text[:58]}…")
            time.sleep(0.4)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            print(f"  [{i}/{len(dogs)}] {label}: HTTP {e.code} {body}")
            if e.code in (401, 402):
                break

    json.dump(made, open(os.path.join(AUDIO, "manifest.json"), "w"), indent=2)
    json.dump(scripts, open(os.path.join(DATA, "scripts.json"), "w", encoding="utf-8"), indent=2)
    print(f"\n{len(made)} clips in web/audio, {total_chars} characters of speech")


if __name__ == "__main__":
    main()
