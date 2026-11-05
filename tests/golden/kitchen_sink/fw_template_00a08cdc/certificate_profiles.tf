# Certificate profiles (F7.14)

resource "panos_certificate_profile" "t_profile_bf27c284" {
  location = {
    template = {
      name = "FW-Template"
    }
  }
  name = "T-Profile"
  block_expired_certificate = true
  certificate = [
    {
      name = "Vsys-Cert"
      default_ocsp_url = "http://ocsp.example.com"
      ocsp_verify_certificate = "yes"
      template_name = "FW-Template"
    }
  ]
  certificate_status_timeout = 30
  domain = "template.example.com"
  ocsp_exclude_nonce = true
  use_crl = true
  use_ocsp = true
  username_field = {
    subject = "cn"
  }
}

