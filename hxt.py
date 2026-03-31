"""
hxt.py
MIT © Gemmina Intelligence LLC

Reference implementation for the .hxt format.
Python 3.8+ with no external dependencies.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

HXT_VERSION = "0.1.0"
MARKER_BEGIN = "<!--hxt:begin-->"
MARKER_END = "<!--hxt:end-->"
AI_BULK_THRESHOLD_CHARS = 500
AI_BULK_THRESHOLD_MS = 2000
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHORT_HASH_RE = re.compile(r"^[0-9a-f]{16}$")
STATE_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def crystallize(
    current_text: str,
    author_type: str = "auto",
    prev_ledger: Optional[Dict[str, Any]] = None,
    prev_length: int = 0,
    elapsed_ms: int = 9999,
    now_ms: Optional[int] = None,
) -> str:
    """Add or update the .hxt ledger in a Markdown document."""
    clean_text = strip_hxt_block(str(current_text))
    now_ms = now_ms if isinstance(now_ms, int) else _epoch_ms()
    delta = len(clean_text) - prev_length
    resolved_author = _resolve_author_type(author_type, delta, elapsed_ms)
    full_hash = sha256_full(clean_text)
    iso_now = _iso_from_ms(now_ms)

    step = {
        "t": now_ms // 1000,
        "type": resolved_author,
        "delta": delta,
        "hash": full_hash[:16],
    }

    previous_steps = list(prev_ledger.get("ledger", [])) if isinstance(prev_ledger, dict) else []
    steps = previous_steps + [step]
    ledger = {
        "hxt_version": HXT_VERSION,
        "genesis": prev_ledger["genesis"] if isinstance(prev_ledger, dict) and isinstance(prev_ledger.get("genesis"), str) else iso_now,
        "ledger": steps,
        "final_seal": {
            "sealed_at": iso_now,
            "human_touch": _compute_human_touch(steps),
            "state_hash": f"sha256:{full_hash}",
            "step_count": len(steps),
        },
    }

    block = f"{MARKER_BEGIN}\n{json.dumps(ledger, indent=2)}\n{MARKER_END}"
    return f"{clean_text}\n\n{block}" if clean_text else block


def inspect(file_content: str) -> Optional[Dict[str, Any]]:
    """Parse the .hxt ledger from file content."""
    parts = _extract_hxt_parts(str(file_content))
    if not parts:
        return None

    try:
        ledger = json.loads(parts["json_text"])
    except json.JSONDecodeError:
        return None

    return {"ledger": ledger, "body_text": parts["body_text"]}


def verify(file_content: str) -> Dict[str, Any]:
    """Verify the integrity and schema of a .hxt document."""
    parts = _extract_hxt_parts(str(file_content))
    if not parts:
        return _malformed("Required hxt markers were not found.")

    try:
        ledger = json.loads(parts["json_text"])
    except json.JSONDecodeError:
        return _malformed("Ledger JSON could not be parsed.")

    schema_error = _validate_ledger_schema(ledger)
    if schema_error:
        return _malformed(schema_error)

    expected_human_touch = _compute_human_touch(ledger["ledger"])
    if ledger["final_seal"]["human_touch"] != expected_human_touch:
        return _malformed("final_seal.human_touch does not match the ledger.")

    full_hash = sha256_full(parts["body_text"])
    short_hash = full_hash[:16]
    expected_state_hash = f"sha256:{full_hash}"
    last_step = ledger["ledger"][-1]

    if last_step["hash"] != short_hash:
        return _tampered("Last step hash does not match document content.", short_hash, last_step["hash"])

    if ledger["final_seal"]["state_hash"] != expected_state_hash:
        return _tampered(
            "state_hash does not match document content.",
            expected_state_hash,
            ledger["final_seal"]["state_hash"],
        )

    return {
        "valid": True,
        "status": "ok",
        "version": ledger["hxt_version"],
        "genesis": ledger["genesis"],
        "sealed_at": ledger["final_seal"]["sealed_at"],
        "step_count": ledger["final_seal"]["step_count"],
        "human_touch": ledger["final_seal"]["human_touch"],
    }


def summary(file_content: str) -> Optional[Dict[str, Any]]:
    """Return a human-readable summary dict."""
    parsed = inspect(str(file_content))
    if not parsed:
        return None

    ledger = parsed["ledger"]
    steps = ledger.get("ledger", [])
    human_touch = ledger.get("final_seal", {}).get("human_touch", 0)

    return {
        "version": ledger.get("hxt_version"),
        "genesis": ledger.get("genesis"),
        "sealed_at": ledger.get("final_seal", {}).get("sealed_at"),
        "step_count": len(steps),
        "ai_steps": sum(1 for step in steps if step.get("type") == "AI"),
        "human_steps": sum(1 for step in steps if step.get("type") == "HUMAN"),
        "human_touch": human_touch,
        "label": _human_touch_label(human_touch),
    }


def strip_hxt_block(text: str) -> str:
    """Remove the hxt block and trailing whitespace before it."""
    begin = text.find(MARKER_BEGIN)
    if begin == -1:
        return text
    return text[:begin].rstrip()


def sha256_full(text: str) -> str:
    """Return the full SHA-256 hex digest of the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_short(text: str) -> str:
    """Return the first 16 hex characters of the SHA-256 digest."""
    return sha256_full(text)[:16]


def _extract_hxt_parts(file_content: str) -> Optional[Dict[str, str]]:
    begin = file_content.find(MARKER_BEGIN)
    end = file_content.find(MARKER_END)

    if begin == -1 or end == -1 or end < begin:
        return None

    return {
        "body_text": file_content[:begin].rstrip(),
        "json_text": file_content[begin + len(MARKER_BEGIN):end].strip(),
    }


def _resolve_author_type(author_type: str, delta: int, elapsed_ms: int) -> str:
    if author_type == "auto":
        return "AI" if abs(delta) > AI_BULK_THRESHOLD_CHARS and elapsed_ms < AI_BULK_THRESHOLD_MS else "HUMAN"
    if author_type in {"AI", "HUMAN"}:
        return author_type
    raise ValueError('author_type must be "AI", "HUMAN", or "auto".')


def _compute_human_touch(steps: list) -> float:
    total = sum(abs(step["delta"]) for step in steps)
    if total == 0:
        return 0.0
    human = sum(abs(step["delta"]) for step in steps if step["type"] == "HUMAN")
    return round(human / total, 3)


def _human_touch_label(score: float) -> str:
    if score >= 0.7:
        return "Sincere"
    if score >= 0.4:
        return "Assisted"
    if score >= 0.1:
        return "AI-heavy"
    return "AI-generated"


def _iso_from_ms(now_ms: int) -> str:
    return datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _epoch_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _is_iso_utc_string(value: Any) -> bool:
    if not isinstance(value, str) or not ISO_UTC_RE.match(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except ValueError:
        return False


def _validate_ledger_schema(ledger: Any) -> Optional[str]:
    if not isinstance(ledger, dict):
        return "Ledger root must be an object."
    if not isinstance(ledger.get("hxt_version"), str) or not SEMVER_RE.match(ledger["hxt_version"]):
        return "hxt_version must be a semantic version string."
    if not _is_iso_utc_string(ledger.get("genesis")):
        return "genesis must be an ISO 8601 UTC timestamp."
    if not isinstance(ledger.get("ledger"), list) or not ledger["ledger"]:
        return "ledger must be a non-empty array."
    if not isinstance(ledger.get("final_seal"), dict):
        return "final_seal must be an object."

    for step in ledger["ledger"]:
        if not isinstance(step, dict):
            return "Each ledger step must be an object."
        if not isinstance(step.get("t"), int):
            return "Each step.t must be an integer."
        if step.get("type") not in {"AI", "HUMAN"}:
            return 'Each step.type must be "AI" or "HUMAN".'
        if not isinstance(step.get("delta"), int):
            return "Each step.delta must be an integer."
        if not isinstance(step.get("hash"), str) or not SHORT_HASH_RE.match(step["hash"]):
            return "Each step.hash must be 16 lowercase hex characters."

    seal = ledger["final_seal"]
    if not _is_iso_utc_string(seal.get("sealed_at")):
        return "final_seal.sealed_at must be an ISO 8601 UTC timestamp."
    if not isinstance(seal.get("human_touch"), (int, float)) or not 0 <= seal["human_touch"] <= 1:
        return "final_seal.human_touch must be a number between 0 and 1."
    if not isinstance(seal.get("state_hash"), str) or not STATE_HASH_RE.match(seal["state_hash"]):
        return 'final_seal.state_hash must look like "sha256:<64 hex chars>".'
    if not isinstance(seal.get("step_count"), int):
        return "final_seal.step_count must be an integer."
    if seal["step_count"] != len(ledger["ledger"]):
        return "final_seal.step_count does not match ledger length."

    return None


def _malformed(reason: str) -> Dict[str, Any]:
    return {"valid": False, "status": "malformed", "reason": reason}


def _tampered(reason: str, expected: str, found: str) -> Dict[str, Any]:
    return {
        "valid": False,
        "status": "tampered",
        "reason": reason,
        "expected": expected,
        "found": found,
    }


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _write_text(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=".hxt reference implementation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify", help="Verify a .hxt document")
    verify_parser.add_argument("path", help="Path to the .hxt file")

    summary_parser = subparsers.add_parser("summary", help="Summarize a .hxt document")
    summary_parser.add_argument("path", help="Path to the .hxt file")

    crystallize_parser = subparsers.add_parser("crystallize", help="Create or update a .hxt file")
    crystallize_parser.add_argument("source", help="Input Markdown or .hxt file")
    crystallize_parser.add_argument("output", help="Output .hxt file")
    crystallize_parser.add_argument("--author", default="auto", choices=["auto", "AI", "HUMAN"], help="Author type")
    crystallize_parser.add_argument("--prev-length", type=int, default=None, help="Override previous body length")
    crystallize_parser.add_argument("--elapsed-ms", type=int, default=9999, help="Milliseconds since last save")
    crystallize_parser.add_argument("--now-ms", type=int, default=None, help="Override current epoch milliseconds")

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "verify":
        result = verify(_read_text(args.path))
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1

    if args.command == "summary":
        result = summary(_read_text(args.path))
        if result is None:
            print(json.dumps(_malformed("Required hxt markers were not found."), indent=2))
            return 1
        print(json.dumps(result, indent=2))
        return 0

    source_content = _read_text(args.source)
    parsed = inspect(source_content)
    prev_ledger = parsed["ledger"] if parsed else None
    prev_length = args.prev_length if args.prev_length is not None else (len(parsed["body_text"]) if parsed else 0)
    output = crystallize(
        source_content,
        author_type=args.author,
        prev_ledger=prev_ledger,
        prev_length=prev_length,
        elapsed_ms=args.elapsed_ms,
        now_ms=args.now_ms,
    )
    _write_text(args.output, output)
    print(json.dumps({"written": args.output}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
