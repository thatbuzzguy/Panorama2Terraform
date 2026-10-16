# Acceptance criteria — F3.10 Architecture document (Epic 3)

F3.10 states the whole pipeline in one document: the data model, the parse
pipeline, the emit pipeline, and the naming rules. It is the last feature of
Epic 3.

## Audit before writing (2026-10-16)

- The three rules a reader must hold together live in three different places:
  the naming rule in a docstring and the README, the location rule in
  `location_block` and the README, the report grouping rule in
  `_report_scope_path` and three docs.
- No document states the data model (identity is the four scope facts) or the
  parse pipeline (safe read, parent map, association tables) as a whole.
- The container table that F4.2 will formalise exists only as the paths inside
  the parse methods.
- One parsed area reaches no output: `parse_regions` returns objects that only
  the console count uses. The document must say that, not claim that every
  entry is accounted for.

## Criteria

1. **File:** `docs/ARCHITECTURE.md` exists and contains the four required
   sections: data model, parse pipeline, emit pipeline, naming rules.
2. **One place for each rule.** The naming rule, the location rule, the
   reference-resolution rule and the report grouping rule are stated once, in
   this document. The README and the other docs link to it instead of
   repeating the rule text.
3. **Every claim matches the code.** Each rule is checked against the
   implementation, not against a previous document.
4. **Every claim is pinned.** Each statement names the test that pins it, or
   is labelled as a design rule enforced by construction, or is labelled as
   not implemented. No statement claims a test that does not exist.
5. **No claim that the document contradicts `backlog.md`** (rulebase not
   emitted, profile bodies not parsed, EDL credentials not parsed, service one
   leg, `location.template_stack` never used).
6. **The document states what the converter does not do.** F4.1, F4.2 and F4.3
   are not implemented; the document does not describe them as behaviour.
7. **Container table.** One row per parse method: the container it reads and
   where its entries go (resource, report, inventory comment, or count only).
8. **New test:** one test pins the data-model claim that every parse method
   records the four scope facts on every object it returns.
9. **Style:** ASD-STE100 short sentences, tables for the mappings, no
   marketing claim, no unverified percentage.
10. **Gates:** ruff clean, pytest green (439 with the new test), terraform
    validate green. No converter code change, so both golden sets stay
    byte-identical.

## Result (2026-10-16)

- `docs/ARCHITECTURE.md` written: modules, data model, parse pipeline, emit
  pipeline, naming rules, determinism, and the non-claims section.
- Every cited test name verified against the test files by script: 20 explicit
  `file::test` citations and 37 short-form citations, all resolve.
- Every rule read back from the implementation, not from a previous document.
- One gap found: `parse_regions` reaches no output (count only). Recorded in
  `backlog.md`; the document states it rather than claiming full accounting.
- One new test added (criterion 8). De-duplicated prose in README,
  `docs/MIGRATION_GUIDE.md` and `docs/USAGE_GUIDE.md`; the stale
  `security_rules.tf` tree line corrected.
- Gates: ruff clean, pytest 439 passed, terraform validate green (5 tests).
  Both golden sets byte-identical (no converter code change).
