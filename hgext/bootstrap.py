# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# This file is executed when extensions from this repository load.
# It's goal is to set up sys.path so all libraries are present.

# We do everything in a function so symbols don't leak.
def HGEXT_BOOTSTRAP():
    import os
    import sys

    # __file__ comes from the invoking script (usually). It shouldn't
    # matter.
    here = os.path.normpath(os.path.abspath(os.path.dirname(__file__)))
    root = None
    while True:
        if not here:
            break

        possible = os.path.join(here, "run-tests")
        if os.path.exists(possible):
            root = here
            break

        newhere = os.path.dirname(here)
        if newhere == here:
            break
        here = newhere

    if not here or not root:
        raise Exception("Could not find repository root.")

    paths = set(sys.path)

    lib_paths = [
        "pylib/configobj",
        "pylib/Bugsy",
        "pylib/flake8",
        "pylib/mccabe",
        "pylib/mozautomation",
        "pylib/mozhg",
        "pylib/pycodestyle",
        "pylib/pyflakes",
        "third_party/python/certifi",
        "third_party/python/chardet",
        "third_party/python/idna",
        "third_party/python/requests",
        "third_party/python/six",
        "third_party/python/urllib3",
    ]
    for p in lib_paths:
        full = os.path.normpath(os.path.join(root, p))
        if full not in paths:
            sys.path.insert(0, full)


if not globals().get("HGEXT_BOOTSTRAPPED", False):
    HGEXT_BOOTSTRAP()
