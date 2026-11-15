# Routing-profile filter containers (F7.8)

resource "panos_filters_access_list_routing_profile" "acl_filter_1e6135f8" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  description = "deny the test host"
  name = "ACL-Filter"
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

resource "panos_filters_access_list_routing_profile" "acl_filter_v6_d3ef6b7c" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  description = "deny the test host over ipv6"
  name = "ACL-Filter-v6"
  type = {
    ipv6 = {
      ipv6_entries = [
        {
          action = "deny"
          name = "rule-1"
          source_address = {
            address = "fd00::/8"
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
  aspath_entries = [
    {
      action = "permit"
      aspath_regex = "^65.*1$"
      name = "rule-1"
    }
  ]
  description = "the four-byte ASNs"
  name = "ASPath-Filter"
}

resource "panos_filters_community_list_routing_profile" "community_filter_60c44efc" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  description = "the lab communities"
  name = "Community-Filter"
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

resource "panos_filters_community_list_routing_profile" "community_filter_extended_734dd4e7" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  description = "the extended community pattern"
  name = "Community-Filter-Extended"
  type = {
    extended = {
      extended_entries = [
        {
          action = "permit"
          extended_community_regexes = [ "^100:.*$" ]
          name = "rule-1"
        }
      ]
    }
  }
}

resource "panos_filters_community_list_routing_profile" "community_filter_large_181a21f2" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  description = "the large community pattern"
  name = "Community-Filter-Large"
  type = {
    large = {
      large_entries = [
        {
          action = "permit"
          large_community_regexes = [ "1|2|3" ]
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
  description = "the lab ranges"
  name = "Prefix-Filter"
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

resource "panos_filters_prefix_list_routing_profile" "prefix_filter_v6_e7da7c05" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  description = "the lab ranges over ipv6"
  name = "Prefix-Filter-v6"
  type = {
    ipv6 = {
      ipv6_entries = [
        {
          action = "permit"
          name = "rule-1"
          prefix = {
            entry = {
              greater_than_or_equal = 64
              less_than_or_equal = 128
              network = "fd00:1::/64"
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
  description = "the lab route map"
  name = "RouteMap-Filter"
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
  name = "Redist-Filter"
}

resource "panos_filters_route_maps_redistribution_routing_profile" "redist_filter_set_9cc6b5fd" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  description = "the set leg of the redistribution route map"
  name = "Redist-Filter-Set"
  ospf = {
    bgp = {
      route_map = [
        {
          action = "permit"
          name = "1"
          set = {
            aspath_prepends = [ "65001" ]
            extended_communities = [ "100:200" ]
            large_communities = [ "1|2|3" ]
            regular_communities = [ "100" ]
          }
        }
      ]
    }
  }
}

