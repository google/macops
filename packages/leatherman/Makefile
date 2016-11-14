# leatherman

LUGGAGE:=/usr/local/share/luggage/luggage.make
include ${LUGGAGE}

PAYLOAD:=install-leatherman

SHELL = /bin/bash -o pipefail

VERSION:=0.7.4
# Set DISTURL to the location of your local downloaded copies
DISTURL:=https://foo.bar/baz/distfiles
# Path to python
PYTHON:=/usr/local/bin/python

LEATHERMAN_DIST:=${DISTURL}/leatherman/leatherman-${VERSION}.tar.gz


${BUILD_D}/CMakeLists.txt: builddir
	${CURL} -Lsf "${LEATHERMAN_DIST}" | ${TAR} -zxC "$(dir ${@})" --strip-components=1

${BUILD_D}/build: | ${BUILD_D}/CMakeLists.txt
	/bin/mkdir -p ${@}

${BUILD_D}/build/Makefile: | ${BUILD_D}/build
	cd "$(dir ${@})" && \
		cmake -DCMAKE_INSTALL_PREFIX=${WORK_D}/usr/local \
			  -DPYTHON_EXECUTABLE=${PYTHON} \
			  -DBOOSTROOT=/usr/local/ \
			  -DBOOST_STATIC=ON \
			  ..

${BUILD_D}/build/bin/leatherman_test: | ${BUILD_D}/build/Makefile
	cd "${BUILD_D}/build" && \
		cmake --build . -- -j ${NCPUS}

install-leatherman: ${BUILD_D}/build/bin/leatherman_test
	cd "${BUILD_D}/build" && \
		sudo make install