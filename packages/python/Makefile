# Makefile for Python 2.7.x.
#
# Requires OpenSSL 1.0.x installation.
#
# Latest package files should be gpg verified before use

LUGGAGE:=/usr/local/share/luggage/luggage.make
include ${LUGGAGE}

PAYLOAD:=install-python install-pip install-setuptools install-virtualenv \
	fix-path install-openssl pack-script-postinstall

# Set DISTURL to the location of your local downloaded copies
DISTURL:=https://foo.bar/baz/distfiles

PYTHON_PATH:=/Library/MegaCorpSupport/Python/2.7
PYTHON_DIST:=${DISTURL}/python/python-latest.tgz
PYTHON_BUILD:=/tmp/build-python
ST_PATH:=${DISTURL}/python/setuptools-latest.tar.gz
PIP_PATH:=${DISTURL}/python/pip-latest.tar.gz
VE_PATH:=${DISTURL}/python/virtualenv-latest.tar.gz


l_Library_MegaCorpSupport: l_Library
	@sudo mkdir -p ${WORK_D}/Library/MegaCorpSupport
	@sudo chown -R root:admin ${WORK_D}/MegaCorpSupport
	@sudo chmod -R 755 ${WORK_D}/MegaCorpSupport

l_Library_MegaCorpSupport_Python2.7: l_Library_MegaCorpSupport
	@sudo mkdir -p ${WORK_D}/${PYTHON_PATH}
	@sudo chown -R root:admin ${WORK_D}/${PYTHON_PATH}
	@sudo chmod -R 755 ${WORK_D}/${PYTHON_PATH}


# The *.ed files are from http://www.opensource.apple.com/source/python/python-89/2.7/fix/
# Fetch from Apple, and try to apply. If they don't apply cleanly,
# add "H" at the top of the .ed file, then try again.
# If there's an error, examine the change and see if the change is still necessary.

configure.ed:
	${CURL} -Lsf ${DISTURL}/python/${@} -o ${@}

setup.py.ed:
	${CURL} -Lsf ${DISTURL}/python/${@} -o ${@}

readline.c.ed:
	${CURL} -Lsf ${DISTURL}/python/${@} -o ${@}

${PYTHON_BUILD}: configure.ed setup.py.ed readline.c.ed
	/bin/mkdir -p ${@}
	${CURL} -Lsf "${PYTHON_DIST}" | ${TAR} -xzC "${@}" --strip-components=1
	/bin/ed - ${@}/configure < configure.ed
	/bin/ed - ${@}/setup.py < setup.py.ed
	/bin/ed - ${@}/Modules/readline.c < readline.c.ed

configure-python: ${PYTHON_BUILD} /Library/MegaCorpSupport/openssl
	cd "${PYTHON_BUILD}" && \
	echo "_socket socketmodule.c timemodule.c" >> Modules/Setup.dist && \
	echo "_ssl _ssl.c -DUSE_SSL -I/Library/MegaCorpSupport/openssl/include -I/Library/MegaCorpSupport/openssl/include/openssl -L/Library/MegaCorpSupport/openssl/lib -lssl -lcrypto" >> Modules/Setup.dist && \
	./configure \
		--prefix="${WORK_D}/${PYTHON_PATH}" \
		--enable-ipv6 \
		--with-system-expat \
		--with-threads \
		--datarootdir="${WORK_D}/${PYTHON_PATH}/share" \
		--datadir="${WORK_D}/${PYTHON_PATH}/share"
	patch ${PYTHON_BUILD}/Lib/ssl.py < log_cert.patch

build-python: configure-python
	cd "${PYTHON_BUILD}" && \
	make -s

install-python: build-python l_Library_MegaCorpSupport_Python2.7
	cd "${PYTHON_BUILD}" && sudo make -s install
	sudo install_name_tool -change \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" \
		"/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" \
		"${WORK_D}/${PYTHON_PATH}/bin/python2.7"
	sudo install_name_tool -change \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" \
		"/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" \
		"${WORK_D}/${PYTHON_PATH}/bin/python2.7"

/tmp/setuptools/setup.py:
	/bin/mkdir -p $(dir ${@})
	${CURL} -Lsf ${ST_PATH} | ${TAR} xz -C $(dir ${@}) --strip-components=1

/tmp/pip/setup.py:
	/bin/mkdir -p $(dir ${@})
	${CURL} -Lsf ${PIP_PATH} | ${TAR} xz -C $(dir ${@}) --strip-components=1

/tmp/virtualenv/setup.py:
	/bin/mkdir -p $(dir ${@})
	${CURL} -Lsf ${VE_PATH} | ${TAR} xz -C $(dir ${@}) --strip-components=1

install-setuptools: /tmp/setuptools/setup.py install-python
	cd /tmp/setuptools && \
	sudo ${WORK_D}/${PYTHON_PATH}/bin/python \
		setup.py install --prefix=${WORK_D}/${PYTHON_PATH}

install-pip: /tmp/pip/setup.py install-python install-setuptools
	cd /tmp/pip && \
	sudo ${WORK_D}/${PYTHON_PATH}/bin/python \
		setup.py install --prefix=${WORK_D}/${PYTHON_PATH}

install-virtualenv: /tmp/virtualenv/setup.py install-python install-setuptools
	cd /tmp/virtualenv && \
	sudo ${WORK_D}/${PYTHON_PATH}/bin/python \
		setup.py install --prefix=${WORK_D}/${PYTHON_PATH}

fix-path: install-virtualenv install-setuptools install-pip install-python
	for f in $$(grep -Il ${WORK_D} ${WORK_D}/${PYTHON_PATH}/bin/*); \
		do sudo sed -i '' -e "s^${WORK_D}^^" $${f}; \
		done

/Library/MegaCorpSupport/openssl:
	@echo "*****"
	@echo "Make sure ${@} on this machine is up to date!"
	@echo "*****"
	@false

install-openssl: /Library/MegaCorpSupport/openssl
	sudo rsync -avE --partial --progress --stats "${<}"/ "${WORK_D}/${<}"/
	sudo chown -R root:wheel "${WORK_D}/${<}"

clean: myclean

myclean:
	@sudo /bin/rm -rf "${PYTHON_BUILD}"
	@sudo /bin/rm -rf /tmp/setuptools /tmp/pip /tmp/virtualenv
	@/bin/rm -rf  ./*.ed ./*.egg-info build dist

.PHONY:=build-python configure-python install-openssl install-python clean myclean
