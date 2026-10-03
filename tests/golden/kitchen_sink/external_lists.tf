# External Dynamic Lists

resource "panos_external_list" "threat_ips" {
  name = "threat-ips"
  type = "ip"
  url = "https://threat.example.com/list.txt"
  recurring = "hourly"
  description = "Threat IP list"
}

