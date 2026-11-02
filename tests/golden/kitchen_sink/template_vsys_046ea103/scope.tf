resource "panos_vsys" "template_vsys_bb284d90" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "template-vsys"
}

