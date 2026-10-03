# Security Profile Groups

resource "panos_security_profile_group" "strict_profile" {
  name = "Strict-Profile"
  virus = "AV-Default"
  spyware = "SPY-Default"
  vulnerability = "VULN-Default"
  url_filtering = "URL-Default"
}

