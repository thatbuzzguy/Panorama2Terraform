# Address Objects

resource "panos_address_object" "web_server_1" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "Web-Server-1"
  description = "Web server"
  value = "10.1.1.10/32"
  tags = ["Production", "Web"]
}

resource "panos_address_object" "web_range" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "Web-Range"
  type = "ip-range"
  value = "10.1.2.0-10.1.2.255"
}

resource "panos_address_object" "external_api" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "External-API"
  description = "External API"
  type = "fqdn"
  value = "api.example.com"
}

