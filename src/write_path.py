"""F6.10.3 the write path: the two file sets, and the one place that forces LF.

`docs/CODEBASE_ASSEMBLY.md` §14 decides which set each file belongs to. Three rules, stated once here.

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

Usage:
    from write_path import LF, root_path, unit_path, write_file
    write_file(unit_path(output_dir, row['directory'], 'provider.tf'), text)
    write_file(root_path(output_dir, unit_manifest.MANIFEST_FILE), unit_manifest.render(rows))
"""

from pathlib import Path

# The only line ending a run writes (rule 1). `os.linesep` is not used anywhere in the write path.
LF = '\n'


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
        path.write_text(contents, encoding='utf-8', newline=LF)
