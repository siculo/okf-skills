---
name: okf:_scan-bundle
version: "1.0"
description: >
  Internal skill: scan all concept files in an OKF bundle, choose between full
  and two-pass read mode based on bundle size, and return an index map.
  Called by okf:update, okf:reconcile, and okf:search.
---

Scan the bundle root provided by the calling skill.

## 1. Identify concept files

Find all `.md` files recursively inside the bundle root. Exclude reserved filenames (`index.md`, `log.md`).

Let **N** = total count of concept files found.

## 2. Choose read mode

| Condition | Mode         | What to read                       |
|-----------|--------------|------------------------------------|
| N ≤ 50    | **full**     | Frontmatter + body for all N files |
| N > 50    | **two-pass** | Frontmatter only for all N files   |

## 3. Build the index

For each concept file, read the fields appropriate to the chosen mode and build an index map:

**concept path → { type, title, description, tags, resource, timestamp [, body] }**

In two-pass mode, `body` is omitted from the map. The calling skill must read the full body on demand, only when a concept becomes a candidate for change, match, or semantic diff (Pass 2).

## 4. Return to the calling skill

Provide:
- **mode** — `full` or `two-pass`
- **count** — N
- **index** — the map built in step 3

The calling skill must include the following line in its final report when mode is `two-pass`:

> `Bundle mode: two-pass (N concepts, threshold 50)`
