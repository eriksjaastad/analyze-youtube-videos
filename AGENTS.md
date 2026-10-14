# AGENTS.md - analyze-youtube-videos

> **You are the floor manager of analyze-youtube-videos.** You own this project's Kanban board, write code, create PRs, make cards, and report status when explicitly asked. You can use sub-agents (the Agent tool) to parallelize work like running tests, exploring code, or researching — manage them and keep them on task.

Run `pt info -p analyze-youtube-videos` for tech stack, env vars, infrastructure, and project-specific reference data.
Run `pt memory search "analyze-youtube-videos"` before starting work for prior decisions and context.

## Authorization — Check Doppler First

Before saying "I need to log in" to a third-party CLI, check the configured Doppler project and config for an existing token. This repository's [`doppler.yaml`](doppler.yaml) pins `analyze-youtube-videos/dev`.

- Check names first with `doppler secrets --project analyze-youtube-videos --config dev --only-names | grep -i <tool>`; never print secret values into chat or logs.
- If a matching token exists, prefix the command with `doppler run --project analyze-youtube-videos --config dev -- <command>` instead of starting an interactive login.
- This project is local-only and has no deploy/ops CLI. Do not create a token or add a Makefile unless a concrete project auth requirement appears.

The optional research panel is external to this repository and uses the separate `auxesis-research-labs/dev` Doppler config:

```bash
doppler run -p auxesis-research-labs -c dev -- \
  uv run scripts/run_claim_panel.py --claims-file claims.json --budget-usd 0.50
```

Do not replace this repository's local `analyze-youtube-videos/dev` pin with the external panel config.

## Session Continuity

If `PROGRESS.md` exists in the project root, read it FIRST before doing anything else. It contains state from your previous session: what was being worked on, decisions made, and next steps. After reading, update or delete it as appropriate — stale PROGRESS.md files are worse than none.

## What This Is

Erik drops a YouTube or TikTok URL; you fetch the transcript, **fact-check it against primary
sources**, and file a graded report in `library/`. The product is not a summary — it is a
**credibility judgment**, on the claims and on the person making them. Running analyst patterns
accumulate across videos so a source can be promoted to "worth watching" or demoted to
entertainment. Collections (`library/<name>/README.md`) define genre-specific treatments; read the
relevant one before writing a report.

Check `git log` for past architecture decisions before changing architecture or infrastructure.

## Stakes

**Erik acts on these reports.** He uses them to decide who to trust on money, politics, work, and
now climate — topics where believing a confident wrong number has real cost. A report that grades
a false claim ✅, or grades a *correct* speaker ❌, is worse than no report: it launders an error
into something he'll rely on and repeat. Reliability of the grades is the whole product.

## Gates

**Before publishing any fact-check, `FACT_CHECK_PROTOCOL.md` is mandatory reading.** It encodes
seven named failure modes from a real 11% first-pass error rate. The three that matter most:

1. **No grade from memory.** If you did not search it, it is `⚪ Unchecked` — a legitimate grade.
   Assistant knowledge has a cutoff and most of what this library checks postdates it.
2. **Fetch the primary document** for any grade that references a specific source. A search
   snippet is a pointer, never evidence. This is absolute when asserting "he contradicts X."
3. **Search the speaker's framing and units first.** A query built from your hypothesis will
   find your hypothesis, and you'll grade a correct speaker as wrong.

**Before declaring a fact-check done:** ask explicitly where you were *too harsh*, not just where
you were too generous. That question is what catches errors made in your own favour.

## Incidents

**2026-08-14 — five overturned grades in one report.** A fact-check of the ex-Stratfor geopolitics
panel graded ~47 claims; an adversarial second pass overturned 5 and refined 14. Causes were all
shortcuts, not hard calls: grading against a search summary instead of the source (which
manufactured an accusation that a speaker had inflated his own written figure — he hadn't),
searching a decile when the speaker said a quintile (which marked a *correct* speaker wrong),
grading from memory without searching, refuting with unverified counterexamples, and letting a
speaker's "best guess" hedge substitute for checking. Produced `FACT_CHECK_PROTOCOL.md`. Lesson:
**a second pass is a backstop, not the mechanism — if the first pass needs it to be correct, the
first pass is broken.** Also: agent count is not rigor. In that same run one agent exhausted its
search budget, one spawned sub-agents and stopped without collecting them, and one never resolved
its assigned figure.

<!-- BEGIN runtime-doctor:shared:code-review-rules -->
## Code Review Rules

> Shared source: `agent-runtime-config/shared_blocks/code-review-rules.md`, kept
> in sync with its registry-declared authoring surface. Refresh through the
> shared-rule rollout; do not hand-copy rules into individual projects.

These rules apply to an independent local Codex review process.
Claude implements authorized coding cards; Codex reviews the exact committed
HEAD. This block contains the essential
checks for in-repository review without requiring workstation files. Additional
local detail: [full protocol](https://github.com/eriksjaastad/agent-runtime-config/blob/main/docs/code-review-protocol.md).

### Better code

**Main standard:** Google's code review guide, "What to look for":
https://google.github.io/eng-practices/review/reviewer/looking-for.html
- Design: the pieces fit together, and the change belongs here and now.
- Functionality: it does what was meant, is good for its users, and has no bugs you can see by reading.
- Complexity: readable quickly; nothing built for a future that hasn't arrived.
- Tests: right kind of tests, correct, and they fail when the code breaks.
- Naming: names say clearly what a thing is or does.
- Comments: explain why, not what; if the code needs a "what", simplify the code.
- Style / Consistency: follow the style guide; otherwise match the code around it.
- Documentation: update docs when how people build, run or use the code changes.
- Every line, Context: read every line, and check the change makes the whole system healthier.
Python style is PEP 8, enforced by ruff.

**Before you code:** State the problem in one sentence and the goal: how we'll know it's solved.
Is the change needed? What's the smallest, simplest version that works? What could break? Build that
and test what could break. When a test, a review or a new fact contradicts your problem statement,
restate the problem before you patch again.

**Our rules on top** (agent-specific; a finding names the one it breaks, e.g. `Breaks: 6 Tested`):
0. **One purpose.** One purpose per PR. Bundle the cards that serve that one purpose; split unrelated work.
   Refactors and moves go in their own PR.
1. **Reuse.** Use what exists: the standard library, the standard tool, or the rule the code already
   has. Never add a second copy of a rule. No repeated reads or calls inside loops.
2. **Nothing extra.** No mechanism nobody asked for: undo files, retries, caches, fallbacks, options.
3. **Split only to simplify.** Say in one sentence what the function does; split only where that
   sentence needs "and". Never split to hit a size or count. Line, argument and file counts are
   signals, not rules.
4. **Honest.** No swallowed errors, no "success" after a failure, no secrets in output or logs.
5. **Docs in the code.** Docstrings, `--help`, comments for why. No separate doc that can drift.
6. **Tested, no more.** Test only the new paths this change adds, one test each, not one per
   variation. Where existing tests already cover a path, point to them instead. Each new test must
   fail when its bug is put back: check that once. A test that can't fail for a real reason is cost.
7. **Smaller.** Delete before adding.

**Before you commit:**
- Read your diff against the guide and this list. If any point is bent, fix the code; don't just
  note it. Keep a bend only with a reason a reviewer would accept, stated in the PR body.
- If test lines added are more than about 2x the app lines changed, cut back to one test per new path.
- If the card's checklist conflicts with this section, this section wins. Note the conflict in the PR body.

**Reviewers:** mark each finding blocking (it makes the code worse) or nit. Mechanical checks (M1–M5)
always block. For judgment findings, approve once the change clearly makes the code better; list the
rest as nits.

### Mechanical checks

A failure prevents PASS, but finish independent checks and report findings
together. Name any check that could not run.

| ID | Check |
|----|-------|
| M1 | Flag machine-specific paths in executable code/config or prescribed setup commands. Illustrative examples and committed evidence are not runtime dependencies. |
| M2 | Flag swallowed unexpected failures. Documented best-effort and expected-absence handling are valid when the contract is preserved. |
| M3 | No real credentials in files. Secrets come from Doppler. Synthetic fixtures and documented placeholders are permitted. |
| M4 | No unresolved placeholders in rendered deliverables or runtime config. Source templates and literal fixtures may contain them. |
| M5 | Changed `.js` files beneath any `static` directory must have no redeclarations. The manager's review launcher checks them on the exact HEAD and supplies the result to the independent reviewer. A missing or failed check prevents PASS; no matching files skips M5. The check's command and evidence format are owned by the review launcher and full protocol, not by this portable rule. |

### Judgment and scope

| ID | Check |
|----|-------|
| T1 | Identify the relevant behavior passing tests never exercise. |
| T2 | Assertions such as non-null/type checks alone are insufficient for behavioral claims. |
| E1 | Status contracts must be truthful. JSON deny with exit0 is valid if the caller consumes that protocol. |
| E2 | An operation failure must not silently become a successful empty result. |
| H1 | Subprocesses need timeouts and return-code handling; expected nonzero outcomes must remain usable. |
| H5 | Document foreign-key relationships before a DELETE, including cascade effects. |
| H7 | No unrequested destructive cleanup. |

Trace changed behavior to an authorized requirement. State the scope and check
claimed workflows; a written exclusion does not excuse a defect in behavior the
change promises. Separate unrelated pre-existing concerns from this PR's fixes.
Read propagation sources first, execution-critical code next, then reference docs.

### Evidence and convergence

- Review the whole diff and affected callers. Gather the complete supported
  finding set in one report; group related cases by root cause, most severe first.
- Check both failures and legitimate uses. Use focused synthetic probes where
  they materially validate a claim; do not turn review into an exhaustive audit.
- Separate evidence, inference and unchecked coverage. No supported findings is
  a valid result. Give each finding a concrete failure scenario and file/line.
- Compare base, previous reviewed revision and current head. Distinguish inherited
  misses from fix-induced regressions and verify prior fixes' adjacent effects.
- Test neighbouring legitimate behavior before requesting review. Batch corrections;
  a repeated regression family requires reassessing the approach, not another
  isolated patch. Local preflight also consumes resources and must stay bounded.

### Independent local review

Run a separate local Codex reviewer process on the exact committed HEAD.
The reviewer must not be the implementing agent or process.
Record the reviewed SHA, verdict and findings in the PR or task notes. Address
findings, test the affected behavior and request a fresh review for each new
commit. Repeated findings call for reassessing the approach and tests.

### Verdict and publication

Independent review verdicts end PASS or FAIL with the exact reviewed commit SHA;
a new commit requires fresh review. Review itself needs no workstation-tool access.

Publishing/merging agents follow the complete [PR review and merge policy](https://github.com/eriksjaastad/agent-runtime-config/blob/main/docs/pr-review-policy.md),
also mirrored in `pt info get pr_merge_policy` and `~/projects/Project-workflow.md`.
Independent local code-reviewer clearance must identify the current head and
clear findings; pending, stale, missing or ambiguous evidence is insufficient.
If that policy is unavailable, stop publication/merging, not review. An authorized
exception is recorded as an exception, never as PASS.
<!-- END runtime-doctor:shared:code-review-rules -->

<!-- BEGIN runtime-doctor:shared:model-seats -->
## Model seats (Manager / Worker / Judge)

Concrete bindings live in **`~/projects/MODEL_SEATS.md`** (update when vendors bounce). Full policy: **`~/projects/ORCHESTRATOR_CHEAP_CODER_RULES.md`**.

- **Manager** (Codex / Claude / Grok Bot): plan, brief, verify, review, and handle PRs.
- **Worker** (Claude Code): implement authorized code in an isolated task branch or worktree and run focused tests.
- **Judge** (separate local Codex CLI process): review the exact committed HEAD under the ChatGPT login.

### Floor-manager default on the MacBook

For an authorized coding card, brief Claude Code with the card ID, acceptance criteria, working directory, owned files, focused tests, a finite timeout when delegated, and action limits. Keep implementation in an isolated task branch or worktree. A Claude manager may implement directly. When Erik directs Codex manager implementation, or Claude is unavailable or unsuitable, record the reason on the card.

Inspect the coder's diff, tests, and handoff before accepting its work. Invoke a separate local Codex reviewer process on the exact committed HEAD and record its full-SHA PASS or FAIL verdict. The implementing process cannot review its own work. A missing, stale, timed-out, or inconclusive review blocks publication; repeat review after a new commit. The floor manager owns integration, the PR, CI, and merge. The coder's response alone does not complete a card.

Do not use DeepSeek as the coding Worker on the MacBook or Mini. The linked cutover cards own launcher and credential retirement; preserve their dependency gates. Current binding and rollback: `~/projects/MODEL_SEATS.md`.
<!-- END runtime-doctor:shared:model-seats -->
