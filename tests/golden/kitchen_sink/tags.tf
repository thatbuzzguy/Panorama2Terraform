# Tags

resource "panos_administrative_tag" "env_prod" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "env-prod"
  color = "green"
  comment = "Production environment"
}

resource "panos_administrative_tag" "web" {
  location {
    device_group {
      name = "Shared"
    }
  }
  name = "web"
  color = "blue"
}

