# Security Policy Rules

resource "panos_security_policy_rules" "allow_web_traffic" {
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
      name = "Allow-Web-Traffic"
      description = "Allow internal users to access web servers"
      source_zones = [ "Trust" ]
      source_addresses = [ panos_address.internal_network.name ]
      destination_zones = [ "DMZ" ]
      destination_addresses = [ panos_address_group.web_servers.name ]
      applications = [ "web-browsing", "ssl" ]
      services = [ "application-default" ]
      action = "allow"
      log_end = true
    }
  ]
}

resource "panos_security_policy_rules" "allow_db_access" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  position = {
    where = "after"
    directly = true
    pivot = "Allow-Web-Traffic"
  }
  depends_on = [ panos_security_policy_rules.allow_web_traffic ]

  rules = [
{
      name = "Allow-DB-Access"
      description = "Allow web servers to access database"
      source_zones = [ "DMZ" ]
      source_addresses = [ panos_address_group.web_servers.name ]
      destination_zones = [ "Trust" ]
      destination_addresses = [ panos_address_group.database_servers.name ]
      applications = [ "mysql" ]
      services = [ panos_service.tcp_3306.name ]
      action = "allow"
      log_end = true
    }
  ]
}

resource "panos_security_policy_rules" "block_risky_apps" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  position = {
    where = "after"
    directly = true
    pivot = "Allow-DB-Access"
  }
  depends_on = [ panos_security_policy_rules.allow_db_access ]

  rules = [
{
      name = "Block-Risky-Apps"
      description = "Block risky applications"
      source_zones = [ "any" ]
      source_addresses = [ "any" ]
      destination_zones = [ "any" ]
      destination_addresses = [ "any" ]
      applications = [ "torrent", "bittorrent" ]
      services = [ "application-default" ]
      action = "deny"
      log_end = true
    }
  ]
}

