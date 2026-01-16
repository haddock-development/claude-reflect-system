#!/usr/bin/env python3
"""
Learning Ledger - SQLite-based tracking for cross-skill learning.

Tracks learnings across multiple skills and repositories.
When a learning appears in 2+ repos, it becomes eligible for promotion to global.
"""

import os
import sys
import json
import sqlite3
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Storage location
REFLECT_DIR = Path.home() / ".claude" / "reflect"
LEDGER_DB = REFLECT_DIR / "learnings.db"

# Promotion threshold (seen in N repos → eligible for global)
DEFAULT_PROMOTION_THRESHOLD = 2


class LearningLedger:
    """Manages the cross-skill learning database."""

    def __init__(self, db_path: Path = LEDGER_DB):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS learnings (
                id TEXT PRIMARY KEY,
                fingerprint TEXT UNIQUE NOT NULL,
                content TEXT NOT NULL,
                learning_type TEXT,
                skill_name TEXT,
                repo_ids TEXT DEFAULT '[]',
                count INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                status TEXT DEFAULT 'pending',
                first_seen TEXT,
                last_seen TEXT,
                promoted_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS promotions (
                id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                from_scope TEXT,
                to_scope TEXT,
                reason TEXT,
                promoted_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_fingerprint ON learnings(fingerprint);
            CREATE INDEX IF NOT EXISTS idx_status ON learnings(status);
            CREATE INDEX IF NOT EXISTS idx_skill ON learnings(skill_name);
        ''')
        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _generate_fingerprint(self, content: str) -> str:
        """Generate stable fingerprint for a learning."""
        # Normalize: lowercase, remove extra whitespace
        normalized = ' '.join(content.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _get_repo_id(self) -> str:
        """Get stable hash of current repository."""
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return hashlib.sha256(result.stdout.strip().encode()).hexdigest()[:12]
        except:
            pass
        # Fallback to cwd
        return hashlib.sha256(os.getcwd().encode()).hexdigest()[:12]

    def record_learning(
        self,
        content: str,
        learning_type: str = "correction",
        skill_name: str = "general",
        confidence: float = 0.5
    ) -> Dict:
        """Record a learning in the ledger."""
        fingerprint = self._generate_fingerprint(content)
        repo_id = self._get_repo_id()
        now = datetime.utcnow().isoformat()

        conn = self._connect()
        cursor = conn.execute(
            "SELECT * FROM learnings WHERE fingerprint = ?",
            (fingerprint,)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing learning
            repo_ids = json.loads(existing['repo_ids'] or '[]')
            if repo_id not in repo_ids:
                repo_ids.append(repo_id)

            conn.execute('''
                UPDATE learnings
                SET repo_ids = ?, count = count + 1, last_seen = ?, 
                    confidence = MAX(confidence, ?), updated_at = ?
                WHERE fingerprint = ?
            ''', (json.dumps(repo_ids), now, confidence, now, fingerprint))
            
            result = {
                "action": "updated",
                "fingerprint": fingerprint,
                "repo_count": len(repo_ids),
                "total_count": existing['count'] + 1
            }
        else:
            # Create new learning
            learning_id = hashlib.md5(f"{fingerprint}{now}".encode()).hexdigest()[:8]
            
            conn.execute('''
                INSERT INTO learnings 
                (id, fingerprint, content, learning_type, skill_name, repo_ids, 
                 confidence, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (learning_id, fingerprint, content, learning_type, skill_name,
                  json.dumps([repo_id]), confidence, now, now))
            
            result = {
                "action": "created",
                "fingerprint": fingerprint,
                "repo_count": 1,
                "total_count": 1
            }

        conn.commit()
        conn.close()
        return result

    def get_learning(self, fingerprint: str) -> Optional[Dict]:
        """Get a learning by fingerprint."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT * FROM learnings WHERE fingerprint = ?",
            (fingerprint,)
        )
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_promotion_candidates(self, threshold: int = DEFAULT_PROMOTION_THRESHOLD) -> List[Dict]:
        """Get learnings eligible for promotion to global."""
        conn = self._connect()
        cursor = conn.execute('''
            SELECT * FROM learnings
            WHERE status != 'promoted'
            AND json_array_length(repo_ids) >= ?
            ORDER BY count DESC, last_seen DESC
        ''', (threshold,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def check_promotion_eligibility(self, fingerprint: str, threshold: int = DEFAULT_PROMOTION_THRESHOLD) -> Dict:
        """Check if a learning is eligible for promotion."""
        learning = self.get_learning(fingerprint)
        
        if not learning:
            return {"eligible": False, "reason": "Learning not found"}

        repo_ids = json.loads(learning['repo_ids'] or '[]')
        repo_count = len(repo_ids)
        
        if learning['status'] == 'promoted':
            return {
                "eligible": False,
                "reason": "Already promoted",
                "fingerprint": fingerprint,
                "repo_count": repo_count
            }

        eligible = repo_count >= threshold
        
        return {
            "eligible": eligible,
            "fingerprint": fingerprint,
            "content": learning['content'],
            "repo_count": repo_count,
            "threshold": threshold,
            "reason": f"Seen in {repo_count}/{threshold} repos" if not eligible else "Ready for promotion",
            "skill_name": learning['skill_name']
        }

    def mark_promoted(self, fingerprint: str, reason: str = "Multi-repo threshold") -> bool:
        """Mark a learning as promoted to global."""
        conn = self._connect()
        now = datetime.utcnow().isoformat()

        # Update learning status
        conn.execute('''
            UPDATE learnings
            SET status = 'promoted', promoted_at = ?, updated_at = ?
            WHERE fingerprint = ?
        ''', (now, now, fingerprint))

        # Record promotion
        promo_id = hashlib.md5(f"{fingerprint}{now}".encode()).hexdigest()[:8]
        conn.execute('''
            INSERT INTO promotions (id, fingerprint, from_scope, to_scope, reason)
            VALUES (?, ?, 'skill', 'global', ?)
        ''', (promo_id, fingerprint, reason))

        affected = conn.total_changes
        conn.commit()
        conn.close()
        return affected > 0

    def get_stats(self) -> Dict:
        """Get ledger statistics."""
        conn = self._connect()
        stats = {}

        # Total learnings
        cursor = conn.execute("SELECT COUNT(*) FROM learnings")
        stats["total_learnings"] = cursor.fetchone()[0]

        # By status
        cursor = conn.execute('''
            SELECT status, COUNT(*) as count
            FROM learnings GROUP BY status
        ''')
        stats["by_status"] = {row['status'] or 'pending': row['count'] for row in cursor.fetchall()}

        # By skill
        cursor = conn.execute('''
            SELECT skill_name, COUNT(*) as count
            FROM learnings GROUP BY skill_name
            ORDER BY count DESC LIMIT 10
        ''')
        stats["by_skill"] = {row['skill_name']: row['count'] for row in cursor.fetchall()}

        # Multi-repo learnings
        cursor = conn.execute('''
            SELECT COUNT(*) FROM learnings
            WHERE json_array_length(repo_ids) >= 2
        ''')
        stats["multi_repo"] = cursor.fetchone()[0]

        # Promotion eligible
        cursor = conn.execute('''
            SELECT COUNT(*) FROM learnings
            WHERE status != 'promoted'
            AND json_array_length(repo_ids) >= 2
        ''')
        stats["promotion_eligible"] = cursor.fetchone()[0]

        # Total promotions
        cursor = conn.execute("SELECT COUNT(*) FROM promotions")
        stats["total_promotions"] = cursor.fetchone()[0]

        conn.close()
        return stats

    def get_skill_learnings(self, skill_name: str) -> List[Dict]:
        """Get all learnings for a specific skill."""
        conn = self._connect()
        cursor = conn.execute('''
            SELECT * FROM learnings
            WHERE skill_name = ?
            ORDER BY last_seen DESC
        ''', (skill_name,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Search learnings by content."""
        conn = self._connect()
        cursor = conn.execute('''
            SELECT * FROM learnings
            WHERE content LIKE ?
            ORDER BY last_seen DESC
            LIMIT ?
        ''', (f"%{query}%", limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Learning Ledger CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Record command
    record_parser = subparsers.add_parser("record", help="Record a learning")
    record_parser.add_argument("content", help="Learning content")
    record_parser.add_argument("--type", default="correction", help="Learning type")
    record_parser.add_argument("--skill", default="general", help="Skill name")

    # Stats command
    subparsers.add_parser("stats", help="Show statistics")

    # Candidates command
    cand_parser = subparsers.add_parser("candidates", help="Show promotion candidates")
    cand_parser.add_argument("--threshold", type=int, default=2, help="Repo threshold")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search learnings")
    search_parser.add_argument("query", help="Search query")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check promotion eligibility")
    check_parser.add_argument("fingerprint", help="Learning fingerprint")

    args = parser.parse_args()
    ledger = LearningLedger()

    if args.command == "record":
        result = ledger.record_learning(args.content, args.type, args.skill)
        print(json.dumps(result, indent=2))

    elif args.command == "stats":
        stats = ledger.get_stats()
        print(json.dumps(stats, indent=2))

    elif args.command == "candidates":
        candidates = ledger.get_promotion_candidates(args.threshold)
        print(f"Found {len(candidates)} promotion candidates:")
        for c in candidates:
            repos = json.loads(c['repo_ids'] or '[]')
            print(f"  [{c['fingerprint'][:8]}] ({len(repos)} repos) {c['content'][:60]}...")

    elif args.command == "search":
        results = ledger.search(args.query)
        print(json.dumps(results, indent=2))

    elif args.command == "check":
        result = ledger.check_promotion_eligibility(args.fingerprint)
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
