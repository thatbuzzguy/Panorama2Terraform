# Address Groups

resource "panos_address_group" "web_servers_1e4e8364" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Servers"
  description = "All web servers"
  static = [panos_address.web_server_1_9ec34c7e.name]
}

resource "panos_address_group" "database_servers_2cd620a9" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Database-Servers"
  static = [panos_address.db_server_1_f5c5dbc2.name]
}

resource "panos_address_group" "public_dns_servers_ae646c66" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Public-DNS-Servers"
  description = "Public DNS servers"
  static = [panos_address.google_dns_1_25141d0f.name, panos_address.google_dns_2_0550b50a.name]
}

