# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A collection of portable agent skills for creating and maintaining OKF (Open Knowledge Format) knowledge bundles. Skills are plain markdown files (`SKILL.md`) consumed by Claude Code and other compatible agents.

## Skill anatomy

Each skill lives in `skills/<name>/SKILL.md` with YAML frontmatter:

```yaml
---
name: okf:<name>
version: "1.0"
description: >
  One-line description. Usage: /okf:<name> <args>
---
```

The body is the agent's instruction set in plain markdown. No code, no tests, no build step — the skill IS the deliverable.

## Public vs. internal skills

- **Public skills** (`create`, `update`, `edit`, `reconcile`, `search`, `validate`): user-facing, invoked as `/okf:<name>`.
- **Internal skills** (`_read-spec`, `_git-commit`, `_scan-bundle`, `_validate`): prefixed with `_`, called by public skills via `Follow \`okf:_<name>\``. Never invoked directly by the user.

Internal skills are shared sub-procedures extracted to avoid duplication across multiple public skills.

## Skill invocation pattern

Public skills call internal skills with the phrase `Follow \`okf:_skill-name\``. The agent resolves this at runtime by finding the matching SKILL.md in the skills directory. Arguments are passed via the `$ARGUMENTS` variable in the skill body.
