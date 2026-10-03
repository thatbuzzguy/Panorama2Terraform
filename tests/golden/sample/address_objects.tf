# Address Objects

resource "panos_address_object" "web_server_1" {
  location {
    device_group {
      name = "Production-DG"
    }
  }
  name = "Web-Server-1"
  description = "Production Web Server"
  value = "10.1.1.10/32"
  tags = ["Production", "Web"]
}

resource "panos_address_object" "db_server_1" {
  location {
    device_group {
      name = "Production-DG"
    }
  }
  name = "DB-Server-1"
  description = "Production Database Server"
  value = "10.1.2.10/32"
}

resource "panos_address_object" "internal_network" {
  location {
    device_group {
      name = "Production-DG"
    }
  }
  name = "Internal-Network"
  description = "Internal RFC1918 Network"
  value = "10.0.0.0/8"
}

resource "panos_address_object" "dmz_network" {
  location {
    device_group {
      name = "Production-DG"
    }
  }
  name = "DMZ-Network"
  value = "172.16.1.0/24"
}

resource "panos_address_object" "external_api" {
  location {
    device_group {
      name = "Production-DG"
    }
  }
  name = "External-API"
  description = "External API Endpoint"
  type = "fqdn"
  value = "api.example.com"
}

resource "panos_address_object" "google_dns_1" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "Google-DNS-1"
  description = "Google Public DNS"
  value = "8.8.8.8/32"
}

resource "panos_address_object" "google_dns_2" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "Google-DNS-2"
  description = "Google Public DNS Secondary"
  value = "8.8.4.4/32"
}

