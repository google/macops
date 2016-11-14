# boost

LUGGAGE:=/usr/local/share/luggage/luggage.make
include ${LUGGAGE}

PAYLOAD:=install-boost

SHELL = /bin/bash -o pipefail

VERSION:=1.59.0

# Set DISTURL to the location of your local downloaded copies
DISTURL:=https://foo.bar/baz/distfiles
# Path to python
PYTHON:=/usr/local/bin/python

BOOST_DIST:=${DISTURL}/boost/boost_${VERSION}.tar.bz2

${BUILD_D}/boostrap.sh: builddir
	${CURL} -Lsf "${BOOST_DIST}" | ${TAR} -jxC "$(dir ${@})" --strip-components=1

${BUILD_D}/b2: | ${BUILD_D}/boostrap.sh
	cd "${BUILD_D}" && \
		./bootstrap.sh --with-python=${PYTHON} \
			--without-libraries=mpi

install-boost: l_usr_local_lib l_usr_local_include | ${BUILD_D}/b2
	cd "${BUILD_D}" && \
		sudo ./b2 link=shared,static threading=multi \
			--prefix=${WORK_D}/usr/local -j ${NCPUS} \
			install
