#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${AI_OFFICE_CONDA_ENV:-ai-office}"

to_bash_path() {
  local raw="${1:-}"
  if [[ -z "$raw" ]]; then
    return 1
  fi

  if [[ "$raw" =~ ^[A-Za-z]:[\\/].* ]]; then
    local drive="${raw:0:1}"
    local rest="${raw:2}"
    rest="${rest//\\//}"

    if [[ -d "/mnt/${drive,,}" ]]; then
      printf '/mnt/%s%s\n' "${drive,,}" "$rest"
      return 0
    fi

    if command -v cygpath >/dev/null 2>&1; then
      cygpath -u "$raw"
      return 0
    fi

    printf '/%s%s\n' "${drive,,}" "$rest"
    return 0
  fi

  printf '%s\n' "${raw//\\//}"
}

emit_if_python_exists() {
  local raw="${1:-}"
  local candidate=""
  if [[ -z "$raw" ]]; then
    return 1
  fi

  for candidate in "$raw" "$(to_bash_path "$raw" 2>/dev/null || true)"; do
    if [[ -n "$candidate" && -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

find_from_conda_base() {
  local conda_base="${1:-}"
  if [[ -z "$conda_base" ]]; then
    return 1
  fi

  emit_if_python_exists "$conda_base/envs/$ENV_NAME/python.exe" && return 0
  emit_if_python_exists "$conda_base/envs/$ENV_NAME/bin/python" && return 0
  return 1
}

find_from_glob() {
  local pattern="${1:-}"
  local match=""
  if [[ -z "$pattern" ]]; then
    return 1
  fi

  while IFS= read -r match; do
    emit_if_python_exists "$match" && return 0
  done < <(compgen -G "$pattern" || true)

  return 1
}

find_python() {
  if [[ -n "${CONDA_PREFIX:-}" && "$(basename "$CONDA_PREFIX")" == "$ENV_NAME" ]]; then
    emit_if_python_exists "$CONDA_PREFIX/python.exe" && return 0
    emit_if_python_exists "$CONDA_PREFIX/bin/python" && return 0
  fi

  if [[ -n "${CONDA_EXE:-}" ]]; then
    local conda_base
    conda_base="$("$CONDA_EXE" info --base 2>/dev/null || true)"
    find_from_conda_base "$conda_base" && return 0
  fi

  if command -v conda >/dev/null 2>&1; then
    local conda_base
    conda_base="$(conda info --base 2>/dev/null || true)"
    find_from_conda_base "$conda_base" && return 0
  fi

  if [[ -n "${USERPROFILE:-}" ]]; then
    emit_if_python_exists "$USERPROFILE/.conda/envs/$ENV_NAME/python.exe" && return 0
    emit_if_python_exists "$USERPROFILE/miniconda3/envs/$ENV_NAME/python.exe" && return 0
    emit_if_python_exists "$USERPROFILE/anaconda3/envs/$ENV_NAME/python.exe" && return 0
  fi

  if [[ -n "${HOME:-}" ]]; then
    emit_if_python_exists "$HOME/.conda/envs/$ENV_NAME/python.exe" && return 0
    emit_if_python_exists "$HOME/miniconda3/envs/$ENV_NAME/python.exe" && return 0
    emit_if_python_exists "$HOME/anaconda3/envs/$ENV_NAME/python.exe" && return 0
  fi

  find_from_glob "/mnt/c/Users/*/.conda/envs/$ENV_NAME/python.exe" && return 0
  find_from_glob "/mnt/c/Users/*/miniconda3/envs/$ENV_NAME/python.exe" && return 0
  find_from_glob "/mnt/c/Users/*/anaconda3/envs/$ENV_NAME/python.exe" && return 0

  return 1
}

PYTHON_BIN="$(find_python)" || {
  printf 'ERROR: cannot locate conda env "%s" python interpreter.\n' "$ENV_NAME" >&2
  printf 'Hint: set CONDA_EXE / CONDA_PREFIX, or ensure %s exists under .conda, miniconda3, or anaconda3.\n' "$ENV_NAME" >&2
  exit 1
}

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
export CONDA_PYTHON_EXE="$PYTHON_BIN"

exec "$PYTHON_BIN" "$@"
