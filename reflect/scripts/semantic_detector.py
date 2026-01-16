#!/usr/bin/env python3
"""Semantic learning detection using Claude Code CLI.

Uses `claude -p` (print mode) to semantically analyze user messages
and determine if they contain reusable learnings.

Advantages over regex:
- Multi-language support (works in German, Spanish, etc.)
- Better accuracy (understands intent, not just keywords)
- Extracts clean, actionable learning statements
"""
import json
import subprocess
import sys
from typing import Optional, Dict, Any, List

# Default timeout for Claude CLI calls (seconds)
DEFAULT_TIMEOUT = 30

# Semantic analysis prompt template
ANALYSIS_PROMPT = '''Analyze this user message from a coding session. Determine if it contains
a reusable learning, correction, or preference that should be remembered for future sessions.

Message: "{text}"

Respond ONLY with valid JSON (no markdown, no explanation):
{{
  "is_learning": true or false,
  "type": "correction" or "positive" or "explicit" or null,
  "confidence": 0.0 to 1.0,
  "reasoning": "brief 1-sentence explanation",
  "extracted_learning": "concise actionable statement, or null if not a learning"
}}

Guidelines:
- correction: User telling AI to do something differently ("use X not Y", "don't use Z")
- positive: User affirming good behavior ("perfect!", "exactly right", "great approach")
- explicit: User explicitly asking to remember ("remember: ...", "always do X")
- is_learning=true only if it's reusable across sessions (not one-time task instructions)
- confidence: How certain this is a genuine, reusable learning (0.6+ to be useful)
- extracted_learning: Should be actionable and concise (e.g., "Use uv instead of pip")
- Works for ANY language - understand intent, not just English keywords
- Filter out: questions, greetings, one-time commands, context-specific requests'''


def semantic_analyze(
    text: str,
    timeout: int = DEFAULT_TIMEOUT,
    model: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Analyze text using Claude to determine if it's a learning.

    Args:
        text: The user message to analyze
        timeout: Timeout in seconds for the Claude CLI call
        model: Optional model override (e.g., "haiku" for faster/cheaper)

    Returns:
        Dictionary with analysis results, or None on failure:
        {
            "is_learning": bool,
            "type": "correction" | "positive" | "explicit" | None,
            "confidence": float (0.0-1.0),
            "reasoning": str,
            "extracted_learning": str | None
        }
    """
    if not text or not text.strip():
        return None

    # Build the prompt
    prompt = ANALYSIS_PROMPT.format(text=text.replace('"', '\\"'))

    # Build command - use haiku by default for speed/cost
    cmd = ["claude", "-p", "--output-format", "json"]
    if model:
        cmd.extend(["--model", model])
    else:
        cmd.extend(["--model", "haiku"])  # Fast and cheap

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        if result.returncode != 0:
            return None

        output = result.stdout.strip()
        if not output:
            return None

        # Parse the JSON output
        try:
            response = json.loads(output)
            if isinstance(response, dict) and "result" in response:
                content = response["result"]
            else:
                content = response
        except json.JSONDecodeError:
            content = _extract_json_from_text(output)
            if content is None:
                return None

        return _validate_response(content)

    except subprocess.TimeoutExpired:
        print(f"Warning: Claude CLI timed out after {timeout}s")
        return None
    except FileNotFoundError:
        print("Error: Claude CLI not found. Is it installed?")
        return None
    except Exception as e:
        print(f"Error in semantic analysis: {e}")
        return None


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Try to extract JSON from text that may have surrounding content."""
    start = text.find('{')
    if start == -1:
        return None

    depth = 0
    for i, char in enumerate(text[start:], start):
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    return None
    return None


def _validate_response(content: Any) -> Optional[Dict[str, Any]]:
    """Validate and normalize the response from Claude."""
    if not isinstance(content, dict):
        return None

    if "is_learning" not in content:
        return None

    # Normalize boolean
    is_learning = content.get("is_learning")
    if isinstance(is_learning, str):
        is_learning = is_learning.lower() in ("true", "yes", "1")
    else:
        is_learning = bool(is_learning)

    # Normalize type
    learning_type = content.get("type")
    if learning_type not in ("correction", "positive", "explicit", None):
        learning_type = None

    # Normalize confidence
    try:
        confidence = float(content.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
    except (TypeError, ValueError):
        confidence = 0.5 if is_learning else 0.0

    return {
        "is_learning": is_learning,
        "type": learning_type if is_learning else None,
        "confidence": confidence,
        "reasoning": str(content.get("reasoning", "")),
        "extracted_learning": content.get("extracted_learning") if is_learning else None,
    }


def analyze_messages(
    messages: List[str],
    timeout: int = DEFAULT_TIMEOUT,
    model: Optional[str] = None,
    min_confidence: float = 0.6
) -> List[Dict[str, Any]]:
    """
    Analyze multiple messages and return only valid learnings.

    Args:
        messages: List of user messages to analyze
        timeout: Timeout per message
        model: Optional model override
        min_confidence: Minimum confidence threshold (default 0.6)

    Returns:
        List of validated learnings above threshold
    """
    learnings = []

    for msg in messages:
        result = semantic_analyze(msg, timeout=timeout, model=model)

        if result is None:
            continue

        if not result.get("is_learning"):
            continue

        if result.get("confidence", 0) < min_confidence:
            continue

        learnings.append({
            "original_message": msg,
            **result
        })

    return learnings


# =============================================================================
# Multi-language examples for testing
# =============================================================================

TEST_MESSAGES = {
    "en": "No, use uv instead of pip!",
    "de": "Nein, benutze immer pytest statt unittest!",
    "es": "No, usa Python en vez de JavaScript",
    "fr": "Non, utilise toujours ruff pour le linting",
    "greeting": "Hello, how are you?",  # Should NOT be detected
    "question": "Can you help me with this?",  # Should NOT be detected
}


if __name__ == "__main__":
    # Test mode
    if len(sys.argv) > 1:
        test_text = " ".join(sys.argv[1:])
        print(f"Analyzing: {test_text!r}")
        result = semantic_analyze(test_text)
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("Analysis failed or returned None")
    else:
        # Run multi-language tests
        print("Running multi-language detection tests...\n")
        for lang, msg in TEST_MESSAGES.items():
            print(f"[{lang}] {msg}")
            result = semantic_analyze(msg)
            if result:
                status = "✓ LEARNING" if result["is_learning"] else "✗ Not a learning"
                print(f"  {status} (confidence: {result['confidence']:.2f})")
                if result.get("extracted_learning"):
                    print(f"  → {result['extracted_learning']}")
            else:
                print("  ✗ Analysis failed")
            print()
