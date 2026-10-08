# Address Groups

resource "panos_address_group" "web_servers_526fa33a" {
  location = {
    shared = {}
  }
  name = "Web-Servers"
  description = "All web servers"
  static = [panos_address.web_server_1_df7a622a.name, "Web-Server-2"]
}

resource "panos_address_group" "dynamic_web_f2b0e073" {
  location = {
    shared = {}
  }
  name = "Dynamic-Web"
  dynamic = {
    dynamic = {
      filter = "tag == \"web\""
    }
  }
}

