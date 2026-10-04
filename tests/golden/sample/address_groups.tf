# Address Groups

resource "panos_address_group" "web_servers_395727b7" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Servers"
  description = "All web servers"
  static = [panos_address.web_server_1_a9a88aa6.name]
}

resource "panos_address_group" "database_servers_fd339f16" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Database-Servers"
  static = [panos_address.db_server_1_1bca8fe6.name]
}

resource "panos_address_group" "public_dns_servers_f7e57583" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Public-DNS-Servers"
  description = "Public DNS servers"
  static = [panos_address.google_dns_1_b1259a37.name, panos_address.google_dns_2_705c53df.name]
}

