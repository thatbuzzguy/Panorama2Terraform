# Acceptance criteria

This file carries the record for each active task, joined by hand at each merge. Each section names the worktree or
branch that owns it. The Piece 12A.3 record is main's, the current task on main. The Epic 13 and Epic 14 records are
pointers: both epics still have open pieces in `to-do.md`, and their criteria are not restated here.

## Piece 12A.3, the statements the documents make about the pins (main, the current task on main)

Piece 12A.3 of Epic 12, the pins. The decisions this piece reads are already taken and landed: the Terraform minimum
is `>= 1.16`, CI runs the 1.16 line at its newest patch (1.16.7), and the provider pin is `~> 2.0.15`. Piece 12A.1
landed the owners and the helpers, Piece 12A.2 moved the owner value and the committed bytes. This piece moves the
document statements, so the documents agree with the pins the codebase already holds.

The pin owners this piece reads, and does not move:

- the Terraform minimum, `src/commit_actions.py::TERRAFORM_MINIMUM`;
- the provider version, `tests/conftest.py::declared_provider`, read from a committed golden `provider.tf`;
- the Terraform version CI runs, the `terraform-gate` job of `.github/workflows/python-tests.yml`.

### Files this piece moves

1. `README.md`: the pinned provider statement, the Terraform requirement line, and the provider fact in the location
   section. The check for other version statements in the document answers these three and nothing else.
2. `docs/USAGE_GUIDE.md`: the pinned provider statement and the Terraform requirement line.
3. `docs/RESOURCE_MAPPING.md`: the pinned provider statement, and the provider fact in the Verification section. The
   dated provider facts in the body stay as they were measured.
4. `docs/COVERAGE_MATRIX.md`: the version the golden `provider.tf` declares, which is the version the schema pins
   read.
5. `docs/CODEBASE_ASSEMBLY.md`: line 9, the sentence that names the pinned provider for the document; §12, the one
   place that states why the 2.0.14 measurements hold for 2.0.15; and the §10 sentence that states what the committed
   goldens declare, which is a live statement of the minimum.
6. `docs/ARCHITECTURE.md`: the one live statement of the pin in that document, the §6 sentence that names the pinned
   provider schema for the drift rows. Its other 2.0.14 statements are dated measurements and stay. The file is in
   this piece's list because the sweep over the documents finds one live statement there, so the criteria below read
   it too.
7. `agent-status.md`: the position record for this piece, and the CI rule that says the statements are brought up to
   the CI version.
8. `to-do.md` and `PLAN.md`: the piece closes Epic 12, so the Epic 12 piece list and the Epic 12 planning section are
   removed and the git history holds them.
9. `backlog.md`: only for a finding this piece opens.

### Criteria

1. Each pin has one owner statement. A document names the owner it reads the value through, and states the value only
   as the pin itself or as the measurement it made; no document states a pin as the project's rule through a copy of
   the version.
2. Every document that states the pin names the pinned provider, `~> 2.0.15`, and names the owner it reads the value
   through. A dated measurement may name the version it was measured on; what cannot stay is a sentence that names
   that version as the pin.
3. A dated measurement stays as it was measured, and no measurement is restated to a different version. §12 carries
   one sentence that states the schema identity, so a provider fact measured against 2.0.14 holds for the pinned
   provider without changing the record of what was measured.
4. The level the action grammar needs, 1.14, stays as a measurement of the language. Only a statement of the project
   minimum moves, and no live statement of the project minimum reads 1.14, in the documents or in the status file. A
   code comment that states 1.14 as the grammar level is not the project minimum and stays.
5. §12 records the re-measurement of the schema identity on the tree this piece runs on: `terraform providers
   schema -json` answers byte for byte the same for 2.0.14 and 2.0.15, 2,146,401 bytes, md5
   `b7d5dcfbe72207e90c09e38fcbed2747`, measured 2026-11-23. The figures `PLAN.md` recorded on 2026-11-22 (2,146,209
   bytes, md5 `dfab791bae568bdd5ccdc69ca066a5b4`) cannot be reproduced from the whole document on this run, so the
   sentence names the run it rests on and the difference stays reported.
6. The gate is measured on the CI line where the binary is available. The binary on this machine is Terraform 1.16.2,
   so the CI line is measured through a 1.16.7 binary held in `/tmp/opencode`, taken from the release and checked
   against the published SHA256SUMS. Every recorded number names the binary that answered it. If the CI line cannot
   be run here, that is the finding, and no measurement is claimed on it.
7. No test changes. The pins read the minimum through `tests/conftest.py::declared_terraform_minimum` and the
   provider version through `tests/conftest.py::declared_provider`, so a document edit moves no pin and no golden.
8. The document rules hold: no document states a test count, a document that names a test names a test that exists,
   and `python3 tools/check_documents.py` reports no finding on the final tree. The three exact phrases the script
   reads — the console line shape, the phrase that the root index names the test set, and the phrase that `README.md`
   §Testing names each entry once — are not changed by this piece.
9. The gate is measured single-threaded and conservatively: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest`, one process, no parallel plugin. The Piece 12A.2 baseline
   is 1,796 passed and 4 `tflint` skips, so 1,800 pins in 54 modules.

### Definition of done

The six documents and the status file state the pinned values through their owners, no document carries a stale pin
value, §12 names the schema identity so the earlier measurements hold on the pin, the gate is green on the tree that
holds the piece, and Epic 12 closes.

## Epic 13, the shapes an input can be (the `input-shapes` worktree)

Pointer. The design record is `docs/INPUT_SHAPES.md`, the pieces are in `to-do.md` §Epic 13, and the live facts are in
`backlog.md`. The criteria this file held for that worktree are in `d4996b5`; they are not restated here, and no piece
of Epic 13 is open on main for this task.

## Epic 14, the blocks a run binds to the live config (the `import-pairing` worktree)

Pointer. The design record is `docs/IMPORT_BINDING.md`, the pieces are in `to-do.md` §Epic 14, the decisions are in
the record §2, and the live facts are in `backlog.md`. The criteria this file held for that worktree are in `0b917e7`;
they are not restated here. No decision is taken, so no piece can be written from one yet, and no `src/` file is
touched until a piece lands.
