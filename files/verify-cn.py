#!/usr/bin/env python3
"""Verify if a user's certificate should be permitted access."""


# Standard Python Libraries
import glob
import logging
import os
from pathlib import Path
import subprocess  # nosec
import sys
from typing import Optional

# Third-Party Libraries
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509 import load_pem_x509_certificate, ocsp
from cryptography.x509.ocsp import OCSPResponseStatus
from python_freeipa import ClientMeta
import requests
import yaml

# Return code constants
ALLOW_USER_CONNECTION_ATTEMPT = 0
CONTINUE_PROCESSING_CERTIFICATE_CHAIN = 0
DENY_USER_CONNECTION_ATTEMPT = 1

# Configuration constants
CONFIG_FILE = "verify-cn.yml"
ISSUER_CERTS_PATH = "/etc/openvpn/server/certs/DHS_CA4_*.pem"
KEYTAB_FILE = "/etc/krb5.keytab"
OCSP_URL = "http://ocsp.dimc.dhs.gov"
PEER_CERT_VARIABLE = "peer_cert"
CERT_PATH = "/etc/openvpn/server/peer_cert.pem"


def find_issuer_certificate():
    """Search for issuer certificates matching the pattern."""
    issuer_cert_files = glob.glob(ISSUER_CERTS_PATH)
    if not issuer_cert_files:
        raise FileNotFoundError("No issuer certificates found.")

    # Optionally, select the most recent certificate based on naming convention
    issuer_cert_files.sort()
    return issuer_cert_files[
        -1
    ]  # Return the last (most recent) file in the sorted list


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


def check_ocsp(issuer_path, cert_path, ocsp_url) -> bool:
    """Send an OCSP request to check the revocation status."""
    logging.debug("Load the issuer cert")

    # Load the issuer certificate
    with open(issuer_path, "rb") as issuer_file:
        issuer_cert_data = issuer_file.read()
    issuer = load_pem_x509_certificate(issuer_cert_data)

    logging.debug("Load the cert to check")

    # Load the certificate to check
    with open(cert_path, "rb") as cert_file:
        cert_data = cert_file.read()
    cert = load_pem_x509_certificate(cert_data)

    logging.debug("Create an OCSP request")

    # Create an OCSP request
    builder = ocsp.OCSPRequestBuilder()
    builder = builder.add_certificate(cert, issuer, hashes.SHA256())
    ocsp_req = builder.build()

    logging.debug("Send the OCSP request")

    # Send the OCSP request
    headers = {"Content-Type": "application/ocsp-request"}
    response = requests.post(
        ocsp_url,
        data=ocsp_req.public_bytes(serialization.Encoding.DER),
        headers=headers,
    )

    logging.debug("Parse the OCSP response")

    # Parse the OCSP response
    if response.status_code == 200:
        logging.debug("load der OCSP response")
        ocsp_resp = ocsp.load_der_ocsp_response(response.content)
        logging.debug("after load der OCSP response")
        if ocsp_resp.response_status == OCSPResponseStatus.SUCCESSFUL:
            logging.debug(
                "after if ocsp_resp.response_status == OCSPResponseStatus.Successful"
            )
            for single_response in ocsp_resp.responses:
                if single_response.serial_number == cert.serial_number:
                    logging.debug("OCSP Response Status: %s", ocsp_resp.response_status)
                    logging.debug(
                        "Certificate Status: %s", single_response.certificate_status
                    )
                    logging.debug("This Update: %s", single_response.this_update)
                    logging.debug("Next Update: %s", single_response.next_update)

                    # Check if the certificate status is not GOOD
                    if single_response.certificate_status != ocsp.OCSPCertStatus.GOOD:
                        return False
                    return True  # Certificate is GOOD
            return False  # Serial number not found in responses
        else:
            logging.debug("OCSP Response Status: %s", ocsp_resp.response_status)
            return False
    else:
        logging.debug(
            "Error contacting OCSP server, status code: %s", response.status_code
        )
        return False


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

    # Count is not the number of uids returned.  It is the number of responses.
    if response["count"] == 1:
        uid_count: int = len(response["result"][0]["uid"])
        if uid_count == 0:
            logging.critical("Unexpected response with no uids: %s", response)
            return False
        if uid_count == 1:
            # Extract username from response
            matched_uid = response["result"][0]["uid"][0]
            logging.info("Certificate matched uid: %s", matched_uid)
        else:  # uid_count > 1
            logging.warning(
                "Only 1 user should match a certificate.  Got %s matches...",
                uid_count,
            )
            for matched_uid in response["result"][0]["uid"]:
                logging.warning("Certificate matched uid: %s", matched_uid)
            return False
    else:  # response["count"] != 1
        # Not sure how this could happen.
        logging.critical("Unexpected response: %s", response)
        return False

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

    # Load client certificate path
    client_certificate_path = CERT_PATH

    if not client_certificate_path:
        # Without a certificate we cannot process any further
        return DENY_USER_CONNECTION_ATTEMPT

    try:
        issuer_cert_path = find_issuer_certificate()
        logging.debug("found issuer: %s", issuer_cert_path)
        cert_path = client_certificate_path
        logging.debug("client cert: %s", client_certificate_path)
        ocsp_url = OCSP_URL
        logging.debug("ocsp_url: %s", ocsp_url)
        if not check_ocsp(issuer_cert_path, cert_path, ocsp_url):
            return DENY_USER_CONNECTION_ATTEMPT
    except Exception as e:
        logging.debug("Error: %s", e)

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
