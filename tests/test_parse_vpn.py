"""Unit tests for PanoramaParser VPN parse methods (IPsec tunnels, IKE gateways, crypto profiles)."""


def _parser(make_parser, fixture_name):
    return make_parser(fixture_name)


def test_parse_ipsec_tunnels(make_parser):
    p = _parser(make_parser, "ipsec_tunnels.xml")
    tunnels = p.parse_ipsec_tunnels()
    assert len(tunnels) == 1
    tunnel = tunnels[0]
    assert tunnel["name"] == "TUN-Branch"
    assert tunnel["tunnel_interface"] == "tunnel.1"
    assert tunnel["type"] == "auto-key"
    assert tunnel["ike_gateway"] == "IKE-GW-Branch"
    assert tunnel["ipsec_crypto_profile"] == "IPSEC-DEFAULT"

    assert len(tunnel["proxy_ids"]) == 1
    proxy = tunnel["proxy_ids"][0]
    assert proxy["name"] == "proxy-1"
    assert proxy["local"] == "10.0.0.0/8"
    assert proxy["remote"] == "192.168.0.0/16"
    assert proxy["protocol"] == "17"


def test_parse_ike_gateways(make_parser):
    p = _parser(make_parser, "ike_gateways.xml")
    gateways = p.parse_ike_gateways()
    assert len(gateways) == 1
    gw = gateways[0]
    assert gw["name"] == "IKE-GW-Branch"
    assert gw["version"] == "ikev2"
    assert gw["ike_crypto_profile"] == "IKE-DEFAULT"
    assert gw["peer_address"] == "branch.example.com"
    assert gw["peer_address_type"] == "fqdn"
    assert gw["auth_type"] == "pre-shared-key"
    assert gw["local_id"] == "local.example.com"
    assert gw["peer_id"] == "peer.example.com"


def test_parse_ike_crypto_profiles(make_parser):
    p = _parser(make_parser, "ike_crypto_profiles.xml")
    profiles = p.parse_ike_crypto_profiles()
    assert len(profiles) == 1
    prof = profiles[0]
    assert prof["name"] == "IKE-DEFAULT"
    assert prof["dh_groups"] == ["group14"]
    assert prof["authentications"] == ["sha256"]
    assert prof["encryptions"] == ["aes256"]
    assert prof["lifetime_hours"] == "24"


def test_parse_ipsec_crypto_profiles(make_parser):
    p = _parser(make_parser, "ipsec_crypto_profiles.xml")
    profiles = p.parse_ipsec_crypto_profiles()
    assert len(profiles) == 1
    prof = profiles[0]
    assert prof["name"] == "IPSEC-DEFAULT"
    assert prof["protocol"] == "esp"
    assert prof["encryptions"] == ["aes256"]
    assert prof["authentications"] == ["sha256"]
    assert prof["dh_group"] == "group14"
    assert prof["lifetime_hours"] == "1"
    assert prof["lifetime_kb"] == "4608000"
