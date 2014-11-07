Overview
========

These are some utilities, tools, and scripts for managing and tracking a fleet of Macintoshes in a corporate environment. We expect to use this primarily as a repository for small scripts or tools that don't warrant
a standalone project.

can\_haz\_image
---------------

Automation tool for creating images: [can\_haz\_image][]

crankd
------

Extras for crankd to log application usage: [crankd tools][]

facter
------

A simple fact for tracking application usage: [facter][]

planb
------
A host remediation program for managed Macs. Securely downloads disk images from your server and installs contained packages.

run_it
------
A utility to measure the system impact of a process. Code right here: https://github.com/google/macops/tree/master/run_it

deprecation_notifier
--------------------
A nagging utility intended to provoke users into doing major OS upgrades.

Related Projects
================

[Simian][] is an enterprise-class Mac OS X software deployment solution

[Munki][] is a set of package management tools

[Cauliflower Vest][] is an end-to-end solution for automatically
enabling and escrowing keys for !FileVault 2.

[PyMacAdmin][] is another collection of Python utilities for Mac OS X
system administration, the main piece of which is crankd

Contact
=======

We have a public mailing list at
[google-macops@googlegroups.com](https://groups.google.com/forum/#!forum/google-macops)

  [can\_haz\_image]: https://code.google.com/p/google-macops/source/browse/#svn%2Ftrunk%2Fcan_haz_image
  [crankd tools]: https://code.google.com/p/google-macops/source/browse/#svn%2Ftrunk%2Fcrankd
  [facter]: https://code.google.com/p/google-macops/source/browse/trunk/facter/apps.rb
  [Simian]: http://code.google.com/p/simian
  [Munki]: http://code.google.com/p/munki
  [Cauliflower Vest]: https://code.google.com/p/cauliflowervest
  [PyMacAdmin]: http://code.google.com/p/pymacadmin
