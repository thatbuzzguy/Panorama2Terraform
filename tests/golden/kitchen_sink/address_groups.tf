# Address Groups

resource "panos_address_group" "web_servers_1d0d5e7d" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Web-Servers"
  description = "All web servers"
  static = [panos_address.web_server_1_427d7cfd.name, "Web-Server-2"]
}

resource "panos_address_group" "dynamic_web_36a918e3" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Dynamic-Web"
  dynamic = {
    dynamic = {
      filter = "tag == \"web\""
    }
  }
}

