#!/usr/bin/env python3
"""Shared routing table loading and normalization for omo workflow hooks."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

HOOKS_DIR = Path(__file__).resolve().parent
DEFAULT_ROUTING_TABLE_PATH = HOOKS_DIR / "routing_table.json"
USER_ROUTING_TABLE_PATH = Path.home() / ".codeagent" / "omo" / "routing_table.json"
ENV_ROUTING_TABLE_PATH = "OMO_ROUTING_TABLE_PATH"


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _candidate_override_paths() -> list[Path]:
    paths: list[Path] = []

    paths.append(USER_ROUTING_TABLE_PATH)

    configured = os.environ.get(ENV_ROUTING_TABLE_PATH, "").strip()
    if configured:
        paths.append(Path(configured).expanduser())

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def _normalize_aliases(data: dict[str, Any]) -> dict[str, str]:
    aliases: dict[str, str] = {}

    for key in ("agent_aliases", "guard_map"):
        raw = data.get(key, {})
        if not isinstance(raw, dict):
            continue
        for alias, agent in raw.items():
            if isinstance(alias, str) and isinstance(agent, str):
                aliases[alias] = agent

    return aliases


def _normalize_categories(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_categories = data.get("categories", {})
    if not isinstance(raw_categories, dict):
        return {}

    categories: dict[str, dict[str, Any]] = {}
    for name, raw_cfg in raw_categories.items():
        if not isinstance(name, str) or not isinstance(raw_cfg, dict):
            continue

        raw_route = raw_cfg.get("route", {})
        if isinstance(raw_route, str):
            route = {"agent": raw_route}
        elif isinstance(raw_route, dict):
            route = dict(raw_route)
        else:
            route = {}

        agent = route.get("agent", raw_cfg.get("agent", ""))
        backend = route.get("backend", raw_cfg.get("backend", ""))
        model = route.get("model", raw_cfg.get("model", ""))
        description = raw_cfg.get("description", "")
        default_skills = raw_cfg.get("default_skills", raw_cfg.get("skills", []))

        if not isinstance(default_skills, list):
            default_skills = []

        categories[name] = {
            "description": description if isinstance(description, str) else "",
            "default_skills": [skill for skill in default_skills if isinstance(skill, str)],
            "route": {
                "agent": agent if isinstance(agent, str) else "",
                "backend": backend if isinstance(backend, str) else "",
                "model": model if isinstance(model, str) else "",
            },
        }

    return categories


def load_routing_table() -> dict[str, Any]:
    """Load routing config from plugin defaults plus external overrides."""
    sources: list[str] = []

    merged = _load_json_file(DEFAULT_ROUTING_TABLE_PATH)
    if merged:
        sources.append(str(DEFAULT_ROUTING_TABLE_PATH))

    for path in _candidate_override_paths():
        if not path.exists():
            continue
        override = _load_json_file(path)
        if not override:
            continue
        merged = _deep_merge(merged, override)
        sources.append(str(path))

    return {
        "version": merged.get("version", 2),
        "agent_aliases": _normalize_aliases(merged),
        "categories": _normalize_categories(merged),
        "_meta": {
            "sources": sources,
            "default_path": str(DEFAULT_ROUTING_TABLE_PATH),
            "user_path": str(USER_ROUTING_TABLE_PATH),
        },
    }


def resolve_agent_alias(table: dict[str, Any], name: str) -> str:
    aliases = table.get("agent_aliases", {})
    if not isinstance(aliases, dict):
        return name
    resolved = aliases.get(name, name)
    return resolved if isinstance(resolved, str) else name
