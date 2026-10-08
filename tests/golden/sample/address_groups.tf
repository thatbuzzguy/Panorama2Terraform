# Address Groups

resource "panos_address_group" "web_servers_313224b7" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Web-Servers"
  description = "All web servers"
  static = [panos_address.web_server_1_11f477f4.name]
}

resource "panos_address_group" "database_servers_b5ac06b1" {
  location = {
    device_group = {
      name = "Production-DG"
    }
  }
  name = "Database-Servers"
  static = [panos_address.db_server_1_bc6e29a2.name]
}

resource "panos_address_group" "public_dns_servers_ed42dba4" {
  location = {
    shared = {}
  }
  name = "Public-DNS-Servers"
  description = "Public DNS servers"
  static = [panos_address.google_dns_1_f95781c2.name, panos_address.google_dns_2_a64236dd.name]
}

