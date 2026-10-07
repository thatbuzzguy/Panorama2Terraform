# Address Objects

resource "panos_address" "web_server_1_9ec34c7e" {
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

resource "panos_address" "db_server_1_f5c5dbc2" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "DB-Server-1"
  description = "Production Database Server"
  ip_netmask = "10.1.2.10/32"
}

resource "panos_address" "internal_network_f1af75f3" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Internal-Network"
  description = "Internal RFC1918 Network"
  ip_netmask = "10.0.0.0/8"
}

resource "panos_address" "dmz_network_65d5bf8f" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "DMZ-Network"
  ip_netmask = "172.16.1.0/24"
}

resource "panos_address" "external_api_ab77cf66" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "External-API"
  description = "External API Endpoint"
  fqdn = "api.example.com"
}

resource "panos_address" "google_dns_1_25141d0f" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Google-DNS-1"
  description = "Google Public DNS"
  ip_netmask = "8.8.8.8/32"
}

resource "panos_address" "google_dns_2_0550b50a" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Google-DNS-2"
  description = "Google Public DNS Secondary"
  ip_netmask = "8.8.4.4/32"
}

