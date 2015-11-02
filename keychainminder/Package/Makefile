#
#  Package Makefile for KeychainMinder
#  Requires TheLuggage (github.com/unixorn/luggage) to be installed.
#

LUGGAGE:=/usr/local/share/luggage/luggage.make
include ${LUGGAGE}

TITLE:=KeychainMinder
REVERSE_DOMAIN:=com.google.corp

PACKAGE_VERSION:=$(shell defaults read $$PWD/../KeychainMinder/Info.plist CFBundleVersion)

PAYLOAD:=pack-SecurityAgentPlugin-KeychainMinder.bundle \
				 pack-Library-LaunchAgents-com.google.corp.keychainminder.plist \
				 pack-Library-LaunchDaemons-com.google.corp.keychainminderagent.plist \
				 pack-script-postinstall

KeychainMinder.bundle:
	@cd .. && xcodebuild -workspace KeychainMinder.xcworkspace -scheme KeychainMinder -configuration Archive OBJROOT=$(PWD)/../build SYMROOT=$(PWD)/../build DSTROOT=$(PWD)/../build
	@cp -R ../build/Release/KeychainMinder.bundle .

l_Library_Security: l_Library
	@sudo mkdir -p ${WORK_D}/Library/Security
	@sudo chown root:admin ${WORK_D}/Library/Security
	@sudo chmod 755 ${WORK_D}/Library/Security

l_Library_Security_SecurityAgentPlugins: l_Library_Security
	@sudo mkdir -p ${WORK_D}/Library/Security/SecurityAgentPlugins
	@sudo chown root:admin ${WORK_D}/Library/Security/SecurityAgentPlugins
	@sudo chmod 755 ${WORK_D}/Library/Security/SecurityAgentPlugins

pack-SecurityAgentPlugin-%: % l_Library_Security_SecurityAgentPlugins
	@sudo ${DITTO} --noqtn "${<}" ${WORK_D}/Library/Security/SecurityAgentPlugins/"${<}"
	@sudo chown -R root:wheel ${WORK_D}/Library/Security/SecurityAgentPlugins/"${<}"
	@sudo chmod 755 ${WORK_D}/Library/Security/SecurityAgentPlugins/"${<}"

clean: myclean

myclean:
	rm -rf ${TITLE}-*.pkg
	rm -rf KeychainMinder.bundle
	rm -rf ../build
