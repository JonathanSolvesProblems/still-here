---
title: "Everyone Believes Black Dogs Get Left Behind. I Checked 99,905 Shelter Records. They Don't."
published: false
tags: weekendchallenge, snowflake, datascience, showdev
---

*This is my entry for the [DEV Weekend Challenge: Dog Days Edition](https://dev.to/challenges/weekend-2026-08-13).*

My family's dog died recently. He lived with my mom, I met him the day he was born, and I knew him almost his whole life. It was hard on all of us in the way that is difficult to explain to anyone who has not had it happen.

A little while later my mom brought home another dog. He does not replace the first one, and nobody in my family pretends otherwise. But a house with a dog in it is a different house, and hers is whole again.

That exchange happens hundreds of thousands of times a year in the United States. What I had not thought about until this weekend is that there is a queue for it, that the queue is very long for some dogs and very short for others, and that the difference is not what almost everyone believes it is.

This is about the dogs at the back of that queue.

There is a dog called Pancho in the Austin animal shelter. He is a white Cairn Terrier, he was picked up as a stray on May 23, 2025, and as I write this he has been there **448 days**.

I know that because Austin publishes its shelter records as open data, and Pancho has an intake row with no outcome row. Nobody has adopted him, nobody has reclaimed him, and he has not been transferred anywhere. He is just still there.

He is one of **516 dogs** in that position right now.

I built **Still Here**: a board of every one of them, ordered by how long they have been waiting, with the record behind each one and a voice that reads it aloud. Then I went looking for the reason the dogs at the top of that board are the ones at the top.

## The claim I set out to check

If you have spent any time around animal shelters you have heard of **black dog syndrome**: the belief that black dogs sit unadopted while lighter dogs go home. It is repeated in shelter training material, in local news segments, and in a great many well-meaning adoption posts every October.

It is a genuinely checkable claim, and Austin has published enough records to check it.

I pulled every completed dog stay the city has released since October 2013 and reconstructed how long each one lasted: **99,905 stays**, of which **51,404 ended in adoption**. Then I took the median wait for each coat color.

| coat | median days to adoption | n |
|---|---|---|
| Blue | 22 | 2,064 |
| Brown Brindle | 16 | 2,520 |
| Fawn | 16 | 617 |
| Brown | 10 | 7,085 |
| White | 10 | 8,796 |
| Chocolate | 10 | 1,163 |
| **Black** | **9** | **13,919** |
| Tan | 8 | 6,236 |
| Cream | 7 | 770 |

Black dogs are in the fast half. Thirteen thousand nine hundred and nineteen of them, leaving in a median of nine days, quicker than white, brown or chocolate.

So the myth does not survive its first contact with the data. That much matches the published research: a [2015 study by Christy Hoffman and colleagues](https://www.sciencedaily.com/releases/2016/02/160203185534.htm) found no evidence for black dog syndrome across two shelters either.

But there is something much more interesting sitting in that same table, and it took me a second pass to see it.

## The colors that wait are the colors pit bulls come in

Look at the top of that list again. Blue, brown brindle, fawn. Those are not random slow colors. They are the coats you picture when you picture a pit bull.

So I split every color by whether the dog was a bully-type breed, meaning pit bull, Staffordshire, or American bulldog:

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

Across the whole corpus: **bully-type dogs wait a median of 28 days, and every other dog waits 8.** That is 3.5 times, on 9,657 bully-type adoptions against 41,747 others.

And it is not a historical curiosity. Of the 516 dogs sitting in that shelter today, **218 are bully-type**. Four of the five longest waits on the board right now are pit bulls.

## What I actually built

**[Still Here](https://jonathansolvesproblems.github.io/still-here/)** does two things.

The board shows all 516 dogs with no recorded outcome, newest data pulled hourly from Austin's live feed. Each card carries the real record: name if the shelter wrote one down (138 of them arrived without a name), breed, coat, intake date, and a running day count. Against each dog it shows where its current wait falls in the distribution of 51,404 completed adoptions for its own breed group. Pancho's card reads *99.7% of similar dogs were home by now*.

Then each of the longest-waiting dogs reads its own record aloud.

That part needed a rule, because it would have been very easy and very dishonest to have an LLM invent a personality for a real animal. **Nothing any dog says is invented.** Every clause maps to a column:

> They called me Pancho. I'm a white Cairn Terrier. I was picked up as a stray on May 23, 2025. That was 448 days ago, more than a year. 99.7 percent of dogs like me were already home by now. The usual wait is 8 days. Nobody has come for me yet.

Name, coat, breed, intake reason, intake date, elapsed days, cohort percentile, cohort median. Eight fields, no biography, no "loves long walks". The phrasing varies between dogs, but it is selected by a hash of the animal ID rather than randomly, so re-running the generator produces byte-identical scripts.

## The stack

**Snowflake** holds the corpus and does the counting. All 99,905 stays and the 516 current dogs load through an internal stage, and every number quoted above comes out of a view rather than out of application code. The bully-type definition lives in a single SQL function, `IS_BULLY()`, so the one judgement call in the whole analysis is auditable in one place instead of scattered through Python.

The piece that genuinely wants a warehouse is the per-dog percentile: for each of the 516 waiting dogs, rank its current wait against every completed stay in its breed group. That is 516 live values against 51,404 historical ones, and it is one view.

**ElevenLabs** turns each script into speech. Sixteen clips, about 4,000 characters.

Everything else is deliberately plain: Python and the standard library for the pipeline, and a single static HTML page with no framework and no build step.

## Things I had to get right, and one I got wrong first

**The data has two eras.** The Austin datasets that every tutorial and blog post points at are frozen at 2025-05-05. They are archives. If you query `wter-evkm` today you get a tidy 173,812 rows and not one of them is from the last fifteen months. The live feeds are different dataset IDs *and a different schema*, and finding that was most of an hour.

**Medians, not averages.** Length of stay is heavily right-skewed. The mean wait for a bully-type dog is 66 days against a median of 28, because a handful of dogs stay for years. Every headline number here is a median.

**Then the mistake.** My first controlled table required only 30 adoptions per cell, and it reported that coat color moved the wait by 28 days within bully-type dogs, which would have undercut the entire finding. The top and bottom of that table were Yellow Brindle at n=35 and Gray at n=62. Two thin cells were setting the whole spread. At a floor of 250 the same table shows 8 days, and that is the number above.

**And one I nearly published.** 15 of the dogs on my first board had arrived dead. Animals recorded dead on intake never get an outcome row, so the anti-join that finds waiting dogs finds them too, and there they were on a page captioned *nobody has come for them yet*. They are filtered out now. The count went from 531 to 516.

## What this is not

This is one municipal shelter. Austin is a no-kill city with an unusually high live-release rate, so if anything these waits are shorter than the national picture, not longer.

Nothing here is causal. It shows which dogs wait, not why any individual adopter chose as they did.

Breed labels also deserve a warning. They are assigned by staff from appearance, and [Olson et al. (2015)](https://www.sciencedirect.com/science/article/pii/S109002331500310X) found that shelter staff called 52% of a sample of dogs pit bull-type while DNA put the figure at 21%. So "bully-type" in this analysis does not mean *a dog with pit bull ancestry*. It means *a dog Austin wrote down as a pit bull*. For a question about who gets adopted, that is arguably the better variable anyway, because the label on the kennel card is what an adopter actually reads.

"No outcome record" is not identical to "in the building". Some of these dogs are in foster care, and the outcome feed lags.

## Why I built it

The interesting thing about the black dog myth is not that it is wrong. It is that it is a *kinder* thing to believe. If dogs are passed over for their color, that is a superstition, and superstitions can be argued away with a good photo and a hashtag.

The real pattern is not a superstition. People are avoiding a breed. 218 of the dogs in that shelter tonight are that breed, and the ones at the top of the board have been waiting since before last summer.

Pancho is not one of them. He is a small white terrier and he has been there 448 days, which is the part I cannot explain and did not try to.

When my mom brought that second dog home, one dog stopped waiting. I did not think about it in those terms at the time and I doubt she did either. This weekend I built the list of everyone still waiting, and it turns out to be 516 names long.

---

**Live board:** https://jonathansolvesproblems.github.io/still-here/
**Code:** https://github.com/JonathanSolvesProblems/still-here
**Data:** Austin Animal Center open data, [live intakes](https://data.austintexas.gov/resource/pyqf-r2dc.json) and [live outcomes](https://data.austintexas.gov/resource/gsvs-ypi7.json). No API key needed, so every number here is checkable.

*Built for the DEV Weekend Challenge: Dog Days Edition. If you are anywhere near Austin, the board is real and so are the dogs on it.*
