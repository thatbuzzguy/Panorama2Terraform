# Address Objects

resource "panos_address" "web_server_1_427d7cfd" {
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

resource "panos_address" "web_range_5ebf95eb" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Web-Range"
  ip_range = "10.1.2.0-10.1.2.255"
}

resource "panos_address" "external_api_d1c4d1ef" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "External-API"
  description = "External API"
  fqdn = "api.example.com"
}

resource "panos_address" "web_wildcard_8892df2b" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Web-Wildcard"
  description = "Wildcard subnet"
  ip_wildcard = "10.1.3.*"
}

resource "panos_address" "masked_host_c44ef4c5" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Masked-Host"
  disable_override = "yes"
  ip_netmask = "10.1.4.5/32"
}

