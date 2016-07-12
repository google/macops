# Facter 3
#
# To build:
# 1) Install the boost and leatherman optional packages from pushy
# 2) Install these prerequisites:
#      CMake >= 3.2.2
#      yaml-cpp >= 0.5.1
#    a) Using homebrew: brew install cmake yaml-cpp
# 5) 'make dmg'


LUGGAGE:=/usr/local/share/luggage/luggage.make
include ${LUGGAGE}

# Set DISTURL to the location of your local downloaded copies
DISTURL:=https://foo.bar/baz/distfiles
# Path to python
PYTHON:=/usr/local/bin/python
# Path to ruby
RUBY:=/usr/local/bin/ruby
SITE_RUBY:=/usr/local/lib/ruby/site_ruby
RUBYLIB:=/usr/local/lib/libruby.dylib
# Path where current OpenSSL is installed
OPENSSL_BASE:=/Library/MegaCorpSupport/openssl


PAYLOAD:=install-facter

SHELL = /bin/bash -o pipefail

VERSION:=3.1.8

FACTER_DIST:=${DISTURL}/facter/facter-${VERSION}.tar.gz

#
# Compile facter
#

${BUILD_D}/CMakeLists.txt: builddir
	${CURL} -Lsf "${FACTER_DIST}" | ${TAR} -zxC "$(dir ${@})" --strip-components=1

CMakeLists.txt.done: CMakeLists.txt.patch | ${BUILD_D}/CMakeLists.txt
	patch ${|} < ${<}
	cp ${<} ${@}

${BUILD_D}/release: CMakeLists.txt.done
	/bin/mkdir -p ${@}

${BUILD_D}/release/Makefile: | ${BUILD_D}/release
	cd "$(dir ${@})" && \
		cmake -DOPENSSL_INCLUDE_DIR=${OPENSSL_BASE}/include \
			  -DWITHOUT_JRUBY=TRUE \
			  -DCMAKE_INSTALL_PREFIX=${WORK_D}/Library/MegaCorpSupport \
			  -DCMAKE_PREFIX_PATH=${WORK_D}/Library/MegaCorpSupport \
			  -DCMAKE_BUILD_WITH_INSTALL_RPATH=TRUE \
			  -DCMAKE_INSTALL_RPATH=/Library/MegaCorpSupport/lib \
			  -DRUBY_EXECUTABLE=${RUBY} \
			  -DFACTER_RUBY=${RUBYLIB} \
			  -DFACTER_PATH=/Library/MegaCorpSupport/bin \
			  -DRUBY_LIB_INSTALL=${WORK_D}/${SITE_RUBY} \
			  -DPYTHON_EXECUTABLE=${PYTHON} \
			  -DBOOSTROOT=/usr/local/ \
			  -DBOOST_STATIC=ON \
			  -DYAMLCPP_STATIC=ON \
			  ..

${BUILD_D}/release/bin/facter: | ${BUILD_D}/release/Makefile
	cd "${BUILD_D}/release" && \
		cmake --build . -- -j${NCPUS}

install-facter: facter
	cd "${BUILD_D}/release" && \
			sudo make install

clean: myclean

myclean:
	rm -f *.done