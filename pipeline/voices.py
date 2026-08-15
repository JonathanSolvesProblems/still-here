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
Writes: audio/<animal_id>.mp3 and audio/manifest.json
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
AUDIO = os.path.join(ROOT, "audio")

API = "https://api.elevenlabs.io/v1"
FORCE = False
MODEL = "eleven_multilingual_v2"
DEFAULT_VOICE = "SAz9YHcvj6GT2YYXdXww"  # River: neutral, relaxed, informative.
# Premade voices only; library and cloned voices 402 on the free tier.

# A voice per breed group. The words stay factual either way, so the character
# has to come from who is reading and from the animal you hear first. Brian is
# deliberately warm for the bully-type dogs, because 51 of the 135 drawn dogs
# are pit bulls and a growling read would reinforce the exact prejudice the
# rest of this page spends 99,905 records dismantling.
VOICES = {
    "bully":     "nPczCjzI2devNBz1zQrb",  # Brian, deep and comforting
    "guardian":  "pqHfZKP75CvOlQylNhV4",  # Bill, wise and mature
    "shepherd":  "onwK4e9ZLuTAKqWW03F9",  # Daniel, steady
    "hound":     "CwhRBWXzGAHq8TQ4Fs17",  # Roger, laid back
    "retriever": "cjVigY5qzO86Huf0OWal",  # Eric, smooth and trustworthy
    "herder":    "Xb7hH8MSUJpSbSDYk0k2",  # Alice, bright and clear
    "spitz":     "N2lVS1w4EtoT3dr4eOWO",  # Callum, husky
    "terrier":   "FGY2WhTYpPnrIDTdsKH5",  # Laura, quirky
    "toy":       "cgSgspJ2msm6clMCkdW9",  # Jessica, playful and warm
    "generic":   DEFAULT_VOICE,
}

# The real animal, generated once per breed group and reused. Costs about 20
# characters of quota each, against roughly 250 for a spoken clip.
SOUNDS = {
    "bully":     "one single deep friendly woof from a large dog, close, dry, no music",
    "guardian":  "one very deep low calm woof from a giant breed dog, dry, no music",
    "shepherd":  "one alert confident bark from a german shepherd, dry, no music",
    "hound":     "a short mournful hound dog howl, dry, no music",
    "spitz":     "a short siberian husky howl, expressive, dry, no music",
    "retriever": "one happy eager bark from a labrador, dry, no music",
    "herder":    "one bright quick bark from a border collie, dry, no music",
    "terrier":   "two quick sharp small terrier yaps, dry, no music",
    "toy":       "one tiny excited yip from a very small dog, dry, no music",
    "generic":   "one single friendly dog bark, dry, no music",
}

# Smaller dogs get a livelier read; the big guardians stay calm.
STYLE = {"toy": 0.45, "terrier": 0.40, "herder": 0.30, "spitz": 0.30}

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

    # 5. the comparison, the only claim that comes from the analysis rather
    #    than straight off the record. "dogs like me" means same breed group.
    compare = (f"{pct} percent of dogs like me were already home by now. "
               f"The usual wait is {int(d['cohort_median'])} days.")

    # 6. no plea, no sentiment the record cannot support
    close = pick([
        "I am still here.",
        "I am still in the building.",
        "Nobody has come for me yet.",
    ], d["animal_id"], "close")

    return " ".join([opener, what, arrival, length, compare, close])


def sound_effect(prompt, key, seconds=2.0):
    req = urllib.request.Request(
        f"{API}/sound-generation",
        data=json.dumps({"text": prompt, "duration_seconds": seconds,
                         "prompt_influence": 0.6}).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def stitch(sound_path, speech_path, dest):
    """bark, a breath, then the record. Levelled so the bark never clips."""
    import subprocess
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-i", sound_path, "-i", speech_path,
           "-filter_complex",
           "[0:a]volume=0.55,afade=t=out:st=1.4:d=0.5,apad=pad_dur=0.35[a];"
           "[1:a]volume=1.0[b];[a][b]concat=n=2:v=0:a=1[out]",
           "-map", "[out]", "-codec:a", "libmp3lame", "-q:a", "4", dest]
    return subprocess.run(cmd, capture_output=True).returncode == 0


def tts(text, voice, key, style=0.0):
    req = urllib.request.Request(
        f"{API}/text-to-speech/{voice}",
        data=json.dumps({
            "text": text,
            "model_id": MODEL,
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.75,
                               "style": style, "use_speaker_boost": True},
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
    global FORCE
    FORCE = "--force" in sys.argv

    stats = json.load(open(os.path.join(DATA, "stats.json"), encoding="utf-8"))
    waiting = stats["waiting"]
    dogs = waiting[:count]

    # The longest waits are overwhelmingly pit bulls, so a straight top-N means
    # thirteen of sixteen clips are the same voice and the same woof, and the
    # howls and yips never play anywhere on the board. Top up with the longest
    # waiter from every breed group the top-N missed.
    have = {d.get("sil") for d in dogs}
    for g in VOICES:
        if g in have:
            continue
        first = next((d for d in waiting if d.get("sil") == g), None)
        if first:
            dogs.append(first)
            print(f"  + {first['name'] or '(unnamed)'} ({g}, {first['days_waiting']}d) "
                  f"so the {g} voice is audible somewhere")
    os.makedirs(AUDIO, exist_ok=True)
    sound_dir = os.path.join(AUDIO, "_sounds")
    os.makedirs(sound_dir, exist_ok=True)

    # One animal per breed group, generated once and reused across every dog in
    # that group. Sixteen separate barks would burn the quota for no gain.
    groups = sorted({d.get("sil") or "generic" for d in dogs})
    print(f"breed groups on the board: {', '.join(groups)}")
    for g in groups:
        p = os.path.join(sound_dir, f"{g}.mp3")
        if os.path.exists(p) and os.path.getsize(p) > 2000:
            continue
        try:
            open(p, "wb").write(sound_effect(SOUNDS.get(g, SOUNDS["generic"]), key))
            print(f"  sound/{g}: made")
            time.sleep(0.4)
        except urllib.error.HTTPError as e:
            print(f"  sound/{g}: HTTP {e.code} {e.read().decode()[:120]}")

    scripts, made = {}, []
    total_chars = 0
    for i, d in enumerate(dogs, 1):
        g = d.get("sil") or "generic"
        text = script_for(d)
        scripts[d["animal_id"]] = {"name": d["name"], "days": d["days_waiting"],
                                   "breed_group": g, "voice": VOICES.get(g, DEFAULT_VOICE),
                                   "text": text}
        total_chars += len(text)
        dest = os.path.join(AUDIO, f"{d['animal_id']}.mp3")
        label = d["name"] or f"#{d['animal_id']}"
        if os.path.exists(dest) and os.path.getsize(dest) > 2000 and not FORCE:
            print(f"  [{i}/{len(dogs)}] {label}: cached")
            made.append(d["animal_id"])
            continue
        try:
            speech = tts(text, VOICES.get(g, DEFAULT_VOICE), key, STYLE.get(g, 0.0))
            tmp = dest + ".speech"
            open(tmp, "wb").write(speech)
            snd = os.path.join(sound_dir, f"{g}.mp3")
            if os.path.exists(snd) and stitch(snd, tmp, dest):
                os.remove(tmp)
            else:
                os.replace(tmp, dest)   # no bark available, ship the voice alone
            made.append(d["animal_id"])
            print(f"  [{i}/{len(dogs)}] {label}: {g} voice, {os.path.getsize(dest)//1024} KB")
            time.sleep(0.4)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:220]
            print(f"  [{i}/{len(dogs)}] {label}: HTTP {e.code} {body}")
            if e.code in (401, 402):
                break

    json.dump(made, open(os.path.join(AUDIO, "manifest.json"), "w"), indent=2)
    json.dump(scripts, open(os.path.join(DATA, "scripts.json"), "w", encoding="utf-8"), indent=2)
    print(f"\n{len(made)} clips in audio/, {total_chars} characters of speech")


if __name__ == "__main__":
    main()
