"""
detect_claude_state() 和 detect_claude_mode() 核心检测函数的单元测试。

测试状态检测逻辑的正确性，包括：
- idle / inputting / interactive / processing / completed 五种状态
- ❯ + 文字 + 分隔线包围 → inputting
- ❯ + 文字 + 分隔线边界内有 ? → interactive
- INTERACTIVE_PROMPTS 精确匹配
- spinner 旋转字符检测
- 模式检测（plan / accept-edits / default）
- 各种优先级和共存场景
"""

import pytest
from terminalcp.claude_status import (
    detect_claude_state,
    detect_claude_mode,
    INTERACTIVE_PROMPTS,
    COMPLETED_WORDS,
    PROCESSING_WORDS,
    SPINNER_CHARS,
)


# =========================================================================
# A. detect_claude_state() 测试
# =========================================================================


class TestIdleState:
    """idle 状态检测测试。"""

    def test_empty_string(self):
        """空字符串 → idle。"""
        assert detect_claude_state("") == ("idle", "")

    def test_blank_lines_only(self):
        """只有空白行 → idle。"""
        assert detect_claude_state("   \n  \n   \n") == ("idle", "")

    def test_prompt_arrow_no_text(self):
        """❯ 后无文本 → idle（等待用户输入）。"""
        assert detect_claude_state("❯ ") == ("idle", "")
        assert detect_claude_state("  ❯  ") == ("idle", "")

    def test_plain_text_no_indicators(self):
        """无任何匹配模式的普通文本 → idle。"""
        output = "Some regular output\nJust normal text\nNothing special here"
        assert detect_claude_state(output) == ("idle", "")


class TestInteractivePromptsState:
    """interactive 状态 — INTERACTIVE_PROMPTS 匹配测试。"""

    def test_should_i_proceed(self):
        """'Should I proceed?' → interactive。"""
        output = "Some context\nShould I proceed?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Should I proceed?"

    def test_do_you_want_to_proceed(self):
        """'Do you want to proceed?' → interactive。"""
        output = "Info\nDo you want to proceed?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Do you want to proceed?"

    def test_would_you_like_to_proceed(self):
        """'Would you like to proceed?' → interactive。"""
        output = "Would you like to proceed?\nSome trailing text"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Would you like to proceed?"

    def test_would_you_like_to_proceed_with_plan(self):
        """'Would you like to proceed with this plan?' → interactive。"""
        output = "Would you like to proceed with this plan?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Would you like to proceed with this plan?"

    def test_proceed_with_this_plan(self):
        """'Proceed with this plan?' → interactive。"""
        output = "Proceed with this plan?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Proceed with this plan?"

    def test_ready_to_submit(self):
        """'Ready to submit your answers?' → interactive。"""
        output = "Ready to submit your answers?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Ready to submit your answers?"

    def test_prompt_with_prefix_text(self):
        """提示出现在行中间（带前缀文本）→ 正确检测。"""
        output = "Context: Should I proceed?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Should I proceed?"

    def test_case_sensitive_no_match(self):
        """大小写变体 → 确认不匹配（case-sensitive）。"""
        output = "should i proceed?"
        state, _ = detect_claude_state(output)
        assert state == "idle"

    def test_bottom_prompt_wins(self):
        """多个 interactive 提示 → 返回最底部那个。"""
        output = "Should I proceed?\nSome middle text\nDo you want to proceed?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Do you want to proceed?"

    def test_prompt_beats_spinner_above(self):
        """INTERACTIVE_PROMPTS 在 spinner 下方 → interactive。"""
        output = "✻ Thinking\nSome context\nShould I proceed?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Should I proceed?"

    def test_all_interactive_prompts_detectable(self):
        """验证所有 INTERACTIVE_PROMPTS 都能被检测到。"""
        for prompt in INTERACTIVE_PROMPTS:
            output = f"Some context\n{prompt}"
            state, detail = detect_claude_state(output)
            assert state == "interactive", f"Failed for prompt: {prompt}"
            assert detail == prompt, f"Wrong detail for prompt: {prompt}"


class TestInteractiveArrowDualCondition:
    """interactive 状态 — ❯ 双条件确认测试（核心保证性验证）。"""

    def test_arrow_with_question_1_line_above(self):
        """❯ + 文字 + 上方1行有 ? → interactive。"""
        output = "Which option?\n❯ Yes"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Yes"

    def test_arrow_with_question_and_options_below(self):
        """❯ + 文字 + 上方有 ? + 下方有其他选项 → interactive。"""
        output = "Which option?\n❯ No\n  Maybe"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "No"

    def test_arrow_with_question_and_stale_spinner(self):
        """❯ + 文字 + 上方有 ? + 更上方有残留 spinner → 必须返回 interactive（核心保证）。"""
        output = "✻ Thinking\nWhich approach?\n❯ Approach A\n  Approach B"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Approach A"

    def test_arrow_with_question_2_lines_above(self):
        """❯ + 文字 + 上方2行有 ?（中间隔空行）→ interactive。"""
        output = "Which approach?\n\n❯ Option A"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Option A"

    def test_arrow_with_question_3_lines_above(self):
        """❯ + 文字 + 上方3行有 ? → 仍在范围内 → interactive。"""
        output = "Which approach?\nSome context\nMore info\n❯ Option A"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Option A"

    def test_arrow_with_question_4_lines_above_in_range(self):
        """❯ + 文字 + 上方4行有 ?（在扩展范围内）→ interactive。"""
        output = "Which approach?\nLine 2\nLine 3\nLine 4\n❯ Option A"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Option A"

    def test_arrow_with_question_8_lines_above_no_separator(self):
        """❯ + 文字 + 上方8行有 ?（无分隔线阻隔）→ interactive。"""
        lines = ["Which approach?"] + [f"Line {i}" for i in range(2, 9)] + ["❯ Option A"]
        output = "\n".join(lines)
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Option A"

    def test_arrow_with_question_15_lines_above_no_separator(self):
        """❯ + 文字 + 上方15行有 ?（无分隔线、在搜索范围内）→ interactive。"""
        lines = ["Which approach?"] + [f"Line {i}" for i in range(2, 16)] + ["❯ Option A"]
        output = "\n".join(lines)
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Option A"

    def test_arrow_with_question_blocked_by_separator(self):
        """❯ + 文字 + ? 被分隔线阻隔 → 不确认为 interactive。"""
        output = "Which approach?\n────────────────────\nSome text\n❯ Option A"
        state, detail = detect_claude_state(output)
        # ? 在分隔线上方，搜索到分隔线停止 → 未找到 ? → idle
        assert state == "idle"

    def test_arrow_without_question_not_interactive(self):
        """❯ + 文字 但上方无 ?（代码输出中的 ❯）→ 不返回 interactive。"""
        output = "Here is the shell prompt:\n❯ ls -la\nSome output"
        state, detail = detect_claude_state(output)
        # ❯ 不被确认，继续扫描 → 无匹配 → idle
        assert state == "idle"

    def test_arrow_with_question_and_spinner_above_both(self):
        """❯ + 文字 + 上方有 ? + 上方也有 spinner → interactive（最关键场景）。"""
        output = "✻ Processing data\nWhich file do you want to edit?\n❯ file1.py\n  file2.py"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "file1.py"

    def test_arrow_with_trimmed_text_and_question(self):
        """❯ 后有多个空格再有文字 + 上方有 ? → 正确 trim 后返回 interactive。"""
        output = "Choose one?\n❯   Option A   "
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Option A"

    def test_arrow_with_completed_spinner_above_question(self):
        """❯ + 文字 + 上方有 ? + 更上方有 COMPLETED spinner → interactive。"""
        output = "✻ Worked\nDo you want to continue?\n❯ Yes\n  No"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Yes"

    def test_real_claude_exit_plan_mode_layout(self):
        """完整的真实 Claude Code CLI "Exit plan mode?" 布局（? 距 ❯ 4行）。"""
        output = (
            "────────────────────────────────────────────────────────────────────────────────\n"
            " Exit plan mode?\n"
            "\n"
            "  Claude wants to exit plan mode\n"
            "\n"
            "  ❯ 1. Yes\n"
            "    2. No"
        )
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert "Yes" in detail

    def test_arrow_idle_not_affected_by_dual_condition(self):
        """❯ 无文字 → idle，不受双条件影响。"""
        output = "Which option?\n❯ "
        state, detail = detect_claude_state(output)
        assert state == "idle"
        assert detail == ""

    def test_arrow_idle_with_question_above(self):
        """❯ 无文字 + 上方有 ? → 仍是 idle（双条件仅适用于 ❯ + 文字）。"""
        output = "Which option?\n❯"
        state, detail = detect_claude_state(output)
        assert state == "idle"
        assert detail == ""


class TestInputtingState:
    """inputting 状态检测测试（❯ + 文字 + 分隔线包围）。

    真实 Claude Code CLI 中，用户在输入框输入文字时：
      ────────────（分隔线）
      ❯ 用户输入的文字
      ────────────（分隔线）
      ⏵⏵ mode 行
    """

    def test_inputting_basic(self):
        """❯ + 文字 + 上下分隔线 → inputting。"""
        output = "────────────────────\n❯ hello world\n────────────────────"
        state, detail = detect_claude_state(output)
        assert state == "inputting"
        assert detail == "hello world"

    def test_inputting_real_layout(self):
        """完整的真实 CLI 输入布局（含 mode 行）→ inputting。"""
        output = (
            "I've finished reviewing the code.\n"
            "\n"
            "────────────────────────────────────────────────────────────────────────────────\n"
            "❯ implement the auth feature\n"
            "────────────────────────────────────────────────────────────────────────────────\n"
            "  ⏵⏵ accept edits on (shift+tab to cycle) · esc to interrupt"
        )
        state, detail = detect_claude_state(output)
        assert state == "inputting"
        assert detail == "implement the auth feature"

    def test_inputting_with_dashed_separator(self):
        """❯ + 文字 + 上下虚线分隔线（╌）→ inputting。"""
        output = "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n❯ some input\n╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌"
        state, detail = detect_claude_state(output)
        assert state == "inputting"
        assert detail == "some input"

    def test_inputting_with_empty_lines_between(self):
        """❯ 与分隔线间有空行（最近非空行是分隔线）→ inputting。"""
        output = "────────────────────\n\n❯ typing here\n\n────────────────────"
        state, detail = detect_claude_state(output)
        assert state == "inputting"
        assert detail == "typing here"

    def test_not_inputting_only_sep_above(self):
        """只有上方有分隔线，下方无 → 不是 inputting。"""
        output = "────────────────────\n❯ some text\nNot a separator"
        state, detail = detect_claude_state(output)
        # 不是 inputting，也无 ?（分隔线阻断搜索）→ idle
        assert state != "inputting"

    def test_not_inputting_only_sep_below(self):
        """只有下方有分隔线，上方无 → 不是 inputting。"""
        output = "Not a separator\n❯ some text\n────────────────────"
        state, detail = detect_claude_state(output)
        assert state != "inputting"

    def test_inputting_question_above_separator_ignored(self):
        """❯ 被分隔线包围 + 分隔线上方有 ? → 仍是 inputting（不是 interactive）。"""
        output = (
            "Which approach?\n"
            "────────────────────\n"
            "❯ my response\n"
            "────────────────────"
        )
        state, detail = detect_claude_state(output)
        assert state == "inputting"
        assert detail == "my response"


class TestSeparatorBoundary:
    """分隔线边界对 ❯ + ? 搜索的影响测试。"""

    def test_question_between_separator_and_arrow(self):
        """? 在分隔线与 ❯ 之间 → interactive。"""
        output = (
            "────────────────────\n"
            "Which option?\n"
            "\n"
            "❯ Yes\n"
            "  No"
        )
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Yes"

    def test_question_above_separator_not_found(self):
        """? 在分隔线上方 → 搜索到分隔线停止 → 不检测为 interactive。"""
        output = (
            "Is this correct?\n"
            "────────────────────\n"
            "Some context\n"
            "❯ Option A\n"
            "  Option B"
        )
        state, detail = detect_claude_state(output)
        # ? 在分隔线上方，分隔线阻断搜索 → 不是 interactive
        assert state == "idle"

    def test_separator_boundary_real_exit_plan_mode(self):
        """真实 "Exit plan mode?" 布局 — ? 在分隔线下方。"""
        output = (
            "────────────────────────────────────────────────────────────────────────────────\n"
            " Exit plan mode?\n"
            "\n"
            "  Claude wants to exit plan mode\n"
            "\n"
            "  ❯ 1. Yes\n"
            "    2. No"
        )
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert "Yes" in detail

    def test_no_separator_question_far_above(self):
        """无分隔线时 ? 在远处 → 仍可找到（分隔线才是边界，非固定行数）。"""
        lines = ["Which approach?"] + [f"Line {i}" for i in range(2, 12)] + ["❯ Option A"]
        output = "\n".join(lines)
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Option A"

    def test_multiple_separators_nearest_blocks(self):
        """多个分隔线 → 最近的分隔线阻断搜索。"""
        output = (
            "Is this right?\n"
            "────────────────────\n"
            "More context?\n"
            "────────────────────\n"
            "Some text\n"
            "❯ Option A"
        )
        state, detail = detect_claude_state(output)
        # 最近的分隔线在 "Some text" 上方，"Some text" 无 ? → 不是 interactive
        # 但 "More context?" 在分隔线下方但被更近的分隔线阻断… 等等
        # 实际搜索：offset 1 → "Some text"（无?），offset 2 → "────────"（分隔线，停止）
        assert state == "idle"


class TestProcessingState:
    """processing 状态检测测试。"""

    def test_spinner_with_known_processing_word(self):
        """spinner + 已知 PROCESSING_WORD → processing。"""
        output = "✻ Thinking"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Thinking"

    def test_spinner_with_ellipsis_ascii(self):
        """spinner + ASCII 省略号 → processing。"""
        output = "✻ Loading..."
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Loading..."

    def test_spinner_with_ellipsis_unicode(self):
        """spinner + Unicode 省略号 → processing。"""
        output = "✻ Loading…"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Loading…"

    def test_spinner_with_unknown_text(self):
        """spinner + 未知文本 → processing。"""
        output = "✻ Custom unknown text"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Custom unknown text"

    def test_spinner_no_text_skipped(self):
        """spinner 行无后续文本 → 跳过，继续扫描。"""
        output = "Some text\n✻ \nAnother text"
        state, _ = detect_claude_state(output)
        # spinner 无文本被跳过，"Another text" 和 "Some text" 都不匹配 → idle
        assert state == "idle"

    def test_multiple_spinners_bottom_wins(self):
        """多个 spinner 行 → 返回最底部的匹配。"""
        output = "✻ Thinking\n✻ Writing"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Writing"

    def test_all_spinner_chars_work(self):
        """验证所有 SPINNER_CHARS 都能触发检测。"""
        for char in SPINNER_CHARS:
            output = f"{char} Processing"
            state, detail = detect_claude_state(output)
            assert state == "processing", f"Failed for spinner char: {char}"

    def test_spinner_with_leading_whitespace(self):
        """spinner 前有空白 → 正常匹配。"""
        output = "   ✻ Thinking"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Thinking"

    def test_some_processing_words(self):
        """测试多个常见的 PROCESSING_WORDS。"""
        words = ["Thinking", "Writing", "Processing", "Cooking", "Computing"]
        for word in words:
            output = f"✻ {word}"
            state, detail = detect_claude_state(output)
            assert state == "processing", f"Failed for word: {word}"
            assert word in detail


class TestCompletedState:
    """completed 状态检测测试。"""

    def test_spinner_with_completed_word(self):
        """spinner + COMPLETED_WORD → completed。"""
        output = "✻ Worked"
        state, detail = detect_claude_state(output)
        assert state == "completed"
        assert detail == "Worked"

    def test_all_completed_words(self):
        """验证所有 COMPLETED_WORDS 都能被检测到。"""
        for word in COMPLETED_WORDS:
            output = f"✻ {word}"
            state, detail = detect_claude_state(output)
            assert state == "completed", f"Failed for completed word: {word}"
            assert detail == word

    def test_completed_word_case_sensitive(self):
        """completed word 大小写不匹配 → 不返回 completed。"""
        output = "✻ worked"
        state, _ = detect_claude_state(output)
        # "worked" 不在 COMPLETED_WORDS（case-sensitive）→ 作为未知文本处理
        assert state == "processing"

    def test_completed_at_bottom_processing_above(self):
        """completed word 在底部、processing word 在上方 → 返回 completed。"""
        output = "✻ Thinking\n✻ Worked"
        state, detail = detect_claude_state(output)
        assert state == "completed"
        assert detail == "Worked"


class TestPriorityAndCoexistence:
    """优先级和共存场景测试（验证单次扫描逻辑的正确性）。"""

    def test_arrow_confirmed_beats_spinner_above(self):
        """❯(+?确认) 在 spinner 下方 → interactive（❯ 更近底部）。"""
        output = "✻ Thinking\nWhich option?\n❯ Option A"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Option A"

    def test_spinner_below_arrow_wins(self):
        """spinner 在 ❯ 下方 → processing（spinner 更近底部）。"""
        output = "Which option?\n❯ Option A\n✻ Thinking"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Thinking"

    def test_interactive_prompt_below_arrow_wins(self):
        """INTERACTIVE_PROMPTS 在 ❯ 下方 → interactive（prompts 更近底部）。"""
        output = "Choose?\n❯ Option A\nShould I proceed?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Should I proceed?"

    def test_all_indicators_coexist_bottom_wins(self):
        """全部三种指示符共存 → 返回最靠近底部的那个。"""
        # 底部是 INTERACTIVE_PROMPT
        output = "✻ Thinking\nChoose?\n❯ Option A\n  Option B\nShould I proceed?"
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Should I proceed?"

    def test_arrow_no_question_fallback_to_spinner(self):
        """❯ 无 ? 确认 + 上方有 spinner → 跳过 ❯ → 返回 spinner 的 processing。"""
        output = "✻ Thinking\nSome text\n❯ ls -la\nMore output"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Thinking"

    def test_spinner_below_unconfirmed_arrow(self):
        """❯ 无 ? 确认 + 下方有 spinner → spinner 先匹配 → processing。"""
        output = "Heading\n❯ Some text\n✻ Writing"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Writing"

    def test_long_output_detects_bottom_state(self):
        """非常长的输出（含大量普通文本）→ 正确检测底部状态。"""
        lines = [f"Line {i}: some regular output" for i in range(100)]
        lines.append("✻ Thinking")
        output = "\n".join(lines)
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Thinking"

    def test_long_output_with_interactive_at_bottom(self):
        """长输出 + 底部有交互提示。"""
        lines = [f"Line {i}" for i in range(50)]
        lines.append("Should I proceed?")
        output = "\n".join(lines)
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Should I proceed?"


class TestBareArrowWithSpinner:
    """空 ❯ 与 spinner 共存的场景测试（真实 Claude Code CLI 布局）。

    真实 Claude Code CLI 在 processing/completed 状态下，屏幕底部有：
      spinner 行
      ────────────（分隔线）
      ❯           （空提示符）
      ────────────（分隔线）
      ⏵⏵ mode 行

    修复前，空 ❯ 立即返回 idle，导致 spinner 永远不会被检测到。
    修复后，空 ❯ 继续向上扫描，正确检测 spinner 状态。
    """

    def test_bare_arrow_with_processing_spinner_above(self):
        """空 ❯ 上方有 processing spinner → processing。"""
        output = "✢ Gallivanting…\n❯"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert "Gallivanting" in detail

    def test_bare_arrow_with_completed_spinner_above(self):
        """空 ❯ 上方有 completed spinner → completed。"""
        output = "✻ Cogitated for 1m 56s\n❯"
        state, detail = detect_claude_state(output)
        assert state == "completed"
        assert detail == "Cogitated"

    def test_bare_arrow_without_spinner_above(self):
        """空 ❯ 上方无 spinner → idle。"""
        output = "Some regular output\nAnother line\n❯"
        state, detail = detect_claude_state(output)
        assert state == "idle"
        assert detail == ""

    def test_bare_arrow_only(self):
        """只有空 ❯ → idle。"""
        assert detect_claude_state("❯") == ("idle", "")
        assert detect_claude_state("❯ ") == ("idle", "")
        assert detect_claude_state("  ❯  ") == ("idle", "")

    def test_real_claude_processing_layout(self):
        """完整的真实 Claude Code CLI processing 布局。"""
        output = (
            "      332  complete -c mk -f -n \"__fish_seen\" -l dry-run\n"
            "      333\n"
            "      334  # config mirror reset --tool\n"
            "\n"
            "✢ Gallivanting… (1m 43s · ↓ 6.4k tokens)\n"
            "\n"
            "────────────────────────────────────────────────────────────────────────────────\n"
            "❯\n"
            "────────────────────────────────────────────────────────────────────────────────\n"
            "  ⏵⏵ accept edits on (shift+tab to cycle) · esc to interrupt"
        )
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert "Gallivanting" in detail

    def test_real_claude_completed_layout(self):
        """完整的真实 Claude Code CLI completed 布局。"""
        output = (
            "✻ Cogitated for 1m 56s\n"
            "\n"
            "────────────────────────────────────────────────────────────────────────────────\n"
            "❯\n"
            "────────────────────────────────────────────────────────────────────────────────\n"
            "  ⏵⏵ accept edits on (shift+tab to cycle)"
        )
        state, detail = detect_claude_state(output)
        assert state == "completed"
        assert detail == "Cogitated"

    def test_real_claude_interactive_layout(self):
        """完整的真实 Claude Code CLI interactive 布局。"""
        output = (
            "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
            "\n"
            " Claude has written up a plan and is ready to execute. Would you like to\n"
            " proceed?\n"
            "\n"
            " ❯ 1. Yes, clear context and auto-accept edits (shift+tab)\n"
            "   2. Yes, auto-accept edits\n"
            "   3. Yes, manually approve edits\n"
            "   4. Type here to tell Claude what to change\n"
            "\n"
            " ctrl-g to edit in Vim · ~/.claude/plans/example.md"
        )
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert "Yes" in detail

    def test_bare_arrow_with_separator_lines(self):
        """空 ❯ 被分隔线包围 + 上方有 spinner → 正确穿透分隔线。"""
        output = (
            "✻ Worked\n"
            "────────\n"
            "❯\n"
            "────────"
        )
        state, detail = detect_claude_state(output)
        assert state == "completed"
        assert detail == "Worked"

    def test_multiple_bare_arrows_spinner_above(self):
        """多个空 ❯ + 上方有 spinner → 都跳过，最终检测到 spinner。"""
        output = "✢ Thinking\nSome output\n❯\n❯"
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Thinking"


# =========================================================================
# B. detect_claude_mode() 测试
# =========================================================================


class TestDetectClaudeMode:
    """detect_claude_mode() 模式检测测试。"""

    def test_empty_string(self):
        """空字符串 → default。"""
        assert detect_claude_mode("") == "default"

    def test_no_mode_indicators(self):
        """无模式标识 → default。"""
        assert detect_claude_mode("Some regular output\nNothing special") == "default"

    def test_plan_mode(self):
        """包含 ⏸ + 'plan' → plan。"""
        assert detect_claude_mode("⏸ plan mode active") == "plan"

    def test_accept_edits_mode(self):
        """包含 ⏵⏵ + 'accept' → accept-edits。"""
        assert detect_claude_mode("⏵⏵ accept edits") == "accept-edits"

    def test_pause_without_plan(self):
        """⏸ 无 'plan' → default。"""
        assert detect_claude_mode("⏸ something else") == "default"

    def test_plan_without_pause(self):
        """'plan' 无 ⏸ → default。"""
        assert detect_claude_mode("This is the plan for today") == "default"

    def test_both_modes_plan_wins(self):
        """两种模式标识同时存在 → plan 先匹配（从上到下扫描）。"""
        output = "⏸ plan mode\n⏵⏵ accept edits"
        assert detect_claude_mode(output) == "plan"

    def test_both_modes_accept_first(self):
        """accept-edits 在 plan 上方 → accept-edits 先匹配。"""
        output = "⏵⏵ accept edits\n⏸ plan mode"
        assert detect_claude_mode(output) == "accept-edits"

    def test_mode_on_non_last_line(self):
        """模式标识在非最后一行 → 仍能检测。"""
        output = "⏸ plan mode\nSome other output\nMore text"
        assert detect_claude_mode(output) == "plan"

    def test_plan_case_insensitive(self):
        """大小写变体 'PLAN'、'Plan' → 都能匹配。"""
        assert detect_claude_mode("⏸ PLAN mode") == "plan"
        assert detect_claude_mode("⏸ Plan Mode") == "plan"

    def test_accept_case_insensitive(self):
        """'accept' 大小写变体 → 都能匹配。"""
        assert detect_claude_mode("⏵⏵ ACCEPT edits") == "accept-edits"
        assert detect_claude_mode("⏵⏵ Accept Edits") == "accept-edits"


# =========================================================================
# C. 真实 CLI 场景集成测试（来自 test_state_simulator.py）
# =========================================================================

# 模拟器使用的常量，与 test_state_simulator.py 保持一致
_SEP = "─" * 80
_MODE_ACCEPT = "  ⏵⏵ accept edits on (shift+tab to cycle) · esc to interrupt"
_MODE_PLAN = "  ⏸ plan mode on (shift+tab to cycle) · esc to interrupt"


def _cli_footer(mode: str = "accept") -> str:
    """真实 CLI 底部框架（空 ❯）。"""
    ml = _MODE_ACCEPT if mode == "accept" else _MODE_PLAN
    return f"\n{_SEP}\n❯\n{_SEP}\n{ml}"


def _cli_footer_inputting(text: str, mode: str = "accept") -> str:
    """真实 CLI 底部框架（❯ 后有文字）。"""
    ml = _MODE_ACCEPT if mode == "accept" else _MODE_PLAN
    return f"\n{_SEP}\n❯ {text}\n{_SEP}\n{ml}"


class TestRealCLIScenarios:
    """真实 Claude Code CLI 终端输出的集成测试。

    每个测试用例直接取自 test_state_simulator.py 中的模拟场景，
    确保 detect_claude_state() 对所有真实布局均能正确检测。
    """

    # ----- processing -----

    def test_sim_processing_thinking(self):
        """真实 CLI 布局：Thinking + cli_footer → processing。"""
        output = (
            "I'll help you implement this feature.\n"
            "\n"
            "Let me first look at the existing code structure.\n"
            "\n"
            f"✻ Thinking{_cli_footer()}"
        )
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert detail == "Thinking"

    def test_sim_processing_gallivanting(self):
        """真实 CLI 布局：Gallivanting… + cli_footer → processing。"""
        output = (
            "      332  complete -c mk -f -n \"__fish_seen\" -l dry-run\n"
            "      333\n"
            "      334  # config mirror reset --tool\n"
            "\n"
            f"✢ Gallivanting… (1m 43s · ↓ 6.4k tokens){_cli_footer()}"
        )
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert "Gallivanting" in detail

    def test_sim_processing_schlepping(self):
        """真实 CLI 布局：Schlepping… + 提示信息 + cli_footer → processing。"""
        output = (
            "⏺ Updated plan\n"
            "  ⎿  /plan to preview\n"
            "\n"
            "✢ Schlepping… (43s · ↑ 694 tokens · thinking)\n"
            "  ⎿  Tip: Did you know you can drag and drop image files into your terminal?"
            f"{_cli_footer()}"
        )
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert "Schlepping" in detail

    def test_sim_processing_unknown_spinner(self):
        """真实 CLI 布局：未知 spinner 文本 + cli_footer → processing。"""
        output = (
            "Looking through the codebase for relevant code.\n"
            "\n"
            f"✳ Searching for patterns in src/{_cli_footer()}"
        )
        state, detail = detect_claude_state(output)
        assert state == "processing"
        assert "Searching for patterns" in detail

    # ----- interactive -----

    def test_sim_interactive_prompt(self):
        """真实 CLI 布局：INTERACTIVE_PROMPT → interactive。"""
        output = (
            "I've analyzed the code and here's my plan:\n"
            "\n"
            "1. Refactor the authentication module\n"
            "2. Add unit tests for the new logic\n"
            "3. Update the API documentation\n"
            "\n"
            "Should I proceed?"
        )
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Should I proceed?"

    def test_sim_interactive_selection_menu(self):
        """真实 CLI 布局：❯ 选择菜单（╌╌╌ 分隔线）→ interactive。"""
        output = (
            "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌\n"
            "\n"
            " Claude has written up a plan and is ready to execute. Would you like to\n"
            " proceed?\n"
            "\n"
            " ❯ 1. Yes, clear context and auto-accept edits (shift+tab)\n"
            "   2. Yes, auto-accept edits\n"
            "   3. Yes, manually approve edits\n"
            "   4. Type here to tell Claude what to change\n"
            "\n"
            " ctrl-g to edit in Vim · ~/.claude/plans/example.md"
        )
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert "Yes" in detail

    def test_sim_interactive_simple_dual(self):
        """真实 CLI 布局：❯ 简单双条件确认 → interactive。"""
        output = (
            "I found two possible approaches.\n"
            "\n"
            "Which approach do you prefer?\n"
            "❯ Yes\n"
            "  No"
        )
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert detail == "Yes"

    def test_sim_interactive_exit_plan_mode(self):
        """真实 CLI 布局：Exit plan mode?（? 距 ❯ 4 行）→ interactive。"""
        output = (
            "────────────────────────────────────────────────────────────────────────────────\n"
            " Exit plan mode?\n"
            "\n"
            "  Claude wants to exit plan mode\n"
            "\n"
            "  ❯ 1. Yes\n"
            "    2. No"
        )
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert "Yes" in detail

    def test_sim_interactive_permission(self):
        """真实 CLI 布局：权限确认（B2 分隔线边界内有 ?）→ interactive。"""
        output = (
            "────────────────────────────────────────────────────────────────────────────────\n"
            " Allow tool Read to read /etc/hosts?\n"
            "\n"
            "  ❯ 1. Allow once\n"
            "    2. Allow always\n"
            "    3. Deny"
        )
        state, detail = detect_claude_state(output)
        assert state == "interactive"
        assert "Allow once" in detail

    # ----- idle (B2 阻断) -----

    def test_sim_idle_question_blocked_by_separator(self):
        """真实 CLI 布局：? 被分隔线阻断 → idle。"""
        output = (
            "Is this correct?\n"
            "────────────────────────────────────────────────────────────────────────────────\n"
            "Some context below separator\n"
            "❯ ls -la"
        )
        state, detail = detect_claude_state(output)
        assert state == "idle"

    # ----- completed -----

    def test_sim_completed_cogitated(self):
        """真实 CLI 布局：Cogitated + cli_footer → completed。"""
        output = f"✻ Cogitated for 1m 56s{_cli_footer()}"
        state, detail = detect_claude_state(output)
        assert state == "completed"
        assert detail == "Cogitated"

    def test_sim_completed_worked(self):
        """真实 CLI 布局：Worked + cli_footer → completed。"""
        output = (
            "I've finished implementing the feature.\n"
            "All changes have been saved.\n"
            "\n"
            f"✻ Worked{_cli_footer()}"
        )
        state, detail = detect_claude_state(output)
        assert state == "completed"
        assert detail == "Worked"

    # ----- inputting -----

    def test_sim_inputting_accept_mode(self):
        """真实 CLI 布局：用户输入（accept 模式）→ inputting。"""
        output = (
            "I've finished reviewing the code."
            f"{_cli_footer_inputting('implement the auth feature')}"
        )
        state, detail = detect_claude_state(output)
        assert state == "inputting"
        assert detail == "implement the auth feature"

    def test_sim_inputting_plan_mode(self):
        """真实 CLI 布局：用户输入（plan 模式）→ inputting。"""
        output = (
            "✻ Worked for 30s"
            f"{_cli_footer_inputting('fix the login bug', mode='plan')}"
        )
        state, detail = detect_claude_state(output)
        assert state == "inputting"
        assert detail == "fix the login bug"

    # ----- idle -----

    def test_sim_idle_bare_arrow_with_footer(self):
        """真实 CLI 布局：空 ❯ + 分隔线 + mode 行 → idle。"""
        output = (
            "Task completed successfully.\n"
            "\n"
            "All tests passed.\n"
            f"{_SEP}\n"
            "❯\n"
            f"{_SEP}\n"
            f"{_MODE_ACCEPT}"
        )
        state, detail = detect_claude_state(output)
        assert state == "idle"
        assert detail == ""

    def test_sim_idle_plain_text(self):
        """真实 CLI 布局：普通文本无任何指示符 → idle。"""
        output = (
            "Some regular terminal output here.\n"
            "This is just normal text with no special indicators.\n"
            "Nothing to detect in this output."
        )
        state, detail = detect_claude_state(output)
        assert state == "idle"
        assert detail == ""
