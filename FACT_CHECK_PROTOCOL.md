# Fact-Check Protocol

**Purpose:** make the *first* pass reliable. A second adversarial pass is a backstop, not the
mechanism — if the first pass needs it to be correct, the first pass is broken.

**Origin:** 2026-08-14. A fact-check of the ex-Stratfor geopolitics panel graded ~47 claims. An
adversarial second pass overturned **5** and refined **14** — an ~11% materially-wrong rate on the
one thing this library exists to do. Every one of the five traces to a *nameable* shortcut, not to
bad luck or a hard call. The shortcuts are listed below, and each has a rule that prevents it.

---

## The five failure modes

Diagnosed from the actual overturns. Learn these by name; they recur.

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
memory. Two didn't qualify — the Polish partitions weren't a war, and the 1944–45 Berlin drive
capped a war Russia didn't start. The claim *was* refutable, but not by the evidence I gave.

**Rule:** **your counterexample is a claim and meets the same bar as theirs.** Verify every
example you use to knock something down. A wrong refutation is worse than no refutation: it looks
like diligence and isn't.

### F5 — Accepted the speaker's hedge instead of checking
**What happened:** a speaker prefaced an attribution with "best guess," so I graded it
`Unverified` and moved on. Checking would have shown the attribution was *settled and public* (the
attacker had claimed the strikes openly), the composition was the opposite of what he described,
and the weapons worked differently than he said. Three errors passed because he sounded modest.

**Rule:** **a hedge changes how harshly you judge the speaker, never whether you check.** Grade
the claim on the evidence, then note the hedge as mitigation. "He flagged it as speculation" goes
in the note column, not in place of the search.

---

## Standing rules

1. **Every graded claim carries a fetched source or the grade `⚪ Unchecked`.** No exceptions for
   claims that seem obvious, that you remember, or that are "just background."
2. **Fetch the primary document for any grade that references a specific source** — the paper, the
   filing, the decree, the article, the speaker's own prior work. Secondary summaries drift, and
   the drift is invisible.
3. **Search in the speaker's own framing and units before testing alternatives.**
4. **Verify your own counterexamples to the same standard as the claim.**
5. **When two sources conflict, cite the one closest in time to the claim, and say the other
   exists.** (The interceptor call was right, but sourced to a later, disputed story instead of
   the analysis published two days before the video.)
6. **Grade "wrong in the speaker's favour" as carefully as "wrong against them."** F2 was only
   caught because the second pass was asked explicitly where the *original was too harsh*. Ask that
   question of yourself in the first pass.
7. **Name what you could not check.** An open gap stated plainly is worth more than a confident
   grade covering it.

---

## Grades

| Grade | Meaning | Requires |
|---|---|---|
| ✅ Confirmed | Checkable and checked out | Fetched source |
| ⚠️ Imprecise / Refined | Directionally right, specifics off | Fetched source + the correct figure |
| ❌ Wrong | Materially false as stated | Fetched source that contradicts it |
| ❓ Unverified | Searched, no adequate source exists | A record of what was searched |
| ⚪ Unchecked | Not investigated | Nothing — but must be labelled, never upgraded |

`❓ Unverified` and `⚪ Unchecked` are different and the difference matters. Unverified means the
evidence isn't out there; Unchecked means you didn't look. Never quietly promote either to a grade.

---

## The second pass

Still run it on any fact-check that will be relied on — but as a **backstop**, not the mechanism.

- Hand the finished grades to independent checkers and instruct them to **refute**, not confirm.
- Require them to report where the original was **too harsh** as well as too generous. This is
  what catches F2, and nothing else does.
- Record corrections **in the report** (a "what the second pass changed" section) rather than
  silently editing them. The corrections are a finding about method.
- **Do not treat agent count as rigor.** In the first run, one agent exhausted its search budget,
  one spawned sub-agents and stopped without collecting them, and one couldn't resolve its
  assigned figure at all. More agents ≠ more reliable. Discipline in the first pass is what makes
  the report trustworthy; the second pass only tells you how well you did.
