#summary How to use can_haz_image.py.

= Introduction =

can haz image is a script that creates a bootable, fully loaded OS X image for you. This image can be put on your netboot server or you can put it on a Mac directly using Firewire/Thunderbolt and Target Disk Mode.


= Details =

*Prerequisites*

  * a webserver - any webserver you can reach from the machine used for building the image will do - running a local webserver on your Mac is fine too!
  * standard system Python - the script specifies Python 2.7 as interpreter, as it uses some functions that were not available in previous versions.
  * at least a package that creates a local user - this will work as a base package you can edit manually: https://code.google.com/p/instadmg/source/browse/#svn%2Ftrunk%2FAddOns%2FcreateUser
  * 30GB of free space


_Directory structure on the webserver_

Your webserver will need two directories, one for the base OS X image (with a specific name) and the other for the packages you intend to install:
(Using http://mywebserver/ as an example, $version is the version of Mac OS X you're building an image for, e.g. '10.8' or '10.9')
  * http://mywebserver/osx_base/$version-default-base.dmg
  * http://mywebserver/$version/base/
  * http://mywebserver/$version/thirdparty/


*Supported packages*
  * PKGs
  * DMGs with Applications in them


*Gotchas*
  * You need to build images from the same OS version you're building for!
  * OS X 10.9 may not be the same as OS X 10.9 - often for new hardware models Apple will ship a branched version of OS X - to ensure compatibility build new images from the hardware you are building for.
