#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail

# Download certificate authority certificates as well as the intermediates, and
# root to which they are chained.  Each certificate is saved in its own file
# with a name based upon its x509 subject and expiration date.

URLS=(
# Department of Energy
"https://enrollwebfed.managed.entrust.com/fssp/cda-docs/certs/EntrustRoot_to_EntrustSSP_2018_08_13.cer"
"https://enrollwebfed.managed.entrust.com/fssp/cda-docs/certs/FedRootCA2019.cer"
# Department of Homeland Security
"https://pki.treas.gov/dhsca_fullpath.p7b"
)

fetch(){
  source_file=$(mktemp)
  url="$*"

  if [[ $url =~ .cer$ ]]; then
    # Download the certificate and massage into correct format.
    curl --insecure --silent "${url}" --output "${source_file}"
    # .cer files can contain either PEM or DER formatted certificates.
    mime_type=$(file --mime-type --brief "${source_file}")
    if [[ $mime_type == "application/octet-stream" ]]; then
      # Convert certificate from DER format to PEM.
      openssl x509 -inform der -in "${source_file}" -out cert-a
    else
      # Certificate is already in PEM format.
      ln "${source_file}" cert-a
    fi
  elif [[ $url =~ .p7b$ ]]; then
    # Download the certificate bundle and massage into correct format.
    curl --insecure --silent "${url}" | \
    openssl pkcs7 -print_certs -inform der -out "${source_file}"

    # Split chain of certificates into individual files.
    if [[ "$OSTYPE" == "darwin"* ]]; then
      # MacOS X
      split -a1 -p "subject" "${source_file}" cert-
    else
      # Assume linux-gnu
      csplit --prefix cert- --elide-empty-files --quiet "${source_file}" /subject/ "{*}"
    fi
  fi

  # Rename each file to subject_expiration.pem
  for filename in cert-*; do
    [ -e "$filename" ] || continue
    # Get the last element of the subject.
    subject=$(openssl x509 -in "${filename}" -noout -subject | sed 's/ = /=/g' | awk -F= '{print $NF}' | tr ' ' '_')
    # Get expiration year.
    expire_year=$(openssl x509 -in "${filename}" -noout -enddate | awk '{print $4}')
    mv "${filename}" "${subject}_${expire_year}.pem"
  done

  # Clean up temporary source file.
  rm "${source_file}"
}

# Create the directory to store the processed certificates.
mkdir -p certs && cd certs

# Loop through CA URLs.
for url in "${URLS[@]}"; do
   fetch "$url"
done

# Calculate hashes and create symlinks for OpenSSL.
# Adding brew path so it works in development environments.
PATH=$PATH:/usr/local/opt/openssl/bin c_rehash .
