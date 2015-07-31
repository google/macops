#!/bin/bash

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root" 1>&2
  exit 1
fi

python /Library/SecurityAgentPlugins/KeychainMinder.bundle/Contents/Resources/update_authdb.py --remove
rm -rf /Library/SecurityAgentPlguins/KeychainMinder.bundle
rm /Library/LaunchAgents/com.google.corp.keychainminder.plist
rm /Library/Preferences/com.google.corp.keychainminder.plist

user=$(/usr/bin/stat -f '%u' /dev/console)
[[ -z "$user" ]] && exit 0
/bin/launchctl asuser ${user} /bin/launchctl remove com.google.corp.keychainminder
