# Decisions

Why the code is the way it is, where the code can't say it. Newest first.

## 2026-10-16: The claim-source audit keys on structure, not vocabulary

`audit_claim_sources` (in `scripts/librarian.py`) enforces Rule 0 of
`FACT_CHECK_PROTOCOL.md` at save: a grade's source link goes in its own row. It
warns and never blocks, because reports live in the gitignored `library/` and
this is the only automated check they get. Every version that tried to
recognise vocabulary failed review; the surviving rules match structure.

- **Which tables are claim tables.** Keying off a numbered first column missed
  tables that don't number. Adding an allowlist of verdict words
  (grade/verdict/reality/...) missed "Verified?" and "Holds up?". A survey of
  every claim-bearing table in the library found 16 header shapes and the
  verdict column spelled at least seven ways, so any allowlist is one spelling
  behind and each miss is silent. The audit now matches the one invariant word,
  "claim", in any header cell. Two of the 16 shapes are not grading tables
  ("# | beat | claim", "# | claim | where") and get flagged anyway; a false
  positive costs one ignored warning, a miss costs an unsourced grade.
- **When a link-free Source cell is allowed.** Only when the grade *leads* with
  Unverified, where the protocol asks for a search trail instead of a link.
  An allowlist of assertive grade words (confirmed/wrong/imprecise/...) was
  beaten by any spelling outside it ("Misleading, unverified"). Accepting any
  prose would let a "Detail" or "Note" column launder an uncited table, which
  is the 2026-08-14 pattern: prose in every row, links only in a list at the
  bottom.
- **Splitting rows.** The split uses a lookbehind on unescaped pipes. An
  earlier version swapped `\|` for a `\x00` placeholder, which corrupted any
  literal NUL in the source text.
