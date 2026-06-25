---
name: okf:_scan-bundle
version: "1.2"
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

## 2. Fallback A: Python inline (script not found, Python available)

If the script is not found but Python 3 is available, enumerate concept files with:

```bash
python3 -c "
import pathlib, json, sys
root = pathlib.Path(sys.argv[1])
files = sorted(str(f.relative_to(root)) for f in root.rglob('*.md') if f.name not in {'index.md', 'log.md'} and not (f.parent == root and f.name in {'README.md', 'SPEC.md'}) and not any(p.startswith('.') for p in f.relative_to(root).parts))
print(json.dumps(files))
" <bundle_root>
```

Use the resulting file list to determine **N**, choose the read mode (§3 table), then read each file using the `Read` tool: full file in full mode, or with `limit: 30` in two-pass mode to capture only the frontmatter. Build the index map manually. Skip to §4.

## 3. Fallback B: native tools only (Python unavailable)

If Python is not available, traverse the directory tree using the `Read` tool:

1. Read the bundle root directory to list its contents.
2. Recurse into each subdirectory, collecting all `.md` files. Exclude `index.md` and `log.md`.
3. Let **N** = total count of files collected.

Choose the read mode:

| Condition | Mode         | What to read                       |
|-----------|--------------|------------------------------------|
| N ≤ 50    | **full**     | Frontmatter + body for all N files |
| N > 50    | **two-pass** | Frontmatter only (use `limit: 30`) |

Build an index map: **concept path → { type, title, description, tags, resource, timestamp [, body] }**

In two-pass mode, `body` is omitted. The calling skill must read the full body on demand, only when a concept becomes a candidate for change, match, or semantic diff (Pass 2).

## 4. Return to the calling skill

Provide:
- **mode** — `full` or `two-pass`
- **count** — N
- **index** — the map built in §1, §2, or §3

The calling skill must include the following line in its final report when mode is `two-pass`:

> `Bundle mode: two-pass (N concepts, threshold 50)`
