# Decryption Policy Rules (F2.9: real v2 resources)

# One iterated block per rule type per unit; the map is the printed form of the unit's rows,
# and the key order is the XML order inside the chain (F2.5).

locals {
  decryption_rules = {
    "0001_6ce3cc69" = {
      name = "Decrypt-HTTPS"
      action = "decrypt"
      category = null
      description = "Decrypt HTTPS"
      destination_addresses = [ "any" ]
      destination_zones = [ "Untrust" ]
      disabled = false
      log_fail = false
      log_setting = "default"
      log_success = false
      profile = "ssl-decrypt-policy"
      services = [ "service-https" ]
      source_addresses = [ "Internal-Network" ]
      source_user = null
      source_zones = [ "Trust" ]
      type = {
        ssl_forward_proxy = {}
      }
    }
  }
}

resource "panos_decryption_policy_rules" "decryption_rules" {
  for_each = local.decryption_rules

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
      category = each.value.category
      description = each.value.description
      destination_addresses = each.value.destination_addresses
      destination_zones = each.value.destination_zones
      disabled = each.value.disabled
      log_fail = each.value.log_fail
      log_setting = each.value.log_setting
      log_success = each.value.log_success
      profile = each.value.profile
      services = each.value.services
      source_addresses = each.value.source_addresses
      source_user = each.value.source_user
      source_zones = each.value.source_zones
      type = each.value.type
    }
  ]
}

