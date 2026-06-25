---
name: okf:_validate
version: "1.0"
description: >
  Internal skill: run a full OKF conformance check on a bundle after changes.
  Called by okf:create, okf:update, okf:reconcile, and okf:edit.
---

Run the same checks defined in `okf:validate` on the bundle.

The bundle must be fully conformant after all changes. If any conformance errors are found:
1. Fix them silently.
2. Re-validate to confirm the bundle is now conformant.
3. Note any fixed regressions in the calling skill's final report.

Do not surface errors to the user unless they cannot be fixed automatically.
