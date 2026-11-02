resource "panos_template" "fw_template_a729659e" {
  location = {
    panorama = {}
  }
  name = "FW-Template"
}

resource "panos_template_variable" "template_tag_74845f02" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "template-tag"
  description = "Template variable the golden set carries"
  type = {
    ip_netmask = "10.9.9.9/32"
  }
}

