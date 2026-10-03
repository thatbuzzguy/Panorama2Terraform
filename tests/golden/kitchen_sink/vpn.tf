# IPsec VPN Configuration
# IMPORTANT: Pre-shared keys are set to generic placeholders.
# You MUST update all pre-shared keys before applying!
# Search for "***CHANGE_ME***" and replace with actual keys.

# IKE Crypto Profiles

resource "panos_ike_crypto_profile" "ike_profile_ike_default" {
  name = "IKE-DEFAULT"
  dh_groups = ["group14"]
  authentications = ["sha256"]
  encryptions = ["aes256"]
  lifetime_hours = 24
}

# IPsec Crypto Profiles

resource "panos_ipsec_crypto_profile" "ipsec_profile_ipsec_default" {
  name = "IPSEC-DEFAULT"
  protocol = "esp"
  encryptions = ["aes256"]
  authentications = ["sha256"]
  dh_group = "group14"
  lifetime_hours = 1
}

# IKE Gateways
# WARNING: Pre-shared keys use placeholder "***CHANGE_ME***"
# Update these with actual keys from your key management system!

resource "panos_ike_gateway" "ike_gw_ike_gw_branch" {
  name = "IKE-GW-Branch"
  version = "ikev2"
  peer_address_type = "fqdn"
  peer_address_value = "branch.example.com"
  auth_type = "pre-shared-key"
  pre_shared_key = "***CHANGE_ME***"  # *** CHANGE THIS KEY ***
  ike_crypto_profile = panos_ike_crypto_profile.ike_profile_ike_default.name
  local_id_type = "ufqdn"
  local_id_value = "local.example.com"
  peer_id_type = "ufqdn"
  peer_id_value = "peer.example.com"
}

# IPsec Tunnels

resource "panos_ipsec_tunnel" "tunnel_tun_branch" {
  name = "TUN-Branch"
  tunnel_interface = "tunnel.1"
  type = "auto-key"
  ak_ike_gateway = panos_ike_gateway.ike_gw_ike_gw_branch.name
  ak_ipsec_crypto_profile = panos_ipsec_crypto_profile.ipsec_profile_ipsec_default.name
}

resource "panos_ipsec_tunnel_proxy_id_ipv4" "proxy_tun_branch_proxy_1" {
  ipsec_tunnel = panos_ipsec_tunnel.tunnel_tun_branch.name
  name = "proxy-1"
  local = "10.0.0.0/8"
  remote = "192.168.0.0/16"
  protocol_number = 17
}

