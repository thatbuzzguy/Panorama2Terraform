# NAT Policy Rules

resource "panos_nat_rule_group" "outbound_nat" {
  position_keyword = "bottom"

  rule {
    name = "Outbound-NAT"
    description = "Outbound NAT for internal users"
    original_packet {
      source_zones = ["Trust"]
      destination_zone = "Untrust"
      source_addresses = ["Internal-Network"]
      destination_addresses = ["any"]
      service = "any"
    }

    source_translation {
      type = "dynamic-ip-and-port"
      translated_addresses = ["Untrust-Interface"]
    }

  }
}

resource "panos_nat_rule_group" "inbound_web_nat" {
  position_keyword = "bottom"

  rule {
    name = "Inbound-Web-NAT"
    description = "Inbound NAT for web server"
    original_packet {
      source_zones = ["Untrust"]
      destination_zone = "DMZ"
      source_addresses = ["any"]
      destination_addresses = ["Public-IP"]
      service = "service-http"
    }

    destination_translation {
      translated_address = "10.1.1.10"
      translated_port = "80"
    }

  }
}

