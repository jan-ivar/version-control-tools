# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from __future__ import absolute_import


from ..checks import (
    PreTxnChangegroupCheck,
    print_banner,
)


SUBREPO_NOT_ALLOWED = b"""
%(node)s contains subrepositories.

Subrepositories are not allowed on this repository.

Please remove .hgsub and/or .hgsubstate files from the repository and try your
push again.
"""


class PreventSubReposCheck(PreTxnChangegroupCheck):
    """Prevents sub-repos from being committed.

    Sub-repos are a power user feature. They make it difficult to convert repos
    to and from Git. We also tend to prefer vendoring into a repo instead of
    creating a "symlink" to another repo.

    This check prevents the introduction of sub-repos on incoming changesets
    for non-user repos. For user repos, it prints a non-fatal warning
    discouraging their use.
    """

    @property
    def name(self):
        return b"prevent_subrepos"

    def relevant(self):
        return True

    def pre(self, node):
        self.done = False

        # Subrepos are defined by .hgsub and .hgsubstate files under version
        # control. Since resolving a manifest can be expensive and since
        # Mercurial indexes tracked paths, we can avoid a bit of work by testing
        # whether there is *any* versioned data for these tracked files. If not,
        # we can short circuit the check and avoid manifest lookups.
        seen = False
        for p in (b".hgsub", b".hgsubstate"):
            fl = self.repo.file(p)
            if len(fl):
                seen = True
                break

        if not seen:
            self.done = True

    def check(self, ctx):
        # Since the check can be non-fatal and since it requires a manifest
        # (which can be expensive to obtain), no-op if there is no work to do.
        if self.done:
            return True

        if b".hgsub" not in ctx and b".hgsubstate" not in ctx:
            return True

        self.done = True

        print_banner(
            self.ui,
            b"error",
            SUBREPO_NOT_ALLOWED
            % {
                b"node": ctx.hex()[0:12],
            },
        )
        return False

    def post_check(self):
        return True
