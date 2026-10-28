"""F4.2 entry coverage: the container table and the unknown-container report.

Two rules, stated once here:

1. The container table. One row per parse method: the container it reads and
   where its entries go. `docs/ARCHITECTURE.md` §3.1 points at this table
   instead of restating it, so a test can compare the table with the code.
2. The entry-container rule. A container is a **section** when no config-object
   entry lies between it and a config root. A config root is the `config`
   element or an entry that defines a scope (see `SCOPE_CONTAINERS`). A
   container inside a config-object entry is a property level, not a section: the
   property-level scan (F4.4) reports it, so this module reports the section level.

The scan reports a section that no row covers. A section that is absent from
the input is not a finding: an export does not have to contain every container
this converter knows. An entry container under `predefined` is not a finding
either: those entries are PAN-OS built-in definitions, not operator objects, so
no parse method is expected to read them.

Matching is by suffix on the tag chain from the config root, because a parse
method reads a container with a relative pattern (`findall('.//address/entry')`)
and the same container can sit under a scope entry or under a rulebase prefix.

F5.4 adds the per-scope shape rule: `response` and `result` are the envelope, never a
container name. For a per-scope source, `result` is the place the declared path names,
and the scan reads the element under it as an entry inside the container the path names
first, so the entry under the root is the declared scope entry. `container_tag` is the
one function that states this, and the scan, the ledger, and the parser scope walk all
read it.

Report order is fixed: findings are sorted by tag chain, then line, so the same
input produces the same bytes. A report body names the source name only, never the
path (`SOURCE_LABEL`); the path is in the provenance record (`provenance.py`, F5.3).
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

from xml_input import ENTRY_SEGMENT, ParsedSource

# Where the entries of a container go. Six destinations match
# docs/ARCHITECTURE.md §2.4. F4.3 adds two entry kinds: `skipped` is an entry a
# parse method visited and did not model, and `unaccounted` is an entry no parse
# method read.
DESTINATION_KINDS = (
    'emitted',      # a resource block
    'report',       # MANUAL_SETUP_REPORT.txt
    'inventory',    # the inventory comment
    'count-only',   # counted, nothing written (a gap)
    'bookkeeping',  # a table or a scope fact, no object
    'nested-block',  # lines inside a parent resource block, not a resource
    'skipped',       # F4.3: an entry a parse method visited and did not model
    'unaccounted',   # F4.3: an entry no parse method read
)

# How a method reaches the container: a findall/find pattern, or the parent
# walk that answers the four scope facts (F3.5).
READ_VIAS = ('pattern', 'scope walk')

# Containers whose entry defines a scope. This is the set the four scope facts
# walk, so the section rule and the identity keys agree.
SCOPE_CONTAINERS = frozenset({'device-group', 'templates', 'template-stack',
                              'devices', 'vsys'})

# The envelope of an API response (F4.2, F5.4). Never a container name: the wrapper
# decision reads `result` as the place a per-scope path names, not as a scanned container.
ENVELOPE = frozenset({'response', 'result'})

# The first path segment a scope path may name (F5.4 AC-1). `shared` is a place the scan
# already knows (PATH_ROOTS), so the CLI validates against the set plus the shared section,
# through this one definition.
SCOPE_PATH_ROOTS = SCOPE_CONTAINERS | frozenset({'shared'})

# The four scope facts (F3.1, F3.2) in report order. F4.3 uses these keys for
# the captured-field rule, so the facts are named in one place.
SCOPE_FACT_KEYS = ('device_group', 'vsys', 'template', 'vsys_device')

# The PAN-OS "this device" placeholder (F3.5). It names no firewall, so it is never a
# `vsys_device` fact, never an `ngfw_device`, and never joins two scopes. One definition,
# read by the generator and by the state scan (F5.6).
PLACEHOLDER_DEVICE = 'localhost.localdomain'

# Segments dropped from a section path: the config root and the two Panorama
# scope markers are places, not part of a container name.
PATH_ROOTS = frozenset({'config', 'shared', 'panorama'})


@dataclass(frozen=True)
class ContainerRow:
    """One parse method reading one container."""

    method: str
    path: str
    destination: str
    note: str = ''
    level: str = 'section'      # 'section' or 'sub-shape'
    read_via: str = 'pattern'   # one of READ_VIAS


# One row per parse method. A new parse method needs a row here, and
# tests/test_container_coverage.py fails when it does not have one.
CONTAINER_TABLE: tuple[ContainerRow, ...] = (
    ContainerRow('parse_device_groups', 'device-group', 'bookkeeping',
                 'the name reaches the output through location'),
    ContainerRow('parse_associations', 'device-group', 'bookkeeping',
                 'association table'),
    ContainerRow('parse_associations', 'templates', 'bookkeeping',
                 'association table'),
    ContainerRow('parse_associations', 'template-stack', 'bookkeeping',
                 'association table'),
    ContainerRow('device_group_of', 'device-group', 'bookkeeping',
                 'device_group scope fact', level='section', read_via='scope walk'),
    ContainerRow('vsys_of', 'vsys', 'bookkeeping', 'vsys scope fact',
                 level='section', read_via='scope walk'),
    ContainerRow('template_of', 'templates', 'bookkeeping', 'template scope fact',
                 level='section', read_via='scope walk'),
    ContainerRow('device_of', 'devices', 'bookkeeping', 'vsys_device scope fact',
                 level='section', read_via='scope walk'),
    ContainerRow('parse_tags', 'tag', 'emitted', 'panos_administrative_tag'),
    ContainerRow('parse_regions', 'region', 'count-only', 'no v2 resource (gap)'),
    ContainerRow('parse_custom_url_categories', 'custom-url-category', 'emitted',
                 'panos_custom_url_category'),
    ContainerRow('parse_application_groups', 'application-group', 'emitted',
                 'panos_application_group'),
    ContainerRow('parse_application_filters', 'application-filter', 'report',
                 'no v2 resource'),
    ContainerRow('parse_external_lists', 'external-list', 'emitted',
                 'panos_external_dynamic_list'),
    ContainerRow('parse_schedules', 'schedule', 'report', 'no v2 resource'),
    ContainerRow('parse_address_objects', 'address', 'emitted',
                 'panos_address, or report when the entry has no v2 attribute'),
    ContainerRow('parse_address_groups', 'address-group', 'emitted',
                 'panos_address_group'),
    ContainerRow('parse_service_objects', 'service', 'emitted',
                 'panos_service; the dropped protocol leg is reported'),
    ContainerRow('parse_service_groups', 'service-group', 'emitted',
                 'panos_service_group'),
    ContainerRow('parse_security_rules', 'security/rules', 'emitted',
                 'panos_security_policy_rules'),
    ContainerRow('parse_nat_rules', 'nat/rules', 'emitted',
                 'panos_nat_policy_rules'),
    ContainerRow('parse_decryption_rules', 'decryption/rules', 'emitted',
                 'panos_decryption_policy_rules'),
    ContainerRow('parse_pbf_rules', 'pbf/rules', 'emitted',
                 'panos_pbf_policy_rules'),
    ContainerRow('parse_application_override_rules', 'application-override/rules',
                 'report', 'no v2 resource'),
    ContainerRow('parse_zones', 'zone', 'emitted', 'panos_zone'),
    ContainerRow('parse_interfaces', 'network/interface/ethernet', 'emitted',
                 'panos_ethernet_interface'),
    ContainerRow('parse_interfaces', 'network/interface/virtual-wire/units',
                 'nested-block', 'nested block; parent type from INTERFACE_RESOURCE_TYPES'),
    ContainerRow('parse_interfaces', 'network/interface/vlan/units', 'emitted',
                 'panos_vlan_interface'),
    ContainerRow('parse_interfaces', 'network/interface/loopback/units', 'emitted',
                 'panos_loopback_interface'),
    ContainerRow('parse_interfaces', 'network/interface/tunnel/units', 'emitted',
                 'panos_tunnel_interface; TAP emits as a nested block'),
    ContainerRow('parse_interfaces', 'network/interface/aggregate-ethernet',
                 'emitted', 'panos_aggregate_interface'),
    ContainerRow('parse_interfaces', 'ipv6/address', 'nested-block',
                 'nested address block; parent type from INTERFACE_RESOURCE_TYPES'),
    ContainerRow('parse_virtual_routers', 'network/virtual-router', 'emitted',
                 'panos_virtual_router plus static routes'),
    ContainerRow('parse_logical_routers', 'network/logical-router', 'emitted',
                 'panos_virtual_router, labelled router_type = logical'),
    ContainerRow('parse_security_profiles', 'profiles/virus', 'inventory',
                 'profile inventory comment'),
    ContainerRow('parse_security_profiles', 'profiles/spyware', 'inventory',
                 'profile inventory comment'),
    ContainerRow('parse_security_profiles', 'profiles/vulnerability', 'inventory',
                 'profile inventory comment'),
    ContainerRow('parse_security_profiles', 'profiles/url-filtering', 'inventory',
                 'profile inventory comment'),
    ContainerRow('parse_security_profiles', 'profiles/file-blocking', 'inventory',
                 'profile inventory comment'),
    ContainerRow('parse_security_profiles', 'profiles/wildfire-analysis', 'inventory',
                 'profile inventory comment'),
    ContainerRow('parse_security_profile_groups', 'profile-group', 'emitted',
                 'panos_security_profile_group'),
    ContainerRow('parse_zone_protection_profiles', 'zone-protection-profile',
                 'report', 'name and description only'),
    ContainerRow('parse_log_settings', 'log-settings/profiles', 'report',
                 'name and description only'),
    ContainerRow('parse_qos_profiles', 'qos/profile', 'report', 'no v2 resource'),
    ContainerRow('parse_tunnel_monitor_profiles',
                 'network/tunnel/global-protect-gateway/Default/tunnel-monitor/monitor-profile',
                 'report', 'no v2 resource'),
    ContainerRow('parse_tunnel_monitor_profiles',
                 'network/tunnel-monitor/monitor-profile', 'report',
                 'no v2 resource'),
    ContainerRow('parse_pbf_monitor_profiles', 'network/profiles/monitor-profile',
                 'emitted', 'panos_monitor_profile'),
    ContainerRow('parse_bgp', 'protocol/bgp', 'report', 'router settings, no v2 resource'),
    ContainerRow('parse_ospf', 'protocol/ospf', 'report', 'router settings, no v2 resource'),
    ContainerRow('parse_ipsec_tunnels', 'network/tunnel/ipsec', 'emitted',
                 'panos_ipsec_tunnel; a manual-key tunnel is reported'),
    ContainerRow('parse_ike_gateways', 'network/ike/gateway', 'emitted',
                 'panos_ike_gateway'),
    ContainerRow('parse_ike_crypto_profiles',
                 'network/ike/crypto-profiles/ike-crypto-profiles', 'emitted',
                 'panos_ike_crypto_profile'),
    ContainerRow('parse_ipsec_crypto_profiles',
                 'network/ike/crypto-profiles/ipsec-crypto-profiles', 'emitted',
                 'panos_ipsec_crypto_profile'),
    # Sub-shape entries: read by a parse method, but inside a config-object
    # entry, so they are property levels. The property-level scan (F4.4) reports
    # the ones a matrix row covers.
    ContainerRow('parse_interfaces', 'units', 'emitted', 'panos_ethernet_layer3_subinterface',
                 level='sub-shape'),
    ContainerRow('parse_interfaces', 'ip', 'nested-block',
                 'nested block; parent type from INTERFACE_RESOURCE_TYPES',
                 level='sub-shape'),
    ContainerRow('parse_interfaces', 'layer3/units', 'emitted',
                 'panos_ethernet_layer3_subinterface', level='sub-shape'),
    ContainerRow('parse_interfaces', 'layer3/ip', 'nested-block',
                 'nested block; parent type from INTERFACE_RESOURCE_TYPES', level='sub-shape'),
    ContainerRow('parse_qos_profiles', 'class', 'report', 'no v2 resource',
                 level='sub-shape'),
    ContainerRow('parse_bgp', 'protocol/bgp/peer-group', 'report', 'no v2 resource',
                 level='sub-shape'),
    ContainerRow('parse_bgp', 'protocol/bgp/peer', 'report', 'no v2 resource',
                 level='sub-shape'),
    ContainerRow('parse_bgp', 'protocol/bgp/redist-rules', 'report', 'no v2 resource',
                 level='sub-shape'),
    ContainerRow('parse_ospf', 'protocol/ospf/area', 'report', 'no v2 resource',
                 level='sub-shape'),
    ContainerRow('parse_ospf', 'protocol/ospf/range', 'report', 'no v2 resource',
                 level='sub-shape'),
    ContainerRow('parse_ospf', 'protocol/ospf/interface', 'report', 'no v2 resource',
                 level='sub-shape'),
    ContainerRow('parse_virtual_routers', 'routing-table/ip/static-route', 'emitted',
                 'panos_virtual_router_static_route_ipv4', level='sub-shape'),
    ContainerRow('parse_ipsec_tunnels', 'auto-key/proxy-id', 'nested-block',
                 'nested proxy_id block inside panos_ipsec_tunnel', level='sub-shape'),
    ContainerRow('parse_ipsec_tunnels', 'auto-key/gateway', 'bookkeeping',
                 'reference to an ike gateway entry', level='sub-shape'),
    ContainerRow('parse_external_lists', 'type', 'bookkeeping',
                 'sub-shape selector for the entry type', level='sub-shape'),
)


def rows_for(method: str) -> list[ContainerRow]:
    """The table rows that belong to one parse method."""
    return [row for row in CONTAINER_TABLE if row.method == method]


def parse_methods() -> list[str]:
    """Every method named in the table, in table order, without duplicates."""
    seen: list[str] = []
    for row in CONTAINER_TABLE:
        if row.method not in seen:
            seen.append(row.method)
    return seen


def parent_map(root: ET.Element) -> dict:
    """Child -> parent map. The parser builds one; the scan uses it."""
    return {child: parent for parent in root.iter() for child in parent}


def container_tag(node: ET.Element, parents: dict,
                  source: Optional[ParsedSource] = None) -> Optional[str]:
    """The container name the scan reads node's parent as (F5.4).

    Normally the parent's tag. For a per-scope source, `result` is the place the path
    names, so the element directly under the root is read as an entry inside the container
    the first path segment names. The envelope is never a container name, so a node whose
    parent is an envelope element that is not the per-scope root has no container name
    here. This is the one place the per-scope shape is stated; the scan, the ledger, and
    the parser scope walk all read it.
    """
    parent = parents.get(node)
    if parent is None:
        return None
    if source is not None and source.is_per_scope and parent is source.root:
        return source.scope_container
    if parent.tag in ENVELOPE:
        return None
    return parent.tag


def is_scope_entry(elem: ET.Element, parents: dict,
                   source: Optional[ParsedSource] = None) -> bool:
    """True when elem is an entry whose container defines a scope (F3.5, F5.4)."""
    return elem.tag == 'entry' and container_tag(elem, parents, source) in SCOPE_CONTAINERS


def is_section(container: ET.Element, parents: dict,
              source: Optional[ParsedSource] = None) -> bool:
    """True when no config-object entry lies between container and a config root."""
    node = container
    while node is not None:
        node = parents.get(node)
        if node is None:
            return True  # reached the config root, or the per-scope place (F5.4)
        if node.tag == 'entry' and not is_scope_entry(node, parents, source):
            return False
    return True


def section_path(container: ET.Element, parents: dict,
                 source: Optional[ParsedSource] = None) -> str:
    """Tag chain from the config root to the container.

    The config element and the Panorama scope markers (``shared``, ``panorama``)
    are places, not part of a container name, so the leading marker is dropped.
    A scope entry stays in the chain because it names the shape the operator
    sees in the file.

    F5.4: for a per-scope source, `result` is the place the path names, never a segment
    of a container name. When the path names an entry, `result` stands as the container
    the path names first, so the chain reads as it reads for the same shape in a
    whole-config export.
    """
    parts = [container.tag]
    node = container
    while node is not None:
        node = parents.get(node)
        if node is None:
            break
        parts.append(node.tag)
    chain = list(reversed(parts))
    if source is not None and source.is_per_scope:
        if chain and chain[0] == 'result':
            chain[0] = source.scope_container  # the root itself is the place
        elif ENTRY_SEGMENT in source.scope.split('/'):
            chain.insert(0, source.scope_container)
    while chain and chain[0] in PATH_ROOTS:
        chain.pop(0)
    return '/'.join(chain)


def covers(row_path: str, section: str) -> bool:
    """True when a table row covers a section path.

    A row path is relative to the scope that holds the container, so the section
    path matches when it is equal to the row path or ends with it.
    """
    return section == row_path or section.endswith('/' + row_path)


def is_known(section: str) -> bool:
    """True when a table row covers this section path."""
    return any(covers(row.path, section) for row in CONTAINER_TABLE)


def record_path(path: str) -> str:
    """The declared path as the record states it: no leading slash (F5.4 AC-5.3).

    The CLI shows a scope path with a leading slash; the request identity, the record, and
    the scan read it without one, so the same path is the same string in all three. A run
    that declares no path has no path to state, so this answers ''.
    """
    return path.strip('/') if path else ''

def is_scope_path(path: str) -> bool:
    """True when a declared path names a scope place (F5.4 AC-6.2).

    The shape is `/<container>` or `/<container>/entry/<name>`, and the first segment
    must name a declared scope container. The CLI validates through this function, so
    the set of readable scopes is stated once.
    """
    segments = [segment for segment in path.strip('/').split('/') if segment]
    if not segments or segments[0] not in SCOPE_PATH_ROOTS:
        return False
    return len(segments) == 1 or (len(segments) == 3 and segments[1] == ENTRY_SEGMENT and segments[2])


def is_predefined(container: ET.Element, parents: dict) -> bool:
    """True when the container sits under a `predefined` section."""
    node = container
    while node is not None:
        if node.tag == 'predefined':
            return True
        node = parents.get(node)
    return False


def entry_containers(root: ET.Element, parents: dict,
                     source: Optional[ParsedSource] = None) -> list[ET.Element]:
    """Every element that holds entries, in document order.

    The envelope is never a scanned container (F4.2, F5.4). A per-scope source reads its
    root `result` as the container the path names, so the root is not skipped; the name
    comes from `section_path`.
    """
    return [el for el in root.iter() if any(child.tag == 'entry' for child in el)
            and not (el.tag in ENVELOPE and el is not root)]


@dataclass(frozen=True)
class Finding:
    """A section the table does not cover."""

    path: str
    line: Optional[int]
    entries: int


def scan(source: ParsedSource, parents: dict) -> list[Finding]:
    """Find every section container the table does not cover, in report order."""
    findings = []
    for container in entry_containers(source.root, parents, source):
        if not is_section(container, parents, source) or is_predefined(container, parents):
            continue
        path = section_path(container, parents, source)
        if is_known(path):
            continue
        findings.append(Finding(path=path,
                                line=source.line_of(container),
                                entries=sum(1 for child in container if child.tag == 'entry')))
    return sorted(findings, key=lambda f: (f.path, f.line or 0))


SECTION_TITLE = 'Entry Coverage: Containers The Parser Does Not Read'

# The label a report body uses for the source it read (F5.3). One label, stated here, so
# the per-entry report and this section cannot disagree. It names the source name only:
# the path belongs to the provenance record, because a report body must stay byte-identical
# between runs that read the same bytes from different paths.
SOURCE_LABEL = 'Source:'


def entry_phrase(count: int) -> str:
    """'1 entry' or 'N entries'. One wording for the report and the console."""
    return f'{count} entry' if count == 1 else f'{count} entries'


def position_phrase(finding: Finding) -> str:
    """The source line, or the honest statement that there is no line."""
    return f'line {finding.line}' if finding.line else 'position unknown'


def finding_phrase(finding: Finding) -> str:
    """Path, position and entry count: the line a finding is described by."""
    return f'{finding.path} ({position_phrase(finding)}): {entry_phrase(finding.entries)}'


def report_line(finding: Finding) -> str:
    """One report line for one finding."""
    return f'  {finding_phrase(finding)} - no parse method reads this container'


def console_line(finding: Finding) -> str:
    """One console line for one finding."""
    return f'  - {finding_phrase(finding)}'


def render_section(findings: list[Finding], source_name: str) -> str:
    """The report section for the findings. Empty when there is nothing to say."""
    if not findings:
        return ''
    lines = [f'--- {SECTION_TITLE} ---', f'{SOURCE_LABEL} {source_name}']
    lines.extend(report_line(finding) for finding in findings)
    lines.append('  No parse method reads these containers, so their entries are '
                 'not in the model and cannot be emitted. Property-level coverage '
                 'is F4.4, in the property section of CONVERSION_REPORT.txt.')
    return '\n'.join(lines)
