#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_JSON = ROOT / "shared" / "registry" / "capability_registry.json"
DEFAULT_SUGGESTIONS = ROOT / "shared" / "registry" / "semantic_relation_suggestions.json"
DEFAULT_REVIEW = ROOT / "shared" / "registry" / "semantic_relation_review.json"


def load_registry() -> dict:
    return load_json(REGISTRY_JSON)


def load_review_policy() -> dict:
    registry = load_registry()
    return (
        registry.get("indexing_policy", {})
        .get("semantic_review_policy", {})
    )


def load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve(path_str: str | None, default: Path) -> Path:
    if not path_str:
        return default
    return (ROOT / path_str).resolve()


def cmd_prepare(args: argparse.Namespace) -> int:
    suggestions_path = _resolve(args.suggestions, DEFAULT_SUGGESTIONS)
    review_path = _resolve(args.output, DEFAULT_REVIEW)
    payload = load_json(suggestions_path)
    suggestions = payload.get("suggestions", []) if isinstance(payload, dict) else payload
    policy = load_review_policy()

    review_doc = {
        "version": 1,
        "prepared_at": _now_iso(),
        "source": str(suggestions_path.relative_to(ROOT).as_posix()),
        "policy_snapshot": policy,
        "items": [],
    }
    for idx, suggestion in enumerate(suggestions, start=1):
        relation_type = suggestion.get("type", "")
        review_doc["items"].append({
            "review_id": f"SR-{idx:03d}",
            "status": "pending",
            "review_notes": "",
            "reviewed_at": "",
            "applied_at": "",
            "documented_evidence": [],
            "discoverability_impact": "",
            "policy_flags": {
                "documented_evidence_required": bool(policy.get("require_documented_evidence", True)),
                "semi_auto_eligible": relation_type in set(policy.get("semi_auto_apply_relation_types", [])),
                "high_risk": relation_type in set(policy.get("high_risk_relation_types", [])),
            },
            "suggestion": suggestion,
        })

    save_json(review_path, review_doc)
    print(f"prepared: {review_path.relative_to(ROOT).as_posix()}")
    print(f"items: {len(review_doc['items'])}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    review_path = _resolve(args.review, DEFAULT_REVIEW)
    review_doc = load_json(review_path)
    items = review_doc.get("items", [])
    if args.status:
        items = [item for item in items if item.get("status") == args.status]
    if args.json:
        sys.stdout.buffer.write((json.dumps(items, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0
    if not items:
        print("(no rows)")
        return 0
    headers = ["review_id", "status", "from", "type", "to", "confidence"]
    widths = {h: len(h) for h in headers}
    rows = []
    for item in items:
        sug = item["suggestion"]
        row = {
            "review_id": item["review_id"],
            "status": item["status"],
            "from": sug["from"],
            "type": sug["type"],
            "to": sug["to"],
            "confidence": sug.get("confidence", ""),
        }
        rows.append(row)
        for key, value in row.items():
            widths[key] = max(widths[key], len(str(value)))
    print(" | ".join(f"{h:<{widths[h]}}" for h in headers))
    print("-+-".join("-" * widths[h] for h in headers))
    for row in rows:
        print(" | ".join(f"{str(row[h]):<{widths[h]}}" for h in headers))
    return 0


def _update_status(review_doc: dict, review_id: str, status: str, notes: str) -> bool:
    for item in review_doc.get("items", []):
        if item.get("review_id") != review_id:
            continue
        item["status"] = status
        item["review_notes"] = notes
        item["reviewed_at"] = _now_iso()
        return True
    return False


def _find_item(review_doc: dict, review_id: str) -> dict | None:
    for item in review_doc.get("items", []):
        if item.get("review_id") == review_id:
            return item
    return None


def cmd_approve(args: argparse.Namespace) -> int:
    review_path = _resolve(args.review, DEFAULT_REVIEW)
    review_doc = load_json(review_path)
    item = _find_item(review_doc, args.review_id)
    if item is None:
        print(f"review id not found: {args.review_id}")
        return 1
    policy = review_doc.get("policy_snapshot", {})
    if policy.get("require_documented_evidence", True) and not args.evidence:
        print("documented evidence is required for approval")
        return 1
    if not args.impact:
        print("discoverability impact is required for approval")
        return 1
    item["status"] = "approved"
    item["review_notes"] = args.notes or ""
    item["reviewed_at"] = _now_iso()
    item["documented_evidence"] = args.evidence or []
    item["discoverability_impact"] = args.impact
    save_json(review_path, review_doc)
    print(f"approved: {args.review_id}")
    return 0


def cmd_reject(args: argparse.Namespace) -> int:
    review_path = _resolve(args.review, DEFAULT_REVIEW)
    review_doc = load_json(review_path)
    if not _update_status(review_doc, args.review_id, "rejected", args.notes or ""):
        print(f"review id not found: {args.review_id}")
        return 1
    save_json(review_path, review_doc)
    print(f"rejected: {args.review_id}")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    review_path = _resolve(args.review, DEFAULT_REVIEW)
    review_doc = load_json(review_path)
    registry = load_registry()
    relations = registry.setdefault("relations", [])
    existing = {(r["from"], r["type"], r["to"]) for r in relations}
    policy = review_doc.get("policy_snapshot", {})
    semi_auto_types = set(policy.get("semi_auto_apply_relation_types", []))

    applied = 0
    skipped = 0
    blocked = 0
    for item in review_doc.get("items", []):
        if item.get("status") != "approved":
            continue
        sug = item["suggestion"]
        key = (sug["from"], sug["type"], sug["to"])
        if not args.include_high_risk and sug["type"] not in semi_auto_types:
            blocked += 1
            continue
        if key in existing:
            item["status"] = "applied"
            item["applied_at"] = _now_iso()
            skipped += 1
            continue
        relations.append({
            "from": sug["from"],
            "type": sug["type"],
            "to": sug["to"],
            "notes": (
                f"approved semantic suggestion ({item['review_id']}): "
                f"{sug.get('reason', '')} | evidence={'; '.join(item.get('documented_evidence', []))} | "
                f"impact={item.get('discoverability_impact', '')}"
            ).strip(),
        })
        existing.add(key)
        item["status"] = "applied"
        item["applied_at"] = _now_iso()
        applied += 1

    registry["updated"] = _now_iso()[:10]
    save_json(REGISTRY_JSON, registry)
    save_json(review_path, review_doc)
    print(f"applied: {applied}")
    print(f"already_present: {skipped}")
    print(f"blocked_high_risk_or_manual: {blocked}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review and apply semantic relation suggestions before they enter the authority registry.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="Convert suggestion output into a review file.")
    p_prepare.add_argument("--suggestions", help="Suggestion JSON path.")
    p_prepare.add_argument("--output", help="Review JSON path.")
    p_prepare.set_defaults(func=cmd_prepare)

    p_list = sub.add_parser("list", help="List review items.")
    p_list.add_argument("--review", help="Review JSON path.")
    p_list.add_argument("--status", choices=["pending", "approved", "rejected", "applied"])
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_approve = sub.add_parser("approve", help="Approve one review item.")
    p_approve.add_argument("review_id")
    p_approve.add_argument("--review", help="Review JSON path.")
    p_approve.add_argument("--notes", help="Optional review notes.")
    p_approve.add_argument("--evidence", action="append", help="Documented evidence path or citation. Required by policy; can be passed multiple times.")
    p_approve.add_argument("--impact", help="How this relation clearly improves discoverability. Required by policy.")
    p_approve.set_defaults(func=cmd_approve)

    p_reject = sub.add_parser("reject", help="Reject one review item.")
    p_reject.add_argument("review_id")
    p_reject.add_argument("--review", help="Review JSON path.")
    p_reject.add_argument("--notes", help="Optional rejection notes.")
    p_reject.set_defaults(func=cmd_reject)

    p_apply = sub.add_parser("apply", help="Apply all approved review items into capability_registry.json.")
    p_apply.add_argument("--review", help="Review JSON path.")
    p_apply.add_argument("--include-high-risk", action="store_true", help="Also apply approved high-risk/manual relation types.")
    p_apply.set_defaults(func=cmd_apply)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
