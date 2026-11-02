# Address Groups

resource "panos_address_group" "public_dns_servers_ed42dba4" {
  location = {
    shared = {}
  }
  name = "Public-DNS-Servers"
  description = "Public DNS servers"
  static = [panos_address.google_dns_1_f95781c2.name, panos_address.google_dns_2_a64236dd.name]
}

