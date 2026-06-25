---
name: okf:_git-commit
version: "1.0"
description: >
  Internal skill: offer to stage all modified and new files and commit them.
  Called by okf:create, okf:update, okf:reconcile, and okf:edit.
  Never runs git init, never force-pushes, never amends existing commits.
---

If the bundle root is inside a git repository:
1. Offer to stage all modified and new files with `git add`.
2. If the user confirms, commit with the message provided by the calling skill.
3. If the user declines, leave the changes unstaged.

Constraints:
- Never run `git init`.
- Never force-push.
- Never amend existing commits.
