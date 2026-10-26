# Advanced Routing Engine (logical routers)

PAN-OS 10.2+ Advanced Routing Engine (ARE) replaces legacy virtual routers with
logical routers. The converter handles both. The document index is in
[README.md](README.md).

## What the converter does

- Parses both router kinds through one path, `.//network/<kind>/entry`, so a
  router is found wherever the export puts it: in a template, in a template's
  device, under a device, or under a device's virtual system. Each entry takes
  its scope from its own ancestors.
- Emits both as `panos_virtual_router`, each labelled with a comment:
  `# Type: Virtual Router (Legacy)` or
  `# Type: Logical Router (Advanced Routing Engine)`.
- Emits static routes as `panos_virtual_router_static_route_ipv4` resources that
  reference the owning router.

## Example (logical router)

The kitchen-sink fixture (`tests/fixtures/kitchen_sink.xml`) contains a logical
router, `lr-main`. Its real generated output, pinned byte-for-byte in
`tests/golden/kitchen_sink/virtual_routers.tf`:

```hcl
# Source: FW-Template
# Type: Logical Router (Advanced Routing Engine)
resource "panos_virtual_router" "lr_main_2258b30f" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-main"
  interfaces = [panos_ethernet_interface.ethernet1_1_d74b05bd.name]
}

resource "panos_virtual_router_static_route_ipv4" "lr_main_2258b30f_lr_default_2029ebbd" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "lr-default"
  virtual_router = panos_virtual_router.lr_main_2258b30f.name
  destination = "0.0.0.0/0"
  interface = "lr-peer"
}
```

(Local resource names are the sanitized PAN-OS name plus an 8-hex digest
of the object's source identity.)

## Static route next hop

Two shapes appear in an export, and the provider models one of them:

| Export shape | Emitted attribute | Note |
|---|---|---|
| `nexthop/ip-address` | `nexthop = { ip_address = "..." }` | direct |
| `nexthop/next-vr` or `nexthop/next-lr` | `interface = "<router name>"` | v2 has no next-VR or next-LR attribute, so the converter writes the name into `interface`. The provider reads `interface` as the outgoing interface, not as another router. Check each such route against the target, and set the next-VR hop there. |

The default route is written as `destination = "0.0.0.0/0"`, because a Panorama
export states the default route destination as `default`.

## Not parsed

These ARE features are not read: routing profiles (authentication, timers,
dampening, filtering), access lists, prefix lists, AS path lists, community
lists, route maps, MP-BGP address families, BFD, and multicast. Configure them
on the target after migration.

BGP, OSPF and their redistribution rules have no v2 resource. The parser reads
them, and `MANUAL_SETUP_REPORT.txt` carries the router ID, AS number, peer
groups, peers, areas and interfaces. The report does not print the BGP
redistribution rules it captured; that gap is recorded in
[`../backlog.md`](../backlog.md).

## References

- Advanced routing:
  <https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-networking-admin/advanced-routing>
- `panos_virtual_router` (v2):
  <https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs/resources/virtual_router>
- `panos_logical_router` (v2 exists, but the converter emits
  `panos_virtual_router` for both router kinds):
  <https://registry.terraform.io/providers/PaloAltoNetworks/panos/latest/docs/resources/logical_router>
