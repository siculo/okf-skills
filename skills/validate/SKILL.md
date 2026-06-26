---
name: okf:validate
version: "1.0"
description: >
  Validate an OKF bundle for conformance with the current spec. Usage: /okf:validate [bundle-path]
---

You are validating an OKF (Open Knowledge Format) bundle for conformance.

## 1. Setup

Determine the bundle root:
- If `$ARGUMENTS` contains a path, use it as the bundle root.
- Otherwise use the current working directory.

Find the OKF specification:
- Look for `SPEC.md` at the bundle root.
- If not found, search parent directories up to the filesystem root.
- If still not found, fetch it from the upstream repository:
  `https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md`
- Extract the conformance rules from §9 of that file. This ensures validation always reflects the current version of the spec, not hardcoded rules.

If `SPEC.md` cannot be found or fetched, report the error and stop.

## 2. Scan the bundle

Collect all `.md` files in the bundle tree recursively. Classify each as:
- **Reserved**: filename is `index.md` or `log.md` (at any level).
- **Infrastructure**: `README.md` or `SPEC.md` located directly at the bundle root, or any file inside a hidden directory (path component starting with `.`, e.g. `.claude/`). These are not OKF concept files and must be silently skipped — do not validate them and do not report them as errors.
- **Concept**: all other `.md` files.

## 3. Hard conformance checks (errors — make the bundle non-conformant per §9)

For each **concept** file:
- [ ] File contains a valid YAML frontmatter block delimited by `---`.
- [ ] Frontmatter contains a non-empty `type` field.

For each **`index.md`**:
- [ ] Contains no frontmatter, EXCEPT the bundle-root `index.md` which MAY have frontmatter containing `okf_version`.
- [ ] Body uses the list format described in §6 (headings + bullet list of links).

For each **`log.md`**:
- [ ] Date headings are in ISO 8601 `YYYY-MM-DD` format as described in §7.

## 4. Soft checks (warnings — spec guidance, not hard requirements)

For each concept file:
- [ ] Has a `title` field (recommended).
- [ ] Has a `description` field (recommended).
- [ ] `timestamp`, if present, is a valid ISO 8601 datetime.
- [ ] Cross-links to other `.md` files within the bundle resolve to existing files.

For each directory:
- [ ] An `index.md` exists (not required, but recommended).
- [ ] All concept files in the directory are listed in the local `index.md`, when one exists.

## 5. Report

Print the report in this exact format:

```
OKF Validation Report
─────────────────────────────────────────
Bundle : <absolute bundle root path>
Spec   : OKF <version from SPEC.md, e.g. 0.1>
Scanned: <N> concept files, <M> reserved files

ERRORS (<count>)
  path/to/file.md — Missing frontmatter
  path/to/file.md — Missing required field: type
  path/to/index.md — Frontmatter present on non-root index

WARNINGS (<count>)
  path/to/file.md — Missing recommended field: title
  path/to/file.md — Broken link → ./missing.md
  tables/ — index.md missing entries for: orders.md, customers.md

RESULT: ✓ Conformant   (or)   ✗ Not conformant — <N> error(s)
Skill version : 1.0
```

## 6. Offer to fix

After reporting:
- If there are **errors**: ask the user whether to fix them automatically (add missing frontmatter skeleton with a placeholder `type: Unknown`, fix malformed date headings in log.md, etc.). Apply fixes only with user approval.
- If there are only **warnings**: offer to auto-fix safe ones (add missing `index.md` entries, sort log entries by date descending). Apply only with user approval.
- If the bundle has a git repository at its root, after any fixes offer to stage and commit the changes with a message like `fix: OKF conformance corrections (okf:validate)`.

## 7. Write invocation log

Follow `okf:_write-log` with:
- `skill`: `okf:validate`, `version`: `1.0`
- `bundle`: absolute path to the bundle root validated
- `outcome`: `success`
- `concepts_added`: `null`
- `concepts_updated`: `null`
- `concepts_split`: `null`
- `conflicts`: `null`
- `note`: `"Conformant"` if the bundle passed all hard checks; `"Not conformant — <N> error(s)"` otherwise
