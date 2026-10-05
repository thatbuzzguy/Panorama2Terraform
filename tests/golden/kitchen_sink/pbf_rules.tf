# Policy-Based Forwarding Rules (F2.9: real v2 resources)
# One panos_pbf_policy_rules resource per rule; per-device-group
# chains preserve XML order (F2.5).

resource "panos_pbf_policy_rules" "pbf_forward_6758164c" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  position = {
    where = "last"
  }

  rules = [
{
      name = "PBF-Forward"
      description = "Forward to next hop"
      from = {
        zone = [ "vsys1" ]
      }
      source_addresses = [ "Internal-Network" ]
      destination_addresses = [ "any" ]
      applications = [ "any" ]
      services = [ "any" ]
      action = {
        forward = {
          nexthop = {
            ip_address = "10.0.0.1"
          }
          egress_interface = "ethernet1/1"
          monitor = {
            ip_address = "10.1.1.1"
            profile = "PM-Branch"
            disable_if_unreachable = true
          }
        }
      }
      enforce_symmetric_return = {
        enabled = true
      }
    }
  ]
}

resource "panos_pbf_policy_rules" "pbf_discard_b20dafec" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  position = {
    where = "after"
    directly = true
    pivot = "PBF-Forward"
  }
  depends_on = [ panos_pbf_policy_rules.pbf_forward_6758164c ]

  rules = [
{
      name = "PBF-Discard"
      from = {
        zone = [ "vsys1" ]
      }
      action = {
        discard = {}
      }
    }
  ]
}

