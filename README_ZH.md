# terminalcp

[terminalcp](https://github.com/badlogic/terminalcp) 的 Python 移植版 — 让 AI 代理像人类一样控制交互式命令行工具。

## 功能简介

terminalcp 使 AI 代理能够实时启动和交互任何 CLI 工具 — 从调试器 (LLDB、GDB) 到其他 AI 编码助手 (Claude Code、Gemini CLI、Codex)。可以将其理解为终端版的 Playwright：你的代理可以启动进程、发送按键、读取输出，并与通常需要人工输入的工具保持完整的交互会话。

核心能力：
- 使用命令行调试器 (LLDB、GDB、pdb) 逐步调试代码
- 通过将其他 AI 工具作为子进程运行来实现协作
- 与 REPL (Python、Node、Ruby)、数据库 Shell 和系统监控器交互
- 控制任何需要人工输入的交互式 CLI
- 同时运行多个进程，不阻塞代理
- 用户可以从自己的终端附加到 AI 启动的进程，类似 screen/tmux

两种输出模式适用于不同场景：
- **终端模式 (stdout)**：返回带完整回滚的渲染屏幕 — 适用于 vim、htop 等 TUI 或可视化布局重要的交互式调试器
- **流模式 (stream)**：返回原始输出，支持 ANSI 剥离和增量读取 — 适用于构建流程、服务器日志和大量输出

每个进程运行在真正的伪终端 (PTY) 中，通过 [pyte](https://github.com/selectel/pyte) 进行完整的终端仿真，保留颜色、光标移动和特殊键序列。进程在后台运行，代理在管理长时间运行的工具时保持响应。

## 环境要求

- Python 3.10 或更高版本
- MCP 客户端 (VS Code、Cursor、Windsurf、Claude Desktop、Claude Code 等)

## 快速开始

### 安装

```bash
pip install terminalcp
```

或使用 uvx 直接运行（无需安装）：

```bash
uvx terminalcp --mcp
```

### MCP 客户端配置

**标准配置**，适用于大多数工具：

```json
{
  "mcpServers": {
    "terminalcp": {
      "command": "uvx",
      "args": ["terminalcp", "--mcp"]
    }
  }
}
```

<details>
<summary>Claude Code</summary>

使用 Claude Code CLI 添加 terminalcp 服务器：

```bash
claude mcp add -s user terminalcp uvx terminalcp --mcp
```
</details>

<details>
<summary>Claude Desktop</summary>

参考 MCP 安装[指南](https://modelcontextprotocol.io/quickstart/user)，使用上述标准配置。
</details>

<details>
<summary>Cursor</summary>

前往 `Cursor Settings` -> `MCP` -> `Add new MCP Server`。命名为 "terminalcp"，类型选 `command`，命令填 `uvx terminalcp --mcp`。
</details>

<details>
<summary>VS Code</summary>

参考 MCP 安装[指南](https://code.visualstudio.com/docs/copilot/chat/mcp-servers#_add-an-mcp-server)，使用上述标准配置。
</details>

<details>
<summary>通过 pip 安装的情况</summary>

如果已通过 `pip install terminalcp` 全局安装：

```json
{
  "mcpServers": {
    "terminalcp": {
      "command": "terminalcp",
      "args": ["--mcp"]
    }
  }
}
```
</details>

## MCP 使用示例

以下示例展示传递给 MCP 服务器暴露的 `terminalcp` 工具的 JSON 参数。MCP 服务器返回纯文本响应以减少 token 使用。

### 启动和管理进程

```json
// 使用自动生成的 ID 启动
{"action": "start", "command": "python3 -i"}
// 返回: "proc-3465b9b687af"

// 使用自定义名称启动（名称即为 ID）
{"action": "start", "command": "npm run dev", "name": "dev-server"}
// 返回: "dev-server"

// 在指定目录启动
{"action": "start", "command": "python3 script.py", "cwd": "/path/to/project", "name": "analyzer"}
// 返回: "analyzer"
```

### 与运行中的会话交互

```json
// 发送文本并按 Enter (\r)
{"action": "stdin", "id": "dev-server", "data": "npm test\r"}
// 返回: ""

// 发送方向键 (\u001b[D = 左箭头)
{"action": "stdin", "id": "editor", "data": "echo hello\u001b[D\u001b[D\u001b[D\u001b[Dhi \r"}

// 发送控制序列
{"action": "stdin", "id": "process", "data": "\u0003"}  // Ctrl+C
{"action": "stdin", "id": "shell", "data": "\u0004"}     // Ctrl+D (EOF)

// 获取终端输出（渲染后的屏幕）
{"action": "stdout", "id": "dev-server"}
// 返回: 带颜色和格式的完整终端屏幕

// 仅获取最后 N 行
{"action": "stdout", "id": "dev-server", "lines": 50}
```

### 监控长时间运行的进程

```json
// 获取所有原始输出（ANSI 码已剥离）
{"action": "stream", "id": "dev-server"}

// 仅获取上次检查后的新输出
{"action": "stream", "id": "dev-server", "since_last": true}

// 保留 ANSI 颜色码
{"action": "stream", "id": "dev-server", "since_last": true, "strip_ansi": false}
```

### 进程管理

```json
// 列出所有会话
{"action": "list"}
// 返回: "dev-server running /Users/you/project npm run dev\nanalyzer stopped /path python3 script.py"

// 停止指定进程
{"action": "stop", "id": "dev-server"}
// 返回: "stopped dev-server"

// 停止所有进程
{"action": "stop"}
// 返回: "stopped 3 processes"

// 关闭终端服务器
{"action": "kill-server"}
// 返回: "shutting down"
```

### AI 代理交互示例

```json
// 启动 Claude
{"action": "start", "command": "/path/to/claude --dangerously-skip-permissions", "name": "claude"}

// 发送提示
{"action": "stdin", "id": "claude", "data": "Write a test for main.py\r"}

// 获取响应
{"action": "stdout", "id": "claude"}

// 清理
{"action": "stop", "id": "claude"}
```

### 使用 LLDB 调试

```json
{"action": "start", "command": "lldb ./myapp", "name": "debugger"}
{"action": "stdin", "id": "debugger", "data": "break main\r"}
{"action": "stdin", "id": "debugger", "data": "run\r"}
{"action": "stdout", "id": "debugger"}
{"action": "stdin", "id": "debugger", "data": "bt\r"}
{"action": "stdout", "id": "debugger"}
```

### 构建过程监控

```json
{"action": "start", "command": "npm run build", "name": "build"}
// 监控进度
{"action": "stream", "id": "build", "since_last": true}
// ... 等待 ...
{"action": "stream", "id": "build", "since_last": true}  // 仅新输出
```

## CLI 使用

terminalcp 也可以作为独立的 CLI 工具使用：

```bash
# 列出所有活跃会话
terminalcp ls

# 启动一个自定义名称的新会话
terminalcp start my-app "npm run dev"

# 交互式附加到会话（Ctrl+B 分离）
terminalcp attach my-app

# 获取会话输出
terminalcp stdout my-app
terminalcp stdout my-app 50  # 最后 50 行

# 向会话发送输入（使用 :: 前缀表示特殊键）
terminalcp stdin my-app "echo hello" ::Enter
terminalcp stdin my-app "echo test" ::Left ::Left ::Left "hi " ::Enter
terminalcp stdin my-app ::C-c  # 发送 Ctrl+C

# 监控日志
terminalcp stream my-app --since-last
terminalcp stream my-app --with-ansi  # 保留 ANSI 码

# 调整终端大小
terminalcp resize my-app 120 40

# 获取终端大小
terminalcp term-size my-app

# 停止会话
terminalcp stop my-app
terminalcp stop  # 停止所有

# 维护
terminalcp version
terminalcp kill-server
```

## Zsh 补全

自动安装（推荐）：

```bash
terminalcp completion
```

手动安装：

```bash
mkdir -p ~/.zsh/completions
cp /path/to/terminalcp/terminalcp/completion/scripts/_terminalcp.zsh ~/.zsh/completions/_terminalcp
```

在 `~/.zshrc` 中启用：

```bash
fpath=(~/.zsh/completions $fpath)
autoload -Uz compinit && compinit
```

## 附加到会话

你可以从自己的终端附加到任何会话，观看或与 AI 启动的进程交互：

1. **AI 启动一个带名称的进程**：
```json
{"action": "start", "command": "python3 -i", "name": "python-debug"}
```

2. **从终端附加**：
```bash
terminalcp attach python-debug
```

3. **直接交互**：
- 正常输入命令
- 终端尺寸自动同步
- 按 **Ctrl+B** 分离（会话继续运行）
- 多个用户可以同时附加到同一会话

## 使用注意事项

- **MCP 转义序列**：使用转义序列发送特殊键：`\r` (Enter)、`\u001b[A` (上箭头)、`\u0003` (Ctrl+C)
- **CLI 特殊键**：使用 `::` 前缀：`::Enter`、`::Left`、`::C-c`、`::M-x`、`::F1`-`::F12`
- **别名不生效**：命令通过 `bash -c` 运行，请使用绝对路径或 PATH 中的命令
- **进程持久化**：会话在 MCP 服务器重启后仍然存在 — 完成后请手动停止
- **命名会话**：启动时使用 `name` 参数创建可读的会话 ID

### 常用转义序列（MCP 用）

```
// 基本键
Enter: "\r"          Tab: "\t"         Escape: "\u001b"      Backspace: "\u007f"

// 控制键
Ctrl+C: "\u0003"     Ctrl+D: "\u0004"  Ctrl+Z: "\u001a"      Ctrl+L: "\u000c"

// 方向键
Up: "\u001b[A"       Down: "\u001b[B"   Right: "\u001b[C"     Left: "\u001b[D"

// 导航键
Home: "\u001b[H"     End: "\u001b[F"    PageUp: "\u001b[5~"   PageDown: "\u001b[6~"

// 功能键
F1: "\u001bOP"       F2: "\u001bOQ"     F3: "\u001bOR"        F4: "\u001bOS"

// Meta/Alt（ESC + 字符）
Alt+x: "\u001bx"     Alt+b: "\u001bb"   Alt+f: "\u001bf"
```

## 编程使用 TerminalManager

`TerminalManager` 类提供了编程式 API，用于驱动 TUI 应用，适用于自动化、测试或构建高级抽象。

### 基本用法

```python
import asyncio
from terminalcp import TerminalManager, build_input

async def main():
    manager = TerminalManager()

    # 启动进程
    session_id = await manager.start('python3 -i', {'name': 'python-repl'})

    # 发送输入
    await manager.send_input(session_id, '2 + 2\r')

    # 等待输出稳定
    await asyncio.sleep(0.5)

    # 获取渲染后的终端屏幕
    output = await manager.get_output(session_id)
    print(output)

    # 获取原始流输出
    stream = await manager.get_stream(session_id, since_last=True)
    print(stream)

    # 使用 build_input 辅助函数发送特殊键
    await manager.send_input(session_id, build_input('Up', 'Enter'))

    # 清理
    await manager.stop(session_id)

asyncio.run(main())
```

### 高级 TUI 交互

```python
import asyncio
from terminalcp import TerminalManager, build_input

async def drive_debugger():
    manager = TerminalManager()

    # 启动 LLDB
    debug_id = await manager.start('lldb ./myapp')
    await manager.send_input(debug_id, 'break main\r')
    await manager.send_input(debug_id, 'run\r')

    await asyncio.sleep(1)

    # 获取调试器输出
    output = await manager.get_output(debug_id)
    print(output)

    # 使用特殊键导航
    await manager.send_input(debug_id, build_input('Up', 'Up', 'Enter'))

    # 监控流输出
    logs = await manager.get_stream(debug_id, since_last=True)
    print(logs)

    await manager.stop(debug_id)

asyncio.run(drive_debugger())
```

### 测试 TUI 应用

```python
import asyncio
import pytest
from terminalcp import TerminalManager

async def wait_for_output(manager, session_id, pattern, timeout=5.0):
    """等待终端输出包含期望的模式。"""
    elapsed = 0.0
    while elapsed < timeout:
        output = await manager.get_output(session_id)
        if pattern in output:
            return output
        await asyncio.sleep(0.1)
        elapsed += 0.1
    raise TimeoutError(f"等待超时: {pattern}")

@pytest.mark.asyncio
async def test_python_repl():
    manager = TerminalManager()
    session_id = await manager.start('python3 -i')

    try:
        await wait_for_output(manager, session_id, '>>>')
        await manager.send_input(session_id, '2 + 2\r')
        output = await wait_for_output(manager, session_id, '4')
        assert '4' in output
    finally:
        await manager.stop(session_id)

@pytest.mark.asyncio
async def test_vim_navigation():
    manager = TerminalManager()
    session_id = await manager.start('vim')

    try:
        await manager.send_input(session_id, 'iHello\x1b')  # 插入模式 + ESC
        await asyncio.sleep(0.3)
        output = await manager.get_output(session_id)
        assert 'Hello' in output
    finally:
        await manager.stop(session_id)
```

## 工作原理

terminalcp 采用分层架构以实现灵活性和持久化：

### 架构层次

1. **TerminalManager** — 管理 PTY 会话的核心库
   - 通过 Python `pty` 模块创建伪终端进程
   - 使用 [pyte](https://github.com/selectel/pyte) 维护虚拟终端
   - 处理输入/输出、ANSI 序列和终端仿真
   - 提供所有终端操作的编程 API

2. **TerminalServer** — 持久化后台守护进程
   - 在 CLI 或 MCP 需要时自动启动
   - 在 Unix 域套接字 `~/.terminalcp/server.sock` 上监听
   - 跨客户端管理所有活跃的终端会话
   - 客户端断开后会话仍然存在

3. **TerminalClient** — 通信层
   - CLI 和 MCP 都通过它与 TerminalServer 通信
   - 通过 Unix 套接字发送命令
   - 处理连接管理、重试和版本检查

4. **用户接口**
   - **MCP 服务器**：通过 [FastMCP](https://github.com/modelcontextprotocol/python-sdk) 暴露 `terminalcp` 工具
   - **CLI**：命令行接口
   - 两种接口提供相同的功能

### MCP 工具：`terminalcp`

MCP 服务器暴露一个名为 `terminalcp` 的工具，接受不同 action 类型的 JSON 命令：

| Action | 参数 | 返回值 |
|--------|------|--------|
| `start` | `command`, `cwd?`, `name?` | 会话 ID 字符串 |
| `stop` | `id?`（省略则停止所有） | 确认消息 |
| `stdout` | `id`, `lines?` | 渲染后的终端屏幕 |
| `stream` | `id`, `since_last?`, `strip_ansi?` | 原始输出文本 |
| `stdin` | `id`, `data` | 空字符串 |
| `list` | — | 换行分隔的会话列表 |
| `term-size` | `id` | "rows cols scrollback_lines" |
| `kill-server` | — | "shutting down" |

## 开发

```bash
# 克隆并以可编辑模式安装
git clone <repo>
cd terminalcp
pip install -e .

# 作为 MCP 服务器运行
terminalcp --mcp

# 作为终端服务器守护进程运行
terminalcp --server

# 本地开发使用 uvx
uvx --from . terminalcp --mcp
```

## 许可证

MIT
