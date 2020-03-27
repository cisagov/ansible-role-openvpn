# ansible-role-openvpn #

[![GitHub Build Status](https://github.com/cisagov/ansible-role-openvpn/workflows/build/badge.svg)](https://github.com/cisagov/ansible-role-openvpn/actions)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/cisagov/ansible-role-openvpn.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/ansible-role-openvpn/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/cisagov/ansible-role-openvpn.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/ansible-role-openvpn/context:python)

Ansible role for installing and configuring an
[OpenVPN](https://openvpn.net) server.  This role also enables IPv4
NAT and iptables persistence.

## Pre-requisites ##

This project requires a build user to exist in AWS.  The accompanying terraform
code will create the user with the appropriate name and permissions.  This only
needs to be run once per project, per AWS account.  This user will also be used by
Travis-CI.

```console
cd terraform
terraform init --upgrade=true
terraform apply
```

Once the user is created you will need to update the `.travis.yml` file with the
new encrypted environment variables.

```console
terraform state show module.iam_user.aws_iam_access_key.key
```

Take the `id` and `secret` fields from the above command's output and [encrypt
and place in the `.travis.yml` file](https://docs.travis-ci.com/user/encryption-keys/).

Here is an example of encrypting the credentials for Travis:

```console
 travis encrypt --com --no-interactive "AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxx"
 travis encrypt --com --no-interactive "AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

## Requirements ##

## Role Variables ##

None.

## Dependencies ##

None.

## Example Playbook ##

Here's how to use it in a playbook:

```yaml
- hosts: all
  become: yes
  become_method: sudo
  roles:
    - openvpn
```

## Contributing ##

We welcome contributions!  Please see [here](CONTRIBUTING.md) for
details.

## License ##

This project is in the worldwide [public domain](LICENSE).

This project is in the public domain within the United States, and
copyright and related rights in the work worldwide are waived through
the [CC0 1.0 Universal public domain
dedication](https://creativecommons.org/publicdomain/zero/1.0/).

All contributions to this project will be released under the CC0
dedication. By submitting a pull request, you are agreeing to comply
with this waiver of copyright interest.

## Author Information ##

Mark Feldhousen - <mark.feldhousen@trio.dhs.gov>
