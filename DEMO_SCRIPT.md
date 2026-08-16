# Still Here: narration script

Roughly 85 seconds at a normal speaking pace. Read the **bold** lines only;
everything else is a shot cue. Written to be spoken rather than read, so the
sentences are short and the numbers are said the way you would actually say
them out loud.

Record it in one take if you can. It should sound like you noticed something,
not like you are presenting a project.

---

### 0:00 – 0:12 · Cold open on Pancho

*Board loads. Pancho's frame fills the screen: empty plate, the number 449
burning white. Hold it. Let the number sit there before you say anything.*

> **This is Pancho.**
>
> **He's a terrier at the Austin animal shelter, and he's been waiting four
> hundred and forty-nine days.**
>
> **He doesn't have a photo. Nobody ever took one.**

---

### 0:12 – 0:26 · Pull back to the sheet

*Scroll out to the contact sheet. Real dog faces fill the grid, ordered by wait,
dimming as they go down the page.*

> **He's one of five hundred and ten dogs who have an intake record here and
> nothing that says they left.**
>
> **Every one of these is real, pulled from the city's open data an hour ago.
> The brighter the frame, the longer they've been waiting.**

---

### 0:26 – 0:36 · Play a clip

*Click* **Hear from Pancho** *. Let the bark land, then a few seconds of the
voice. Do not talk over it. Only 23 dogs have a recording; the rest of the
cards say "no recording" instead of showing a dead button.*

*(audio: a bark, then "They called me Pancho. I'm a white Cairn Terrier…")*

> **Each one reads its own record out loud. Nothing in there is invented.**

---

### 0:36 – 0:52 · The myth

*Cut to the coat colour chart. Black bar highlighted.*

> **Now, everyone in rescue will tell you black dogs get left behind.**
>
> **So I checked. Ninety-nine thousand shelter records, going back to 2013.**
>
> **It isn't true. Black dogs leave in nine days. That's faster than white,
> faster than brown.**

---

### 0:52 – 1:08 · The actual answer

*The chart splits into two panels, bully-type on the left, everyone else on the
right, on the same scale. The gap is obvious. Hold this one.*

> **The coats that do wait are blue, and brindle, and fawn. Which are the coats
> pit bulls come in.**
>
> **Split them by breed and the whole thing falls out. A bully-type dog waits
> twenty-eight days. Every other dog waits eight.**
>
> **It was never about the colour.**

---

### 1:08 – 1:20 · What it is for

*Back to the board. Type "husky" into the search box, results narrow. Click a
dog; its real adoption page opens.*

> **Austin's own adoption site won't tell you any of this. It'll show you a dog,
> but never how long he's been sitting there.**
>
> **This puts the two halves back together. And every dog here links straight to
> the page where you could actually take them home.**

---

### 1:20 – 1:28 · Close

*Back to Pancho's empty frame. Hold on the number.*

> **Two hundred and sixteen of the dogs waiting tonight are pit bulls.**
>
> **Pancho isn't. He's a small white terrier, and he's been there four hundred
> and forty-nine days.**

*Hold two seconds. Cut.*

---

## Recording setup

Record the window at about **1400px wide**, not maximised on a 1920 monitor.
The layout caps its content at 1140px, so a full-width 1080p window leaves
roughly 40% of the frame as empty background and the type ends up small in the
final video. A narrower window, or 125% browser zoom, fills the frame properly.

Everything else from the first take was right: fullscreen with chrome hidden,
dark theme, 60fps.

## Shot list

Capture into `broll/`, which is gitignored. Screen recording at 1280x720 or
better, dark theme, browser chrome hidden if you can.

| # | shot | notes |
|---|---|---|
| 1 | Pancho hero, static | let the 449 sit, no cursor movement |
| 2 | Scroll from hero into the sheet | slow, one smooth pass |
| 3 | Sheet mid-scroll, faces visible | the brightness gradient should read |
| 4 | Click **Hear from Pancho** | catch the button changing state |
| 5 | Coat colour chart | whole chart in frame |
| 6 | The two-panel split | the money shot, hold it longest |
| 7 | Breed chart, pit bull at the top | brief |
| 8 | Typing "husky" into search | show the results narrowing |
| 9 | Clicking a dog, adoption page opens | the new tab landing on Adopets |
| 10 | Back to Pancho, hold | closing shot |

## What this script is deliberately not doing

- It opens on a dog, not on an architecture diagram.
- Every number is in days, about an animal, never about my own code.
- It runs on live data pulled the morning of recording, never seeded.
- Snowflake and ElevenLabs are never named. They are how it works, not what it
  is, and the writeup covers them.
- The climax is the two-panel chart and then Pancho's empty frame, not a table
  of green ticks.

## Numbers as of the last refresh

Re-check these against `data/stats.json` before recording. They move daily.

| | |
|---|---|
| dogs waiting | 510 |
| Pancho | 449 days |
| corpus | 99,916 stays, 51,413 adoptions |
| black dogs | 9 days median, n=13,922 |
| bully-type vs everyone else | 28 days vs 8 |
| bully-type waiting now | 216 of 510 |
| over a year | 18 |
| with a photograph | 377 of 510 |
