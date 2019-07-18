#!/usr/bin/env python3
"""Verify a certificate Common Name should have access."""


import sys


def main():
    """Check the arguments to see if the CN is valid."""
    _, depth, x509cn = sys.argv
    depth = int(depth)
    print("VERIFY-CN", depth, ":", x509cn)
    if depth > 0:
        # We are not at depth 0 (the client certificate)
        # Tell OpenVPN to continue processing the chain
        return 0
    if "OU=DHS HQ" in x509cn:
        # Verify the user.  TODO: This is an example.
        # Tell OpenVPN to allow the connection
        return 0
    # User CN is not on the list
    # Tell OpenVPN to deny the connection
    return 1


if __name__ == "__main__":
    sys.exit(main())
