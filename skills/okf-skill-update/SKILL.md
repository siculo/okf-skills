---
name: okf:update
version: "1.0"
description: >
  Add new source documents to an existing OKF bundle; the skill classifies each
  piece of extracted knowledge as new, update, split, or conflict and proposes a
  structured diff before writing anything. Use when you have new files to ingest.
  Use okf:reconcile for a full alignment check against all existing sources;
  use okf:edit for a direct natural-language change that does not involve a source document.
---

You are updating an existing OKF (Open Knowledge Format) bundle with new source documents.

## 1. Parse arguments

`$ARGUMENTS` may contain:
- A path to new source documents: a single file, a directory, or a glob pattern (required).
- `bundle:<path>` — path to the existing bundle root (default: current working directory).

If no source path is provided, ask the user before proceeding.

## 2. Read the spec

Follow `okf:_okf-skill-read-spec`.

## 3. Read the existing bundle

Follow `okf:_okf-skill-scan-bundle`. Use the returned index as the bundle state, including:
- Concept ID → `type`, `title`, `description`, `resource`, `tags`, `timestamp` (and body in full mode).
- Existing cross-links between concepts.
- Current `index.md` contents per directory.

## 4. Read new source documents

Read every source document at the given path. For each, extract the same information as in `/okf:create` step 3: topics, facts, relationships, external resources.

## 5. Classify changes

For each piece of knowledge extracted from the new documents, decide which category it falls into:

- **New concept**: the knowledge describes something not represented by any existing concept. → Create a new `.md` file.
- **Update to existing concept**: the knowledge extends, corrects, or enriches an existing concept (matched by topic, `resource` URI, or semantic similarity). → Merge new content into the existing file; update `timestamp`.
- **Split of existing concept**: the new document provides enough detail about distinct sub-topics within an existing concept file that the file should be broken into multiple atomic files. Apply when an existing file covers N distinct named entities, processes, or ideas — each of which warrants its own file under the granularity principle of `/okf:create` §4.1. → Replace the original file with N atomic concept files; update all cross-links in the bundle that pointed to the original.
- **Conflict**: the new document contradicts or significantly overlaps an existing concept in a way that requires human judgement. → Flag for user review; do not auto-apply.

Use semantic reasoning to make these classifications. When uncertain between "new" and "update", default to "new" and let the user decide. When uncertain between "update" and "split", default to "split" if the existing file contains multiple distinct named entities each with their own H2/H3 sections.

In two-pass mode: read the full body of each candidate concept before classifying it.

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

SPLITS (<N>)
  ÷ <path/to/existing>.md → <group>/<concept-a>.md, <group>/<concept-b>.md, … — <reason for split>

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

### Split concepts
For each split:
- Create each new atomic concept file following the same rules as `/okf:create` step 5.
- Delete the original file, unless it had many inbound cross-links — in that case, repurpose it as a redirect stub with a short body pointing to the new files.
- Update every cross-link in the bundle that pointed to the original file to point to the appropriate new file.
- Add cross-links between the new atomic files where the relationship is meaningful.

### Index files
Regenerate `index.md` for every directory that gained or lost concepts. Preserve any manually written sections in the existing `index.md` — only add or remove entries for the affected concepts.

### Log file
Prepend a new date section to the bundle-root `log.md` (or create it if absent):
```markdown
## <YYYY-MM-DD>
* **Creation**: Added [<title>](<path>) — <description>.   ← for each new concept
* **Update**: Updated [<title>](<path>) — <what changed>.  ← for each updated concept
* **Split**: Split [<original title>](<original path>) into [<title-a>](<path-a>), [<title-b>](<path-b>), … — <reason>.  ← for each split
```

## 8. Git (optional)

Follow `okf:_okf-skill-git-commit` with commit message:
`update: add <N> concepts, update <M> concepts (<source name>)`

## 9. Validate

Follow `okf:_okf-skill-validate`.

## 10. Final report

```
OKF bundle updated
─────────────────────────────────────────
Bundle    : <absolute path>
Added     : <N> new concept(s)
Updated   : <M> existing concept(s)
Split     : <K> concept(s) split into <J> new files
Skipped   : <L> conflict(s) — review manually
Git       : committed  /  not committed
Validation: ✓ Conformant (OKF <version>)
Bundle mode: <full / two-pass (N concepts, threshold 50)>
Skill version: 1.0
```

## 11. Write invocation log

Follow `okf:_okf-skill-write-log` with:
- `skill`: `okf:update`, `version`: `1.0`
- `bundle`: absolute path to the bundle root
- `outcome`: `success` if the final report was printed; `cancelled` if the user declined the proposed changes; `error` if an unrecoverable error occurred
- `concepts_added`: number of new concept files created (N from final report)
- `concepts_updated`: number of existing concepts updated (M from final report)
- `concepts_split`: number of concepts split (K from final report)
- `conflicts`: number of conflicts skipped (L from final report)
- `note`: `null`
