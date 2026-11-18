"""Document checks, not pins (`docs/ARCHITECTURE.md` §1.1).

The test set pins the index rule once, in `tests/test_layout.py`, and reads no document wording: a wording
edit is a document review, not a code failure. This script holds the document-review checks and prints what
disagrees. It is a developer script, so it is not part of the gate, the test set does not read it, and it
imports no tool module (`tools/README.md`): it reads the tool's tables through `ast` and the license split
through `git blame`. It imports only the standard library and writes no file.

Checks:

1. A pin claim in a markdown document names a name the test module defines.
2. The matrix table in `docs/COVERAGE_MATRIX.md` agrees with `resource_mapping.COVERAGE_MATRIX`, row for row.
3. The counts `docs/LICENSING.md` states agree with `git blame` at the commit that document names, with each
   notice's file total read at the same commit.
4. The wording rules the test set held before it stopped reading document prose: the console line shape stated
   once in §3.2, §3.1 pointing at the container table, §4 of `docs/API_CONVERSION_PATH.md` staying the blocked
   live facts, §1.1 stating that the test set is named by the root index, and the §1 rule column naming each
   row shape the module defines.
5. No document states a test count. `agent-status.md` and `acceptance.md` hold the measurement, so they are
   read for the claims and not for the count rule.
6. `README.md` §Testing names each entry once, which is the rule that section states. A pin holds a name being
   present and cannot hold a name appearing once, so this is a document review, not a pin.

Exit 0 when every check agrees, 1 when a finding is printed.
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
TESTS = ROOT / "tests"
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
EXAMPLES = ROOT / "examples"

# The markdown the claim check reads: the four indexes, the documents, the tracking markdown, and the two
# `.github/` contribution templates, which the root index names because `.github/` holds no index of its own
# (`docs/ARCHITECTURE.md` §1.1).
MARKDOWN = (
    [ROOT / "README.md", ROOT / "AGENTS.md"]
    + sorted(DOCS.glob("*.md"))
    + sorted(EXAMPLES.glob("*.md"))
    + sorted(TOOLS.glob("*.md"))
    + sorted((ROOT / ".github").glob("*.md"))
    + [ROOT / name for name in ("PLAN.md", "backlog.md", "to-do.md", "agent-status.md", "acceptance.md")]
)

# `agent-status.md`, `acceptance.md` and the tracking markdown hold the measurement, so they are read for the
# claims and not for the rule that a document states no test count. The documents and the indexes are the set
# the count rule reads.
DOCUMENT_MARKDOWN = (
    [ROOT / "README.md", ROOT / "AGENTS.md"]
    + sorted(DOCS.glob("*.md"))
    + sorted(EXAMPLES.glob("*.md"))
    + sorted(TOOLS.glob("*.md"))
)
COUNT_MARKDOWN = DOCUMENT_MARKDOWN

CLAIM_RE = re.compile(r"`(tests/[A-Za-z0-9_]+\.py)::([A-Za-z0-9_]+)`")
# A test count, not a path number: `path 2 pins` names the pins of path 2, so the lookbehind excludes it.
COUNT_RE = re.compile(r"(?<!path )(?<!F\d )\b(\d[\d,]*) (pins|test modules|test functions|collected pins)\b")
# A list entry in `README.md` §Testing is one name, so the check reads the name at its start and no prose.
ENTRY_RE = re.compile(r"^- `([^`]+)`")
UPSTREAM = "devnullNZ"
OURS = "Ryan Brown"

# Each row shape, and the §1 row whose rule column must name it. The matrix row shape is stated by the test
# that reads the matrix, so its §1 row is the table owner.
SHAPES = (
    ("src/site_data.py", "site_data.py", "SITE_ROW_FIELDS"),
    ("src/commit_actions.py", "commit_actions.py", "ACTION_ROW_FIELDS"),
    ("src/import_blocks.py", "import_blocks.py", "IMPORT_ROW_FIELDS"),
    ("tests/test_coverage_matrix.py", "resource_mapping.py", "MATRIX_ROW_FIELDS"),
)

findings = []


def claim_names(module: Path) -> set[str]:
    """The names a test module defines: its pins, and the helpers and constants a claim can name."""
    tree = ast.parse(module.read_text(encoding="utf-8"))
    names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    names |= {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    return names


def check_claims() -> None:
    """Check 1: every `tests/<module>.py::<name>` claim names something the module defines."""
    for md in MARKDOWN:
        for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            for file, name in CLAIM_RE.findall(line):
                module = ROOT / file
                if not module.is_file():
                    findings.append(
                        f"{md.relative_to(ROOT)}:{lineno}: claim names a module that does not exist ({file})"
                    )
                    continue
                if name not in claim_names(module):
                    findings.append(
                        f"{md.relative_to(ROOT)}:{lineno}: claim names a name the module does not "
                        f"define ({file}::{name})"
                    )


def code_matrix() -> list[dict]:
    """`resource_mapping.COVERAGE_MATRIX` read as data, through `ast`, so the script imports no tool module."""
    tree = ast.parse((SRC / "resource_mapping.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "COVERAGE_MATRIX"
        ):
            return list(ast.literal_eval(node.value))
    return []


def check_matrix_table() -> None:
    """Check 2: the document table shows the code table, row for row, on the six fields it can show."""
    text = (DOCS / "COVERAGE_MATRIX.md").read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.startswith("| `panos")]
    code = {row["resource"]: row for row in code_matrix()}
    shown = set()
    for line in rows:
        parts = [p.strip().strip("`") for p in line.split("|")[1:-1]]
        shown.add(parts[0])
        row = code.get(parts[0])
        if row is None:
            findings.append(f"docs/COVERAGE_MATRIX.md: row {parts[0]} is not in the code table")
            continue
        for index, field in enumerate(
            ("resource", "xml_element", "xml_name", "emitted_name", "fixture", "output_file")
        ):
            if parts[index] != row[field]:
                findings.append(
                    f"docs/COVERAGE_MATRIX.md: row {parts[0]} states {parts[index]} for {field}, "
                    f"the code table states {row[field]}"
                )
    for resource in code:
        if resource not in shown:
            findings.append(f"docs/COVERAGE_MATRIX.md: the code table row {resource} is not in the document table")


def blame_by_author(rev: str, paths: list[str]) -> dict[str, int]:
    """The lines by author for a set of tracked files at one commit, through `git blame --line-porcelain`."""
    counts: dict[str, int] = {}
    for name in paths:
        out = subprocess.run(
            ["git", "blame", rev, "--line-porcelain", "--", name], cwd=ROOT, capture_output=True, text=True
        ).stdout
        for line in out.splitlines():
            if not line.startswith("\t") and line.startswith("author "):
                counts[line[7:]] = counts.get(line[7:], 0) + 1
    return counts


def file_lines_at(rev: str, name: str) -> int:
    """The lines a file holds at the commit the document names, through `git show`.

    The document states the split as measured at that commit, so every part of the measurement is read at that
    commit. Reading the total from the working tree would move a count on any later edit, which is what the
    document says must not happen.
    """
    out = subprocess.run(["git", "show", f"{rev}:{name}"], cwd=ROOT, capture_output=True, text=True).stdout
    return len(out.splitlines())


def check_licensing() -> None:
    """Check 3: the counts `docs/LICENSING.md` states agree with `git blame` at the commit it names.

    The document names the commit it was measured at, so the numbers stay checkable after the tree changes:
    a later edit moves a count, and the document then has to name a new measurement. Both sides are read at that
    commit, so the `ruff format` pass over the Python files cannot move a count the document states.
    """
    text = (DOCS / "LICENSING.md").read_text(encoding="utf-8")
    stated_rev = re.search(r"at commit `([0-9a-f]{7,40})`", text)
    if not stated_rev:
        findings.append("docs/LICENSING.md: the split must name the commit it was measured at")
        return
    rev = stated_rev.group(1)
    tracked = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", rev], cwd=ROOT, capture_output=True, text=True
    ).stdout.split()
    per_file = {name: blame_by_author(rev, [name]) for name in sorted(tracked)}

    def stated(pattern: str) -> tuple[int, int, float | None]:
        """The pair a table row states, as (upstream, ours, upstream share in percent). The share is None when
        the row states no share, as the commits row does, and the tool then checks only the pair.
        """
        match = re.search(pattern, text)
        if not match:
            findings.append("docs/LICENSING.md: the split table does not state the pair this check reads")
            return (0, 0, None)
        groups = match.groups()
        share = float(groups[1]) if len(groups) == 3 else None
        return (int(groups[0].replace(",", "")), int(groups[-1].replace(",", "")), share)

    def measured(paths: list[str]) -> tuple[int, int]:
        agg: dict[str, int] = {}
        for name, authors in per_file.items():
            if paths and not any(name.startswith(p) for p in paths):
                continue
            for author, count in authors.items():
                agg[author] = agg.get(author, 0) + count
        return (agg.get(UPSTREAM, 0), agg.get(OURS, 0))

    log = subprocess.run(["git", "log", rev, "--format=%an"], cwd=ROOT, capture_output=True, text=True).stdout
    commits: dict[str, int] = {}
    for author in log.splitlines():
        commits[author] = commits.get(author, 0) + 1

    for label, pair, fact in (
        ("whole tree", stated(r"Tracked lines, whole tree \| ([\d,]+) \((\d+\.\d)%\) \| ([\d,]+)"), measured([])),
        (
            "src/, tests/ and tools/",
            stated(
                r"Tracked lines in `src/`, `tests/`, `tools/` \| ([\d,]+) "
                r"\((\d+\.\d)%\) \| ([\d,]+)"
            ),
            measured(["src/", "tests/", "tools/"]),
        ),
        ("commits", stated(r"Commits \| (\d+) \| (\d+)"), (commits.get(UPSTREAM, 0), commits.get(OURS, 0))),
    ):
        if pair[:2] != fact:
            findings.append(
                f"docs/LICENSING.md: the {label} count states {pair[:2]}, git blame at {rev} measures {fact}"
            )
        elif pair[2] is not None and fact[1] and round(100 * fact[0] / sum(fact), 1) != pair[2]:
            findings.append(
                f"docs/LICENSING.md: the {label} row states the upstream share as {pair[2]}%, "
                f"which is {round(100 * fact[0] / sum(fact), 1)}% at {rev}"
            )

    # The inherited set: one row per file that still holds an upstream line, and the total as the sum of the
    # rows, so the count is stated as derived from the table.
    upstream_rows = {name: counts[UPSTREAM] for name, counts in per_file.items() if counts.get(UPSTREAM, 0)}
    table = {}
    for line in text.splitlines():
        if not line.startswith("| `") or "|" not in line[2:]:
            continue
        parts = [p.strip().strip("`") for p in line.split("|")[1:-1]]
        if len(parts) == 2 and parts[1].replace(",", "").isdigit():
            table[parts[0]] = int(parts[1].replace(",", ""))
    if not table:
        findings.append("docs/LICENSING.md: the inherited set table was not read")
        return
    if set(table) != set(upstream_rows):
        findings.append(
            "docs/LICENSING.md: the inherited set names "
            f"{sorted(set(upstream_rows) - set(table))} that the table does not, and "
            f"{sorted(set(table) - set(upstream_rows))} that holds no upstream line"
        )
    for name, count in table.items():
        if upstream_rows.get(name) != count:
            findings.append(
                f"docs/LICENSING.md: {name} states {count} upstream lines, "
                f"git blame at {rev} measures {upstream_rows.get(name)}"
            )
    total = re.search(r"The set is (\d+) files and ([\d,]+) upstream lines", text)
    if total and (
        int(total.group(1)) != len(upstream_rows) or int(total.group(2).replace(",", "")) != sum(upstream_rows.values())
    ):
        findings.append(
            f"docs/LICENSING.md: the set states ({total.group(1)}, {total.group(2)}), "
            f"git blame at {rev} measures ({len(upstream_rows)}, {sum(upstream_rows.values())})"
        )

    # The notice table: the count agrees, and a module the measurement shows is not upstream whole cannot be
    # claimed as "the upstream, unchanged".
    notice = text.split("## The copyright notices in `src/`")[1].split("##")[0]
    for line in notice.splitlines():
        if not line.startswith("| `src/"):
            continue
        parts = [p.strip().strip("`") for p in line.split("|")[1:-1]]
        name, count, claim = parts[0], int(parts[1]), parts[2]
        if upstream_rows.get(name, 0) != count:
            findings.append(
                f"docs/LICENSING.md: the notice table states {count} upstream lines for {name}, "
                f"git blame at {rev} measures {upstream_rows.get(name, 0)}"
            )
        held = file_lines_at(rev, name)
        share = re.search(r"(\d+) of ([\d,]+)", claim)
        if share and int(share.group(2).replace(",", "")) != held:
            findings.append(
                f"docs/LICENSING.md: the notice for {name} states {share.group(2)} lines, "
                f"while `git show {rev}` measures {held}"
            )
        if "unchanged" in claim and count < held:
            findings.append(
                f'docs/LICENSING.md: the notice for {name} states "the upstream, unchanged", '
                f"while the file held {held} lines at {rev} and {count} upstream lines"
            )
    notices = len([p for p in SRC.glob("*.py") if "Copyright (c)" in p.read_text(encoding="utf-8")])
    holders = re.search(r"(\d+) of the (\d+) modules carry a notice", text)
    if holders and (int(holders.group(1)) != notices or int(holders.group(2)) != len(list(SRC.glob("*.py")))):
        findings.append(
            f"docs/LICENSING.md: the notice table states {holders.group(1)} of {holders.group(2)} "
            f"modules, `src/` holds {len(list(SRC.glob('*.py')))} modules and {notices} notices"
        )


def check_wording() -> None:
    """Check 4: the rules the test set held before it stopped reading document prose."""
    architecture = (DOCS / "ARCHITECTURE.md").read_text(encoding="utf-8")
    shape = "  - <scope>  <position>  <identity>  <fact>"
    if architecture.count(shape) != 1:
        findings.append(
            f"docs/ARCHITECTURE.md §3.2: the console line shape is stated {architecture.count(shape)} times, not once"
        )
    if "container_coverage.console_line" not in architecture:
        findings.append("docs/ARCHITECTURE.md §3.2: the shape must name the function that holds it")
    if "The console prints the gap lines only" in architecture or "The console prints no shadow line" in architecture:
        findings.append("docs/ARCHITECTURE.md §3.2: the document still states a shape the function contradicts")
    section_3_1 = architecture.split("### 3.1")[1].split("### 3.2")[0]
    if "container_coverage.CONTAINER_TABLE" not in section_3_1:
        findings.append("docs/ARCHITECTURE.md §3.1: the document must point at the table, not restate it")
    if "§4" not in (DOCS / "API_CONVERSION_PATH.md").read_text(encoding="utf-8"):
        findings.append("docs/API_CONVERSION_PATH.md: the live facts stay blocked in §4")

    # §1.1 owns the layout rule, so it states who names the test set, and `tests/` keeps no index of its own.
    layout = architecture.split("### 1.1")[1].split("\n\n")[1]
    if "test set is named by the root index" not in layout:
        findings.append("docs/ARCHITECTURE.md §1.1: the section must state that the root index names the test set")
    if (TESTS / "README.md").is_file():
        findings.append("tests/ holds an index, which §1.1 says it does not")

    # One name per row shape: the module states it, and the §1 rule column names it for that module.
    table = architecture.split("## 1. Modules")[1].split("### 1.1")[0]
    for path, row_name, shape_name in SHAPES:
        module = ROOT / path
        defined = {
            target.id
            for node in ast.walk(ast.parse(module.read_text(encoding="utf-8")))
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        if shape_name not in defined:
            findings.append(f"{path}: the module does not define {shape_name}")
        row = [line for line in table.splitlines() if line.startswith(f"| `{row_name}` |")]
        if not row:
            findings.append(f"docs/ARCHITECTURE.md §1: no row for {row_name}")
        elif shape_name not in row[0]:
            findings.append(f"docs/ARCHITECTURE.md §1: the rule column for {row_name} does not name {shape_name}")


def check_no_test_counts() -> None:
    """Check 5: no document states a test count; the count lives in `agent-status.md` and the git history."""
    for md in COUNT_MARKDOWN:
        for lineno, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if COUNT_RE.search(line):
                findings.append(f"{md.relative_to(ROOT)}:{lineno}: a document states a test count")


def check_test_set_names_each_entry_once() -> None:
    """Check 6: `README.md` §Testing names each entry once, the rule that section states.

    The index rule is that the root index names every test module, and `tests/test_layout.py` pins it as names.
    A pin holds a name being present, not a name appearing twice, so the once rule cannot be a pin and lives
    here. The section is a list of names, so this reads the name at the start of each entry and no prose: a
    repeated name is a finding, and a section that dropped the rule it states is a finding too.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    if "## Testing" not in text:
        findings.append("README.md: the section that names the test set is not in the document")
        return
    section = text.split("## Testing", 1)[1].split("\n## ", 1)[0]
    if "named once" not in section:
        findings.append("README.md §Testing: the section must state that each module is named once")
    counts: dict[str, int] = {}
    for line in section.splitlines():
        match = ENTRY_RE.match(line)
        if match:
            counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    for name, count in sorted(counts.items()):
        if count > 1:
            findings.append(
                f"README.md §Testing: {name} is named {count} times, which contradicts the rule the section states"
            )


def main() -> int:
    check_claims()
    check_matrix_table()
    check_licensing()
    check_wording()
    check_no_test_counts()
    check_test_set_names_each_entry_once()

    for finding in findings:
        print(f"FINDING: {finding}")
    if findings:
        print(f"{len(findings)} finding. No document was changed by this script.")
        return 1
    print("Every document agrees with measurement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
