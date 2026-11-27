# Writing rules

This document is the owner of the writing rules. `docs/README.md`, which owns the rule that each rule lives in one
document, names this document, and the root index, `README.md`, names it too. The other documents link to this
document and state no writing rule of their own. `agent-status.md` keeps the agent status and the links, and it
holds no writing rule.

The rules are read by `tools/check_documents.py`, a developer script that states that the test set does not read
it, and by one pin, `tests/test_layout.py::test_the_indexes_name_every_document_under_them`, which reads names and
not wording. "Check n" below is a check in `tools/check_documents.py`.

## The rules

1. **Machine-readable tables are code.** A document explains a table and never restates it row by row, so a
   regenerated table cannot drift. Check 7 reads this rule for the input shape table in `src/input_shapes.py`: four
   consecutive words of a row inside a quotation or a code span, or six consecutive words in prose, is a restated
   row. The guard is the length, so a short quote of a row is not a finding.
2. **No test counts in a document.** A document names the test that pins a rule; the count lives in
   `agent-status.md` and the git history. Check 5 reads the documents for a count, and check 1 reads every markdown
   document for a test-name claim, including the tracking markdown, so `agent-status.md` and `acceptance.md` are
   read for the claims and not for the count rule.
3. **A document that names a test names a test that exists.** Check 1 reads each claim in the shape
   `tests/<module>.py::<name>` and answers whether the named module defines the name.
4. **A pin measures content or a name, never the wording of a document.** A wording check is a document review, so
   it lives in `tools/check_documents.py`, which the test set does not read (`docs/ARCHITECTURE.md` §1.1).
5. **A claim about what the tool does must name the module or the test that holds it.** A feature id is written
   only when a module or a test uses it as a name.
6. **ASD-STE100 Simplified Technical English**, no marketing voice, no emoji.
7. **A historical record is not kept in the markdown.** The git history is the record, and the markdown states the
   current state.
8. **A record is data, so a document describes its fields and never restates a record.** The example in
   `docs/USAGE_GUIDE.md` is an illustration with a shortened hash, and not a pin.
9. **Completed epic, phase, feature and task detail is removed from the tracking markdown after the work is
   committed.** `AGENTS.md` owns this rule, so this document links to it.

The index rule, that each index names every document under it, is owned by `docs/ARCHITECTURE.md` §1.1, so this
document links to it: `docs/README.md` names this document, and the root index names this document.

## What these rules do not cover

The gate and CI rules are outside this document, and the shape-table and write-path watch list is outside it. The gate
and CI rules have their own owner document, `docs/GATE_AND_CI.md`. The watch list stays recorded open in `backlog.md`,
with the document it needs. This document states no rule that a run measures; it states only what a document may hold.
