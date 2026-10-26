# Migration Guide

This guide is the operator workflow: export, convert, read the reports, adjust,
validate, apply. It covers one device group and the multi-virtual-router case,
where several device groups land on one target firewall.

The rules that explain the output are not restated here. They are in
[ARCHITECTURE.md](ARCHITECTURE.md), and the document index is in
[README.md](README.md).

## What the converter produces

Real Terraform resources for:

- Address objects and groups, service objects and groups, tags, application
  groups, custom URL categories, external dynamic lists
- Security, NAT, decryption and policy-based forwarding rules, one resource per
  rule, in XML order
- Security profile groups
- Zones, interfaces (physical, subinterface, VLAN, loopback, tunnel, aggregate),
  virtual routers, logical routers, static routes, PBF path monitoring profiles
- IKE and IPsec crypto profiles, IKE gateways, IPsec tunnels

Report-only, because the provider has no v2 resource or the body is not parsed:

- BGP, OSPF, application filters, application override rules, QoS profiles, IPsec
  tunnel monitor profiles
- Security profile bodies, log forwarding profiles, schedules
- Address types with no `panos_address` attribute, and the second protocol leg of
  a dual-protocol service

The full list and the reason are in [RESOURCE_MAPPING.md](RESOURCE_MAPPING.md).

## Workflow

### 1. Export the configuration

Choose one method.

- **Web UI:** Device → Setup → Operations → save a configuration snapshot, then
  extract the XML.
- **CLI:** `set cli config-output-format xml`, then `configure`, then `show`.
- **API:**
  `curl -k -X GET 'https://panorama/api/?type=export&category=configuration&key=KEY' -o config.xml`

Save the export. It is the reference for the migration, and the converter reads
it once.

### 2. Split by device group, when you need one run per device group

```bash
python3 split_device_groups.py panorama_export.xml
```

This is optional. The converter handles a full export and emits one rule chain
per device group. Split when you want one Terraform directory per device group,
or per HA pair. The join rule and the limits are in
[DEVICE_GROUP_SPLITTING.md](DEVICE_GROUP_SPLITTING.md).

### 3. Convert

```bash
python3 panorama_to_terraform.py source-config.xml --output-dir migration_configs --validate
```

`--validate` runs `terraform init` and `terraform validate` in the same run. The
gate always runs the static checks and writes `SANITY_REPORT.txt`.

### 4. Read the reports

| Report | What to take from it |
|---|---|
| `MANUAL_SETUP_REPORT.txt` | Every item you must configure by hand, with the reason |
| `INTERFACE_MIGRATION_REPORT.txt` | Interface and IP inventory, grouped by the scope the export declares |
| `VPN_MIGRATION_REPORT.txt` | VPN inventory, and the pre-shared key actions |
| `CONVERSION_REPORT.txt` | One line per entry the parse read, so you can see what became a resource, a report entry, or a gap |
| `SANITY_REPORT.txt` | The checks the output passed |

### 5. Adjust for the target platform

Interface names, IP addresses, and virtual router names are the usual changes.
Keep the `location` block as the converter wrote it: it names the device group,
template, or virtual system the export states.

### 6. Validate and apply

```bash
cd migration_configs
terraform init
terraform plan          # review every change
terraform apply
```

Before apply: replace the placeholder VPN pre-shared keys, confirm the
credential variables in `terraform.tfvars`, and finish the manual items from the
report.

## Interface mapping

Build a mapping table before you edit anything:

| Source interface | Source IP | Zone | Target interface | Target IP | Note |
|---|---|---|---|---|---|
| ethernet1/1 | 10.1.1.1/24 | Trust | ethernet1/1 | 10.1.1.1/24 | Direct |
| ethernet1/3 | 172.16.1.1/24 | DMZ | ethernet1/5 | 172.16.1.1/24 | Different port |
| vlan.10 | 192.168.10.1/24 | Mgmt | vlan.10 | 192.168.10.1/24 | Same VLAN |

In provider v2, the physical interface carries the mode, and the IPv4 address of
the untagged interface lives on the `.0` layer-3 subinterface. Real generated
output (`tests/golden/kitchen_sink/interfaces.tf`):

```hcl
resource "panos_ethernet_interface" "ethernet1_1_d74b05bd" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ethernet1/1"
  comment = "Trust uplink"
  layer3 = {
    interface_management_profile = "Management1"
  }
}

resource "panos_ethernet_layer3_subinterface" "ethernet1_1_0_279a35e7" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "ethernet1/1.0"
  parent = panos_ethernet_interface.ethernet1_1_d74b05bd.name
  tag = 0
  ip = [{ name = "192.168.10.1/24" }]
}
```

The local name is the sanitized PAN-OS name plus an 8-hex digest of the source
identity. Do not shorten it: the digest is what keeps two firewalls that both
declare `ethernet1/1` apart.

Zones carry membership under `network`:

```hcl
resource "panos_zone" "trust_c2dcfb60" {
  location = {
    vsys = {
      name = "vsys1"
    }
  }
  name = "trust"
  network = {
    layer3 = [ panos_ethernet_interface.ethernet1_1_d74b05bd.name ]
    zone_protection_profile = "ZPP-Default"
  }
}
```

A zone the export defines in a template gets `template = { name = "<template>" }`,
and `ngfw_device` when the export names the owning firewall.

## Multiple HA pairs to one firewall with several virtual routers

This is a common brown-field shape: three device groups, one per HA pair,
converted into one target device with one virtual router per function.

The converter does not merge the routing tables. It emits one rule chain per
(device group, vsys), and it keeps each resource in the scope the export states.
So:

1. Convert each device group, or run the converter once on the full export.
2. Name the virtual routers for the target on the device, after the apply, or
   edit the emitted `panos_virtual_router` resource.
3. Add the interface memberships for the target ports.
4. Route between virtual routers with static routes. Normal next-hop routes use
   `panos_virtual_router_static_route_ipv4`. PAN-OS next-VR routes have no v2
   attribute, so configure them on the target.

Keep one Terraform directory per device group, or merge the `.tf` files into one
directory. When two device groups emit the same file name, rename the files on
the merge. Do not merge two `provider.tf` files.

Routing protocols are report-only. BGP and OSPF settings go to
`MANUAL_SETUP_REPORT.txt`; use a different router ID per virtual router on the
merged device.

## Policy order

PAN-OS is first-match, so rule order is part of the security posture. The
converter preserves XML order inside a chain: the first rule of a chain anchors
at the end of the rulebase (`where = "last"`), and each later rule is placed
directly after the previous one and depends on it. A rule never pivots on, or
depends on, a rule in another virtual system or device group.

The rulebase (pre, post, shared) is not recorded, so a device group that has
both pre- and post-rules chains across them. This is a known limit recorded in
[`../backlog.md`](../backlog.md). Verify the rule order against the source before
you apply.

## Pre-migration checklist

- [ ] Export the configuration and keep the XML file
- [ ] Run the converter with `--validate`
- [ ] Read `SANITY_REPORT.txt`: no FAIL finding
- [ ] Read `CONVERSION_REPORT.txt` and the gap section
- [ ] Read `MANUAL_SETUP_REPORT.txt` and plan each manual item
- [ ] Build the interface and IP mapping table
- [ ] Replace the VPN pre-shared key placeholders
- [ ] Test in a lab environment before production
- [ ] Prepare a rollback: keep the source backup, and know which resources the
      state tracks

## Rollback

If Terraform has applied and you must go back:

1. `terraform destroy` removes what Terraform created.
2. Restore the source device from its backup, or restore the Panorama snapshot.
3. Verify connectivity, then reschedule.

Do not mix the two: a partial apply plus a manual restore leaves the Terraform
state and the device disagreeing.

## Common issues

| Symptom | Cause and action |
|---|---|
| Zone creation fails, interface not found | The interface is in another device group or template. Check the `location` block, and apply the interface first. |
| Apply fails with "not found" on a name | The name lives outside the export, so the converter left it as a plain string. Create the object, or point the provider at the right scope. |
| Rules land in the wrong order | The export mixed rulebases, or you edited the chain. Compare the plan with `CONVERSION_REPORT.txt`. |
| Interface names do not match the target | Edit the `name` attributes, then the zone membership and the virtual router membership. |
| Static route missing | The route is a next-VR route, which has no v2 attribute. Configure it on the target. |
| Profile reference missing | Profile bodies are report-only. Create the profile, then the profile group. |
