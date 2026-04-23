#!/usr/bin/env python3
"""
Workflow Coordinator v2.0
Thin CLI wrapper over WorkflowEngine (engine.py).

Changes from v1.0:
  - Node completion delegates to WorkflowEngine (retry/timeout/error-log)
  - Stop hook uses engine.is_terminal_state() instead of inline check
  - workflow_errors.log records all validator failures (JSONL)
  - Retry / timeout fields in workflow JSON are now enforced
  - coordinator_legacy.py preserved as rollback target
"""
import json
import sys
import os
import time
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = ROOT / 'shared' / 'workflows'

# Ensure engine.py (same directory) is importable regardless of CWD
_this_dir = str(Path(__file__).resolve().parent)
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)
DEFINITIONS_DIR = WORKFLOWS_DIR / 'definitions'
STATE_FILE = WORKFLOWS_DIR / 'state' / 'current.json'
OVERRIDE_AUDIT_LOG = WORKFLOWS_DIR / 'state' / 'force_close_audit.jsonl'
RUNTIME_LOG = WORKFLOWS_DIR / 'state' / 'workflow_runtime.jsonl'

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


def _append_override_audit(entry: dict):
    """Append a force-close override audit entry."""
    OVERRIDE_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with OVERRIDE_AUDIT_LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def _append_runtime_log(event: str, **payload):
    """Append a workflow runtime event."""
    RUNTIME_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    with RUNTIME_LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + '\n')


# ─── Script Injection ───────────────────────────────────────────────

def _run_injection_script(script_path: str, timeout: int = 60) -> dict:
    """Execute a pre-node Python script, capture stdout as injected context.

    Non-blocking: failures are logged as warnings, never abort the workflow.
    Returns dict with keys: script, ok, stdout, stderr, returncode, duration_ms, error.
    """
    result = {
        "script": script_path,
        "ok": False,
        "stdout": "",
        "stderr": "",
        "returncode": None,
        "duration_ms": 0,
        "error": None,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }
    resolved = Path(script_path)
    if not resolved.is_absolute():
        resolved = (ROOT / script_path).resolve()
    if not resolved.exists():
        result["error"] = f"script not found: {resolved}"
        _append_runtime_log('script_injection_error', script=script_path, error=result["error"])
        return result

    py_exec = os.environ.get("CONDA_PYTHON_EXE") or sys.executable
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    t0 = time.time()
    try:
        proc = subprocess.run(
            [py_exec, str(resolved)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
            cwd=str(ROOT),
        )
        result["stdout"] = (proc.stdout or "")[:65536]  # cap at 64 KB
        result["stderr"] = (proc.stderr or "")[:8192]
        result["returncode"] = proc.returncode
        result["ok"] = proc.returncode == 0
        if not result["ok"]:
            result["error"] = f"exit {proc.returncode}"
    except subprocess.TimeoutExpired:
        result["error"] = f"timeout after {timeout}s"
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"{type(exc).__name__}: {exc}"
    result["duration_ms"] = int((time.time() - t0) * 1000)

    _append_runtime_log(
        'script_injection',
        script=str(resolved),
        ok=result["ok"],
        returncode=result["returncode"],
        duration_ms=result["duration_ms"],
        stdout_len=len(result["stdout"]),
        error=result["error"],
    )
    return result


# ─── Core Operations ────────────────────────────────────────────────

def start(workflow_name: str, context: dict, script: str = None) -> tuple:
    """Start a new workflow instance. Returns (success, message).

    If `script` is given, run it before creating the instance and attach
    stdout as context.injected_script (does not abort on script failure).
    """
    state = _load_state()
    defn = _load_definition(workflow_name)

    injection = None
    if script:
        injection = _run_injection_script(script)
        context = dict(context or {})
        context["injected_script"] = {
            "path": injection["script"],
            "ok": injection["ok"],
            "stdout": injection["stdout"],
            "error": injection["error"],
            "ran_at": injection["ran_at"],
        }

    instance_id = f"{workflow_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

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

    warning_flag = STATE_FILE.parent / '.stop_warning_shown'
    warning_flag.unlink(missing_ok=True)

    ready = [n['id'] for n in defn['nodes'] if nodes[n['id']]['status'] == 'ready']
    blocked = [n['id'] for n in defn['nodes'] if nodes[n['id']]['status'] == 'blocked']
    _append_runtime_log(
        'workflow_started',
        workflow=workflow_name,
        instance_id=instance_id,
        context=context,
        ready_nodes=ready,
        blocked_nodes=blocked,
    )
    msg = (
        f"[WORKFLOW] Started '{workflow_name}' as {instance_id}\n"
        f"  Nodes: {len(defn['nodes'])} total\n"
        f"  READY: {', '.join(ready)}\n"
    )
    if blocked:
        msg += f"  BLOCKED: {', '.join(blocked)}\n"
    if injection is not None:
        tag = "OK" if injection["ok"] else "WARN"
        msg += f"  [SCRIPT {tag}] {injection['script']} ({injection['duration_ms']} ms"
        if injection["error"]:
            msg += f"; {injection['error']}"
        msg += f"; stdout={len(injection['stdout'])} chars)\n"
        if injection["stdout"]:
            preview = injection["stdout"].strip().splitlines()
            head = preview[:20]
            msg += "  --- injected stdout ---\n"
            for ln in head:
                msg += f"  | {ln}\n"
            if len(preview) > 20:
                msg += f"  | ... ({len(preview) - 20} more lines — full stdout stored in state)\n"
    return True, msg


def complete(node_id: str, outputs: dict = None, instance_id: str = None, script: str = None) -> tuple:
    """Complete a node using WorkflowEngine (retry/timeout/error-log aware).

    If `script` is given, run it before validating the node and merge its
    stdout into outputs.injected_script (non-blocking; a failed script is
    logged as a warning but does not abort node completion).
    """
    from engine import WorkflowEngine  # lazy import to avoid circular at module level

    state = _load_state()
    outputs = dict(outputs or {})
    injection = None
    if script:
        injection = _run_injection_script(script)
        outputs["injected_script"] = {
            "path": injection["script"],
            "ok": injection["ok"],
            "stdout": injection["stdout"],
            "error": injection["error"],
            "ran_at": injection["ran_at"],
        }

    # Locate instance
    inst = None
    if instance_id and instance_id in state["active"]:
        inst = state["active"][instance_id]
    else:
        for iid, candidate in state["active"].items():
            if node_id in candidate["nodes"]:
                inst = candidate
                instance_id = iid
                break

    if inst is None:
        for h in state.get("history", []):
            if h.get("workflow"):
                try:
                    defn_check = _load_definition(h["workflow"])
                    if any(n["id"] == node_id for n in defn_check["nodes"]):
                        return False, (
                            f"[ERROR] No active workflow contains node '{node_id}' "
                            "(workflow already completed and archived)"
                        )
                except (FileNotFoundError, KeyError):
                    pass
        return False, f"[ERROR] No active workflow contains node '{node_id}'"

    # Delegate to engine
    engine = WorkflowEngine.from_instance(inst, state)
    _append_runtime_log(
        'complete_requested',
        workflow=inst["workflow"],
        instance_id=instance_id,
        node=node_id,
        outputs=outputs,
    )
    ok, msg = engine.complete_node(node_id, outputs)

    if ok:
        # Check if all required nodes are now done
        all_required_done = engine.is_terminal_state()

        if all_required_done:
            # Auto-skip remaining optional nodes
            defn = inst["definition"]
            for n in defn["nodes"]:
                nid = n["id"]
                if (not n.get("required", True)
                        and inst["nodes"][nid]["status"] not in ("completed", "skipped")):
                    inst["nodes"][nid]["status"] = "skipped"

            inst["completed_at"] = datetime.now(timezone.utc).isoformat()
            _archive_completed(state, instance_id)
            _increment_counter(state, inst["workflow"])
            _append_runtime_log(
                'workflow_completed',
                workflow=inst["workflow"],
                instance_id=instance_id,
                node=node_id,
                completed_at=inst["completed_at"],
            )
            msg += f"\n[WORKFLOW] '{inst['workflow']}' fully completed!"

            wf_name = inst["workflow"]
            count = state["counters"].get(wf_name, 0)
            if wf_name == "post_task" and count % 3 == 0 and count > 0:
                msg += (
                    f"\n[PROMOTE] post_task completed {count} times. "
                    "Consider running /promote for knowledge upgrade review."
                )

    if injection is not None:
        tag = "OK" if injection["ok"] else "WARN"
        script_msg = (
            f"\n  [SCRIPT {tag}] {injection['script']} ({injection['duration_ms']} ms"
        )
        if injection["error"]:
            script_msg += f"; {injection['error']}"
        script_msg += f"; stdout={len(injection['stdout'])} chars)"
        if injection["stdout"]:
            preview_lines = injection["stdout"].strip().splitlines()
            head = preview_lines[:20]
            script_msg += "\n  --- injected stdout ---"
            for ln in head:
                script_msg += f"\n  | {ln}"
            if len(preview_lines) > 20:
                script_msg += f"\n  | ... ({len(preview_lines) - 20} more lines)"
        msg = script_msg + "\n" + msg

    _append_runtime_log(
        'complete_result',
        workflow=inst["workflow"],
        instance_id=instance_id,
        node=node_id,
        ok=ok,
        message=msg,
    )
    _save_state(state)
    return ok, msg


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
            elif st == "SKIPPED":
                icon = "[-]"
            elif st == "READY":
                icon = "[>]"
            elif st == "FAILED":
                icon = "[!]"
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
    state["last_workflow_completed_at"] = inst["completed_at"]
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


# ─── Hook Handlers ──────────────────────────────────────────────────

def _detect_significant_work() -> bool:
    """Heuristic: recent file modifications suggest work was done."""
    import glob as _glob
    now = time.time()

    state = _load_state()
    last_completed = state.get("last_workflow_completed_at")
    if not last_completed and state.get("history"):
        last_completed = state["history"][0].get("completed_at")

    cutoff = now - 1800  # fallback: 30 minutes
    if last_completed:
        try:
            cutoff = datetime.fromisoformat(last_completed).timestamp() + 7200  # 2h grace
        except (ValueError, OSError):
            pass

    patterns = [
        str(ROOT / 'projects' / '*' / 'vault' / 'outputs' / '*'),
        str(ROOT / 'projects' / '*' / 'workspace' / 'db' / '*.db'),
        # Extended: daily ECR/analysis work patterns
        str(ROOT / 'projects' / '*' / 'workspace' / 'scripts' / '*.py'),
        str(ROOT / 'projects' / '*' / 'workspace' / 'project_state.md'),
        str(ROOT / 'projects' / '*' / 'workspace' / 'memos' / '*'),
        str(ROOT / 'shared' / 'kb' / 'dynamic' / '*.md'),
    ]
    for pattern in patterns:
        for f in _glob.glob(pattern):
            try:
                if Path(f).stat().st_mtime > cutoff:
                    return True
            except OSError:
                continue

    # Also check workflow_runtime.jsonl for any recent complete_result event
    if RUNTIME_LOG.exists():
        try:
            with RUNTIME_LOG.open('r', encoding='utf-8') as _f:
                for _line in _f:
                    try:
                        _entry = json.loads(_line.strip())
                        if _entry.get('event') == 'complete_result':
                            _ts = _entry.get('ts', '')
                            if _ts and datetime.fromisoformat(_ts).timestamp() > cutoff:
                                return True
                    except (json.JSONDecodeError, ValueError):
                        continue
        except OSError:
            pass

    return False


def _handle_stop_hook():
    """Called by Stop hook. Uses engine.is_terminal_state() to decide."""
    from engine import WorkflowEngine  # lazy import

    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        hook_input = {}

    if hook_input.get('stop_hook_active'):
        sys.exit(0)

    state = _load_state()

    # No active workflows
    if not state["active"]:
        warning_flag = STATE_FILE.parent / '.stop_warning_shown'
        if _detect_significant_work():
            if not warning_flag.exists():
                warning_flag.write_text(
                    datetime.now(timezone.utc).isoformat(), encoding='utf-8'
                )
                msg = (
                    "[WARNING] No active workflow, but recent work detected "
                    "(workspace/scripts, project_state.md, memos, kb/dynamic, or workflow completion events).\n"
                    "Did you forget to run post_task workflow?\n"
                    "  python shared/workflows/coordinator.py start post_task "
                    "--context '{\"project\":\"...\",\"task\":\"...\"}'\n"
                    "To proceed without post_task, stop again."
                )
                sys.stderr.write(msg)
                sys.exit(2)
            else:
                warning_flag.unlink(missing_ok=True)
                sys.exit(0)
        else:
            warning_flag.unlink(missing_ok=True)
            sys.exit(0)

    # Check terminal state for each active workflow via engine
    pending_lines = []
    for iid, inst in state["active"].items():
        engine = WorkflowEngine.from_instance(inst, state)
        if not engine.is_terminal_state():
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
            + "\n\nComplete these nodes before stopping. If this is a workflow design gap,"
              " the user may explicitly override with:\n"
              "  python shared/workflows/coordinator.py force_close "
              "--approved-by-user --reason \"workflow_design_gap\""
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


def force_close(user_approved: bool = False, reason: str = ''):
    """Force-close all active workflows without completing nodes."""
    if not user_approved:
        return (
            "[DENY] force_close requires explicit user approval. "
            "Re-run with --approved-by-user --reason \"workflow_design_gap|validator_false_fail|exceptional_business_case\""
        )
    if not reason.strip():
        return "[DENY] force_close requires a non-empty --reason for audit logging."

    state = _load_state()
    closed = list(state["active"].keys())
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "closed_instances": closed,
        "active_count": len(closed),
    }
    for iid in closed:
        inst = state["active"][iid]
        inst["completed_at"] = datetime.now(timezone.utc).isoformat()
        _archive_completed(state, iid)
    _append_override_audit(entry)
    _append_runtime_log(
        'force_close_override',
        reason=reason,
        closed_instances=closed,
        active_count=len(closed),
    )
    _save_state(state)
    if closed:
        return (
            f"[FORCE] Closed {len(closed)} workflow(s): {', '.join(closed)} "
            f"| reason={reason}"
        )
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
            print("Usage: coordinator.py start <workflow_name> [--context '{...}'] [--script <path>]")
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
        script_path = None
        if '--script' in sys.argv:
            idx = sys.argv.index('--script')
            if idx + 1 < len(sys.argv):
                script_path = sys.argv[idx + 1]
        ok, msg = start(wf_name, ctx, script=script_path)
        print(msg)
        sys.exit(0 if ok else 1)

    elif cmd == 'complete':
        if len(sys.argv) < 3:
            print("Usage: coordinator.py complete <node_id> [--outputs '{...}'] [--instance <id>] [--script <path>]")
            sys.exit(1)
        node_id = sys.argv[2]
        outputs = {}
        inst_id = None
        script_path = None
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
        if '--script' in sys.argv:
            idx = sys.argv.index('--script')
            if idx + 1 < len(sys.argv):
                script_path = sys.argv[idx + 1]
        ok, msg = complete(node_id, outputs, inst_id, script=script_path)
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
        approved = '--approved-by-user' in sys.argv
        reason = ''
        if '--reason' in sys.argv:
            idx = sys.argv.index('--reason')
            if idx + 1 < len(sys.argv):
                reason = sys.argv[idx + 1]
        result = force_close(user_approved=approved, reason=reason)
        print(result)
        sys.exit(0 if result.startswith("[FORCE]") else 1)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == '__main__':
    main()
