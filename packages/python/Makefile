# Create a python virtual environment from upstream python source.
#
# Requires OpenSSL 1.0.x installation.
#
# Latest package files should be gpg verified before use

SHELL = /bin/bash -o pipefail

LUGGAGE:=/usr/local/share/luggage/luggage.make
include ${LUGGAGE}

PAYLOAD:=install-openssl install-python install-venv pack-script-postinstall pack-script-preinstall

# Set DISTURL to the location of your local downloaded copies
DISTURL:=https://foo.bar/baz/distfiles

PYTHON_DIST:=${DISTURL}/python/python-latest.tgz
PYTHON_BUILD:=/tmp/build-python
PYTHON_PATH:=/Library/MegaCorpSupport/Python/2.7
PYTHON_INSTALL:=${WORK_D}/${PYTHON_PATH}
PYTHON_INSTALL_BIN:=${PYTHON_INSTALL}/bin/python
ST_PATH:=${DISTURL}/python/setuptools-latest.tar.gz
PIP_PATH:=${DISTURL}/python/pip-latest.tar.gz

VE_PATH:=${DISTURL}/python/virtualenv-latest.tar.gz
VENV:=/Library/MegaCorpSupport/Python/Env
VENV_BIN:=${VENV}/bin/python
OPENSSL_BASE:=/Library/MegaCorpSupport/openssl


l_Library_MegaCorpSupport_Python2.7: l_Library_MegaCorpSupport
	@sudo mkdir -p ${WORK_D}/${PYTHON_PATH}
	@sudo chown -R root:admin ${WORK_D}/${PYTHON_PATH}
	@sudo chmod -R 755 ${WORK_D}/${PYTHON_PATH}

l_Library_MegaCorpSupport_Python_Env: l_Library_MegaCorpSupport
	@sudo mkdir -p ${WORK_D}/${VENV}
	@sudo chown -R root:admin ${WORK_D}/${VENV}
	@sudo chmod -R 755 ${WORK_D}/${VENV}

l_Library_MegaCorpSupport_OpenSSL: l_Library_MegaCorpSupport
	@sudo mkdir -p ${WORK_D}/${OPENSSL_BASE}
	@sudo chown -R root:admin ${WORK_D}${OPENSSL_BASE}
	@sudo chmod -R 755 ${WORK_D}${OPENSSL_BASE}

#
# OpenSSL should be already compiled and installed on the build machine.
#

/Library/MegaCorpSupport/openssl:
	@echo "*****"
	@echo "Make sure ${@} on this machine is up to date!"
	@echo "*****"
	@false

install-openssl: /Library/MegaCorpSupport/openssl l_Library_MegaCorpSupport_OpenSSL
	sudo rsync -avE --partial --progress --stats "${<}"/ "${WORK_D}/${<}"/
	sudo chown -R root:wheel "${WORK_D}/${<}"


#
# Compile python from source
#

# These *.ed and .patch files are from http://www.opensource.apple.com/source/python/python-89/2.7/fix/
# Local modifications to patch cleanly.
configure.ed:
	${CURL} -Lsf ${DISTURL}/python/${@} -o ${@}

setup.py.ed:
	${CURL} -Lsf ${DISTURL}/python/${@} -o ${@}

readline.c.ed:
	${CURL} -Lsf ${DISTURL}/python/${@} -o ${@}

setup.py.patch:
	${CURL} -Lsf ${DISTURL}/python/${@} -o ${@}

${PYTHON_BUILD}: configure.ed setup.py.ed setup.py.patch readline.c.ed
	/bin/mkdir -p ${@}
	${CURL} -Lsf "${PYTHON_DIST}" | ${TAR} -xzC "${@}" --strip-components=1
	/bin/ed - ${@}/configure < configure.ed
	/bin/ed - ${@}/setup.py < setup.py.ed
	/bin/ed - ${@}/Modules/readline.c < readline.c.ed
	patch ${PYTHON_BUILD}/setup.py < setup.py.patch

${PYTHON_BUILD}/configure: | ${PYTHON_BUILD}

${PYTHON_BUILD}/Makefile: | ${PYTHON_BUILD}/configure
	cd "${PYTHON_BUILD}" && \
	echo "_socket socketmodule.c timemodule.c" >> Modules/Setup.dist && \
	echo "_ssl _ssl.c -DUSE_SSL -I/Library/MegaCorpSupport/openssl/include -I/Library/MegaCorpSupport/openssl/include/openssl -L/Library/MegaCorpSupport/openssl/lib -lssl -lcrypto" >> Modules/Setup.dist && \
	./configure \
		--prefix="${PYTHON_INSTALL}" \
		--enable-ipv6 \
		--with-threads \
		--datarootdir="${PYTHON_INSTALL}/share" \
		--datadir="${PYTHON_INSTALL}/share"
	patch ${PYTHON_BUILD}/Lib/ssl.py < log_cert.patch
	patch ${PYTHON_BUILD}/Lib/logging/handlers.py < handlers.py.patch

${PYTHON_BUILD}/python.exe: | ${PYTHON_BUILD}/Makefile
	cd "${PYTHON_BUILD}" && \
	make -s -j 4

codesign-python: ${PYTHON_BUILD}/python.exe
	cp ${<} python
	# Codesigning step goes here
	codesign -s "Your Company, Inc." python
	mv python ${@}

python: codesign-python
	cp ${<} ${@}
	@if [ -f ${@} ]; then \
		if codesign -dvv ${@}; then \
			sudo cp ${@} ${PYTHON_BUILD}/python.exe ; \
			touch ${@} ; \
			touch -r ${@} ${<} codesign-python ; \
			sudo touch -r ${@} ${PYTHON_BUILD}/python.exe ; \
		else \
	  		echo "*****" ; \
			echo "Code signature for ${@} is invalid." ; \
			echo "*****" ; \
			rm ${@} ; \
			false ; \
		fi ; \
	else \
		echo "*****" ; \
		echo "Code signature for ${@} is invalid." ; \
		echo "*****" ; \
		false ; \
	fi

${PYTHON_INSTALL_BIN}: python | l_Library_MegaCorpSupport_Python2.7
	@if codesign -dvv ${PYTHON_BUILD}/python.exe; then \
		cd "${PYTHON_BUILD}" && \
		sudo make -s install ; \
	else \
		echo "Code signature is invalid." ; \
		false ; \
	fi

/tmp/setuptools/setup.py:
	/bin/mkdir -p $(dir ${@})
	${CURL} -Lsf ${ST_PATH} | ${TAR} xz -C $(dir ${@}) --strip-components=1

/tmp/pip/setup.py:
	/bin/mkdir -p $(dir ${@})
	${CURL} -Lsf ${PIP_PATH} | ${TAR} xz -C $(dir ${@}) --strip-components=1

/tmp/virtualenv/setup.py:
	/bin/mkdir -p $(dir ${@})
	${CURL} -Lsf ${VE_PATH} | ${TAR} xz -C $(dir ${@}) --strip-components=1

${PYTHON_INSTALL}/bin/easy_install: /tmp/setuptools/setup.py ${PYTHON_INSTALL_BIN}
	cd /tmp/setuptools && \
	sudo ${PYTHON_INSTALL_BIN} \
		setup.py install --prefix=${PYTHON_INSTALL}

${PYTHON_INSTALL}/bin/pip: /tmp/pip/setup.py ${PYTHON_INSTALL_BIN} ${PYTHON_INSTALL}/bin/easy_install
	cd /tmp/pip && \
	sudo ${PYTHON_INSTALL_BIN} \
		setup.py install --prefix=${PYTHON_INSTALL}

${PYTHON_INSTALL}/bin/virtualenv: /tmp/virtualenv/setup.py ${PYTHON_INSTALL_BIN} ${PYTHON_INSTALL}/bin/easy_install
	cd /tmp/virtualenv && \
	sudo ${PYTHON_INSTALL_BIN} \
		setup.py install --prefix=${PYTHON_INSTALL}

fix-path-python: ${PYTHON_INSTALL_BIN} ${PYTHON_INSTALL}/bin/easy_install ${PYTHON_INSTALL}/bin/pip ${PYTHON_INSTALL}/bin/virtualenv l_Library_MegaCorpSupport_Python2.7
	for f in $$(grep -Il ${WORK_D} ${WORK_D}/${PYTHON_PATH}/bin/*); \
		do sudo sed -i '' -e "s^${WORK_D}^^" $${f}; \
		done

install-python: fix-path-python


#
# Create python virtual environment
#

# Create a PyPi mirror with pip2pi first. E.g., to cache pyobjc:
# $ pip2pi --normalize-package-names $USER@$UBIQUITY_HOST:${DISTURL}/python pyobjc
pip-%: ${VENV_BIN}
	sudo MACOSX_DEPLOYMENT_TARGET=10.10 CC=clang LDFLAGS="-L${OPENSSL_BASE}/lib" CFLAGS="-I${OPENSSL_BASE}/include" \
		${WORK_D}/${VENV}/bin/pip install --no-cache-dir --index-url ${DISTURL}/python/simple \
		$(subst pip-,,${@})

# Main python virtual environment, build from custom python+openssl
build-venv: l_Library_MegaCorpSupport_Python_Env install-python
	@sudo ${PYTHON_INSTALL}/bin/virtualenv --always-copy -p ${PYTHON_INSTALL_BIN} ${WORK_D}/${VENV}

# Update to latest pip
build-pip: build-venv
	sudo ${WORK_D}/${VENV}/bin/pip install --upgrade --no-cache-dir --index-url ${DISTURL}/python_venv/simple pip

fix-path-venv: build-venv build-pip pip-pyopenssl pip-xattr pip-pyobjc-core pip-pyobjc pip-pip2pi pip-readline
	for f in $$(grep -Il ${WORK_D} ${WORK_D}/${VENV}/bin/*); \
		do sudo sed -i '' -e "s^${WORK_D}^^" $${f}; \
		done
	sudo sed -i '' -e "s^${WORK_D}^^" ${WORK_D}/${VENV}/lib/python2.7/orig-prefix.txt

install-venv: fix-path-venv

#
# Cleanup
#

clean: myclean

myclean:
	@sudo /bin/rm -rf ${PYTHON_BUILD}
	@/bin/rm -rf  ./*.ed setup.py.patch
	@sudo /bin/rm -rf /tmp/setuptools /tmp/pip /tmp/virtualenv
	@/bin/rm -f python python.zip codesign-python.zip

.PHONY:=install-python clean cleanwarn myclean install-openssl build-venv build-pip fix-path install-venv