#!/usr/bin/env python3
"""
Claude Code CLI 状态检测模拟器。

在终端中循环显示各种状态输出，每 5 秒切换一次，
用于配合 terminalcp 会话测试 detect_claude_state() 的检测逻辑。

输出格式模拟真实 Claude Code CLI 的屏幕布局，包含：
- 分隔线 ────────
- 空 ❯ 提示符
- 模式行 ⏵⏵ accept edits on...
"""

import sys
import time

# ANSI 控制码
CLEAR_SCREEN = "\033[2J\033[H"

# 真实 Claude Code CLI 中的分隔线
SEPARATOR = "─" * 80

# 真实 Claude Code CLI 中的模式行
MODE_LINE_ACCEPT = "  ⏵⏵ accept edits on (shift+tab to cycle) · esc to interrupt"
MODE_LINE_PLAN = "  ⏸ plan mode on (shift+tab to cycle) · esc to interrupt"


def write(text: str) -> None:
    """写入并立即刷新。"""
    sys.stdout.write(text)
    sys.stdout.flush()


# 真实 Claude Code CLI 底部框架（processing/completed 共用）
def cli_footer(mode: str = "accept") -> str:
    """生成真实 Claude Code CLI 底部布局（空 ❯ 提示符）。"""
    mode_line = MODE_LINE_ACCEPT if mode == "accept" else MODE_LINE_PLAN
    return f"\n{SEPARATOR}\n❯\n{SEPARATOR}\n{mode_line}"


# 真实 Claude Code CLI 底部框架（inputting — 用户正在输入）
def cli_footer_inputting(text: str, mode: str = "accept") -> str:
    """生成真实 Claude Code CLI 输入布局（❯ 后有文字）。"""
    mode_line = MODE_LINE_ACCEPT if mode == "accept" else MODE_LINE_PLAN
    return f"\n{SEPARATOR}\n❯ {text}\n{SEPARATOR}\n{mode_line}"


# 定义各状态的模拟输出，每项为 (状态名, 预期检测结果, 终端输出内容)
STATES = [
    (
        "processing — 真实 CLI 布局 (Thinking)",
        "('processing', 'Thinking')",
        f"""\
I'll help you implement this feature.

Let me first look at the existing code structure.

✻ Thinking{cli_footer()}""",
    ),
    (
        "processing — 真实 CLI 布局 (Gallivanting…)",
        "('processing', 'Gallivanting… (1m 43s · ↓ 6.4k tokens)')",
        f"""\
      332  complete -c mk -f -n "__fish_seen" -l dry-run
      333
      334  # config mirror reset --tool

✢ Gallivanting… (1m 43s · ↓ 6.4k tokens){cli_footer()}""",
    ),
    (
        "processing — spinner + 未知文本",
        "('processing', 'Searching for patterns in src/')",
        f"""\
Looking through the codebase for relevant code.

✳ Searching for patterns in src/{cli_footer()}""",
    ),
    (
        "interactive (A) — INTERACTIVE_PROMPT",
        "('interactive', 'Should I proceed?')",
        """\
I've analyzed the code and here's my plan:

1. Refactor the authentication module
2. Add unit tests for the new logic
3. Update the API documentation

Should I proceed?""",
    ),
    (
        "interactive (B) — ❯ 选择菜单 (真实布局)",
        "('interactive', '1. Yes, clear context and auto-accept edits (shift+tab)')",
        """\
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

 Claude has written up a plan and is ready to execute. Would you like to
 proceed?

 ❯ 1. Yes, clear context and auto-accept edits (shift+tab)
   2. Yes, auto-accept edits
   3. Yes, manually approve edits
   4. Type here to tell Claude what to change

 ctrl-g to edit in Vim · ~/.claude/plans/example.md""",
    ),
    (
        "interactive (B) — ❯ 双条件确认 (简单)",
        "('interactive', 'Yes')",
        """\
I found two possible approaches.

Which approach do you prefer?
❯ Yes
  No""",
    ),
    (
        "interactive (B) — Exit plan mode? (? 距 ❯ 4行)",
        "('interactive', '1. Yes')",
        """\
────────────────────────────────────────────────────────────────────────────────
 Exit plan mode?

  Claude wants to exit plan mode

  ❯ 1. Yes
    2. No""",
    ),
    (
        "interactive (B2) — 权限确认 (分隔线边界)",
        "('interactive', '1. Allow once')",
        """\
────────────────────────────────────────────────────────────────────────────────
 Allow tool Read to read /etc/hosts?

  ❯ 1. Allow once
    2. Allow always
    3. Deny""",
    ),
    (
        "idle (B2) — ? 被分隔线阻断",
        "('idle', '')",
        """\
Is this correct?
────────────────────────────────────────────────────────────────────────────────
Some context below separator
❯ ls -la""",
    ),
    (
        "completed — 真实 CLI 布局 (Cogitated)",
        "('completed', 'Cogitated')",
        f"""\
✻ Cogitated for 1m 56s{cli_footer()}""",
    ),
    (
        "completed — 真实 CLI 布局 (Worked)",
        "('completed', 'Worked')",
        f"""\
I've finished implementing the feature.
All changes have been saved.

✻ Worked{cli_footer()}""",
    ),
    (
        "inputting (B1) — 用户正在输入 (accept 模式)",
        "('inputting', 'implement the auth feature')",
        f"""\
I've finished reviewing the code.
{cli_footer_inputting("implement the auth feature")}""",
    ),
    (
        "inputting (B1) — plan 模式下输入",
        "('inputting', 'fix the login bug')",
        f"""\
✻ Worked for 30s
{cli_footer_inputting("fix the login bug", mode="plan")}""",
    ),
    (
        "idle — 空 ❯ 无 spinner (真正的 idle)",
        "('idle', '')",
        f"""\
Task completed successfully.

All tests passed.
{SEPARATOR}
❯
{SEPARATOR}
{MODE_LINE_ACCEPT}""",
    ),
    (
        "idle — 无任何匹配模式的普通文本",
        "('idle', '')",
        """\
Some regular terminal output here.
This is just normal text with no special indicators.
Nothing to detect in this output.""",
    ),
]


def main() -> None:
    total = len(STATES)
    cycle = 0

    try:
        while True:
            for idx, (name, expected, content) in enumerate(STATES):
                cycle_info = f"cycle={cycle + 1}"
                header = (
                    f"{'=' * 60}\n"
                    f"  [{idx + 1}/{total}] {name}\n"
                    f"  expected: {expected}  ({cycle_info})\n"
                    f"{'=' * 60}\n"
                )

                write(CLEAR_SCREEN)
                write(header)
                write("\n")
                write(content)
                write("\n")

                time.sleep(5)

            cycle += 1

    except KeyboardInterrupt:
        write("\n\n--- 模拟器已停止 ---\n")


if __name__ == "__main__":
    main()
