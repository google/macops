Overview [![Build Status](https://travis-ci.org/google/macops.png?branch=master)](https://travis-ci.org/google/macops)
========

These are some utilities, tools, and scripts for managing and tracking a fleet of Macintoshes in a corporate environment. We expect to use this primarily as a repository for small scripts or tools that don't warrant
a standalone project.

can\_haz\_image
---------------
Automation tool for creating images

crankd
------
Extras for crankd to log application usage

deprecation_notifier
--------------------
A nagging utility intended to provoke users into doing major OS upgrades.

facter
------
A simple fact for tracking application usage

gmacpyutil
----------
Python modules with useful methods for managing and controlling Macintosh computers

macdestroyer
------------
A package that attempts to render the target machine unbootable.

planb
------
A host remediation program for managed Macs. Securely downloads disk images from your server and installs contained packages.

run_it
------
A utility to measure the system impact of a process.


Related Projects
================

[Simian][] is an enterprise-class Mac OS X software deployment solution

[Munki][] is a set of package management tools

[Santa][] is a binary whitelisting/blacklisting solution for OS X. It features a kernel extension that monitors executions, and a GUI agent that alerts the user that a binary is blocked. Read more at the Santa repo: https://github.com/google/santa

[Cauliflower Vest][] is an end-to-end solution for automatically
enabling and escrowing keys for !FileVault 2.

[PyMacAdmin][] is another collection of Python utilities for Mac OS X
system administration, the main piece of which is crankd

Contact
=======

We have a public mailing list at
[google-macops@googlegroups.com](https://groups.google.com/forum/#!forum/google-macops)

Disclaimer
==========

This is not an official Google product.

  [Simian]: http://code.google.com/p/simian
  [Munki]: http://code.google.com/p/munki
  [Santa]: https://github.com/google/santa
  [Cauliflower Vest]: https://code.google.com/p/cauliflowervest
  [PyMacAdmin]: http://code.google.com/p/pymacadmin
