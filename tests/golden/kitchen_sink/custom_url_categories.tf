# Custom URL Categories

resource "panos_custom_url_category" "blocked_sites_aa7fc2d9" {
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

