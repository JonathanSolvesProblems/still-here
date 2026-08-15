# Still Here

**515 dogs have an intake record at the Austin animal shelter and no outcome record. This is the board.**

Built for the [DEV Weekend Challenge: Dog Days Edition](https://dev.to/challenges/weekend-2026-08-13), August 2026.

**Live board: https://stillhere.jonathanandrei.com/**

The longest wait on the board belongs to Pancho, a white Cairn Terrier who was
picked up as a stray on May 23, 2025. As of the last data pull he had been there
**448 days**. 99.7% of dogs in his breed group were adopted in less time than he
has already been waiting.

## The finding

Black dog syndrome, the belief that black dogs are passed over for their color,
does not appear in Austin's records. Across **99,905 completed dog stays** since
2013, black dogs leave in a median of **9 days**, faster than white, brown or
chocolate.

The colors that *do* wait are blue, brindle and fawn, which are the coats
bully-type dogs come in. Split each color by breed group and the picture
resolves:

| coat | bully-type | everyone else |
|---|---|---|
| Brown | 32.5 | 9 |
| Black | 31 | 8 |
| Tan | 30 | 7 |
| White | 29 | 8 |
| Blue | 26 | 11 |
| Brown Brindle | 25 | 11 |

The two columns never overlap. Hold breed constant and coat color moves the
median wait by about 4 days; change the breed and it moves by 20. Overall,
bully-type dogs wait a median of **28 days** against **8** for every other dog.

217 of the 515 dogs waiting right now are bully-type.

## Running it

```bash
python pipeline/fetch.py            # pull both data eras, rebuild the corpus
python pipeline/photos.py           # join Austin's adoption listings for faces
python pipeline/analyze.py          # compute stats.json (feeds the site)
python pipeline/load_snowflake.py   # load into Snowflake, run the views
python pipeline/verify.py           # assert Snowflake and Python agree
python pipeline/voices.py 16        # ElevenLabs clips for the longest waits
python pipeline/factcheck.py        # assert the writeup matches the data
python -m http.server 8931          # then open /index.html
```

`verify.py` and `factcheck.py` are the two that matter before publishing.
The first re-runs every headline question in Python and diffs it against
Snowflake (102 checks). The second re-reads `stats.json` and asserts each
number quoted in `README.md` and `POST.md`, because a figure written on
Saturday and a pipeline re-run on Sunday is exactly how a writeup ends up
lying about its own data.

Copy `.env.example` to `.env` and fill in credentials first. Only
`load_snowflake.py` and `voices.py` need them; the corpus and the site work
without any keys, because Austin's data needs no authentication.

## How it fits together

```
Austin Socrata feeds ──▶ fetch.py ──▶ data/outcomes.csv   (99,905 completed stays)
   (no API key)                   └──▶ data/waiting.csv    (515 dogs, no outcome)
                                        │
                                        ├──▶ analyze.py ──▶ data/stats.json ──▶ index.html
                                        │
                                        └──▶ load_snowflake.py ──▶ Snowflake
                                                    │                 STILL_HERE.SHELTER
                                                    │                 views: HEADLINE, BY_COLOR,
                                                    │                 BY_COLOR_CONTROLLED, SPREAD,
                                                    │                 BY_BREED, WAITING_RANKED
                                                    └──▶ data/snowflake_results.json

data/stats.json ──▶ voices.py ──▶ ElevenLabs ──▶ audio/*.mp3
```

### Snowflake

`pipeline/queries.sql` is the analysis. The corpus loads through an internal
stage rather than row-by-row inserts, and every number on the site comes out of
a view. Two things live there deliberately:

- **`IS_BULLY()`** is a SQL function, so the single judgement call in the whole
  analysis sits in one auditable place instead of being scattered through
  application code.
- **`WAITING_RANKED`** ranks each of the 515 live waits against all 51,404
  completed adoptions in that dog's breed group. That is the number on every
  card, and it is the part that actually wants a warehouse.

`verify.py` re-runs the same questions in Python and diffs the two, so the
warehouse and the local pipeline have to agree before anything ships.

### The photographs

The open data has no images in it. Austin's adoption listings run on Adopets,
and that platform's `code` field is the same animal id the Socrata feeds use, so
the two join directly: **380 of the 515 dogs on the board have a real photo**.
They are embedded from the shelter's platform rather than copied, and every
frame links back to that dog's real adoption page.

`photos.py` refuses to write the join if fewer than 90% of matched, named dogs
agree on the name, because a wrong face on a real animal is worse than no face.
It currently sits at 97%; the disagreements are all the shelter renaming a dog
after intake (`Unknown` becomes `Tinkerbelle`, `Fat Boy` becomes `Big Boy`).

The 135 without a photo are mostly not being overlooked. They are recent
arrivals still inside a mandatory stray hold, and their median wait is 20 days
against 84 for the listed ones. A few are not recent at all: Pancho, the longest
wait on the board, is one of them.

### ElevenLabs

Each of the longest-waiting dogs reads its own record aloud. **Nothing a dog says
is invented.** Every clause maps to a column: name, coat, breed, intake reason,
intake date, elapsed days, cohort percentile, cohort median. Phrasing varies
between dogs but is selected by a hash of the animal ID, not randomly, so
re-running produces byte-identical scripts.

## Data notes

Austin publishes shelter records on Socrata with no API key required. There are
two eras and they do not share a schema:

| | intakes | outcomes | status |
|---|---|---|---|
| archive, 2013-10-01 to 2025-05-05 | `wter-evkm` | `9t4d-g238` | frozen |
| current, 2025-05-05 onward | `pyqf-r2dc` | `gsvs-ypi7` | hourly |

Most tutorials point at the archive, which has not moved since May 2025.

**Length of stay.** The live outcome feed ships `days_in_shelter`. The archive
does not, so each archived outcome is paired with the most recent intake for
that animal that precedes it. Dogs cycle through more than once, and matching on
animal ID alone would charge a repeat stray's whole history to one stay. 652
outcomes could not be paired and were dropped rather than guessed at.

**Who counts as waiting.** An intake row with no outcome row. Not identical to
being in the building: some dogs are in foster, and the outcome feed lags.
Animals recorded dead on intake never get an outcome row either, so 15 of them
were excluded. Without that filter they appear on the board as though they are
waiting for a home.

**Medians, not averages.** Length of stay is heavily right-skewed. The mean
bully-type wait is 66 days against a median of 28. Every headline number is a
median. Controlled color cells need 250 adoptions on each side of the split to
appear; at a lower floor a 35-dog cell was setting the reported spread.

**Limits.** One municipal shelter, and Austin is a no-kill city with a high
live-release rate, so these waits are likely shorter than the national picture.
Nothing here is causal. Breed labels are staff visual assessments, and
[Olson et al. (2015)](https://www.sciencedirect.com/science/article/pii/S109002331500310X)
found staff labelled 52% of a sample pit bull-type where DNA put it at 21%, so
"bully-type" means *what Austin wrote down*, which is also what an adopter reads.

## Credits

Data: [Austin Animal Center](https://data.austintexas.gov) open data.
Black dog syndrome prior work: Hoffman et al., summarized
[here](https://www.sciencedaily.com/releases/2016/02/160203185534.htm).
Breed identification: Olson et al., *The Veterinary Journal* 206 (2015) 197-202.
