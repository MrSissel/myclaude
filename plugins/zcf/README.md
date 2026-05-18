# zcf — Git 工作流工具集

zcf 提供一组 Git 实用命令，涵盖分支清理、提交生成、回滚和 worktree 管理，基于纯 Git 操作，无需依赖包管理器或构建工具。

---

## 功能概览

| 命令 | 用途 |
|------|------|
| `/git-cleanBranches` | 安全清理已合并或过期的分支，支持 dry-run 和受保护分支配置 |
| `/git-commit` | 仅用 Git 分析变更，生成符合 Conventional Commits 规范的消息，支持 emoji 前缀 |
| `/git-rollback` | 交互式回滚分支到历史版本，执行前多重安全确认 |
| `/git-worktree` | 在 `../.zcf/project-name/` 下管理 Git worktree，支持 IDE 集成和环境文件迁移 |

---

## 命令用法

### `/git-cleanBranches`

清理已合并或长期不活跃的分支。

```bash
/git-cleanBranches --dry-run           # 预览待清理分支（默认行为）
/git-cleanBranches --stale 90         # 清理 90 天无新提交的分支
/git-cleanBranches --base release/v2  # 以 release/v2 为基准清理
/git-cleanBranches --remote --yes     # 同时清理远程分支并跳过确认
```

关键特性：
- 默认 `--dry-run` 预览模式，确认后再执行删除
- 支持配置受保护分支（`git config --add branch.cleanup.protected develop`）
- 支持通配符保护（`release/*`）

---

### `/git-commit`

分析当前变更，生成 Conventional Commits 格式的提交信息。

```bash
/git-commit                      # 分析当前 staged/unstaged 变更
/git-commit --emoji              # 生成带 emoji 前缀的消息
/git-commit --all                # 自动 git add -A 后提交
/git-commit --scope ui --type feat   # 指定 scope 和 type
/git-commit --no-verify          # 跳过 Git hooks
```

关键特性：
- 仅依赖 Git，不调用任何包管理器
- 自动检测变更类型（feat/fix/docs/refactor 等）
- 变更跨越多个顶层目录或超过 300 行时，自动建议拆分提交
- 默认执行本地 Git hooks

---

### `/git-rollback`

交互式回滚分支到历史版本。

```bash
/git-rollback                         # 全交互模式（列出分支 → 选择 → 列出版本 → 选择 → 确认）
/git-rollback --branch dev            # 指定分支，其余交互
/git-rollback --branch main --target v1.2.0 --mode reset --yes   # 单命令执行
```

关键特性：
- `--dry-run` 默认开启，执行前预览操作
- 支持 `reset`（重写历史）和 `revert`（生成反向提交，保持历史完整）
- 危险操作前额外确认受保护分支
- 自动在 reflog 中记录备份点

---

### `/git-worktree`

管理 Git worktree，存放在 `../.zcf/project-name/` 目录。

```bash
/git-worktree add feature-ui           # 创建 worktree 和同名的 feature-ui 分支
/git-worktree add feature-ui -b my-feature -o   # 创建指定分支名并打开 IDE
/git-worktree list                    # 列出所有 worktree
/git-worktree remove feature-ui        # 移除 worktree
/git-worktree migrate feature-ui --from main      # 将 main 的未提交变更迁移到 feature-ui
/git-worktree migrate feature-ui --stash           # 迁移 stash 内容
```

关键特性：
- 从 main repo 或已有 worktree 中执行均能正确计算路径
- 自动复制 `.gitignore` 中声明的 `.env` 和 `.env.*` 文件到新 worktree
- 支持 VS Code / Cursor / WebStorm / Sublime Text / Vim 自动检测
- 支持跨 worktree 的内容迁移（未提交变更或 stash）

---

## Output Styles

Output Styles 用于在 Claude Code 中切换 AI 的输出语气和风格，使交互更符合个人偏好。

| 风格 | 文件 |
|------|------|
| 工程师专业版 | `engineer-professional.cn.md` / `engineer-professional.en.md` |
| 老王暴躁技术流 | `laowang-engineer.cn.md` / `laowang-engineer.en.md` |
| Linus Torvalds | `linus-torvalds.cn.md` / `linus-torvalds.en.md` |
| 猫娘工程师 | `nekomata-engineer.cn.md` / `nekomata-engineer.en.md` |
| 傲娇大小姐工程师 | `ojousama-engineer.cn.md` / `ojousama-engineer.en.md` |

风格特点：

- **工程师专业版** — 基于 SOLID/KISS/DRY/YAGNI 原则，严谨技术导向
- **老王暴躁技术流** — 嘴骂但代码高质量，执行到底不放弃
- **Linus Torvalds** — 直接精确、零容忍平庸，8 字符缩进、80 列限制
- **猫娘工程师** — 白发金眼猫娘，严谨中带颜文字情感表达，结尾带"喵～"
- **傲娇大小姐工程师** — 蓝发双马尾大小姐，完美主义傲娇语气，称用户为"笨蛋"

所有风格均包含：危险操作确认机制、KISS/YAGNI/DRY/SOLID 原则执行、路径处理规范、工具优先级（ripgrep > grep）。

---

## 接入方式

假设 marketplace 名称为 `wario-marketplace`，配置参考根目录 `README.md` 中的 `extraKnownMarketplaces` 说明。

**第一步**：在 `~/.claude/settings.json` 中添加 marketplace：

```json
{
  "extraKnownMarketplaces": {
    "wario-marketplace": {
      "source": {
        "source": "github",
        "repo": "MrSissel/myclaude"
      }
    }
  }
}
```

**第二步**：在 `enabledPlugins` 中启用本插件：

```json
{
  "enabledPlugins": {
    "zcf@wario-marketplace": true
  }
}
```

**第三步**：安装命令：

```
/plugin install zcf@wario-marketplace
```

---

## 目录结构

```
plugins/zcf/
├── README.md
├── .claude-plugin/
│   └── plugin.json              # 插件元数据
├── commands/
│   ├── git-cleanBranches.md
│   ├── git-commit.md
│   ├── git-rollback.md
│   └── git-worktree.md
└── output-styles/
    ├── engineer-professional.{cn,en}.md
    ├── laowang-engineer.{cn,en}.md
    ├── linus-torvalds.{cn,en}.md
    ├── nekomata-engineer.{cn,en}.md
    └── ojousama-engineer.{cn,en}.md
```
