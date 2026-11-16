"""The index rule (`docs/ARCHITECTURE.md` §1.1), pinned in one place.

The pin reads names, not wording. An index is a list of names, so a pin can hold it: each index names every
markdown document under it, the root index names the test set and the response set, and every `src/` module is
named in the §1 module table. What a document says about a rule is wording, and a wording edit is a document
review, not a code failure, so the wording checks live in `tools/check_documents.py`, which the test set does
not read.

`tests/` has no index of its own: the root index names the test set, and §1.1 states that rule. Two `.github/`
template files sit outside every index, which `backlog.md` records as its own finding, so this pin reads only
the four index scopes. No pin reads `backlog.md`, and no pin reads `AGENTS.md`.
"""

from conftest import REPO_ROOT, SRC_DIR, TESTS_DIR

# The four readme indexes `AGENTS.md` states, each with the directory its index covers. The root index is the
# index for the root set, which holds the tracking markdown and the test set.
INDEXES = (
    (REPO_ROOT / 'README.md', REPO_ROOT),
    (REPO_ROOT / 'docs' / 'README.md', REPO_ROOT / 'docs'),
    (REPO_ROOT / 'examples' / 'README.md', REPO_ROOT / 'examples'),
    (REPO_ROOT / 'tools' / 'README.md', REPO_ROOT / 'tools'),
)


def test_the_indexes_name_every_document_under_them():
    """AC-1 to AC-3 of `docs/ARCHITECTURE.md` §1.1: each index names every markdown document under it, the
    root index names the test set and the response set, and the §1 module table names every `src/` module.
    Each half reads a name, so a correct rewording of a document cannot fail this pin.
    """
    root = (REPO_ROOT / 'README.md').read_text(encoding='utf-8')

    # AC-1: each index names every markdown document under it, and the root index names each index.
    for index, directory in INDEXES:
        text = index.read_text(encoding='utf-8')
        assert index.name in root, (index.name, 'the root index names each index')
        for path in sorted(directory.glob('*.md')):
            if path.name != index.name:
                assert path.name in text, (index.name, path.name, 'a document under an index must be named')

    # AC-2: the root index names the test set, so `tests/` keeps no index of its own, and it names the
    # response set too, because a committed response is not corpus material (§1.1).
    modules = sorted(path.name for path in TESTS_DIR.glob('test_*.py'))
    assert len(modules) > 1, modules
    for name in modules:
        assert f'tests/{name}' in root, (name, 'the root index names the test set')
    assert 'tests/conftest.py' in root, 'the root index names the shared harness'

    # AC-3: one file per accepted request shape, each named by the identity that produced it.
    responses = sorted(path.name for path in (TESTS_DIR / 'responses').glob('*.xml'))
    assert len(responses) == 3, responses
    for name in responses:
        assert f'tests/responses/{name}' in root, (name, 'the root index names the response set')

    # AC-4: every module in `src/` is named in the §1 module table.
    table = (REPO_ROOT / 'docs' / 'ARCHITECTURE.md').read_text(encoding='utf-8')
    table = table.split('## 1. Modules')[1].split('### 1.1')[0]
    for path in sorted(SRC_DIR.glob('*.py')):
        assert f'| `{path.name}` |' in table, (path.name, 'the module table names every src module')
