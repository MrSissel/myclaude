# Claude Code macOS 通知插件

为 Claude Code 提供 macOS 原生桌面通知，让 AI 协作过程中的重要事件能够及时提醒你。

## 功能特性

- **任务完成提醒**：Claude Code 执行完任务时，收到桌面通知，显示项目名和最后一条助手消息
- **错误及时告警**：运行出错时立即弹出通知，显示错误类型和摘要信息
- **交互式提醒**：需要用户回答问题时，弹出通知提醒及时响应
- **状态变化通知**：等待继续、授权提醒等各种状态变化都会通过通知告知
- **智能内容处理**：通知内容自动截断到 80 字符，确保显示效果良好
- **不同事件不同音效**：错误用 Basso 音效，完成用 Glass 音效，提示用 Ping 音效

## 安装步骤

### 方式 A：通过 Marketplace 安装（推荐）

确保已注册 `wario-marketplace`：

```bash
/plugin install macos-notification@wario-marketplace
```

安装后插件自动生效，无需额外配置。

### 方式 B：手动安装

将插件目录链接到 Claude Code 插件目录：

```bash
mkdir -p ~/.claude/plugins
ln -s /path/to/wario-config/plugins/macos-notification ~/.claude/plugins/macos-notification
```

重启 Claude Code 后插件自动加载。

### 验证安装

运行一个 Claude Code 任务，完成后应该能看到 macOS 通知弹出。

## 通知类型说明

| 事件 | 标题格式 | 内容 | 音效 |
|------|---------|------|------|
| 任务完成 | `{项目名} - 已完成` | 最后一条助手消息 | Glass |
| 发生错误 | `{项目名} - 遇到错误` | 错误信息或助手消息 | Basso |
| 需要回答 | `{项目名} - 需要你的回答` | "有提问需要你的回答" | Ping |
| 等待继续 | `{项目名} - 等待继续` | 助手消息 | Glass |
| 需要授权 | `{项目名} - 需要授权` | 助手消息 | Glass |
| 登录成功 | `{项目名} - 登录成功` | 助手消息 | Glass |

## 技术实现

- 使用 `osascript` 调用 macOS 原生通知，不依赖外部工具
- 通过 hook 机制捕获 Claude Code 事件
- JSON 解析使用 Python3 保证兼容性
