Overview
========

macdestroyer is a simple payload-only package that attempts to render the target machine unbootable. It works best on 10.8 systems with FileVault 2 encrypted volumes.

Mechanisms
----------

On 10.8, if the machine's local disk is FV2-encrypted:

1. Adds a new user called `fde_locked_user` with a random password
2. Adds this user to the list of users who can unlock the disk
3. Removes all other users
4. Shuts down the machine


Otherwise:

1. Renames `launchd` to `launchd_disabled`
2. Shuts down the machine


The 10.8/encrypted case is best when using some sort of FileVault key escrow mechanism, like [Cauliflower Vest](https://github.com/google/cauliflowervest), as this allows for recovery of the disk's data for, e.g., legal discovery.

The non-FV2 case is, obviously, merely an annoyance to anyone knowledgeable with OS X.

Customization
-------------

In the `postflight`, the `LOCK_USER_NAME` and `LOCK_USER_HINT` could be informative:
`LOCK_USER_HINT="Contact Helpdesk"`

The included `Makefile` is a simple [luggage](https://github.com/unixorn/luggage) recipe. You'll have to update the `LUGGAGE` variable to point to the location of `luggage.make` in your build environment.
