---
title: Session File Names
description: How files in uc-node's sessions directory are named, by repository, piece of work and kind of record, and what goes in their front matter.
version: 0.1.0
status: provisional
date: 2026-11-23
language: en-CA
---

# Session File Names

This directory holds the records of working sessions on uc-node with Claude: the plan and kickoff prompt that start a piece of work, and the reports written at each stop along the way.

## The pattern

Every file is named after the repository, the piece of work, and the kind of record, in lower case with words separated by hyphens:

```text
uc-node-<work>-<kind>.md
```

For example:

```text
uc-node-platforms-plan-and-kickoff.md
uc-node-platforms-phase-one-report.md
uc-node-platforms-phase-two-report.md
```

| Part | Meaning | Example |
| :-- | :-- | :-- |
| `uc-node` | The repository, so a file still says where it belongs when it is copied elsewhere | `uc-node` |
| `<work>` | A short name for the piece of work, the same in every file that belongs to it | `platforms` |
| `<kind>` | What the file records | `plan-and-kickoff` |

Named this way, an alphabetical listing groups each piece of work together, with its plan first and its reports after it.

## The kinds of record

| Kind | What it holds | Written by |
| :-- | :-- | :-- |
| `plan-and-kickoff` | Where the repository stands, the plan in phases, and the kickoff prompt for Claude Code | Claude, in chat, before the work starts |
| `phase-<number>-report` | What one phase changed, the checks it ran and their results, and what to know before the next phase | Claude Code, at the end of that phase |
| `session` | The record of a working session that is not split into phases | Whoever runs the session |

Phase numbers are written as words, `phase-one`, `phase-two`, to match the headings inside the files.

## Front matter

Every file starts with the same front matter as the other documents under `en/docs/`:

```yaml
---
title: Platforms for uc-node, Phase One Report
description: What phase one of the platforms work changed, the checks it passed, and what to know before phase two.
version: 0.1.0
status: provisional
date: 2026-11-23
language: en-CA
---
```

| Field | Meaning |
| :-- | :-- |
| `title` | The title, in the form `<Work> for uc-node, <Kind>` |
| `description` | One sentence on what the file holds |
| `version` | The document's own version, bumped by hand whenever the file changes, independent of the repository's `VERSION` |
| `status` | `provisional` while the work is under way, then `final` when the piece of work is merged |
| `date` | The date of the latest change, in ISO 8601 |
| `language` | `en-CA` |

The date lives in the front matter rather than in the file name, so a file keeps its name, and every link to it, when it is revised.

## What never goes in a session record

Session records are published with the repository, so they follow the same rule as the rest of it: no secrets, password hashes, real IP addresses, client names or real node definitions. Examples use `203.0.113.0/24`, `198.51.100.0/24` and `example.org`.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-23 | First version, adapted from the timestamped session naming convention to the names uc-node uses |
