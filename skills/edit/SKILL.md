---
name: okf:edit
version: "1.0"
description: >
  Modify an OKF bundle based on a natural-language instruction (rename, move, merge,
  add a section, bulk-tag). Use when you know exactly what to change and do not have
  a source document to ingest. Use okf:update to ingest new source documents;
  use okf:reconcile for a full source-alignment pass.
---

You are editing an OKF (Open Knowledge Format) bundle based on the user's instructions.

## 1. Parse arguments

`$ARGUMENTS` may contain:
- A natural language instruction describing what to change (required). May be quoted or unquoted.
- `bundle:<path>` — path to the bundle root (default: current working directory).

If no instruction is provided, ask the user what they want to change before proceeding.

## 2. Classify the instruction

Understand what the user wants. Instructions fall into these categories — a single instruction may combine several:

**Content edits** — modifying the text of one or more concept files:
- Rewriting or extending a body section (`# Schema`, `# Examples`, etc.)
- Adding or removing a section
- Correcting factual content
- Updating `description`, `title`, or other frontmatter fields

**Structural edits** — changing the organization of the bundle:
- Renaming a concept file or directory
- Moving concepts between directories
- Splitting one concept into multiple files
- Merging multiple concepts into one
- Creating or deleting concepts

**Bulk edits** — applying a uniform change across multiple concepts:
- Changing a `type` value across all matching concepts
- Adding or removing a tag from a set of concepts
- Adding a section to all concepts of a given type
- Normalizing frontmatter fields (e.g., converting `timestamp` to UTC)

**Cross-link edits** — modifying how concepts reference each other:
- Fixing broken links
- Converting relative links to absolute (bundle-relative) links or vice versa
- Adding links between concepts that should be related but aren't

Identify the category, the **scope** (single concept / directory / whole bundle / cross-cutting filter), and the **target** (which files are affected).

## 3. Read the relevant portion of the bundle

- For single-concept edits: read only that file.
- For directory-scoped edits: read all concept files in that directory.
- For whole-bundle or bulk edits: scan all concepts and read the files that match the filter implied by the instruction.

Also read the affected `index.md` files and `log.md`.

## 4. Plan the changes

Before writing anything, produce a clear plan:

```
Edit plan
─────────────────────────────────────────
Instruction : "<user instruction>"
Scope       : <single concept / <N> concepts / whole bundle>
Bundle      : <path>

CHANGES (<N> files)
  ~ path/to/concept.md
      [field] description: "old value" → "new value"
      [body]  Added section "# Usage" with <N> lines
      [move]  → new/path/concept.md

  ~ path/to/other.md
      [type]  "BigQuery Table" → "Table"

INDEX UPDATES (<N>)
  ↻ tables/index.md  — reflects rename

LOG ENTRY
  log.md — will add **Edit** entry for today
```

For **destructive changes** (deleting concepts, merging files, removing sections), call them out explicitly:

```
DESTRUCTIVE CHANGES — review carefully
  ✗ legacy/old-concept.md — will be deleted
  ✗ tables/orders.md (body section "# Old Notes") — will be removed
```

Ask: **"Apply these changes? (yes / no / describe adjustments)"**

Wait for the user's answer. If they request adjustments, revise the plan and show it again. Never apply any change without explicit approval.

## 5. Apply changes

After user approval, apply in this order to avoid broken intermediate states:

1. **Content edits**: rewrite fields and body sections as planned. Preserve all frontmatter keys not mentioned in the plan. Update `timestamp` to the current datetime on any concept whose content changed.
2. **Structural edits**:
   - Renames/moves: write the file at the new path, delete the old one, update all cross-links in the bundle that pointed to the old path.
   - Splits: write the new concept files, remove the original, update cross-links.
   - Merges: write the merged concept, remove the originals, update cross-links.
3. **Index files**: regenerate `index.md` for every affected directory. Preserve any manually written content not related to the changed concepts.
4. **Log file**: prepend an entry to `log.md` at the bundle root:
   ```markdown
   ## <YYYY-MM-DD>
   * **Edit**: <concise description of what changed and why, derived from the instruction>.
   ```

## 6. Cross-link integrity

After all changes, scan the bundle for broken links caused by the edit (renamed or deleted files). Report any that remain and offer to fix them. Do not leave the bundle in a state with newly introduced broken links without warning the user.

## 7. Git (optional)

If the bundle root contains a git repository, offer to stage all modified files and commit with a message derived from the instruction:
`edit: <concise description of the change>`

## 8. Validate

Run the same checks as `/okf:validate`. The bundle must remain conformant after the edit. Fix any conformance regressions silently and note them in the final report.

## 9. Final report

```
OKF bundle edited
─────────────────────────────────────────
Bundle     : <absolute path>
Changed    : <N> concept file(s)
Structural : <renames / moves / splits / merges, or "none">
Links fixed: <N> cross-links updated
Git        : committed  /  not committed
Validation : ✓ Conformant (OKF <version>)
Skill version : 1.0
```

## Examples of valid instructions

- `"Rename type 'BigQuery Table' to 'Table' everywhere"`
- `"Move all concepts tagged 'legacy' into a new legacy/ directory"`
- `"Add a # Usage section to tables/orders.md explaining how to query it"`
- `"Split tables/customers.md into two concepts: one for schema, one for PII handling"`
- `"Convert all relative cross-links to absolute bundle-relative paths"`
- `"Remove the tag 'wip' from all concepts that have a description"`
- `"Merge datasets/sales.md and datasets/marketing.md into a single datasets/commercial.md"`
