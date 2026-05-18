#!/usr/bin/env python3
import datetime
import json
import os
import shutil
import subprocess
import sys

if not shutil.which("alerter"):
    raise RuntimeError("alerter not found. Run: brew install vjeantet/tap/alerter")

LOG_FILE = f"/tmp/claude-notification-{os.getuid()}-debug.log"


def log_debug(*lines: str) -> None:
    if os.environ.get("CLAUDE_PLUGIN_OPTION_DEBUG") == "true":
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            os.fchmod(f.fileno(), 0o600)
            for line in lines:
                f.write(f"[{ts}] {line}\n")


def truncate(text: str, max_len: int = 80) -> str:
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def send_notification(title: str, body: str, sound: str = "Glass") -> None:
    subprocess.Popen(
        [
            "alerter",
            "--title", title,
            "--message", body,
            "--timeout", "10",
            "--sound", sound,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def get_project_name(cwd: str | None) -> str:
    if cwd:
        project = os.path.basename(cwd)
        if project:
            return project
    try:
        project = os.path.basename(os.getcwd())
        if project:
            return project
    except Exception:
        pass
    return "ClaudeCode"


def main() -> None:
    data = sys.stdin.read()

    payload: dict = {}
    if data:
        try:
            payload = json.loads(data)
        except Exception:
            pass

    hook_event = payload.get("hook_event_name") or ""
    cwd = payload.get("cwd") or ""
    last_assistant = payload.get("last_assistant_message") or ""
    msg = payload.get("message") or ""
    error = payload.get("error") or ""
    error_details = payload.get("error_details") or ""
    notification_type = payload.get("notification_type") or ""
    tool_name = payload.get("tool_name") or ""
    stdin_title = payload.get("title") or ""

    log_debug(
        f"HOOK_EVENT={hook_event} NOTIFICATION_TYPE={notification_type}",
        f"RAW_JSON: {data}",
        "---",
    )

    project_name = get_project_name(cwd)

    title = ""
    body = ""
    sound = "Glass"

    if hook_event == "StopFailure":
        if error:
            title = f"{project_name} - 遇到错误: {error}"
        else:
            title = f"{project_name} - 遇到错误"
        if last_assistant:
            body = last_assistant
        elif error_details:
            body = error_details
        else:
            body = "对话因 API 错误异常结束"
        body = truncate(body)
        sound = "Basso"

    elif hook_event == "PreToolUse" and tool_name and "AskUserQuestion" in tool_name:
        title = f"{project_name} - 需要你的回答"
        body = "有提问需要你的回答"
        sound = "Ping"

    elif hook_event == "Stop":
        title = f"{project_name} - 已完成"
        if last_assistant:
            body = last_assistant
        else:
            body = "任务完成，请查看结果"
        body = truncate(body)
        sound = "Glass"

    else:
        type_display = ""
        if notification_type == "permission_prompt":
            type_display = "需要授权"
        elif notification_type == "idle_prompt":
            type_display = "等待继续"
        elif notification_type == "auth_success":
            type_display = "登录成功"
        elif notification_type == "elicitation_dialog":
            type_display = "想确认一下"
        elif notification_type == "elicitation_complete":
            type_display = "已了解"
        elif notification_type == "elicitation_response":
            type_display = "收到回复"

        if type_display:
            title = f"{project_name} - {type_display}"
            if msg:
                body = truncate(msg)
            elif last_assistant:
                body = truncate(last_assistant)
            else:
                body = "-"

            if stdin_title:
                title = f"{project_name} - {stdin_title}"
        else:
            title = f"{project_name} - Unknown Event HOOK_EVENT={hook_event} TYPE={notification_type}"
            body = "See /tmp/claude-notification-debug.log for details"
            sound = "Glass"

    send_notification(title, body, sound)


if __name__ == "__main__":
    main()
