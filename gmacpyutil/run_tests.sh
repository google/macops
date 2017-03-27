#!/bin/bash

sudo easy_install pip
sudo pip install ez_setup
sudo pip install -q pyyaml
sudo pip install mock
sudo pip install mox
sudo pip install google_apputils
sudo pip install pyopenssl
sudo pip install pyobjc-core pyobjc-framework-CoreWLAN pyobjc-framework-Cocoa pyobjc-framework-SystemConfiguration
python -m unittest discover -s gmacpyutil -p '*_test.py' -t .
