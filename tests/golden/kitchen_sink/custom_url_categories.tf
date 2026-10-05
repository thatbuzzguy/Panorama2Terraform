# Custom URL Categories

resource "panos_custom_url_category" "blocked_sites_589e0493" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "blocked-sites"
  type = "block"
  description = "Blocked websites"
  list = ["example.com", "bad.example.org"]
}

