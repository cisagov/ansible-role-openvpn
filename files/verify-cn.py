#!/usr/bin/env python3
"""Verify if a user's certificate should be permitted access."""


# Standard Python Libraries
import logging
import os
from pathlib import Path
import subprocess  # nosec
import sys
from typing import Optional

# Third-Party Libraries
from python_freeipa import ClientMeta
import yaml

# Return code constants
ALLOW_USER_CONNECTION_ATTEMPT = 0
CONTINUE_PROCESSING_CERTIFICATE_CHAIN = 0
DENY_USER_CONNECTION_ATTEMPT = 1

# Configuration constants
CONFIG_FILE = "verify-cn.yml"
KEYTAB_FILE = "/etc/krb5.keytab"
PEER_CERT_VARIABLE = "peer_cert"


def load_client_certificate() -> Optional[str]:
    """Read certificate data from file identified by environment variable."""
    # OpenVPN sends us the client's certificate though the peer_cert environment
    # variable.
    try:
        client_certificate_path: Path = Path(os.environ[PEER_CERT_VARIABLE])
    except KeyError:
        logging.critical(
            "OpenVPN did not set the 'peer_cert' environment variable."
            "Ensure 'tls-export-cert' option is set in OpenVPN configuration."
        )
        return None

    logging.debug("%s=%s", PEER_CERT_VARIABLE, client_certificate_path)

    if not client_certificate_path.exists():
        logging.critical(
            "Certificate file sent from OpenVPN was not found: %s",
            client_certificate_path,
        )
        return None

    with client_certificate_path.open() as f:
        cert_data: str = f.read()

    # Chop off header, footer, and remove new lines
    return "".join(cert_data.split("\n")[1:-2])


def kinit() -> None:
    """Obtain kerberos credentials for LDAP login."""
    logging.debug("Running kinit")
    proc = subprocess.run(["/usr/bin/kinit", "-k", "-t", KEYTAB_FILE])  # nosec
    logging.debug("kinit returned %s", proc.returncode)


def query_freeipa(client_certificate: str, realm: str, group: str) -> bool:
    """Determine if a user should be allowed to connect."""
    # Create the FreeIPA client
    ipa_client: ClientMeta = ClientMeta(dns_discovery=realm)

    # Login client using kerberos credentials
    logging.debug("Logging with kerberos to IPA server for realm: %s", realm)
    ipa_client.login_kerberos()

    logging.debug("Searching for user with matching certificate.")
    response = ipa_client.certmap_match(client_certificate)
    logging.debug("Received response from FreeIPA: %s", response)

    matched_uid: str

    if response["count"] == 0:
        logging.warning("No matching user found.")
        return False

    if response["count"] > 1:
        logging.warning(
            "More than 1 user matched certificate.  Count: %s.", response["count"]
        )
        for matched_uid in response["result"][0]["uid"]:
            logging.warning("Certificate matched uid: %s", matched_uid)
        return False

    # Extract username from response
    matched_uid = response["result"][0]["uid"][0]
    logging.info("Certificate matched uid: %s", matched_uid)

    # Get user data from FreeIPA
    logging.debug("Looking up user record for: %s", matched_uid)
    user = ipa_client.user_find(matched_uid)["result"][0]
    logging.debug("User record: %s", user)

    group_ok: bool
    account_enabled: bool
    account_not_preserved: bool

    # Check to see if user is a member of the group
    if group in user["memberof_group"]:
        logging.debug("%s is member of %s", matched_uid, group)
        group_ok = True
    else:
        logging.warning("%s is NOT a member of %s", matched_uid, group)
        group_ok = False

    # Check to see if the user's account is active
    if user["nsaccountlock"] is False:
        logging.debug("%s account is not locked.", matched_uid)
        account_enabled = True
    else:
        logging.warning("%s account IS LOCKED.", matched_uid)
        account_enabled = False

    # Check to see if the user's account is active
    if user["preserved"] is False:
        logging.debug("%s account is not preserved.", matched_uid)
        account_not_preserved = True
    else:
        logging.warning("%s account IS PRESERVED.", matched_uid)
        account_not_preserved = False

    # Pass judgement on the user
    if group_ok and account_enabled and account_not_preserved:
        logging.info("%s will be permitted access.", matched_uid)
        return True
    else:
        logging.warning("%s ACCESS DENIED.", matched_uid)
        return False


def main() -> int:
    """Check the arguments to see if the CN is valid."""
    _, depth_arg, x509cn = sys.argv
    depth: int = int(depth_arg)

    # load configuration
    config = yaml.safe_load(open(CONFIG_FILE))

    logging.basicConfig(
        format="VERIFY-CN: %(levelname)s %(message)s",
        level=config.get("log_level", "INFO"),
    )

    if depth > 0:
        # We are not at depth 0 (the client certificate)
        # Tell OpenVPN to continue processing the chain
        return CONTINUE_PROCESSING_CERTIFICATE_CHAIN

    # We are evaluating the user's certificate (depth 0)
    logging.debug("x509cn = %s", x509cn)

    # Load client certificate
    client_certificate = load_client_certificate()

    if not client_certificate:
        # Without a certificate we cannot process any further
        return DENY_USER_CONNECTION_ATTEMPT

    # Make sure we have valid kerberos credentials
    kinit()

    if query_freeipa(client_certificate, config["realm"], config["vpn_group"]):
        # The user was authorized by FreeIPA
        # Tell OpenVPN to allow the connection
        return ALLOW_USER_CONNECTION_ATTEMPT

    # The user was not authorized by FreeIPA
    # Tell OpenVPN to deny the connection
    return DENY_USER_CONNECTION_ATTEMPT


if __name__ == "__main__":
    sys.exit(main())
