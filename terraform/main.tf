# Configure AWS
provider "aws" {
  region = "us-east-1"
}

module "iam_user" {
  source = "github.com/cisagov/molecule-packer-travisci-iam-user-tf-module"

  ssm_parameters = ["/openvpn/server/*"]
  user_name      = "test-ansible-role-openvpn"
  tags = {
    Team        = "CISA - Development"
    Application = "ansible-role-openvpn testing"
  }
}
