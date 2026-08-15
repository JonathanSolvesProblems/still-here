"""
Generate one illustration per breed group for the dogs with no photograph.

Five attempts at hand-authored SVG produced snowmen, mushrooms and a pelican, so
this draws them properly instead.

Two rules make this honest:

  1. These illustrate a BREED TYPE, never an individual. The prompt asks for "a
     Labrador head", not for Sheba. Generating a portrait of a specific real
     animal that nobody has photographed would be inventing evidence about a
     real dog; drawing the breed on its card, with "no photograph on file" still
     printed across it, is a type marker and reads as one.

  2. The art is generated as a solid white shape on transparency and used as a
     CSS mask, not as a picture. The alpha channel carries the drawing and the
     fill colour still comes from the coat the shelter recorded, so a black pit
     bull and a white Great Pyrenees stay visibly different animals.

Usage:  python pipeline/breed_art.py [--force]
Needs:  OPENAI_API_KEY in .env
Writes: assets/breeds/<group>.png
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "breeds")
API = "https://api.openai.com/v1/images/generations"
MODEL = "gpt-image-1"

# One shared style so the ten read as a set rather than ten separate drawings.
STYLE = (
    "Flat vector silhouette illustration. A single solid pure white shape on a "
    "fully transparent background. No background, no shadow, no gradient, no "
    "outline, no border, no text, no colour other than white. Smooth confident "
    "edges. The whole shape is one connected piece. Head and neck only, cropped "
    "at the base of the neck, facing right in strict side profile, centred and "
    "filling most of the square. Elegant, restrained, editorial."
)

BREEDS = {
    "bully": "an American Pit Bull Terrier, broad blocky skull, short wide muzzle, "
             "small folded rose ears set high, thick powerful neck",
    "shepherd": "a German Shepherd, long tapered muzzle, large erect pointed ears, "
                "lean head, sloping neck",
    "retriever": "a Labrador Retriever, softly rounded skull, medium straight muzzle, "
                 "floppy ears hanging flat against the cheek",
    "toy": "a Chihuahua, tiny domed skull, very short fine muzzle, oversized erect "
           "pointed ears, slender neck",
    # "scruffy shaggy" produced wispy edges that vanished into the alpha channel
    # and returned an image with zero opaque pixels. Solid wording only.
    "terrier": "a Cairn Terrier, small compact head, short blunt muzzle, small erect "
               "triangular ears, thick square beard under the chin, solid bold shape",
    "hound": "a Coonhound, long deep muzzle, very long low-set drooping ears hanging "
             "well below the jaw, loose skin",
    "spitz": "a Siberian Husky, wedge-shaped head, erect triangular ears, thick fur "
             "ruff around the neck",
    "guardian": "a Great Pyrenees, massive broad heavy head, deep muzzle, small drop "
                "ears, very thick furry neck",
    "herder": "a Border Collie, alert medium head, tapered muzzle, semi-erect ears "
              "tipped forward, feathered ruff",
    "generic": "a medium-sized mixed breed dog, medium muzzle, one ear semi-erect, "
               "ordinary and unremarkable",
}


def load_env():
    p = os.path.join(ROOT, ".env")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def generate(prompt, key):
    req = urllib.request.Request(
        API,
        data=json.dumps({
            "model": MODEL,
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "background": "transparent",
            "quality": "medium",
            "output_format": "png",
        }).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    return base64.b64decode(d["data"][0]["b64_json"])


def opaque_fraction(png_bytes):
    """A generation can come back visually empty. Check before trusting it."""
    try:
        from PIL import Image
        import io as _io
        im = Image.open(_io.BytesIO(png_bytes)).convert("RGBA")
        alpha = im.getchannel("A")
        hist = alpha.histogram()
        solid = sum(hist[200:])
        return solid / float(im.width * im.height)
    except Exception:
        return 1.0   # cannot check, assume fine rather than block the run


def main():
    load_env()
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        sys.exit("Missing OPENAI_API_KEY in .env")
    force = "--force" in sys.argv
    os.makedirs(OUT, exist_ok=True)

    made = []
    for i, (group, desc) in enumerate(BREEDS.items(), 1):
        dest = os.path.join(OUT, f"{group}.png")
        if os.path.exists(dest) and os.path.getsize(dest) > 5000 and not force:
            print(f"  [{i}/{len(BREEDS)}] {group}: cached")
            made.append(group)
            continue
        prompt = f"{STYLE} The subject is {desc}."
        try:
            png, frac = None, 0.0
            for attempt in range(3):
                png = generate(prompt, key)
                frac = opaque_fraction(png)
                if frac >= 0.04:
                    break
                print(f"      retry: only {frac*100:.1f}% of the frame is opaque")
                time.sleep(1.0)
            if frac < 0.04:
                print(f"  [{i}/{len(BREEDS)}] {group}: came back empty three times, skipped")
                continue
            open(dest, "wb").write(png)
            made.append(group)
            print(f"  [{i}/{len(BREEDS)}] {group}: {len(png)//1024} KB, {frac*100:.0f}% opaque")
            time.sleep(1.0)
        except urllib.error.HTTPError as e:
            print(f"  [{i}/{len(BREEDS)}] {group}: HTTP {e.code} {e.read().decode()[:200]}")
            if e.code in (401, 429):
                break
        except Exception as e:
            print(f"  [{i}/{len(BREEDS)}] {group}: {str(e)[:140]}")

    optimise()
    json.dump(made, open(os.path.join(OUT, "manifest.json"), "w"), indent=2)
    print(f"\n{len(made)}/{len(BREEDS)} breed illustrations in assets/breeds/")


def optimise():
    """The page uses these as CSS masks, so only the alpha channel matters.

    A 1024px full-colour PNG is about 1.2 MB, and ten of them would be 12 MB of
    assets for artwork that renders at 150 pixels. Flattening to white-on-alpha,
    trimming the empty margin and halving the resolution takes each to a few KB
    with no visible difference at display size.
    """
    try:
        from PIL import Image
    except ImportError:
        print("  (Pillow unavailable, leaving images unoptimised)")
        return
    import glob
    before_total = after_total = 0
    for f in sorted(glob.glob(os.path.join(OUT, "*.png"))):
        before = os.path.getsize(f)
        im = Image.open(f).convert("RGBA")
        alpha = im.getchannel("A")
        box = alpha.getbbox()
        if box:
            alpha = alpha.crop(box)
        alpha.thumbnail((512, 512), Image.LANCZOS)
        out = Image.new("RGBA", alpha.size, (255, 255, 255, 0))
        out.putalpha(alpha)
        out.save(f, optimize=True)
        after = os.path.getsize(f)
        before_total += before
        after_total += after
        print(f"    {os.path.basename(f):<15} {before // 1024:>5} KB -> {after // 1024:>3} KB")
    if before_total:
        print(f"  assets: {before_total // 1024} KB -> {after_total // 1024} KB")


if __name__ == "__main__":
    main()
