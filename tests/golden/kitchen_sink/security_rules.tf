# Security Policy Rules

resource "panos_security_rule_group" "allow_web_traffic" {
  location {
    device_group {
      name = "Production-DG"
    }
  }
  position_keyword = "bottom"

  rule {
    name = "Allow-Web-Traffic"
    description = "Allow web traffic"
    source_zones = ["Trust"]
    source_addresses = ["Internal-Network"]
    destination_zones = ["DMZ"]
    destination_addresses = ["Web-Servers"]
    applications = ["web-browsing", "ssl"]
    services = ["application-default"]
    action = "allow"
    log_start = true
  }
}

resource "panos_security_rule_group" "block_risky_apps" {
  location {
    device_group {
      name = "Production-DG"
    }
  }
  position_keyword = "bottom"

  rule {
    name = "Block-Risky-Apps"
    source_zones = ["any"]
    source_addresses = ["any"]
    destination_zones = ["any"]
    destination_addresses = ["any"]
    applications = ["torrent"]
    services = ["application-default"]
    action = "deny"
    log_end = true
    disabled = true
  }
}

