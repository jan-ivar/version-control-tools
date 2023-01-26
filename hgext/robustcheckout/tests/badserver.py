# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

from mercurial import (
    pycompat,
)

from mercurial.hgweb import (
    hgweb_mod,
)


def extsetup(ui):
    class droppinghgweb(hgweb_mod.hgweb):
        def _runwsgi(self, req, res, repo):
            bytelimit = repo.ui.configint(b"badserver", b"bytelimit")

            untilgoodcount = repo.vfs.tryread(b"badserveruntilgood")
            if untilgoodcount:
                untilgoodcount = int(untilgoodcount)

            # This check is different than the one above because it is
            # comparing an int type instead of a string. The first check could
            # be true for "0" but this check would be false for int(0).
            if untilgoodcount:
                repo.vfs.write(
                    b"badserveruntilgood", pycompat.bytestr(untilgoodcount - 1)
                )

            bytecount = 0
            for r in super(droppinghgweb, self)._runwsgi(req, res, repo):
                # We serviced the requested number of requests. Do everything
                # like normal.
                if untilgoodcount == 0:
                    yield r
                    continue

                if bytelimit:
                    if bytecount + len(r) >= bytelimit:
                        yield r[0 : bytelimit - bytecount]
                        return

                bytecount += len(r)
                yield r

                bytecount += len(r)

    hgweb_mod.hgweb = droppinghgweb
