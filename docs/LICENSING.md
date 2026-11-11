# Licensing

This document is the owner of the license rule. The license texts are the authority:
[`../LICENSE-AGPL`](../LICENSE-AGPL) and [`../LICENSE-COMMERCIAL`](../LICENSE-COMMERCIAL). This document
states who holds what and what each grant covers. It is not legal advice. Lawyer review is recorded in
[`../backlog.md`](../backlog.md).

## The rule

The work as a whole is AGPL v3. Two holders hold it:

- The upstream author holds the lines they wrote that are still in the tree.
- Ryan Brown holds every other line.

Our contributions are licensed under AGPL v3 only. This project grants no commercial terms for them.

## The source

This repository is a fork of
[gswsystems/Panorama2Terraform](https://github.com/gswsystems/Panorama2Terraform), taken at v4.0.2
(commit `92cb2a3`, 2025-12-09), and published as
[thatbuzzguy/Panorama2Terraform](https://github.com/thatbuzzguy/Panorama2Terraform). Both license files came
from the upstream unchanged, so they are the upstream author's texts. The dual-license history is inherited
with them.

## The split, measured

Measured 2026-11-11 through `git blame` on the committed tree, counted by author:

| Measure | Upstream (`devnullNZ`) | Ours (`Ryan Brown`) |
|---|---|---|
| Tracked lines, whole tree | 2,172 (3.7%) | 57,157 |
| Tracked lines in `src/`, `tests/`, `tools/` | 588 (1.2%) | 50,008 |
| Commits | 9 | 121 |

The rewrite is the reason this project asserts its own copyright for its contributions. `git blame` is the
authority for the split, so the inherited set is measured and not decided: a file is in the set while it holds
at least one line the upstream wrote, and it leaves the set when its last upstream line is replaced.

## The inherited set

Measured 2026-11-11. Each file in this set still holds upstream text, so its notice stays the upstream's.

| File | Upstream lines |
|---|---|
| `LICENSE-AGPL` | 594 |
| `src/panorama_to_terraform.py` | 431 |
| `LICENSE-COMMERCIAL` | 241 |
| `examples/sample_panorama_config.xml` | 228 |
| `src/split_device_groups.py` | 130 |
| `docs/VPN_ROUTING_CONFIG_EXAMPLES.md` | 127 |
| `examples/example_interface_report.txt` | 73 |
| `docs/MIGRATION_GUIDE.md` | 63 |
| `docs/DEVICE_GROUP_SPLITTING.md` | 48 |
| `.gitignore` | 39 |
| `README.md` | 38 |
| `docs/USAGE_GUIDE.md` | 29 |
| `tools/quick_start.sh` | 27 |
| `.github/ISSUE_TEMPLATE.md` | 26 |
| `.github/workflows/python-tests.yml` | 21 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 21 |
| `docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md` | 16 |
| `examples/example_terraform_output.txt` | 4 |

`docs/DUAL-LICENSING-EXPLAINED.md` held 16 upstream lines. This document replaces it, and no upstream line
carries into this document, so the set is 18 files and 2,156 upstream lines after the removal.

## The copyright notices in `src/`

Four of the 22 modules carry a notice, and each notice names the holder for the lines that module holds:

| Module | Upstream lines | Notice |
|---|---|---|
| `src/panorama_to_terraform.py` | 431 | The upstream, unchanged |
| `src/split_device_groups.py` | 130 | The upstream, unchanged |
| `src/source_fetch.py` | 0 | Ryan Brown, 2026. States no commercial term. |
| `src/xml_input.py` | 0 | Ryan Brown, 2026. States no commercial term. |

The other 18 modules carry no notice. This document is the authority for them, and no header is added: a
notice that names one holder for a file the two holders share is a claim the split does not support. The
choice to keep the notice set unpinned is recorded in [`../backlog.md`](../backlog.md).

## The commercial option

`LICENSE-COMMERCIAL` is the upstream author's grant, so it covers the upstream parts only. Only the upstream
author can grant it, and only for the lines they wrote.

A user cannot get the whole work under commercial terms from this project, because the whole work needs a
grant for both parts. For our contributions there is one option: AGPL v3.

## AGPL v3, and the word "non-commercial"

AGPL v3 permits commercial use. Its condition is the copyleft rule, and for a derivative work that means:

- keep the copyright notices, including the upstream's;
- include the license text;
- document the changes you made;
- provide the source to anyone who receives the software, and to anyone who uses it over a network (AGPL
  §13, the network copyleft rule);
- license your modifications under AGPL v3.

AGPL §10 does not allow an extra non-commercial condition on a derivative work, so the choice for our
contributions is stated as "AGPL v3 only, with no commercial alternative from this project" and not as a
non-commercial license.
