# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import hashlib

from mercurial import (
    pycompat,
)


def mozrepohash(ui, repo, no_raw=False, **opts):
    """obtain a hash of the repo contents.

    The hash can be used to test for repository equivalence. Useful for
    determining if a repo on 2 different servers is identical.
    """
    # Hash of revisions in default repoview.
    h_default = hashlib.sha256()
    # Hash of revisions in unfiltered repoview.
    h_unfiltered = hashlib.sha256()
    # Hash of revisions with phases.
    h_phases = hashlib.sha256()
    # Hash of heads in default repoview.
    h_heads = hashlib.sha256()
    # Hash of heads in unfiltered repoview.
    h_heads_unfiltered = hashlib.sha256()
    # Hash of pushlog data.
    h_pushlog = hashlib.sha256()
    # Hash of obsolete records.
    h_obsrecords = hashlib.sha256()
    # Hash of obsstore data.
    h_obsstore = hashlib.sha256()

    pushlog = getattr(repo, r"pushlog", None)
    if pushlog:
        for push in pushlog.pushes():
            h_pushlog.update(b"%d%d%s" % (push.pushid, push.when, push.user))

            for node in push.nodes:
                h_pushlog.update(node)

    # Add each changelog entry to the hash, complete with its push ID.
    for rev in repo:
        ctx = repo[rev]

        h_default.update(b"%d%s" % (rev, ctx.node()))

    urepo = repo.unfiltered()
    for rev in urepo:
        ctx = urepo[rev]
        phase = ctx.phase()
        node = ctx.node()

        h_unfiltered.update(b"%d%s" % (rev, node))
        h_phases.update(b"%d%s%d" % (rev, node, phase))

    for head in sorted(repo.heads()):
        h_heads.update(head)

    for head in sorted(urepo.heads()):
        h_heads_unfiltered.update(head)

    for pre, sucs, flags, metadata, date, parents in sorted(repo.obsstore):
        h_obsrecords.update(pre)

        for suc in sucs:
            h_obsrecords.update(suc)

        h_obsrecords.update(b"%d" % flags)

        for k, v in metadata:
            h_obsrecords.update(k)
            h_obsrecords.update(v)

        h_obsrecords.update(b"%d" % date[0])
        h_obsrecords.update(b"%d" % date[1])

        for p in parents or []:
            h_obsrecords.update(p)

    # Add extra files from storage.
    h_obsstore.update(b"obsstore")
    h_obsstore.update(repo.svfs.tryread(b"obsstore"))

    # Output with formatting
    fm = ui.formatter("mozrepohash", pycompat.byteskwargs(opts))
    fm.startitem()
    fm.write(b"revisions_visible", b"visible revisions: %d\n", len(repo))
    fm.write(b"revisions_total", b"total revisions: %d\n", len(urepo))
    fm.write(b"heads_visible", b"visible heads: %d\n", len(repo.heads()))
    fm.write(b"heads_total", b"total heads: %d\n", len(urepo.heads()))
    fm.write(
        b"normal", b"normal repo hash: %s\n", pycompat.bytestr(h_default.hexdigest())
    )
    fm.write(
        b"unfiltered",
        b"unfiltered repo hash: %s\n",
        pycompat.bytestr(h_unfiltered.hexdigest()),
    )
    fm.write(b"phases", b"phases hash: %s\n", pycompat.bytestr(h_phases.hexdigest()))
    fm.write(b"heads", b"heads hash: %s\n", pycompat.bytestr(h_heads.hexdigest()))
    fm.write(
        b"unfiltered_heads",
        b"unfiltered heads hash: %s\n",
        pycompat.bytestr(h_heads_unfiltered.hexdigest()),
    )
    fm.write(b"pushlog", b"pushlog hash: %s\n", pycompat.bytestr(h_pushlog.hexdigest()))

    if repo.svfs.exists(b"obsstore"):
        fm.write(
            b"obsolete_records_count",
            b"obsolete records count: %d\n",
            len(repo.obsstore),
        )
        fm.write(
            b"obsolete_records",
            b"obsolete records hash: %s\n",
            pycompat.bytestr(h_obsrecords.hexdigest()),
        )

        if not no_raw:
            fm.write(
                b"obsstore",
                b"obsstore hash: %s\n",
                pycompat.bytestr(h_obsstore.hexdigest()),
            )

    fm.end()
