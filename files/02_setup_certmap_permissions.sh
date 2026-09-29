#!/usr/bin/env bash

set -o nounset
set -o errexit
set -o pipefail

# This script is intended to set up the permissions necessary for this
# host to check client PIV certificates against the certmap data
# stored in FreeIPA.  It creates these permissions if they do not already
# exist, then assigns them to this host if necessary.
#
# These variables must be set before running this script:
#
# hostname: The hostname of this IPA client (e.g. client.example.com).

# The file installed by cloud-init that contains the value for the
# above variable.
freeipa_vars_file=/var/lib/cloud/instance/freeipa-vars.sh

# Load above variable from a file installed by cloud-init:
if [[ -f "$freeipa_vars_file" ]]; then
  # Disable this warning since the file is only available at runtime
  # on the server.
  #
  # shellcheck disable=SC1090
  source "$freeipa_vars_file"
else
  echo "FreeIPA variables file does not exist: $freeipa_vars_file"
  echo "It should have been created by cloud-init at boot."
  exit 254
fi

# Create the necessary permissions to query against the certificate
# mapping data stored in FreeIPA if they do not already exist.
function create_and_assign_permissions_if_needed {
  # Since the role may already be created and/or the privilege already
  # assigned, an error code may be returned, so we need to temporarily
  # turn off errexit for these commands.
  set +o errexit
  ipa role-add "Cert Mapping Automation" --desc="Allows hosts to match client certificates"
  ipa role-add-privilege "Cert Mapping Automation" --privileges="Certificate Identity Mapping Administrators"
  # hostname is defined in the FreeIPA variables file that is
  # sourced toward the top of this file.  Hence we can ignore the
  # "undefined variable" warning from shellcheck.
  #
  # shellcheck disable=SC2154
  ipa role-add-member "Cert Mapping Automation" --hosts="$hostname"
  set -o errexit
}

create_and_assign_permissions_if_needed
