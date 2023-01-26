# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from setuptools import find_packages, setup

setup(
    name="hgmolib",
    version="0.0",
    packages=find_packages(),
    description="hg.mozilla.org tools and utilities",
    url="https://mozilla-version-control-tools.readthedocs.io/",
    author="Mozilla",
    author_email="dev-version-control@lists.mozilla.org",
    license="MPL 2.0",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
    ],
    entry_points={
        "console_scripts": [
            "find-hg-repos=hgmolib.environment:script_find_hg_repos",
            "generate-hg-s3-bundles=hgmolib.generate_hg_s3_bundles:main",
        ]
    },
)
