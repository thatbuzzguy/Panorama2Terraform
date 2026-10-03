# To-Do — Epic 1: Testing and Linting Foundation

Goal 1: CI passes offline. Every emitted resource type and argument is verified against the provider schema.

## Tasks

- [x] **F1.1 Tooling baseline** — pytest + ruff in `requirements.txt`, pre-commit config, CI runs lint and tests, smoke tests for both scripts. (COMPLETED)
- [x] **F1.2 Parser unit tests** — one test per parse method, isolated XML snippet fixtures. (COMPLETED — found and fixed 5 parser bugs: VR/LR template path, vsys-level VR path, IPsec gateway tag, aggregate IP leak, vlan/loopback/tunnel name collision)
- [x] **F1.3 Generator golden-file tests** — generate from a fixture, diff against committed expected output. (COMPLETED — 39 tests, 2 golden sets: sample + kitchen-sink)
- [x] **F1.4 Provider schema conformance test** — assert every emitted resource type exists in `terraform providers schema -json`; assert required arguments are present. (COMPLETED — 56 cases; 43 xfailed with Epic 2 references, 13 xpassed)
- [x] **F1.5 CI Terraform gate** — `terraform init -backend=false` + `terraform validate` on generated sample output. (COMPLETED — init green; validate xfail until Epic 2)
- [ ] **F1.6 Fixture corpus** — edge-case configs: quoted DG names, duplicate names across DGs, multi-vsys, mixed VR/LR, IPv6, multi-port services.
- [ ] **F1.7 Security and robustness tests** — hostile XML (entity expansion), DTD rejection, control-character escaping, empty and colliding names.
- [x] **F1.8 Lint both scripts** — `split_device_groups.py` under the same ruff gate as `panorama_to_terraform.py`. (COMPLETED with F1.1)

## Notes

- F1.1 and F1.8 overlap: F1.1 sets up the gate, F1.8 makes sure the splitter passes it.
- The smoke test in F1.1 is temporary scaffolding. F1.2–F1.4 replace and extend it.
