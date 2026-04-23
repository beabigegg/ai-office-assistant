#!/usr/bin/env python3
"""Project reference helpers for workflow context normalization."""

from __future__ import annotations

from pathlib import Path


def normalize_project_id(project: str | None) -> str:
    """Return canonical project id without a leading `projects/` segment."""
    value = (project or "").strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    if value.startswith("/"):
        value = value[1:]
    if value.startswith("projects/"):
        value = value[len("projects/") :]
    return value.strip("/")


def project_exists(root: Path, project: str | None, allow_shared: bool = True) -> bool:
    """Return True when project id resolves to a valid project directory."""
    project_id = normalize_project_id(project)
    if not project_id:
        return False
    if allow_shared and project_id == "shared":
        return True
    return project_root(root, project_id).is_dir()


def list_project_ids(root: Path) -> list[str]:
    """Return sorted project directory names under `<root>/projects`."""
    projects_dir = root / "projects"
    if not projects_dir.exists():
        return []
    return sorted(p.name for p in projects_dir.iterdir() if p.is_dir())


def project_root(root: Path, project: str | None) -> Path:
    """Return `<root>/projects/<project_id>`."""
    return root / "projects" / normalize_project_id(project)


def project_workspace(root: Path, project: str | None) -> Path:
    """Return `<root>/projects/<project_id>/workspace`."""
    return project_root(root, project) / "workspace"


def project_db_dir(root: Path, project: str | None) -> Path:
    """Return `<root>/projects/<project_id>/workspace/db`."""
    return project_workspace(root, project) / "db"
