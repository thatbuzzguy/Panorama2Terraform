# Address Groups

resource "panos_address_group" "web_servers" {
  name = "Web-Servers"
  description = "All web servers"
  static_value = ["Web-Server-1"]
}

resource "panos_address_group" "database_servers" {
  name = "Database-Servers"
  static_value = ["DB-Server-1"]
}

resource "panos_address_group" "public_dns_servers" {
  name = "Public-DNS-Servers"
  description = "Public DNS servers"
  static_value = ["Google-DNS-1", "Google-DNS-2"]
}

