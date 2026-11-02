# Address Objects

resource "panos_address" "web_server_1_11f477f4" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Server-1"
  description = "Production Web Server"
  ip_netmask = "10.1.1.10/32"
  tags = ["Production", "Web"]
}

resource "panos_address" "db_server_1_bc6e29a2" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "DB-Server-1"
  description = "Production Database Server"
  ip_netmask = "10.1.2.10/32"
}

resource "panos_address" "internal_network_8d9b5271" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Internal-Network"
  description = "Internal RFC1918 Network"
  ip_netmask = "10.0.0.0/8"
}

resource "panos_address" "dmz_network_1c758f51" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "DMZ-Network"
  ip_netmask = "172.16.1.0/24"
}

resource "panos_address" "external_api_484f6ef6" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "External-API"
  description = "External API Endpoint"
  fqdn = "api.example.com"
}

