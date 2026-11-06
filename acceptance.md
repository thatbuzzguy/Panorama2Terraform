# Acceptance criteria — the Epic 8 plan (task for this commit)

Scope: documents only. This task writes no code and no test, so no golden moves and no pin changes.
The deliverable is the design record for the second conversion path, plus the tracking markdown that
carries it. The rule that makes a document a finding is the one in `AGENTS.md`: a claim about what the
tool does must name the module or the test that holds it, and each index must name every document
under it.

## 1. The design record

1.1 `docs/API_CONVERSION_PATH.md` is the owner document for the path 2 rules, and `docs/README.md`
names both the document and the rules it owns.

1.2 The record states which parts of the pipeline path 2 shares with path 1, and states that path 2
adds no second version of them. The pins that read the `src/` set are named.

1.3 The record states the three accepted request shapes, and names the one decision that must be made
before any other path 2 piece can be written: the wrapper rule for the op shape, and how
`container_coverage.SCOPE_PATH_ROOTS` reads a `predefined` path.

1.4 The record states that the scope set is read from the responses, never guessed, and that path 2
never assembles one tree from many responses, because the line map, the entry ledger, and the parent
walk are keyed on the source that was parsed.

1.5 The record states the facts only a live target states, the request shape that gives each one, what
each one unlocks, and the condition that keeps it blocked. It states no fact as available.

1.6 The record states what path 2 does not close, so the plan does not promise a parse gap as an input
gain.

1.7 The record states the offline rule for path 2, and the agreement rule between the two paths for
content with no live-only fact.

1.8 The record names the two modules path 2 adds, and the rule each keeps.

## 2. The tracking markdown

2.1 `PLAN.md` carries Goal 7 and Epic 8 with the four phases and the definition of done for the epic.
It states no rule that the design record owns.

2.2 `to-do.md` holds the buildable pieces for Epic 8, in the order the design record states them, and
each piece names the module and the test that will hold its rule. It holds no piece that needs a
server.

2.3 `backlog.md` records the blocked path 2 facts and links to the design record instead of restating
the shapes.

2.4 `agent-status.md` names the current position, the next piece, and the pieces that stay blocked.

## 3. The checks

3.1 `ruff check .` is clean.

3.2 `python3 -m pytest` passes 1567 pins with no skip. No code and no fixture moved, so the pins read
the same set as before.

3.3 The commit is markdown only, with an ASD-STE100 message.

## Result

Measured after the change: `ruff check .` is clean, and `python3 -m pytest` collects and passes 1567
pins with no skip. `git status` names only the tracking markdown and the documents: `PLAN.md`,
`backlog.md`, `to-do.md`, `acceptance.md`, `agent-status.md`, `docs/README.md`, and the new
`docs/API_CONVERSION_PATH.md`. No code, no test, and no fixture moved.
