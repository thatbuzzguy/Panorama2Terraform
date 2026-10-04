# NAT Policy Rules

resource "panos_nat_policy_rules" "outbound_nat_a79e9d81" {
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
      name = "Outbound-NAT"
      description = "Outbound NAT for internal users"
      source_zones = [ "Trust" ]
      destination_zone = [ "Untrust" ]
      source_addresses = [ panos_address.internal_network_a80109b4.name ]
      destination_addresses = [ "any" ]
      service = "any"
      nat_type = "ipv4"
      source_translation = {
        dynamic_ip_and_port = {
          interface_address = {
            interface = "Untrust-Interface"
          }
        }
      }
    }
  ]
}

resource "panos_nat_policy_rules" "inbound_web_nat_4da8a1a9" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  position = {
    where = "after"
    directly = true
    pivot = "Outbound-NAT"
  }
  depends_on = [ panos_nat_policy_rules.outbound_nat_a79e9d81 ]

  rules = [
{
      name = "Inbound-Web-NAT"
      description = "Inbound NAT for web server"
      source_zones = [ "Untrust" ]
      destination_zone = [ "DMZ" ]
      source_addresses = [ "any" ]
      destination_addresses = [ "Public-IP" ]
      service = "service-http"
      destination_translation = {
        translated_address = "10.1.1.10"
        translated_port = 80
      }
    }
  ]
}

