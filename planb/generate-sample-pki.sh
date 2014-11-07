#!/bin/bash
#
# Sample public-key setup with CA, intermediate, server and client certificates.
# On OS X, default configuration in /System/Library/OpenSSL/openssl.cnf is used.
#
# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

readonly DEFAULT_MD="sha256"
readonly KEYSIZE="2048"
readonly OPENSSL="/usr/bin/openssl"

readonly CN_AUTHORITY="Megacorp Certificate Authority"
readonly CN_INTERMEDIATE="Megacorp Intermediate Authority"
readonly CN_SERVER="mac.internal.megacorp.com"
readonly CN_CLIENT="Megacorp Client #0001"

readonly COUNTRY="US"
readonly STATE="New York"
readonly LOCALITY="New York City"
readonly ORG="Megacorp Inc."
readonly UNIT="Megacorp Internal"

/bin/mkdir -p demoCA/newcerts
/usr/bin/touch demoCA/index.txt
echo 1000 > demoCA/serial

${OPENSSL} genrsa -out ca.key ${KEYSIZE}
${OPENSSL} req -new -x509 -days 365 \
  -${DEFAULT_MD} -extensions v3_ca \
  -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${ORG}/CN=${CN_AUTHORITY}" \
  -key ca.key -out ca.pem
echo -e "Created certificate authority: ca.pem"
${OPENSSL} x509 -text -nameopt multiline \
  -certopt no_sigdump -certopt no_pubkey -noout -in ca.pem

${OPENSSL} genrsa -out intermediate.key ${KEYSIZE}
${OPENSSL} req -new -${DEFAULT_MD} -new \
  -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${ORG}/CN=${CN_INTERMEDIATE}" \
  -key intermediate.key -out intermediate.csr
${OPENSSL} ca -extensions v3_ca -notext -md ${DEFAULT_MD} \
  -keyfile ca.key -cert ca.pem \
  -in intermediate.csr -out intermediate.pem
echo -e "Created intermediate authority: intermediate.pem, verifying ..."
${OPENSSL} verify -CAfile ca.pem intermediate.pem

/bin/cat ca.pem intermediate.pem > chain.pem
echo -e "Created chain: chain.pem"

${OPENSSL} genrsa -out server.key ${KEYSIZE}
${OPENSSL} req -new -${DEFAULT_MD} \
  -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${ORG}/CN=${CN_SERVER}" \
  -key server.key -out server.csr
${OPENSSL} ca -extensions usr_cert -notext -md ${DEFAULT_MD} \
  -keyfile intermediate.key -cert intermediate.pem \
  -in server.csr -out server.pem
echo -e "Created server certificate: server.pem"
${OPENSSL} x509 -text -nameopt multiline \
  -certopt no_sigdump -certopt no_pubkey -noout -in server.pem

echo 01 > intermediate.srl
echo """[ tls_client ]
basicConstraints = CA:FALSE
nsCertType = client
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth""" > client.cnf
${OPENSSL} genrsa -out client.key ${KEYSIZE}
${OPENSSL} req -new -${DEFAULT_MD} \
  -subj "/C=${COUNTRY}/ST=${STATE}/L=${LOCALITY}/O=${ORG}/CN=${CN_CLIENT}" \
  -key client.key -out client.csr
${OPENSSL} x509 -req -days 365 -extfile client.cnf -extensions tls_client \
  -CA intermediate.pem -CAkey intermediate.key \
  -in client.csr -out client.pem
echo -e "Created client certificate: client.pem"
${OPENSSL} x509 -text -nameopt multiline \
  -certopt no_sigdump -certopt no_pubkey -noout -in client.pem

