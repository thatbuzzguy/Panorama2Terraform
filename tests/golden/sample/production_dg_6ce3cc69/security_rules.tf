# Security Policy Rules

# One iterated block per rule type per unit; the map is the printed form of the unit's rows,
# and the key order is the XML order inside the chain (F2.5).

locals {
  security_rules = {
    "0001_6ce3cc69" = {
      name = "Allow-Web-Traffic"
      action = "allow"
      applications = [ "web-browsing", "ssl" ]
      description = "Allow internal users to access web servers"
      destination_addresses = [ panos_address_group.web_servers_313224b7.name ]
      destination_zones = [ "DMZ" ]
      disabled = false
      log_end = true
      log_start = false
      profile_setting = null
      services = [ "application-default" ]
      source_addresses = [ panos_address.internal_network_8d9b5271.name ]
      source_zones = [ "Trust" ]
    }
    "0002_6ce3cc69" = {
      name = "Allow-DB-Access"
      action = "allow"
      applications = [ "mysql" ]
      description = "Allow web servers to access database"
      destination_addresses = [ panos_address_group.database_servers_b5ac06b1.name ]
      destination_zones = [ "Trust" ]
      disabled = false
      log_end = true
      log_start = false
      profile_setting = null
      services = [ panos_service.tcp_3306_2d089705.name ]
      source_addresses = [ panos_address_group.web_servers_313224b7.name ]
      source_zones = [ "DMZ" ]
    }
    "0003_6ce3cc69" = {
      name = "Block-Risky-Apps"
      action = "deny"
      applications = [ "torrent", "bittorrent" ]
      description = "Block risky applications"
      destination_addresses = [ "any" ]
      destination_zones = [ "any" ]
      disabled = false
      log_end = true
      log_start = false
      profile_setting = null
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

