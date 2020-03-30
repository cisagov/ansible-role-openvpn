"""Module containing the tests for the default scenario."""

# Standard Python Libraries
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
