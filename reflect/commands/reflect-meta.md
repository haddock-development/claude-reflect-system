---
name: reflect-meta
description: Show meta-learning statistics and pattern performance
---

# /reflect-meta Command

Shows statistics about how well the reflection patterns are performing based on your feedback history.

## What This Shows

1. **Overall Health** - How well your patterns are performing
2. **Decision Breakdown** - Accept/Modify/Skip distribution
3. **Pattern Health** - Which patterns work well, which need review
4. **Deprecated Patterns** - Patterns you frequently skip (may need removal)
5. **High-Performing Patterns** - Patterns you consistently accept

## Usage

```bash
/reflect-meta
```

## How Meta-Learning Works

Meta-learning is **completely passive by default**:

1. When you run `/reflect`, your decisions (Accept/Modify/Skip) are recorded
2. Over time, patterns that get frequently skipped are flagged
3. Patterns that get accepted consistently are marked as "excellent"
4. This data is stored locally in `~/.claude/reflect/meta/`

## Activating Score-Based Adjustments

To enable meta-learning to actually influence confidence scores:

```bash
/reflect --use-meta
```

This will:
- Boost confidence of high-performing patterns (+0.1)
- Lower confidence of poorly-performing patterns (-0.15 to -0.3)
- Flag deprecated patterns in the review UI

## Data Management

View raw scores:
```bash
python ~/.claude/skills/reflect/scripts/meta_learning.py scores
```

Reset all meta-learning data:
```bash
python ~/.claude/skills/reflect/scripts/meta_learning.py reset --confirm
```

## Privacy

All data stays 100% local. Nothing is sent anywhere.
Data is stored in human-readable JSON format.
