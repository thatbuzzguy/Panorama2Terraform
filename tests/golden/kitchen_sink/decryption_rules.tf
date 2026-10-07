# Decryption Policy Rules (F2.9: real v2 resources)
# One panos_decryption_policy_rules resource per rule; per-device-group
# chains preserve XML order (F2.5).

resource "panos_decryption_policy_rules" "decrypt_https_41e0f278" {
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
      name = "Decrypt-HTTPS"
      description = "Decrypt HTTPS"
      source_zones = [ "Trust" ]
      destination_zones = [ "Untrust" ]
      source_addresses = [ "Internal-Network" ]
      destination_addresses = [ "any" ]
      services = [ "service-https" ]
      action = "decrypt"
      type = {
        ssl_forward_proxy = {}
      }
      profile = "ssl-decrypt-policy"
      log_setting = "default"
    }
  ]
}

