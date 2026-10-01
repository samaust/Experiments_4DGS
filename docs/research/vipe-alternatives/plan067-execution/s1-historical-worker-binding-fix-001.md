# Historical worker binding regression

The standing retry full-suite run exposed a historical preservation bug after
the worker entrypoint gained generic identity routing. Completed reservation
evidence retained its original worker SHA256 and size, while `lifecycle` and
`canonical_dispatch` compared that evidence against current worker bytes.
The public third-identity admission reproduced the failure at
`S1 lifecycle reservation binding/order` before the fix.

Completed lifecycle snapshots now derive exactly one canonical worker record
from their strictly verified immutable dispatch qualification. If a verified
source requalification event is present, its validation reference supplies the
record. The historical record has an exact path, SHA256 and size schema; its
source file is allowed to have evolved. A private dispatch comparator checks
the historical request, worker evidence and command against that pinned record.

Public `canonical_dispatch`, reservation and active-launch checks continue to
read and verify current worker bytes. No caller can supply historical worker
metadata through the public dispatch interface. The existing public next
identity test additionally rejects old worker evidence for a new dispatch.
Completed history, authorization, qualification and reservation bytes are not
rewritten.

The old clock test now accepts canonical identity 010 and rejects malformed
000 and 0010. The standing fixture qualifies the same canonical worker that
its public reservation consumes, using a link only inside its disposable
source tree.

Validation covered all 25 affected historical identity/review methods, six
standing methods and three current registration/reservation/requalification
methods. The first combined run passed all historical methods and exposed the
standing fixture mismatch, which was corrected before the final standing run.
No GPU execution or live ledger, model or environment changes occurred.
