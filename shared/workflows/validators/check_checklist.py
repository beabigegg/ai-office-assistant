#!/usr/bin/env python3
"""Checklist validator — ensures AI addressed all active checklist items.

Reads checklist from: shared/workflows/checklists/{workflow}__{node_id}.yaml
Checks that outputs["checklist_responses"] has an entry for each active item.

Enforcement levels:
1. Presence: every active item must have a response
2. Length: response must be >= MIN_ANSWER_LEN characters
3. Evidence (optional): if item has 'evidence_pattern', response must match the regex

The validator does NOT judge whether answers are correct — that is the user's role.
It enforces that all active items were explicitly addressed with substantive responses.
"""
import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHECKLISTS_DIR = ROOT / 'shared' / 'workflows' / 'checklists'

MIN_ANSWER_LEN = 10


def _normalize_responses(responses):
    """Accept both legacy dict responses and structured list-of-dict responses."""
    if isinstance(responses, dict):
        return {str(k): str(v) for k, v in responses.items()}

    if isinstance(responses, list):
        normalized = {}
        for item in responses:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", "")).strip()
            if not item_id:
                continue
            evidence = str(item.get("evidence", "")).strip()
            status = str(item.get("status", "")).strip()
            details = item.get("details")
            answer = evidence
            if status:
                answer = f"{status}: {answer}" if answer else status
            if details:
                answer = f"{answer} | details={details}" if answer else f"details={details}"
            normalized[item_id] = answer
        return normalized

    return {}


def _load_yaml(path):
    """Load YAML file, fallback to basic parsing if PyYAML unavailable."""
    if yaml:
        return yaml.safe_load(path.read_text(encoding='utf-8'))

    # Minimal fallback: parse just the item IDs and statuses
    import re
    content = path.read_text(encoding='utf-8')
    items = []
    current = {}
    for line in content.split('\n'):
        m = re.match(r'\s*-\s*id:\s*(.+)', line)
        if m:
            if current:
                items.append(current)
            current = {'id': m.group(1).strip().strip('"').strip("'")}
        m = re.match(r'\s*status:\s*(.+)', line)
        if m and current:
            current['status'] = m.group(1).strip().strip('"').strip("'")
        m = re.match(r'\s*description:\s*(.+)', line)
        if m and current:
            current['description'] = m.group(1).strip().strip('"').strip("'")
        m = re.match(r'\s*evidence_pattern:\s*(.+)', line)
        if m and current:
            current['evidence_pattern'] = m.group(1).strip().strip('"').strip("'")
    if current:
        items.append(current)
    return {'items': items}


def validate(context: dict) -> tuple:
    """Validate that all active checklist items have been answered.

    Returns (bool, str):
        (True, message) if all items addressed
        (False, message) if items missing or answers too short
    """
    node_id = context.get("node_id", "unknown")
    instance = context.get("instance", {})
    outputs = context.get("outputs", {})
    workflow_name = instance.get("workflow", "unknown")

    # Find checklist file
    checklist_path = CHECKLISTS_DIR / f"{workflow_name}__{node_id}.yaml"
    if not checklist_path.exists():
        return True, f"No checklist for {workflow_name}__{node_id} (OK)"

    # Load and filter active items
    try:
        checklist = _load_yaml(checklist_path)
    except Exception as e:
        return False, f"Failed to parse checklist: {e}"

    items = checklist.get('items', [])
    active_items = [c for c in items if c.get('status', 'active') == 'active']

    if not active_items:
        return True, "No active checklist items"

    # Check responses
    responses = _normalize_responses(outputs.get("checklist_responses", {}))
    if not responses:
        item_list = ', '.join(c['id'] for c in active_items)
        return False, f"Missing checklist_responses in outputs. Required: {item_list}"

    missing = []
    too_short = []
    for item in active_items:
        item_id = item['id']
        answer = responses.get(item_id, "")
        if not answer:
            missing.append(item_id)
        elif len(str(answer).strip()) < MIN_ANSWER_LEN:
            too_short.append(item_id)

    if missing:
        return False, f"Checklist items not answered: {', '.join(missing)}"
    if too_short:
        return False, f"Checklist answers too short (<{MIN_ANSWER_LEN} chars): {', '.join(too_short)}"

    # Evidence pattern check (R2: Harness Engineering)
    no_evidence = []
    for item in active_items:
        item_id = item['id']
        pattern = item.get('evidence_pattern')
        if not pattern:
            continue
        answer = str(responses.get(item_id, ""))
        try:
            if not re.search(pattern, answer, re.IGNORECASE):
                no_evidence.append(f"{item_id} (expected: /{pattern}/)")
        except re.error:
            pass  # skip malformed patterns

    if no_evidence:
        return False, f"Checklist answers lack required evidence: {', '.join(no_evidence)}"

    return True, f"Checklist passed: {len(active_items)} items verified"
