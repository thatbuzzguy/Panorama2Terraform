# Tags

resource "panos_administrative_tag" "env_prod_0d9ceea1" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "env-prod"
  color = "color4"
  comments = "Production environment"
}

resource "panos_administrative_tag" "web_370c996c" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "web"
  color = "color5"
}

