# Address Groups

resource "panos_address_group" "web_servers" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Servers"
  description = "All web servers"
  static = [panos_address.web_server_1.name]
}

resource "panos_address_group" "database_servers" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Database-Servers"
  static = [panos_address.db_server_1.name]
}

resource "panos_address_group" "public_dns_servers" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Public-DNS-Servers"
  description = "Public DNS servers"
  static = [panos_address.google_dns_1.name, panos_address.google_dns_2.name]
}

