# ansible-role-openvpn #

[![GitHub Build Status](https://github.com/cisagov/ansible-role-openvpn/workflows/build/badge.svg)](https://github.com/cisagov/ansible-role-openvpn/actions)
[![CodeQL](https://github.com/cisagov/ansible-role-openvpn/workflows/CodeQL/badge.svg)](https://github.com/cisagov/ansible-role-openvpn/actions/workflows/codeql-analysis.yml)

Ansible role for installing and configuring an
[OpenVPN](https://openvpn.net) server.  This role also enables IPv4
NAT via [ufw](https://wiki.ubuntu.com/UncomplicatedFirewall), although
*it does not set the default policy for routed packets in UFW, nor
does it create any rules to allow them through.*  This is because
there is no way to know a priori whether the user wants to deny all
routed packets and create rules to allow them through or just default
allow all routed packets; therefore, you must manage this part of the
ufw configuration outside of this Ansible role.

Note that this role cannot perform every step necessary to set up NAT.
Once an instance is started up, one must determine the NAT interface
and add a `nat` table configuration to the top of
`/etc/ufw/before.rules`:

```console
# nat Table rules
*nat
:POSTROUTING ACCEPT [0:0]

# Forward VPN client traffic
-A POSTROUTING -s <client_network_cidr> -o <interface_name> -j MASQUERADE

# don't delete the 'COMMIT' line or these nat table rules won't be processed
COMMIT
```

Finally, one must activate the `nat` table rules:

```console
ufw disable && ufw enable
```

These steps can be performed via cloud-init, as is done
[here](https://github.com/cisagov/openvpn-server-tf-module/blob/develop/cloudinit/create-iptables-rule-for-nat.sh).

## Requirements ##

None.

## Role Variables ##

None.

<!--
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| optional_variable | Describe its purpose. | `default_value` | No |
| required_variable | Describe its purpose. | n/a | Yes |
-->

## Dependencies ##

- [cisagov/ansible-role-pip](https://github.com/cisagov/ansible-role-pip)
- [cisagov/ansible-role-python](https://github.com/cisagov/ansible-role-python)
- [cisagov/ansible-role-ufw](https://github.com/cisagov/ansible-role-ufw)

## Installation ##

This role can be installed via the command:

```console
ansible-galaxy install --role-file path/to/requirements.yml
```

where `requirements.yml` looks like:

```yaml
---
- name: skeleton
  src: https://github.com/cisagov/skeleton-ansible-role
```

and may contain other roles as well.

For more information about installing Ansible roles via a YAML file,
please see [the `ansible-galaxy`
documentation](https://docs.ansible.com/ansible/latest/galaxy/user_guide.html#installing-multiple-roles-from-a-file).

## Example Playbook ##

Here's how to use it in a playbook:

```yaml
- hosts: all
  become: true
  become_method: sudo
  tasks:
    - name: Install and configure OpenVPN
      ansible.builtin.include_role:
        name: openvpn
```

## Contributing ##

We welcome contributions!  Please see [`CONTRIBUTING.md`](CONTRIBUTING.md) for
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

Mark Feldhousen - <mark.feldhousen@gwe.cisa.dhs.gov>
