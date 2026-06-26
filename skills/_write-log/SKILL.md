---
name: okf:_write-log
version: "1.0"
description: >
  Internal skill: append one JSON line to .claude/invocation-log.jsonl at the
  repository root. Called at the end of each public okf skill.
---

You are writing one structured log entry for a completed skill invocation.

## 1. Collect fields from the calling context

The calling skill provides these values inline:

| Field              | Description                                              |
|--------------------|----------------------------------------------------------|
| `skill`            | `okf:<skill-name>` (e.g. `okf:create`)                  |
| `version`          | Skill version string from frontmatter (e.g. `"1.0"`)    |
| `bundle`           | Absolute path to the bundle root used in this invocation |
| `outcome`          | `success`, `conflict`, `error`, or `cancelled`           |
| `concepts_added`   | Integer or `null`                                        |
| `concepts_updated` | Integer or `null`                                        |
| `concepts_split`   | Integer or `null`                                        |
| `conflicts`        | Integer or `null`                                        |
| `note`             | Short human-readable string or `null`                    |

Generate `ts` yourself: current datetime in ISO 8601 UTC format (e.g. `2026-06-26T14:05:00Z`).

## 2. Find the repository root

Run:
```bash
git rev-parse --show-toplevel
```

If the command fails (not a git repo), use the current working directory as the root.

## 3. Build the JSON line

Construct a single-line JSON object with keys in this exact order:

```json
{"ts":"<ts>","skill":"<skill>","version":"<version>","args":"<args>","bundle":"<bundle>","outcome":"<outcome>","concepts_added":<concepts_added>,"concepts_updated":<concepts_updated>,"concepts_split":<concepts_split>,"conflicts":<conflicts>,"note":<note>}
```

- String values must be JSON-escaped.
- `null` values must be the JSON literal `null`, not the string `"null"`.
- The `note` field: use `null` if not applicable, otherwise a JSON string.
- Do not pretty-print; the entire object must fit on one line.

## 4. Append to the log file

Target path: `<repo-root>/.claude/invocation-log.jsonl`

```bash
mkdir -p <repo-root>/.claude
echo '<json-line>' >> <repo-root>/.claude/invocation-log.jsonl
```

Never overwrite or truncate the file. Always append (`>>`).

If the append fails, print a one-line warning and continue — do not abort the calling skill's flow.
