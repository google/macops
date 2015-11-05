# Makefile for OpenSSL 1.0.2
#
# Latest package files should be gpg verified before use

LUGGAGE:=/usr/local/share/luggage/luggage.make
include ${LUGGAGE}

PAYLOAD:=build-openssl

# Set DISTURL to the location of your local downloaded copies
DISTURL:=https://foo.bar/baz/distfiles
OPENSSL_DIST:=${DISTURL}/openssl/openssl-latest.tar.gz
OPENSSL_BUILD:=/tmp/build-openssl

l_Library_MegaCorpSupport: l_Library
	@sudo mkdir -p ${WORK_D}/Library/MegaCorpSupport
	@sudo chown -R root:admin ${WORK_D}/Library/MegaCorpSupport
	@sudo chmod -R 755 ${WORK_D}/Library/MegaCorpSupport

l_Library_MegaCorp_openssl: l_Library_MegaCorpSupport
	@sudo mkdir -p ${WORK_D}/Library/MegaCorpSupport/openssl
	@sudo chown -R root:admin ${WORK_D}/Library/MegaCorpSupport/openssl
	@sudo chmod -R 755 ${WORK_D}/Library/MegaCorpSupport/openssl

build-openssl: l_Library_MegaCorp_openssl
	/bin/mkdir "${OPENSSL_BUILD}"
	cd "${OPENSSL_BUILD}" && \
	${CURL} -Lsf "${OPENSSL_DIST}" | ${TAR} -xzC "${OPENSSL_BUILD}" --strip-components=1 && \
	perl ./Configure \
		--prefix="${WORK_D}/Library/MegaCorpSupport/openssl" \
		--openssldir="${WORK_D}/Library/MegaCorpSupport/openssl" \
		no-ssl2 no-ssl3 no-idea no-zlib no-comp shared \
		darwin64-x86_64-cc enable-ec_nistp_64_gcc_128 && \
	make -s depend && \
	sed -i.b -e "s%/tmp/the_luggage/openssl-[0-9]*/root%%" ./crypto/opensslconf.h \
	  ./tools/c_rehash && \
	make -s all && \
	sudo make install && \
	sudo install_name_tool -id \
		"/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" && \
	sudo install_name_tool -id \
		"/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" && \
	sudo install_name_tool -change \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" \
		"/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" \
		"${WORK_D}/Library/MegaCorpSupport/openssl/bin/openssl" && \
	sudo install_name_tool -change \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" \
		"/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" \
		"${WORK_D}/Library/MegaCorpSupport/openssl/bin/openssl" && \
	sudo install_name_tool -change \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" \
		"/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" && \
	sudo install_name_tool -change \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" \
		"/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib"

clean: myclean

myclean:
	@sudo /bin/rm -rf "${OPENSSL_BUILD}"
	@sudo /bin/rm -f openssl openssl-*.dmg
