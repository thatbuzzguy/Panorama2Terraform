# Security Policy Rules

# One iterated block per rule type per unit; the map is the printed form of the unit's rows,
# and the key order is the XML order inside the chain (F2.5).

locals {
  security_rules = {
    "0001_6ce3cc69" = {
      name = "Allow-Web-Traffic"
      action = "allow"
      applications = [ "web-browsing", "ssl" ]
      description = "Allow web traffic"
      destination_addresses = [ "Web-Servers" ]
      destination_zones = [ "DMZ" ]
      disabled = false
      log_end = false
      log_start = true
      profile_setting = null
      services = [ "application-default" ]
      source_addresses = [ "Internal-Network" ]
      source_zones = [ "Trust" ]
    }
    "0002_6ce3cc69" = {
      name = "Block-Risky-Apps"
      action = "deny"
      applications = [ "torrent" ]
      description = null
      destination_addresses = [ "any" ]
      destination_zones = [ "any" ]
      disabled = true
      log_end = true
      log_start = false
      profile_setting = {
        group = [ "Strict-Profile" ]
      }
      services = [ "application-default" ]
      source_addresses = [ "any" ]
      source_zones = [ "any" ]
    }
  }
}

resource "panos_security_policy_rules" "security_rules" {
  for_each = local.security_rules

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
      destination_zones = each.value.destination_zones
      disabled = each.value.disabled
      log_end = each.value.log_end
      log_start = each.value.log_start
      profile_setting = each.value.profile_setting
      services = each.value.services
      source_addresses = each.value.source_addresses
      source_zones = each.value.source_zones
    }
  ]
}

