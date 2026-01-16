#!/usr/bin/env python3
"""
Extracts learning signals from conversation transcripts.
Identifies corrections, approvals, and patterns with confidence levels.

Supports two detection modes:
- Regex (default): Fast pattern matching, English-focused
- Semantic (--semantic): AI-powered, multi-language, higher accuracy
"""

import json
import re
import os
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import semantic detector (optional)
try:
    from semantic_detector import semantic_analyze, analyze_messages
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

# Correction patterns (HIGH confidence)
CORRECTION_PATTERNS = [
    r"(?i)no,?\s+don't\s+(?:do|use)\s+(.+?)[,.]?\s+(?:do|use)\s+(.+)",
    r"(?i)actually,?\s+(.+?)\s+(?:is|should be)\s+(.+)",
    r"(?i)instead\s+of\s+(.+?),?\s+(?:you\s+should|use|do)\s+(.+)",
    r"(?i)never\s+(?:do|use)\s+(.+)",
    r"(?i)always\s+(?:do|use|check for)\s+(.+)",
    # German patterns
    r"(?i)nein,?\s+(?:benutze|verwende)\s+(.+?)\s+(?:statt|anstatt)\s+(.+)",
    r"(?i)immer\s+(.+)",
    r"(?i)niemals?\s+(.+)",
]

# Approval patterns (MEDIUM confidence)
APPROVAL_PATTERNS = [
    r"(?i)(?:yes,?\s+)?(?:that's\s+)?(?:perfect|great|exactly|correct)",
    r"(?i)works?\s+(?:perfectly|great|well)",
    r"(?i)(?:good|nice)\s+(?:job|work)",
    # German patterns
    r"(?i)(?:ja,?\s+)?(?:das\s+ist\s+)?(?:perfekt|super|genau|richtig)",
]

# Question patterns (LOW confidence)
QUESTION_PATTERNS = [
    r"(?i)have\s+you\s+considered\s+(.+)",
    r"(?i)why\s+not\s+(?:try|use)\s+(.+)",
    r"(?i)what\s+about\s+(.+)",
    # German patterns
    r"(?i)hast\s+du\s+(?:schon\s+)?(?:an\s+)?(.+)\s+gedacht",
    r"(?i)was\s+ist\s+mit\s+(.+)",
]


def extract_signals(
    transcript_path: Optional[str] = None,
    use_semantic: bool = False,
    semantic_model: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parse transcript and extract learning signals.
    
    Args:
        transcript_path: Path to transcript file (auto-detected if None)
        use_semantic: Use AI-powered semantic analysis
        semantic_model: Model for semantic analysis (default: haiku)
    
    Returns:
        Dict of signals grouped by skill name.
    """
    if not transcript_path:
        transcript_path = find_latest_transcript()

    if not transcript_path or not Path(transcript_path).exists():
        print(f"Warning: Transcript not found: {transcript_path}")
        return {}

    signals = []
    messages = load_transcript(transcript_path)
    skills_used = find_skill_invocations(messages)

    # Extract user messages for analysis
    user_messages = []
    for i, msg in enumerate(messages):
        if msg.get('role') == 'user':
            user_messages.append({
                'index': i,
                'content': str(msg.get('content', '')),
                'context': messages[max(0, i-5):i+1]
            })

    # Phase 1: Regex-based detection (fast)
    for user_msg in user_messages:
        content = user_msg['content']
        context = user_msg['context']
        i = user_msg['index']

        # Check for corrections (HIGH)
        for pattern in CORRECTION_PATTERNS:
            if match := re.search(pattern, content):
                signals.append({
                    'confidence': 'HIGH',
                    'confidence_score': 0.85,
                    'type': 'correction',
                    'content': content,
                    'context': context,
                    'skills': skills_used if skills_used else ['general'],
                    'match': match.groups() if match.groups() else (content,),
                    'description': extract_correction_description(content, match),
                    'detection_method': 'regex'
                })

        # Check for approvals (MEDIUM)
        prev_msg = messages[i-1] if i > 0 else None
        if prev_msg and prev_msg.get('role') == 'assistant':
            for pattern in APPROVAL_PATTERNS:
                if re.search(pattern, content):
                    signals.append({
                        'confidence': 'MEDIUM',
                        'confidence_score': 0.65,
                        'type': 'approval',
                        'content': content,
                        'context': context,
                        'skills': skills_used if skills_used else ['general'],
                        'previous_approach': extract_approach(prev_msg),
                        'description': 'Approved approach',
                        'detection_method': 'regex'
                    })

        # Check for questions (LOW)
        for pattern in QUESTION_PATTERNS:
            if match := re.search(pattern, content):
                signals.append({
                    'confidence': 'LOW',
                    'confidence_score': 0.45,
                    'type': 'question',
                    'content': content,
                    'context': context,
                    'skills': skills_used if skills_used else ['general'],
                    'suggestion': match.group(1) if match.groups() else content,
                    'description': f'Consider: {match.group(1) if match.groups() else content}',
                    'detection_method': 'regex'
                })

    # Phase 2: Semantic analysis (if enabled)
    if use_semantic:
        if not SEMANTIC_AVAILABLE:
            print("Warning: Semantic detector not available. Using regex only.")
        else:
            print("Running semantic analysis...")
            signals = enhance_with_semantic(
                signals, 
                user_messages, 
                skills_used,
                model=semantic_model
            )

    return group_by_skill(signals)


def enhance_with_semantic(
    regex_signals: List[Dict[str, Any]],
    user_messages: List[Dict[str, Any]],
    skills_used: List[str],
    model: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Enhance regex signals with semantic analysis.
    Also finds signals that regex missed.
    """
    enhanced_signals = []
    regex_contents = {s['content'] for s in regex_signals}

    # Analyze all user messages
    for user_msg in user_messages:
        content = user_msg['content']
        context = user_msg['context']

        # Run semantic analysis
        result = semantic_analyze(content, model=model)
        
        if result is None:
            # Semantic failed, keep regex result if exists
            for sig in regex_signals:
                if sig['content'] == content:
                    enhanced_signals.append(sig)
            continue

        if not result.get('is_learning'):
            # Semantic says not a learning - skip even if regex matched
            continue

        # Check if regex already found this
        existing_signal = None
        for sig in regex_signals:
            if sig['content'] == content:
                existing_signal = sig
                break

        if existing_signal:
            # Merge: take higher confidence
            merged = {**existing_signal}
            semantic_conf = result.get('confidence', 0)
            regex_conf = existing_signal.get('confidence_score', 0.5)
            
            merged['confidence_score'] = max(semantic_conf, regex_conf)
            merged['semantic_confidence'] = semantic_conf
            merged['semantic_type'] = result.get('type')
            merged['semantic_reasoning'] = result.get('reasoning')
            merged['detection_method'] = 'regex+semantic'
            
            if result.get('extracted_learning'):
                merged['extracted_learning'] = result['extracted_learning']
            
            # Update confidence label
            if merged['confidence_score'] >= 0.8:
                merged['confidence'] = 'HIGH'
            elif merged['confidence_score'] >= 0.6:
                merged['confidence'] = 'MEDIUM'
            else:
                merged['confidence'] = 'LOW'
            
            enhanced_signals.append(merged)
        else:
            # New signal found by semantic only
            conf = result.get('confidence', 0.5)
            enhanced_signals.append({
                'confidence': 'HIGH' if conf >= 0.8 else 'MEDIUM' if conf >= 0.6 else 'LOW',
                'confidence_score': conf,
                'type': result.get('type', 'correction'),
                'content': content,
                'context': context,
                'skills': skills_used if skills_used else ['general'],
                'description': result.get('extracted_learning', 'Learning detected'),
                'extracted_learning': result.get('extracted_learning'),
                'semantic_reasoning': result.get('reasoning'),
                'detection_method': 'semantic'
            })

    return enhanced_signals


def find_latest_transcript() -> Optional[str]:
    """Find the most recent transcript file"""
    try:
        if os.getenv('TRANSCRIPT_PATH'):
            return os.getenv('TRANSCRIPT_PATH')

        session_dir = Path(os.getenv('SESSION_DIR', Path.home() / '.claude' / 'session-env')).expanduser()
        if session_dir.exists():
            transcripts = list(session_dir.glob('*/transcript.jsonl'))
            if transcripts:
                return str(max(transcripts, key=lambda p: p.stat().st_mtime))
    except Exception as e:
        print(f"Error finding transcript: {e}")

    return None


def load_transcript(path: str) -> List[Dict[str, Any]]:
    """Load JSONL transcript into message list"""
    messages = []
    try:
        with open(path) as f:
            for line in f:
                if line.strip():
                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        print(f"Error loading transcript: {e}")

    return messages


def find_skill_invocations(messages: List[Dict[str, Any]]) -> List[str]:
    """Find which skills were invoked in conversation"""
    skills = set()
    for msg in messages:
        if 'tool_uses' in msg:
            for tool in msg.get('tool_uses', []):
                if tool.get('name') == 'Skill':
                    params = tool.get('parameters', {})
                    if 'skill' in params:
                        skills.add(params['skill'])

        content = str(msg.get('content', ''))
        if matches := re.findall(r'/([a-z][a-z0-9-]*)', content):
            skills.update(matches)

    return list(skills)


def extract_approach(message: Dict[str, Any]) -> str:
    """Extract the approach Claude took from assistant message"""
    content = str(message.get('content', ''))
    return content[:500]


def extract_correction_description(content: str, match) -> str:
    """Extract a human-readable description from correction pattern"""
    if match.groups():
        if len(match.groups()) == 2:
            return f"Use '{match.group(2)}' instead of '{match.group(1)}'"
        elif len(match.groups()) == 1:
            return f"Correction: {match.group(1)}"
    return "User provided correction"


def group_by_skill(signals: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group signals by the skills they relate to"""
    grouped = {}
    for signal in signals:
        for skill in signal.get('skills', ['general']):
            if skill not in grouped:
                grouped[skill] = []
            grouped[skill].append(signal)
    return grouped


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Extract learning signals from Claude Code transcripts'
    )
    parser.add_argument(
        'transcript',
        nargs='?',
        help='Path to transcript file (auto-detected if not provided)'
    )
    parser.add_argument(
        '--semantic',
        action='store_true',
        help='Use AI-powered semantic analysis (slower but more accurate, multi-language)'
    )
    parser.add_argument(
        '--model',
        default=None,
        help='Model for semantic analysis (default: haiku)'
    )
    
    args = parser.parse_args()

    if args.semantic and not SEMANTIC_AVAILABLE:
        print("Error: semantic_detector.py not found in same directory")
        print("Make sure semantic_detector.py is in reflect/scripts/")
        exit(1)

    signals = extract_signals(
        args.transcript,
        use_semantic=args.semantic,
        semantic_model=args.model
    )
    
    print(json.dumps(signals, indent=2, ensure_ascii=False))
