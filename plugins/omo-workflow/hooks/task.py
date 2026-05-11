#!/usr/bin/env python3
"""task.py — Translate task() abstraction to codeagent-wrapper invocation.

Usage:
    # Category-based delegation (auto-selects agent + model):
    task.py --category deep --skills frontend-ui-ux <<'EOF'
    Implement feature X...
    EOF

    # Direct agent routing (specialists):
    task.py --agent oracle <<'EOF'
    Consult on architecture...
    EOF

    # Resume a previous session:
    task.py --agent oracle --session abc123 <<'EOF'
    Follow-up instruction...
    EOF

    # List available categories and agents:
    task.py --list

Reads prompt from stdin, injects skill instructions, resolves category/agent
from the routing table (plugin defaults plus optional external override at
~/.codeagent/omo/routing_table.json), and delegates via codeagent-wrapper
with real-time stdout/stderr passthrough. Session ID is extracted from
structured output and printed to stderr for session continuity.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from routing_config import load_routing_table, resolve_agent_alias

HOOKS_DIR = Path(__file__).resolve().parent
SKILLS_DIR = HOOKS_DIR / "skills"
MODELS_JSON_PATH = Path.home() / ".codeagent" / "models.json"


def load_models_json() -> dict[str, Any]:
    """Load models.json from ~/.codeagent/models.json."""
    try:
        return json.loads(MODELS_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error loading models.json: {e}", file=sys.stderr)
        sys.exit(1)


def resolve_category(table: dict[str, Any], category: str) -> tuple[str, str, str, list[str]]:
    """Resolve category name to (agent, backend, model, default_skills)."""
    categories = table.get("categories", {})
    cat = categories.get(category)
    if cat is None:
        available = ", ".join(sorted(categories.keys()))
        print(
            f"Unknown category: {category}\nAvailable: {available}",
            file=sys.stderr,
        )
        sys.exit(1)
    route = cat.get("route", {})
    if not isinstance(route, dict):
        route = {}

    agent = route.get("agent", "")
    if not isinstance(agent, str) or not agent.strip():
        print(
            f"Invalid category config: '{category}' is missing categories.{category}.route.agent",
            file=sys.stderr,
        )
        sys.exit(1)
    backend = route.get("backend", "")
    model = route.get("model", "")
    default_skills = cat.get("default_skills", [])
    if not isinstance(default_skills, list):
        default_skills = []
    return agent.strip(), backend, model, [skill for skill in default_skills if isinstance(skill, str)]


def merge_skill_names(*skill_groups: list[str]) -> list[str]:
    """Merge skill names with stable ordering and deduplication."""
    merged: list[str] = []
    seen: set[str] = set()
    for group in skill_groups:
        for skill in group:
            if skill in seen:
                continue
            seen.add(skill)
            merged.append(skill)
    return merged


def validate_agent(agent: str, models: dict[str, Any], source: str) -> None:
    """Ensure the resolved agent exists in ~/.codeagent/models.json."""
    agents = models.get("agents", {})
    if not isinstance(agents, dict):
        return
    if agent in agents:
        return
    available = ", ".join(sorted(agents.keys()))
    print(
        f"Configured agent '{agent}' from {source} is not defined in {MODELS_JSON_PATH}.\n"
        f"Available agents: {available}",
        file=sys.stderr,
    )
    sys.exit(1)


def build_skills_injection(skill_names: list[str]) -> str:
    """Build [SKILL: ...] sections from hooks/skills/<name>.md files."""
    sections = []
    for name in skill_names:
        skill_file = SKILLS_DIR / f"{name}.md"
        if skill_file.exists():
            content = skill_file.read_text(encoding="utf-8").strip()
        else:
            content = f"Apply {name} domain expertise and best practices."
        sections.append(f"[SKILL: {name}]\n{content}")
    return "\n\n".join(sections)


def build_command(agent: str, backend: str, model: str, workdir: str, session_id: str = "", output_file: str = "") -> list[str]:
    """Build the codeagent-wrapper command line."""
    cmd = ["codeagent-wrapper"]
    if session_id:
        cmd += ["resume", session_id]
    else:
        cmd += ["--agent", agent]
        if backend:
            cmd += ["--backend", backend]
        if model:
            cmd += ["--model", model]
    if output_file:
        cmd += ["--output", output_file]
    cmd += ["-", workdir]
    return cmd


def _report_session_id(output_file: str) -> None:
    """Extract session_id from structured output and print to stderr."""
    if not output_file:
        return
    try:
        data = json.loads(Path(output_file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    results = data.get("results", [])
    if results:
        sid = results[0].get("session_id", "")
        if sid:
            print(f"\n[SESSION_ID] {sid}", file=sys.stderr)


def _cleanup_output(output_file: str) -> None:
    """Remove the temp output file."""
    if not output_file:
        return
    try:
        Path(output_file).unlink()
    except OSError:
        pass


def run_list(table: dict) -> None:
    """Print available categories and agents, then exit."""
    categories = table.get("categories", {})
    meta = table.get("_meta", {})
    sources = meta.get("sources", []) if isinstance(meta, dict) else []
    user_path = meta.get("user_path", "") if isinstance(meta, dict) else ""

    if sources:
        print("Routing config sources:")
        for path in sources:
            print(f"  {path}")
        print()
    elif user_path:
        print(f"Routing config override path: {user_path} (not found)")
        print()

    if categories:
        print("Categories (use with --category):")
        for name, cfg in categories.items():
            route = cfg.get("route", {})
            if not isinstance(route, dict):
                route = {}
            agent = route.get("agent", "")
            if not isinstance(agent, str) or not agent.strip():
                agent = "<missing route.agent>"
            backend = route.get("backend", "")
            model = route.get("model", "")
            skills = cfg.get("default_skills", [])
            skills_str = f"  default_skills: {', '.join(skills)}" if skills else ""
            backend_model = f"{backend}/{model}" if backend or model else "models.json default"
            backend_str = f" ({backend_model})" if backend_model else ""
            print(f"  {name:25s} → {agent}{backend_str}{skills_str}")
        print()

    # Agent list from models.json
    try:
        models = load_models_json()
        agents = models.get("agents", {})
        if agents:
            print("Agents (use with --agent):")
            for agent_name in sorted(agents.keys()):
                print(f"  {agent_name}")
    except SystemExit:
        print("Agents: (models.json not available)", file=sys.stderr)

    sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate task() abstraction to codeagent-wrapper invocation",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--category", "-c",
        help="Category name (e.g. deep, quick, visual-engineering)",
    )
    group.add_argument(
        "--agent", "-a",
        help="Direct agent name (e.g. oracle, code-scout, explore)",
    )
    group.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available categories and agents",
    )
    parser.add_argument(
        "--skills", "-s",
        default="",
        help="Comma-separated skill names (e.g. frontend-ui-ux,playwright)",
    )
    parser.add_argument(
        "--session", "-S",
        default="",
        help="Session ID to resume (enables codeagent-wrapper resume mode)",
    )
    parser.add_argument(
        "--workdir", "-w",
        default=".",
        help="Working directory (default: current)",
    )
    args = parser.parse_args()

    table = load_routing_table()

    # --list mode
    if args.list:
        run_list(table)

    # Resolve agent and backend
    models = load_models_json()
    if args.category:
        agent, backend, model, category_skills = resolve_category(table, args.category)
        validate_agent(agent, models, f"category '{args.category}'")
    else:
        agent = resolve_agent_alias(table, args.agent)
        backend = ""
        model = ""
        category_skills = []

    # Parse skills
    cli_skills = [s.strip() for s in args.skills.split(",") if s.strip()]
    skill_names = merge_skill_names(category_skills, cli_skills)

    # Read prompt from stdin (heredoc)
    prompt = sys.stdin.read()
    if not prompt.strip():
        print("Error: empty prompt (pass content via stdin heredoc)", file=sys.stderr)
        sys.exit(1)

    # Inject skills before the task prompt
    skill_injection = build_skills_injection(skill_names)
    if skill_injection:
        full_prompt = f"{skill_injection}\n\n[TASK]\n{prompt}"
    else:
        full_prompt = prompt

    # Create temp file for structured output (captures session_id)
    output_file = ""
    fd, output_file = tempfile.mkstemp(suffix=".json", prefix="task_out_")
    os.close(fd)

    # Build codeagent-wrapper command
    cmd = build_command(agent, backend, model, args.workdir, session_id=args.session, output_file=output_file)

    # Execute with real-time passthrough
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    except FileNotFoundError:
        print(
            "Error: codeagent-wrapper not found in PATH.\n"
            "Install oh-my-opencode or ensure codeagent-wrapper is on PATH.",
            file=sys.stderr,
        )
        _cleanup_output(output_file)
        sys.exit(127)

    # Write prompt to codeagent-wrapper's stdin
    try:
        proc.stdin.write(full_prompt.encode("utf-8"))
        proc.stdin.close()
    except BrokenPipeError:
        pass

    # Forward signals to child process
    def _forward(signum: int, _frame: Any) -> None:
        proc.send_signal(signum)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _forward)

    # Wait for completion
    exit_code = proc.wait()

    # Extract and report session_id from structured output
    _report_session_id(output_file)
    _cleanup_output(output_file)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
