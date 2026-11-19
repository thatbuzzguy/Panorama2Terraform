# Policy-Based Forwarding Rules (F2.9: real v2 resources)

# One iterated block per rule type per unit; the map is the printed form of the unit's rows,
# and the key order is the XML order inside the chain (F2.5).

locals {
  pbf_rules = {
    "0001_6ce3cc69" = {
      name = "PBF-Forward"
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
      applications = [ "any" ]
      description = "Forward to next hop"
      destination_addresses = [ "any" ]
      disabled = false
      enforce_symmetric_return = {
        enabled = true
      }
      schedule = null
      services = [ "any" ]
      source_addresses = [ "Internal-Network" ]
      source_users = null
      from = {
        zone = [ "vsys1" ]
      }
    }
    "0002_6ce3cc69" = {
      name = "PBF-Discard"
      action = {
        discard = {}
      }
      applications = null
      description = null
      destination_addresses = null
      disabled = false
      enforce_symmetric_return = null
      schedule = null
      services = null
      source_addresses = null
      source_users = null
      from = {
        zone = [ "vsys1" ]
      }
    }
  }
}

resource "panos_pbf_policy_rules" "pbf_rules" {
  for_each = local.pbf_rules

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
      name = each.value.name
      action = each.value.action
      applications = each.value.applications
      description = each.value.description
      destination_addresses = each.value.destination_addresses
      disabled = each.value.disabled
      enforce_symmetric_return = each.value.enforce_symmetric_return
      schedule = each.value.schedule
      services = each.value.services
      source_addresses = each.value.source_addresses
      source_users = each.value.source_users
      from = each.value.from
    }
  ]
}

