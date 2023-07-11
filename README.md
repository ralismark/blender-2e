# blender-2e

This is the second edition of my discord bot, that I worked on in 2019.

```
$ ls -l
total 199
-rwxr-xr-x 1 temmie users  5186 Oct 28  2019 admin.py
drwxr-xr-x 3 temmie users    12 Oct 28  2019 base
-rw-r--r-- 1 temmie users   266 Dec  8  2019 blender.service
-rwxr-xr-x 1 temmie users  9669 Apr 17  2019 clacks.py
-rwxr-xr-x 1 temmie users  5586 Oct  4  2019 client.py
-rw-r--r-- 1 temmie users  1925 Jul 11 20:21 config.json
-rwxr-xr-x 1 temmie users  1476 Oct  4  2019 dad.py
-rwxr-xr-x 1 temmie users  1780 Apr 18  2019 karma.py
-rwxr-xr-x 1 temmie users   710 Oct 28  2019 linker.py
-rw-r--r-- 1 temmie users   418 Dec  8  2019 Makefile
-rwxr-xr-x 1 temmie users 11854 Dec  8  2019 managed_cat.py
-rwxr-xr-x 1 temmie users  1788 Oct 31  2019 misc.py
-rwxr-xr-x 1 temmie users  1998 Jan 25  2019 orac.py
-rwxr-xr-x 1 temmie users  1021 Mar 27  2019 pipe.py
-rwxr-xr-x 1 temmie users  1300 Mar 20  2019 poll.py
drwxr-xr-x 2 temmie users     9 Oct 31  2019 __pycache__
-rw-r--r-- 1 temmie users   663 Jan 10  2019 README.md
-rwxr-xr-x 1 temmie users  2341 Mar 28  2019 roll.py
-rw-r--r-- 1 temmie users  7168 Dec  8  2019 srv.0.db
-rwxr-xr-x 1 temmie users  2617 Oct 28  2019 starboard.py
-rwxr-xr-x 1 temmie users  1515 Oct 31  2019 utils.py
```

I would eventually decommission/rewrite it, where it would become [blender-3e](https://github.com/ralismark/blender-3e).

# Old Design Docs from 2019

This document details the design of the system.

## Goals

- Separate components (known as fragments) that are able to coexists and interoperate, but use a shared base layer.
	- Fragments should not need to know about the existence of other fragments, except in the case of conflicts (e.g. naming conflicts).
	- There should be no need to subvert the base layer - everything addressed by it should provide all necessary functionality without limiting fragments.
- This shared base layer should be independent of any individual fragment.

## Overall Design

A fragment should be a file, with global function calls to register required components.
