"""The index rule (`docs/ARCHITECTURE.md` §1.1), pinned in one place.

The pin reads names, not wording. An index is a list of names, so a pin can hold it: each index names every
markdown document under it, a directory with no index of its own is named by the root index, the root index names
the test set and the two test material sets (the response set and the tflint set), and every `src/` module is named
in the §1 module table. What a document says about a rule is wording, and a wording edit is a document review, not
a code failure, so the wording checks live in `tools/check_documents.py`, which the test set does not read.

`tests/` has no index of its own: the root index names the test set, and §1.1 states that rule. So does
`.github/`, which holds the two contribution templates, so the root index names them. The pin reads the name of
every markdown file in the tree, so `backlog.md` and `AGENTS.md` are read for a name, not for wording. A count is
not a name, so the response-set count is not read here; it is held by `tests/test_api_requests.py`, which reads
the requests the files answer.
"""

from conftest import REPO_ROOT, SRC_DIR, TESTS_DIR

# The four readme indexes `AGENTS.md` states, each with the directory its index covers. The root index is the
# index for the root set, which holds the tracking markdown and the test set.
INDEXES = (
    (REPO_ROOT / "README.md", REPO_ROOT),
    (REPO_ROOT / "docs" / "README.md", REPO_ROOT / "docs"),
    (REPO_ROOT / "examples" / "README.md", REPO_ROOT / "examples"),
    (REPO_ROOT / "tools" / "README.md", REPO_ROOT / "tools"),
)


def test_the_indexes_name_every_document_under_them():
    """AC-1 to AC-4 of `docs/ARCHITECTURE.md` §1.1: each index names every markdown document under it, a
    directory with no index of its own is named by the root index, the root index names the test set and the
    response set, and the §1 module table names every `src/` module. Each half reads a name, so a correct
    rewording of a document cannot fail this pin.
    """
    root_index = REPO_ROOT / "README.md"
    root_text = root_index.read_text(encoding="utf-8")

    # AC-1 and AC-2: the owner of a document is the index of the directory it sits in, or the root index when the
    # directory holds no index of its own. The set read is every markdown file in the tree, so a directory such as
    # `.github/` and the tracking markdown are covered by the rule rather than by an exception.
    for index, _directory in INDEXES:
        assert index.name in root_text, (index.name, "the root index names each index")

    owners = {directory: index for index, directory in INDEXES}
    for path in sorted(REPO_ROOT.rglob("*.md")):
        index = owners.get(path.parent, root_index)
        if path.name == index.name:
            continue
        text = root_text if index == root_index else index.read_text(encoding="utf-8")
        assert path.name in text, (index.name, path.name, "the index that owns the directory names the document")

    # AC-3: the root index names the test set, so `tests/` keeps no index of its own, and it names the two test
    # material sets too, because neither is corpus material (§1.1). Names only: the response-set count is
    # held by `tests/test_api_requests.py`, which reads the requests the files answer.
    modules = sorted(path.name for path in TESTS_DIR.glob("test_*.py"))
    assert len(modules) > 1, modules
    for name in modules:
        assert f"tests/{name}" in root_text, (name, "the root index names the test set")
    assert "tests/conftest.py" in root_text, "the root index names the shared harness"

    for name in ("responses", "tflint"):
        for path in sorted(p for p in (TESTS_DIR / name).iterdir() if p.is_file()):
            assert f"tests/{name}/{path.name}" in root_text, (
                name,
                path.name,
                "the root index names the test material set",
            )

    # AC-4: every module in `src/` is named in the §1 module table.
    table = (REPO_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    table = table.split("## 1. Modules")[1].split("### 1.1")[0]
    for path in sorted(SRC_DIR.glob("*.py")):
        assert f"| `{path.name}` |" in table, (path.name, "the module table names every src module")

    # AC-4: every module in `src/` is named in the §1 module table.
    table = (REPO_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    table = table.split("## 1. Modules")[1].split("### 1.1")[0]
    for path in sorted(SRC_DIR.glob("*.py")):
        assert f"| `{path.name}` |" in table, (path.name, "the module table names every src module")
