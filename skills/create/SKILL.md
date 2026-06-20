---
name: okf:create
description: >
  Create a new OKF bundle from source documents. Usage: /okf:create <source-path> [output:<bundle-path>] [git:yes|no]
---

You are creating a new OKF (Open Knowledge Format) bundle from one or more source documents.

## 1. Parse arguments

`$ARGUMENTS` may contain:
- A path to source documents: a single file, a directory, or a glob pattern (required).
- `output:<path>` — destination directory for the new bundle (default: `./okf-bundle`).
- `git:yes` or `git:no` — whether to initialize a git repository (default: ask at the end).

If no source path is provided, ask the user before proceeding.

## 2. Read the spec

Find `SPEC.md`:
- Look in the current working directory first.
- If not found, search parent directories up to the filesystem root.
- If still not found, fetch it from the upstream repository:
  `https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md`

Extract:
- The OKF version (for the `okf_version` field in the root `index.md`).
- Frontmatter field definitions (§4.1).
- Reserved filenames and their required structure (§3.1, §6, §7).
- Conformance rules (§9).

## 3. Read source documents

Read every source document at the given path. Supported formats: `.md`, `.txt`, `.pdf`, `.csv`, and any other readable format. For each document, extract:
- Main topic and subtopics.
- Key facts, definitions, processes, schemas, or relationships described.
- Any explicit references to external resources (URLs, system names, table names, etc.).
- Relationships between topics that could become cross-links.

## 4. Design the bundle structure

From the extracted knowledge, decide:
1. **Concepts**: what distinct concepts to create. Each concept is one `.md` file. Prefer granular concepts over monolithic ones — if a source document covers five distinct topics, create five concept files.
2. **Types**: assign a `type` to each concept. Be descriptive and consistent within the bundle (e.g., `Metric`, `BigQuery Table`, `API Endpoint`, `Playbook`, `Reference`). Use the same type string for the same kind of thing across all concepts.
3. **Hierarchy**: group concepts into subdirectories by domain or category, not by source file. A concept from document A and a concept from document B may belong in the same subdirectory.
4. **Cross-links**: identify relationships between concepts that should be expressed as markdown links in the body.
5. **Tags**: identify cross-cutting tags.

**Before writing any files**, present the proposed structure to the user:

```
Proposed OKF bundle: <output path>
─────────────────────────────────────────
<bundle-root>/
├── index.md
├── log.md
├── <group>/
│   ├── index.md
│   ├── <concept>.md
│   └── <concept>.md
└── <group>/
    ├── index.md
    └── <concept>.md

Concepts : <N>
Types    : <list of distinct type values>
Tags     : <list of distinct tags>
Source   : <N> document(s) read
```

Ask: **"Proceed with this structure? (yes / no / describe changes)"**

Wait for the user's answer. If they request changes, revise the structure and show it again before writing.

## 5. Write the bundle

After user approval:

### Concept files
For each concept, write a `.md` file at the planned path with:
- Frontmatter:
  - `type`: as decided
  - `title`: human-readable display name
  - `description`: one sentence summarizing the concept
  - `resource`: canonical URI if the concept describes a concrete external asset; omit otherwise
  - `tags`: YAML list of relevant tags
  - `timestamp`: current datetime in ISO 8601 (UTC)
- Body: structured markdown derived from the source content. Use headings, lists, and tables. Add cross-links to related concepts using bundle-relative paths (starting with `/`). Include a `# Citations` section if claims are sourced from external material.

### Index files
For each directory (including the root), write `index.md` with no frontmatter. Exception: the root `index.md` MAY include frontmatter with `okf_version`. Format per §6:
```markdown
# <Directory / Group Name>

* [Title](./concept.md) - description from frontmatter
* [Subdirectory](./subdir/) - what this group contains
```

### Log file
Write `log.md` at the bundle root. Format per §7, with today's date and one entry per concept created:
```markdown
# Bundle Update Log

## <YYYY-MM-DD>
* **Creation**: Initialized OKF bundle from <N> source document(s).
* **Creation**: Added [<title>](<path>) — <description>.
…
```

### Skill files
Copy all skill files found in `skills/` (relative to the current working directory) into `<bundle-root>/skills/`.

Then fetch `SPEC.md` from the upstream repository and write it to `<bundle-root>/SPEC.md`:
`https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md`

This makes the bundle self-maintaining: anyone who clones it gets all the skills and the version of the spec it was built against, with no additional setup required.

## 6. Git (optional)

If `git:yes` was specified, or if not specified and the user confirms:
1. Run `git init` in the bundle root.
2. Run `git add .`
3. Commit with message: `Initialize OKF bundle (<N> concepts, <M> types)`

If the bundle root is already inside a git repository, skip `git init` and instead offer to stage and commit the new bundle directory.

## 7. Validate

Run the same checks as `/okf:validate` on the newly created bundle. The bundle must be fully conformant. If any errors are found, fix them silently and re-validate before reporting.

## 8. Final report

```
OKF bundle created
─────────────────────────────────────────
Path      : <absolute path>
Concepts  : <N> files across <M> directories
Types     : <list>
Git       : initialized with initial commit  /  not initialized
Validation: ✓ Conformant (OKF <version>)

The bundle includes /okf:validate and /okf:create — open it in Claude Code to use them.
```
