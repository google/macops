# Python virtual environment with PyObjC and tools

LUGGAGE:=/usr/local/share/luggage/luggage.make
include ${LUGGAGE}

PAYLOAD:=venv install-openssl install-python

# Set DISTURL to the location of your local downloaded copies
DISTURL:=https://foo.bar/baz/distfiles


PYTHON_BASE:=/Library/MegaCorpSupport/Python/2.7
PYTHON_BIN:=${PYTHON_BASE}/bin/python
OPENSSL_BASE:=/Library/MegaCorpSupport/openssl
VENV:=/Library/MegaCorpSupport/Python/Env

l_Library_MegaCorpSupport: l_Library
	@sudo mkdir -p ${WORK_D}/Library/MegaCorpSupport
	@sudo chown -R root:admin ${WORK_D}/Library/MegaCorpSupport
	@sudo chmod -R 755 ${WORK_D}/Library/MegaCorpSupport

l_Library_MegaCorpSupport_Python_Env: l_Library_MegaCorpSupport
	@sudo mkdir -p ${WORK_D}/${VENV}
	@sudo chown -R root:admin ${WORK_D}/${VENV}
	@sudo chmod -R 755 ${WORK_D}/${VENV}

# Main python virtual environment, build from custom python+openssl
build-venv: l_Library_MegaCorpSupport_Python_Env
	sudo ${PYTHON_BASE}/bin/virtualenv -p ${PYTHON_BIN} ${WORK_D}/${VENV}

# Update to latest pip
build-pip: build-venv
	sudo ${WORK_D}/${VENV}/bin/pip install --upgrade --no-cache-dir --index-url ${DISTURL}/python_venv/simple pip

# pyopenssl and xattr are used by munki
build-pyopenssl: build-venv
	sudo ${WORK_D}/${VENV}/bin/pip install --no-cache-dir --index-url ${DISTURL}/python_venv/simple pyopenssl

build-xattr: build-venv
	sudo ${WORK_D}/${VENV}/bin/pip install --no-cache-dir --index-url ${DISTURL}/python_venv/simple xattr

# Python-ObjectiveC bridge
build-pyobjc: build-venv
	sudo ${WORK_D}/${VENV}/bin/pip install --no-cache-dir --index-url ${DISTURL}/python_venv/simple pyobjc-core
	sudo ${WORK_D}/${VENV}/bin/pip install --no-cache-dir --index-url ${DISTURL}/python_venv/simple pyobjc

# For locally caching pip data in $DISTURL/python_venv
build-pip2pi: build-venv
	sudo ${WORK_D}/${VENV}/bin/pip install --no-cache-dir --index-url ${DISTURL}/python_venv/simple pip2pi

build-readline: build-venv
	sudo ${WORK_D}/${VENV}/bin/pip install --no-cache-dir --index-url ${DISTURL}/python_venv/simple readline

fix-path: build-venv build-pip build-pyopenssl build-xattr build-pyobjc build-pip2pi build-readline
	for f in $$(grep -Il ${WORK_D} ${WORK_D}/${VENV}/bin/*); \
		do sudo sed -i '' -e "s^${WORK_D}^^" $${f}; \
		done

venv: build-venv fix-path

${OPENSSL_BASE}:
	@echo "*****"
	@echo "Make sure ${@} on this machine is up to date!"
	@echo "*****"
	@false

install-openssl: ${OPENSSL_BASE} $(WORK_D) venv
	sudo rsync -avE --partial --progress --stats "${<}"/ "${WORK_D}/${<}"/
	sudo chown -R root:wheel "${WORK_D}/${<}"

install-python: ${PYTHON_BASE} ${WORK_D} venv
	sudo rsync -avE --partial --progress --stats "${<}"/ "${WORK_D}/${<}"/
	sudo chown -R root:wheel "${WORK_D}/${<}"


.PHONY:=build-venv build-pyopenssl build-xattr build-pyobjc build-pip2pi build-readline fix-path install-openssl