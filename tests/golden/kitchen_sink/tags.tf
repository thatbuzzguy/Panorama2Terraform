# Tags

resource "panos_administrative_tag" "env_prod" {
  name = "env-prod"
  color = "green"
  comment = "Production environment"
}

resource "panos_administrative_tag" "web" {
  name = "web"
  color = "blue"
}

