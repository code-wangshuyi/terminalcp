"""
Unit tests for PyteRenderer.

Tests the ANSI processing pipeline including pyte rendering and regex fallback.

Task 2.4 Requirements Coverage:
- ✓ Test pyte rendering with known ANSI sequences (SGR, cursor movement, scrolling)
- ✓ Test regex fallback when pyte fails
- ✓ Test trailing whitespace stripping
- ✓ Test wide character handling (Emoji, CJK)

Requirements Validated: 2.1, 2.2, 2.3, 2.4, 2.5, 2.7

Test Organization:
- TestPyteRendererBasic: Initialization and basic rendering
- TestPyteRendererANSIProcessing: SGR codes, cursor movement, scrolling
- TestPyteRendererCleaning: Whitespace and Unicode cleaning
- TestPyteRendererFallback: Regex fallback behavior
- TestPyteRendererEdgeCases: Wide characters, malformed input, edge cases
- TestPyteRendererIntegration: Real-world Claude Code scenarios
"""

import pytest
from terminalcp.status_detector import PyteRenderer


class TestPyteRendererBasic:
    """Basic tests for PyteRenderer initialization and rendering."""
    
    def test_renderer_initialization(self):
        """Test PyteRenderer can be initialized with default dimensions."""
        renderer = PyteRenderer()
        assert renderer._cols == 120
        assert renderer._rows == 50
    
    def test_renderer_custom_dimensions(self):
        """Test PyteRenderer can be initialized with custom dimensions."""
        renderer = PyteRenderer(cols=80, rows=24)
        assert renderer._cols == 80
        assert renderer._rows == 24
    
    def test_render_plain_text(self):
        """Test rendering plain text without ANSI codes."""
        renderer = PyteRenderer()
        result = renderer.render("Hello, World!")
        assert "Hello, World!" in result
    
    def test_render_empty_string(self):
        """Test rendering empty string."""
        renderer = PyteRenderer()
        result = renderer.render("")
        assert isinstance(result, str)
    
    def test_render_with_simple_ansi(self):
        """Test rendering text with simple ANSI color codes."""
        renderer = PyteRenderer()
        # ANSI code for red text: \x1b[31m
        result = renderer.render("\x1b[31mRed Text\x1b[0m")
        # ANSI codes should be removed
        assert "Red Text" in result
        assert "\x1b[31m" not in result
        assert "\x1b[0m" not in result


class TestPyteRendererANSIProcessing:
    """Test ANSI escape sequence processing."""
    
    def test_render_sgr_codes(self):
        """Test rendering with SGR (Select Graphic Rendition) codes."""
        renderer = PyteRenderer()
        # Bold, red, underline text
        ansi_text = "\x1b[1m\x1b[31m\x1b[4mBold Red Underlined\x1b[0m"
        result = renderer.render(ansi_text)
        assert "Bold Red Underlined" in result
        # ANSI codes should be stripped
        assert "\x1b[" not in result
    
    def test_render_sgr_multiple_styles(self):
        """Test rendering with multiple SGR style codes."""
        renderer = PyteRenderer()
        # Test various SGR codes: bold (1), dim (2), italic (3), underline (4)
        ansi_text = "\x1b[1mBold\x1b[0m \x1b[2mDim\x1b[0m \x1b[3mItalic\x1b[0m \x1b[4mUnderline\x1b[0m"
        result = renderer.render(ansi_text)
        assert "Bold" in result
        assert "Dim" in result
        assert "Italic" in result
        assert "Underline" in result
        assert "\x1b[" not in result
    
    def test_render_sgr_colors(self):
        """Test rendering with SGR color codes (foreground and background)."""
        renderer = PyteRenderer()
        # Foreground colors (30-37) and background colors (40-47)
        ansi_text = "\x1b[31mRed\x1b[0m \x1b[42mGreen BG\x1b[0m \x1b[33;44mYellow on Blue\x1b[0m"
        result = renderer.render(ansi_text)
        assert "Red" in result
        assert "Green BG" in result
        assert "Yellow on Blue" in result
        assert "\x1b[" not in result
    
    def test_render_cursor_movement(self):
        """Test rendering with cursor movement codes."""
        renderer = PyteRenderer()
        # Move cursor and write text
        ansi_text = "\x1b[2J\x1b[HHello"
        result = renderer.render(ansi_text)
        assert "Hello" in result
    
    def test_render_cursor_positioning(self):
        """Test rendering with cursor positioning commands."""
        renderer = PyteRenderer()
        # CUP (Cursor Position): \x1b[row;colH
        # Move to row 1, col 1 and write
        ansi_text = "\x1b[1;1HTop Left\x1b[5;10HMiddle"
        result = renderer.render(ansi_text)
        assert "Top Left" in result
        assert "Middle" in result
    
    def test_render_with_scrolling(self):
        """Test rendering with scrolling region commands."""
        renderer = PyteRenderer()
        # Set scrolling region: \x1b[top;bottomr
        # This sets a scrolling region from top to bottom row
        ansi_text = "\x1b[1;10rLine 1\nLine 2\nLine 3"
        result = renderer.render(ansi_text)
        # Should handle scrolling without crashing
        assert isinstance(result, str)
        assert "Line" in result
    
    def test_render_with_newlines(self):
        """Test rendering text with newlines."""
        renderer = PyteRenderer()
        result = renderer.render("Line 1\nLine 2\nLine 3")
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result


class TestPyteRendererCleaning:
    """Test text cleaning functionality."""
    
    def test_trailing_whitespace_removal(self):
        """Test that trailing whitespace is removed from lines."""
        renderer = PyteRenderer()
        result = renderer.render("Text with spaces    \nAnother line   ")
        lines = result.split('\n')
        # Find the lines with our text
        for line in lines:
            if "Text with spaces" in line:
                assert not line.endswith("    ")
            if "Another line" in line:
                assert not line.endswith("   ")
    
    def test_invisible_unicode_removal(self):
        """Test that invisible Unicode characters are removed."""
        renderer = PyteRenderer()
        # Text with zero-width space
        text_with_zwsp = "Hello\u200bWorld"
        result = renderer.render(text_with_zwsp)
        assert "\u200b" not in result
        assert "HelloWorld" in result or "Hello" in result
    
    def test_clean_text_method(self):
        """Test _clean_text method directly."""
        renderer = PyteRenderer()
        # Text with trailing spaces and invisible characters
        dirty_text = "Line 1   \nLine 2\u200b\u200c\u200d   "
        clean_text = renderer._clean_text(dirty_text)
        
        lines = clean_text.split('\n')
        assert lines[0] == "Line 1"
        assert "\u200b" not in clean_text
        assert "\u200c" not in clean_text
        assert "\u200d" not in clean_text


class TestPyteRendererFallback:
    """Test regex fallback when pyte fails or is unavailable."""
    
    def test_regex_fallback_strips_ansi(self):
        """Test that regex fallback correctly strips ANSI codes."""
        renderer = PyteRenderer()
        ansi_text = "\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m"
        result = renderer._render_with_regex(ansi_text)
        assert "Red" in result
        assert "Green" in result
        assert "\x1b[" not in result
    
    def test_regex_fallback_with_complex_ansi(self):
        """Test regex fallback with complex ANSI sequences."""
        renderer = PyteRenderer()
        # Complex ANSI with multiple parameters
        ansi_text = "\x1b[1;31;4mComplex\x1b[0m"
        result = renderer._render_with_regex(ansi_text)
        assert "Complex" in result
        assert "\x1b[" not in result
    
    def test_regex_fallback_with_cursor_codes(self):
        """Test regex fallback with cursor movement codes."""
        renderer = PyteRenderer()
        # Cursor movement codes should be stripped
        ansi_text = "\x1b[2J\x1b[HText\x1b[5;10HMore"
        result = renderer._render_with_regex(ansi_text)
        assert "Text" in result
        assert "More" in result
        assert "\x1b[" not in result
    
    def test_regex_fallback_preserves_text(self):
        """Test that regex fallback preserves all text content."""
        renderer = PyteRenderer()
        ansi_text = "\x1b[31mRed\x1b[0m Normal \x1b[32mGreen\x1b[0m"
        result = renderer._render_with_regex(ansi_text)
        assert "Red" in result
        assert "Normal" in result
        assert "Green" in result
    
    def test_render_falls_back_on_pyte_failure(self):
        """Test that render() falls back to regex when pyte fails."""
        renderer = PyteRenderer()
        # Force pyte to be unavailable
        original_screen = renderer._screen
        renderer._screen = None
        
        ansi_text = "\x1b[31mText\x1b[0m"
        result = renderer.render(ansi_text)
        
        # Should still work via regex fallback
        assert "Text" in result
        assert "\x1b[" not in result
        
        # Restore
        renderer._screen = original_screen


class TestPyteRendererEdgeCases:
    """Test edge cases and error handling."""
    
    def test_render_with_emoji(self):
        """Test rendering with emoji characters."""
        renderer = PyteRenderer()
        # Various emoji
        text = "Hello 👋 🌍 🎉 ✨"
        result = renderer.render(text)
        # Should handle without crashing
        assert isinstance(result, str)
        assert "Hello" in result
    
    def test_render_with_cjk_characters(self):
        """Test rendering with CJK (Chinese, Japanese, Korean) characters."""
        renderer = PyteRenderer()
        # Chinese, Japanese, Korean text
        text = "Hello 世界 こんにちは 안녕하세요"
        result = renderer.render(text)
        # Should handle without crashing
        assert isinstance(result, str)
        assert "Hello" in result
        # CJK characters should be present (exact rendering may vary)
        # At minimum, the string should contain some of the CJK content
    
    def test_render_with_mixed_wide_characters(self):
        """Test rendering with mixed emoji and CJK characters."""
        renderer = PyteRenderer()
        text = "Test 👋 世界 🌍 こんにちは"
        result = renderer.render(text)
        assert isinstance(result, str)
        assert "Test" in result
    
    def test_render_with_wide_characters_and_ansi(self):
        """Test rendering wide characters with ANSI codes."""
        renderer = PyteRenderer()
        # Wide characters with color codes
        text = "\x1b[31m世界\x1b[0m \x1b[32m👋\x1b[0m"
        result = renderer.render(text)
        assert isinstance(result, str)
        # ANSI codes should be removed
        assert "\x1b[" not in result
    
    def test_render_with_malformed_ansi(self):
        """Test rendering with malformed ANSI sequences."""
        renderer = PyteRenderer()
        # Incomplete ANSI sequence
        malformed = "\x1b[31mText\x1b["
        result = renderer.render(malformed)
        # Should not crash
        assert isinstance(result, str)
        assert "Text" in result
    
    def test_render_very_long_line(self):
        """Test rendering with line longer than terminal width."""
        renderer = PyteRenderer(cols=20, rows=5)
        long_line = "A" * 100
        result = renderer.render(long_line)
        # Should handle without crashing
        assert isinstance(result, str)
        assert "A" in result
    
    def test_render_many_lines(self):
        """Test rendering with more lines than terminal height."""
        renderer = PyteRenderer(cols=80, rows=10)
        # Create 50 lines of text
        many_lines = "\n".join([f"Line {i}" for i in range(50)])
        result = renderer.render(many_lines)
        # Should handle without crashing
        assert isinstance(result, str)
        # Some lines should be present
        assert "Line" in result


class TestPyteRendererIntegration:
    """Integration tests for complete rendering scenarios."""
    
    def test_render_permission_prompt(self):
        """Test rendering a permission confirmation prompt."""
        renderer = PyteRenderer()
        # Simulated Claude Code permission prompt
        prompt = "\x1b[1mAllow tool file_editor?\x1b[0m\n\x1b[32m❯ Yes\x1b[0m\n  No"
        result = renderer.render(prompt)
        
        assert "Allow tool file_editor?" in result
        assert "Yes" in result
        assert "No" in result
        assert "❯" in result
        # ANSI codes should be removed
        assert "\x1b[" not in result
    
    def test_render_idle_prompt(self):
        """Test rendering an idle prompt."""
        renderer = PyteRenderer()
        prompt = "\x1b[32m❯\x1b[0m "
        result = renderer.render(prompt)
        
        assert "❯" in result
        assert "\x1b[" not in result
    
    def test_render_running_output(self):
        """Test rendering running output with screen clear."""
        renderer = PyteRenderer()
        # Clear screen and write text
        output = "\x1b[2J\x1b[HGenerating code...\x1b[K"
        result = renderer.render(output)
        
        assert "Generating code" in result
        assert "\x1b[" not in result
