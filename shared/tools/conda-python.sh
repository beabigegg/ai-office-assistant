#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${AI_OFFICE_CONDA_ENV:-ai-office}"

find_python() {
  if [[ -n "${CONDA_PREFIX:-}" && "$(basename "$CONDA_PREFIX")" == "$ENV_NAME" ]]; then
    if [[ -x "$CONDA_PREFIX/python.exe" ]]; then
      printf '%s\n' "$CONDA_PREFIX/python.exe"
      return 0
    fi
    if [[ -x "$CONDA_PREFIX/bin/python" ]]; then
      printf '%s\n' "$CONDA_PREFIX/bin/python"
      return 0
    fi
  fi

  if command -v conda >/dev/null 2>&1; then
    local conda_base
    conda_base="$(conda info --base 2>/dev/null || true)"
    if [[ -n "$conda_base" ]]; then
      if [[ -x "$conda_base/envs/$ENV_NAME/python.exe" ]]; then
        printf '%s\n' "$conda_base/envs/$ENV_NAME/python.exe"
        return 0
      fi
      if [[ -x "$conda_base/envs/$ENV_NAME/bin/python" ]]; then
        printf '%s\n' "$conda_base/envs/$ENV_NAME/bin/python"
        return 0
      fi
    fi
  fi

  if [[ -n "${USERPROFILE:-}" && -x "$USERPROFILE/.conda/envs/$ENV_NAME/python.exe" ]]; then
    printf '%s\n' "$USERPROFILE/.conda/envs/$ENV_NAME/python.exe"
    return 0
  fi

  return 1
}

PYTHON_BIN="$(find_python)" || {
  printf 'ERROR: cannot locate conda env "%s" python interpreter.\n' "$ENV_NAME" >&2
  printf 'Hint: activate the env or ensure `conda info --base` works in Git Bash.\n' >&2
  exit 1
}

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

exec "$PYTHON_BIN" "$@"
