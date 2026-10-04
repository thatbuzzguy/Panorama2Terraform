# Address Groups

resource "panos_address_group" "web_servers" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Web-Servers"
  description = "All web servers"
  static = [panos_address.web_server_1.name, "Web-Server-2"]
}

resource "panos_address_group" "dynamic_web" {
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

