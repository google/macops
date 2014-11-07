Overview
========

Plan B is a remediation program for managed Macs. It is meant to be run to re-install other management software.

Features
------

  - Secure download of disk images from an Internet-facing server.
  - Installation of package files contained on the disk images.
  - Validation of server certificate against explicitly trusted certificate authorities only.
  - Support for client certificate authentication to ensure only trusted clients can access your server.
  - URL construction to download packages based on a client's configuration in a plist.
  - Extensive logging of presented certificate details for auditing and MITM detection.
  - No external dependencies; the compiled program is tiny and can be easily deployed.

Usage
------

First, create a server which will host disk images containing a single `.pkg` package file on each `.dmg`.

There is also a shell script included to help you generate a public-key infrastructure, if one is not already in place.

If your server has enabled client certificate authentication, first install the client certificate and private key to system keychain. You may first need to convert them to PKCS#12 format with something like, `openssl pkcs12 -export -in client.crt -inkey client.key -certfile ca.pem -out client.p12`. Otherwise, the program will perform server certificate validation only.

Compiling Plan B requires a modern version of Xcode, available from Apple's developer site.

* Check out the code with `git clone https://github.com/google/macops` and open the Xcode project with `open macops/planb/planb.xcodeproj`

By default, the program will try download `https://mac.internal.megacorp.com/pkgs/pkg1/package1-stable.dmg`, `.../pkg2/package2-stable.dmg` and so on.

* Edit `PBConnectionDelegate.m` and change `kConnectionDelegateHost` to the hostname of your server and `kConnectionDelegatePackageBase` to the path of the folder containing your disk images. By default, the program will use `https://mac.internal.megacorp.com/pkgs/`

* Edit `main.m` and change the `packages` array to match the names of your disk image names and their contained packages' receipt names. By default, the program will construct `pkg1/package1-stable.dmg` and forget the receipt for package `com.megacorp.package1` prior to re-installation, and so on.

* Edit `PBURLBuilder.m` and change the `kMachineInfo` to match a machine information plist, which may contain a `ConfigurationTrack` value, for example. This value is used to construct the disk image suffix, like `package1-stable.dmg`, `package1-testing.dmg` or `package1-unstable.dmg`. This is useful if you have machines on multiple configuration tracks.

* Edit `roots.pem` and change the contents to include a single or multiple PEM-encoded certificate authorities you wish to trust for server validation. By default, the program will use `GeoTrust Global CA`, the authority used to sign Google's intermediate certificates, however you should use the CA which has signed your server's certificate or your server's intermediate certificate.

* Build and run the program. It requires root privileges in order to install the software packages.

The resulting, compiled program will run on its own without any external dependencies.

It is recommended to create a simple script to determine the health of the machine, for example by checking the last successful run date of your primary management software, and running Plan B if the condition is not met. This script can then be started periodically as a system launch daemon.
