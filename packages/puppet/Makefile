# Puppet
# Create a puppet package inside a dmg from git bundles

# To create packaging.bundle:
# git clone git://github.com/puppetlabs/packaging && cd packaging
# git bundle create packaging.bundle HEAD --tags

# To create the puppet-4.5.2.bundle:
# git clone git://github.com/puppetlabs/puppet && cd puppet && git checkout 4.5.2
# git bundle create puppet-4.5.2.bundle HEAD --tags


TITLE:=puppet
BASE_VERSION:=4.5.2
BASE_NAME:=$(TITLE)-$(BASE_VERSION)
BASE_SRC:=/tmp/$(BASE_NAME)-src
# Local patch level; set to empty if there are no local patches
RC:=
DIST_URL:=http://foo.bar/baz/distfiles/
PACKAGING_BUNDLE:=packaging.bundle
PACKAGING_DIST_URL:=$(DIST_URL)/packaging/$(PACKAGING_BUNDLE)
PACKAGING_BUNDLE_LOCAL:=/tmp/$(PACKAGING_BUNDLE)
PUPPET_BUNDLE:=$(BASE_NAME).bundle
PUPPET_DIST_URL:=$(DIST_URL)/$(TITLE)/$(PUPPET_BUNDLE)
PUPPET_BUNDLE_LOCAL:=/tmp/$(PUPPET_BUNDLE)
ifeq ($(RC),)
	RELEASE:=$(BASE_NAME)
else
	RELEASE:=$(BASE_NAME)-$(RC)
endif

$(PUPPET_BUNDLE_LOCAL):
	curl -Lf $(PUPPET_DIST_URL) -o $(@)

$(PACKAGING_BUNDLE_LOCAL): $(PUPPET_BUNDLE_LOCAL)
	curl -Lf $(PACKAGING_DIST_URL) -o $(@)

$(BASE_SRC): $(PUPPET_BUNDLE_LOCAL) $(PACKAGING_BUNDLE_LOCAL)
	mkdir $(BASE_SRC)
	git clone $(PUPPET_BUNDLE_LOCAL) $(BASE_SRC)
	git clone $(PACKAGING_BUNDLE_LOCAL) $(BASE_SRC)/ext/packaging

# You should tweak the build_default.yaml.patch as needed; we patch
# the 'packager' so we can have a different pkgid
patch_build_defaults: build_defaults.yaml.patch | $(BASE_SRC)
	patch $(BASE_SRC)/ext/build_defaults.yaml < ${<}
	pushd $(BASE_SRC) && git commit -a -m $(@) && popd

# This patch ensures puppet is executed using the correct ruby interpreter
patch_apple_rake: apple.rake.patch | $(BASE_SRC)
	patch $(BASE_SRC)/ext/packaging/tasks/apple.rake < ${<}
	pushd $(BASE_SRC)/ext/packaging && git commit -a -m $(@) && popd

# Example local patch follows. This target should be added as a prereq for dmg
# patch_file_mapping: file_mapping.yaml.patch | $(BASE_SRC)
# 	# https://tickets.puppetlabs.com/browse/PUP-4714
# 	patch $(BASE_SRC)/ext/osx/file_mapping.yaml < ${<}
# 	pushd $(BASE_SRC) && git commit -a -m $(@) && popd

dmg: $(BASE_SRC) patch_build_defaults patch_apple_rake
	pushd $(BASE_SRC) && \
		rake package:apple && \
		popd && \
		cp $(BASE_SRC)/pkg/apple/$(BASE_NAME)*.dmg $(RELEASE).dmg

clean:
	sudo rm -rf $(BASE_SRC)
	rm -rf $(PUPPET_BUNDLE_LOCAL) $(PACKAGING_BUNDLE_LOCAL) $(RELEASE).dmg

.PHONY: dmg