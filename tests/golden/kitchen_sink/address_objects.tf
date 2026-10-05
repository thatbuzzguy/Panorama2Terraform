# Address Objects

resource "panos_address" "web_server_1_91d60c17" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Web-Server-1"
  description = "Web server"
  ip_netmask = "10.1.1.10/32"
  tags = ["Production", "Web"]
}

resource "panos_address" "web_range_5c41fc5b" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Web-Range"
  ip_range = "10.1.2.0-10.1.2.255"
}

resource "panos_address" "external_api_f8f09c31" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "External-API"
  description = "External API"
  fqdn = "api.example.com"
}

