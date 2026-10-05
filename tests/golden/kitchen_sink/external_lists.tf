# External Dynamic Lists

resource "panos_external_dynamic_list" "threat_ips_3c4af1a2" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "threat-ips"
  type = {
    ip = {
      url = "https://threat.example.com/list.txt"
      recurring = {
        hourly = {}
      }
      description = "Threat IP list"
    }
  }
}

