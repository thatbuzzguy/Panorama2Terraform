# External Dynamic Lists

resource "panos_external_dynamic_list" "threat_ips_25ccec46" {
  location = {
    shared = {}
  }
  name = "threat-ips"
  type = {
    ip = {
      url = "https://threat.example.com/list.txt"
      recurring = {
        hourly = {}
      }
      description = "Threat IP list"
    }
  }
}

resource "panos_external_dynamic_list" "bad_domains_73b2b3b4" {
  location = {
    shared = {}
  }
  name = "bad-domains"
  type = {
    domain = {
      url = "https://threat.example.com/domains.txt"
      exception_list = [ "example.com" ]
      expand_domain = true
      certificate_profile = "default"
      recurring = {
        weekly = {
          at = "6"
          day_of_week = "monday"
        }
      }
      description = "Bad domain list"
    }
  }
}

resource "panos_external_dynamic_list" "panw_url_list_2015fbf3" {
  location = {
    shared = {}
  }
  name = "panw-url-list"
  type = {
    predefined_url = {
      url = "https://url.paloaltonetworks.com/geturlversion.php"
      description = "Palo Alto Networks URL list"
    }
  }
}

