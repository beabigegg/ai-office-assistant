#!/usr/bin/env python3
"""
Workflow Coordinator v1.0
Node-based workflow enforcer for Agent Office v3.0.
Turns soft CLAUDE.md rules into hard-enforced workflow gates via Claude Code Hooks.
"""
import json
import sys
import os
import time
import importlib.util
import tempfile
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = ROOT / 'shared' / 'workflows'
DEFINITIONS_DIR = WORKFLOWS_DIR / 'definitions'
VALIDATORS_DIR = WORKFLOWS_DIR / 'validators'
STATE_FILE = WORKFLOWS_DIR / 'state' / 'current.json'

MAX_HISTORY = 50


# ─── State Management ───────────────────────────────────────────────

def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            pass
    return {"active": {}, "counters": {}, "history": []}


def _save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix('.tmp')
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(str(tmp), str(STATE_FILE))


def _load_definition(name: str) -> dict:
    path = DEFINITIONS_DIR / f'{name}.json'
    if not path.exists():
        raise FileNotFoundError(f"Workflow definition not found: {path}")
    return json.loads(path.read_text(encoding='utf-8'))


# ─── Validator Engine ────────────────────────────────────────────────

def _load_validator(name: str):
    """Dynamically load validators/<name>.py and return its validate function."""
    path = VALIDATORS_DIR / f'{name}.py'
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, 'validate', None)


def _run_validator(validator_name: str, context: dict) -> tuple:
    """Run a named validator. Returns (passed: bool, message: str)."""
    fn = _load_validator(validator_name)
    if fn is None:
        return True, f"validator '{validator_name}' not found, skipped"
    try:
        return fn(context)
    except Exception as e:
        return False, f"validator '{validator_name}' error: {e}"


# ─── Core Operations ────────────────────────────────────────────────

def start(workflow_name: str, context: dict) -> tuple:
    """Start a new workflow instance. Returns (success, message)."""
    state = _load_state()
    defn = _load_definition(workflow_name)

    instance_id = f"{workflow_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # Build node status map
    nodes = {}
    for node in defn['nodes']:
        nid = node['id']
        deps = node.get('depends_on', [])
        nodes[nid] = {
            "status": "ready" if not deps else "blocked",
            "completed_at": None,
            "outputs": {},
            "validator_result": None,
        }

    instance = {
        "id": instance_id,
        "workflow": workflow_name,
        "context": context,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "nodes": nodes,
        "definition": defn,
    }

    state["active"][instance_id] = instance
    _save_state(state)

    # Summary
    ready = [n['id'] for n in defn['nodes'] if nodes[n['id']]['status'] == 'ready']
    blocked = [n['id'] for n in defn['nodes'] if nodes[n['id']]['status'] == 'blocked']
    msg = (
        f"[WORKFLOW] Started '{workflow_name}' as {instance_id}\n"
        f"  Nodes: {len(defn['nodes'])} total\n"
        f"  READY: {', '.join(ready)}\n"
    )
    if blocked:
        msg += f"  BLOCKED: {', '.join(blocked)}\n"
    return True, msg


def complete(node_id: str, outputs: dict = None, instance_id: str = None) -> tuple:
    """Complete a node in an active workflow. Returns (success, message)."""
    state = _load_state()
    outputs = outputs or {}

    # Find the instance containing this node
    inst = None
    if instance_id and instance_id in state["active"]:
        inst = state["active"][instance_id]
    else:
        # Search active workflows for one with this node
        for iid, candidate in state["active"].items():
            if node_id in candidate["nodes"]:
                inst = candidate
                instance_id = iid
                break

    if inst is None:
        return False, f"[ERROR] No active workflow contains node '{node_id}'"

    if node_id not in inst["nodes"]:
        return False, f"[ERROR] Node '{node_id}' not found in {instance_id}"

    node_state = inst["nodes"][node_id]

    if node_state["status"] == "completed":
        return True, f"[SKIP] Node '{node_id}' already completed"

    # Check preconditions (dependencies)
    defn = inst["definition"]
    node_def = next((n for n in defn["nodes"] if n["id"] == node_id), None)
    if node_def is None:
        return False, f"[ERROR] Node definition for '{node_id}' not found"

    deps = node_def.get("depends_on", [])
    for dep in deps:
        if dep in inst["nodes"] and inst["nodes"][dep]["status"] != "completed":
            return False, f"[BLOCKED] Node '{node_id}' requires '{dep}' to complete first"

    # Run postcondition validator if defined
    validator_name = node_def.get("validator")
    validator_result = None
    if validator_name:
        ctx = {
            "outputs": outputs,
            "instance": inst,
            "params": node_def.get("validator_params", {}),
            "root": str(ROOT),
            "project": inst["context"].get("project", ""),
        }
        passed, vmsg = _run_validator(validator_name, ctx)
        validator_result = {"passed": passed, "message": vmsg}
        if not passed:
            node_state["validator_result"] = validator_result
            _save_state(state)
            return False, f"[FAIL] Validator '{validator_name}': {vmsg}"

    # Mark completed
    node_state["status"] = "completed"
    node_state["completed_at"] = datetime.now(timezone.utc).isoformat()
    node_state["outputs"] = outputs
    node_state["validator_result"] = validator_result

    # Unblock downstream nodes
    for n in defn["nodes"]:
        nid = n["id"]
        if nid == node_id:
            continue
        ndeps = n.get("depends_on", [])
        if node_id in ndeps and inst["nodes"][nid]["status"] == "blocked":
            # Check if ALL deps are now completed
            all_met = all(
                inst["nodes"].get(d, {}).get("status") == "completed"
                for d in ndeps
            )
            if all_met:
                inst["nodes"][nid]["status"] = "ready"

    # Check if all required nodes are done
    all_required_done = all(
        inst["nodes"][n["id"]]["status"] == "completed"
        for n in defn["nodes"]
        if n.get("required", True)
    )

    msg = f"[DONE] Node '{node_id}' completed"
    if validator_result:
        msg += f" (validator: {validator_result['message']})"

    if all_required_done:
        # Archive this workflow
        inst["completed_at"] = datetime.now(timezone.utc).isoformat()
        _archive_completed(state, instance_id)
        _increment_counter(state, inst["workflow"])
        msg += f"\n[WORKFLOW] '{inst['workflow']}' fully completed!"

        # Check promote threshold
        wf_name = inst["workflow"]
        count = state["counters"].get(wf_name, 0)
        if wf_name == "post_task" and count % 3 == 0 and count > 0:
            msg += f"\n[PROMOTE] post_task completed {count} times. Consider running /promote for knowledge upgrade review."

    _save_state(state)
    return True, msg


def status(instance_id: str = None) -> str:
    """Return human-readable status of active workflows."""
    state = _load_state()

    if not state["active"]:
        lines = ["No active workflows."]
        if state["counters"]:
            lines.append("\nCounters:")
            for k, v in state["counters"].items():
                lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    lines = []
    targets = (
        {instance_id: state["active"][instance_id]}
        if instance_id and instance_id in state["active"]
        else state["active"]
    )

    for iid, inst in targets.items():
        defn = inst["definition"]
        lines.append(f"=== {iid} ===")
        lines.append(f"  Workflow: {inst['workflow']}")
        lines.append(f"  Started:  {inst['started_at']}")
        lines.append(f"  Context:  {json.dumps(inst['context'])}")
        lines.append(f"  Nodes:")

        for node in defn["nodes"]:
            nid = node["id"]
            ns = inst["nodes"][nid]
            req = "REQ" if node.get("required", True) else "OPT"
            st = ns["status"].upper()

            if st == "COMPLETED":
                icon = "[x]"
            elif st == "READY":
                icon = "[>]"
            else:
                icon = "[ ]"

            line = f"    {icon} {nid} ({req}) - {st}"
            if ns.get("validator_result"):
                vr = ns["validator_result"]
                tag = "PASS" if vr["passed"] else "FAIL"
                line += f" | validator: {tag}"
            lines.append(line)

        lines.append("")

    if state["counters"]:
        lines.append("Counters:")
        for k, v in state["counters"].items():
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def check_pending() -> str:
    """Check for pending required nodes across all active workflows."""
    state = _load_state()

    if not state["active"]:
        return "No pending workflow actions."

    pending = []
    for iid, inst in state["active"].items():
        defn = inst["definition"]
        for node in defn["nodes"]:
            nid = node["id"]
            ns = inst["nodes"][nid]
            if node.get("required", True) and ns["status"] != "completed":
                pending.append({
                    "instance": iid,
                    "node": nid,
                    "status": ns["status"],
                    "description": node.get("description", ""),
                })

    if not pending:
        return "No pending workflow actions."

    lines = [f"[PENDING] {len(pending)} required node(s) incomplete:"]
    for p in pending:
        lines.append(f"  - [{p['status'].upper()}] {p['instance']}/{p['node']}: {p['description']}")
    return "\n".join(lines)


# ─── Lifecycle Helpers ───────────────────────────────────────────────

def _archive_completed(state: dict, instance_id: str):
    inst = state["active"].pop(instance_id, None)
    if inst is None:
        return
    # Strip definition to save space in history
    summary = {
        "id": inst["id"],
        "workflow": inst["workflow"],
        "context": inst["context"],
        "started_at": inst["started_at"],
        "completed_at": inst["completed_at"],
        "node_count": len(inst["nodes"]),
    }
    state["history"].insert(0, summary)
    if len(state["history"]) > MAX_HISTORY:
        state["history"] = state["history"][:MAX_HISTORY]


def _increment_counter(state: dict, workflow_name: str):
    state["counters"][workflow_name] = state["counters"].get(workflow_name, 0) + 1


def _find_active_instance(state: dict, node_id: str) -> str:
    for iid, inst in state["active"].items():
        if node_id in inst["nodes"]:
            return iid
    return None


# ─── Hook Handlers ──────────────────────────────────────────────────

def _handle_stop_hook():
    """Called by Stop hook. Exit 2 to block, exit 0 to allow."""
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        hook_input = {}

    # Prevent infinite loop
    if hook_input.get('stop_hook_active'):
        sys.exit(0)

    state = _load_state()
    if not state["active"]:
        sys.exit(0)

    pending_lines = []
    for iid, inst in state["active"].items():
        defn = inst["definition"]
        for node in defn["nodes"]:
            nid = node["id"]
            ns = inst["nodes"][nid]
            if node.get("required", True) and ns["status"] != "completed":
                pending_lines.append(f"  - {nid}: {node.get('description', '')}")

    if pending_lines:
        msg = (
            "[WORKFLOW BLOCKED] Cannot stop - pending required nodes:\n"
            + "\n".join(pending_lines)
            + "\n\nComplete these nodes before stopping, or use 'coordinator.py force_close' to override."
        )
        sys.stderr.write(msg)
        sys.exit(2)

    sys.exit(0)


def _handle_post_tool():
    """Called by PostToolUse hook for Write/Edit. Injects context if file matches a node output."""
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        sys.exit(0)

    tool_input = hook_input.get('tool_input', {})
    file_path = tool_input.get('file_path', '') or tool_input.get('command', '')

    if not file_path:
        sys.exit(0)

    # Normalize path for matching
    file_path_lower = file_path.replace('\\', '/').lower()

    state = _load_state()
    matches = []

    for iid, inst in state["active"].items():
        defn = inst["definition"]
        for node in defn["nodes"]:
            nid = node["id"]
            ns = inst["nodes"][nid]
            if ns["status"] == "completed":
                continue
            for out in node.get("required_outputs", []):
                pattern = out.get("path_contains", "").lower()
                if pattern and pattern in file_path_lower:
                    matches.append({
                        "instance": iid,
                        "node": nid,
                        "pattern": out.get("path_contains"),
                    })

    if matches:
        hints = []
        for m in matches:
            hints.append(
                f"File write matched workflow node '{m['node']}' in {m['instance']}. "
                f"Run: python shared/workflows/coordinator.py complete {m['node']}"
            )
        result = {"additionalContext": " | ".join(hints)}
        print(json.dumps(result))

    sys.exit(0)


def force_close():
    """Force-close all active workflows without completing nodes."""
    state = _load_state()
    closed = list(state["active"].keys())
    for iid in closed:
        inst = state["active"][iid]
        inst["completed_at"] = datetime.now(timezone.utc).isoformat()
        _archive_completed(state, iid)
    _save_state(state)
    if closed:
        return f"[FORCE] Closed {len(closed)} workflow(s): {', '.join(closed)}"
    return "[FORCE] No active workflows to close."


# ─── CLI Interface ──────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: coordinator.py <command> [args]")
        print("Commands: start, complete, status, check_pending, hook_stop, hook_post, force_close")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'start':
        if len(sys.argv) < 3:
            print("Usage: coordinator.py start <workflow_name> [--context '{...}']")
            sys.exit(1)
        wf_name = sys.argv[2]
        ctx = {}
        if '--context' in sys.argv:
            idx = sys.argv.index('--context')
            if idx + 1 < len(sys.argv):
                try:
                    ctx = json.loads(sys.argv[idx + 1])
                except json.JSONDecodeError:
                    print("[ERROR] Invalid JSON in --context")
                    sys.exit(1)
        ok, msg = start(wf_name, ctx)
        print(msg)
        sys.exit(0 if ok else 1)

    elif cmd == 'complete':
        if len(sys.argv) < 3:
            print("Usage: coordinator.py complete <node_id> [--outputs '{...}'] [--instance <id>]")
            sys.exit(1)
        node_id = sys.argv[2]
        outputs = {}
        inst_id = None
        if '--outputs' in sys.argv:
            idx = sys.argv.index('--outputs')
            if idx + 1 < len(sys.argv):
                try:
                    outputs = json.loads(sys.argv[idx + 1])
                except json.JSONDecodeError:
                    print("[ERROR] Invalid JSON in --outputs")
                    sys.exit(1)
        if '--instance' in sys.argv:
            idx = sys.argv.index('--instance')
            if idx + 1 < len(sys.argv):
                inst_id = sys.argv[idx + 1]
        ok, msg = complete(node_id, outputs, inst_id)
        print(msg)
        sys.exit(0 if ok else 1)

    elif cmd == 'status':
        inst_id = sys.argv[2] if len(sys.argv) > 2 else None
        print(status(inst_id))

    elif cmd == 'check_pending':
        print(check_pending())

    elif cmd == 'hook_stop':
        _handle_stop_hook()

    elif cmd == 'hook_post':
        _handle_post_tool()

    elif cmd == 'force_close':
        print(force_close())

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()
