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


# The "type" string must correspond to a get*(section, option,...)
# method of the ConfigParser class.  Options for the "type" string
# are:
# - "", which results in a call to get() and returns a string value
# - "boolean" which results in a call to getboolean() and returns a
#   Boolean value
# - "int" which results in a call to getint() and returns an integer
#   value
# - "float" which results in a call to getfloat() and returns a
#   floating-point value
#
# See here for more details:
# https://docs.python.org/3/library/configparser.html#configparser.ConfigParser.get
@pytest.mark.parametrize(
    "section,option,value,value_type",
    [
        ("Unit", "After", "network.target multi-user.target cloud-final.service", ""),
        ("Service", "PrivateTmp", False, "boolean"),
    ],
)
def test_openvpn_unit_modifications(host, section, option, value, value_type):
    """Test that OpenVPN unit has been modified as expected."""
    cmd = host.run("systemctl cat openvpn-server@primary.service")
    assert cmd.rc == 0
    config = configparser.ConfigParser(strict=False)
    config.read_string(cmd.stdout)

    # Now we dynamically construct the method of ConfigParser that we
    # want to call depending on the value of "type".
    method_name = f"get{value_type}"
    assert hasattr(config, method_name)
    assert callable(method := getattr(config, method_name))
    assert method(section, option) == value
