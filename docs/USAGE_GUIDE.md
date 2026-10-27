# Usage Guide

This is the technical reference for the two scripts. It states how to run them
and what each output file holds. The rules behind the output are in
[ARCHITECTURE.md](ARCHITECTURE.md); the document index is in
[README.md](README.md).

## What the tool does

The converter reads a Panorama XML configuration export and writes Terraform
configuration for the `PaloAltoNetworks/panos` provider v2 (pinned
`~> 2.0.14`). It also writes reports for configuration that has no v2
resource, so nothing is dropped silently.

The tool is a local file converter. By default it connects to no server, runs no
command, and needs no credentials. Reading from the Panorama API is an explicit
choice (`--source api`), and a run that reads only the cache (`--offline`) needs no
key and connects to no server.

## Requirements

- Python 3.9 or later. Standard library only.
- Terraform 1.0 or later, only for the optional `--validate` check.
- A Panorama XML export.

No installation step. Run the script from the repository. The API source needs no
package: it uses `urllib`, so the https rules below are the tool's own.

## Running the converter

```bash
python3 panorama_to_terraform.py export.xml --output-dir out
```

| Argument | Meaning |
|---|---|
| `input_file` | Panorama XML export. Optional with `--source api` |
| `--source file\|api` | Where the input comes from. Default `file` |
| `--host HOST` | Panorama host for `--source api`. Required with `--source api` |
| `--cache-dir DIR` | Where fetched responses are kept. Default `panorama_cache` |
| `--offline` | Read the cache only: no request, no key |
| `--insecure` | Skip certificate verification. Explicit choice, api source only |
| `--output-dir DIR` | Output directory. Default `terraform_output` |
| `--max-input-bytes N` | Refuse an input larger than N. Default 67,108,864 (64 MiB) |
| `--validate` | Add the `terraform init` + `terraform validate` check to the post-run gate |

The input check runs before the read allocates and before any file is written.
The tool refuses a DTD, which is the only path an entity expansion or an
external entity takes, and a Panorama export carries none. A refusal names the
file, the limit and the measured size, exits non-zero, and writes nothing.
Raise the size limit only for a trusted file. A fetched response runs the same
checks through the same boundary, and a refusal is written to no cache entry.

### Reading from the API

```bash
export PANOS_API_KEY=...
python3 panorama_to_terraform.py --source api --host panorama --output-dir out
python3 panorama_to_terraform.py --source api --host panorama --offline --output-dir out
```

- The key is read from `PANOS_API_KEY`. It is never taken from a command line, so it
  does not appear in a shell history or in a process list, and it never appears in an
  output file or in a cache entry name.
- The request is https only. A redirect that changes the scheme is refused, because
  following it would send the key over a plain connection.
- Each response is stored in `--cache-dir` under the SHA-256 hex of the host and the
  sorted request parameters. The same request finds the same entry, so a repeat run reads
  the cache and sends no request. `--offline` reads the cache only and refuses an entry
  that is not there.
- A stored response is the bytes the parser read, so the report lines name the lines of
  that file. The report names the cache entry as the input.
- An API response is an envelope (`response/result/config`). The converter reads the
  `config` element inside it, so the conversion is the same as for an export file.

## Quick start script

`quick_start.sh` runs the converter on the committed sample export
(`sample_panorama_config.xml`) and prints the next steps. It is a demonstration,
not part of the converter. It adds `--validate` when the terraform binary is
present, so the gate runs the terraform check when it can.

## Running the splitter

The splitter is optional pre-processing. It writes one XML file per device
group.

```bash
python3 split_device_groups.py export.xml --output-dir split_output
```

| Argument | Meaning |
|---|---|
| `input_file` | Panorama XML export |
| `--output-dir DIR`, `-o DIR` | Output directory. Default `split_configs` inside the input file's directory |
| `--max-input-bytes N` | The same input check as the converter |

How the splitter joins a device group to a template is in
[DEVICE_GROUP_SPLITTING.md](DEVICE_GROUP_SPLITTING.md). The splitter writes XML,
so it has no `.tf` output and no gate run.

## Output files

The converter writes a file only when it has content.

| File | Content |
|---|---|
| `provider.tf` | Provider block, wired to the three credential variables |
| `variables.tf` | `panos_hostname`, `panos_username`, `panos_password` |
| `address_objects.tf`, `address_groups.tf`, `service_objects.tf`, `service_groups.tf`, `tags.tf`, `custom_url_categories.tf`, `application_groups.tf`, `external_lists.tf` | Object resources |
| `security_rules.tf`, `nat_rules.tf`, `decryption_rules.tf`, `pbf_rules.tf` | Policy rules, one resource per rule, chained in XML order |
| `security_profile_groups.tf` | Profile group resources |
| `security_profiles.tf` | Inventory only: names and descriptions, with the resource name the emitter would use |
| `interfaces.tf`, `zones.tf`, `virtual_routers.tf`, `monitor_profiles.tf`, `vpn.tf` | Network and VPN resources |
| `README.md` | Deployment steps for the generated directory |
| `MANUAL_SETUP_REPORT.txt` | Report-only configuration, plus a section for a container no parse method reads |
| `INTERFACE_MIGRATION_REPORT.txt` | Interface and IP inventory |
| `VPN_MIGRATION_REPORT.txt` | VPN inventory and the pre-shared key actions |
| `CONVERSION_REPORT.txt` | One line per entry the parse read |
| `SANITY_REPORT.txt` | The post-run gate result |

The interface report, the VPN report, and the conversion report share one grouping
rule: one section per scope the export declares (device group, then the template or
the device), and the shared section is named `Shared`. The rule is in
[ARCHITECTURE.md](ARCHITECTURE.md) §4.5. The manual report is organised by object
kind instead, so it does not name the scope on each line; that is recorded in
[`../backlog.md`](../backlog.md).

`SANITY_REPORT.txt` is written on every run, by the gate, not only when it has a
finding. The other reports are written only when they have content.

## Post-run sanity gate

Every conversion runs the gate on the files it wrote, prints a summary, and
writes `SANITY_REPORT.txt`. The gate reads the files, so it reports what you
receive, not what the generator intended.

| Check | Rule | Severity |
|---|---|---|
| `emitted_types` | every resource type is in `EMITTED_TYPES` | FAIL |
| `location_present` | every resource block carries `location` | FAIL |
| `references` | every `.name` reference resolves to a resource declared in the same run | FAIL |
| `variables` | every declared variable has a `var.` consumer | FAIL |
| `control_chars` | no raw control character or DEL in a `.tf` file | FAIL |
| `placeholders` | an expected placeholder (the VPN key `***CHANGE_ME***`) is listed | WARN |
| `terraform` | `terraform init` + `terraform validate`, with `--validate` | FAIL, or SKIPPED when the binary is absent |

A WARN does not fail the run. A FAIL finding exits 1. A SKIPPED check never
changes the exit code. The rules live in `sanity_checks.py` and are stated in
[ARCHITECTURE.md](ARCHITECTURE.md) §4.6.

Exit codes: 0 when the gate reports no FAIL finding, 1 when a check fails or
the input is refused. A coverage gap or an unaccounted entry is an operator
action, so it does not change the exit code.

## Reading the generated Terraform

Three things explain the shape of the output:

- **Naming.** A local resource name is the sanitized PAN-OS name plus an 8-hex
  digest of the source identity, so the same name in two device groups, virtual
  systems, templates or firewalls is two resources. The rule is in
  [ARCHITECTURE.md](ARCHITECTURE.md) §5.
- **Location.** Each resource carries the `location` block the source scope
  states, in the shape the provider declares for that type. The branch order is
  in [ARCHITECTURE.md](ARCHITECTURE.md) §4.2.
- **References.** A name the same run declares is emitted as a `.name`
  reference, so apply order follows the dependency. A name outside the export
  stays a plain string. The resolution order is in
  [ARCHITECTURE.md](ARCHITECTURE.md) §4.3.

## Deploying the generated configuration

1. Create `terraform.tfvars` with the credentials. Do not commit it.
2. Replace the placeholder VPN pre-shared keys.
3. Read `MANUAL_SETUP_REPORT.txt` and configure those items by hand.
4. Check interface names against the target platform
   (`INTERFACE_MIGRATION_REPORT.txt`).
5. `terraform init`, then `terraform plan`, then `terraform apply`. Review the
   plan before you apply it.

## Troubleshooting

| Symptom | Cause and action |
|---|---|
| `ParseError: not well-formed` | The export is truncated or invalid. Export again from Panorama. |
| `Error: ... larger than the limit` | The input exceeds `--max-input-bytes`. Raise the limit only for a trusted file. |
| `Refused: input declares a DTD` | The file is not a Panorama export. Do not disable the check; obtain the export again. |
| Gate FAIL on `references` | A `.name` reference points at a resource this run did not declare. Read `SANITY_REPORT.txt`; the converter never declares a resource to make a reference work. |
| Gate FAIL on `variables` | A declared variable has no `var.` consumer. Only the three credential variables are declared. |
| Gate WARN on `placeholders` | Expected. A VPN pre-shared key is a placeholder, and you must set it before apply. |
| Duplicate local resource names | A true duplicate of the same identity. The generator adds a numeric suffix so the output stays valid HCL. Two different identities never need it. |
| `terraform validate` reports an unknown `location` sub-block | The gate checks presence only, not shape. Read `LOCATION_SCHEMA` in `resource_mapping.py`; `terraform validate` accepts an unknown sub-block and drops it silently. |
| Apply fails with "not found" | The referenced object exists in another tenant, so the converter left the name as a plain string. Create it, or point the provider at the right device group. |
| Splitter prints "No device groups found" | The export came from a firewall, not Panorama. Run the converter on it directly. |
| Splitter copies no template | No device appears in both the device group and the template. The splitter prints the fact. Fix the export, or copy the template section by hand. |

## Extending the converter

Add a type in this order, so the tests cannot drift:

1. Add the type to `EMITTED_TYPES` in `resource_mapping.py`, and to
   `LOCATION_SCHEMA` with the sub-blocks the provider schema declares.
2. Add a `COVERAGE_MATRIX` row with the XML element, the fixture entry, the
   expected emitted name, the fixture, and the output file.
3. Add the parse method, and mark each entry it reads. Add the container-table
   row in `container_coverage.py`.
4. Add the generator method.
5. Add or extend a fixture, and the row test. Run `python3 -m pytest` and
   `ruff check .`.

An emitter change that skips step 2 fails `tests/test_coverage_matrix.py`. A
parse method that reads entries without marking them fails
`tests/test_entry_coverage.py`.

## Limitations

The limits are recorded in [`../backlog.md`](../backlog.md) and in
[RESOURCE_MAPPING.md](RESOURCE_MAPPING.md). The main ones:

- BGP, OSPF, application filters, application override rules, QoS profiles, and
  IPsec tunnel monitor profiles have no v2 resource.
- Security profile bodies, log forwarding profiles, and schedules are captured
  only as name and description, so they are reported, not emitted.
- Address types with no `panos_address` attribute (country, region, continent,
  container, external) are reported.
- A service that defines both tcp and udp emits one leg, because the provider
  accepts one.
- Rulebase (pre, post, shared) is not recorded, so a device group with both
  pre- and post-rules chains across them.
- `location.template_stack` is never emitted, and a template that targets two
  devices keeps interface names as strings.

## License

The project is dual-licensed: AGPL v3 for open source use, and a commercial
license for proprietary use. The terms are in
[DUAL-LICENSING-EXPLAINED.md](DUAL-LICENSING-EXPLAINED.md), and the license
texts are `LICENSE-AGPL` and `LICENSE-COMMERCIAL`.

## Additional resources

- [Palo Alto Terraform provider](https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs)
- [PAN-OS API documentation](https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-panorama-api/get-started-with-panorama-api)
- Testing and linting: `python3 -m pytest`, `ruff check .`
