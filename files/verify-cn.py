#!/usr/bin/env python3
"""Verify a user's certificate should be permitted access."""


import sys

import ldap

ALLOW_USER_CONNECTION_ATTEMPT = 0
CONTINUE_PROCESSING_CERTIFICATE_CHAIN = 0
DENY_USER_CONNECTION_ATTEMPT = 1
LDAP_URI = "ldaps://ipa.cool.cyber.dhs.gov"
REALM = "COOL.CYBER.DHS.GOV"
VPN_GROUP = "vpnusers"


def log(msg):
    """Pring a log message that will show up in openvpn's logs."""
    print(f"VERIFY-CN {msg}")


def rev_dn_order(dn):
    """Reverse the order of RDNs in a DN.

    X.500 order: DC=com,DC=example,CN=users,CN=Certuser
    LDAP order:  CN=Certuser,CN=Users,DC=example,DC=com
    """
    # see: https://docs.pagure.org/SSSD.sssd/design_pages/matching_and_mapping_certificates.html#some-notes-about-dns
    return ldap.dn.dn2str(ldap.dn.str2dn(dn)[::-1])


def query_ldap(ldap_ordered_dn):
    """Query LDAP server and return True if user should be permitted."""
    con = ldap.initialize(LDAP_URI)
    con.sasl_gssapi_bind_s()
    # Convert realm into a base DN. e.g.; dc=cool,dc=cyber,dc=dhs,dc=gov
    realm_dn = ",".join([f"dc={x.lower()}" for x in REALM.split(".")])
    base_dn = f"cn=users,cn=accounts,{realm_dn}"
    vpngroup_dn = f"cn={VPN_GROUP},cn=groups,cn=accounts,{realm_dn}"
    rec = con.search_s(
        base_dn,
        ldap.SCOPE_SUBTREE,
        f"(ipaCertMapData=X509:<I>*<S>{ldap_ordered_dn})",
        attrlist=["memberOf"],
    )
    if len(rec) == 0:
        log("No matching certificate found in LDAP")
        return False

    if len(rec) > 1:
        log(f"More than 1 record matched.  Found: {len(rec)}.")
        return False

    user_dn, attribute_list = rec[0]
    log(f"Found user: {user_dn}")
    users_groups = attribute_list.get("memberOf")
    # Check to see if user is a member of the correct group
    return vpngroup_dn.encode("utf-8") in users_groups


def main():
    """Check the arguments to see if the CN is valid."""
    _, depth, x509cn = sys.argv
    depth = int(depth)
    # log(f"Depth:{depth} Subject:{x509cn}")

    if depth > 0:
        # We are not at depth 0 (the client certificate)
        # Tell OpenVPN to continue processing the chain
        return CONTINUE_PROCESSING_CERTIFICATE_CHAIN

    # We are evaluating the user's certificate (depth 0)
    ldap_ordered_dn = rev_dn_order(x509cn)
    log(f"LDAP-DN: {ldap_ordered_dn}")

    if query_ldap(ldap_ordered_dn):
        # The user was authorized by LDAP
        # Tell OpenVPN to allow the connection
        return ALLOW_USER_CONNECTION_ATTEMPT

    # The user was not authorized by LDAP
    # Tell OpenVPN to deny the connection
    return DENY_USER_CONNECTION_ATTEMPT


if __name__ == "__main__":
    sys.exit(main())
