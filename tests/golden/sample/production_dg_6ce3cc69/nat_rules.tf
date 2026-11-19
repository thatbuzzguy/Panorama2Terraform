# NAT Policy Rules

# One iterated block per rule type per unit; the map is the printed form of the unit's rows,
# and the key order is the XML order inside the chain (F2.5).

locals {
  nat_rules = {
    "0001_6ce3cc69" = {
      name = "Outbound-NAT"
      description = "Outbound NAT for internal users"
      destination_addresses = [ "any" ]
      destination_translation = null
      destination_zone = [ "Untrust" ]
      disabled = false
      service = "any"
      source_addresses = [ panos_address.internal_network_8d9b5271.name ]
      source_translation = {
        dynamic_ip_and_port = {
          interface_address = {
            interface = "Untrust-Interface"
          }
        }
      }
      source_zones = [ "Trust" ]
    }
    "0002_6ce3cc69" = {
      name = "Inbound-Web-NAT"
      description = "Inbound NAT for web server"
      destination_addresses = [ "Public-IP" ]
      destination_translation = {
        translated_address = "10.1.1.10"
        translated_port = 80
      }
      destination_zone = [ "DMZ" ]
      disabled = false
      service = "service-http"
      source_addresses = [ "any" ]
      source_translation = null
      source_zones = [ "Untrust" ]
    }
  }
}

resource "panos_nat_policy_rules" "nat_rules" {
  for_each = local.nat_rules

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
      description = each.value.description
      destination_addresses = each.value.destination_addresses
      destination_translation = each.value.destination_translation
      destination_zone = each.value.destination_zone
      disabled = each.value.disabled
      service = each.value.service
      source_addresses = each.value.source_addresses
      source_translation = each.value.source_translation
      source_zones = each.value.source_zones
      nat_type = "ipv4"
    }
  ]
}

