#require docker

  $ . $TESTDIR/hgext/reviewboard/tests/helpers.sh
  $ commonenv

  $ cd client
  $ echo initial > foo
  $ hg -q commit -A -m 'root commit'
  $ hg phase --public -r .

  $ bugzilla create-user author@example.com password 'Patch Author'
  created user 5
  $ bugzilla create-user reviewer@example.com password 'Mozilla Reviewer [:reviewer]' --group editbugs
  created user 6

Create a review

  $ exportbzauth author@example.com password
  $ bugzilla create-bug TestProduct TestComponent 'First Bug'

  $ echo bug > foo
  $ hg commit -m 'Bug 1 - Initial commit to review'
  $ hg --config bugzilla.username=author@example.com push http://localhost:$HGPORT/test-repo > /dev/null

  $ rbmanage add-reviewer $HGPORT1 1 --user reviewer
  1 people listed on review request
  $ rbmanage publish $HGPORT1 1

Sanity check to ensure we have a review flag set

  $ bugzilla dump-bug 1
  Bug 1:
    attachments:
    - attacher: author@example.com
      content_type: text/x-review-board-request
      data: http://localhost:$HGPORT1/r/1/
      description: 'MozReview Request: bz://1/mynick'
      file_name: reviewboard-1-url.txt
      flags:
      - id: 1
        name: review
        requestee: reviewer@example.com
        setter: author@example.com
        status: '?'
      id: 1
      is_obsolete: false
      is_patch: false
      summary: 'MozReview Request: bz://1/mynick'
    blocks: []
    cc:
    - reviewer@example.com
    comments:
    - author: author@example.com
      id: 1
      tags: []
      text: ''
    - author: author@example.com
      id: 2
      tags: []
      text: 'Created attachment 1
  
        MozReview Request: bz://1/mynick
  
  
        /r/2 - Bug 1 - Initial commit to review
  
  
        Pull down this commit:
  
  
        hg pull -r 9bc52583656f082a8ff0c5a8994322ba65688ca5 http://localhost:$HGPORT/test-repo'
    component: TestComponent
    depends_on: []
    platform: All
    product: TestProduct
    resolution: ''
    status: UNCONFIRMED
    summary: First Bug

Publishing a review will clear the r? flag

  $ exportbzauth reviewer@example.com password
  $ rbmanage create-review $HGPORT1 1 --body-top 'I have reservations' --public
  created review 1

  $ bugzilla dump-bug 1
  Bug 1:
    attachments:
    - attacher: author@example.com
      content_type: text/x-review-board-request
      data: http://localhost:$HGPORT1/r/1/
      description: 'MozReview Request: bz://1/mynick'
      file_name: reviewboard-1-url.txt
      flags: []
      id: 1
      is_obsolete: false
      is_patch: false
      summary: 'MozReview Request: bz://1/mynick'
    blocks: []
    cc:
    - reviewer@example.com
    comments:
    - author: author@example.com
      id: 1
      tags: []
      text: ''
    - author: author@example.com
      id: 2
      tags: []
      text: 'Created attachment 1
  
        MozReview Request: bz://1/mynick
  
  
        /r/2 - Bug 1 - Initial commit to review
  
  
        Pull down this commit:
  
  
        hg pull -r 9bc52583656f082a8ff0c5a8994322ba65688ca5 http://localhost:$HGPORT/test-repo'
    - author: reviewer@example.com
      id: 3
      tags: []
      text: 'Comment on attachment 1
  
        MozReview Request: bz://1/mynick
  
  
        http://localhost:$HGPORT1/r/1/#review1
  
  
        I have reservations'
    component: TestComponent
    depends_on: []
    platform: All
    product: TestProduct
    resolution: ''
    status: UNCONFIRMED
    summary: First Bug

Posting a non Ship It review without a review flag adds a comment

  $ rbmanage create-review $HGPORT1 1 --body-top 'One more thing...' --public
  created review 2

  $ bugzilla dump-bug 1
  Bug 1:
    attachments:
    - attacher: author@example.com
      content_type: text/x-review-board-request
      data: http://localhost:$HGPORT1/r/1/
      description: 'MozReview Request: bz://1/mynick'
      file_name: reviewboard-1-url.txt
      flags: []
      id: 1
      is_obsolete: false
      is_patch: false
      summary: 'MozReview Request: bz://1/mynick'
    blocks: []
    cc:
    - reviewer@example.com
    comments:
    - author: author@example.com
      id: 1
      tags: []
      text: ''
    - author: author@example.com
      id: 2
      tags: []
      text: 'Created attachment 1
  
        MozReview Request: bz://1/mynick
  
  
        /r/2 - Bug 1 - Initial commit to review
  
  
        Pull down this commit:
  
  
        hg pull -r 9bc52583656f082a8ff0c5a8994322ba65688ca5 http://localhost:$HGPORT/test-repo'
    - author: reviewer@example.com
      id: 3
      tags: []
      text: 'Comment on attachment 1
  
        MozReview Request: bz://1/mynick
  
  
        http://localhost:$HGPORT1/r/1/#review1
  
  
        I have reservations'
    - author: reviewer@example.com
      id: 4
      tags: []
      text: 'http://localhost:$HGPORT1/r/1/#review2
  
  
        One more thing...'
    component: TestComponent
    depends_on: []
    platform: All
    product: TestProduct
    resolution: ''
    status: UNCONFIRMED
    summary: First Bug

  $ cd ..

Cleanup

  $ mozreview stop
  stopped 5 containers
