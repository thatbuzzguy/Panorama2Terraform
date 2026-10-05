# IPsec VPN Configuration
# IMPORTANT: Pre-shared keys are set to generic placeholders.
# You MUST update all pre-shared keys before applying!
# Search for "***CHANGE_ME***" and replace with actual keys.

# IKE Crypto Profiles

resource "panos_ike_crypto_profile" "ike_profile_ike_default_58021a99" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "IKE-DEFAULT"
  encryption = ["aes256"]
  hash = ["sha256"]
  dh_group = ["group14"]
  lifetime = {
    hours = 24
  }
}

# IPsec Crypto Profiles

resource "panos_ipsec_crypto_profile" "ipsec_profile_ipsec_default_964d437a" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "IPSEC-DEFAULT"
  dh_group = "group14"
  esp = {
    encryption = [ "aes256" ]
    authentication = [ "sha256" ]
  }
  lifetime = {
    hours = 1
  }
  lifesize = {
    kb = 4608000
  }
}

# IKE Gateways
# WARNING: Pre-shared keys use placeholder "***CHANGE_ME***"
# Update these with actual keys from your key management system!

resource "panos_ike_gateway" "ike_gw_ike_gw_branch_2b6fe510" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "IKE-GW-Branch"
  protocol = {
    version = "ikev2"
    ikev2 = {
      ike_crypto_profile = panos_ike_crypto_profile.ike_profile_ike_default_58021a99.name
    }
  }
  peer_address = {
    fqdn = "branch.example.com"
  }
  authentication = {
    pre_shared_key = {
      key = "***CHANGE_ME***"
    }
  }  # *** CHANGE THIS KEY ***
  local_id = {
    id = "local.example.com"
  }
  peer_id = {
    id = "peer.example.com"
  }
}

# IPsec Tunnels

resource "panos_ipsec_tunnel" "tunnel_tun_branch_654a01ce" {
  location = {
    template = {
      name = "Shared"
    }
  }
  name = "TUN-Branch"
  tunnel_interface = "tunnel.1"
  auto_key = {
    ike_gateway = [
{
        name = panos_ike_gateway.ike_gw_ike_gw_branch_2b6fe510.name
      }
    ]
    ipsec_crypto_profile = panos_ipsec_crypto_profile.ipsec_profile_ipsec_default_964d437a.name
    proxy_id = [
{
        name = "proxy-1"
        local = "10.0.0.0/8"
        remote = "192.168.0.0/16"
        protocol = {
          number = 17
        }
      }
    ]
  }
}

