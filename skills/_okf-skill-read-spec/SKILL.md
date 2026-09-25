---
name: okf:_okf-skill-read-spec
version: "1.0"
description: >
  Internal skill: locate SPEC.md and extract the OKF version and conformance rules.
  Called by okf:create, okf:update, okf:reconcile, and okf:edit.
---

Locate `SPEC.md` using the following search order:

1. The bundle root (or current working directory when called from `okf:create`).
2. Parent directories, walking up to the filesystem root.
3. If still not found, fetch from the upstream repository:
   `https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md`

Extract and return to the calling skill (locate sections by title, not by number, since numbering changes between spec versions):
- The OKF version (for the `okf_version` field in the root `index.md`).
- Frontmatter field definitions ("Frontmatter" section).
- Reserved filenames and their required structure ("Reserved filenames", "Index files" and "Log files" sections).
- Conformance rules ("Conformance" section).
