"""F3.3: every interface kind emits its schema-verified resource type.

The provider has no virtual-wire resource type: virtual-wire and tap entries
are nested blocks on panos_ethernet_interface. Subinterface resources carry a
parent reference to the physical interface or aggregate group declared in the
same run.

The last two pins read the parse object, not the print, so they run in process: `tag` is a field every
interface row declares, and a list field has two export shapes (`docs/COVERAGE_MATRIX.md` §1).
"""

import re

import container_coverage
import entry_coverage
from conftest import FIXTURES_DIR, RESOURCE_RE, file_text, run_pipeline, run_script, tf_files


def _generate(fixture: str, tmp_path) -> str:
    proc = run_script("panorama_to_terraform.py", str(FIXTURES_DIR / fixture), "--output-dir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    # F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): `interfaces.tf` is the unit's file, so the reader keys
    # it by the path, and this helper joins the parts in path order.
    return file_text(tf_files(tmp_path), "interfaces.tf")


def _blocks(text: str) -> dict[str, str]:
    """Resource bodies keyed by the resource `name` attribute."""
    out = {}
    for block in re.findall(r'resource "[a-z0-9_]+" "[^"]+" \{\n(.*?)\n\}', text, re.S):
        # The resource name attribute sits at two-space indent; the location
        # block also contains an indented `name`, so anchor on the indent.
        m = re.search(r'^  name = "([^"]+)"', block, re.M)
        if m:
            out[m.group(1)] = block
    return out


def _block_types(text: str) -> dict[str, str]:
    """Resource type keyed by the resource `name` attribute, for the shape the emitter chose."""
    types = {}
    for m in RESOURCE_RE.finditer(text):
        body = text[m.end() : text.find("\n}", m.end())]
        name = re.search(r'^  name = "([^"]+)"', body, re.M)
        if name:
            types[name.group(1)] = m.group(1)
    return types


def test_every_kind_emits_its_resource_type(tmp_path):
    """Each parsed kind emits the provider resource type for that kind."""
    text = _generate("interfaces_other.xml", tmp_path)
    types = {m.group(1) for m in RESOURCE_RE.finditer(text)}
    assert types == {
        "panos_vlan_interface",
        "panos_loopback_interface",
        "panos_tunnel_interface",
        "panos_aggregate_interface",
        "panos_aggregate_layer3_subinterface",
    }


def test_ethernet_subinterface_unit_emits_with_parent_reference(tmp_path):
    """A units/entry becomes its own resource with a reference to the parent."""
    text = _generate("interfaces_ethernet.xml", tmp_path)
    blocks = _blocks(text)

    parent_block = blocks["ethernet1/1"]
    parent_local = re.search(r'resource "panos_ethernet_interface" "([^"]+)"', text).group(1)
    sub = blocks["ethernet1/1.10"]
    assert f"parent = panos_ethernet_interface.{parent_local}.name" in sub
    assert "tag = 10" in sub
    assert 'name = "ethernet1/1.10"' in sub
    assert parent_block  # the physical entry is still emitted


def test_subinterface_parents_resolve_to_declared_resources(tmp_path):
    """No subinterface keeps a plain string parent when the parent is in the run."""
    text = _generate("interfaces_other.xml", tmp_path)
    blocks = _blocks(text)

    ae_group_local = re.search(r'resource "panos_aggregate_interface" "([^"]+)"', text).group(1)
    ae_sub_local = re.search(r'resource "panos_aggregate_layer3_subinterface" "([^"]+)"', text).group(1)
    assert f"parent = panos_aggregate_interface.{ae_group_local}.name" in blocks["ae1.101"]
    assert f"parent = panos_aggregate_layer3_subinterface.{ae_sub_local}.name" in blocks["ae1.101.20"]


def test_the_aggregate_shape_choice_is_the_entry_the_scan_measures(tmp_path):
    """The aggregate subinterface type comes from the entry inside the aggregate entry.

    The emitter takes the type from `INTERFACE_RESOURCE_TYPES` for a `units` entry, and from the name rule
    for an aggregate entry whose name already carries a unit. The container row covers the first, so the type
    the run prints for `ae1.101.20` is the type the property scan measures through that row.
    """
    types = _block_types(_generate("interfaces_other.xml", tmp_path))
    assert types["ae1"] == "panos_aggregate_interface", types
    assert types["ae1.101"] == "panos_aggregate_layer3_subinterface", types
    assert types["ae1.101.20"] == "panos_aggregate_layer3_subinterface", types


def test_aggregate_group_has_no_parent_or_tag(tmp_path):
    """The aggregate group resource has neither parent nor tag in the schema."""
    blocks = _blocks(_generate("interfaces_other.xml", tmp_path))
    group = blocks["ae1"]
    assert "parent" not in group
    assert "tag" not in group
    assert "layer2 = {}" in group


def test_virtual_wire_and_tap_emit_as_blocks(tmp_path):
    """Virtual-wire and tap are nested blocks, not separate resource types."""
    text = _generate("interfaces_ethernet.xml", tmp_path)
    blocks = _blocks(text)
    assert "virtual_wire = {}" in blocks["ethernet1/3"]
    assert "virtual_wire = {}" in blocks["ethernet1/4.1"]
    assert "tap = {}" in blocks["ethernet1/5"]
    # F3.3 criterion 4: no manual-review note for a modeled mode.
    assert "requires manual review" not in text


def test_ip_list_is_emitted_for_every_kind(tmp_path):
    """Regression: the ip attribute was dropped because the helper mutated a str."""
    blocks = _blocks(_generate("interfaces_other.xml", tmp_path))
    for name in ("vlan.10", "loopback.1", "tunnel.1", "ae1.101", "ae1.101.20"):
        assert "ip = [" in blocks[name], name


def test_interfaces_are_template_scoped(tmp_path):
    """The provider scopes interface resources to a template, not a device group."""
    text = _generate("interfaces_other.xml", tmp_path)
    assert "device_group" not in text
    assert "template = {" in text


INTERFACE_KIND_CONTENT = """<?xml version="1.0"?>
<config version="10.0.0">
  <devices>
    <entry name="localhost.localdomain">
      <vsys>
        <entry name="vsys1">
          <network>
            <interface>
              <ethernet>
                <entry name="ethernet1/1">
                  <mode>layer3</mode>
                  <tag>7</tag>
                  <layer3>
                    <interface-management-profile>Mgmt-A</interface-management-profile>
                    <ip><entry name="10.1.1.1/24"/></ip>
                    <ipv6><address><member>2001:db8::1/64</member></address></ipv6>
                  </layer3>
                  <comment>Physical entry</comment>
                </entry>
                <entry name="ethernet1/4.1">
                  <mode>virtual-wire</mode>
                  <virtual-wire><tag>101</tag></virtual-wire>
                  <comment>Virtual-wire unit</comment>
                </entry>
              </ethernet>
              <vlan>
                <units>
                  <entry name="20">
                    <comment>Vlan unit</comment>
                    <ip><entry name="10.1.20.1/24"/></ip>
                    <ipv6><address><entry name="2001:db8::20/64"/></address></ipv6>
                    <interface-management-profile>Mgmt-C</interface-management-profile>
                  </entry>
                </units>
              </vlan>
              <loopback>
                <units>
                  <entry name="1">
                    <comment>Loopback unit</comment>
                    <ip><member>10.1.1.2/32</member></ip>
                    <ipv6><address><member>2001:db8::2/128</member></address></ipv6>
                    <interface-management-profile>Mgmt-D</interface-management-profile>
                  </entry>
                </units>
              </loopback>
              <tunnel>
                <units>
                  <entry name="2">
                    <comment>Tunnel unit</comment>
                    <ip><entry name="10.1.1.3/32"/></ip>
                    <ipv6><address><member>2001:db8::3/128</member></address></ipv6>
                    <interface-management-profile>Mgmt-E</interface-management-profile>
                  </entry>
                </units>
              </tunnel>
              <aggregate-ethernet>
                <entry name="ae1">
                  <comment>Aggregate group</comment>
                  <layer3>
                    <ip><member>10.1.101.1/24</member></ip>
                    <ipv6><address><member>2001:db8::101/128</member></address></ipv6>
                    <interface-management-profile>Mgmt-F</interface-management-profile>
                  </layer3>
                </entry>
                <entry name="ae1.101">
                  <comment>Aggregate subinterface</comment>
                  <layer3>
                    <ip><member>10.1.102.1/24</member></ip>
                    <ipv6><address><member>2001:db8::102/128</member></address></ipv6>
                    <interface-management-profile>Mgmt-G</interface-management-profile>
                  </layer3>
                </entry>
              </aggregate-ethernet>
            </interface>
          </network>
        </entry>
      </vsys>
    </entry>
  </devices>
</config>
"""


def _run_in_process(converter_module, content: str, out_dir):
    """Run content this pin wrote, in process, so the read record survives.

    The parse object is what these pins read, so the run cannot be a subprocess: `run_script`
    loses the ledger with the process. The content is in `tmp_path`, not in `tests/fixtures/`,
    so the corpus set is unchanged.
    """
    source = out_dir.parent / (out_dir.name + ".xml")
    source.write_text(content, encoding="utf-8")
    parser = run_pipeline(converter_module, str(source), out_dir)
    assert parser is not None, source
    return parser.ledger


def test_the_interface_object_holds_the_fields_its_row_declares(converter_module, tmp_path):
    """For every interface row, the keys the parse stored are the fields that row declares (F4.4).

    One entry per kind, each stating every field its row declares, so the stored key set is the row's
    properties plus `name` and the five scope facts, and holds no key the row does not state. `zone` and
    `virtual_router` are not interface fields: the provider models membership from the other side
    (`panos_zone.interfaces`, `panos_virtual_router.interfaces`), so the interface object carries no key for
    either. `parent` is a field only for the kinds whose row declares it, so a physical entry and a
    virtual-wire unit hold no parent key.

    Before the change a physical entry stored no `tag`, and every kind stored `zone` and `virtual_router`.
    """
    ledger = _run_in_process(converter_module, INTERFACE_KIND_CONTENT, tmp_path / "kinds")
    stored = {}
    for entry in ledger.entries():
        mark = ledger.mark_for(entry)
        if mark is None:
            continue
        captured = mark["captured"]
        row = entry_coverage.matrix_row_for(
            container_coverage.section_path(ledger.parents[entry], ledger.parents, ledger.source)
        )
        assert row is not None and row["resource"].startswith("panos_"), entry.get("name")
        fields = set(captured) - entry_coverage.NON_FIELD_KEYS
        assert fields == set(row["properties"]), (captured.get("type"), sorted(fields), sorted(row["properties"]))
        # Only the interface parse objects carry a stored name; the scope entry records the scope facts.
        if captured.get("name") is not None:
            stored[captured["name"]] = captured
    assert sorted(stored) == ["ae1", "ae1.101", "ethernet1/1", "ethernet1/4.1", "loopback.1", "tunnel.2", "vlan.20"], (
        sorted(stored)
    )

    # The `tag` the row states, from either place the export states it, or from the name when the name
    # carries the unit (`TerraformParser._interface_tag`). The aggregate group has no unit in its name, so
    # the rule states no value for it, and `captured_fields` cannot see an empty field (F4.4 rule 4).
    assert {name: obj["tag"] for name, obj in stored.items()} == {
        "ethernet1/1": "7",  # the entry's own `tag` element
        "ethernet1/4.1": "101",  # the `tag` inside the mode block
        "vlan.20": "20",  # the unit part of the name
        "loopback.1": "1",
        "tunnel.2": "2",
        "ae1": None,
        "ae1.101": "101",
    }, {name: obj["tag"] for name, obj in stored.items()}
    # Only the kinds whose row declares a parent hold the key.
    assert {name: ("parent" in obj) for name, obj in stored.items()} == {
        "ethernet1/1": False,
        "ethernet1/4.1": False,
        "vlan.20": True,
        "loopback.1": True,
        "tunnel.2": True,
        "ae1": True,
        "ae1.101": True,
    }


def test_a_list_field_is_read_in_both_export_shapes(converter_module, tmp_path):
    """A list field is the entry names or the member texts under the element the field names (F4.4).

    Before the change the interface parse read only the entry form, so a member-form address was dropped.
    The two forms are one field read by one rule, `_list_values`, which is the list form of the value rule
    that already accepts both. Only direct children count, so a `units` container inside the read scope
    cannot put its entries' values into the parent's list; the aggregate branch is the shape that shows
    it, because its units sit inside `layer3`, inside the element the parent's field reads.
    """
    content = """<?xml version="1.0"?>
<config version="10.0.0">
  <shared>
    <network>
      <interface>
        <aggregate-ethernet>
          <entry name="ae1">
            <layer3>
              <ip><member>10.1.1.1/24</member></ip>
              <ipv6><address><entry name="2001:db8::1/64"/></address></ipv6>
              <units>
                <entry name="10"><ip><member>10.1.10.1/24</member></ip></entry>
              </units>
            </layer3>
          </entry>
        </aggregate-ethernet>
      </interface>
    </network>
  </shared>
</config>
"""
    ledger = _run_in_process(converter_module, content, tmp_path / "shapes")
    recorded = {
        entry.get("name"): ledger.mark_for(entry)["captured"]
        for entry in ledger.entries()
        if ledger.mark_for(entry) is not None
    }
    parent = recorded["ae1"]
    # The member form is read, and the parent's list holds only its own member: the `units` container
    # inside `layer3` did not reach it.
    assert parent["ip_addresses"] == ["10.1.1.1/24"], parent["ip_addresses"]
    # The entry form is read: the entry name under `ipv6/address` is the value.
    assert parent["ipv6_addresses"] == ["2001:db8::1/64"], parent["ipv6_addresses"]
    # The unit entry keeps its own value, on its own object, through the same rule.
    unit = recorded["10"]
    assert unit["ip_addresses"] == ["10.1.10.1/24"], unit["ip_addresses"]
    assert unit["parent"] == "ae1", unit["parent"]
