---
description: Update an existing OKF bundle with new source documents. Usage: /okf:update <source-path> [bundle:<bundle-path>]
---

You are updating an existing OKF (Open Knowledge Format) bundle with new source documents.

## 1. Parse arguments

`$ARGUMENTS` may contain:
- A path to new source documents: a single file, a directory, or a glob pattern (required).
- `bundle:<path>` — path to the existing bundle root (default: current working directory).

If no source path is provided, ask the user before proceeding.

## 2. Read the spec

Read `SPEC.md` from the bundle root, or if not found there, from parent directories. Extract the current OKF version and conformance rules. This ensures update logic reflects the current spec.

## 3. Read the existing bundle

Scan the bundle recursively. For each concept file, read its frontmatter and body. Build an internal map of:
- Concept ID → `type`, `title`, `description`, `resource`, `tags`, `timestamp`, body summary.
- Existing cross-links between concepts.
- Current `index.md` contents per directory.

## 4. Read new source documents

Read every source document at the given path. For each, extract the same information as in `/okf:create` step 3: topics, facts, relationships, external resources.

## 5. Classify changes

For each piece of knowledge extracted from the new documents, decide which category it falls into:

- **New concept**: the knowledge describes something not represented by any existing concept. → Create a new `.md` file.
- **Update to existing concept**: the knowledge extends, corrects, or enriches an existing concept (matched by topic, `resource` URI, or semantic similarity). → Merge new content into the existing file; update `timestamp`.
- **Conflict**: the new document contradicts or significantly overlaps an existing concept in a way that requires human judgement. → Flag for user review; do not auto-apply.

Use semantic reasoning to make these classifications. When uncertain between "new" and "update", default to "new" and let the user decide.

## 6. Propose changes

Before writing anything, present a structured diff to the user:

```
Proposed changes to: <bundle root path>
─────────────────────────────────────────
NEW CONCEPTS (<N>)
  + <group>/<concept>.md  [type: <Type>] — <one-line description>
  + <group>/<concept>.md  [type: <Type>] — <one-line description>

UPDATES TO EXISTING CONCEPTS (<N>)
  ~ <path/to/concept>.md — <what changes: new section added / description revised / schema extended / …>

CONFLICTS — REQUIRES YOUR INPUT (<N>)
  ! <path/to/concept>.md — <describe the conflict>

INDEX FILES TO REGENERATE (<N>)
  ↻ <dir>/index.md

LOG ENTRY
  log.md — will add entry for <today's date>
```

Ask: **"Apply these changes? (yes / no / describe adjustments)"**

Wait for the user's answer. If they request adjustments, revise and show the proposal again. For conflicts, present each one individually and ask the user how to resolve it before including it in the plan.

## 7. Apply changes

After user approval:

### New concepts
Write each new concept file following the same rules as `/okf:create` step 5. Add cross-links to related existing concepts where appropriate.

### Updated concepts
For each updated concept:
- Merge new content into the body. Prefer adding new sections or extending existing ones over rewriting existing prose.
- Update `timestamp` to the current datetime.
- Do NOT change `type` or `resource` unless the update explicitly requires it.
- Preserve all existing frontmatter keys, including producer-defined extensions.

### Index files
Regenerate `index.md` for every directory that gained or lost concepts. Preserve any manually written sections in the existing `index.md` — only add or remove entries for the affected concepts.

### Log file
Prepend a new date section to the bundle-root `log.md` (or create it if absent):
```markdown
## <YYYY-MM-DD>
* **Creation**: Added [<title>](<path>) — <description>.   ← for each new concept
* **Update**: Updated [<title>](<path>) — <what changed>.  ← for each updated concept
```

## 8. Git (optional)

If the bundle root contains a git repository:
- After applying changes, offer to stage all modified and new files and commit with message:
  `update: add <N> concepts, update <M> concepts (<source name>)`
- If the user declines, leave the changes unstaged.

## 9. Validate

Run the same checks as `/okf:validate` on the bundle after changes. The bundle must remain fully conformant. Fix any conformance errors silently before reporting.

## 10. Final report

```
OKF bundle updated
─────────────────────────────────────────
Bundle    : <absolute path>
Added     : <N> new concept(s)
Updated   : <M> existing concept(s)
Skipped   : <K> conflict(s) — review manually
Git       : committed  /  not committed
Validation: ✓ Conformant (OKF <version>)
```
