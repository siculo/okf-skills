#!/usr/bin/env python3
"""Scan an OKF bundle and output an index map as JSON.

Usage: scan_bundle.py <bundle_root>

Exits 0 with JSON on stdout, exits 1 with error on stderr.
"""

import json
import re
import sys
from pathlib import Path

THRESHOLD = 50
RESERVED = {"index.md", "log.md"}
FRONTMATTER_FIELDS = ("type", "title", "description", "tags", "resource", "timestamp")


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 4:].lstrip("\n")

    fields = {}
    lines = fm_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^([\w][\w_-]*):\s*(.*)', line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val == "" or val is None:
                # possible multi-line list
                items = []
                i += 1
                while i < len(lines) and lines[i].startswith("  - "):
                    items.append(lines[i][4:].strip())
                    i += 1
                fields[key] = items
                continue
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                fields[key] = [v.strip().strip("\"'") for v in inner.split(",") if v.strip()]
            elif val.startswith('"') and val.endswith('"'):
                fields[key] = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                fields[key] = val[1:-1]
            else:
                fields[key] = val
        i += 1

    return fields, body


def scan(bundle_root):
    root = Path(bundle_root).resolve()
    if not root.is_dir():
        print(f"Error: {bundle_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    concept_files = sorted(
        f for f in root.rglob("*.md") if f.name not in RESERVED
    )
    count = len(concept_files)
    mode = "full" if count <= THRESHOLD else "two-pass"

    index = {}
    for f in concept_files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as e:
            print(f"Warning: could not read {f}: {e}", file=sys.stderr)
            continue
        fm, body = parse_frontmatter(text)
        entry = {k: fm.get(k, "") for k in FRONTMATTER_FIELDS}
        if mode == "full":
            entry["body"] = body
        index[str(f.relative_to(root))] = entry

    return {"mode": mode, "count": count, "index": index}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: scan_bundle.py <bundle_root>", file=sys.stderr)
        sys.exit(1)
    result = scan(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
