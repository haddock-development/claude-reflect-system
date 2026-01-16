#!/usr/bin/env python3
"""
Promote Learning - Move skill-level learnings to global CLAUDE.md

When a learning appears in multiple repositories, it becomes a candidate
for promotion to the global CLAUDE.md file.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

try:
    from learning_ledger import LearningLedger
    from scope_analyzer import ScopeAnalyzer
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

# Paths
GLOBAL_CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"
BACKUP_DIR = Path.home() / ".claude" / "backups"


class LearningPromoter:
    """Handles promotion of learnings to global scope."""

    def __init__(self):
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError("learning_ledger.py and scope_analyzer.py required")
        
        self.ledger = LearningLedger()
        self.analyzer = ScopeAnalyzer()

    def get_candidates(self, threshold: int = 2) -> List[Dict]:
        """Get learnings eligible for promotion."""
        return self.analyzer.get_promotion_suggestions()

    def preview_promotion(self, fingerprint: str) -> Dict:
        """Preview what would be added to CLAUDE.md."""
        learning = self.ledger.get_learning(fingerprint)
        if not learning:
            return {"error": "Learning not found"}

        eligibility = self.ledger.check_promotion_eligibility(fingerprint)
        if not eligibility["eligible"]:
            return {
                "error": "Not eligible for promotion",
                "reason": eligibility["reason"]
            }

        # Generate the entry for CLAUDE.md
        entry = self._format_entry(learning)

        return {
            "fingerprint": fingerprint,
            "content": learning['content'],
            "skill_name": learning.get('skill_name', 'general'),
            "repo_count": eligibility['repo_count'],
            "formatted_entry": entry,
            "target_file": str(GLOBAL_CLAUDE_MD)
        }

    def _format_entry(self, learning: Dict) -> str:
        """Format learning as CLAUDE.md entry."""
        content = learning['content']
        skill = learning.get('skill_name', 'general')
        repos = json.loads(learning.get('repo_ids', '[]'))
        
        entry = f"\n## From {skill} (promoted)\n\n"
        entry += f"{content}\n\n"
        entry += f"<!-- Promoted: {datetime.utcnow().isoformat()} | "
        entry += f"Seen in {len(repos)} repos | "
        entry += f"Fingerprint: {learning['fingerprint'][:8]} -->\n"
        
        return entry

    def _backup_file(self, filepath: Path) -> Optional[Path]:
        """Create timestamped backup of file."""
        if not filepath.exists():
            return None

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"CLAUDE.md.{timestamp}.bak"
        
        shutil.copy2(filepath, backup_path)
        return backup_path

    def promote(self, fingerprint: str, dry_run: bool = False) -> Dict:
        """Promote a learning to global CLAUDE.md."""
        learning = self.ledger.get_learning(fingerprint)
        if not learning:
            return {"success": False, "error": "Learning not found"}

        eligibility = self.ledger.check_promotion_eligibility(fingerprint)
        if not eligibility["eligible"]:
            return {
                "success": False,
                "error": "Not eligible",
                "reason": eligibility["reason"]
            }

        entry = self._format_entry(learning)

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "would_add": entry,
                "to_file": str(GLOBAL_CLAUDE_MD)
            }

        # Backup existing file
        backup_path = self._backup_file(GLOBAL_CLAUDE_MD)

        # Append to CLAUDE.md
        GLOBAL_CLAUDE_MD.parent.mkdir(parents=True, exist_ok=True)
        
        with open(GLOBAL_CLAUDE_MD, 'a') as f:
            f.write(entry)

        # Mark as promoted in ledger
        self.ledger.mark_promoted(
            fingerprint, 
            f"Seen in {eligibility['repo_count']} repos"
        )

        return {
            "success": True,
            "fingerprint": fingerprint,
            "content": learning['content'][:100],
            "added_to": str(GLOBAL_CLAUDE_MD),
            "backup": str(backup_path) if backup_path else None
        }

    def promote_all(self, dry_run: bool = False) -> Dict:
        """Promote all eligible learnings."""
        candidates = self.get_candidates()
        results = {
            "total": len(candidates),
            "promoted": [],
            "failed": [],
            "dry_run": dry_run
        }

        for candidate in candidates:
            result = self.promote(candidate['fingerprint'], dry_run=dry_run)
            if result.get('success'):
                results["promoted"].append({
                    "fingerprint": candidate['fingerprint'],
                    "content": candidate['content'][:60]
                })
            else:
                results["failed"].append({
                    "fingerprint": candidate['fingerprint'],
                    "error": result.get('error')
                })

        return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Promote learnings to global")
    subparsers = parser.add_subparsers(dest="command")

    # List candidates
    subparsers.add_parser("list", help="List promotion candidates")

    # Preview
    preview_parser = subparsers.add_parser("preview", help="Preview promotion")
    preview_parser.add_argument("fingerprint", help="Learning fingerprint")

    # Promote single
    promote_parser = subparsers.add_parser("promote", help="Promote a learning")
    promote_parser.add_argument("fingerprint", help="Learning fingerprint")
    promote_parser.add_argument("--dry-run", action="store_true", help="Preview only")

    # Promote all
    all_parser = subparsers.add_parser("all", help="Promote all eligible")
    all_parser.add_argument("--dry-run", action="store_true", help="Preview only")

    # Stats
    subparsers.add_parser("stats", help="Show ledger statistics")

    args = parser.parse_args()

    if not DEPENDENCIES_AVAILABLE:
        print("Error: learning_ledger.py and scope_analyzer.py required")
        print("Make sure they are in the same directory.")
        return 1

    promoter = LearningPromoter()

    if args.command == "list":
        candidates = promoter.get_candidates()
        if candidates:
            print(f"\n{len(candidates)} learnings ready for promotion:\n")
            for c in candidates:
                print(f"  [{c['fingerprint'][:8]}] ({c['repo_count']} repos)")
                print(f"    {c['content'][:70]}...")
                print(f"    From: {c['skill_name']}")
                print()
        else:
            print("No learnings ready for promotion.")
            print("Learnings become eligible when seen in 2+ repositories.")

    elif args.command == "preview":
        result = promoter.preview_promotion(args.fingerprint)
        if "error" in result:
            print(f"Error: {result['error']}")
            if "reason" in result:
                print(f"Reason: {result['reason']}")
        else:
            print(f"\nWould add to {result['target_file']}:\n")
            print("─" * 60)
            print(result['formatted_entry'])
            print("─" * 60)

    elif args.command == "promote":
        result = promoter.promote(args.fingerprint, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))

    elif args.command == "all":
        result = promoter.promote_all(dry_run=args.dry_run)
        print(json.dumps(result, indent=2))

    elif args.command == "stats":
        ledger = LearningLedger()
        stats = ledger.get_stats()
        print(json.dumps(stats, indent=2))

    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
