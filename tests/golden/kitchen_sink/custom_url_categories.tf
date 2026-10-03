# Custom URL Categories

resource "panos_custom_url_category" "blocked_sites" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "blocked-sites"
  description = "Blocked websites"
  sites = ["example.com", "bad.example.org"]
}

