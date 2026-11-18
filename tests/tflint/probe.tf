terraform {
  required_version = ">= 1.14"
  required_providers {
    panos = {
      source  = "PaloAltoNetworks/panos"
      version = "~> 2.0.14"
    }
    http = {
      source  = "hashicorp/http"
      version = "3.4.0"
    }
  }
}

variable "Bad_Name" {
  type = string
}

variable "ok_list" {
  type = list(string)
}

locals {
  legacy_index = var.ok_list.0
  interpolation_only = "${var.Bad_Name}"
  two_argument_lookup = lookup({ "a" = "b" }, "a")
  empty_list_check = var.ok_list == []
  duplicate_key = {
    first = "1"
    first = "2"
  }
}

resource "panos_address" "ok_name" {
  name = var.ok_list[0]
}

// a comment in the wrong shape
