# Address Objects

resource "panos_address" "web_server_1_df7a622a" {
  location = {
    shared = {}
  }
  name = "Web-Server-1"
  description = "Web server"
  ip_netmask = "10.1.1.10/32"
  tags = ["Production", "Web"]
}

resource "panos_address" "web_range_f9cb5402" {
  location = {
    shared = {}
  }
  name = "Web-Range"
  ip_range = "10.1.2.0-10.1.2.255"
}

resource "panos_address" "external_api_e826c30a" {
  location = {
    shared = {}
  }
  name = "External-API"
  description = "External API"
  fqdn = "api.example.com"
}

resource "panos_address" "web_wildcard_21fc2e66" {
  location = {
    shared = {}
  }
  name = "Web-Wildcard"
  description = "Wildcard subnet"
  ip_wildcard = "10.1.3.*"
}

resource "panos_address" "masked_host_f81cf9c5" {
  location = {
    shared = {}
  }
  name = "Masked-Host"
  disable_override = "yes"
  ip_netmask = "10.1.4.5/32"
}

resource "panos_address" "vsys_duplicate_a082f4ca" {
  location = {
    vsys = {
      name = "vsys1"
      ngfw_device = "fw-2.example.com"
    }
  }
  name = "Vsys-Duplicate"
  description = "vsys1 copy of a shared name"
  ip_netmask = "10.20.1.10/32"
}

resource "panos_address" "vsys_duplicate_e8ae6906" {
  location = {
    vsys = {
      name = "vsys2"
      ngfw_device = "fw-2.example.com"
    }
  }
  name = "Vsys-Duplicate"
  description = "vsys2 copy of a shared name"
  ip_netmask = "10.20.2.10/32"
}

