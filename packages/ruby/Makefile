# Makefile for Ruby 2.0.x
#
# Requires OpenSSL 1.0.x installation.
#
# Latest package files should be sha256 verified before use

LUGGAGE:=/usr/local/share/luggage/luggage.make
include ${LUGGAGE}

PAYLOAD:=install-ruby fix-path install-openssl create-symlinks install-gems

RUBY_PATH:=/Library/MegaCorpSupport/Ruby
RUBY_DIST:=${DISTURL}/ruby/ruby-latest.tar.gz
SQLITE3_DIST:=${DISTURL}/ruby/sqlite3-1.3.10.gem
RUBY_BUILD:=/tmp/build-ruby

l_Library_MegaCorpSupport: l_Library
	@sudo mkdir -p ${WORK_D}/Library/MegaCorpSupport
	@sudo chown -R root:admin ${WORK_D}/MegaCorpSupport
	@sudo chmod -R 755 ${WORK_D}/MegaCorpSupport

l_Library_MegaCorpSupport_Ruby: l_Library_MegaCorpSupport
	@sudo mkdir -p ${WORK_D}/${RUBY_PATH}
	@sudo chown -R root:admin ${WORK_D}/${RUBY_PATH}
	@sudo chmod -R 755 ${WORK_D}/${RUBY_PATH}

${RUBY_BUILD}:
	/bin/mkdir -p ${@}
	set -o pipefail && ${CURL} -Lsf "${RUBY_DIST}" | ${TAR} -xzC "${@}" --strip-components=1

configure-ruby: ${RUBY_BUILD}
	cd "${RUBY_BUILD}" && \
	./configure --prefix=${WORK_D}/Library/MegaCorpSupport/Ruby \
		--with-opt-dir=/Library/MegaCorpSupport/openssl \
		--enable-load-relative

build-ruby: configure-ruby
	cd "${RUBY_BUILD}" && \
	make

install-ruby: build-ruby l_Library_MegaCorpSupport_Ruby
	cd "${RUBY_BUILD}" && sudo make install
	sudo install_name_tool -change \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" \
		"/Library/MegaCorpSupport/openssl/lib/libssl.1.0.0.dylib" \
		"${WORK_D}/${RUBY_PATH}/bin/ruby"
	sudo install_name_tool -change \
		"${WORK_D}/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" \
		"/Library/MegaCorpSupport/openssl/lib/libcrypto.1.0.0.dylib" \
		"${WORK_D}/${RUBY_PATH}/bin/ruby"

sqlite3-1.3.10.gem:
	${CURL} -Lsf ${SQLITE3_DIST} -o ${@}

install-sqlite3: install-ruby sqlite3-1.3.10.gem
	sudo ${WORK_D}/${RUBY_PATH}/bin/gem install sqlite3-1.3.10.gem

install-gems: install-sqlite3

create-symlinks: install-ruby
	sudo mkdir -p ${WORK_D}/Library/MegaCorpSupport/bin
	sudo ln -s ${RUBY_PATH}/bin/ruby ${WORK_D}/Library/MegaCorpSupport/bin/ruby
	sudo ln -s ${RUBY_PATH}/bin/irb ${WORK_D}/Library/MegaCorpSupport/bin/irb
	sudo ln -s ${RUBY_PATH}/bin/gem ${WORK_D}/Library/MegaCorpSupport/bin/gem
	sudo ln -s ${RUBY_PATH}/bin/erb ${WORK_D}/Library/MegaCorpSupport/bin/erb

fix-path: install-ruby
	for f in $$(grep -Il ${WORK_D} ${WORK_D}/${RUBY_PATH}/bin/*); \
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
	@sudo /bin/rm -rf "${RUBY_BUILD}" sqlite3-1.3.10.gem

.PHONY:=myclean configure-ruby build-ruby install-ruby install-openssl install-gems install-sqlite3
