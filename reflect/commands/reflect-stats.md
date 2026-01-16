---
description: Show cross-skill learning statistics
allowed-tools: Bash
---

# /reflect-stats

Show statistics about your learning ledger.

## Usage

```bash
python3 ~/.claude/skills/reflect/scripts/learning_ledger.py stats
```

## Example Output

```json
{
  "total_learnings": 47,
  "by_status": {
    "pending": 42,
    "promoted": 5
  },
  "by_skill": {
    "python-project-creator": 15,
    "general": 12,
    "reflect": 8
  },
  "multi_repo": 8,
  "promotion_eligible": 3,
  "total_promotions": 5
}
```

## What The Numbers Mean

- **total_learnings**: All tracked learnings across all skills
- **multi_repo**: Learnings seen in 2+ repositories
- **promotion_eligible**: Ready to promote to global
- **total_promotions**: Already promoted to `~/.claude/CLAUDE.md`
