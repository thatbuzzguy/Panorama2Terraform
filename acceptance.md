# Piece 23 acceptance criteria — the stale line-count entry in `backlog.md`, §`src/split_device_groups.py`

The last open item in the 2026-11-12 audit's `src/split_device_groups.py` set says `docs/LICENSING.md` still
states 130 lines for `src/split_device_groups.py` and calls it "the upstream, unchanged". This piece measures the
current facts and closes the entry.

Closed conditions:

1. The finding is measured, not assumed: the document's numbers are re-read at the commit the document names as
   its measurement, and the working-tree count is measured separately.
2. If the measurement agrees with `docs/LICENSING.md`, the completed finding entry is removed from `backlog.md`,
   and the fact is stated nowhere else: the git history and the owner document (`docs/LICENSING.md`) hold it.
3. If the measurement contradicts `docs/LICENSING.md`, the document is fixed and the measurement is recorded here.
4. The gate, single-threaded: `ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py` reporting
   no finding, and the full `python3 -m pytest`. The pin count does not move: this piece adds, removes and weakens
   no pin.

Criteria for the measurement:

1. `docs/LICENSING.md` names commit `ac7609e` (measured 2026-11-16) as the measurement for the split, through
   `git blame --line-porcelain`, counted by author.
2. `docs/LICENSING.md` states 68 upstream lines for `src/split_device_groups.py` in the inherited set, and the
   notice as "GSW Systems, 2025, for the lines it wrote: 68 of 383".
3. `git blame ac7609e --line-porcelain -- src/split_device_groups.py` answers 68 lines for the upstream author, and
   `git show ac7609e:src/split_device_groups.py` answers 383 lines, so both numbers the document states for that
   file agree with the measurement at the commit the document names.
4. `docs/LICENSING.md` states that neither GSW Systems file is upstream whole, so the notice covers the lines the
   header names and not the file, and that a notice saying "the upstream, unchanged" would claim more than the
   measurement supports. `tools/check_documents.py` reads that rule: for each notice row it compares the upstream
   count with `git blame` at the named commit, compares the file total in the "X of Y" claim with `git show` at
   that commit, and reports a finding when a claim says "unchanged" while the upstream count is less than the file
   total. The document states no such claim, so no finding.
5. `python3 tools/check_documents.py` reports no finding, including the LICENSING checks above.
6. The working tree measures 384 lines for the file, 60 of them upstream. This is not the set of numbers the tool
   reads, because the tool reads the file total at the commit the document names, so a later edit to the file
   cannot move a number the document states. The `backlog.md` entry is stale on two counts: it names a number the
   document no longer states, and a wording the document no longer uses.
7. No test reads `docs/LICENSING.md`, so the pin count cannot move with this piece; the check is the tool.

Measurement, as it landed (2026-11-20):
- `git blame ac7609e --line-porcelain -- src/split_device_groups.py`: 68 lines by `devnullNZ`, which is the number
  the document states in both tables.
- `git show ac7609e:src/split_device_groups.py`: 383 lines, which is the number the notice's claim states.
- Working tree: `src/split_device_groups.py` 384 lines, 60 of them upstream, and the file holds Piece 6's decisions.
- `python3 tools/check_documents.py`: no finding.
- Decision: the finding is already closed by the measurement `docs/LICENSING.md` records, so the entry is removed
  from `backlog.md` and the fact is restated nowhere else. No document was fixed.

Gate measurement, as it landed (2026-11-20, on the final tree, single-threaded): `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 103 Python files, `python3 tools/check_documents.py` reports no finding, and
`python3 -m pytest` passes 1,717 pins with the same 4 skip for the missing `tflint` binary — 1,721 pins in 53 test
modules, as Piece 22 left them, in 5m40s (309.24s). The pin count did not move, because this piece adds, removes
and weakens no pin and no test reads `docs/LICENSING.md`.
