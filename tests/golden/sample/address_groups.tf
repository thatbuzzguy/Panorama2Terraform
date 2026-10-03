# Address Groups

resource "panos_address_group" "web_servers" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Servers"
  description = "All web servers"
  static = ["Web-Server-1"]
}

resource "panos_address_group" "database_servers" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Database-Servers"
  static = ["DB-Server-1"]
}

resource "panos_address_group" "public_dns_servers" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Public-DNS-Servers"
  description = "Public DNS servers"
  static = ["Google-DNS-1", "Google-DNS-2"]
}

