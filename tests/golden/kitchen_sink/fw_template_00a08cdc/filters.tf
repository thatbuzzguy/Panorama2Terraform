# Routing-profile filter containers (F7.8)

resource "panos_filters_access_list_routing_profile" "acl_kitchen_b56ca7e4" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "ACL-Kitchen"
  description = "The kitchen sink access list"
  type = {
    ipv4 = {
      ipv4_entries = [
        {
          action = "deny"
          name = "kitchen-rule"
          source_address = {
            address = "10.9.9.9/32"
          }
        }
      ]
    }
  }
}

