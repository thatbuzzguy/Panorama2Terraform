# Security Profile Groups

resource "panos_security_profile_group" "strict_profile_fced3373" {
  location = {
    shared = {}
  }
  name = "Strict-Profile"
  virus = ["AV-Default"]
  spyware = ["SPY-Default"]
  vulnerability = ["VULN-Default"]
  url_filtering = ["URL-Default"]
}

