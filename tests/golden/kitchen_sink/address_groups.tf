# Address Groups

resource "panos_address_group" "web_servers_18d3eea0" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "Web-Servers"
  description = "All web servers"
  static = [panos_address.web_server_1_91d60c17.name, "Web-Server-2"]
}

resource "panos_address_group" "dynamic_web_30a07597" {
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

