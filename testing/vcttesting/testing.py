# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import absolute_import, unicode_literals

import errno
import json
import os
import subprocess
import sys

from coverage import Coverage


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))


PYTHON_COVERAGE_DIRS = (
    "hgext",
    "pylib",
    "hghooks",
)

# Directories containing tests. See ``get_test_files()``.
#
# The Mercurial test harness can run ``.py`` tests. So it isn't necessary
# to list directories here that are scanned for Mercurial tests (namely
# ``hgext/`` and ``hghooks/``. ``.t`` files in directories listed here will
# be executed by the Mercurial test harness and ``.py`` tests will be executed
# by the Python test harness.
UNIT_TEST_DIRS = {
    "git/tests": {
        "venvs": {"global"},
    },
    "hgserver/tests": {
        "venvs": {"global"},
    },
    "pylib": {
        "venvs": {"global", "hgdev"},
    },
    "hghooks/tests": {
        "venvs": {"global"},
    },
}

# Directories whose Python unit tests we should ignore.
UNIT_TEST_IGNORES = (
    "pylib/Bugsy",
    "pylib/flake8",
    "pylib/mccabe",
    "pylib/pycodestyle",
    "pylib/pyflakes",
    "pylib/requests",
    "third_party",
)

COVERAGE_OMIT = (
    "venv/*",
    "pylib/Bugsy/*",
    "pylib/flake/*",
    "pylib/mccabe/*",
    "pylib/mercurial-support/*",
    "pylib/pycodestyle/*",
    "pylib/pyflakes/*",
    "pylib/requests/*",
)


def is_test_filename(f):
    """Is a path a test file."""
    return f.startswith("test-") and f.endswith((".py", ".t"))


def get_extension_dirs():
    """Obtain directories with Mercurial extensions.

    yields 2-tuples of (base dir, directory to scan for extension files).
    """
    # Directories under hgext/ are extensions.
    for d in os.listdir(os.path.join(ROOT, "hgext")):
        full = os.path.join(ROOT, "hgext", d)

        if d.startswith(".") or not os.path.isdir(full):
            continue

        yield full, full

    # Add other well-known directories.
    yield os.path.join(ROOT, "hghooks"), os.path.join(ROOT, "hghooks", "mozhghooks")


def get_extensions():
    """Obtain information about extensions.

    Returns a list of dicts with extension metadata.
    """
    extensions = []

    for ext_dir, compat_dir in get_extension_dirs():
        e = {"tests": set(), "testedwith": set()}

        # Find test files.
        test_dir = os.path.join(ext_dir, "tests")
        if os.path.isdir(test_dir):
            for f in os.listdir(test_dir):
                if f.startswith("."):
                    continue

                if is_test_filename(f):
                    e["tests"].add(os.path.join(test_dir, f))

        # Look for compatibility info.
        for f in os.listdir(compat_dir):
            if f.startswith(".") or not f.endswith(".py"):
                continue

            with open(os.path.join(compat_dir, f), "rb") as fh:
                lines = fh.readlines()

            for line in lines:
                if not line.startswith(b"testedwith"):
                    continue

                v, value = line.split(b"=", 1)
                value = value.strip().strip(b"'").strip(b'"').strip()
                e["testedwith"] = set(value.split())

        extensions.append(e)

    return extensions


def get_test_files(extensions):
    """Resolves test files to run.

    ``extensions`` is the result of ``get_extensions()``. ``venv`` is the
    name of the activated virtualenv.

    The returned dict maps classes of tests to sets of paths. Keys are:

    extension
       Related to Mercurial extensions
    hg
       Mercurial tests not associated with extensions
    unit
       Generic Python unit tests (to be executed with a Python test harness)
    all
       Union of all of the above
    docker_requirements
       Dict of test path to set of Docker requirements. The set is empty
       if Docker is not required.

    Essentially, the tests are segmented by whether they are executed by
    Mercurial's test harness (``run-tests.py``) or a Python test harness
    (like nose).

    The Mercurial test harness is the only harness capable of executing
    ``.t`` tests. So all ``.t`` tests are assigned to it. ``.py`` tests
    can be executed by both the Mercurial and Python harness. Some ``.py``
    tests require the Mercurial test harness. So input directories that are
    related to Mercurial automatically have their ``.py`` tests assigned to
    Mercurial. The Python test harness should only get ``.py`` tests if they
    obviously don't belong to Mercurial.
    """
    extension_tests = []

    for e in extensions:
        extension_tests.extend(e["tests"])

    hg_tests = []
    unit_tests = []
    for base, settings in sorted(UNIT_TEST_DIRS.items()):
        base = os.path.join(ROOT, base)
        for root, dirs, files in os.walk(base):
            relative = root[len(ROOT) + 1 :]
            if relative.startswith(UNIT_TEST_IGNORES):
                continue

            for f in files:
                if f.startswith("test") and f.endswith(".py"):
                    unit_tests.append(os.path.join(root, f))
                elif f.startswith("test") and f.endswith(".t"):
                    hg_tests.append(os.path.join(root, f))

    all_tests = set(extension_tests) | set(hg_tests) | set(unit_tests)

    return {
        "extension": sorted(extension_tests),
        "hg": sorted(hg_tests),
        "unit": sorted(unit_tests),
        "all": all_tests,
        "docker_requirements": {t: docker_requirements_for_test(t) for t in all_tests},
    }


def docker_requirements_for_test(path):
    """Given a path to a test, determine its Docker requirements.

    Returns a set of strings describing which Docker features are
    needed. String values are:

    hgmo
       Requires images to run hg.mozilla.org
    """
    docker_keywords = ()

    res = set()

    with open(path, "rb") as fh:
        content = fh.read()

        if b"#require hgmodocker" in content:
            res.add("hgmo")

        for keyword in docker_keywords:
            if keyword in content:
                # This could probably be defined better.
                res.add("hgmo")

    return res


def docker_requirements(tests):
    """Determine what Docker features are needed by the given tests."""

    res = set()
    for test in tests:
        res |= docker_requirements_for_test(test)

    return res


def produce_coverage_reports(coverdir):
    cov = Coverage(data_file="coverage")
    cov.combine(data_paths=[os.path.join(coverdir, "data")])

    pydirs = [os.path.join(ROOT, d) for d in PYTHON_COVERAGE_DIRS]
    omit = [os.path.join(ROOT, d) for d in COVERAGE_OMIT]

    # Ensure all .py files show up in coverage report.
    for d in pydirs:
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.endswith(".py"):
                    cov.data.touch_file(os.path.join(root, f))

    cov.html_report(
        directory=os.path.join(coverdir, "html"), ignore_errors=True, omit=omit
    )
    cov.xml_report(
        outfile=os.path.join(coverdir, "coverage.xml"), ignore_errors=True, omit=omit
    )


def run_nose_tests(tests, process_count=None, verbose=False):
    """Run nose tests and return result code."""
    noseargs = [sys.executable, "-m", "nose.core", "-s"]

    if process_count and process_count > 1:
        noseargs.extend(
            [
                "--processes=%d" % process_count,
                "--process-timeout=120",
            ]
        )

    if verbose:
        noseargs.append("-v")
    else:
        noseargs.append("--nologcapture")

    noseargs.extend(tests)

    env = dict(os.environ)
    paths = [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]

    # We need the directory with sitecustomize.py in sys.path for code
    # coverage to work. This is arguably a bug in the location of
    # sitecustomize.py.
    paths.append(os.path.dirname(sys.executable))

    return subprocess.call(noseargs, env=env)


def get_hg_version(hg):
    env = dict(os.environ)
    env[b"HGPLAIN"] = b"1"
    env[b"HGRCPATH"] = b"/dev/null"
    try:
        out = subprocess.check_output(
            "%s debuginstall -T json" % hg, env=env, shell=True
        )
    except subprocess.CalledProcessError as e:
        out = e.output

    # index 0 because Mercurial's JSON templates always emit
    # a list, with a single element in our case
    debuginstall_info = json.loads(out)[0]
    return debuginstall_info["hgver"], debuginstall_info["pythonver"]


def remove_err_files(tests):
    for t in tests:
        err = "%s.err" % t
        try:
            os.remove(err)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
