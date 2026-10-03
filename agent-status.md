# Agent Status

## Current position
Epic 1 (testing and lint foundation), F1.6 completed. Next: F1.7 security and robustness tests.

## Session log

### F1.6 — Fixture corpus for edge cases (this session)
- Added six edge fixtures under tests/fixtures/: edge_quoted_dg_names,
  edge_dup_names_across_dgs, edge_multi_vsys, edge_mixed_vr_lr,
  edge_ipv6, edge_multi_port_services.
- Added tests/test_edge_cases.py (12 tests; 10 pass, 2 xfail):
  - quoted DG names: splitter now matches attributes in Python instead of
    f-string XPath (single-quote names used to raise
    `SyntaxError: invalid predicate`). Fixed split_device_groups.py in
    both the device-group and template lookups.
  - duplicate names across DGs: pinned current last-wins behavior (green)
    and xfail the desired per-DG survival (Epic 3 F3.1).
  - multi-vsys: both vsys objects parse (green).
  - mixed VR/LR: VR in template + LR in vsys both parse; routes keep
    next-vip vs next-vr attribution (green).
  - IPv6: IPv4 parses (green); IPv6 value retention xfail (Epic 2 F2.4).
  - multi-port/dual services: port list passes through; dual tcp/udp
    keeps tcp only (green pin; udp drop added to backlog).
- Gate: ruff clean. pytest 96 passed, 46 xfailed, 13 xpassed.

### F1.5 — CI Terraform gate (this session)
- Added tests/test_terraform_validate.py. It generates the sample output
  with the converter CLI, then runs `terraform init -backend=false` (must
  pass today) and `terraform validate` (xfail until Epic 2 F2.2/F2.3/F2.4
  rewrite the generator: v1 types unsupported, missing location).
- The test skips when the terraform binary is absent, so the Python matrix
  jobs are unaffected.
- Added a terraform-gate CI job to .github/workflows/python-tests.yml.
  It installs terraform 1.16.1 (hashicorp/setup-terraform@v3) and runs the
  validate test. It needs the lint-and-test job.
- Gate: ruff clean. pytest 86 passed, 44 xfailed, 13 xpassed.

### F1.4 — Provider schema conformance (this session)
- Added tests/test_schema_conformance.py. It reads the panos provider
  source and version from the golden provider.tf, runs
  `terraform init -backend=false` + `terraform providers schema -json`,
  and checks the committed golden output against the schema:
  - every emitted resource type must exist in the provider;
  - every required attribute of an existing type (e.g. location) must
    be present in every generated block.
- Red→green: 13 of 28 emitted types are not in provider v2 and no
  generated block carries the required `location` attribute. All 43
  failing cases are xfail-marked with Epic 2 task references (F2.2
  resource mapping, F2.3 location). 13 cases xpass.
- Confirmed against the live v2 schema: the 13 missing types match the
  F2.2 mapping list (panos_address_object, panos_application_filter,
  panos_bgp*, panos_external_list, panos_ipsec_tunnel_proxy_id_ipv4,
  panos_layer2_subinterface, panos_nat_rule_group, panos_ospf*,
  panos_security_rule_group, panos_service_object, panos_static_route_ipv4).
- Gate: ruff clean. pytest: 85 passed, 43 xfailed, 13 xpassed.

### F1.3 — Generator golden-file tests (this session)
- Built `tests/fixtures/kitchen_sink.xml` (761 lines): a merge of all per-method
  fixtures into one config that exercises every generator path the sample
  never reaches (VRs, LRs, VPN, BGP, OSPF, profiles, schedules, PBF, ...).
  Merge tool: `tools/build_kitchen_sink.py` (rerun when new fixtures land).
- Committed golden output sets under `tests/golden/`:
  - `sample/` — 8 .tf files from the sample config.
  - `kitchen_sink/` — 29 .tf files, every generator path exercised.
- `tests/test_golden_files.py`: 39 tests (2 file-set + 37 byte-exact).
  The converter runs once per case via a session fixture.
- Goldens pin the current v1-style output (e.g. `panos_virtual_router` with
  an `interfaces` list, `panos_ike_crypto_profile`). The Epic 2 provider-v2
  rewrite will update them deliberately; the diff is the review surface.
- Gate: ruff clean; pytest 85 passed (46 parser/smoke + 39 golden).

### F1.2 — Parser unit tests (this session)
- Wrote 46 unit tests across 6 modules under `tests/` (one test per parse method,
  34 isolated XML fixtures in `tests/fixtures/` using the real Panorama structure).
- Tests found 5 real parser bugs; all fixed and pinned by tests:
  1. `parse_virtual_routers`/`parse_logical_routers` searched `.//template/entry`
     but Panorama exports use `<templates><entry>` — template VRs/LRs were silently
     dropped. The README "Multi-VR support (tested)" claim was not supported because
     the sample config contains no virtual routers.
  2. Device-level VR/LR path missed the real location
     `devices/entry/vsys/entry/network/virtual-router/entry`.
  3. `parse_ipsec_tunnels` looked for `auto-key/ike-gateway/entry`; real exports use
     `auto-key/gateway/entry`. Now accepts both.
  4. Aggregate parent interface collected subinterface IPs (`.//ip/entry` descended
     into `<units>`). Now direct-child lookup only.
  5. vlan/loopback/tunnel dedup keyed on the raw unit number, so `loopback.1`
     silently dropped `tunnel.1` (both unit number 1 — a common real-world case).
     Now deduped on the namespaced name.
- Parser extraction gaps (silent data loss) recorded in `backlog.md` for Epic 2/3:
  app-filter description, service-object tags, schedule description, security-rule
  profile refs, NAT service member-list form, dynamic address-group filter content.
- Sample config output re-verified end-to-end (converter runs clean, all 8 files).
  Baseline snapshot saved at `/tmp/tf_baseline` (not committed).
- Gate: `ruff check .` clean; `pytest` 50 passed (46 parser + 4 smoke).

## Environment notes
- Python 3.12.3; use `uvx --with pytest==9.1.1 pytest` and
  `uvx --with ruff==0.16.10 ruff` (PEP 668 blocks system pip installs).
- terraform 1.16.1 available at /usr/bin/terraform.
- Converter CLI: `python3 panorama_to_terraform.py <input.xml> [--output-dir DIR]`
  (output dir is a flag, default `terraform_output`).
- The sample config has no templates/vsys network config, so VR/LR/BGP/OSPF/IPsec
  paths were never exercised by the sample-based smoke test.

## Conventions
- One task at a time; `acceptance.md` overwritten before each task.
- ASD-STE100 in commits and docs.
- Commit per feature; remove completed items from markdown only when the epic
  completes (completed items are marked (COMPLETED) until then).
