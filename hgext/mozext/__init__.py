# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""make Mozilla contributors more productive

This extension adds Mozilla-centric commands and functionality to Mercurial
to enable contributors to Firefox and related applications to be more
productive.

Included are commands that interface with Mozilla's automation infrastructure.
These allow developers to quickly check the status of repositories and builds
without having to leave the comfort of the terminal.

Repository Aliases
==================

This extension installs aliases for common repository and tree names. Any time
a command is looking for a tree or repository name, you can specify the
canonical repository name, the common name, or any number of aliases.

To view the list of known repository aliases, run `hg moztrees`.

Unified Repositories
====================

Gecko code is developed in parallel across a number of repositories that are
cloned from the canonical repository, mozilla-central. Seasoned developers
typically interact with multiple repositories.

This extension provides mechanisms to create and maintain a single Mercurial
repository that contains changesets from multiple "upstream" repositories.

The recommended method to create a unified repository is to run `hg
cloneunified`.

Once you have a unified repository, you can pull changesets from repositories
by running `hg pulltree`. e.g. `hg pulltree central fx-team` will pull from
mozilla-central and fx-team.
"""

import os
import sys

import mercurial.commands as commands

from mercurial.i18n import _
from mercurial.commands import (
    bookmark,
    pull,
    push,
)
from mercurial import (
    cmdutil,
    hg,
    util,
)


commands.norepo += ' cloneunified moztrees treestatus'
cmdtable = {}
command = cmdutil.command(cmdtable)

colortable = {
    'buildstatus.success': 'green',
    'buildstatus.failed': 'red',
    'buildstatus.testfailed': 'cyan',
}


@command('moztrees', [], _('hg moztrees'))
def moztrees(ui, **opts):
    """Show information about Mozilla source trees."""
    from mozautomation.repository import TREE_ALIASES, REPOS

    longest = max(len(tree) for tree in REPOS.keys())
    ui.write('%s  %s\n' % (_('Repo').rjust(longest), _('Aliases')))

    for name in sorted(REPOS):
        aliases = []
        for alias, targets in TREE_ALIASES.items():
            if len(targets) > 1:
                continue

            if targets[0] == name:
                aliases.append(alias)

        ui.write('%s: %s\n' % (name.rjust(longest), ', '.join(sorted(aliases))))


@command('cloneunified', [], _('hg cloneunified [DEST]'))
def cloneunified(ui, dest='gecko', **opts):
    """Clone main Mozilla repositories into a unified local repository.

    This command will clone the most common Mozilla repositories and will
    add changesets and remote tracking markers into a common repository.

    If the destination path is not given, 'gecko' will be used.

    This command is effectively an alias for a number of other commands.
    However, due to the way Mercurial internally stores data, it is recommended
    to run this command to ensure optimal storage of data.
    """
    from mozautomation.repository import resolve_trees_to_uris

    repo = hg.repository(ui, ui.expandpath(dest), create=True)

    for r in ('esr17', 'release', 'beta', 'aurora', 'central', 'inbound'):
        tree, uri = resolve_trees_to_uris([r])[0]
        ui.warn('Pulling changesets from %s\n' % uri)
        peer = hg.peer(ui, {}, uri)
        result = repo.pull(peer)
        ui.write('%s\n' % result)


@command('treestatus', [], _('hg treestatus [TREE] ...'))
def treestatus(ui, *trees, **opts):
    """Show the status of the Mozilla repositories.

    If trees are open, it is OK to land code on them.

    If trees require approval, you'll need to obtain approval from
    release management to land changes.

    If trees are closed, you shouldn't push unless you are fixing the reason
    the tree is closed.
    """
    from mozautomation.repository import resolve_trees_to_official
    from mozautomation.treestatus import TreeStatusClient

    client = TreeStatusClient()
    status = client.all()

    trees = resolve_trees_to_official(trees)

    if trees:
        status = {k: status[k] for k in status if k in trees}

    longest = max(len(s) for s in status)

    for tree in sorted(status):
        s = status[tree]
        ui.write('%s: %s\n' % (tree.rjust(longest), s.status))


@command('pulltree', [], _('hg pulltree [TREE] ...'))
def pulltree(ui, repo, *trees, **opts):
    """Pull changesets from a Mozilla repository into this repository.

    Trees can be specified by their common name or aliases (see |hg moztrees|).
    When a tree is pulled, a bookmark is created with the common name of the
    tree. This allows updating to specified trees via e.g. |hg up central|.

    If no arguments are specified, the main landing trees (central and inbound)
    will be pulled.
    """
    from mozautomation.repository import resolve_trees_to_uris

    if not trees:
        trees = ['central', 'inbound']

    uris = resolve_trees_to_uris(trees)

    bms = {}

    for tree, uri in uris:
        if uri is None:
            ui.warn('Unknown Mozilla repository: %s\n' % tree)
            continue

        if pull(ui, repo, uri):
            ui.warn('Error pulling from %s\n' % uri)
            continue

        peer = hg.peer(repo, {}, uri)
        default = peer.lookup('default')

        bookmark(ui, repo, rev=default, force=True, mark=tree)


@command('pushtree',
    [('r', 'rev', 'tip', _('revision'), _('REV'))],
    _('hg pushtree [-r REV] TREE'))
def pushtree(ui, repo, tree=None, rev=None, **opts):
    """Push changesets to a Mozilla repository.

    If only the tree argument is defined, we will attempt to push the current
    tip to the repository specified. This may fail due to pushed mq patches,
    local changes, etc. Please note we only attempt to push the current tip and
    it's ancestors, not all changesets not in the remote repository. This is
    different from the default behavior of |hg push|.

    If you would like to push a non-active head, specify it with -r REV. For
    example, if you are currently on mozilla-central but wish to push the
    inbound bookmark to mozilla-inbound, run  |hg pushtree -r inbound inbound|.
    """
    if not tree:
        raise util.Abort(_('A tree must be specified.'))

    from mozautomation.repository import resolve_trees_to_uris

    tree, uri = resolve_trees_to_uris([tree], write_access=True)[0]

    if not uri:
        raise util.Abort("Don't know about tree %s" % tree)

    return push(ui, repo, rev=rev, dest=uri)
