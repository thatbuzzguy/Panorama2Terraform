# Security Policy Rules

resource "panos_security_rule_group" "allow_web_traffic" {
  position_keyword = "bottom"

  rule {
    name = "Allow-Web-Traffic"
    description = "Allow internal users to access web servers"
    source_zones = ["Trust"]
    source_addresses = ["Internal-Network"]
    destination_zones = ["DMZ"]
    destination_addresses = ["Web-Servers"]
    applications = ["web-browsing", "ssl"]
    services = ["application-default"]
    action = "allow"
    log_end = true
  }
}

resource "panos_security_rule_group" "allow_db_access" {
  position_keyword = "bottom"

  rule {
    name = "Allow-DB-Access"
    description = "Allow web servers to access database"
    source_zones = ["DMZ"]
    source_addresses = ["Web-Servers"]
    destination_zones = ["Trust"]
    destination_addresses = ["Database-Servers"]
    applications = ["mysql"]
    services = ["TCP-3306"]
    action = "allow"
    log_end = true
  }
}

resource "panos_security_rule_group" "block_risky_apps" {
  position_keyword = "bottom"

  rule {
    name = "Block-Risky-Apps"
    description = "Block risky applications"
    source_zones = ["any"]
    source_addresses = ["any"]
    destination_zones = ["any"]
    destination_addresses = ["any"]
    applications = ["torrent", "bittorrent"]
    services = ["application-default"]
    action = "deny"
    log_end = true
  }
}

