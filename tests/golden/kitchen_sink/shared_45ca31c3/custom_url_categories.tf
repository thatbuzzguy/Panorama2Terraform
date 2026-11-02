# Custom URL Categories

resource "panos_custom_url_category" "blocked_sites_0180a3cc" {
  location = {
    shared = {}
  }
  name = "blocked-sites"
  type = "block"
  description = "Blocked websites"
  list = ["example.com", "bad.example.org"]
}

