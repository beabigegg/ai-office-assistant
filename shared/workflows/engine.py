#!/usr/bin/env python3
"""
WorkflowEngine v1.0 — pytransitions-based workflow FSM core.

Wraps coordinator node execution with:
  - retry/timeout per node (from JSON definition)
  - workflow_errors.log for failure audit trail
  - is_terminal_state() for Stop hook decisions

Usage (internal — called by coordinator.py):
    engine = WorkflowEngine.from_instance(inst, global_state)
    ok, msg = engine.complete_node(node_id, outputs)
    done = engine.is_terminal_state()
"""
import json
import importlib.util
import threading
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    from transitions import Machine
    _TRANSITIONS_AVAILABLE = True
except ImportError:
    _TRANSITIONS_AVAILABLE = False

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR = ROOT / 'shared' / 'workflows'
VALIDATORS_DIR = WORKFLOWS_DIR / 'validators'
ERRORS_LOG = WORKFLOWS_DIR / 'state' / 'workflow_errors.log'
RUNTIME_LOG = WORKFLOWS_DIR / 'state' / 'workflow_runtime.jsonl'

# ─── Error Logging ──────────────────────────────────────────────────────────

def _log_error(workflow: str, node: str, attempt: int, error: str, instance_id: str):
    """Append a JSONL entry to workflow_errors.log."""
    ERRORS_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "workflow": workflow,
        "node": node,
        "attempt": attempt,
        "error": error,
        "instance_id": instance_id,
    }
    try:
        with ERRORS_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    except OSError:
        pass  # non-fatal — don't let logging break the workflow


def _log_runtime(event: str, **payload):
    """Append a workflow runtime event to workflow_runtime.jsonl."""
    RUNTIME_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **payload,
    }
    try:
        with RUNTIME_LOG.open('a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + '\n')
    except OSError:
        pass


# ─── Validator Loader ────────────────────────────────────────────────────────

def _ensure_validators_package() -> str:
    """Register VALIDATORS_DIR as a real package so validators can use
    relative imports (e.g. ``from ._sidecar import ...``).

    Returns the package name used (``ai_office_validators``)."""
    import sys
    pkg_name = 'ai_office_validators'
    if pkg_name in sys.modules:
        return pkg_name
    pkg_spec = importlib.util.spec_from_file_location(
        pkg_name,
        str(VALIDATORS_DIR / '__init__.py'),
        submodule_search_locations=[str(VALIDATORS_DIR)],
    )
    pkg = importlib.util.module_from_spec(pkg_spec)
    # Avoid trying to exec a non-existent __init__.py.
    sys.modules[pkg_name] = pkg
    return pkg_name


def _load_validator(name: str):
    path = VALIDATORS_DIR / f'{name}.py'
    if not path.exists():
        return None
    pkg_name = _ensure_validators_package()
    full_name = f'{pkg_name}.{name}'
    spec = importlib.util.spec_from_file_location(full_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    # Important for relative imports (`from ._sidecar import ...`).
    mod.__package__ = pkg_name
    import sys
    sys.modules[full_name] = mod
    spec.loader.exec_module(mod)
    return getattr(mod, 'validate', None)


def _run_validator(validator_name: str, context: dict) -> tuple:
    fn = _load_validator(validator_name)
    if fn is None:
        return False, f"validator '{validator_name}' not found"
    try:
        return fn(context)
    except Exception as e:
        return False, f"validator '{validator_name}' error: {e}"


def _iter_output_strings(value) -> Iterable[str]:
    """Yield string values from nested outputs for artifact proof matching."""
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _iter_output_strings(nested)
        return
    if isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _iter_output_strings(nested)


def _resolve_output_path(raw: str, root: Path, project: str) -> Path | None:
    """Resolve an output path against likely workspace roots."""
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    attempts = [root / candidate]
    if project:
        attempts.append(root / 'projects' / project / candidate)
        attempts.append(root / project / candidate)

    for attempt in attempts:
        if attempt.exists():
            return attempt
    return None


def _validate_required_artifacts(node_def: dict, outputs: dict, root: Path, project: str) -> tuple:
    """Check that outputs include explicit artifact paths for required_outputs."""
    required_outputs = node_def.get('required_outputs', [])
    if not required_outputs:
        return True, "no required artifacts"

    candidates = list(dict.fromkeys(_iter_output_strings(outputs)))

    missing = []
    for req in required_outputs:
        output_key = req.get('output_key')
        if output_key:
            value = outputs.get(output_key)
            if value not in (None, '', [], {}, ()):
                continue
            missing.append(req.get('description') or output_key)
            continue

        pattern = str(req.get('path_contains', '')).replace('\\', '/').lower()
        if not pattern:
            continue
        if not candidates:
            missing.append(req.get('description') or req.get('path_contains') or pattern)
            continue

        matched = False
        for raw in candidates:
            norm = raw.replace('\\', '/').lower()
            if pattern not in norm:
                continue
            resolved = _resolve_output_path(raw, root, project)
            if resolved is not None:
                matched = True
                break

        if not matched:
            missing.append(req.get('description') or req.get('path_contains') or pattern)

    if missing:
        return False, f"required artifacts not proven: {', '.join(missing)}"
    return True, f"artifact proof matched {len(required_outputs)} requirement(s)"


def _should_validate_required_outputs(node_def: dict, outputs: dict) -> bool:
    """Return True when required_outputs should be enforced for this completion."""
    required_outputs = node_def.get('required_outputs', [])
    if not required_outputs:
        return False

    cond_key = node_def.get('required_outputs_if')
    if cond_key and not outputs.get(cond_key):
        return False

    unless_key = node_def.get('required_outputs_unless')
    if unless_key and outputs.get(unless_key):
        return False

    return True


# ─── Timeout Helper ──────────────────────────────────────────────────────────

def _run_with_timeout(fn, args, timeout_sec: int):
    """Run fn(*args) with a timeout. Returns (result, timed_out)."""
    result = [None]
    exc = [None]

    def target():
        try:
            result[0] = fn(*args)
        except Exception as e:
            exc[0] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout=timeout_sec)
    if t.is_alive():
        return None, True  # timed out
    if exc[0]:
        raise exc[0]
    return result[0], False


# ─── WorkflowEngine ──────────────────────────────────────────────────────────

class WorkflowEngine:
    """
    Workflow execution engine with retry/timeout/error-log support.

    States (pytransitions):
        running → done     (all required nodes complete)
        running → failed   (unrecoverable error / force_close)
    """

    _WF_STATES = ['running', 'done', 'failed']

    def __init__(self, definition: dict, instance_id: str,
                 instance_state: dict, global_state: dict):
        self.definition = definition
        self.instance_id = instance_id
        self.instance_state = instance_state  # live reference into global_state
        self.global_state = global_state

        # pytransitions Machine (workflow-level phase, not node-level)
        if _TRANSITIONS_AVAILABLE:
            self.machine = Machine(
                model=self,
                states=self._WF_STATES,
                model_attribute='wf_phase',
                initial='running',
                transitions=[
                    {'trigger': 'finish',        'source': 'running', 'dest': 'done'},
                    {'trigger': 'fail_workflow',  'source': 'running', 'dest': 'failed'},
                ],
                after_state_change='_on_phase_change',
                ignore_invalid_triggers=True,
            )
        else:
            self.wf_phase = 'running'

    # ── Factory methods ─────────────────────────────────────────────────

    @classmethod
    def from_instance(cls, instance: dict, global_state: dict) -> 'WorkflowEngine':
        return cls(
            definition=instance['definition'],
            instance_id=instance['id'],
            instance_state=instance,
            global_state=global_state,
        )

    @classmethod
    def find_by_node(cls, global_state: dict, node_id: str):
        """Return engine for first active workflow containing node_id, or None."""
        for iid, inst in global_state.get('active', {}).items():
            if node_id in inst.get('nodes', {}):
                return cls.from_instance(inst, global_state)
        return None

    # ── Core operations ─────────────────────────────────────────────────

    def complete_node(self, node_id: str, outputs: dict) -> tuple:
        """
        Complete node_id with retry/timeout support.
        Returns (success: bool, message: str).
        """
        inst = self.instance_state
        defn = self.definition

        if node_id not in inst['nodes']:
            return False, f"[ERROR] Node '{node_id}' not in {self.instance_id}"

        node_state = inst['nodes'][node_id]
        if node_state['status'] == 'completed':
            return True, f"[SKIP] Node '{node_id}' already completed"

        # Dependency check
        node_def = next((n for n in defn['nodes'] if n['id'] == node_id), None)
        if node_def is None:
            return False, f"[ERROR] Node definition for '{node_id}' not found"

        for dep in node_def.get('depends_on', []):
            if inst['nodes'].get(dep, {}).get('status') != 'completed':
                return False, f"[BLOCKED] '{node_id}' requires '{dep}' to complete first"

        # Retry configuration (from JSON or defaults)
        retry_cfg = node_def.get('retry', {})
        max_attempts = max(1, retry_cfg.get('max', 1))
        backoff_mode = retry_cfg.get('backoff', 'none')  # none | linear | exponential
        timeout_sec = node_def.get('timeout', None)

        validator_spec = node_def.get('validator')
        validators = []
        if validator_spec:
            validators = validator_spec if isinstance(validator_spec, list) else [validator_spec]

        ctx = {
            'node_id': node_id,
            'outputs': outputs,
            'instance': inst,
            'params': node_def.get('validator_params', {}),
            'root': str(ROOT),
            'project': inst['context'].get('project', ''),
        }

        # Retry loop
        last_fail_msg = ''
        for attempt in range(1, max_attempts + 1):
            all_results = []
            overall_passed = True
            fail_msg = ''
            _log_runtime(
                'node_attempt_started',
                workflow=inst['workflow'],
                instance_id=self.instance_id,
                node=node_id,
                attempt=attempt,
                outputs=outputs,
            )

            if _should_validate_required_outputs(node_def, outputs):
                passed, vmsg = _validate_required_artifacts(
                    node_def=node_def,
                    outputs=outputs,
                    root=Path(ctx['root']),
                    project=ctx['project'],
                )
                all_results.append({
                    'validator': '__required_artifacts__',
                    'passed': passed,
                    'message': vmsg,
                })
                _log_runtime(
                    'validator_result',
                    workflow=inst['workflow'],
                    instance_id=self.instance_id,
                    node=node_id,
                    attempt=attempt,
                    validator='__required_artifacts__',
                    passed=passed,
                    message=vmsg,
                )
                if not passed:
                    overall_passed = False
                    fail_msg = vmsg

            for vname in validators if overall_passed else []:
                if timeout_sec:
                    try:
                        result, timed_out = _run_with_timeout(
                            _run_validator, (vname, ctx), timeout_sec
                        )
                        if timed_out:
                            passed, vmsg = False, f"timeout after {timeout_sec}s"
                        else:
                            passed, vmsg = result
                    except Exception as e:
                        passed, vmsg = False, str(e)
                else:
                    passed, vmsg = _run_validator(vname, ctx)

                all_results.append({'validator': vname, 'passed': passed, 'message': vmsg})
                _log_runtime(
                    'validator_result',
                    workflow=inst['workflow'],
                    instance_id=self.instance_id,
                    node=node_id,
                    attempt=attempt,
                    validator=vname,
                    passed=passed,
                    message=vmsg,
                )

                if not passed:
                    overall_passed = False
                    fail_msg = vmsg
                    break

            if overall_passed:
                # Success — mark completed
                validator_result = {'passed': True, 'results': all_results}
                node_state['status'] = 'completed'
                node_state['completed_at'] = datetime.now(timezone.utc).isoformat()
                node_state['outputs'] = outputs
                node_state['validator_result'] = validator_result
                self._unlock_downstream(node_id)
                _log_runtime(
                    'node_completed',
                    workflow=inst['workflow'],
                    instance_id=self.instance_id,
                    node=node_id,
                    attempt=attempt,
                    outputs=outputs,
                    validator_result=validator_result,
                )

                msg = f"[DONE] Node '{node_id}' completed"
                if attempt > 1:
                    msg += f" (after {attempt} attempts)"
                return True, msg

            else:
                # Failed on this attempt
                _log_error(
                    workflow=self.instance_state['workflow'],
                    node=node_id,
                    attempt=attempt,
                    error=fail_msg,
                    instance_id=self.instance_id,
                )
                _log_runtime(
                    'node_attempt_failed',
                    workflow=inst['workflow'],
                    instance_id=self.instance_id,
                    node=node_id,
                    attempt=attempt,
                    error=fail_msg,
                    validator_result={'passed': False, 'results': all_results},
                )
                last_fail_msg = fail_msg
                node_state['validator_result'] = {'passed': False, 'results': all_results}

                if attempt < max_attempts:
                    # Backoff before retry
                    delay = _calc_backoff(attempt, backoff_mode)
                    if delay > 0:
                        time.sleep(delay)
                    print(f"[RETRY] Node '{node_id}' attempt {attempt} failed: {fail_msg}. Retrying...")

        # All attempts exhausted
        node_state['status'] = 'failed'
        _log_runtime(
            'node_failed',
            workflow=inst['workflow'],
            instance_id=self.instance_id,
            node=node_id,
            error=last_fail_msg,
            outputs=outputs,
        )
        return False, f"[FAIL] Validator: {last_fail_msg}"

    def is_terminal_state(self) -> bool:
        """Return True when all required nodes are completed."""
        nodes = self.instance_state.get('nodes', {})
        return all(
            nodes.get(n['id'], {}).get('status') == 'completed'
            for n in self.definition['nodes']
            if n.get('required', True)
        )

    def archive_if_done(self) -> bool:
        """Check terminal state; if done, mark completed_at and return True."""
        if self.is_terminal_state():
            self.instance_state['completed_at'] = datetime.now(timezone.utc).isoformat()
            return True
        return False

    # ── Private helpers ──────────────────────────────────────────────────

    def _unlock_downstream(self, completed_node_id: str):
        """Unblock nodes whose dependencies are now all met."""
        inst = self.instance_state
        defn = self.definition
        for n in defn['nodes']:
            nid = n['id']
            if nid == completed_node_id:
                continue
            ndeps = n.get('depends_on', [])
            if (completed_node_id in ndeps
                    and inst['nodes'].get(nid, {}).get('status') == 'blocked'):
                all_met = all(
                    inst['nodes'].get(d, {}).get('status') == 'completed'
                    for d in ndeps
                )
                if all_met:
                    inst['nodes'][nid]['status'] = 'ready'

    def _on_phase_change(self):
        """pytransitions after_state_change callback — placeholder for persistence."""
        pass


# ─── Utility ────────────────────────────────────────────────────────────────

def _calc_backoff(attempt: int, mode: str) -> float:
    """Calculate retry delay in seconds."""
    if mode == 'linear':
        return float(attempt)
    if mode == 'exponential':
        return float(2 ** (attempt - 1))
    return 0.0
