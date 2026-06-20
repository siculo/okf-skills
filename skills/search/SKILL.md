---
name: okf:search
description: >
  Search concepts in an OKF bundle by query, type, tags, or full-text. Usage: /okf:search <query> [type:<Type>] [tags:<tag>,<tag>] [bundle:<path>] [in:title|description|body|all]
---

You are searching an OKF (Open Knowledge Format) bundle for concepts matching the user's query.

## 1. Parse arguments

`$ARGUMENTS` may contain, in any order:
- A free-text query string (the main search terms).
- `type:<value>` — filter by exact or partial `type` match (case-insensitive).
- `tags:<tag1>,<tag2>` — filter to concepts that have ALL the listed tags.
- `bundle:<path>` — path to the bundle root (default: current working directory).
- `in:title` / `in:description` / `in:body` / `in:all` — scope of text search (default: `in:all`).

If `$ARGUMENTS` is empty, ask the user for a query before proceeding.

Examples:
- `/okf:search orders` — full-text search for "orders"
- `/okf:search revenue type:Metric` — find Metrics mentioning revenue
- `/okf:search tags:sales,orders` — all concepts tagged both "sales" and "orders"
- `/okf:search freshness in:body bundle:./my-bundle` — body-only search in a specific bundle

## 2. Locate the bundle

Use the `bundle:` argument if provided, otherwise the current working directory. Verify it is an OKF bundle by checking for at least one `.md` file with frontmatter.

## 3. Build the search index

Scan all concept files (non-reserved `.md` files) recursively. For each, read:
- Frontmatter: `type`, `title`, `description`, `tags`, `resource`, `timestamp`.
- Body: full markdown text.

Do not index `index.md` or `log.md` as searchable concepts.

## 4. Score and rank results

For each concept, compute a relevance score based on:

| Match location              | Weight   |
|-----------------------------|----------|
| `title` exact match         | Highest  |
| `title` partial match       | High     |
| `description` match         | High     |
| `tags` match                | Medium   |
| `type` match                | Medium   |
| Body text match             | Lower    |

Apply filters first (`type:`, `tags:`, `in:`), then rank by score. Return all matches above a relevance threshold; if no matches exceed the threshold, return the top 5 regardless and note low confidence.

For semantic relevance (e.g., "revenue" matching a concept about "income"), use your language understanding — OKF search is agent-native and does not require exact string matching.

## 5. Display results

Print results in this format:

```
OKF Search: "<query>"
Bundle: <path>  |  Scanned: <N> concepts
─────────────────────────────────────────
<rank>. [<title>](<bundle-relative path>)
   Type: <type>  |  Tags: <tags>
   <description>
   Match: <where the match was found and a short excerpt>

<rank>. [<title>](<bundle-relative path>)
   …

─────────────────────────────────────────
<N> result(s)  |  Filters: <active filters or "none">
```

If there are no results:
```
No results for "<query>" in <N> concepts.
Suggestions:
  - Try broader terms
  - Available types: <list all distinct type values in the bundle>
  - Available tags: <list all distinct tags in the bundle>
```

## 6. Follow-up

After displaying results, offer these actions the user can take:
- **Open a result**: "Type the number of a result to read the full concept."
- **Refine search**: "Add `type:X` or `tags:Y` to narrow results."
- **Related concepts**: if the user selects a result, show its cross-links as further exploration paths.

If the user selects a result by number, read and display the full concept file (frontmatter + body), formatted as readable markdown. Then offer to open related concepts reachable via its cross-links.
