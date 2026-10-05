"""F2.6 dependency wiring.

A name attribute that points at an object exported by the same run must
be a Terraform ``.name`` reference so apply order is deterministic. A
name that points outside the export (built-ins, other tenants) stays a
plain string: the generator never declares a phantom resource to make a
reference work.

Pins on the dedicated fixture:

- group member lists, rule zone/address/service lists, zone and virtual
  router interface lists, subinterface parents, and the VPN reference
  chain all reference declared objects;
- object scope wins over group scope on name collisions;
- undeclared names stay plain strings;
- invariant: every emitted ``.name`` reference resolves to a resource
  declared in the same output;
- the output passes ``terraform init`` + ``terraform validate``.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import FIXTURES_DIR, run_script

TERRAFORM = shutil.which("terraform")
FIXTURE = FIXTURES_DIR / "dependency_wiring.xml"

REF_RE = re.compile(r"\b(panos_[a-z0-9_]+)\.([a-z0-9_]+)\.name\b")
RESOURCE_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"([^"]+)"')


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory) -> Path:
    """Generate the fixture output once for the whole module."""
    out = tmp_path_factory.mktemp("dependency_wiring")
    proc = run_script("panorama_to_terraform.py", str(FIXTURE), "--output-dir", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return out


def _read(out_dir: Path, name: str) -> str:
    return (out_dir / name).read_text(encoding="utf-8")


def _declared(out_dir: Path) -> set[tuple[str, str]]:
    """All (type, local) resource addresses declared in the output."""
    declared = set()
    for path in out_dir.iterdir():
        if path.suffix != ".tf":
            continue
        declared.update(RESOURCE_RE.findall(path.read_text(encoding="utf-8")))
    return declared


def _local_of(text: str, rtype: str, panos_name: str) -> str:
    """Terraform local name of the resource whose PAN-OS name attribute
    equals panos_name (a block ends at the first column-0 brace)."""
    m = re.search(
        r'resource\s+"' + re.escape(rtype) + r'"\s+"([^"]+)"\s*\{(?:(?!\n\}).)*?'
        r'name\s*=\s*"' + re.escape(panos_name) + r'"',
        text,
        re.S,
    )
    return m.group(1) if m else None


# --- Group member lists ------------------------------------------------------

def test_address_group_static_mixed_refs(out_dir):
    text = _read(out_dir, "address_groups.tf")
    both_local = _local_of(_read(out_dir, "address_objects.tf"), "panos_address", "both")
    host_local = _local_of(_read(out_dir, "address_objects.tf"), "panos_address", "host-a")
    assert both_local and host_local
    m = re.search(r"static = \[([^\]]*)\]", text)
    assert m is not None
    # Object scope wins on the "both" collision; ghost stays plain.
    assert f'panos_address.{both_local}.name' in m.group(1)
    assert f'panos_address.{host_local}.name' in m.group(1)
    assert '"ghost-addr"' in m.group(1)
    # The colliding group itself must not be referenced by its own member.
    assert "panos_address_group" not in m.group(1)


def test_service_group_members_mixed_refs(out_dir):
    text = _read(out_dir, "service_groups.tf")
    svc_local = _local_of(_read(out_dir, "service_objects.tf"), "panos_service", "svc-both")
    assert svc_local
    m = re.search(r"members = \[([^\]]*)\]", text)
    assert m is not None
    assert f'panos_service.{svc_local}.name' in m.group(1)
    assert "panos_service_group" not in m.group(1)  # object scope wins
    assert '"ghost-svc"' in m.group(1)


# --- Object attributes -------------------------------------------------------

def test_address_tag_wired_and_ghost_plain(out_dir):
    text = _read(out_dir, "address_objects.tf")
    tag_local = _local_of(_read(out_dir, "tags.tf"), "panos_administrative_tag", "tag-one")
    assert tag_local
    m = re.search(r"tags = \[([^\]]*)\]", text)
    assert m is not None
    assert f"panos_administrative_tag.{tag_local}.name" in m.group(1)
    assert '"tag-ghost"' in m.group(1)


# --- Rule lists --------------------------------------------------------------

def test_security_rule_zone_address_service_refs(out_dir):
    text = _read(out_dir, "security_rules.tf")
    zones = _read(out_dir, "zones.tf")
    zone_in = _local_of(zones, "panos_zone", "zone-in")
    zone_out = _local_of(zones, "panos_zone", "zone-out")
    both = _local_of(_read(out_dir, "address_objects.tf"), "panos_address", "both")
    svc_both = _local_of(_read(out_dir, "service_objects.tf"), "panos_service", "svc-both")
    # Zones: declared zone refs + ghost zone plain.
    assert f"panos_zone.{zone_in}.name" in text
    assert f"panos_zone.{zone_out}.name" in text
    assert '"zone-ghost"' in text
    # Addresses: object scope wins the "both" collision; ghost plain.
    assert f"panos_address.{both}.name" in text
    assert '"ghost-addr"' in text
    assert "panos_address_group" not in text
    # Services: object scope wins the "svc-both" collision; ghost plain.
    assert f"panos_service.{svc_both}.name" in text
    assert '"svc-ghost"' in text
    # Applications are built-in PAN-OS names: never wired.
    m = re.search(r"applications = \[([^\]]*)\]", text)
    assert m is not None and '"web-browsing"' in m.group(1)
    assert "panos_" not in m.group(1)


def test_nat_rule_refs_and_translation_interface(out_dir):
    text = _read(out_dir, "nat_rules.tf")
    zone_in = _local_of(_read(out_dir, "zones.tf"), "panos_zone", "zone-in")
    zone_out = _local_of(_read(out_dir, "zones.tf"), "panos_zone", "zone-out")
    both = _local_of(_read(out_dir, "address_objects.tf"), "panos_address", "both")
    svc_both = _local_of(_read(out_dir, "service_objects.tf"), "panos_service", "svc-both")
    eth11 = _local_of(_read(out_dir, "interfaces.tf"), "panos_ethernet_interface", "ethernet1/1")
    assert f"panos_zone.{zone_in}.name" in text
    m = re.search(r"destination_zone = \[([^\]]*)\]", text)
    assert m is not None and f"panos_zone.{zone_out}.name" in m.group(1)
    assert f"panos_address.{both}.name" in text
    m = re.search(r"^\s+service = (\S+)$", text, re.M)
    assert m is not None and m.group(1) == f"panos_service.{svc_both}.name"
    m = re.search(r"interface = (\S+)", text)
    assert m is not None and m.group(1) == f"panos_ethernet_interface.{eth11}.name"


# --- Network lists -----------------------------------------------------------

def _iface_locals(out_dir: Path) -> tuple[str, str, str]:
    """Local names of ethernet1/1, ethernet1/2, and ethernet1/2.10."""
    text = _read(out_dir, "interfaces.tf")
    return (
        _local_of(text, "panos_ethernet_interface", "ethernet1/1"),
        _local_of(text, "panos_ethernet_interface", "ethernet1/2"),
        _local_of(text, "panos_ethernet_layer3_subinterface", "ethernet1/2.10"),
    )


def test_zone_network_and_vr_interface_lists(out_dir):
    eth11, _eth12, eth1210 = _iface_locals(out_dir)
    zones = _read(out_dir, "zones.tf")
    m = re.search(r"layer3 = \[([^\]]*)\]", zones)
    assert m is not None
    # Mixed list: physical interface, subinterface, ghost stays plain.
    assert f"panos_ethernet_interface.{eth11}.name" in m.group(1)
    assert f"panos_ethernet_layer3_subinterface.{eth1210}.name" in m.group(1)
    assert '"ghost-iface"' in m.group(1)

    vrs = _read(out_dir, "virtual_routers.tf")
    m = re.search(r"interfaces = \[([^\]]*)\]", vrs)
    assert m is not None
    assert f"panos_ethernet_interface.{eth11}.name" in m.group(1)
    assert f"panos_ethernet_layer3_subinterface.{eth1210}.name" in m.group(1)
    assert '"ghost-iface"' in m.group(1)


def test_subinterface_parent_wired(out_dir):
    eth11, eth12, _eth1210 = _iface_locals(out_dir)
    text = _read(out_dir, "interfaces.tf")
    parents = re.findall(r"^\s+parent = (\S+)$", text, re.M)
    assert len(parents) == 2  # .0 subinterface + tagged subinterface
    assert f"panos_ethernet_interface.{eth11}.name" in parents
    assert f"panos_ethernet_interface.{eth12}.name" in parents


# --- VPN chain -----------------------------------------------------------------

def test_vpn_references_and_brown_field_fallback(out_dir):
    text = _read(out_dir, "vpn.tf")
    ike_local = _local_of(text, "panos_ike_crypto_profile", "dw-ike")
    gw_local = _local_of(text, "panos_ike_gateway", "dw-gw")
    ipsec_local = _local_of(text, "panos_ipsec_crypto_profile", "dw-ipsec")
    eth11, _eth12, _eth1210 = _iface_locals(out_dir)
    # Gateway -> IKE crypto profile (declared in this run).
    assert f"panos_ike_crypto_profile.{ike_local}.name" in text
    # Gateway local address -> interface (declared in this run).
    m = re.search(r"local_address = \{\s*interface = (\S+)", text)
    assert m is not None and m.group(1) == f"panos_ethernet_interface.{eth11}.name"
    # Tunnel -> gateway + IPsec profile (both declared in this run).
    assert f"panos_ike_gateway.{gw_local}.name" in text
    assert f"panos_ipsec_crypto_profile.{ipsec_local}.name" in text
    # Brown-field gateway: plain string, no reference.
    assert '"gw-undeclared"' in text
    # Regression: the old code declared a phantom gateway for the
    # brown-field name. Exactly one gateway resource may exist.
    declared = _declared(out_dir)
    gateways = [local for (rtype, local) in declared if rtype == "panos_ike_gateway"]
    assert gateways == [gw_local]


# --- F2.7 naming -----------------------------------------------------------------

def test_local_names_are_sanitized_name_plus_digest(out_dir):
    """Every local name is the sanitized name plus an 8-hex digest (F2.7),
    and no resource address is declared twice."""
    declared = _declared(out_dir)
    assert len(declared) == len({(rtype, local) for rtype, local in declared})
    for rtype, local in declared:
        assert re.fullmatch(r"[a-z0-9_]+_[0-9a-f]{8}(?:_\d+)?", local), (
            f"{rtype}.{local} does not match the F2.7 naming shape")


# --- Invariant ------------------------------------------------------------------

def test_every_emitted_reference_resolves_to_a_declared_resource(out_dir):
    """No dangling references anywhere in the generated output."""
    declared = _declared(out_dir)
    dangling = []
    for path in out_dir.iterdir():
        if path.suffix != ".tf":
            continue
        for rtype, local in REF_RE.findall(path.read_text(encoding="utf-8")):
            if (rtype, local) not in declared:
                dangling.append(f"{path.name}: {rtype}.{local}.name")
    assert dangling == [], "dangling references: " + ", ".join(dangling)


# --- Terraform gate --------------------------------------------------------------

def test_terraform_validate(out_dir):
    """The wired output must init and validate against the v2 provider."""
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (the CI terraform-gate job provides it)")
    init = subprocess.run(
        [TERRAFORM, "init", "-backend=false", "-input=false"],
        cwd=out_dir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert init.returncode == 0, f"terraform init failed:\n{init.stdout[-2000:]}\n{init.stderr[-2000:]}"
    result = subprocess.run(
        [TERRAFORM, "validate"],
        cwd=out_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"terraform validate failed:\n{result.stdout[-4000:]}\n{result.stderr[-2000:]}"
