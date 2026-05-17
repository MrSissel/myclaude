#!/bin/bash

# =========================
# macOS Notification Plugin for Claude Code
# =========================

# Read JSON from stdin
DATA=""
if [ -p /dev/stdin ] || [ ! -t 0 ]; then
    DATA=$(cat)
fi

# Extract all fields in a single Python call for efficiency
if [ -n "$DATA" ]; then
    eval "$(echo "$DATA" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
    def esc(s):
        if s is None:
            return ""
        return json.dumps(s, ensure_ascii=False)
    print("HOOK_EVENT=%s" % esc(d.get("hook_event_name")))
    print("CWD=%s" % esc(d.get("cwd")))
    print("LAST_ASSISTANT=%s" % esc(d.get("last_assistant_message")))
    print("MSG=%s" % esc(d.get("message")))
    print("ERROR=%s" % esc(d.get("error")))
    print("ERROR_DETAILS=%s" % esc(d.get("error_details")))
    print("NOTIFICATION_TYPE=%s" % esc(d.get("notification_type")))
    print("TOOL_NAME=%s" % esc(d.get("tool_name")))
    print("STDIN_TITLE=%s" % esc(d.get("title")))
except Exception:
    pass
' 2>/dev/null)"
fi

# Debug logging: write raw JSON to log file
LOG_FILE="/tmp/claude-notification-debug.log"
if [ -n "$DATA" ]; then
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$TIMESTAMP] HOOK_EVENT=$HOOK_EVENT NOTIFICATION_TYPE=$NOTIFICATION_TYPE" >> "$LOG_FILE"
    echo "RAW_JSON: $DATA" >> "$LOG_FILE"
    echo "---" >> "$LOG_FILE"
fi

# Extract project name from cwd basename
if [ -n "$CWD" ]; then
    PROJECT_NAME=$(basename "$CWD" 2>/dev/null || echo "")
else
    PROJECT_NAME=""
fi

# Fallback to current directory if project name is still empty
if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME=$(basename "$(pwd)" 2>/dev/null || echo "")
fi

if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME="ClaudeCode"
fi

# =========================
# Truncate body
# =========================
truncate_body() {
    local text="$1"
    if [ ${#text} -gt 80 ]; then
        echo "${text:0:77}..."
    else
        echo "$text"
    fi
}

# Escape for osascript (double quotes only)
escape_osascript() {
    local text="$1"
    echo "$text" | sed 's/"/\\"/g'
}

# =========================
# Build notification based on event type
# =========================
TITLE=""
BODY=""
SOUND="Glass"

if [ "$HOOK_EVENT" = "StopFailure" ]; then
    if [ -n "$ERROR" ]; then
        TITLE="$PROJECT_NAME - 遇到错误: $ERROR"
    else
        TITLE="$PROJECT_NAME - 遇到错误"
    fi
    if [ -n "$LAST_ASSISTANT" ]; then
        BODY="$LAST_ASSISTANT"
    elif [ -n "$ERROR_DETAILS" ]; then
        BODY="$ERROR_DETAILS"
    else
        BODY="对话因 API 错误异常结束"
    fi
    BODY=$(truncate_body "$BODY")
    SOUND="Basso"

elif [ "$HOOK_EVENT" = "PreToolUse" ] && [ -n "$TOOL_NAME" ] && echo "$TOOL_NAME" | grep -q "AskUserQuestion"; then
    TITLE="$PROJECT_NAME - 需要你的回答"
    BODY="有提问需要你的回答"
    SOUND="Ping"

elif [ "$HOOK_EVENT" = "Stop" ]; then
    TITLE="$PROJECT_NAME - 已完成"
    if [ -n "$LAST_ASSISTANT" ]; then
        BODY="$LAST_ASSISTANT"
    else
        BODY="任务完成，请查看结果"
    fi
    BODY=$(truncate_body "$BODY")
    SOUND="Glass"

else
    # Map notification_type to Chinese display names
    case "$NOTIFICATION_TYPE" in
        "permission_prompt")
            TYPE_DISPLAY="需要授权"
            ;;
        "idle_prompt")
            TYPE_DISPLAY="等待继续"
            ;;
        "auth_success")
            TYPE_DISPLAY="登录成功"
            ;;
        "elicitation_dialog")
            TYPE_DISPLAY="想确认一下"
            ;;
        "elicitation_complete")
            TYPE_DISPLAY="已了解"
            ;;
        "elicitation_response")
            TYPE_DISPLAY="收到回复"
            ;;
        *)
            TITLE="$PROJECT_NAME - Unknown Event HOOK_EVENT=$HOOK_EVENT TYPE=$NOTIFICATION_TYPE"
            BODY="See /tmp/claude-notification-debug.log for details"
            SOUND="Glass"
            ;;
    esac

    if [ -n "$TYPE_DISPLAY" ]; then
        TITLE="$PROJECT_NAME - $TYPE_DISPLAY"

        # Use message field if available, fallback to last_assistant_message
        if [ -n "$MSG" ]; then
            BODY=$(truncate_body "$MSG")
        elif [ -n "$LAST_ASSISTANT" ]; then
            BODY=$(truncate_body "$LAST_ASSISTANT")
        else
            BODY="-"
        fi

        # Override title if stdin provides one (prepend project name)
        if [ -n "$STDIN_TITLE" ]; then
            TITLE="$PROJECT_NAME - $STDIN_TITLE"
        fi
    fi
fi

# =========================
# Send macOS notification via osascript
# =========================
SAFE_TITLE=$(escape_osascript "$TITLE")
SAFE_BODY=$(escape_osascript "$BODY")

osascript -e "display notification \"$SAFE_BODY\" with title \"$SAFE_TITLE\" sound name \"$SOUND\""
