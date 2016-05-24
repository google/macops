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

[deprecation_notifier][]
--------------------
A nagging utility intended to provoke users into doing major OS upgrades.

facter
------
A simple fact for tracking application usage.
A class for caching custom fact values.

[gmacpyutil][]
----------
Python modules with useful methods for managing and controlling Macintosh computers

[keychainminder][]
--------------
A SecurityAgentPlugin to keep the login keychain synchronized in enterprise environments.

[macdestroyer][]
------------
A package that attempts to render the target machine unbootable.

[momenu][]
------------
A menubar item with a plug-in architecture which allows admins to create anything that helps their fleet: from setting user preferences to reporting on machine status.

[planb][]
------
A host remediation program for managed Macs. Securely downloads disk images from your server and installs contained packages.

[run_it][]
------
A utility to measure the system impact of a process.


Related Projects
================

[Simian][] is an enterprise-class Mac OS X software deployment solution.

[Munki][] is a set of package management tools.

[Santa][] is a binary whitelisting/blacklisting solution for OS X. It features a kernel extension that monitors executions, and a GUI agent that alerts the user that a binary is blocked. Read more at the Santa repo: https://github.com/google/santa

[Cauliflower Vest][] is an end-to-end solution for automatically enabling and escrowing keys for FileVault 2.

[PyMacAdmin][] is another collection of Python utilities for Mac OS X system administration, the main piece of which is crankd

Contact
=======

We have a public mailing list at
[google-macops@googlegroups.com](https://groups.google.com/forum/#!forum/google-macops)

Disclaimer
==========

This is not an official Google product.

  [Simian]: https://github.com/google/simian
  [Munki]: https://github.com/munki/munki
  [Santa]: https://github.com/google/santa
  [Cauliflower Vest]: https://github.com/google/cauliflowervest
  [PyMacAdmin]:  https://github.com/MacSysadmin/pymacadmin
  [deprecation_notifier]: https://github.com/google/macops/tree/master/deprecation_notifier
  [gmacpyutil]: https://github.com/google/macops/tree/master/gmacpyutil
  [keychainminder]: https://github.com/google/macops-keychainminder
  [macdestroyer]: https://github.com/google/macops/tree/master/macdestroyer
  [momenu]: https://github.com/google/macops-MOMenu
  [planb]: https://github.com/google/macops-planb
  [run_it]: https://github.com/google/macops/tree/master/run_it
