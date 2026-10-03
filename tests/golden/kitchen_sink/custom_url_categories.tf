# Custom URL Categories

resource "panos_custom_url_category" "blocked_sites" {
  name = "blocked-sites"
  description = "Blocked websites"
  sites = ["example.com", "bad.example.org"]
}

