# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import sys
import re
import shlex
import subprocess

from configparser import RawConfigParser
from html import escape

from hgmolib.ldap_helper import (
    get_ldap_attribute,
    get_ldap_settings,
    get_scm_groups,
)
import repo_group
from sh_helper import (
    prompt_user,
    run_command,
)


Popen = subprocess.Popen
PIPE = subprocess.PIPE

HG = "/var/hg/venv_pash/bin/hg"

SUCCESSFUL_AUTH = """
A SSH connection has been successfully established.

Your account (%s) has privileges to access Mercurial over
SSH.

""".lstrip()

NO_SSH_COMMAND = """
You did not specify a command to run on the server. This server only
supports running specific commands. Since there is nothing to do, you
are being disconnected.
""".lstrip()

INVALID_SSH_COMMAND = """
The command you specified is not allowed on this server.

Goodbye.
""".lstrip()

LDAP_GROUP_MEMBERSHIP = """
You are a member of the following LDAP groups that govern source control
access:

   {groups}

This will give you write access to the following repos:

   {access}

You will NOT have write access to the following repos:

   {no_access}
""".lstrip()

NO_LDAP_GROUP_MEMBERSHIP = """
You are NOT a member of any LDAP groups that govern source control access.

You will NOT be able to push to any repository until you have been granted
commit access.

See https://www.mozilla.org/about/governance/policies/commit/access-policy/ for
more information.
""".lstrip()

USER_REPO_EXISTS = """
You already have a repo called %s.

If you think this is wrong, please file a Developer Services :: hg.mozilla.org
bug at
https://bugzilla.mozilla.org/enter_bug.cgi?product=Developer%%20Services&component=Mercurial%%3A%%20hg.mozilla.org
""".strip()

NO_SOURCE_REPO = """
Sorry, there is no source repo called %s.

If you think this is wrong, please file a Developer Services :: hg.mozilla.org
bug at
https://bugzilla.mozilla.org/enter_bug.cgi?product=Developer%%20Services&component=Mercurial%%3A%%20hg.mozilla.org
""".strip()

HGWEB_ERROR = """
Problem opening hgweb.wsgi file.

Please file a Developer Services :: hg.mozilla.org bug at
https://bugzilla.mozilla.org/enter_bug.cgi?product=Developer%20Services&component=Mercurial%3A%20hg.mozilla.org
""".strip()

MAKING_REPO = """
Making repo {repo} for {user}.

This repo will appear as {cname}/users/{user_dir}/{repo}.

If you need a top level repo, please quit now and file a
Developer Services :: hg.mozilla.org bug at
https://bugzilla.mozilla.org/enter_bug.cgi?product=Developer%20Services&component=Mercurial%3A%20hg.mozilla.org
""".strip()

EDIT_DESCRIPTION = """
You are about to edit the description for hg.mozilla.org/users/{user_dir}/{repo}.

If you need to edit the description for a top level repo, please quit now
and file a Developer Services :: hg.mozilla.org bug at
https://bugzilla.mozilla.org/enter_bug.cgi?product=Developer%20Services&component=Mercurial%3A%20hg.mozilla.org
""".strip()

DOC_ROOT = "/repo/hg/mozilla"

OBSOLESCENCE_ENABLED = """
Obsolescence is now enabled for this repository.

Obsolescence is currently an experimental feature. It may be disabled at any
time. Your obsolescence data may be lost at any time. You have been warned.

Enjoy living on the edge.
""".strip()


def is_valid_user(mail):
    url = get_ldap_settings()["url"]

    mail = mail.strip()
    replacements = {
        "(": "",
        ")": "",
        "'": "",
        '"': "",
        ";": "",
    }
    for search, replace in replacements.items():
        mail = mail.replace(search, replace)
    account_status = get_ldap_attribute(mail, "hgAccountEnabled", url)
    if account_status == "TRUE":
        return 1
    elif account_status == "FALSE":
        return 2
    else:
        return 0


GROUP_REPOS = {
    "scm_level_1": {
        "Try",
        "User Repos (users/)",
    },
    "scm_level_2": {
        "Project Repos (projects/)",
    },
    "scm_level_3": {
        "Firefox Repos via Lando",
    },
    "scm_allow_direct_push": {
        "Firefox Repos via direct push",
    },
    "scm_autoland": {
        "Autoland (integration/autoland)",
    },
    "scm_l10n": {
        "Localization Repos (releases/l10n/*, others)",
    },
    "scm_versioncontrol": {"Version Control Tools (hgcustom/version-control-tools)"},
}


def group_membership_message(mail):
    """Obtain a message denoting LDAP group membership."""
    groups = get_scm_groups(mail)

    if groups is None:
        return "Unable to determine LDAP group membership."
    elif not groups:
        return NO_LDAP_GROUP_MEMBERSHIP
    else:
        access = set()
        for group in groups:
            access |= GROUP_REPOS.get(group, set())

        no_access = set()
        for group, values in GROUP_REPOS.items():
            if group not in groups:
                no_access |= values

        if not access:
            access.add("Unknown")
        if not no_access:
            no_access.add("Unknown")

        return LDAP_GROUP_MEMBERSHIP.format(
            groups=", ".join(sorted(groups)),
            access=", ".join(sorted(access)),
            no_access=", ".join(sorted(no_access)),
        )


# Please be very careful when you relax/change the regular expressions.
# Being lax can open us up to all kind of security problems.
def is_valid_repo_name(repo_name):
    # Trailing slashes can be ignored.
    repo_name = repo_name.rstrip("/")

    part_re = re.compile(
        r"^[a-zA-Z0-9]"  # must start with a letter or number
        r"[a-zA-Z0-9./_-]*$"  # . / _ and - are allowed after the first char
    )
    for part in repo_name.split("/"):
        if not part_re.search(part):
            return False
        if part.endswith((".hg", ".git")):
            return False
    return True


def assert_valid_repo_name(repo_name):
    if not is_valid_repo_name(repo_name):
        sys.stderr.write(
            'Only alpha-numeric characters, ".", "_", and "-" are '
            "allowed in repository\n"
        )
        sys.stderr.write(
            "names.  Additionally the first character of "
            "repository names must be alpha-numeric.\n"
        )
        sys.exit(1)


def run_hg_clone(user_repo_dir, repo_name, source_repo_path):
    userdir = "%s/users/%s" % (DOC_ROOT, user_repo_dir)
    dest_dir = "%s/%s" % (userdir, repo_name)
    dest_url = "/users/%s/%s" % (user_repo_dir, repo_name)

    if os.path.exists(dest_dir):
        print(USER_REPO_EXISTS % repo_name)
        sys.exit(1)

    assert_valid_repo_name(source_repo_path)
    if not os.path.exists("%s/%s" % (DOC_ROOT, source_repo_path)):
        print(NO_SOURCE_REPO % source_repo_path)
        sys.exit(1)

    if not os.path.exists(userdir):
        run_command("mkdir %s" % userdir)
    print("Please wait.  Cloning /%s to %s" % (source_repo_path, dest_url))
    run_command(
        "nohup %s --config format.usegeneraldelta=true init %s" % (HG, dest_dir)
    )
    run_command(
        "nohup %s -R %s pull %s/%s" % (HG, dest_dir, DOC_ROOT, source_repo_path)
    )
    run_command("nohup %s -R %s replicatesync" % (HG, dest_dir))
    # TODO ensure user WSGI files are in place on hgweb machine.
    # (even better don't rely on per-use WSGI files)
    print("Clone complete.")


def make_wsgi_dir(cname, user_repo_dir):
    wsgi_dir = "/repo/hg/webroot_wsgi/users/%s" % user_repo_dir
    # Create user's webroot_wsgi folder if it doesn't already exist
    if not os.path.isdir(wsgi_dir):
        os.mkdir(wsgi_dir)

    print("Creating hgweb.config file")
    # Create hgweb.config file if it doesn't already exist
    if not os.path.isfile("%s/hgweb.config" % wsgi_dir):
        hgconfig = open("%s/hgweb.config" % wsgi_dir, "w")
        hgconfig.write("[web]\n")
        hgconfig.write("baseurl = http://%s/users/%s\n" % (cname, user_repo_dir))
        hgconfig.write("[paths]\n")
        hgconfig.write("/ = %s/users/%s/*\n" % (DOC_ROOT, user_repo_dir))
        hgconfig.close()

    # Create hgweb.wsgi file if it doesn't already exist
    if not os.path.isfile("%s/hgweb.wsgi" % wsgi_dir):
        try:
            hgwsgi = open("%s/hgweb.wsgi" % wsgi_dir, "w")
        except Exception:
            print(HGWEB_ERROR)
            sys.exit(1)

        hgwsgi.write("#!/usr/bin/env python\n")
        hgwsgi.write("config = '%s/hgweb.config'\n" % wsgi_dir)
        hgwsgi.write("from mercurial import demandimport; demandimport.enable()\n")
        hgwsgi.write("from mercurial.hgweb import hgweb\n")
        hgwsgi.write("import os\n")
        hgwsgi.write("os.environ['HGENCODING'] = 'UTF-8'\n")
        hgwsgi.write("application = hgweb(config)\n")
        hgwsgi.close()


def fix_user_repo_perms(repo_name):
    user = os.getenv("USER")
    user_repo_dir = user.replace("@", "_")
    print("Fixing permissions, don't interrupt.")
    try:
        run_command(
            "/var/hg/version-control-tools/scripts/repo-permissions %s/users/%s/%s %s scm_level_1 wwr"
            % (DOC_ROOT, user_repo_dir, repo_name, user)
        )
    except Exception as e:
        print("Exception %s" % (e))


def make_repo_clone(cname, repo_name, quick_src, source_repo=""):
    user = os.getenv("USER")
    user_repo_dir = user.replace("@", "_")
    source_repo = ""
    if quick_src:
        run_hg_clone(user_repo_dir, repo_name, quick_src)
        fix_user_repo_perms(repo_name)
        # New user repositories are non-publishing by default.
        set_repo_publishing(repo_name, False)
        sys.exit(0)

    print(
        MAKING_REPO.format(
            repo=repo_name, user=user, cname=cname, user_dir=user_repo_dir
        )
    )
    selection = prompt_user("Proceed?", ["yes", "no"])
    if selection != "yes":
        return

    print("You can clone an existing public repo or create an empty repo.")
    selection = prompt_user(
        "Source repository:",
        ["Clone a public repository", "Create an empty repository"],
    )
    if selection == "Clone a public repository":
        exec_command = (
            "/usr/bin/find " + DOC_ROOT + " -maxdepth 3 -mindepth 2 -type d -name .hg"
        )
        args = shlex.split(exec_command)
        with open(os.devnull, "wb") as devnull:
            p = Popen(args, stdout=PIPE, stdin=PIPE, stderr=devnull)
            repo_list = p.communicate()[0].decode("utf-8").split("\n")
        if repo_list:
            print("We have the repo_list")
            repo_list = map(lambda x: x.replace(DOC_ROOT + "/", ""), repo_list)
            repo_list = map(lambda x: x.replace("/.hg", ""), repo_list)
            repo_list = [x.strip() for x in sorted(repo_list) if x.strip()]
            print("List of available public repos")
            source_repo = prompt_user("Pick a source repo:", repo_list, period=False)
    elif selection == "Create an empty repository":
        source_repo = ""
    else:
        # We should not get here
        source_repo = ""
    if source_repo != "":
        print(
            "About to clone /%s to /users/%s/%s"
            % (source_repo, user_repo_dir, repo_name)
        )
        response = prompt_user("Proceed?", ["yes", "no"])
        if response == "yes":
            print("Please do not interrupt this operation.")
            run_hg_clone(user_repo_dir, repo_name, source_repo)
    else:
        print(
            "About to create an empty repository at /users/%s/%s"
            % (user_repo_dir, repo_name)
        )
        response = prompt_user("Proceed?", ["yes", "no"])
        if response == "yes":
            if not os.path.exists("%s/users/%s" % (DOC_ROOT, user_repo_dir)):
                try:
                    exec_command = "/bin/mkdir %s/users/%s" % (DOC_ROOT, user_repo_dir)
                    run_command(exec_command)
                except Exception as e:
                    print("Exception %s" % (e))

            run_command(
                "/usr/bin/nohup %s --config format.usegeneraldelta=true init %s/users/%s/%s"
                % (HG, DOC_ROOT, user_repo_dir, repo_name)
            )
    fix_user_repo_perms(repo_name)
    # New user repositories are non-publishing by default.
    set_repo_publishing(repo_name, False)
    sys.exit(0)


def get_and_validate_user_repo(repo_name):
    user = os.getenv("USER")
    user_repo_dir = user.replace("@", "_")
    rel_path = "/users/%s/%s" % (user_repo_dir, repo_name)
    fs_path = "%s%s" % (DOC_ROOT, rel_path)

    if not os.path.exists(fs_path):
        sys.stderr.write("Could not find repository at %s.\n" % rel_path)
        sys.exit(1)

    return fs_path


def get_user_repo_config(repo_dir):
    """Obtain a ConfigParser for a repository.

    If the hgrc file doesn't exist, it will be created automatically.
    """
    user = os.getenv("USER")
    path = "%s/.hg/hgrc" % repo_dir
    if not os.path.isfile(path):
        run_command("touch %s" % path)
        run_command("chown %s:scm_level_1 %s" % (user, path))

    config = RawConfigParser()
    if not config.read(path):
        sys.stderr.write("Could not read the hgrc file for this repo\n")
        sys.stderr.write("Please file a Developer Services :: hg.mozilla.org bug\n")
        sys.exit(1)

    return path, config


def edit_repo_description(repo_name):
    user = os.getenv("USER")
    user_repo_dir = user.replace("@", "_")
    print(EDIT_DESCRIPTION.format(user_dir=user_repo_dir, repo=repo_name))
    selection = prompt_user("Proceed?", ["yes", "no"])
    if selection != "yes":
        return

    repo_path = get_and_validate_user_repo(repo_name)

    repo_description = input("Enter a one line descripton for the repository: ")
    if not repo_description:
        return

    repo_description = repo_description.splitlines()
    if not repo_description:
        return

    repo_description = repo_description[0]
    if repo_description == "":
        return

    repo_description = escape(repo_description)

    config_path, config = get_user_repo_config(repo_path)

    if not config.has_section("web"):
        config.add_section("web")

    config.set("web", "description", repo_description)

    with open(config_path, "w+") as fh:
        config.write(fh)

    run_command("%s -R %s replicatehgrc" % (HG, repo_path))


def set_repo_publishing(repo_name, publish):
    """Set the publishing flag on a repository.

    A publishing repository turns its pushed commits into public
    phased commits. It is the default behavior.

    Non-publishing repositories have their commits stay in the draft phase
    when pushed.
    """
    repo_path = get_and_validate_user_repo(repo_name)
    config_path, config = get_user_repo_config(repo_path)

    if not config.has_section("phases"):
        config.add_section("phases")

    value = "True" if publish else "False"

    config.set("phases", "publish", value)

    with open(config_path, "w") as fh:
        config.write(fh)

    run_command("%s -R %s replicatehgrc" % (HG, repo_path))

    if publish:
        sys.stderr.write(
            "Repository marked as publishing: changesets will "
            "change to public phase when pushed.\n"
        )
    else:
        sys.stderr.write(
            "Repository marked as non-publishing: draft "
            "changesets will remain in the draft phase when pushed.\n"
        )


def set_repo_obsolescence(repo_name, enabled):
    """Enable or disable obsolescence support on a repository."""
    repo_path = get_and_validate_user_repo(repo_name)
    config_path, config = get_user_repo_config(repo_path)

    if not config.has_section("experimental"):
        config.add_section("experimental")

    if enabled:
        config.set("experimental", "evolution", "true")
    else:
        config.remove_option("experimental", "evolution")

    with open(config_path, "w") as fh:
        config.write(fh)

    run_command("%s -R %s replicatehgrc" % (HG, repo_path))

    if enabled:
        print(OBSOLESCENCE_ENABLED)
    else:
        print("Obsolescence is now disabled for this repo.")


def do_delete(repo_dir, repo_name):
    repo_path = "%s/users/%s/%s" % (DOC_ROOT, repo_dir, repo_name)
    run_command("nohup %s -R %s replicatedelete" % (HG, repo_path))
    purge_log = open("/tmp/pushlog_purge.%s" % os.getpid(), "a")
    purge_log.write("echo users/%s/%s\n" % (repo_dir, repo_name))
    purge_log.close()


def delete_repo(cname, repo_name, do_quick_delete):
    user = os.getenv("USER")
    user_repo_dir = user.replace("@", "_")
    if os.path.exists("%s/users/%s/%s" % (DOC_ROOT, user_repo_dir, repo_name)):
        if do_quick_delete:
            do_delete(user_repo_dir, repo_name)
        else:
            print(
                "\nAre you sure you want to delete /users/%s/%s?"
                % (user_repo_dir, repo_name)
            )
            print("\nThis action is IRREVERSIBLE.")
            selection = prompt_user("Proceed?", ["yes", "no"])
            if selection == "yes":
                do_delete(user_repo_dir, repo_name)
    else:
        sys.stderr.write(
            "Could not find the repository at /users/%s/%s.\n"
            % (user_repo_dir, repo_name)
        )
        sys.stderr.write(
            "Please check the list at https://%s/users/%s\n" % (cname, user_repo_dir)
        )
        sys.exit(1)
    sys.exit(0)


def edit_repo(cname, repo_name, do_quick_delete):
    if do_quick_delete:
        delete_repo(cname, repo_name, do_quick_delete)
    else:
        action = prompt_user(
            "What would you like to do?",
            [
                "Delete the repository",
                "Edit the description",
                "Mark repository as non-publishing",
                "Mark repository as publishing",
                "Enable obsolescence support (experimental)",
                "Disable obsolescence support",
            ],
        )
        if action == "Edit the description":
            edit_repo_description(repo_name)
        elif action == "Delete the repository":
            delete_repo(cname, repo_name, False)
        elif action == "Mark repository as non-publishing":
            set_repo_publishing(repo_name, False)
        elif action == "Mark repository as publishing":
            set_repo_publishing(repo_name, True)
        elif action == "Enable obsolescence support (experimental)":
            set_repo_obsolescence(repo_name, True)
        elif action == "Disable obsolescence support":
            set_repo_obsolescence(repo_name, False)
    return


def serve(
    cname, enable_repo_config=False, enable_repo_group=False, enable_user_repos=False
):
    ssh_command = os.getenv("SSH_ORIGINAL_COMMAND")
    if not ssh_command:
        sys.stderr.write(SUCCESSFUL_AUTH % os.environ["USER"])
        sys.stderr.write(group_membership_message(os.environ["USER"]))
        sys.stderr.write("\n")
        sys.stderr.write(NO_SSH_COMMAND)
        sys.exit(1)

    args = shlex.split(ssh_command)

    if args[0] == "hg":
        # SECURITY it is critical that invoked commands be limited to
        # `hg -R <path> serve --stdio`. If a user manages to pass arguments
        # to coerce Mercurial into say opening a debugger, that is effectively
        # giving them a remote shell. We require that command arguments match
        # an exact pattern and that the repo name is sanitized.
        if args[1] != "-R" or args[3:] != ["serve", "--stdio"]:
            sys.stderr.write(
                "invalid `hg` command executed; can only run " "serve --stdio\n"
            )
            sys.exit(1)

        # At this point, the only argument not validated to match exact bytes
        # is the value for -R. We sanitize that through our repo name validator
        # *and* verify it exists on disk.

        repo_path = args[2]
        # This will ensure the repo path is essentially alphanumeric. So we
        # don't have to worry about ``..``, Unicode, spaces, etc.
        assert_valid_repo_name(repo_path)
        full_repo_path = "%s/%s" % (DOC_ROOT, repo_path)

        if not os.path.isdir("%s/.hg" % full_repo_path):
            sys.stderr.write("requested repo %s does not exist\n" % repo_path)
            sys.exit(1)

        os.execv(HG, [HG, "-R", full_repo_path, "serve", "--stdio"])

    elif args[0] == "clone":
        if not enable_user_repos:
            print("user repository management is not enabled")
            sys.exit(1)

        if len(args) == 1:
            sys.stderr.write(
                "clone usage: ssh hg.mozilla.org clone newrepo " "[srcrepo]\n"
            )
            sys.exit(1)
        assert_valid_repo_name(args[1])
        if len(args) == 2:
            make_repo_clone(cname, args[1], None)
        elif len(args) == 3:
            make_repo_clone(cname, args[1], args[2])
        sys.exit(0)
    elif args[0] == "edit":
        if not enable_user_repos:
            print("user repository management is not enabled")
            sys.exit(1)

        if len(args) == 2:
            assert_valid_repo_name(args[1])
            edit_repo(cname, args[1], False)
        elif len(args) == 4 and args[2] == "delete" and args[3] == "YES":
            assert_valid_repo_name(args[1])
            edit_repo(cname, args[1], True)
        else:
            sys.stderr.write(
                "edit usage: ssh hg.mozilla.org edit "
                "[userrepo delete] - WARNING: will not "
                "prompt!\n"
            )
            sys.exit(1)
    elif args[0] == "repo-group":
        if not enable_repo_group:
            print("repo-group command not available")
            sys.exit(1)

        assert_valid_repo_name(args[1])
        print(repo_group.repo_owner(args[1]))
    elif args[0] == "repo-config":
        if not enable_repo_config:
            print("repo-config command not available")
            sys.exit(1)

        repo = args[1]
        assert_valid_repo_name(repo)
        hgrc = "/repo/hg/mozilla/%s/.hg/hgrc" % repo
        if os.path.exists(hgrc):
            with open(hgrc, "r", encoding="utf-8") as fh:
                sys.stdout.write(fh.read())
    else:
        sys.stderr.write(SUCCESSFUL_AUTH % os.environ["USER"])
        sys.stderr.write(INVALID_SSH_COMMAND)
        sys.exit(1)
