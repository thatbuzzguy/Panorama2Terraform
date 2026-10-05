# Security Policy Rules

resource "panos_security_policy_rules" "allow_web_traffic_56c0cc46" {
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
      description = "Allow web traffic"
      source_zones = [ "Trust" ]
      source_addresses = [ "Internal-Network" ]
      destination_zones = [ "DMZ" ]
      destination_addresses = [ panos_address_group.web_servers_18d3eea0.name ]
      applications = [ "web-browsing", "ssl" ]
      services = [ "application-default" ]
      action = "allow"
      log_start = true
    }
  ]
}

resource "panos_security_policy_rules" "block_risky_apps_82d67173" {
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
  depends_on = [ panos_security_policy_rules.allow_web_traffic_56c0cc46 ]

  rules = [
{
      name = "Block-Risky-Apps"
      source_zones = [ "any" ]
      source_addresses = [ "any" ]
      destination_zones = [ "any" ]
      destination_addresses = [ "any" ]
      applications = [ "torrent" ]
      services = [ "application-default" ]
      action = "deny"
      log_end = true
      disabled = true
    }
  ]
}

