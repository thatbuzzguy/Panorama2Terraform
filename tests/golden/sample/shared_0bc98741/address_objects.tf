# Address Objects

resource "panos_address" "google_dns_1_f95781c2" {
  location = {
    shared = {}
  }
  name = "Google-DNS-1"
  description = "Google Public DNS"
  ip_netmask = "8.8.8.8/32"
}

resource "panos_address" "google_dns_2_a64236dd" {
  location = {
    shared = {}
  }
  name = "Google-DNS-2"
  description = "Google Public DNS Secondary"
  ip_netmask = "8.8.4.4/32"
}

