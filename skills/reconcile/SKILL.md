---
name: okf:reconcile
version: "1.0"
description: >
  Full alignment pass: compare the entire bundle against all source documents and
  handle new content, changed content, and stale concepts in one operation.
  Use when sources have changed substantially or you want a complete sync.
  Use okf:update to add only new documents without touching existing ones;
  use okf:edit for a targeted manual change.
---

You are reconciling an OKF bundle against a set of source documents. The goal is to bring the bundle into alignment with the *current* state of the sources — handling added, changed, and removed content — while preserving any knowledge that was added manually to the bundle and has no counterpart in the sources.

## 1. Parse arguments

`$ARGUMENTS` may contain:
- A path to the source documents: a file, a directory, or a glob pattern (required).
- `bundle:<path>` — path to the bundle root (default: current working directory).

If no source path is provided, ask the user before proceeding.

## 2. Read the spec

Follow `okf:_read-spec`.

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

- **SPLIT**: a single concept file in the bundle covers N distinct named entities, processes, or topics — each of which has a clear, separate counterpart in the source documents. The monolithic file should be replaced with N atomic concept files, following the granularity principle of `/okf:create` §4.1. Indicators: the source document has independent H2/H3 sections for each sub-topic, and each sub-topic is substantial enough to stand alone.

- **STALE**: the concept exists in the bundle and was clearly derived from source content that no longer exists in the current sources. The source knowledge was removed or superseded.

- **NEW IN SOURCES**: knowledge present in the current sources has no corresponding concept in the bundle. A new concept should be created.

- **MANUAL ONLY**: the concept exists in the bundle but has no counterpart in the sources — it was added manually after the bundle was created (editorial notes, playbooks written directly in OKF, etc.). These must be preserved and never touched.

Use semantic reasoning for classification. When a concept partially overlaps with source content (some sections still valid, others outdated), classify it as TO UPDATE and note which sections changed.

When uncertain whether a concept is STALE or MANUAL ONLY, default to MANUAL ONLY — it is safer to preserve and flag than to remove.
When uncertain whether a concept is TO UPDATE or SPLIT, default to SPLIT if the existing file contains multiple distinct named entities each with their own H2/H3 sections.

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
SPLIT          (<N>)  — monolithic concept to break into atomic files
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

SPLIT
  ÷ <group>/<concept>.md → <group>/<concept-a>.md, <group>/<concept-b>.md, … — <reason for split>

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
2. **SPLIT**: for each monolithic concept to split:
   - Create each new atomic concept file following the same rules as `/okf:create` step 5. Add cross-links between the new files where the relationship is meaningful.
   - Delete the original file, unless it has many inbound cross-links — in that case, repurpose it as a redirect stub with a short body pointing to the new files.
   - Update every cross-link in the bundle that pointed to the original file to point to the appropriate new file.
3. **NEW IN SOURCES**: create new concept files following the same rules as `/okf:create` step 5.
4. **STALE**: add `stale: true` / `stale_since:` to frontmatter, or move to `_stale/` if the user chose that option.
5. **Index files**: regenerate `index.md` for every affected directory. If a `_stale/` directory was created, add it to the root `index.md` with a note.
6. **Log file**: prepend an entry to `log.md`:
   ```markdown
   ## <YYYY-MM-DD>
   * **Reconciliation**: Aligned bundle with sources. Updated <N> concepts, split <N>, added <N>, marked <N> as stale.
   * **Split**: Split [<original title>](<original path>) into [<title-a>](<path-a>), [<title-b>](<path-b>), … — <reason>.
   ```

## 9. Git (optional)

Follow `okf:_git-commit` with commit message:
`reconcile: align bundle with sources (<N> updated, <N> added, <N> stale)`

## 10. Validate

Follow `okf:_validate`.

## 11. Final report

```
OKF Reconciliation complete
─────────────────────────────────────────
Bundle     : <absolute path>
Updated    : <N> concept(s)
Split      : <N> concept(s) split into <M> new files
Added      : <N> concept(s)
Stale      : <N> concept(s) flagged  (or deleted, if user confirmed)
Preserved  : <N> manual concept(s) untouched
Git        : committed  /  not committed
Validation : ✓ Conformant (OKF <version>)
Skill version : 1.0
```
