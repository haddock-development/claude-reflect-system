#!/usr/bin/env python3
"""
Scope Analyzer - Determines if a learning should be project or global.

Uses heuristics and cross-repo tracking to decide optimal placement:
- Project scope: Specific to current project/repo
- Global scope: Universal patterns useful everywhere
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    from learning_ledger import LearningLedger
    LEDGER_AVAILABLE = True
except ImportError:
    LEDGER_AVAILABLE = False

# Indicators that suggest PROJECT scope (specific to this repo)
PROJECT_INDICATORS = [
    # Path patterns
    (r'src/components/', 2),
    (r'apps/', 2),
    (r'packages/', 2),
    (r'\.env\.', 2),
    (r'docker-compose', 2),
    
    # Project-specific terms
    (r'\b(client|customer|vendor)\s+name', 2),
    (r'\b(internal|proprietary)\b', 2),
    (r'\bapi\.[a-z]+\.com\b', 3),  # Specific API URLs
    (r'\blocalhost:\d+', 2),
    
    # Monorepo patterns
    (r'pnpm\s+-C\s+packages/', 3),
    (r'nx\s+', 2),
    (r'turbo\b', 2),
]

# Indicators that suggest GLOBAL scope (universal patterns)
GLOBAL_INDICATORS = [
    # Universal engineering behaviors
    (r'\brun\s+tests?\b', 3),
    (r'\bsmall\s+(pr|commit)', 2),
    (r'\bcommit\s+message', 2),
    (r'\bcode\s+review', 2),
    (r'\bverify\s+before', 2),
    (r'\bbackup\s+first', 2),
    (r'\balways\s+check', 2),
    (r'\bnever\s+commit\s+secrets', 3),
    
    # Common tools (language-agnostic advice)
    (r'\bgit\b', 2),
    (r'\bdocker\b', 2),
    (r'\buse\s+(uv|pip|npm|yarn|pnpm)\b', 2),
    (r'\buse\s+(pytest|jest|vitest)\b', 2),
    (r'\buse\s+(ruff|eslint|prettier)\b', 2),
    
    # German patterns (your language!)
    (r'\bimmer\s+', 2),
    (r'\bniemals?\s+', 2),
    (r'\bverwende\s+', 2),
    (r'\bbenutze\s+', 2),
    (r'\bstatt\b', 2),
]


class ScopeAnalyzer:
    """Analyzes and decides learning scope."""

    def __init__(self, promotion_threshold: int = 2):
        self.promotion_threshold = promotion_threshold
        self.ledger = LearningLedger() if LEDGER_AVAILABLE else None

    def calculate_scores(self, content: str) -> Tuple[float, float]:
        """Calculate project and global scores for content."""
        text_lower = content.lower()
        
        project_score = 0.0
        global_score = 0.0

        for pattern, weight in PROJECT_INDICATORS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                project_score += weight

        for pattern, weight in GLOBAL_INDICATORS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                global_score += weight

        return project_score, global_score

    def check_cross_repo(self, content: str) -> Dict:
        """Check if this learning exists in multiple repos."""
        if not self.ledger:
            return {"repo_count": 0, "repos": [], "available": False}

        # Generate fingerprint same way as ledger
        import hashlib
        normalized = ' '.join(content.lower().split())
        fingerprint = hashlib.sha256(normalized.encode()).hexdigest()[:16]

        learning = self.ledger.get_learning(fingerprint)
        if not learning:
            return {"repo_count": 0, "repos": [], "fingerprint": fingerprint}

        repo_ids = json.loads(learning.get('repo_ids', '[]'))
        return {
            "repo_count": len(repo_ids),
            "repos": repo_ids,
            "fingerprint": fingerprint,
            "status": learning.get('status'),
            "count": learning.get('count', 1)
        }

    def analyze(self, content: str, skill_name: str = "general") -> Dict:
        """Full scope analysis for a learning."""
        project_score, global_score = self.calculate_scores(content)
        cross_repo = self.check_cross_repo(content)

        # Decision logic
        recommended_scope = "skill"  # Default: stay in skill file
        reasons = []

        # Rule 1: Cross-repo threshold → promote to global
        if cross_repo.get("repo_count", 0) >= self.promotion_threshold:
            if cross_repo.get("status") != "promoted":
                recommended_scope = "global"
                reasons.append(f"Seen in {cross_repo['repo_count']} repos → promote to global")
            else:
                recommended_scope = "global"
                reasons.append("Already promoted to global")

        # Rule 2: Strong global indicators
        elif global_score > project_score * 1.5 and global_score >= 4:
            recommended_scope = "global"
            reasons.append(f"Strong global indicators (score: {global_score:.1f})")

        # Rule 3: Strong project indicators
        elif project_score > global_score * 1.5 and project_score >= 4:
            recommended_scope = "skill"
            reasons.append(f"Strong project indicators (score: {project_score:.1f})")

        # Rule 4: Default to skill-level
        else:
            recommended_scope = "skill"
            reasons.append("Default: keep in skill scope")

        # Check promotion eligibility
        eligible_for_promotion = (
            recommended_scope == "skill" and
            cross_repo.get("repo_count", 0) >= 1 and
            global_score >= project_score * 0.5
        )

        return {
            "content": content[:100] + "..." if len(content) > 100 else content,
            "skill_name": skill_name,
            "recommended_scope": recommended_scope,
            "reasons": reasons,
            "scores": {
                "project": project_score,
                "global": global_score
            },
            "cross_repo": cross_repo,
            "eligible_for_promotion": eligible_for_promotion,
            "promotion_threshold": self.promotion_threshold
        }

    def should_promote(self, content: str) -> bool:
        """Quick check if learning should be promoted."""
        analysis = self.analyze(content)
        return analysis["recommended_scope"] == "global"

    def get_promotion_suggestions(self) -> List[Dict]:
        """Get all learnings that should be promoted."""
        if not self.ledger:
            return []

        candidates = self.ledger.get_promotion_candidates(self.promotion_threshold)
        suggestions = []

        for candidate in candidates:
            analysis = self.analyze(candidate['content'], candidate.get('skill_name', 'general'))
            if analysis["recommended_scope"] == "global":
                suggestions.append({
                    "fingerprint": candidate['fingerprint'],
                    "content": candidate['content'],
                    "skill_name": candidate.get('skill_name'),
                    "repo_count": len(json.loads(candidate.get('repo_ids', '[]'))),
                    "total_count": candidate.get('count', 1),
                    "analysis": analysis
                })

        return suggestions


def analyze_learning(content: str, skill_name: str = "general") -> Dict:
    """Convenience function to analyze a single learning."""
    analyzer = ScopeAnalyzer()
    return analyzer.analyze(content, skill_name)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze learning scope")
    subparsers = parser.add_subparsers(dest="command")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a learning")
    analyze_parser.add_argument("content", help="Learning content")
    analyze_parser.add_argument("--skill", default="general", help="Skill name")

    # Suggestions command
    subparsers.add_parser("suggestions", help="Get promotion suggestions")

    args = parser.parse_args()
    analyzer = ScopeAnalyzer()

    if args.command == "analyze":
        result = analyzer.analyze(args.content, args.skill)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "suggestions":
        suggestions = analyzer.get_promotion_suggestions()
        if suggestions:
            print(f"Found {len(suggestions)} promotion suggestions:\n")
            for s in suggestions:
                print(f"[{s['fingerprint'][:8]}] ({s['repo_count']} repos)")
                print(f"  Skill: {s['skill_name']}")
                print(f"  Content: {s['content'][:60]}...")
                print(f"  → {s['analysis']['reasons'][0]}")
                print()
        else:
            print("No promotion suggestions found.")

    else:
        # Default: show help
        parser.print_help()


if __name__ == "__main__":
    main()
