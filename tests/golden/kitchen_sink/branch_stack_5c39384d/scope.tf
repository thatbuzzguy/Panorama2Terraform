resource "panos_template_stack" "branch_stack_a844b86b" {
  location = {
    panorama = {}
  }
  name = "Branch-Stack"
  description = "Template stack the golden set carries"
  templates = [ "FW-Template" ]
}

