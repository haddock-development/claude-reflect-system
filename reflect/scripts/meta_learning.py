#!/usr/bin/env python3
"""
Meta-Learning Module for Reflect System.

Tracks pattern performance based on user feedback (Accept/Modify/Skip)
and provides confidence adjustments for future proposals.

Design Principles:
- PASSIVE by default: Only records data, doesn't change behavior
- OPT-IN activation: Score-based weighting requires explicit --use-meta flag
- NON-BLOCKING: Failures in meta-learning never break core reflect workflow
- TRANSPARENT: All data stored in human-readable JSON

Storage: ~/.claude/reflect/meta/
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict


# Constants - use same base directory as learning_ledger.py for consistency
REFLECT_DIR = Path.home() / '.claude' / 'reflect'
META_DIR = REFLECT_DIR / 'meta'
PATTERN_SCORES_FILE = META_DIR / 'pattern-scores.json'
FEEDBACK_LOG_FILE = META_DIR / 'feedback-log.jsonl'

# Thresholds for auto-actions (only when meta-learning is ACTIVE)
DEPRECATION_THRESHOLD = 0.20  # Patterns below this get flagged
PROMOTION_THRESHOLD = 0.80    # Patterns above this get boosted
MIN_SAMPLES = 5               # Minimum feedback count before adjustments


def ensure_meta_dir():
    """Create meta directory if it doesn't exist."""
    META_DIR.mkdir(parents=True, exist_ok=True)


def log_feedback(
    pattern_type: str,
    pattern_regex: str,
    skill_name: str,
    confidence_level: str,
    decision: str,  # 'accept', 'modify', 'skip', 'quit'
    signal_content: str,
    modification: Optional[str] = None
) -> bool:
    """
    Log user feedback on a proposed change.

    This is the ONLY function called from present_review.py.
    It's completely passive - just appends to a log file.

    Returns True if logged successfully, False otherwise (never raises).
    """
    try:
        ensure_meta_dir()

        entry = {
            'timestamp': datetime.now().isoformat(),
            'pattern_type': pattern_type,      # 'correction', 'approval', 'question'
            'pattern_regex': pattern_regex,    # The regex that matched (if any)
            'skill_name': skill_name,
            'confidence_level': confidence_level,  # 'HIGH', 'MEDIUM', 'LOW'
            'decision': decision,
            'signal_content': signal_content[:500],  # Truncate for storage
            'modification': modification
        }

        with open(FEEDBACK_LOG_FILE, 'a') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        return True

    except Exception as e:
        # Silent fail - meta-learning should never break core workflow
        return False


def compute_pattern_scores() -> Dict[str, Dict[str, Any]]:
    """
    Compute acceptance scores for each pattern from feedback log.

    Returns dict of pattern_key -> {
        'accept_count': int,
        'modify_count': int,
        'skip_count': int,
        'total': int,
        'acceptance_rate': float,  # (accept + modify) / total
        'pure_accept_rate': float, # accept / total
        'status': str  # 'healthy', 'needs_review', 'deprecated'
    }
    """
    scores = defaultdict(lambda: {
        'accept_count': 0,
        'modify_count': 0,
        'skip_count': 0,
        'total': 0,
        'skills': set(),
        'last_seen': None
    })

    if not FEEDBACK_LOG_FILE.exists():
        return {}

    try:
        with open(FEEDBACK_LOG_FILE) as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)

                    # Create pattern key from type + confidence
                    pattern_key = f"{entry.get('confidence_level', 'UNKNOWN')}:{entry.get('pattern_type', 'unknown')}"

                    decision = entry.get('decision', 'skip')

                    if decision == 'accept':
                        scores[pattern_key]['accept_count'] += 1
                    elif decision == 'modify':
                        scores[pattern_key]['modify_count'] += 1
                    elif decision in ('skip', 'quit'):
                        scores[pattern_key]['skip_count'] += 1

                    scores[pattern_key]['total'] += 1
                    scores[pattern_key]['skills'].add(entry.get('skill_name', 'unknown'))
                    scores[pattern_key]['last_seen'] = entry.get('timestamp')

                except json.JSONDecodeError:
                    continue

    except Exception:
        return {}

    # Compute rates and status
    result = {}
    for pattern_key, data in scores.items():
        total = data['total']
        if total == 0:
            continue

        accept_rate = (data['accept_count'] + data['modify_count']) / total
        pure_accept_rate = data['accept_count'] / total

        # Determine status
        if total < MIN_SAMPLES:
            status = 'insufficient_data'
        elif accept_rate < DEPRECATION_THRESHOLD:
            status = 'deprecated'
        elif accept_rate < 0.5:
            status = 'needs_review'
        elif accept_rate >= PROMOTION_THRESHOLD:
            status = 'excellent'
        else:
            status = 'healthy'

        result[pattern_key] = {
            'accept_count': data['accept_count'],
            'modify_count': data['modify_count'],
            'skip_count': data['skip_count'],
            'total': total,
            'acceptance_rate': round(accept_rate, 3),
            'pure_accept_rate': round(pure_accept_rate, 3),
            'status': status,
            'skills': list(data['skills']),
            'last_seen': data['last_seen']
        }

    return result


def save_pattern_scores():
    """Save computed scores to file for quick access."""
    try:
        ensure_meta_dir()
        scores = compute_pattern_scores()

        output = {
            'computed_at': datetime.now().isoformat(),
            'thresholds': {
                'deprecation': DEPRECATION_THRESHOLD,
                'promotion': PROMOTION_THRESHOLD,
                'min_samples': MIN_SAMPLES
            },
            'patterns': scores
        }

        with open(PATTERN_SCORES_FILE, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        return True
    except Exception:
        return False


def get_confidence_adjustment(
    confidence_level: str,
    pattern_type: str,
    use_meta: bool = False
) -> Tuple[float, Optional[str]]:
    """
    Get confidence adjustment based on historical performance.

    Args:
        confidence_level: 'HIGH', 'MEDIUM', 'LOW'
        pattern_type: 'correction', 'approval', 'question'
        use_meta: If False, returns (0.0, None) - no adjustment

    Returns:
        (adjustment: float, reason: str or None)
        adjustment is -0.3 to +0.2 range
    """
    if not use_meta:
        return (0.0, None)

    scores = compute_pattern_scores()
    pattern_key = f"{confidence_level}:{pattern_type}"

    if pattern_key not in scores:
        return (0.0, None)

    data = scores[pattern_key]

    if data['status'] == 'insufficient_data':
        return (0.0, None)

    if data['status'] == 'deprecated':
        return (-0.3, f"Pattern has {data['acceptance_rate']*100:.0f}% acceptance rate")

    if data['status'] == 'needs_review':
        return (-0.15, f"Pattern needs review ({data['acceptance_rate']*100:.0f}% acceptance)")

    if data['status'] == 'excellent':
        return (+0.1, f"Pattern highly trusted ({data['acceptance_rate']*100:.0f}% acceptance)")

    return (0.0, None)


def get_statistics() -> Dict[str, Any]:
    """
    Get comprehensive meta-learning statistics.

    Used by /reflect-meta command.
    """
    if not FEEDBACK_LOG_FILE.exists():
        return {
            'status': 'no_data',
            'message': 'No feedback recorded yet. Use /reflect and make decisions to start learning.',
            'total_feedback': 0
        }

    scores = compute_pattern_scores()

    # Count entries
    total_entries = 0
    decisions = defaultdict(int)
    skills_seen = set()

    try:
        with open(FEEDBACK_LOG_FILE) as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line)
                        total_entries += 1
                        decisions[entry.get('decision', 'unknown')] += 1
                        skills_seen.add(entry.get('skill_name', 'unknown'))
                    except json.JSONDecodeError:
                        continue
    except Exception:
        pass

    # Categorize patterns
    excellent_patterns = []
    healthy_patterns = []
    needs_review_patterns = []
    deprecated_patterns = []

    for pattern_key, data in scores.items():
        info = {'pattern': pattern_key, **data}
        if data['status'] == 'excellent':
            excellent_patterns.append(info)
        elif data['status'] == 'healthy':
            healthy_patterns.append(info)
        elif data['status'] == 'needs_review':
            needs_review_patterns.append(info)
        elif data['status'] == 'deprecated':
            deprecated_patterns.append(info)

    # Calculate overall health
    total_patterns = len(scores)
    if total_patterns == 0:
        overall_health = 'unknown'
    elif len(deprecated_patterns) > total_patterns * 0.3:
        overall_health = 'poor'
    elif len(excellent_patterns) > total_patterns * 0.5:
        overall_health = 'excellent'
    elif len(needs_review_patterns) > total_patterns * 0.3:
        overall_health = 'needs_attention'
    else:
        overall_health = 'good'

    return {
        'status': 'active',
        'total_feedback': total_entries,
        'decisions': dict(decisions),
        'skills_analyzed': list(skills_seen),
        'overall_health': overall_health,
        'pattern_summary': {
            'total': total_patterns,
            'excellent': len(excellent_patterns),
            'healthy': len(healthy_patterns),
            'needs_review': len(needs_review_patterns),
            'deprecated': len(deprecated_patterns)
        },
        'patterns': {
            'excellent': excellent_patterns,
            'healthy': healthy_patterns,
            'needs_review': needs_review_patterns,
            'deprecated': deprecated_patterns
        },
        'thresholds': {
            'deprecation': f"<{DEPRECATION_THRESHOLD*100:.0f}%",
            'promotion': f">{PROMOTION_THRESHOLD*100:.0f}%",
            'min_samples': MIN_SAMPLES
        }
    }


def format_statistics_report() -> str:
    """Format statistics as human-readable report for terminal."""
    stats = get_statistics()

    if stats['status'] == 'no_data':
        return f"""
======================================================================
  REFLECT META-LEARNING STATUS
======================================================================

  Status: No data collected yet

  {stats['message']}

  How it works:
  1. Run /reflect and review proposed changes
  2. Your decisions (Accept/Modify/Skip) are recorded
  3. Patterns that get frequently skipped are flagged
  4. Patterns that get accepted are reinforced

  This is completely passive - it only records, doesn't change behavior.
  Use --use-meta flag with /reflect to enable score-based adjustments.
"""

    lines = ["""
======================================================================
  REFLECT META-LEARNING STATUS
======================================================================
"""]

    # Overview
    lines.append(f"  Overall Health: {stats['overall_health'].upper()}")
    lines.append(f"  Total Feedback: {stats['total_feedback']} decisions recorded")
    lines.append(f"  Skills Analyzed: {len(stats['skills_analyzed'])}")
    lines.append("")

    # Decision breakdown
    decisions = stats['decisions']
    total = sum(decisions.values())
    if total > 0:
        lines.append("  Decision Breakdown:")
        for dec, count in sorted(decisions.items(), key=lambda x: -x[1]):
            pct = count / total * 100
            bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
            lines.append(f"    {dec:8} {bar} {count:3} ({pct:.0f}%)")
        lines.append("")

    # Pattern summary
    summary = stats['pattern_summary']
    lines.append("  Pattern Health:")
    if summary['excellent']:
        lines.append(f"    [OK] Excellent: {summary['excellent']}")
    if summary['healthy']:
        lines.append(f"    [OK] Healthy:   {summary['healthy']}")
    if summary['needs_review']:
        lines.append(f"    [!]  Review:    {summary['needs_review']}")
    if summary['deprecated']:
        lines.append(f"    [X]  Deprecated:{summary['deprecated']}")
    lines.append("")

    # Show deprecated patterns (if any)
    deprecated = stats['patterns']['deprecated']
    if deprecated:
        lines.append("  [!] Patterns Needing Attention:")
        for p in deprecated[:5]:
            lines.append(f"    - {p['pattern']}: {p['acceptance_rate']*100:.0f}% acceptance ({p['total']} samples)")
        lines.append("")

    # Show excellent patterns
    excellent = stats['patterns']['excellent']
    if excellent:
        lines.append("  [OK] High-Performing Patterns:")
        for p in excellent[:5]:
            lines.append(f"    - {p['pattern']}: {p['acceptance_rate']*100:.0f}% acceptance ({p['total']} samples)")
        lines.append("")

    lines.append(f"  Thresholds: deprecation {stats['thresholds']['deprecation']}, ")
    lines.append(f"              promotion {stats['thresholds']['promotion']}, ")
    lines.append(f"              min samples: {stats['thresholds']['min_samples']}")
    lines.append("")
    lines.append("  Note: Meta-learning is PASSIVE by default.")
    lines.append("  Use '/reflect --use-meta' to enable score-based adjustments.")

    return "\n".join(lines)


def reset_data(confirm: bool = False) -> bool:
    """Reset all meta-learning data. Requires confirm=True."""
    if not confirm:
        return False

    try:
        if FEEDBACK_LOG_FILE.exists():
            # Backup before delete
            backup = FEEDBACK_LOG_FILE.with_suffix('.jsonl.backup')
            FEEDBACK_LOG_FILE.rename(backup)

        if PATTERN_SCORES_FILE.exists():
            PATTERN_SCORES_FILE.unlink()

        return True
    except Exception:
        return False


# CLI interface
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == 'stats':
            print(format_statistics_report())

        elif cmd == 'scores':
            scores = compute_pattern_scores()
            print(json.dumps(scores, indent=2, ensure_ascii=False))

        elif cmd == 'reset':
            if '--confirm' in sys.argv:
                if reset_data(confirm=True):
                    print("OK: Meta-learning data reset")
                else:
                    print("ERROR: Failed to reset data")
            else:
                print("Use --confirm to actually reset data")

        else:
            print(f"Unknown command: {cmd}")
            print("Usage: meta_learning.py [stats|scores|reset]")

    else:
        print(format_statistics_report())
