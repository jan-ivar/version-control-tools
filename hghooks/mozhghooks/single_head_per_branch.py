#!/usr/bin/env python

# Copyright (C) 2010 Mozilla Foundation
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


def hook(ui, repo, source=None, **kwargs):
    if source in (b"pull", b"strip"):
        return 0

    for branch, heads in repo.branchmap().iteritems():
        newheads = []

        for node in heads:
            ctx = repo[node]

            # Filter closed branch heads.
            if ctx.closesbranch():
                continue

            # Hidden changesets shouldn't matter.
            if ctx.hidden():
                continue

            newheads.append(node)

        if len(newheads) > 1:
            ui.write(
                b"\n\n************************** ERROR ****************************\n"
            )
            ui.write(b"Multiple heads detected on branch '%s'\n" % branch)
            ui.write(b"Only one head per branch is allowed!\n")
            ui.write(
                b"*************************************************************\n\n\n"
            )
            return 1
    return 0
