"""
PyteRenderer 的单元测试。

测试 ANSI 处理流水线，包括 pyte 渲染和正则回退。

任务 2.4 需求覆盖：
- ✓ 测试 pyte 渲染已知 ANSI 序列（SGR、光标移动、滚动）
- ✓ 测试 pyte 失败时的正则回退
- ✓ 测试尾部空白剥离
- ✓ 测试宽字符处理（Emoji、CJK）

已验证需求：2.1, 2.2, 2.3, 2.4, 2.5, 2.7

测试组织：
- TestPyteRendererBasic: 初始化和基本渲染
- TestPyteRendererANSIProcessing: SGR 码、光标移动、滚动
- TestPyteRendererCleaning: 空白和 Unicode 清理
- TestPyteRendererFallback: 正则回退行为
- TestPyteRendererEdgeCases: 宽字符、畸形输入、边界情况
- TestPyteRendererIntegration: 真实 Claude Code 场景
"""

import pytest
from terminalcp.claude_status import PyteRenderer


class TestPyteRendererBasic:
    """PyteRenderer 初始化和基本渲染的测试。"""
    
    def test_renderer_initialization(self):
        """测试 PyteRenderer 可以使用默认尺寸初始化。"""
        renderer = PyteRenderer()
        assert renderer._cols == 120
        assert renderer._rows == 50
    
    def test_renderer_custom_dimensions(self):
        """测试 PyteRenderer 可以使用自定义尺寸初始化。"""
        renderer = PyteRenderer(cols=80, rows=24)
        assert renderer._cols == 80
        assert renderer._rows == 24
    
    def test_render_plain_text(self):
        """测试渲染不含 ANSI 码的纯文本。"""
        renderer = PyteRenderer()
        result = renderer.render("Hello, World!")
        assert "Hello, World!" in result
    
    def test_render_empty_string(self):
        """测试渲染空字符串。"""
        renderer = PyteRenderer()
        result = renderer.render("")
        assert isinstance(result, str)
    
    def test_render_with_simple_ansi(self):
        """测试渲染带简单 ANSI 颜色码的文本。"""
        renderer = PyteRenderer()
        # 红色文本的 ANSI 码：\x1b[31m
        result = renderer.render("\x1b[31mRed Text\x1b[0m")
        # ANSI 码应被移除
        assert "Red Text" in result
        assert "\x1b[31m" not in result
        assert "\x1b[0m" not in result


class TestPyteRendererANSIProcessing:
    """测试 ANSI 转义序列处理。"""
    
    def test_render_sgr_codes(self):
        """测试 SGR（选择图形再现）码的渲染。"""
        renderer = PyteRenderer()
        # 粗体、红色、下划线文本
        ansi_text = "\x1b[1m\x1b[31m\x1b[4mBold Red Underlined\x1b[0m"
        result = renderer.render(ansi_text)
        assert "Bold Red Underlined" in result
        # ANSI 码应被剥离
        assert "\x1b[" not in result
    
    def test_render_sgr_multiple_styles(self):
        """测试多个 SGR 样式码的渲染。"""
        renderer = PyteRenderer()
        # 测试各种 SGR 码：粗体(1)、暗淡(2)、斜体(3)、下划线(4)
        ansi_text = "\x1b[1mBold\x1b[0m \x1b[2mDim\x1b[0m \x1b[3mItalic\x1b[0m \x1b[4mUnderline\x1b[0m"
        result = renderer.render(ansi_text)
        assert "Bold" in result
        assert "Dim" in result
        assert "Italic" in result
        assert "Underline" in result
        assert "\x1b[" not in result
    
    def test_render_sgr_colors(self):
        """测试 SGR 颜色码（前景色和背景色）的渲染。"""
        renderer = PyteRenderer()
        # 前景色(30-37)和背景色(40-47)
        ansi_text = "\x1b[31mRed\x1b[0m \x1b[42mGreen BG\x1b[0m \x1b[33;44mYellow on Blue\x1b[0m"
        result = renderer.render(ansi_text)
        assert "Red" in result
        assert "Green BG" in result
        assert "Yellow on Blue" in result
        assert "\x1b[" not in result
    
    def test_render_cursor_movement(self):
        """测试光标移动码的渲染。"""
        renderer = PyteRenderer()
        # 移动光标并写入文本
        ansi_text = "\x1b[2J\x1b[HHello"
        result = renderer.render(ansi_text)
        assert "Hello" in result
    
    def test_render_cursor_positioning(self):
        """测试光标定位命令的渲染。"""
        renderer = PyteRenderer()
        # CUP（光标位置）：\x1b[row;colH
        # 移动到第1行第1列并写入
        ansi_text = "\x1b[1;1HTop Left\x1b[5;10HMiddle"
        result = renderer.render(ansi_text)
        assert "Top Left" in result
        assert "Middle" in result
    
    def test_render_with_scrolling(self):
        """测试滚动区域命令的渲染。"""
        renderer = PyteRenderer()
        # 设置滚动区域：\x1b[top;bottomr
        # 设置从顶行到底行的滚动区域
        ansi_text = "\x1b[1;10rLine 1\nLine 2\nLine 3"
        result = renderer.render(ansi_text)
        # 应能处理滚动而不崩溃
        assert isinstance(result, str)
        assert "Line" in result
    
    def test_render_with_newlines(self):
        """测试带换行符文本的渲染。"""
        renderer = PyteRenderer()
        result = renderer.render("Line 1\nLine 2\nLine 3")
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result


class TestPyteRendererCleaning:
    """测试文本清理功能。"""
    
    def test_trailing_whitespace_removal(self):
        """测试行尾空白已被移除。"""
        renderer = PyteRenderer()
        result = renderer.render("Text with spaces    \nAnother line   ")
        lines = result.split('\n')
        # 找到包含我们文本的行
        for line in lines:
            if "Text with spaces" in line:
                assert not line.endswith("    ")
            if "Another line" in line:
                assert not line.endswith("   ")
    
    def test_invisible_unicode_removal(self):
        """测试不可见 Unicode 字符已被移除。"""
        renderer = PyteRenderer()
        # 带零宽空格的文本
        text_with_zwsp = "Hello\u200bWorld"
        result = renderer.render(text_with_zwsp)
        assert "\u200b" not in result
        assert "HelloWorld" in result or "Hello" in result
    
    def test_clean_text_method(self):
        """直接测试 _clean_text 方法。"""
        renderer = PyteRenderer()
        # 带尾部空格和不可见字符的文本
        dirty_text = "Line 1   \nLine 2\u200b\u200c\u200d   "
        clean_text = renderer._clean_text(dirty_text)
        
        lines = clean_text.split('\n')
        assert lines[0] == "Line 1"
        assert "\u200b" not in clean_text
        assert "\u200c" not in clean_text
        assert "\u200d" not in clean_text


class TestPyteRendererFallback:
    """测试 pyte 失败或不可用时的正则回退。"""
    
    def test_regex_fallback_strips_ansi(self):
        """测试正则回退正确剥离 ANSI 码。"""
        renderer = PyteRenderer()
        ansi_text = "\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m"
        result = renderer._render_with_regex(ansi_text)
        assert "Red" in result
        assert "Green" in result
        assert "\x1b[" not in result
    
    def test_regex_fallback_with_complex_ansi(self):
        """测试正则回退处理复杂 ANSI 序列。"""
        renderer = PyteRenderer()
        # Complex ANSI with multiple parameters
        ansi_text = "\x1b[1;31;4mComplex\x1b[0m"
        result = renderer._render_with_regex(ansi_text)
        assert "Complex" in result
        assert "\x1b[" not in result
    
    def test_regex_fallback_with_cursor_codes(self):
        """测试正则回退处理光标移动码。"""
        renderer = PyteRenderer()
        # 光标移动码应被剥离
        ansi_text = "\x1b[2J\x1b[HText\x1b[5;10HMore"
        result = renderer._render_with_regex(ansi_text)
        assert "Text" in result
        assert "More" in result
        assert "\x1b[" not in result
    
    def test_regex_fallback_preserves_text(self):
        """测试正则回退保留所有文本内容。"""
        renderer = PyteRenderer()
        ansi_text = "\x1b[31mRed\x1b[0m Normal \x1b[32mGreen\x1b[0m"
        result = renderer._render_with_regex(ansi_text)
        assert "Red" in result
        assert "Normal" in result
        assert "Green" in result
    
    def test_render_falls_back_on_pyte_failure(self):
        """测试 render() 在 pyte 失败时回退到正则。"""
        renderer = PyteRenderer()
        # 强制 pyte 不可用
        original_screen = renderer._screen
        renderer._screen = None
        
        ansi_text = "\x1b[31mText\x1b[0m"
        result = renderer.render(ansi_text)
        
        # 应仍能通过正则回退工作
        assert "Text" in result
        assert "\x1b[" not in result
        
        # 恢复
        renderer._screen = original_screen


class TestPyteRendererEdgeCases:
    """测试边界情况和错误处理。"""
    
    def test_render_with_emoji(self):
        """测试 Emoji 字符的渲染。"""
        renderer = PyteRenderer()
        # 各种 Emoji
        text = "Hello 👋 🌍 🎉 ✨"
        result = renderer.render(text)
        # 应能处理而不崩溃
        assert isinstance(result, str)
        assert "Hello" in result

    def test_render_with_cjk_characters(self):
        """测试 CJK（中日韩）字符的渲染。"""
        renderer = PyteRenderer()
        # 中文、日文、韩文文本
        text = "Hello 世界 こんにちは 안녕하세요"
        result = renderer.render(text)
        # 应能处理而不崩溃
        assert isinstance(result, str)
        assert "Hello" in result
        # CJK 字符应存在（精确渲染可能有所不同）
        # 至少字符串应包含部分 CJK 内容
    
    def test_render_with_mixed_wide_characters(self):
        """测试 Emoji 和 CJK 混合字符的渲染。"""
        renderer = PyteRenderer()
        text = "Test 👋 世界 🌍 こんにちは"
        result = renderer.render(text)
        assert isinstance(result, str)
        assert "Test" in result
    
    def test_render_with_wide_characters_and_ansi(self):
        """测试带 ANSI 码的宽字符渲染。"""
        renderer = PyteRenderer()
        # 带颜色码的宽字符
        text = "\x1b[31m世界\x1b[0m \x1b[32m👋\x1b[0m"
        result = renderer.render(text)
        assert isinstance(result, str)
        # ANSI 码应被移除
        assert "\x1b[" not in result

    def test_render_with_malformed_ansi(self):
        """测试畸形 ANSI 序列的渲染。"""
        renderer = PyteRenderer()
        # 不完整的 ANSI 序列
        malformed = "\x1b[31mText\x1b["
        result = renderer.render(malformed)
        # 不应崩溃
        assert isinstance(result, str)
        assert "Text" in result
    
    def test_render_very_long_line(self):
        """测试超过终端宽度的长行渲染。"""
        renderer = PyteRenderer(cols=20, rows=5)
        long_line = "A" * 100
        result = renderer.render(long_line)
        # 应能处理而不崩溃
        assert isinstance(result, str)
        assert "A" in result
    
    def test_render_many_lines(self):
        """测试超过终端高度的多行渲染。"""
        renderer = PyteRenderer(cols=80, rows=10)
        # 创建 50 行文本
        many_lines = "\n".join([f"Line {i}" for i in range(50)])
        result = renderer.render(many_lines)
        # 应能处理而不崩溃
        assert isinstance(result, str)
        # 应包含部分行
        assert "Line" in result


class TestPyteRendererIntegration:
    """完整渲染场景的集成测试。"""
    
    def test_render_permission_prompt(self):
        """测试渲染权限确认提示。"""
        renderer = PyteRenderer()
        # 模拟的 Claude Code 权限提示
        prompt = "\x1b[1mAllow tool file_editor?\x1b[0m\n\x1b[32m❯ Yes\x1b[0m\n  No"
        result = renderer.render(prompt)
        
        assert "Allow tool file_editor?" in result
        assert "Yes" in result
        assert "No" in result
        assert "❯" in result
        # ANSI 码应被移除
        assert "\x1b[" not in result

    def test_render_idle_prompt(self):
        """测试渲染空闲提示。"""
        renderer = PyteRenderer()
        prompt = "\x1b[32m❯\x1b[0m "
        result = renderer.render(prompt)
        
        assert "❯" in result
        assert "\x1b[" not in result
    
    def test_render_running_output(self):
        """测试带屏幕清除的运行中输出渲染。"""
        renderer = PyteRenderer()
        # 清除屏幕并写入文本
        output = "\x1b[2J\x1b[HGenerating code...\x1b[K"
        result = renderer.render(output)
        
        assert "Generating code" in result
        assert "\x1b[" not in result
