# Address Groups

resource "panos_address_group" "web_servers" {
  name = "Web-Servers"
  description = "All web servers"
  static_value = ["Web-Server-1", "Web-Server-2"]
}

resource "panos_address_group" "dynamic_web" {
  name = "Dynamic-Web"
  dynamic_value = "\n            "
}

