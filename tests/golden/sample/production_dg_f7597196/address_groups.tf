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

