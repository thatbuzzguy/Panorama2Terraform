# Routing-profile filter containers (F7.8)

resource "panos_filters_access_list_routing_profile" "acl_filter_1e6135f8" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "ACL-Filter"
  description = "deny the test host"
  type = {
    ipv4 = {
      ipv4_entries = [
        {
          action = "deny"
          name = "rule-1"
          source_address = {
            address = "10.0.0.0/8"
          }
        }
      ]
    }
  }
}

resource "panos_filters_as_path_access_list_routing_profile" "aspath_filter_ca3a5a50" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "ASPath-Filter"
  aspath_entries = [
    {
      action = "permit"
      aspath_regex = "^65.*1$"
      name = "rule-1"
    }
  ]
  description = "the four-byte ASNs"
}

resource "panos_filters_community_list_routing_profile" "community_filter_60c44efc" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "Community-Filter"
  description = "the lab communities"
  type = {
    regular = {
      regular_entries = [
        {
          action = "permit"
          communities = [ "100:200" ]
          name = "rule-1"
        }
      ]
    }
  }
}

resource "panos_filters_prefix_list_routing_profile" "prefix_filter_bd77f8a6" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "Prefix-Filter"
  description = "the lab ranges"
  type = {
    ipv4 = {
      ipv4_entries = [
        {
          action = "permit"
          name = "rule-1"
          prefix = {
            entry = {
              greater_than_or_equal = 24
              less_than_or_equal = 32
              network = "172.16.1.0/24"
            }
          }
        }
      ]
    }
  }
}

resource "panos_filters_bgp_route_map_routing_profile" "routemap_filter_1dfe434a" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "RouteMap-Filter"
  description = "the lab route map"
  route_map = [
    {
      action = "permit"
      match = {
        interface = "ethernet1/1"
        metric = 10
      }
      name = "1"
      set = {
        tag = 100
      }
    }
  ]
}

resource "panos_filters_route_maps_redistribution_routing_profile" "redist_filter_27b7dcd0" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "Redist-Filter"
  bgp = {
    ospf = {
      route_map = [
        {
          action = "permit"
          match = {
            interface = "ethernet1/1"
            metric = 10
          }
          name = "1"
          set = {
            tag = 100
          }
        }
      ]
    }
  }
  description = "the redistribution route map"
}

