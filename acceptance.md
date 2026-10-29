# Acceptance criteria — housekeeping: clean the root markdown

This is a documentation cleanup task. No converter behavior changes. The scope is the markdown
files in the repository root; `docs/` is not changed. The user confirmed three rules for this task:

1. Only the root markdown files are cleaned.
2. Completed work is removed strictly per `AGENTS.md`: completed epic, phase, feature and task
   detail comes out of the markdown, and the git history holds it.
3. `ADVERSARIAL_AUDIT_REPORT.md` is removed, because the audit is complete.

## Decisions

### 1. What "completed work" means for each file

- `PLAN.md`: remove the Epic 4 and Epic 5 sections (both epics are complete) and the
  per-feature paragraphs for F6.1 to F6.6 (features complete inside an open epic). Keep the
  goals table, a short current state, and the open Epic 6 work (F6.7 plus the open pieces).
  Every rule reference points to its owner document (`docs/ARCHITECTURE.md`,
  `docs/CODEBASE_ASSEMBLY.md`) or to `backlog.md`.
- `backlog.md`: remove items that state completed work (the "Notes on Already-Completed Work"
  section, the per-feature landed decision summaries, items worded as "landed as Fx.y", the
  audit reference). Keep open items, tech debt, out-of-scope items, nice-to-haves, and design
  decisions that are still live rules, because a test or a module still holds them.
- `agent-status.md`: keep the current position, the rules for writing documents, and the open
  watch items. Remove the completed-feature change lists and the measured facts, because the
  git history holds them.
- `acceptance.md`: holds only the acceptance record for the current task, as the house rule
  states. This file is that record.
- `README.md`: user-facing documentation, not a tracking board. Keep it, and fix only stale
  references.

### 2. The audit report

`ADVERSARIAL_AUDIT_REPORT.md` is removed. The house rule that a historical record keeps its
findings applies while the record is open work; this audit is closed, and the git history holds
the report. `PLAN.md` states the three closed problems in one sentence without naming the file.

### 3. Pointers the cleanup would leave dangling

A test or module docstring that names a removed markdown section must point to the owner
document instead. Only the specific pointers are changed, and no test asserts a markdown file:

- `import_blocks.py` rule 5 names `acceptance.md` Decision 3; it changes to
  `docs/CODEBASE_ASSEMBLY.md` §7, which is the owner document for the rule.
- `tests/test_scope_objects.py` names `acceptance.md` decision 11; it changes to
  `docs/CODEBASE_ASSEMBLY.md` §8.
- `tests/test_smoke.py` names `to-do.md` F1.2-F1.4, tasks completed long ago; it changes to the
  git history.
- The data-module test docstrings that say "and `acceptance.md`" name a record that changes with
  every feature; they name the module, which is the owner, instead.

### 4. Quality gates

- `ruff check .` is clean and `pytest` is green after the change. No test logic changes; only
  docstring text changes.
- Every markdown link still resolves to a file that exists.
- No file states a fact that no module, test, or owner document holds.

## Acceptance criteria

1. `ADVERSARIAL_AUDIT_REPORT.md` is gone, and no markdown or Python file references it.
2. `PLAN.md` holds no completed epic or feature detail; it states the current state, the goals,
   and the open Epic 6 work, and each rule points to its owner document.
3. `backlog.md` holds no completed-work item: no "landed as" item, no already-completed-work
   notes, no audit reference. Every remaining item is open work, tech debt, out of scope, a
   nice-to-have, or a still-live design decision.
4. `agent-status.md` states where the work stands and what to watch; it carries no
   completed-feature change list.
5. `to-do.md` tracks this task's pieces and the open Epic 6 pieces, and no completed task stays
   in it after the commit.
6. `acceptance.md` is this record.
7. `README.md` has no stale reference, and every link resolves.
8. `ruff check .` is clean, `pytest` is green, and the change is committed.
