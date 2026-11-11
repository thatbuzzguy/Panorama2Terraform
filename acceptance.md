# Acceptance criteria — the licensing rule: our contributions under AGPL v3

## Scope

This repository is a fork of [gswsystems/Panorama2Terraform](https://github.com/gswsystems/Panorama2Terraform),
taken at v4.0.2 (commit `92cb2a3`, 2025-12-09), so it carries the upstream's two license files and the
upstream's authorship claims. Measured 2026-11-11 through `git blame` on the committed tree: 59,329 tracked
lines, 2,172 (3.7%) authored by the upstream and 57,157 by us. In `src/`, `tests/` and `tools/`: 588 upstream
lines against 50,008 ours. The 130 commits are 9 upstream and 121 ours.

The problem this task fixes: the two license files state one copyright holder for the whole program, and five
`src/` modules carry a header that names the upstream, including two modules that hold no upstream line.

This task states the licensing rule in one owner document, corrects the two notices that name the upstream for
content the upstream did not write, and makes every other statement of the license agree. It adds no test: the
rule is a document rule, and the choice to keep it unpinned is recorded in `backlog.md`. No functional code
changes.

## The rule, in one sentence

The work as a whole is AGPL v3; the upstream holds the copyright on the lines it wrote that are still in the
tree, Ryan Brown holds the copyright on every other line, and the commercial option covers the upstream parts
only, so this project grants no commercial terms for its own contributions.

## The criteria

1. **One owner document.** `docs/LICENSING.md` is the owner of the license rule.
   `docs/DUAL-LICENSING-EXPLAINED.md` is removed, because one rule has one owner document. `docs/README.md`
   names the new document in its index table, `README.md` names it, and `docs/USAGE_GUIDE.md` and
   `docs/ARCHITECTURE.md` §1.1 link to it instead of restating the rule.
2. **The source is named.** The document names the forked repository, the version it was taken at, the commit,
   and the measured split with the date and the method (`git blame`, by author).
3. **The inherited set is a record.** The document lists the files that still hold upstream text, and states
   the rule that a file enters the set by `git blame` and leaves it when its last upstream line is replaced, so
   the set is measured and not decided.
4. **The holders are named for each part.** The document names the holder for the retained upstream lines and
   the holder for every other line, and states that our contributions are licensed under AGPL v3 only.
5. **The commercial option is scoped.** The document states that `LICENSE-COMMERCIAL` is the upstream author's
   grant, that it covers the upstream parts, and that a user cannot get the whole work under commercial terms
   from this project, because the whole work needs a grant for both parts.
6. **The word "non-commercial" is not used as a license name.** AGPL v3 permits commercial use; its condition
   is the copyleft rule, including the network rule (§13). The document states this, so the choice reads as
   "AGPL v3 only" and not as a non-commercial restriction, which AGPL §10 does not allow on a derivative work.
7. **The AGPL duties for a derivative work are kept.** Keep the notices, include the license text, document the
   changes, provide the source to a recipient and to a network user, and license your modifications under
   AGPL v3.
8. **Two notices are corrected.** `src/source_fetch.py` and `src/xml_input.py` name Ryan Brown (2026) and state
   no commercial term, because they hold no upstream line. `src/panorama_to_terraform.py` and
   `src/split_device_groups.py` keep the upstream notice unchanged, because they hold upstream lines. No new
   header is added to a module that has none.
9. **The license texts are not changed.** `LICENSE-AGPL` and `LICENSE-COMMERCIAL` stay byte-identical to the
   upstream's files; the scope of each grant for this fork is stated in the owner document.
10. **The gate is unchanged.** `ruff check .` is clean and `python3 -m pytest` passes the same number of pins
    as before the change, because no pin reads a notice line and no functional code changed.

## Measured

Run 2026-11-11 in the worktree, on branch `licensing`, from `ba6cb17`:

- `ruff check .` - all checks passed.
- `python3 -m pytest` - 1,641 pins, the same count as before the change, exit 0, Python 3.12.3. No pin reads a
  copyright notice, so no pin changed.
- Criteria 1 to 9 are met by the documents and the two notices as written. Criterion 10 is met by the gate run
  above.
- Files the task changed: `docs/LICENSING.md` added; `docs/DUAL-LICENSING-EXPLAINED.md` removed;
  `docs/README.md` (the index row and the owner row); `README.md` (the index entry and the License section);
  `docs/USAGE_GUIDE.md` §License; `docs/ARCHITECTURE.md` §1.1; `src/source_fetch.py`; `src/xml_input.py`;
  `backlog.md`; `PLAN.md`.
- The statement check: a scan of the markdown set for the words "dual", "commercial" and "license" reports the
  owner document, the three documents that link to it, the tracking set, and the four module notices. No
  document restates the rule.
- The notice check: `src/source_fetch.py` and `src/xml_input.py` name Ryan Brown (2026);
  `panorama_to_terraform.py` and `split_device_groups.py` name the upstream; and the other 18 modules name
  none. `git blame` reports 0 upstream lines in the two corrected modules, so each notice agrees with the
  split.
