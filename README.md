# Wario Config — 个人 Claude Code 插件市场

个人 Claude Code 插件市场，基于 cchub 中转，使用 Kimi / MiniMax 作为 AI 后端。

## 快捷接入

### 方式 A：本地路径（单机使用）

在 `~/.claude/settings.json` 中添加：

```json
{
  "extraKnownMarketplaces": {
    "wario-marketplace": {
      "source": {
        "source": "directory",
        "path": "/path/to/wario-config"
      }
    }
  },
  "enabledPlugins": {
    "omo-workflow@wario-marketplace": true
  }
}
```

> 将 `/path/to/wario-config` 替换为本仓库的实际路径。
>
> 如需指向 marketplace.json 文件，可使用 file 类型：
> ```json
> {
>   "extraKnownMarketplaces": {
>     "wario-marketplace": {
>       "source": {
>         "source": "file",
>         "path": "/path/to/wario-config/.claude-plugin/marketplace.json"
>       }
>     }
>   },
>   "enabledPlugins": {
>     "omo-workflow@wario-marketplace": true
>   }
> }
> ```

### 方式 B：GitHub（跨机器同步）

在 `~/.claude/settings.json` 中添加：

```json
{
  "extraKnownMarketplaces": {
    "wario-marketplace": {
      "source": {
        "source": "github",
        "repo": "MrSissel/myclaude"
      }
    }
  },
  "enabledPlugins": {
    "omo-workflow@wario-marketplace": true
  }
}
```

配置好后，打开任意项目时 Claude Code 会自动提示安装 `omo-workflow`，也可以手动执行：

```
/plugin install omo-workflow@wario-marketplace
```

---

## 完整配置

## 完整配置

### 1. 配置 models.json

创建 `~/.codeagent/models.json`：

```json
{
  "default_backend": "claude",
  "default_model": "kimi-for-coding",
  "full-output": true,
  "agents": {
    "hephaestus":        { "backend": "claude", "model": "kimi-for-coding",         "yolo": true },
    "oracle":            { "backend": "claude", "model": "kimi-for-coding",         "yolo": true },
    "metis":             { "backend": "claude", "model": "kimi-for-coding",         "yolo": true },
    "momus":             { "backend": "claude", "model": "kimi-for-coding",         "yolo": true },
    "ultrabrain":        { "backend": "claude", "model": "kimi-for-coding",         "yolo": true },
    "deep":              { "backend": "claude", "model": "kimi-for-coding",         "yolo": true },
    "artistry":          { "backend": "claude", "model": "kimi-for-coding",         "yolo": true },
    "unspecified-high":  { "backend": "claude", "model": "kimi-for-coding",         "yolo": true },
    "multimodal-looker": { "backend": "claude", "model": "kimi-for-coding",         "yolo": true },
    "code-scout":              { "backend": "claude", "model": "MiniMax-M2.7-highspeed", "yolo": true },
    "librarian":               { "backend": "claude", "model": "MiniMax-M2.7-highspeed", "yolo": true },
    "frontend-ui-ux-engineer": { "backend": "claude", "model": "MiniMax-M2.7-highspeed", "yolo": true },
    "document-writer":         { "backend": "claude", "model": "MiniMax-M2.7-highspeed", "yolo": true },
    "visual-engineering":      { "backend": "claude", "model": "MiniMax-M2.7-highspeed", "yolo": true },
    "quick":                   { "backend": "claude", "model": "MiniMax-M2.7-highspeed", "yolo": true },
    "unspecified-low":         { "backend": "claude", "model": "MiniMax-M2.7-highspeed", "yolo": true },
    "writing":                 { "backend": "claude", "model": "MiniMax-M2.7-highspeed", "yolo": true }
  }
}
```

### 2. 配置 cchub（ccswitch env）

```json
{
  "ANTHROPIC_BASE_URL": "https://app.claude-code-hub.orb.local",
  "ANTHROPIC_AUTH_TOKEN": "你的token",
  "ANTHROPIC_REASONING_MODEL": "kimi-for-coding",
  "ANTHROPIC_DEFAULT_OPUS_MODEL": "kimi-for-coding",
  "ANTHROPIC_MODEL": "kimi-for-coding",
  "ANTHROPIC_DEFAULT_HAIKU_MODEL": "MiniMax-M2.7-highspeed",
  "ANTHROPIC_DEFAULT_SONNET_MODEL": "kimi-for-coding",
  "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
  "CLAUDE_CODE_NO_FLICKER": "1"
}
```

---

## 插件列表

- **omo-workflow** `v1.1.0` - OmO 多 Agent 编排工作流，包含 `/omo`、`/omo-plan`、`/omo-execute` 三个入口，依赖 `codeagent-wrapper`
- **macos-notification** `v1.0.0` - Claude Code macOS 原生通知插件，任务完成、错误、等待输入时发送桌面通知，零依赖

---

## codeagent-wrapper 安装

```bash
# macOS (Apple Silicon)
mkdir -p ~/.claude/bin
curl -L -o ~/.claude/bin/codeagent-wrapper \
  https://github.com/cexll/myclaude/releases/latest/download/codeagent-wrapper-darwin-arm64
chmod +x ~/.claude/bin/codeagent-wrapper
```

在 `~/.zshrc` 中添加 PATH：

```bash
export PATH="$HOME/.claude/bin:$PATH"
```

添加后**重启 Claude Code** 使 PATH 生效。

---

## 模型分工

| 模型 | 负责的 Agent |
|---|---|
| `kimi-for-coding` | 主调度（Sisyphus/Atlas/Prometheus）、复杂实现（hephaestus/deep/ultrabrain）、架构咨询（oracle/metis）、多模态（multimodal-looker） |
| `MiniMax-M2.7-highspeed` | 代码探索（code-scout）、文档检索（librarian）、前端实现（visual-engineering）、轻量任务（quick/unspecified-low）、文档写作（writing） |

---

## 目录结构

```
wario-config/
├── README.md
├── .claude-plugin/
│   └── marketplace.json          # marketplace 注册文件
├── .claude/
│   └── skills/
│       └── marketplace-organizer/ # 插件结构规范 skill
└── plugins/
    └── omo-workflow/             # OmO 多 Agent 编排工作流
        ├── .claude-plugin/
        │   └── plugin.json
        ├── hooks/                # agent_guard.py, task.py, routing_table.json
        ├── skills/               # /omo, /omo-plan, /omo-execute
        ├── references/           # 各专家 Agent 的 prompt
        └── README.md
```
