# ansible-role-openvpn #

[![GitHub Build Status](https://github.com/cisagov/ansible-role-openvpn/workflows/build/badge.svg)](https://github.com/cisagov/ansible-role-openvpn/actions)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/cisagov/ansible-role-openvpn.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/ansible-role-openvpn/alerts/)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/cisagov/ansible-role-openvpn.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/cisagov/ansible-role-openvpn/context:python)

Ansible role for installing and configuring an
[OpenVPN](https://openvpn.net) server.  This role also enables IPv4
NAT and iptables persistence.

Note that this role cannot perform every step necessary to set up NAT.
Once an instance is started up, one must determine the NAT interface
and add an iptables rule of the form

```console
iptables -t nat -A POSTROUTING -s <client_network_cidr> -o <interface_name> -j MASQUERADE
```

Next, one must save the iptables rules so they become persistent.
This entails the commands

```console
iptables-save > /etc/iptables/rules.v4
```

or

```console
iptables-save > /etc/sysconfig/iptables
```

depending on whether the OS family is Debian or RedHat, respectively.
These steps can be performed via cloud-init, as is done
[here](https://github.com/cisagov/openvpn-server-tf-module/blob/develop/cloudinit/create-iptables-rule-for-nat.sh).

## Requirements ##

None.

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
