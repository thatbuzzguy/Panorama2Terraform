# Acceptance Criteria — F1.1 Tooling Baseline

Task: add pytest and ruff to the project gate. Lint and tests must run in pre-commit and CI.

## Done When

1. `requirements.txt` lists `pytest` and `ruff`. The version pins allow the installed releases.
2. A ruff config file exists. It lints both `panorama_to_terraform.py` and `split_device_groups.py`.
3. `ruff check .` passes with zero errors on the repository.
4. A `tests/` directory exists. It contains at least one smoke test per script.
   - The converter smoke test runs `panorama_to_terraform.py` on the committed sample config.
     It asserts that the expected output files exist.
   - The splitter smoke test runs `split_device_groups.py --help`. It asserts exit code 0.
5. `pytest` passes with zero failures.
6. The CI workflow installs `requirements.txt`, runs ruff, then runs pytest.
   The workflow no longer installs the unused packages `python-docx`, `python-pptx`, `openpyxl`.
7. A `.pre-commit-config.yaml` runs ruff on Python files.
8. All of the above commands also pass on local Python 3.12.

## Out of Scope for This Task

- Parser unit tests (F1.2)
- Golden-file generator tests (F1.3)
- Provider schema conformance (F1.4)
- Terraform validate gate (F1.5)
