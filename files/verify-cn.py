#!/usr/bin/env python3
"""Verify a user's certificate should be permitted access."""


# Standard Python Libraries
import logging
import subprocess  # nosec
import sys

# Third-Party Libraries
import dns.resolver
import ldap
import ldap.filter
import yaml

# Return code constants
ALLOW_USER_CONNECTION_ATTEMPT = 0
CONTINUE_PROCESSING_CERTIFICATE_CHAIN = 0
DENY_USER_CONNECTION_ATTEMPT = 1

# Configuration constants
KEYTAB_FILE = "/etc/krb5.keytab"
LOG_LEVEL = "INFO"


def kinit():
    """Obtain kerberos credentials for LDAP login."""
    logging.debug("Running kinit")
    proc = subprocess.run(["/usr/bin/kinit", "-k", "-t", KEYTAB_FILE])  # nosec
    logging.debug(f"kinit returned {proc.returncode}")


def lookup_ldap_uri(realm):
    """Generate the LDAP URI from DNS service records."""
    logging.debug(f"Looking up LDAP server for realm {realm}")
    resolver = dns.resolver.Resolver()
    answers = resolver.query(f"_ldap._tcp.{realm}", "SRV")
    hostname = answers[0].target.to_text()[:-1]  # chop off trailing period
    logging.debug(f"Found LDAP server record: {hostname}")
    return f"ldaps://{hostname}"


def query_ldap(dn, realm, vpn_group):
    """Query LDAP server and return True if user should be permitted."""
    # lookup LDAP server name
    ldap_uri = lookup_ldap_uri(realm)
    con = ldap.initialize(ldap_uri)
    con.sasl_gssapi_bind_s()
    # Convert realm into a base DN. e.g.; dc=cool,dc=cyber,dc=dhs,dc=gov
    realm_dn = ",".join([f"dc={x.lower()}" for x in realm.split(".")])
    base_dn = f"cn=users,cn=accounts,{realm_dn}"
    vpngroup_dn = f"cn={vpn_group},cn=groups,cn=accounts,{realm_dn}"
    logging.debug(f"Searching for user mapped to certificate: {dn}")
    escaped_dn = ldap.filter.escape_filter_chars(dn)
    rec = con.search_s(
        base_dn,
        ldap.SCOPE_SUBTREE,
        f"(ipaCertMapData=X509:<I>*<S>{escaped_dn})",
        attrlist=["memberOf"],
    )
    if len(rec) == 0:
        logging.warning("No matching certificate found in LDAP")
        logging.warning(f"Searched for: {dn}")
        return False

    if len(rec) > 1:
        logging.warning(f"More than 1 record found in LDAP.  Count: {len(rec)}.")
        return False

    user_dn, attribute_list = rec[0]
    logging.info(f"Found user in LDAP: {user_dn}")
    users_groups = attribute_list.get("memberOf")
    # Check to see if user is a member of the correct group
    permit_user = vpngroup_dn.encode("utf-8") in users_groups
    if permit_user:
        logging.info(f"User is member of {vpngroup_dn}")
    else:
        logging.warning(f"User IS NOT member of {vpngroup_dn}")
    return permit_user


def main():
    """Check the arguments to see if the CN is valid."""
    _, depth, x509cn = sys.argv
    depth = int(depth)
    logging.basicConfig(format="VERIFY-CN: %(levelname)s %(message)s", level=LOG_LEVEL)

    # load configuration
    config = yaml.safe_load(open("verify-cn.yml"))

    if depth > 0:
        # We are not at depth 0 (the client certificate)
        # Tell OpenVPN to continue processing the chain
        return CONTINUE_PROCESSING_CERTIFICATE_CHAIN

    # We are evaluating the user's certificate (depth 0)

    # Normalize the DN by parsing it and re-serializing
    normalized_dn = ldap.dn.dn2str(ldap.dn.str2dn(x509cn))

    # Make sure we have valid kerberos credentials
    kinit()

    if query_ldap(normalized_dn, config["realm"], config["vpn_group"]):
        # The user was authorized by LDAP
        # Tell OpenVPN to allow the connection
        return ALLOW_USER_CONNECTION_ATTEMPT

    # The user was not authorized by LDAP
    # Tell OpenVPN to deny the connection
    return DENY_USER_CONNECTION_ATTEMPT


if __name__ == "__main__":
    sys.exit(main())
