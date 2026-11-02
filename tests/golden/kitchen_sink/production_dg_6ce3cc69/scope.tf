resource "panos_device_group" "production_dg_5c9acffe" {
  location = {
    panorama = {}
  }
  name = "Production-DG"
  description = "Production device group"
}

resource "panos_device_group_parent" "production_dg_fcf49f53" {
  location = {
    panorama = {}
  }
  device_group = "Production-DG"
  parent = "Corporate-DG"
}

