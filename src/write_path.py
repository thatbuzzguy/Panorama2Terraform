"""F6.10.3 the write path: the two file sets, and the one place that forces LF.

`docs/CODEBASE_ASSEMBLY.md` §14 decides which set each file belongs to. Seven rules, stated once here.

1. **One function writes bytes.** Every file a run writes goes through `write_file`, so the byte rule
   (`docs/ARCHITECTURE.md` §6) is enforced in one place and not in an operator note: `open(..., 'w')`
   writes `os.linesep`, so a run on a Windows desktop writes CRLF and the goldens stop matching byte for
   byte. `newline=LF` forces LF, which is what the goldens and the determinism rule measure. Text is the
   set a run produces; `bytes` is the source cache, and the cache holds the bytes the door parsed, so that
   half of rule 1 writes them without translation.
2. **Two path builders, one per set.** The unit set is written inside the directory the manifest row names
   (`unit_path`); the codebase root set is written at the codebase root (`root_path`). A writer names which
   builder it uses, so no module builds a path for a file it does not own.
3. **A per-unit file names its unit only by its directory** (§14), so this module states no rule that puts
   a unit inside a file, and no unit-set file name names a unit. The path is the only place a file states
   the unit it belongs to, which is why a gate finding for a per-unit file names the path.
4. **The run writes one directory per unit its own set names, and it writes no directory for a unit it read
   only through the record** (`docs/MULTI_RUN_CODEBASE.md` §6 rule 2). The run's set is `unit_manifest.units`
   over the rows its own ledger read; the codebase's set is `unit_manifest.units` over the merged manifest
   rows read through `parse_rows`. A unit that only the codebase set names gets no directory and no file from
   this run, so the files an earlier run wrote inside it stay as that run wrote them. The write path states no
   unit rule and no unit set of its own: it reads both sets through `unit_manifest`, keeps the two builders of
   rule 2, and names no new file shape. Pinned by
   `tests/test_write_path.py::test_the_run_writes_no_directory_for_a_unit_it_read_only_through_the_record` and
   `tests/test_write_path.py::test_the_write_path_states_the_run_set_rule_and_reads_the_unit_set_through_its_owner`.
5. **The tool owns every file it writes, so a file it has content for is written over the bytes an earlier run wrote
   for it.** `write_file` writes the bytes this run built for the file shape, inside the directory its own set names,
   so a second run inside the same unit directory replaces that file. A shape this run has no content for is not
   written, so the bytes an earlier run wrote for it stay inside the directory. A file outside the two sets is not
   the tool's file, so a run writes none and touches none: `terraform.tfvars` stays the operator's file through
   `docs/CODEBASE_ASSEMBLY.md` §11, and this module names no file. Pinned by
   `tests/test_write_path.py::test_the_run_overwrites_the_files_it_owns_in_a_unit_directory_it_wrote_into` and
   `tests/test_write_path.py::test_the_run_writes_no_file_it_does_not_own`.
6. **The write path holds no delete rule.** `write_file` makes the directory when it is needed and writes the bytes;
   nothing in the module takes a file away, so a run that writes into an existing codebase leaves every file that was
   there, inside its own unit directory, inside a unit it read only through the record, and at the codebase root. The
   only file removal in the tool is the cache prune action, read through `provenance.py`, which acts on cache entries
   outside the two sets. Pinned by
   `tests/test_write_path.py::test_the_run_deletes_no_file_in_the_codebase_it_wrote_into` and
   `tests/test_write_path.py::test_the_write_path_states_no_delete_rule_and_the_only_file_removal_is_the_cache_prune`.
7. **The write path holds no record of what it wrote**, which is the rule `AGENTS.md` states for a historical record.
   A run writes the bytes it built and writes nothing about which run wrote them, so the difference between two runs
   is read through git, which is the rule `docs/MULTI_RUN_CODEBASE.md` §3 rule 6 states for the codebase. Pinned by
   `tests/test_write_path.py::test_the_write_path_holds_no_record_of_what_it_wrote`.

Usage:
    from write_path import LF, root_path, unit_path, write_file
    write_file(unit_path(output_dir, row['directory'], 'provider.tf'), text)
    write_file(root_path(output_dir, unit_manifest.MANIFEST_FILE), unit_manifest.render(rows))
    for facts in unit_manifest.units(ledger):        # the run's set, the rule the writer uses (rule 4)
        write_file(unit_path(output_dir, unit_manifest.directory_name(facts, naming.sanitize), 'provider.tf'), text)
    # A unit that only `unit_manifest.units(unit_manifest.parse_rows(text))` names writes nothing here.
    # A run that writes into a tree an earlier run wrote writes over the file it has content for (rule 5), removes
    # nothing (rule 6), and writes no record of what it wrote (rule 7).
"""

from pathlib import Path

# The only line ending a run writes (rule 1). `os.linesep` is not used anywhere in the write path.
LF = "\n"


def unit_path(output_dir: Path, directory: str, name: str) -> Path:
    """The path of a unit-set file: the directory the manifest row names, then the file name (rule 2)."""
    return Path(output_dir) / directory / name


def root_path(output_dir: Path, name: str) -> Path:
    """The path of a codebase root-set file: one file for the run, at the root (rule 2)."""
    return Path(output_dir) / name


def write_file(path: Path, contents) -> None:
    """Write the bytes the operator receives (rule 1), and make the directory when it is needed.

    A file is written only when it has content; that is the rule the report files, the data files and the
    unit-set files share, so the caller checks the content and this function holds only the byte rule.
    `contents` as `str` is text and takes LF; as `bytes` it is the source cache, and the cache holds the
    bytes the door parsed, so the byte rule there is "no translation".
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contents, bytes):
        path.write_bytes(contents)
    else:
        path.write_text(contents, encoding="utf-8", newline=LF)
