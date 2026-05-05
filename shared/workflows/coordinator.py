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

from project_ref import list_project_ids, normalize_project_id, project_exists


def _launcher_prefix() -> str:
    return "bash shared/tools/conda-python.sh shared/workflows/coordinator.py"


def _load_promo_module():
    """Load promotion_state module. Returns module or None on any error."""
    try:
        import importlib.util as _ilu
        _path = ROOT / 'shared' / 'tools' / 'promotion_state.py'
        if not _path.exists():
            return None
        _spec = _ilu.spec_from_file_location('promotion_state', str(_path))
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        return _mod
    except Exception:
        return None


def _scan_and_queue_candidates(pm, min_usage: int = 3) -> list:
    """Query kb_index.db for mature learning nodes and enqueue new candidates.

    Returns list of newly-added learning IDs.
    """
    db_path = ROOT / 'shared' / 'kb' / 'knowledge_graph' / 'kb_index.db'
    if not db_path.exists():
        return []
    import sqlite3
    from datetime import timedelta
    try:
        existing = {e.get('learning_id') for e in pm.load_queue(ROOT)}
        # Eval-history: block re-enqueueing of recently evaluated candidates
        eval_history: dict = {}
        if hasattr(pm, 'load_eval_history'):
            try:
                eval_history = pm.load_eval_history(ROOT)
            except Exception:
                pass
        # Build overlap guard: existing skill directory names
        skills_dir = ROOT / '.claude' / 'skills-on-demand'
        existing_skills: set = set()
        if skills_dir.exists():
            existing_skills = {
                d.name for d in skills_dir.iterdir()
                if d.is_dir() and (d / 'SKILL.md').exists()
            }
        with sqlite3.connect(str(db_path)) as _conn:
            rows = _conn.execute(
                "SELECT id, meta_json, refs_skill FROM nodes "
                "WHERE node_type='learning' AND status='active'"
            ).fetchall()
        added = []
        for (_id, _meta_raw, _refs_raw) in rows:
            if _id in existing:
                continue
            try:
                _meta = json.loads(_meta_raw) if _meta_raw else {}
            except Exception:
                _meta = {}
            if int(_meta.get('usage_count', 0) or 0) < min_usage:
                continue
            if _meta.get('status') == 'promoted':
                continue
            # Eval-history exclusion
            _eval = eval_history.get(_id)
            if _eval:
                _eval_result = _eval.get('result', '')
                if _eval_result == 'proposed':
                    # Awaiting /promote approval — never re-enqueue
                    continue
                if _eval_result in ('below_threshold', 'failed', 'unknown'):
                    # 30-day cooldown after failed eval
                    try:
                        _dt = datetime.fromisoformat(_eval.get('evaluated_at', ''))
                        if datetime.now(timezone.utc) - _dt < timedelta(days=30):
                            continue
                    except Exception:
                        continue  # Unparseable timestamp → treat as still cooling down
                if _eval_result == 'overlap':
                    # 7-day cooldown; shorter because overlap may resolve if the blocking
                    # skill is later removed — live overlap guard below is the final check
                    try:
                        _dt = datetime.fromisoformat(_eval.get('evaluated_at', ''))
                        if datetime.now(timezone.utc) - _dt < timedelta(days=7):
                            continue
                    except Exception:
                        continue
                if _eval_result == 'in_progress':
                    # Workflow picked this up but hasn't concluded yet (or crashed).
                    # 24-hour suppression window — long enough to avoid duplicate queuing,
                    # short enough to allow retry after a genuine crash.
                    try:
                        _dt = datetime.fromisoformat(_eval.get('evaluated_at', ''))
                        if datetime.now(timezone.utc) - _dt < timedelta(hours=24):
                            continue
                    except Exception:
                        continue
            # Parse refs_skill: may be JSON array like '["bom-rules"]' or plain string
            _suggested = None
            if _refs_raw:
                try:
                    _parsed = json.loads(_refs_raw)
                    if isinstance(_parsed, list) and _parsed:
                        _suggested = str(_parsed[0])
                    elif isinstance(_parsed, str):
                        _suggested = _parsed
                except Exception:
                    _suggested = _refs_raw
            # Overlap guard: skip if a skill with the same name already exists
            if _suggested and _suggested in existing_skills:
                continue
            if pm.add_candidate(ROOT, _id, _meta, suggested_skill=_suggested):
                added.append(_id)
        return added
    except Exception:
        return []


def _format_sample_outputs(node: dict, project: str = "...") -> dict:
    if node.get("id") == "check_memory_trigger":
        return {
            "memory_conditions_met": True,
            "snapshot_path": "shared/kb/memory/YYYY-MM-DD.md",
            "snapshot_id": "YYYY-MM-DD",
            "trigger_reasons": ["new_decisions"],
            "trigger_evidence": {
                "conversation_rounds": 12,
                "files_written": ["projects/.../workspace/project_state.md"],
                "db_schema_changed": False,
                "db_paths": [],
                "report_paths": [],
            },
        }
    if node.get("id") == "sync_knowledge_index":
        return {
            "index_synced": True,
            "exports_refreshed": True,
        }
    if node.get("id") == "check_promote_threshold":
        return {
            "active_high_count": 5,
            "suggest_run_promote": True,
            "reason": "active_high_count >= 5",
        }
    sample = {}
    required_outputs = node.get("required_outputs", [])
    for req in required_outputs:
        output_key = req.get("output_key")
        if output_key:
            sample[output_key] = f"<{output_key}>"
            continue
        path_contains = req.get("path_contains", "")
        if path_contains:
            if "project_state.md" in path_contains:
                sample["file"] = f"projects/{project}/workspace/project_state.md"
            else:
                sample["file"] = path_contains
    return sample


def _next_step_command(node: dict, instance_id: str, project: str = "...") -> str:
    parts = [_launcher_prefix(), "complete", node["id"], "--instance", instance_id]
    sample_outputs = _format_sample_outputs(node, project=project)
    if sample_outputs:
        parts.extend(["--outputs", f"'{json.dumps(sample_outputs, ensure_ascii=False)}'"])
    return " ".join(parts)


def _usage_text() -> str:
    return (
        "Usage: coordinator.py <command> [args]\n"
        "Commands:\n"
        "  start <workflow_name> [--context '{...}'] [--script <path>]\n"
        "  complete <node_id> [--instance <id>|--session <id>] "
        "[--outputs '{...}'|--artifacts '{...}'] [--sidecar <path>] [--script <path>]\n"
        "    --sidecar  Path to a JSON file produced by an upstream tool "
        "(see shared/tools/sidecar.py).\n"
        "               Its 'outputs' map is merged into node outputs; existing keys "
        "in --outputs win.\n"
        "               The path itself is also injected as 'outputs._sidecar_path'.\n"
        "  list\n"
        "  status [instance_id]\n"
        "  show <instance_id>\n"
        "  check_pending\n"
        "  hook_stop\n"
        "  hook_post\n"
        "  force_close [--instance <id>] --approved-by-user --reason \"...\"\n"
        "  help [command]\n"
    )


def _load_sidecar_outputs(sidecar_path: str) -> tuple[dict, str | None]:
    """Read a sidecar JSON and return (outputs_dict, error_message).

    On success returns (outputs, None). On failure returns ({}, message).
    """
    p = Path(sidecar_path)
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    if not p.exists():
        return {}, f"[ERROR] --sidecar file not found: {p}"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {}, f"[ERROR] --sidecar file is not valid JSON ({p}): {e}"
    sc_outputs = data.get("outputs")
    if sc_outputs is None:
        sc_outputs = {}
    elif not isinstance(sc_outputs, dict):
        return {}, (
            f"[ERROR] --sidecar 'outputs' must be an object, got "
            f"{type(sc_outputs).__name__} ({p})"
        )
    return {"_outputs": sc_outputs, "_path": str(p)}, None


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
    context = dict(context or {})
    if 'project' in context:
        raw_project = context.get('project')
        context['project'] = normalize_project_id(raw_project)
        project_id = context['project']
        raw_project_norm = (raw_project or '').strip().replace('\\', '/').strip('/')
        if raw_project_norm.startswith('projects/'):
            available = ", ".join(list_project_ids(ROOT)[:12])
            return False, (
                "[ERROR] Invalid context.project. Use canonical project id only "
                "(for example 'ecr-ecn', not 'projects/ecr-ecn'). "
                f"Got: {raw_project}. "
                f"Available projects: {available}"
            )
        if not project_exists(ROOT, project_id):
            available = ", ".join(list_project_ids(ROOT)[:12])
            return False, (
                "[ERROR] Invalid context.project. Use canonical project id only "
                "(for example 'ecr-ecn', not 'projects/ecr-ecn'). "
                f"Got: {project_id or '<empty>'}. "
                f"Available projects: {available}"
            )

    injection = None
    if script:
        injection = _run_injection_script(script)
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
    hints = _next_node_hints(defn['nodes'], nodes, instance_id=instance_id, project=context.get('project', '...'))
    if hints:
        msg += hints
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
        # Dequeue select_candidate as soon as it completes (not on workflow end),
        # so the queue is unblocked even if later eval nodes fail or the workflow aborts.
        if node_id == "select_candidate" and inst.get("workflow") == "skill_self_learning":
            _pm = _load_promo_module()
            if _pm is not None:
                try:
                    _sel_out = (outputs or {})
                    _lid = _sel_out.get('learning_id')
                    if not _lid:
                        # Fallback: read from instance state (engine may have stored outputs already)
                        _lid = (
                            inst.get('nodes', {})
                            .get('select_candidate', {})
                            .get('outputs', {}) or {}
                        ).get('learning_id')
                    if _lid:
                        _removed = _pm.remove_candidate(ROOT, _lid)
                        msg += (
                            f"\n[DEQUEUE] {'Removed' if _removed else 'Was not in queue'}: "
                            f"{_lid}"
                        )
                        # Mark as in_progress immediately so the scan suppresses this
                        # learning for 24 h even if the workflow later fails or is aborted.
                        if hasattr(_pm, 'record_eval_result'):
                            _pm.record_eval_result(ROOT, _lid, 'in_progress')
                except Exception:
                    pass

        # Check if all required nodes are now done
        all_required_done = engine.is_terminal_state()

        if not all_required_done:
            hints = _next_node_hints(
                inst["definition"]["nodes"],
                inst["nodes"],
                instance_id=instance_id,
                project=inst.get("context", {}).get("project", "..."),
            )
            if hints:
                msg += hints

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

            if wf_name == "post_task":
                # Run candidate scan on EVERY post_task completion (cheap SQLite read)
                _pm = _load_promo_module()
                if _pm is not None:
                    try:
                        _newly_added = _scan_and_queue_candidates(_pm)
                        if _newly_added:
                            msg += (
                                f"\n[SCAN] Queued {len(_newly_added)} promotion candidate(s): "
                                f"{', '.join(_newly_added[:3])}"
                                + (f" (+{len(_newly_added)-3} more)" if len(_newly_added) > 3 else "")
                            )
                    except Exception:
                        pass
                if count % 3 == 0 and count > 0:
                    msg += (
                        f"\n[PROMOTE] post_task completed {count} times. "
                        "Consider running /promote for knowledge upgrade review."
                    )
                    if _pm is not None:
                        try:
                            _queue = _pm.load_queue(ROOT)
                            if _queue:
                                _ids = [c.get('learning_id', '?') for c in _queue[:3]]
                                _more = f" (+{len(_queue)-3} more)" if len(_queue) > 3 else ""
                                msg += (
                                    f"\n[AUTO-PROMOTE] {len(_queue)} candidate(s) in queue: "
                                    f"{', '.join(_ids)}{_more}. "
                                    "Run: bash shared/tools/conda-python.sh "
                                    "shared/workflows/coordinator.py start skill_self_learning "
                                    "--context '{\"project\":\"system\"}'"
                                )
                        except Exception:
                            pass

            elif wf_name == "skill_self_learning":
                # Dequeue was already handled when select_candidate node completed.
                # Write eval outcome to eval_history so the candidate is not
                # indefinitely re-enqueued on future post_task scans.
                _pm = _load_promo_module()
                if _pm is not None and hasattr(_pm, 'record_eval_result'):
                    try:
                        _lid = (
                            inst.get('nodes', {})
                            .get('select_candidate', {})
                            .get('outputs', {}) or {}
                        ).get('learning_id')
                        _prop_out = (
                            inst.get('nodes', {})
                            .get('propose_promotion', {})
                            .get('outputs', {}) or {}
                        )
                        if _lid:
                            if _prop_out.get('proposed') is True:
                                _pm.record_eval_result(
                                    ROOT, _lid, 'proposed',
                                    proposal_path=_prop_out.get('proposal_path', ''),
                                )
                            elif _prop_out.get('proposed') is False:
                                _reason = _prop_out.get('reason', 'unknown')
                                _kwargs = {}
                                if 'pass_rate' in _prop_out:
                                    _kwargs['pass_rate'] = _prop_out['pass_rate']
                                _pm.record_eval_result(ROOT, _lid, _reason, **_kwargs)
                    except Exception:
                        pass

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
            if st == "READY" and node.get("delegate_to"):
                line += f" | delegate: {node['delegate_to']}"
            lines.append(line)

        lines.append("")

    if state["counters"]:
        lines.append("Counters:")
        for k, v in state["counters"].items():
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def show(instance_id: str) -> str:
    """Alias for status(instance_id), but errors if instance is missing."""
    state = _load_state()
    if instance_id not in state["active"]:
        return f"[ERROR] Active workflow instance not found: {instance_id}"
    return status(instance_id)


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


def _next_node_hints(defn_nodes: list, nodes_state: dict, instance_id: str = None, project: str = "...") -> str:
    """Return instruction text for all READY nodes that have an 'instruction' field."""
    lines = []
    for node in defn_nodes:
        nid = node["id"]
        if nodes_state.get(nid, {}).get("status") == "ready":
            instr = node.get("instruction", "").strip()
            delegate_to = node.get("delegate_to")
            delegate_hint = node.get("delegate_hint", "").strip()
            prefix = f"\n  [TODO: {nid}]"
            if delegate_to:
                prefix += f" [delegate_to={delegate_to}]"
            lines.append(prefix + "\n")
            if delegate_hint:
                lines.append(f"  Delegate hint: {delegate_hint}\n")
            if instr:
                lines.append(f"  {instr}\n")
            if instance_id:
                lines.append(f"  Next: {_next_step_command(node, instance_id, project=project)}\n")
    return "".join(lines)


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
                    "  bash shared/tools/conda-python.sh shared/workflows/coordinator.py start post_task "
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
              "  bash shared/tools/conda-python.sh shared/workflows/coordinator.py force_close "
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
                f"Run: {_launcher_prefix()} complete {m['node']} --instance {m['instance']}"
            )
        result = {"additionalContext": " | ".join(hints)}
        print(json.dumps(result))

    sys.exit(0)


def force_close(user_approved: bool = False, reason: str = '', instance_id: str = None):
    """Force-close one or all active workflows without completing nodes."""
    if not user_approved:
        return (
            "[DENY] force_close requires explicit user approval. "
            "Re-run with --approved-by-user --reason \"workflow_design_gap|validator_false_fail|exceptional_business_case\""
        )
    if not reason.strip():
        return "[DENY] force_close requires a non-empty --reason for audit logging."

    state = _load_state()
    if instance_id:
        if instance_id not in state["active"]:
            return f"[FORCE] No active workflow matches instance: {instance_id}"
        closed = [instance_id]
    else:
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
        print(_usage_text())
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd in ('help', '--help', '-h'):
        topic = sys.argv[2] if len(sys.argv) > 2 else None
        if topic == 'complete':
            print(
                "Usage: coordinator.py complete <node_id> [--instance <id>|--session <id>] "
                "[--outputs '{...}'|--artifacts '{...}'] [--script <path>]"
            )
        elif topic == 'start':
            print("Usage: coordinator.py start <workflow_name> [--context '{...}'] [--script <path>]")
        elif topic in ('status', 'list'):
            print("Usage: coordinator.py status [instance_id]")
        elif topic == 'show':
            print("Usage: coordinator.py show <instance_id>")
        elif topic == 'force_close':
            print("Usage: coordinator.py force_close [--instance <id>] --approved-by-user --reason \"...\"")
        else:
            print(_usage_text())
        sys.exit(0)

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
            print(
                "Usage: coordinator.py complete <node_id> [--instance <id>|--session <id>] "
                "[--outputs '{...}'|--artifacts '{...}'] [--sidecar <path>] [--script <path>]"
            )
            sys.exit(1)
        node_id = sys.argv[2]
        outputs = {}
        inst_id = None
        script_path = None
        sidecar_path = None
        if '--outputs' in sys.argv:
            idx = sys.argv.index('--outputs')
            if idx + 1 < len(sys.argv):
                try:
                    outputs = json.loads(sys.argv[idx + 1])
                except json.JSONDecodeError:
                    print("[ERROR] Invalid JSON in --outputs")
                    sys.exit(1)
        if '--artifacts' in sys.argv:
            idx = sys.argv.index('--artifacts')
            if idx + 1 < len(sys.argv):
                try:
                    artifact_outputs = json.loads(sys.argv[idx + 1])
                except json.JSONDecodeError:
                    print("[ERROR] Invalid JSON in --artifacts")
                    sys.exit(1)
                if isinstance(artifact_outputs, dict):
                    outputs.update(artifact_outputs)
        if '--sidecar' in sys.argv:
            idx = sys.argv.index('--sidecar')
            if idx + 1 < len(sys.argv):
                sidecar_path = sys.argv[idx + 1]
                loaded, err = _load_sidecar_outputs(sidecar_path)
                if err:
                    print(err)
                    sys.exit(1)
                # Merge: explicit --outputs / --artifacts win over sidecar
                merged = dict(loaded["_outputs"])
                merged.update(outputs)
                outputs = merged
                # Always inject the sidecar path so validators can find it
                outputs["_sidecar_path"] = loaded["_path"]
        if '--instance' in sys.argv:
            idx = sys.argv.index('--instance')
            if idx + 1 < len(sys.argv):
                inst_id = sys.argv[idx + 1]
        elif '--session' in sys.argv:
            idx = sys.argv.index('--session')
            if idx + 1 < len(sys.argv):
                inst_id = sys.argv[idx + 1]
        if '--script' in sys.argv:
            idx = sys.argv.index('--script')
            if idx + 1 < len(sys.argv):
                script_path = sys.argv[idx + 1]
        ok, msg = complete(node_id, outputs, inst_id, script=script_path)
        print(msg)
        sys.exit(0 if ok else 1)

    elif cmd == 'list':
        print(status())

    elif cmd == 'status':
        inst_id = sys.argv[2] if len(sys.argv) > 2 else None
        print(status(inst_id))

    elif cmd == 'show':
        if len(sys.argv) < 3:
            print("Usage: coordinator.py show <instance_id>")
            sys.exit(1)
        result = show(sys.argv[2])
        print(result)
        sys.exit(0 if not result.startswith("[ERROR]") else 1)

    elif cmd == 'check_pending':
        print(check_pending())

    elif cmd == 'hook_stop':
        _handle_stop_hook()

    elif cmd == 'hook_post':
        _handle_post_tool()

    elif cmd == 'force_close':
        approved = '--approved-by-user' in sys.argv
        reason = ''
        inst_id = None
        if '--reason' in sys.argv:
            idx = sys.argv.index('--reason')
            if idx + 1 < len(sys.argv):
                reason = sys.argv[idx + 1]
        if '--instance' in sys.argv:
            idx = sys.argv.index('--instance')
            if idx + 1 < len(sys.argv):
                inst_id = sys.argv[idx + 1]
        result = force_close(user_approved=approved, reason=reason, instance_id=inst_id)
        print(result)
        sys.exit(0 if result.startswith("[FORCE]") else 1)

    else:
        print(f"Unknown command: {cmd}")
        print(_usage_text())
        sys.exit(1)


if __name__ == '__main__':
    main()
