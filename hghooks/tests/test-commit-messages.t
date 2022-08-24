  $ hg init server
  $ cat >> server/.hg/hgrc << EOF
  > [hooks]
  > pretxnchangegroup.commit_message = python:mozhghooks.commit-message.hook
  > EOF

  $ hg clone server client
  updating to branch default
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ cd client
  $ cat >> .hg/hgrc << EOF
  > [extensions]
  > strip=
  > EOF

Normal commits must have a bug number. The following tests look for the
various syntax allowed.

No bug is rejected

  $ echo 'no bug' > foo
  $ hg commit -A -m 'create foo'
  adding foo
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev b648292ceed8 needs "Bug N" or "No bug" in the commit message.
  test
  create foo
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]

  $ hg -q strip -r .

Bug XYZ syntax is accepted

  $ echo preferred > foo
  $ hg commit -A -m 'Bug 603517 - Enable mochitest to optionally run in loops without restarting r=ctalbert'
  adding foo
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

Adding a few dummy commits for upcoming backouts.

  $ echo dummycommit1 > foo
  $ hg commit -A -m 'Bug 100 - Part 1: Test. r=me'
  $ echo dummycommit2 > foo
  $ hg commit -A -m 'Bug 100 - Part 2: Test. r=me'
  $ echo dummycommit3 > foo
  $ hg commit -A -m 'Bug 100 - Part 3: Test. r=me'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 3 changesets with 3 changes to 1 files

Backouts need to reference a changeset with 12 digit hash.

Backing out a single changeset

  $ hg backout -r . -m 'Backed out changeset 4910f543acd8'
  reverting foo
  changeset 4:ceac31c0ce89 backs out changeset 3:4910f543acd8
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

  $ hg backout -r . -m 'Backout of ceac31c0ce89 due to bustage'
  reverting foo
  changeset 5:41f80b316d60 backs out changeset 4:ceac31c0ce89
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

Including the local numeric ID is silly and deprecated, but allowed

  $ hg backout -r . -m 'backout 5:41f80b316d60'
  reverting foo
  changeset 6:8b918b1082f8 backs out changeset 5:41f80b316d60
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  Warning: Rev 8b918b1082f8 has malformed backout message.
  added 1 changesets with 1 changes to 1 files

Checking "revert to" syntax

  $ hg backout -r . -m 'Revert to changeset 41f80b316d60 due to incomplete backout'
  reverting foo
  changeset 7:6b805c7a1ea0 backs out changeset 6:8b918b1082f8
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

Multiple changesets should work

  $ hg backout -r . -m 'Backout changesets  9e4ab3907b29, 3abc0dbbf710 due to m-oth permaorange'
  reverting foo
  changeset 8:2d4e565cf83f backs out changeset 7:6b805c7a1ea0
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

Tag syntax should be allowed

  $ echo addedtag > foo
  $ hg commit -m 'Added tag AURORA_BASE_20110412 for changeset 2d4e565cf83f'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

"no bug" should work around bug requirement

  $ echo nobug > foo
  $ hg commit -m 'Fix typo in comment within nsFrame.cpp (no bug) rs=dbaron'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

  $ echo nobug2 > foo
  $ hg commit -m 'Fix ARM assert (no bug, r=cdleary).'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

  $ echo nobugbackout > foo
  $ hg commit -m 'Backout 3b59c196aaf9 - no bug # in commit message'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

Test some bad commit messages

  $ echo massrevert > foo
  $ hg commit -m 'Mass revert m-i to the last known good state'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev 9dafa242bc02 needs "Bug N" or "No bug" in the commit message.
  test
  Mass revert m-i to the last known good state
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo updaterevision > foo
  $ hg commit -m 'update revision of Add-on SDK tests to latest tip; test-only'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev 25cc2437fe62 needs "Bug N" or "No bug" in the commit message.
  test
  update revision of Add-on SDK tests to latest tip; test-only
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo fixstupid > foo
  $ hg commit -m 'Fix stupid bug in foo::bar()'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev b8a6d8dcb77a needs "Bug N" or "No bug" in the commit message.
  test
  Fix stupid bug in foo::bar()
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo firstline > foo
  $ cat >> message << EOF
  > First line does not have a bug number
  > 
  > bug 123456
  > EOF
  $ hg commit -l message
  $ rm message
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev 50d0d93c30bd needs "Bug N" or "No bug" in the commit message.
  test
  First line does not have a bug number
  
  bug 123456
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo imported1 > foo
  $ hg commit -m 'imported patch phishingfixes'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev 8d84ebce3706 needs "Bug N" or "No bug" in the commit message.
  test
  imported patch phishingfixes
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo imported2 > foo
  $ hg commit -m 'imported patch 441197-1'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev 1a6c631a1bbe needs "Bug N" or "No bug" in the commit message.
  test
  imported patch 441197-1
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo backout > foo
  $ hg commit -m "Back out Dao's push because of build bustage"
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  Warning: Rev 0c2851fbf7ba has malformed backout message.
  
  
  ************************** ERROR ****************************
  Backout rev 0c2851fbf7ba needs a bug number or a rev id.
  test
  Back out Dao's push because of build bustage
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo bump > foo
  $ hg commit -m 'Bump mozilla-central version numbers for the next release on a CLOSED TREE'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev 86cf6b0971a5 needs "Bug N" or "No bug" in the commit message.
  test
  Bump mozilla-central version numbers for the next release on a CLOSED TREE
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo bumpsync > foo
  $ hg commit -m 'Bump Sync version to 1.9.0. r=me'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev d856cba17651 needs "Bug N" or "No bug" in the commit message.
  test
  Bump Sync version to 1.9.0. r=me
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo review > foo
  $ hg commit -m "Bug 100 - Foo. r?bar"
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev 46daa311b1ff contains 'r?' in the commit message. Please use 'r=' instead.
  test
  Bug 100 - Foo. r?bar
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

  $ echo review > foo
  $ hg commit -m "Bug 100 - Foo. r?"
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev e56ddd0ce39a contains 'r?' in the commit message. Please use 'r=' instead.
  test
  Bug 100 - Foo. r?
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
  $ hg strip -r . > /dev/null

Ensure `WIP:` commit messages are rejected.

  $ echo a > b
  $ hg -q commit -A -m 'WIP: bug 123: this is a wip r=reviewer'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev c3e477021244 seems to be marked as WIP.
  test
  WIP: bug 123: this is a wip r=reviewer
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]

IGNORE BAD COMMIT MESSAGES should work

  $ echo ignore > foo
  $ hg commit -m 'IGNORE BAD COMMIT MESSAGES'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 2 changesets with 2 changes to 2 files

"try" at the end of words should not trigger the try syntax checking

  $ echo nottry > foo
  $ hg commit -m 'Bug 1084180 - Refine RemoveEntry: Not only remove this entry but also its children if exist. r=dhylands'
  $ hg push
  pushing to $TESTTMP/server
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

  $ cd ..

Reapplying a stripped bundle should not trigger hook

  $ hg init striptest
  $ cd striptest
  $ echo initial > foo
  $ hg -q commit -A -m initial
  $ echo good > foo
  $ hg commit -m 'Bug 123 - Good commit'
  $ hg -q up -r 0
  $ echo 'no bug' > foo
  $ hg commit -m 'bad commit'
  created new head

  $ cat >> .hg/hgrc << EOF
  > [extensions]
  > strip=
  > 
  > [hooks]
  > pretxnchangegroup.commit_message = python:mozhghooks.commit-message.hook
  > EOF

  $ hg strip -r 1 --no-backup

  $ hg log -T '{rev} {desc}\n'
  1 bad commit
  0 initial

Commit message hook allows changes to special vendored directories to go through

  $ hg init server-vendor
  $ cat > server-vendor/.hg/hgrc << EOF
  > [hooks]
  > pretxnchangegroup.commit_message = python:mozhghooks.commit-message.hook
  > EOF

  $ hg -q clone --pull server-vendor client-vendor
  $ cd client-vendor

  $ touch foo
  $ hg -q commit -A -m 'Bug 123 - initial'
  $ hg push
  pushing to $TESTTMP/striptest/server-vendor
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

Messages without "Source-Revision: " aren't excluded

  $ mkdir servo
  $ touch servo/foo
  $ hg -q commit -A -m 'servo: Merge #42 - Do the thing'
  $ hg push
  pushing to $TESTTMP/striptest/server-vendor
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev 4d8b899b5483 needs "Bug N" or "No bug" in the commit message.
  test
  servo: Merge #42 - Do the thing
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]

  $ hg commit --amend -l - << EOF
  > servo: Merge #42 - do the thing
  > 
  > Another line.
  > 
  > Source-Repo: https://github.com/servo/servo
  > Source-Revision: 287b02e21fa2c81d58b070be36add5e951512679
  > EOF
  saved backup bundle to $TESTTMP/striptest/client-vendor/.hg/strip-backup/4d8b899b5483-3f97f200-amend*.hg (glob)

  $ hg push
  pushing to $TESTTMP/striptest/server-vendor
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  (768c84b471a9 looks like a vendoring change; ignoring commit message hook)
  added 1 changesets with 1 changes to 1 files

Malformed backout message in vendored path

  $ touch servo/bar
  $ hg -q commit -A -m 'backout bug 123456'
  $ hg push
  pushing to $TESTTMP/striptest/server-vendor
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev 169f75837913 has malformed backout message.
  test
  backout bug 123456
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]

Well formed backout message in vendored path

  $ hg -q commit --amend -m 'Backout changeset 287b02e21fa2'
  $ hg push
  pushing to $TESTTMP/striptest/server-vendor
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  added 1 changesets with 1 changes to 1 files

Malformed backout message outside of vendored path should be allowed but show
a warning.

  $ mkdir not-vendored
  $ touch not-vendored/foo
  $ hg -q commit -A -m 'backout bug 123456'
  $ hg push
  pushing to $TESTTMP/striptest/server-vendor
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  Warning: Rev 018e10233c06 has malformed backout message.
  added 1 changesets with 1 changes to 1 files

Change a random file and make sure someone isn't cheating the hook

  $ touch not-vendored/bar
  $ hg -q commit -A -l - << EOF
  > servo: Merge #42 - Not really servo
  > 
  > Not a real vendor since file not correct.
  > 
  > Source-Repo: https://github.com/servo/servo
  > Source-Revision: 287b02e21fa2c81d58b070be36add5e951512679
  > EOF

  $ hg push
  pushing to $TESTTMP/striptest/server-vendor
  searching for changes
  adding changesets
  adding manifests
  adding file changes
  
  
  ************************** ERROR ****************************
  Rev b2f8699d705c needs "Bug N" or "No bug" in the commit message.
  test
  servo: Merge #42 - Not really servo
  
  Not a real vendor since file not correct.
  
  Source-Repo: https://github.com/servo/servo
  Source-Revision: 287b02e21fa2c81d58b070be36add5e951512679
  *************************************************************
  
  
  transaction abort!
  rollback completed
  abort: pretxnchangegroup.commit_message hook failed
  [255]
