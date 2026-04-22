"""PreToolUse hook: Bash command guard.

Reads tool_input from stdin (JSON), checks for forbidden patterns.
Exit codes:
  0 = allow
  2 = block (stderr message fed back to AI)

Note: Only checks the first line / actual command, not heredoc content
or string literals inside the command (e.g., commit messages).
"""
import json
import re
import sys


FORBIDDEN_PATTERNS = [
    # CLAUDE.md §1.4 explicit bans — match command invocations, not string mentions
    (r'(?:^|\||\&\&|\;)\s*powershell\b', 'powershell is forbidden. Use Git Bash or Python.'),
    (r'(?:^|\||\&\&|\;)\s*cmd\s*/c\b', 'cmd /c is forbidden. Use Git Bash or Python.'),
    (r'(?:^|\||\&\&|\;)\s*chmod\b', 'chmod is forbidden on Windows.'),
    (r'(?:^|\||\&\&|\;)\s*iconv\b', 'iconv is forbidden. Use Python chardet + codecs.'),
    # System Python ban (CLAUDE.md §1.2) — path-based, unlikely in string literals
    (
        r'C:\\Users\\.*\\AppData\\Local\\Programs\\Python',
        'System Python is forbidden. Use conda env: '
        r'"C:\Users\lin46\.conda\envs\ai-office\python.exe"',
    ),
    (
        r'C:\\Python3',
        'System Python is forbidden. Use conda env.',
    ),
    # Destructive operations
    (r'\brm\s+-rf\s+/', 'rm -rf / is blocked.'),
    (r'(?:^|\||\&\&|\;)\s*git\s+push\s+--force\b', 'git push --force requires user confirmation.'),
    (r'(?:^|\||\&\&|\;)\s*git\s+reset\s+--hard\b', 'git reset --hard requires user confirmation.'),
]

COMPILED = [(re.compile(pat, re.IGNORECASE), msg) for pat, msg in FORBIDDEN_PATTERNS]


def _extract_command_portion(command: str) -> str:
    """Extract the actual command portion, stripping heredoc content.

    Heredocs (<<'EOF' ... EOF) contain user-authored text that should not
    be checked for forbidden patterns.
    """
    # Strip heredoc blocks: everything between <<'EOF' (or <<EOF) and the closing delimiter
    # This prevents false positives from commit messages, echo strings, etc.
    cleaned = re.sub(
        r"<<-?\s*'?(\w+)'?.*?\n\1",
        '',
        command,
        flags=re.DOTALL,
    )
    return cleaned


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)  # can't parse → allow

    command = ''
    tool_input = data.get('tool_input', {})
    if isinstance(tool_input, dict):
        command = tool_input.get('command', '')
    elif isinstance(tool_input, str):
        command = tool_input

    if not command:
        sys.exit(0)

    # Only check the command portion, not heredoc/string content
    check_text = _extract_command_portion(command)

    for pattern, message in COMPILED:
        if pattern.search(check_text):
            print(f'BLOCKED: {message}', file=sys.stderr)
            sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
