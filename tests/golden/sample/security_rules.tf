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
      source_addresses = [ "Internal-Network" ]
      destination_zones = [ "DMZ" ]
      destination_addresses = [ "Web-Servers" ]
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
    where = "last"
  }

  rules = [
{
      name = "Allow-DB-Access"
      description = "Allow web servers to access database"
      source_zones = [ "DMZ" ]
      source_addresses = [ "Web-Servers" ]
      destination_zones = [ "Trust" ]
      destination_addresses = [ "Database-Servers" ]
      applications = [ "mysql" ]
      services = [ "TCP-3306" ]
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
    where = "last"
  }

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

