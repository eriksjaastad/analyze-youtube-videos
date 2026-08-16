# Fact-Check Protocol

**Purpose:** make the *first* pass reliable. A second adversarial pass should be a backstop — if the
first pass needs it to be correct, the first pass is broken. **That remains the goal. It is not yet
the measured reality: see F7.**

**Origin, in two parts.**

**2026-07-29 — the geopolitics report.** A fact-check of the ex-Stratfor panel graded ~47 claims. An
adversarial second pass overturned **5** and refined **14** — an ~11% materially-wrong rate on the one
thing this library exists to do. Every one traced to a *nameable* shortcut, not to bad luck or a hard
call. Those shortcuts are **F1–F5**.

**2026-08-14 — the Galpin report.** A fact-check filed *without* the fan-out was later re-run with
nine adversarial agents. **15 of 24 grades changed — a ~50% revision rate**, plus a fabricated author
attribution, two mis-sourced citations, and a `⚪ Unchecked` block concealing the most harmful material
in the source. That produced **F6** (silent omission) and **F7** (unreviewed first passes are
provisional), and forced the correction now embedded in F4 — where this document was found to have
committed the very failure it documents.

**The through-line:** every failure mode here was discovered by checking work that already looked
finished. None was caught by the person doing it, at the time they did it. That is the argument for
the second pass, and the reason this file keeps its errors visible instead of quietly editing them
out.

---

## The seven failure modes

Diagnosed from actual overturns. Learn these by name; they recur.

F1–F5 came from the 2026-07-29 geopolitics report. **F6 and F7 were added 2026-08-14** after a
nine-agent adversarial pass on the Galpin report revised **15 of 24 grades** — and they are the two
that describe how a report can look compliant while being unreliable.

### F1 — Graded against a search snippet instead of the source
**What happened:** claimed a speaker's on-air number was "inflated against his own written work,"
based on a search-engine *summary* of his article. The actual article said what he said on air.
The accusation was fabricated by the summarizer, and I published it.

**Rule:** a search snippet is a pointer, never evidence. **Fetch the document before grading
against it.** This is absolute when the grade asserts a discrepancy *with* a specific source —
"he contradicts X" requires having read X.

### F2 — The query presupposed the answer
**What happened:** the speaker said "top **20%** of Americans consume 50%." I searched for the
*top 10%* figure, found it, and graded him as having garbled a decile. I never searched his actual
framing. The top-20% figure exists, is the same analyst's own cohort, and showed he had
*understated* — he was right and I marked him wrong.

**Rule:** **search the speaker's framing first, in their units.** If they say 20%, search 20%
before you search 10%. Only after their framing comes back empty may you test whether they
garbled a neighbouring statistic. A query built from your hypothesis will find your hypothesis.

### F3 — Graded from training memory without searching
**What happened:** graded a nuclear-casualty claim "roughly right in magnitude" from memory. The
declassified figures are 1.5–2.3× lower than claimed, and the fallout deaths I assumed were
additive are already inside the number.

**Rule:** **no grade from memory. Ever.** Assistant knowledge has a cutoff; much of what this
library checks postdates it, and the pre-cutoff material is exactly where false confidence lives.
If you did not run a search for a claim, its grade is `⚪ Unchecked`, which is a legitimate
publishable grade. "I'm confident" is not a source.

### F4 — Refuted from memory; the refutation was never checked
**What happened:** refuted "Russia never won an offensive war" with four counterexamples from
memory. The 1944–45 Berlin drive didn't qualify — it capped a war Russia didn't start. The claim
*was* refutable, but not by all of the evidence I gave.

**Rule:** **your counterexample is a claim and meets the same bar as theirs.** Verify every
example you use to knock something down. A wrong refutation is worse than no refutation: it looks
like diligence and isn't.

> **⚠️ This section committed F4 while documenting F4. Corrected 2026-08-14.**
>
> The original text listed a *second* disqualified counterexample: "the Polish partitions weren't a
> war." **That is false, and it was asserted from memory without a search — the exact behaviour this
> section exists to prevent.** There were two real wars, both initiated by Russia and both won:
>
> - **[Polish–Russian War of 1792](https://en.wikipedia.org/wiki/Polish%E2%80%93Russian_War_of_1792)**
>   (18 May – 27 Jul 1792). Russia under Catherine the Great invaded; Russian victory; produced the
>   Second Partition.
> - **[Kościuszko Uprising](https://en.wikipedia.org/wiki/Ko%C5%9Bciuszko_Uprising)** (Mar–Dec 1794).
>   Major combat including Maciejowice and the storming of Praga; Russo-Prussian victory; produced the
>   Third Partition and erased the Commonwealth for 123 years.
>
> So the partitions *were* a legitimate counterexample, and the protocol was **wrong to disqualify
> them.** Found by a parallel session re-checking the geopolitics report; verified here against the
> primary accounts before this edit was made, rather than accepted on a peer's say-so.
>
> **Keep this correction visible rather than deleting the error.** A document that teaches "verify
> your counterexamples" using an unverified counterexample is worse than one that doesn't teach it —
> and the nesting is the most convincing evidence the failure mode is real. F4 is not a beginner's
> mistake you outgrow. It caught the person writing the rule against it.

### F5 — Accepted the speaker's hedge instead of checking
**What happened:** a speaker prefaced an attribution with "best guess," so I graded it
`Unverified` and moved on. Checking would have shown the attribution was *settled and public* (the
attacker had claimed the strikes openly), the composition was the opposite of what he described,
and the weapons worked differently than he said. Three errors passed because he sounded modest.

**Rule:** **a hedge changes how harshly you judge the speaker, never whether you check.** Grade
the claim on the evidence, then note the hedge as mitigation. "He flagged it as speculation" goes
in the note column, not in place of the search.

### F6 — Silent omission, which is a grade whether you admit it or not
**What happened (2026-08-14, Galpin report):** the first pass graded 24 claims and *silently skipped*
the rest of the checkable ones. It reported 4 Unchecked (17%) and looked compliant with the Unchecked
floor. The true figure was far higher — the skipped claims simply weren't in the table to be counted.

The omissions were **not random.** When the second pass graded them, **every single one came back
against the speaker**: the magnesium form, the "moderate to strong evidence" table claim, "all diets
just reduce intake," the gardening-equivalence claim, the vitamin D threshold, "nobody needs
supplements." Six for six.

That is the mechanism worth understanding. You skip a claim because checking it looks like work, and
the claims that look like work are disproportionately the vague, sweeping, hard-to-source ones — which
are disproportionately the wrong ones. **Omission is not neutral. It is a systematic thumb on the
scale in the speaker's favour, and it is invisible in the Unchecked count.**

**Rule:** **enumerate every checkable claim first, then grade each one — including as `⚪ Unchecked`.**
A claim you decided not to check must appear in the table. The Unchecked *budget* only means anything
if the denominator is honest.

### F7 — Treating an unreviewed first pass as finished work
**What happened (2026-08-14, Galpin report):** a report was written and filed as a fact-check without
the research fan-out (the Agent tool was unavailable) and without WebSearch (budget exhausted). When
the fan-out was later run — nine agents, all instructed to refute — **15 of 24 original grades changed:
11 against the speaker, 4 in his favour.** A ~50% revision rate. It also surfaced one **fabricated
author attribution**, two mis-sourced citations, and a `⚪ Unchecked` block that turned out to be
concealing the most harmful material in the source (6 of 7 cardiac claims wrong, including one that
inverts lipid-management consensus).

This is in tension with the standing framing below that "a second pass is a backstop, not the
mechanism." That framing is aspirational and remains the goal. **The measured reality is that a first
pass run without the fan-out is not reliable enough to publish.**

**Rule:** **a report produced without the adversarial fan-out is provisional and must say so in its
first ten lines.** Not a disclaimer for cover — a load-bearing status. Provisional reports do not seed
analyst patterns, do not get cited by later reports, and are not represented to Erik as fact-checks.
Say out loud what blocked the fan-out, so it can be unblocked.

---

## Rule 0 — the source goes in the row

**Every claim-table row carries its own source link. A bulk `## Sources` list at the bottom of the
report does not satisfy this and never has.**

This is rule zero because it is the one that makes the other seven enforceable, and because
skipping it is what let F1 and F3 through undetected.

**The failure it prevents:** in a claim table with no source column, a claim you fetched a primary
document for and a claim you invented from memory **render identically**. There is no visual
difference, so there is nothing for you, a reviewer, or Erik to catch. A bulk source list at the
bottom looks like diligence while proving nothing about any individual grade — the 2026-07-29
report carried 40+ links and **49 of 49 claim rows had none bound to them.**

**Required table shape.** The `Source` column is not optional and not last-minute:

| # | Claim | Grade | Source | Note |
|---|---|---|---|---|
| 1 | "80% of their energy is imported" | ❌ Wrong | [SASAC 2025](http://en.sasac.gov.cn/2025/04/01/c_19074.htm) | Self-sufficiency is 84.7%; import dependence ~15% |

- **An empty Source cell means the grade is `⚪ Unchecked`.** Not "I'll add it later" — the
  emptiness *is* the grade. This makes the omission self-reporting.
- **Link the document you actually read**, not a search page and not a summary of it.
- **`❓ Unverified` still needs a Source cell**, holding what you searched — "searched X, Y, Z;
  no primary source found." That is the difference between Unverified and Unchecked, made visible.
- Keep the bottom-of-report `## Sources` section as a reading list. It is a convenience, never
  the citation.

### Where Rule 0 came from

The **research layer** has required primary-source verification since 2026-06-27
(`extract_research_targets()` plus the `## Research Addendum` spec in `README.md`), including a
`Sources consulted` line. That rule was never wrong — it was **unenforced**, and unenforced in a
specific way worth naming: it asked for sources *somewhere in the report* rather than *bound to a
claim*. Measured across the library: 6 of 128 reports carry an Addendum at all, and **all 8
reports with a claim table have 100% unsourced rows.**

Rule 0 does not replace that layer (see [the two layers](#relationship-to-the-research-addendum)
below — they stay separate). It moves the *citation* from the end of the report into the claim
row, where its absence is visible instead of silent.

---

## Standing rules

1. **Every graded claim carries a fetched source or the grade `⚪ Unchecked`** — in its own row,
   per Rule 0. No exceptions for claims that seem obvious, that you remember, or that are "just
   background."
2. **Fetch the primary document for any grade that references a specific source** — the paper, the
   filing, the decree, the article, the speaker's own prior work. Secondary summaries drift, and
   the drift is invisible.
3. **Search in the speaker's own framing and units before testing alternatives.**
4. **Verify your own counterexamples to the same standard as the claim.**
5. **When two sources conflict, cite the one closest in time to the claim, and say the other
   exists.** (The interceptor call was right, but sourced to a later, disputed story instead of
   the analysis published two days before the video.)
6. **Re-check every ❌, in the speaker's favour, before publishing.** Not "be self-critical" —
   that's the judgment that already failed. The mechanical version: take each claim you graded
   `❌ Wrong` and run **one more search using the speaker's own wording**, asking "what would make
   this right?" F2 was a `❌` that a single search in his framing would have flipped. This is
   cheap — wrong grades are rare — and it targets exactly the error you cannot feel yourself
   making. Record the outcome; "re-checked, still wrong" is a fine result.
7. **Name what you could not check.** An open gap stated plainly is worth more than a confident
   grade covering it. Every report ends with an explicit **open gaps** list, and an empty list
   must be a deliberate statement, not an omission.

---

## Grades

| Grade | Meaning | Source cell must contain |
|---|---|---|
| ✅ Confirmed | Checkable and checked out | Link to the fetched source |
| ⚠️ Imprecise / Refined | Directionally right, specifics off | Link to the source carrying the correct figure |
| ❌ Wrong | Materially false as stated | Link to the source that contradicts it |
| ❓ Unverified | Searched, no adequate source exists | What you searched — "searched X, Y; nothing primary" |
| ⚪ Unchecked | Not investigated | Empty. The emptiness is the grade |

`❓ Unverified` and `⚪ Unchecked` are different and the difference matters. Unverified means the
evidence isn't out there; Unchecked means you didn't look. Never quietly promote either to a grade.

**The Unchecked floor.** `⚪ Unchecked` is an honest label, not a way to pass. It is a *budget*:

- If **any** claim in the report is Unchecked, the verdict box must carry the count.
- If **more than 20%** of graded claims are Unchecked, the report is **not publishable as a
  fact-check**. Say so in the first ten lines, or go check them.
- A claim the report leans on — anything cited in the verdict, the pro/con, or the analyst
  pattern — may **never** be Unchecked. If it's load-bearing, check it or don't lean on it.

### Relationship to the Research Addendum

`README.md` documents a separate **Research Addendum** layer with its own per-claim verdicts
(`SUPPORTED` / `REFUTED` / `UNVERIFIED` / `DISPUTED`) produced by research sub-agents. That layer
and this one are **not** the same and must not be merged:

| | Claim table (this protocol) | Research Addendum (`README.md`) |
|---|---|---|
| Who grades | You, in the first pass | Research sub-agents |
| Unit | Every checkable assertion in the video | External claims needing primary-source work |
| Vocabulary | ✅ ⚠️ ❌ ❓ ⚪ | SUPPORTED / REFUTED / UNVERIFIED / DISPUTED |

An Addendum verdict is **evidence feeding a claim-table grade**, never a substitute for one. A
`DISPUTED` addendum verdict does not by itself make the claim-table grade `❓` — you still decide
and still cite. If the two layers disagree, say so in the report rather than silently picking one.

---

## The second pass

**Run it on any fact-check that will be relied on. Without it, the report is provisional (F7).**

The aspiration below still stands — the first pass should be good enough that the second finds
little. Measured against that aspiration, the 2026-08-14 run failed: a 50% revision rate. Treat the
second pass as *required for publication* and the low-revision-rate goal as the standard you are
trying to reach, not a licence to skip it.

- Hand the finished grades to independent checkers and instruct them to **refute**, not confirm.
- Require them to report where the original was **too harsh** as well as too generous. This is
  what catches F2, and nothing else does.
- Record corrections **in the report** (a "what the second pass changed" section) rather than
  silently editing them. The corrections are a finding about method.
- **Hunt for over-harshness explicitly, and expect to find some.** In the 2026-08-14 run, 4 of 15
  revisions went *in the speaker's favour*, including one where he had **underclaimed** against the
  source and was marked down for it. An agent that only finds the speaker wrong has not been
  adversarial; it has been agreeable in the other direction.
- **A wrong hunch that stayed Unchecked is a success, not a near-miss.** The same report flagged a
  host's "15 basis points" figure as implausible — "probably 15%, or misheard" — while correctly
  declining to grade it. The executive had said exactly 15 basis points. **The hunch was wrong and the
  discipline saved it.** This is the single best argument for keeping `⚪ Unchecked` a legitimate
  published grade: it is what a wrong guess looks like when it doesn't reach print.
- **Do not treat agent count as rigor.** In the 2026-08-14 run all eight agents did eventually
  report, but getting there was not clean: one stopped after spawning its own sub-agents without
  collecting them and had to be re-prompted, two reported exhausting their search budget
  mid-task, and two flagged assigned figures they could not resolve (the 1990s Russian nickel
  trough; ASML's supplier country count). Those are the agents' own words in their returned
  reports — **which are session-scoped and not preserved in this repo, so treat this paragraph as
  a first-hand observation, not a citable finding.** The point stands regardless: more agents ≠
  more reliable. Discipline in the first pass is what makes the report trustworthy; the second
  pass only tells you how well you did.

> Flagged in review: the previous version of this paragraph stated the agent failures flatly, with
> no source and no record in the repo — committing F3 inside the document written against F3. It
> is corrected above rather than deleted, because the correction is the more useful artifact.
