# This script-only package does the following:
#
# If the machine's local disk is FV2-encrypted:
#   1) Adds a new user called fde_locked_user with a random password
#   2) Adds this user to the list of users who can unlock the disk
#   3) Removes any other user
#   4) Shuts down the machine
#
# If not:
#   1) Renames launchd to launchd_disabled - required to boot the machine
#   2) Shuts down the machine
#

# Update this with path to luggage.make in your environment.
LUGGAGE:=../luggage.make
include ${LUGGAGE}

PAYLOAD:=pack-script-postinstall
