# Acceptance — criteria for Epic 13, the shapes an input can be (2026-11-23)

The task is the planning of Epic 13 in the `input-shapes` worktree. The Epic 12 criteria this
file held are in `a153b04`. The design record is `docs/INPUT_SHAPES.md`, the pieces are in
`to-do.md`, and the live facts are in `backlog.md`.

## Criteria

1. **The archive input gains a producer, not a check.** The F5.1 rule is unchanged:
   `check_bytes` is the one definition of the two checks, and the door runs them on the
   decompressed bytes. No module states a second size definition, a second DTD rule, or a second
   reader.
2. **The size cap holds during decompression.** A pin hands the door a compressed input that
   expands past the cap, and the refusal names the origin and builds no tree. The pin runs
   offline on a committed fixture, so Goal 1 and the no-network rule are unchanged.
3. **The accepted shapes are read from the bytes, not from the file name.** The single-member
   gzip and single-XML-member tar.gz shapes are accepted only after the member decision is taken.
   A selection rule that reads member order is refused by the determinism rule
   (`docs/ARCHITECTURE.md` §6), so the refusal is the starting shape and the decision must be
   taken before an emitter, a gate rule, or a report can read a selection.
4. **One decision, stated once, for what the provenance record names for an archive read**: the
   origin kind, the member name, which bytes `size` and `sha256` name, and how the cache rule
   reads. The F5.3 rule already answers the byte question for the door — the record names the
   bytes the door checked — so the decision is how the archive enters that rule, not a second
   version of it.
5. **The splitter diagnostic prints the fact, not a guess.** It states the number of
   `device-group/entry` rows read, the shape the tree holds instead, and the source line. The
   finding fits the four parts of the console-line rule (`container_coverage.console_line`,
   `docs/ARCHITECTURE.md` §3.2), or prints in the report only because it compares two sets. The
   exit code stays with the rules that read the files (`docs/ARCHITECTURE.md` §4.6).
6. **Fixtures move the pins in one commit.** Each accepted shape gets a committed fixture read
   through the fixture assembler, and the pins that state the printed fixture set name the new
   fixture count in the same commit (`to-do.md` §Rules the layout keeps).
7. **Version facts stay measurements.** The comparison of the "XML and XPath" page names the
   pages measured — 9.1 and 11.1 & Later, 2026-11-23, same node model and entry shape — and the
   10.2 leg stays open until measured. No document states a version difference it cannot name a
   measurement for. The documentation-to-fixture relationship is owned by
   `docs/API_DOCUMENTATION_AND_MOCKS.md`, so this epic adds no second rule for it.
8. **Live-target facts stay in `backlog.md`**: the UI download form, the backup DOCTYPE question,
   multi-member bundles, and the unfinished comparison leg. Nothing in the design record states
   them as facts.
9. **The layout rules hold**: `docs/INPUT_SHAPES.md` is named in the `docs/README.md` index and
   carries its owner row; the shape table names its owner module in the `docs/ARCHITECTURE.md` §1
   table when it lands; no new module states a second naming rule, writer, console line, or
   environment name, so the pins that scan the `src/` set read it with the other modules.
10. **No `src/` path that Epic 11C or Epic 12 runs on is touched by this worktree**, and the
    shared tracking markdown is merged by hand against main.

## Definition of done

Every rule in `docs/INPUT_SHAPES.md` names its owner. Each pending decision in §2 is recorded as
a decision before the code that reads it lands, and the pins that hold each rule run offline on
committed material.
