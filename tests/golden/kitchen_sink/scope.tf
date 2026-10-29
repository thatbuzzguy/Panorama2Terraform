resource "panos_device_group" "production_dg_5c9acffe" {
  location = {
    panorama = {}
  }
  name = "Production-DG"
  description = "Production device group"
}

resource "panos_device_group" "dev_dg_65548ef8" {
  location = {
    panorama = {}
  }
  name = "Dev-DG"
}

resource "panos_device_group_parent" "production_dg_fcf49f53" {
  location = {
    panorama = {}
  }
  device_group = "Production-DG"
  parent = "Corporate-DG"
}

resource "panos_template" "fw_template_a729659e" {
  location = {
    panorama = {}
  }
  name = "FW-Template"
}

resource "panos_template_stack" "branch_stack_a844b86b" {
  location = {
    panorama = {}
  }
  name = "Branch-Stack"
  description = "Template stack the golden set carries"
  templates = [ "FW-Template" ]
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

resource "panos_vsys" "template_vsys_bb284d90" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "template-vsys"
}

