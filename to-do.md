# To Do — F4.2 Entry coverage: container table and line tracking

Feature: Epic 4 / F4.2. F4.1 (the post-run sanity gate) landed on 2026-10-19.

Why this is the next slice: the gate now checks what the generator wrote. It cannot
say what the input contained. F4.3 (per-entry accounting) needs two things the
parser does not have: a container table in code, and the line where an entry
opened. ElementTree records no line numbers, so the parser must record them during
parse. F4.2 puts that data in place; it does not write a report.

Pieces (one at a time, in order):

- [ ] Overwrite `acceptance.md` with the F4.2 criteria before code or tests.
- [ ] Record the entry opening line during parse (a line-tracking `TreeBuilder`), so
  a report can name file, line, object type.
- [ ] Move the container table from `docs/ARCHITECTURE.md` §3.1 into code: one row per
  parse method (container path → destination kind).
- [ ] Report a container the parser does not know under a known config root, instead of
  skipping it silently.
- [ ] Tests: line tracking pinned on a fixture; the table matches the parse methods
  (every method has a row, every row has a method); an unknown container is reported.
- [ ] Keep the gate green: ruff, pytest, golden tests unchanged, `terraform validate`
  green.
- [ ] Docs: `docs/ARCHITECTURE.md` §3.1 points to the table in code, §7 updated; commit.

Scope guard: F4.3 (the per-entry `CONVERSION_REPORT.txt`) and F4.4 (property level
coverage) are not in this slice.
