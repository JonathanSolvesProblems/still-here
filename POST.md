---
title: "Everyone Believes Black Dogs Get Left Behind. I Checked 99,905 Shelter Records. They Don't."
published: false
description: "A live board of the 510 dogs Austin hasn't placed yet, ordered by how long they have waited, and the 99,905-record reason the ones at the top are still there."
tags: weekendchallenge, snowflake, datascience, showdev
cover_image: https://raw.githubusercontent.com/JonathanSolvesProblems/still-here/main/assets/shots/1-hero.jpg
---

*This is my entry for the [DEV Weekend Challenge: Dog Days Edition](https://dev.to/challenges/weekend-2026-08-13).*

My family's dog died recently. He lived with my mom, I met him the day he was born, and I knew him almost his whole life. It was hard on all of us in the way that is difficult to explain to anyone who has not had it happen.

A little while later my mom brought home another dog. He does not replace the first one, and nobody in my family pretends otherwise. But a house with a dog in it is a different house, and hers is whole again.

That exchange happens hundreds of thousands of times a year. What I had not thought about until this weekend is that there is a queue for it, that the queue is very long for some dogs and very short for others, and that the difference is not what almost everyone believes it is.

## What I Built

**[Still Here](https://jonathansolvesproblems.github.io/still-here/)** is a live board of every dog Austin Animal Center has an intake record for and no outcome record. As I write this there are **510** of them.

![The board opens on Pancho, a white Cairn Terrier who has been waiting 448 days and has no photograph anywhere public](https://raw.githubusercontent.com/JonathanSolvesProblems/still-here/main/assets/shots/1-hero.jpg)

The one at the top is called Pancho. He is a white Cairn Terrier, he was picked up as a stray on May 23, 2025, and he has been there **449 days**. 99.7% of the dogs in his breed group were adopted in less time than he has already been waiting.

Then I went looking for the reason the dogs at the top of that board are the ones at the top.

The board moves. Between two runs of the pipeline a day apart, nine dogs came off it: **seven were adopted**, one was reclaimed by an owner who came looking, and one was transferred to a partner rescue. Four new dogs arrived. Baxter had been waiting 71 days and went home on the fifteenth.

### The claim I set out to check

If you have spent any time around animal shelters you have heard of **black dog syndrome**: the belief that black dogs sit unadopted while lighter dogs go home. It is repeated in shelter training material, in local news segments, and in a great many well-meaning adoption posts every October.

It is a genuinely checkable claim, and Austin has published enough records to check it.

I pulled every completed dog stay the city has released since October 2013 and reconstructed how long each one lasted: **99,916 stays**, of which **51,413** ended in adoption. Then I took the median wait for each coat color.

| coat | median days to adoption | n |
|---|---|---|
| Blue | 22 | 2,064 |
| Brown Brindle | 16 | 2,521 |
| Fawn | 16 | 617 |
| Brown | 10 | 7,085 |
| White | 10 | 8,797 |
| Chocolate | 10 | 1,163 |
| **Black** | **9** | **13,922** |
| Tan | 8 | 6,236 |
| Cream | 7 | 770 |

Black dogs are in the fast half. Thirteen thousand nine hundred and twenty-two of them, leaving in a median of nine days, quicker than white, brown or chocolate.

So the myth does not survive its first contact with the data. That much matches the published research: a [2015 study by Christy Hoffman and colleagues](https://www.sciencedaily.com/releases/2016/02/160203185534.htm) found no evidence for black dog syndrome across two shelters either.

But there is something much more interesting sitting in that same table, and it took me a second pass to see it.

### The colors that wait are the colors pit bulls come in

Look at the top of that list again. Blue, brown brindle, fawn. Those are not random slow colors. They are the coats you picture when you picture a pit bull.

So I split every color by whether the dog was a bully-type breed, meaning pit bull, Staffordshire, or American bulldog:

![Two charts on a shared scale: every bully-type coat lands between 25 and 32.5 days, every other coat between 7 and 11](https://raw.githubusercontent.com/JonathanSolvesProblems/still-here/main/assets/shots/3-finding.jpg)

| coat | bully-type | everyone else |
|---|---|---|
| Brown | 32.5 | 9 |
| **Black** | **31** | **8** |
| Tan | 30 | 7 |
| White | 29 | 8 |
| Red | 27 | 8 |
| Chocolate | 26.5 | 8 |
| Blue | 26 | 11 |
| Brown Brindle | 25 | 11 |

The two columns do not overlap anywhere. Every bully-type cell is between 25 and 32.5 days. Every other cell is between 7 and 11. The *fastest* bully-type coat is still 14 days slower than the *slowest* coat outside the group.

**Within a breed group, coat color moves the median wait by at most 7.5 days. Changing the breed group moves it by 20.**

Black only looked fast in the first table because black dogs are the *least* likely to be bully-type: 12% of them, against 81% of the blue ones. The color signal was a breed signal the whole time. A black dog that is not a bully breed waits 8 days. A black pit bull waits 31.

Across the whole corpus: **bully-type dogs wait a median of 28 days, and every other dog waits 8.** That is 3.5 times, on 9,658 bully-type adoptions against 41,755 others.

And it is not a historical curiosity. Of the 510 dogs sitting in that shelter today, **216 are bully-type**. Four of the five longest waits on the board right now are pit bulls.

### The thing the adoption site does not tell you

Austin publishes, in open data, exactly how long every dog has been in its care. Its adoption site shows none of it.

I checked the listings the city actually serves to adopters. A listing carries breed, sex, size, age, kennel number, and a set of behavior tags. There is no intake date on it, no length of stay, and no way to sort or filter by either. There is a manual "Long-term resident" tag a staff member can tick, but nothing that gives you a number.

So a person browsing Austin's adoption page can look straight at Fritz and have no idea he arrived on May 28 of last year.

Both halves of that are public. They are just never printed next to each other. Still Here is the join.

## Demo

**Live board: [jonathansolvesproblems.github.io/still-here](https://jonathansolvesproblems.github.io/still-here/)**

The board is a photographic contact sheet, one frame per dog, ordered by how long each has waited. The day count and the glow are that wait: the longer a dog has been there, the more it has burned into the plate.

![The contact sheet, 510 frames of real dogs with real photographs from Austin's adoption listings](https://raw.githubusercontent.com/JonathanSolvesProblems/still-here/main/assets/shots/2-sheet.jpg)

Every frame links to that dog's real adoption page, so clicking one takes you somewhere you could actually adopt it.

![Canela, 322 days, with her photograph, an adopt button, and a play button to hear her record read aloud](https://raw.githubusercontent.com/JonathanSolvesProblems/still-here/main/assets/shots/4-adopt.jpg)

Things worth trying:

- **Press play on any dog.** Each one reads its own record aloud, and each breed group opens with its own sound: a howl for the hounds, a husky's howl for the spitz breeds, a yip for the toy dogs.
- **Filter to "Over a year"** for the 18 dogs who have been there more than 365 days.
- **Filter to "Unnamed"** for the ones who arrived without a name.
- **Click any day count** to pin that dog to the top, then copy the link. `?dog=7950` is Pancho.

## Code

{% embed https://github.com/JonathanSolvesProblems/still-here %}

Everything is in the open, including the corpus, so every number here is checkable.

## How I Built It

### The data has two eras, and the famous one is frozen

Austin publishes intakes and outcomes on Socrata with no API key required. The dataset IDs that every tutorial points at are **archives frozen at 2025-05-05**. Query `wter-evkm` today and you get a tidy 173,812 rows, not one of them from the last fifteen months. The live feeds are different IDs *and a different schema*, and finding that out was most of an hour.

This project reads both. The live outcome feed ships a `days_in_shelter` column; the archive does not, so each archived outcome is paired with the most recent intake for that animal that *precedes* it. Dogs cycle through the shelter more than once, and matching on animal ID alone would charge a repeat stray's whole history to a single stay. 652 outcomes could not be paired and were dropped rather than guessed at.

### Snowflake does the counting

All 99,916 stays and the 510 current dogs load through an internal stage, and every number quoted above comes out of a view rather than out of application code. The bully-type definition lives in a single SQL function, `IS_BULLY()`, so the one judgement call in the whole analysis is auditable in one place instead of scattered through Python.

The piece that genuinely wants a warehouse is the per-dog percentile: for each of the 510 waiting dogs, rank its current wait against every completed stay in its breed group. That is 510 live values against 51,413 historical ones, and it is one view.

I also kept the Python implementation and made the two argue. `verify.py` re-runs every headline question locally and diffs it against what Snowflake returned, across the medians, the counts, the color table, the controlled split, the spreads, and the per-dog percentile for the top 25 dogs. **102 of 102 checks agree.** If they ever disagree, one of them is wrong and the number does not go in the writeup.

### Finding the faces

The open data has no photographs in it. But Austin's adoption listings run on a platform called Adopets, and its `code` field is the same animal id the open data uses, so the two join directly.

I checked the join rather than trusting it: of the matched dogs that have a name on both sides, **97% agree**, and the handful that disagree are the shelter renaming a dog after intake. `Unknown` becomes `Tinkerbelle`. `Fat Boy` becomes `Big Boy`. The importer refuses to write the mapping at all if agreement drops below 90%, because a wrong face on a real animal is worse than no face.

**377 of the 510 have a real photograph**, embedded from the shelter's own platform rather than copied.

133 have none. I nearly wrote that up as dogs being overlooked, which would have been wrong: most are recent arrivals still inside a mandatory stray hold, and their median wait is 20 days against 84 for the listed ones. But the unlisted share never drops below about a sixth at any length of stay, and **33 dogs have passed 100 days without appearing publicly at all**. Pancho is one of them, which is why the biggest frame on the page is empty.

For those 133 I generated one illustration per breed group and used it as a CSS mask, so the alpha channel carries the drawing while the fill comes from the coat the shelter recorded. A black pit bull and a white Great Pyrenees stay visibly different animals. They illustrate a breed *type*, never an individual: generating a portrait of a specific dog nobody has photographed would be inventing evidence about a real animal, and the "no photograph on file" caption stays on every one.

### Giving them a voice

Each of the longest-waiting dogs reads its own record aloud, and every clip opens with a real generated sound for that breed group: a mournful howl for the hounds, a husky's howl for the spitz breeds, a tiny yip for the toy dogs, a single deep woof for the guardians.

**Nothing any dog says is invented.** Every clause maps to a column:

> They called me Pancho. I'm a white Cairn Terrier. I was picked up as a stray on May 23, 2025. That was 448 days ago, more than a year. 99.7 percent of dogs like me were already home by now. The usual wait is 8 days. Nobody has come for me yet.

The clips are recordings made on 2026-08-15, so a day count spoken aloud can sit a day behind the board, which recomputes on every load.

Name, coat, breed, intake reason, intake date, elapsed days, cohort percentile, cohort median. Eight fields, no biography, no "loves long walks". The phrasing varies between dogs but is selected by a hash of the animal ID rather than randomly, so re-running produces byte-identical scripts.

The pit bulls deliberately got the warmest, deepest voice available, because 51 of the dogs without photographs are pit bulls and a growling read would reinforce the exact prejudice the other 99,916 records spend this whole page dismantling.

A straight top-16 by wait length turned out to be thirteen pit bulls, which meant no howl or yip would ever have played anywhere, so the generator tops up with the longest waiter from every breed group the top-16 missed. Twenty-three clips, all ten groups.

### Things I had to get right, and four I got wrong first

**Medians, not averages.** Length of stay is heavily right-skewed. The mean wait for a bully-type dog is 66 days against a median of 28, because a handful of dogs stay for years. Every headline number here is a median.

**The controlled table was wrong the first time.** It required only 30 adoptions per cell, and reported that coat color moved the wait by 28 days within bully-type dogs, which would have undercut the entire finding. The top and bottom of that table were Yellow Brindle at n=35 and Gray at n=62. Two thin cells were setting the whole spread. At a floor of 250 the same table shows 7.5 days.

**15 of the dogs on my first board had arrived dead.** Animals recorded dead on intake never get an outcome row, so the anti-join that finds waiting dogs finds them too, and there they were on a page captioned *nobody has come for them yet*. Filtering them took the count from 531 to 516.

**And one more after that.** Princess has two intake rows a day apart with no outcome between them, so she was on the board twice. The anti-join emits one row per intake, not per dog. Deduplicating by animal id took it to **515**.

**The charts drew nothing at all for a while.** Both panels rendered a bar of identical length whatever the number said, because the fill was an inline `<span>` and inline elements silently ignore `width`. The comparison the whole page is built on was showing two identical rows.

Because the writeup kept drifting from the pipeline, there is now a `factcheck.py` that re-reads the data and asserts every number quoted in this post. It caught eight stale figures the first time I ran it.

## Prize Categories

**Snowflake** and **ElevenLabs**.

Snowflake holds the corpus and answers every question in the piece, with the one judgement call isolated in a SQL function and a 102-check cross-examination against an independent Python implementation.

ElevenLabs gives 23 dogs a voice and gives each breed group its own animal, generated rather than sampled.

## What this is not

This is one municipal shelter, and Austin is a no-kill city with an unusually high live-release rate, so these waits are likely shorter than the national picture rather than longer.

Nothing here is causal. It shows which dogs wait, not why any individual adopter chose as they did.

Breed labels deserve a warning too. They are assigned by staff from appearance, and [Olson et al. (2015)](https://nationalcanineresearchcouncil.com/research_library/summary-analysis-inconsistent-identification-of-pit-bull-type-dogs-by-shelter-staff/) found that shelter staff called 52% of a sample of dogs pit bull-type while DNA put the figure at 21% (*The Veterinary Journal* 206: 197-202). So "bully-type" here does not mean *a dog with pit bull ancestry*. It means *a dog Austin wrote down as a pit bull*. For a question about who gets adopted that is arguably the better variable anyway, because the label on the kennel card is what an adopter actually reads.

"No outcome record" is also not identical to "in the building". Some of these dogs are in foster care, and the outcome feed lags.

## Why I built it

The interesting thing about the black dog myth is not that it is wrong. It is that it is a *kinder* thing to believe. If dogs are passed over for their color, that is a superstition, and superstitions can be argued away with a good photo and a hashtag.

The real pattern is not a superstition. People are avoiding a breed. 216 of the dogs in that shelter tonight are that breed, and the ones at the top of the board have been waiting since before last summer.

Pancho is not one of them. He is a small white terrier and he has been there 448 days, which is the part I cannot explain and did not try to.

When my mom brought that second dog home, one dog stopped waiting. I did not think about it in those terms at the time and I doubt she did either. This weekend I built the list of everyone still waiting, and it turns out to be 510 names long.

---

**Live board:** https://jonathansolvesproblems.github.io/still-here/
**Code:** https://github.com/JonathanSolvesProblems/still-here
**Data:** Austin Animal Center open data, [live intakes](https://data.austintexas.gov/resource/pyqf-r2dc.json) and [live outcomes](https://data.austintexas.gov/resource/gsvs-ypi7.json). No API key needed, so every number here is checkable.

*If you are anywhere near Austin, the board is real and so are the dogs on it.*
