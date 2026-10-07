# Tags

resource "panos_administrative_tag" "env_prod_79f15cbc" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "env-prod"
  color = "color4"
  comments = "Production environment"
}

resource "panos_administrative_tag" "web_dc16804d" {
  location = {
    device_group = {
      name = "Shared"
    }
  }
  name = "web"
  color = "color5"
}

