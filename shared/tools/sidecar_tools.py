"""Canonical tool identifier constants for sidecar JSON.

Writers (tools) and readers (validators) MUST import these constants
instead of hardcoding tool-name strings. This ensures rename safety.
"""

TOOL_KB_GENERATE_SUMMARY = "kb.py:generate-summary"
TOOL_KB_PROJECT_STATE_INDEX = "kb.py:project-state-index"
TOOL_KB_GENERATE_SESSION_CONTEXT = "kb.py:generate-session-context"
TOOL_KB_VALIDATE = "kb.py:validate"
TOOL_KB_EXPORT_ALL = "kb.py:export-all"
TOOL_KB_ADD_DECISION = "kb.py:add-decision"
TOOL_KB_ADD_LEARNING = "kb.py:add-learning"
