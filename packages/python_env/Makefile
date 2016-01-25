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
LDFLAGS:="-L${OPENSSL_BASE}/lib"
CFLAGS:="-I${OPENSSL_BASE}/include"


l_Library_MegaCorpSupport: l_Library
	@sudo mkdir -p ${WORK_D}/Library/MegaCorpSupport
	@sudo chown -R root:admin ${WORK_D}/Library/MegaCorpSupport
	@sudo chmod -R 755 ${WORK_D}/Library/MegaCorpSupport

l_Library_MegaCorpSupport_Python_Env: l_Library_MegaCorpSupport
	@sudo mkdir -p ${WORK_D}/${VENV}
	@sudo chown -R root:admin ${WORK_D}/${VENV}
	@sudo chmod -R 755 ${WORK_D}/${VENV}

pip-%: build-venv
	sudo CC=clang LDFLAGS="$(LDFLAGS)" CFLAGS="$(CFLAGS)" \
		${WORK_D}/${VENV}/bin/pip install --no-cache-dir --index-url ${DISTURL}/python_venv/simple \
		$(subst pip-,,${@})

# Instead of just pip-installing pyobjc-core and pyobjc, install the subpackages.
# The current upstream pybojc-core is busted since (apparently) 10.10.5 due to
# CoreLocation issue/deprecation.
# https://bitbucket.org/ronaldoussoren/pyobjc/issues/140/install-fail-on-osx-10105
pyobjc: \
	pip-pyobjc-framework-Accounts \
	pip-pyobjc-framework-AddressBook \
	pip-pyobjc-framework-AppleScriptKit \
	pip-pyobjc-framework-AppleScriptObjC \
	pip-pyobjc-framework-Automator \
	pip-pyobjc-framework-CFNetwork \
	pip-pyobjc-framework-Cocoa \
	pip-pyobjc-framework-Collaboration \
	pip-pyobjc-framework-CoreData \
	pip-pyobjc-framework-CoreText \
	pip-pyobjc-framework-DictionaryServices \
	pip-pyobjc-framework-EventKit \
	pip-pyobjc-framework-ExceptionHandling \
	pip-pyobjc-framework-FSEvents \
	pip-pyobjc-framework-InputMethodKit \
	pip-pyobjc-framework-InstallerPlugins \
	pip-pyobjc-framework-InstantMessage \
	pip-pyobjc-framework-LatentSemanticMapping \
	pip-pyobjc-framework-LaunchServices \
	pip-pyobjc-framework-OpenDirectory \
	pip-pyobjc-framework-PreferencePanes \
	pip-pyobjc-framework-PubSub \
	pip-pyobjc-framework-QTKit \
	pip-pyobjc-framework-Quartz \
	pip-pyobjc-framework-ScreenSaver \
	pip-pyobjc-framework-ScriptingBridge \
	pip-pyobjc-framework-SearchKit \
	pip-pyobjc-framework-ServiceManagement \
	pip-pyobjc-framework-Social \
	pip-pyobjc-framework-SyncServices \
	pip-pyobjc-framework-SystemConfiguration \
	pip-pyobjc-framework-WebKit

# Main python virtual environment, build from custom python+openssl
build-venv: l_Library_MegaCorpSupport_Python_Env
	sudo ${PYTHON_BASE}/bin/virtualenv -p ${PYTHON_BIN} ${WORK_D}/${VENV}

# Update to latest pip
build-pip: build-venv
	sudo ${WORK_D}/${VENV}/bin/pip install --upgrade --no-cache-dir --index-url ${DISTURL}/python_venv/simple pip

fix-path: build-venv build-pip pip-pyopenssl pip-xattr pyobjc pip-pip2pi pip-readline
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
