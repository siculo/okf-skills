---
name: github-issue
description: >
  Start working on a GitHub issue. Fetches the issue details and automatically
  activates the relevant development skills based on issue labels. Use when the
  user says "work on issue #N", "start issue N", or invokes /github-issue <number>.
  Requires a GitHub issue number as argument.
---

# Work on GitHub Issue

You have been asked to start working on a GitHub issue. Follow these steps:

## Step 1 — Fetch the issue

Run this command to get the issue details (replace `<number>` with the argument):

```bash
gh issue view <number> --json number,title,body,state,labels,assignees
```

If the command fails, inform the user and stop.

## Step 2 — Create the feature branch (if needed)

Check the current git branch. If you are NOT already on a branch that
references this issue number (e.g., `feature/<number>-*`), ask the user
whether they want to create or switch to one.

## Step 3 — Fetch implementation progress from comments

Check the issue comments for an existing **implementation progress** todo list:

```bash
gh api repos/{owner}/{repo}/issues/<number>/comments --jq '.[] | select(.body | contains("## Implementation progress")) | {id: .id, body: .body}'
```

If found:
- Parse the todo list (lines matching `- [x]` and `- [ ]`)
- Present it to the user as the current status, clearly separating done and
  remaining items
- Throughout the session, **update the comment** when tasks are completed:

```bash
gh api repos/{owner}/{repo}/issues/<number>/comments/<comment_id> \
  -X PATCH -f body='<updated body with checkboxes toggled>'
```

If not found, skip this step — the user may add one later.

## Step 4 — Present the issue summary

After activating the skills, present the issue to the user in this format:

```
## Issue #<number>: <title>

**State:** <state>
**Labels:** <comma-separated label names>
**Assignees:** <comma-separated assignee logins, or "none">

<issue body, rendered as markdown>
```

If an implementation progress comment was found in Step 4, append:

```
### Implementation progress

**Done:**
- item 1
- item 2

**Remaining:**
- item 3
- item 4
```

Then ask the user how they would like to proceed with the implementation.
