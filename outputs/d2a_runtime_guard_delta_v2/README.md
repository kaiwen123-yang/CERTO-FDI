# Small metadata guard delta V2

This supplements immutable outputs/d2a_runtime_checkpoint_v1. Its base manifest
SHA256 is 13e6aed87eee6eb422ff680946c68aada226f849f1de1562e9f811fcfb6b0005.
It preserves C1/C2 guard fixes and the readonly full-grid metadata validator,
not science data, current locks/PIDs, a full D2 result or a final science release.

Verify this directory with python -S -B verify_delta.py. Before restoring in
a fresh separate workspace, first verify/restore V1 and its exact R1 bootstrap,
then overlay the listed relative sources. Check their original/before hashes
in the fix report; refuse to overwrite unrelated edits. Never overlay an active
science workspace automatically, rerun preflight over frozen directions, or
relabel these metadata checks as full science/ZIP acceptance.

The active full-grid script remains metadata-only. Big witnesses and required
standalone arithmetic/actual-ZIP replay remain separate gates.
