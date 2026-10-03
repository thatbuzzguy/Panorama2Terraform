# Address Objects

resource "panos_address" "web_server_1" {
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

resource "panos_address" "db_server_1" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "DB-Server-1"
  description = "Production Database Server"
  ip_netmask = "10.1.2.10/32"
}

resource "panos_address" "internal_network" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Internal-Network"
  description = "Internal RFC1918 Network"
  ip_netmask = "10.0.0.0/8"
}

resource "panos_address" "dmz_network" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "DMZ-Network"
  ip_netmask = "172.16.1.0/24"
}

resource "panos_address" "external_api" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "External-API"
  description = "External API Endpoint"
  fqdn = "api.example.com"
}

resource "panos_address" "google_dns_1" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Google-DNS-1"
  description = "Google Public DNS"
  ip_netmask = "8.8.8.8/32"
}

resource "panos_address" "google_dns_2" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Google-DNS-2"
  description = "Google Public DNS Secondary"
  ip_netmask = "8.8.4.4/32"
}

