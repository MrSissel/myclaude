#!/usr/bin/env python3
"""Unified single-file hook entrypoint for omo activation, state management, agent guard, and prompt injection.

Responsibilities:
- store, read, and expire omo activation markers locally in this file

Supported modes:
1. agent-guard: deny non-whitelisted Agent tool calls while omo is active
2. user-prompt-submit: inject routing context when active
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from routing_config import load_routing_table, resolve_agent_alias

HOOKS_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = HOOKS_DIR / "prompts"

# ---------------------------------------------------------------------------
# 配置常量
# ---------------------------------------------------------------------------

# 标记文件存活时间（秒），12 小时后视为过期
TTL_SECONDS = 12 * 60 * 60


# ---------------------------------------------------------------------------
# 状态管理
# ---------------------------------------------------------------------------


def _plugin_data_dir() -> Path:
    """获取插件的持久数据目录（CLAUDE_PLUGIN_DATA 环境变量）。

    回退顺序:
    1. $CLAUDE_PLUGIN_DATA（插件 hook 环境中由 Claude Code 注入）
    2. ~/.claude/plugins/data/omo（手动回退）
    """
    env = os.environ.get("CLAUDE_PLUGIN_DATA", "")
    if env:
        return Path(env)
    return Path.home() / ".claude" / "plugins" / "data" / "omo"


def _project_key(cwd: str) -> str:
    """将项目路径编码为安全的目录名。

    编码策略: 将路径中的 / 替换为 -，确保作为目录名合法且唯一。
    例如: /Users/zgray/Projects/foo -> -Users-zgray-Projects-foo
    """
    if not cwd:
        return "_unknown"
    return cwd.replace("/", "-")


def _state_dir(project_key: str, create: bool = False) -> Path:
    """获取指定项目的标记文件目录。

    Args:
        project_key: 编码后的项目路径
        create: 是否自动创建目录（激活时需要）
    """
    path = _plugin_data_dir() / project_key
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def _state_file_path(project_key: str, session_id: str, create_dir: bool = False) -> Path:
    """获取标记文件的完整路径（按 session 隔离）。"""
    return _state_dir(project_key, create=create_dir) / f"{session_id}.json"


def project_key_from_payload(payload: dict) -> str:
    """从 hook payload 中提取 project_key。

    优先使用 cwd 字段（hook 框架注入），回退到 CLAUDE_PROJECT_DIR 环境变量。
    """
    cwd = payload.get("cwd", "") or os.environ.get("CLAUDE_PROJECT_DIR", "")
    return _project_key(cwd)


def _read_marker(path: Path) -> dict | None:
    """读取标记文件，返回解析后的 dict 或 None（文件不存在/损坏时）。"""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_marker(path: Path, session_id: str) -> None:
    """写入激活标记文件。"""
    now = time.time()
    data = {
        "activated_at": now,
        "activated_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "session_id": session_id,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _is_marker_expired(data: dict) -> bool:
    """判断标记数据是否已过期。"""
    activated_at = float(data.get("activated_at", 0))
    return (time.time() - activated_at) > TTL_SECONDS


def activate(payload: dict) -> None:
    """激活 omo 模式 — 写入标记文件。

    在 PreToolUse(Skill) 检测到 /omo 调用时触发。
    若缺少 session_id 则拒绝写入，避免无会话标识的跨会话污染。
    """
    session_id = payload.get("session_id", "")
    if not session_id:
        _debug_log("[activate] skipped: missing session_id in payload")
        return
    key = project_key_from_payload(payload)
    path = _state_file_path(key, session_id, create_dir=True)
    _write_marker(path, session_id)


def is_active(payload: dict) -> bool:
    """检查 omo 模式是否处于激活状态（按 session 隔离）。

    检查逻辑:
    1. 没有 session_id -> 未激活
    2. 读取该 session 对应的标记文件
    3. 文件不存在 -> 未激活
    4. 标记已过期 -> 删除标记文件并视为未激活
    5. 标记有效 -> 已激活
    """
    key = project_key_from_payload(payload)
    current_session = payload.get("session_id", "")
    if not current_session:
        return False
    path = _state_file_path(key, current_session)
    data = _read_marker(path)
    if data is None:
        return False
    if _is_marker_expired(data):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        return False
    return True


def should_activate_from_prompt(payload: dict) -> bool:
    """检测用户 prompt 是否调用了 omo skill。

    匹配规则:
    - /omo, /omo:omo, /omo:omo-plan 等（原始格式）
    - /omo-workflow:omo, /omo-workflow:omo-plan 等（插件命令格式）
    不匹配 /omox, /omosphere 等非 omo 前缀。
    """
    prompt = payload.get("prompt", "").strip()
    return bool(
        re.match(r"^/omo(?::|[\s]|$)", prompt) or
        re.match(r"^/omo-workflow:omo", prompt)
    )


def cleanup_expired() -> int:
    """主动扫描 CLAUDE_PLUGIN_DATA 下所有项目的过期标记并删除。

    返回清理的标记文件数量。在 SessionStart 时调用以确保磁盘不累积垃圾。
    """
    data_root = _plugin_data_dir()
    if not data_root.exists():
        return 0

    cleaned = 0
    for state_dir in data_root.iterdir():
        if not state_dir.is_dir():
            continue
        for marker in state_dir.glob("*.json"):
            data = _read_marker(marker)
            if data and _is_marker_expired(data):
                try:
                    marker.unlink()
                    cleaned += 1
                except FileNotFoundError:
                    pass
        # 清理空目录（rmdir 仅当目录为空时才成功）
        try:
            state_dir.rmdir()
        except OSError:
            pass
    return cleaned


# ---------------------------------------------------------------------------
# Shared IO helpers
# ---------------------------------------------------------------------------


def load_payload() -> dict[str, Any]:
    """Read the JSON payload passed to the hook through stdin."""
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def emit_deny(event_name: str, reason: str) -> None:
    """Write a PreToolUse deny decision and stop the tool invocation."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=True))


def emit_context(event_name: str, context: str) -> None:
    """Write additional context for SessionStart or UserPromptSubmit hooks."""
    output = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": context,
        }
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=True))


def load_prompt(filename: str) -> str:
    """Load prompt content from prompts/<filename>, falling back to empty text."""
    try:
        return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _inject_paths(text: str) -> str:
    """Replace path placeholders with actual absolute paths."""
    return text.replace("__TASK_PY__", f"{HOOKS_DIR}/task.py")


# ---------------------------------------------------------------------------
# Agent guard helpers
# ---------------------------------------------------------------------------

# Only these subagent types may continue to use the built-in Agent tool.
ALLOWED_SUBAGENT_TYPES = {"claude-code-guide"}

# Path to models.json (single source of truth for registered agents)
_MODELS_JSON_PATH = Path.home() / ".codeagent" / "models.json"


def _load_known_agents() -> set[str]:
    """从 ~/.codeagent/models.json 读取已注册 agent 名。"""
    try:
        data = json.loads(_MODELS_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    agents = data.get("agents", {})
    if not isinstance(agents, dict):
        return set()
    return set(agents.keys())


# ---------------------------------------------------------------------------
# Mode handlers
# ---------------------------------------------------------------------------


def normalize_subagent_type(value: object) -> str:
    """Normalize subagent_type into a displayable string."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "<missing>"


def build_deny_reason(subagent_type: str, resolved_name: str, original_prompt: str = "") -> str:
    """构建 deny 消息，明确指示用 Bash 工具执行 task.py。"""
    task_py = f"{HOOKS_DIR}/task.py"
    task_content = original_prompt.strip() if original_prompt.strip() else "<your task here>"
    return (
        f"Agent tool '{subagent_type}' is BLOCKED by omo agent guard.\n"
        f"Instead, use Bash tool to run:\n"
        f"  {task_py} --agent {resolved_name} <<'TASK'\n"
        f"{task_content}\n"
        f"TASK\n"
    )


def handle_agent_guard(payload: dict[str, Any]) -> int:
    """Deny non-whitelisted Agent tool calls while omo mode is active."""
    active = is_active(payload)
    _debug_log(f"[agent-guard] is_active={active}")
    if not active:
        return 0

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    subagent_type = normalize_subagent_type(tool_input.get("subagent_type"))
    original_prompt = str(tool_input.get("prompt", "") or tool_input.get("description", ""))
    _debug_log(f"[agent-guard] subagent_type={subagent_type} prompt_len={len(original_prompt)}")
    if subagent_type in ALLOWED_SUBAGENT_TYPES:
        _debug_log(f"[agent-guard] whitelisted, allowing")
        return 0

    # 1. Build known agents from models.json + alias map
    known_agents = _load_known_agents()
    routing_table = load_routing_table()
    aliases = routing_table.get("agent_aliases", {})
    alias_keys = sorted(aliases.keys()) if isinstance(aliases, dict) else []
    _debug_log(f"[agent-guard] known_agents={sorted(known_agents)} alias_keys={alias_keys}")

    # 2. Check if subagent_type is a known agent or resolves via alias map
    resolved = resolve_agent_alias(routing_table, subagent_type)
    _debug_log(f"[agent-guard] resolved={resolved} in_known={subagent_type in known_agents} resolved_in_known={resolved in known_agents}")
    if subagent_type in known_agents or resolved in known_agents:
        emit_deny("PreToolUse", build_deny_reason(subagent_type, resolved, original_prompt))
    else:
        emit_deny("PreToolUse", build_deny_reason(subagent_type, subagent_type, original_prompt))
    return 0



def handle_user_prompt_submit(payload: dict[str, Any]) -> int:
    """Detect omo skill invocation and inject routing context when active."""
    # 检测 /omo 调用并激活（PreToolUse matcher 无法匹配 Skill，改用 prompt 检测）
    if should_activate_from_prompt(payload):
        activate(payload)
        _debug_log(f"[user-prompt-submit] activated via prompt detection")

    active = is_active(payload)
    _debug_log(f"[user-prompt-submit] is_active={active}")
    if not active:
        return 0

    header = load_prompt("user_prompt_submit.md")
    if not header:
        _debug_log(f"[user-prompt-submit] no user_prompt_submit.md content, skipping")
        return 0

    header = _inject_paths(header)

    _debug_log(f"[user-prompt-submit] injecting context ({len(header)} chars)")
    emit_context("UserPromptSubmit", header)
    return 0


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def _debug_log(message: str) -> None:
    """Append a timestamped log line to PLUGIN_DATA/debug.log."""
    log_dir = _plugin_data_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "debug.log"
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    try:
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except OSError:
        pass


def main() -> int:
    """Dispatch the unified hook entrypoint by CLI mode."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "agent-guard"

    payload = load_payload()
    _debug_log(f"mode={mode} payload_keys={sorted(payload.keys())}")

    if mode == "agent-guard":
        return handle_agent_guard(payload)
    if mode == "user-prompt-submit":
        return handle_user_prompt_submit(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
