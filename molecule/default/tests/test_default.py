"""Module containing the tests for the default scenario."""

# Standard Python Libraries
import configparser
import os

# Third-Party Libraries
import pytest
import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ["MOLECULE_INVENTORY_FILE"]
).get_hosts("all")


@pytest.mark.parametrize("setting", [{"net.ipv4.ip_forward": 1}])
def test_sysctl_settings(host, setting):
    """Test that sysctl values were set properly."""
    for key in setting:
        assert setting[key] == host.sysctl(key)


@pytest.mark.parametrize(
    "section,option,value",
    [
        ("Unit", "After", "network.target multi-user.target cloud-final.service"),
        ("Service", "PrivateTmp", "False"),
    ],
)
def test_openvpn_unit_modifications(host, section, option, value):
    """Test that OpenVPN unit has been modified as expected."""
    cmd = host.run("systemctl cat openvpn-server@primary.service")
    assert cmd.rc == 0
    config = configparser.ConfigParser(strict=False)
    config.read_string(cmd.stdout)
    assert config[section][option]
    assert config[section][option] == value
