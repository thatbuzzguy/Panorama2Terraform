# Tags

resource "panos_administrative_tag" "env_prod_5301b734" {
  location = {
    shared = {}
  }
  name = "env-prod"
  color = "color4"
  comments = "Production environment"
}

resource "panos_administrative_tag" "web_4d6aa528" {
  location = {
    shared = {}
  }
  name = "web"
  color = "color5"
}

