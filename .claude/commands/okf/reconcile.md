---
description: Reconcile an OKF bundle against its source documents, aligning the bundle to the current state of the sources. Usage: /okf:reconcile <source-path> [bundle:<path>]
---

You are reconciling an OKF bundle against a set of source documents. The goal is to bring the bundle into alignment with the *current* state of the sources — handling added, changed, and removed content — while preserving any knowledge that was added manually to the bundle and has no counterpart in the sources.

## 1. Parse arguments

`$ARGUMENTS` may contain:
- A path to the source documents: a file, a directory, or a glob pattern (required).
- `bundle:<path>` — path to the bundle root (default: current working directory).

If no source path is provided, ask the user before proceeding.

## 2. Read the spec

Read `SPEC.md` from the bundle root or a parent directory. Note the current OKF version.

## 3. Read the existing bundle

Scan all concept files recursively. For each, extract:
- Frontmatter: all fields.
- Body: full text, broken into logical sections (headings and their content).
- Cross-links to other concepts.

Build a map: **concept ID → full content**. This is the *bundle state*.

## 4. Read the source documents

Read all source documents at the given path. For each document, extract all knowledge present in the current version: topics, subtopics, facts, schemas, processes, relationships.

Build a map: **topic/entity → knowledge extracted**. This is the *source state*.

## 5. Semantic diff

Compare the bundle state against the source state. Classify each concept and each piece of source knowledge into exactly one category:

- **IN SYNC**: the concept's content faithfully reflects the corresponding source knowledge. No action needed.

- **TO UPDATE**: the concept exists in the bundle and has a counterpart in the sources, but the source content has changed (schema updated, facts revised, sections rewritten). The bundle needs to catch up.

- **STALE**: the concept exists in the bundle and was clearly derived from source content that no longer exists in the current sources. The source knowledge was removed or superseded.

- **NEW IN SOURCES**: knowledge present in the current sources has no corresponding concept in the bundle. A new concept should be created.

- **MANUAL ONLY**: the concept exists in the bundle but has no counterpart in the sources — it was added manually after the bundle was created (editorial notes, playbooks written directly in OKF, etc.). These must be preserved and never touched.

Use semantic reasoning for classification. When a concept partially overlaps with source content (some sections still valid, others outdated), classify it as TO UPDATE and note which sections changed.

When uncertain whether a concept is STALE or MANUAL ONLY, default to MANUAL ONLY — it is safer to preserve and flag than to remove.

## 6. Produce the reconciliation report

Before making any changes, present the full report:

```
OKF Reconciliation Report
─────────────────────────────────────────
Bundle  : <absolute path>
Sources : <source path>  (<N> document(s) read)
Spec    : OKF <version>

IN SYNC        (<N>)  — no action needed
TO UPDATE      (<N>)  — source content changed
STALE          (<N>)  — no longer present in sources
NEW IN SOURCES (<N>)  — missing from bundle
MANUAL ONLY    (<N>)  — preserved as-is

─────────────────────────────────────────
TO UPDATE
  ~ tables/orders.md
      Schema section: 2 columns added, 1 column type changed
      Description outdated: source now describes partitioning strategy

  ~ metrics/revenue.md
      Definition revised in source

STALE
  ! legacy/old-pipeline.md — source content removed; recommend deletion or archival
  ! datasets/staging.md    — no longer referenced in any source document

NEW IN SOURCES
  + tables/returns.md       [type: BigQuery Table] — new table in source schema
  + playbooks/sla-breach.md [type: Playbook]       — new runbook in source docs

MANUAL ONLY (preserved)
  · editorial/glossary.md   — no source counterpart; kept as-is
  · playbooks/oncall.md     — no source counterpart; kept as-is
```

Then ask: **"How do you want to proceed?"** and present these options:

```
Options:
  [A] Apply all recommended changes (updates + additions; mark stale for review)
  [B] Select changes individually
  [C] Cancel
```

Wait for the user's answer before writing anything.

## 7. Handle stale concepts

Never delete stale concepts automatically. Instead, for each STALE concept:
- Add a frontmatter field `stale: true` and `stale_since: <today's date>` to flag it.
- Optionally (ask the user): move it to a `_stale/` subdirectory to keep the main bundle clean.

If the user explicitly confirms deletion of a stale concept, delete the file and remove it from `index.md`. Update all cross-links that pointed to it, replacing them with a note: `[<title>](<path>) *(removed)*`.

## 8. Apply approved changes

Apply in this order:

1. **TO UPDATE**: merge updated content into existing concept files. Update changed sections; preserve unchanged sections and manual edits within the file. Update `timestamp`.
2. **NEW IN SOURCES**: create new concept files following the same rules as `/okf:create` step 5.
3. **STALE**: add `stale: true` / `stale_since:` to frontmatter, or move to `_stale/` if the user chose that option.
4. **Index files**: regenerate `index.md` for every affected directory. If a `_stale/` directory was created, add it to the root `index.md` with a note.
5. **Log file**: prepend an entry to `log.md`:
   ```markdown
   ## <YYYY-MM-DD>
   * **Reconciliation**: Aligned bundle with sources. Updated <N> concepts, added <N>, marked <N> as stale.
   ```

## 9. Git (optional)

If the bundle root contains a git repository, offer to commit with:
`reconcile: align bundle with sources (<N> updated, <N> added, <N> stale)`

## 10. Validate

Run the same checks as `/okf:validate`. The bundle must remain conformant after reconciliation. Fix any regressions silently and note them in the final report.

## 11. Final report

```
OKF Reconciliation complete
─────────────────────────────────────────
Bundle     : <absolute path>
Updated    : <N> concept(s)
Added      : <N> concept(s)
Stale      : <N> concept(s) flagged  (or deleted, if user confirmed)
Preserved  : <N> manual concept(s) untouched
Git        : committed  /  not committed
Validation : ✓ Conformant (OKF <version>)
```
