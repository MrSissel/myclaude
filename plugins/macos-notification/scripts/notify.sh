#!/bin/bash

# macOS Notification Plugin for Claude Code
# Entry script: delegates to notify.py

CLAUDE_PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export CLAUDE_PLUGIN_ROOT

exec "${CLAUDE_PLUGIN_ROOT}/scripts/notify.py"
