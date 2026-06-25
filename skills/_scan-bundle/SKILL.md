---
name: okf:_scan-bundle
version: "1.1"
description: >
  Internal skill: scan all concept files in an OKF bundle, choose between full
  and two-pass read mode based on bundle size, and return an index map.
  Called by okf:update, okf:reconcile, and okf:search.
---

Scan the bundle root provided by the calling skill.

## 1. Run the scanner script (preferred)

Look for `scan_bundle.py` in these locations, in order:

1. `skills/_scan-bundle/scan_bundle.py` (relative to the current working directory)
2. `~/.claude/skills/_scan-bundle/scan_bundle.py`

If found and Python 3 is available, run:

```bash
python3 <path>/scan_bundle.py <bundle_root>
```

The script outputs JSON to stdout:

```json
{
  "mode": "full | two-pass",
  "count": 42,
  "index": {
    "group/concept.md": {
      "type": "...", "title": "...", "description": "...",
      "tags": [], "resource": "...", "timestamp": "...",
      "body": "..."
    }
  }
}
```

Parse this output and use it as the result of this skill. Skip to §4.

## 2. Fallback: identify concept files manually

If the script is not found or fails, proceed manually.

Find all `.md` files recursively inside the bundle root using:

```bash
find <bundle_root> -name "*.md" ! -name "index.md" ! -name "log.md"
```

Let **N** = total count of files found.

## 3. Fallback: choose read mode and build the index

| Condition | Mode         | What to read                       |
|-----------|--------------|------------------------------------|
| N ≤ 50    | **full**     | Frontmatter + body for all N files |
| N > 50    | **two-pass** | Frontmatter only for all N files   |

For each concept file, read the fields appropriate to the chosen mode:

- **Full mode**: read the entire file.
- **Two-pass mode**: read only the frontmatter (lines from the first `---` to the closing `---`, typically within the first 20–30 lines). Use the `Read` tool with `limit: 30`.

Build an index map: **concept path → { type, title, description, tags, resource, timestamp [, body] }**

In two-pass mode, `body` is omitted. The calling skill must read the full body on demand, only when a concept becomes a candidate for change, match, or semantic diff (Pass 2).

## 4. Return to the calling skill

Provide:
- **mode** — `full` or `two-pass`
- **count** — N
- **index** — the map built in §1 or §3

The calling skill must include the following line in its final report when mode is `two-pass`:

> `Bundle mode: two-pass (N concepts, threshold 50)`
