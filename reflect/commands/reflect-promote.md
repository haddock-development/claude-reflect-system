---
description: Promote learnings from skills to global CLAUDE.md
allowed-tools: Bash, Read, Write
---

# /reflect-promote

Promote skill-level learnings to global scope when they appear in multiple repositories.

## What This Does

When you correct Claude in multiple projects, those learnings become candidates for promotion to your global `~/.claude/CLAUDE.md` file. This means Claude will remember them everywhere, not just in specific skills.

## Usage

```bash
# List learnings ready for promotion
python3 ~/.claude/skills/reflect/scripts/promote_learning.py list

# Preview what would be added
python3 ~/.claude/skills/reflect/scripts/promote_learning.py preview <fingerprint>

# Promote a specific learning
python3 ~/.claude/skills/reflect/scripts/promote_learning.py promote <fingerprint>

# Promote all eligible learnings
python3 ~/.claude/skills/reflect/scripts/promote_learning.py all

# Dry-run (preview without changes)
python3 ~/.claude/skills/reflect/scripts/promote_learning.py all --dry-run
```

## How It Works

1. **Track**: Every `/reflect` session records learnings in SQLite ledger
2. **Detect**: When same learning appears in 2+ repos → eligible for promotion
3. **Promote**: Append to `~/.claude/CLAUDE.md` with metadata
4. **Backup**: Original file backed up before changes

## Example

```
$ python3 promote_learning.py list

2 learnings ready for promotion:

  [a1b2c3d4] (3 repos)
    Use uv instead of pip for Python projects
    From: python-project-creator

  [e5f6g7h8] (2 repos)
    Always run tests before committing
    From: general
```

## Thresholds

- Default: 2 repos required for promotion
- Can be configured in scope_analyzer.py

## Files

- Ledger DB: `~/.claude/reflect/learnings.db`
- Global rules: `~/.claude/CLAUDE.md`
- Backups: `~/.claude/backups/`
