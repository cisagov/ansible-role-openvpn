#!/bin/bash

# Download the DHS certificate authority certificates as well as the
# intermediates, and root to which they are chained.  Each certificate
# is saved in its own file with a name based upon its x509 subject and
# expiration date.

set -o errexit
#set -o xtrace

mkdir -p certs && cd certs

# download the certificate bundle and massage into correct format
curl --insecure --silent https://pki.treas.gov/dhsca_fullpath.p7b | \
openssl pkcs7 -print_certs -inform der -out dhsca_fullpath.pem

# split chain of certificates into individual files
if [[ "$OSTYPE" == "darwin"* ]]; then
  # MacOS X
  split -a1 -p "subject" dhsca_fullpath.pem cert-
else
  # Assume linux-gnu
  csplit --prefix cert- --elide-empty-files --quiet dhsca_fullpath.pem /subject/ "{*}"
fi
# rename each file to subject_expiration.pem
for filename in cert-*; do
  [ -e "$filename" ] || continue
  # get the last element of the subject
  subject=$(openssl x509 -in "${filename}" -noout -subject | sed 's/ = /=/g' | awk -F= '{print $NF}' | tr ' ' '_')
  # get expiration year
  expire_year=$(openssl x509 -in "${filename}" -noout -enddate | awk '{print $4}')
  mv "${filename}" "${subject}_${expire_year}.pem"
done

# remove source file
rm dhsca_fullpath.pem

# calculate hashes and create symlinks for openssl
# adding brew path so it works in dev
PATH=$PATH:/usr/local/opt/openssl/bin c_rehash .
