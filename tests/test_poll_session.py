"""
StatusDetector._poll_session 方法的测试。

测试输出轮询和稳定性跟踪功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from terminalcp.claude_status import (
    StatusDetector,
    SessionState,
    TerminalState,
    TaskStatus,
)


class TestPollSession:
    """测试 _poll_session 方法。"""
    
    @pytest.mark.asyncio
    async def test_poll_session_output_changed_resets_stable_count(self):
        """测试输出变化时 stable_count 重置为 0。"""
        # 创建模拟终端客户端
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="output line 1\noutput line 2")

        # 初始化 StatusDetector
        detector = StatusDetector(mock_client)

        # 创建一个 stable_count 非零的会话状态
        session_id = "test-session-1"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        detector._session_states[session_id].stable_count = 5
        detector._session_states[session_id].last_output = "previous output"
        
        # 轮询会话
        await detector._poll_session(session_id)

        # 验证 stable_count 已重置为 0
        assert detector._session_states[session_id].stable_count == 0

        # 验证 last_output 已更新
        assert detector._session_states[session_id].last_output != "previous output"

        # 验证输出已缓存
        assert session_id in detector._live_outputs
        assert detector._live_outputs[session_id] != "previous output"
    
    @pytest.mark.asyncio
    async def test_poll_session_output_unchanged_increments_stable_count(self):
        """测试输出未变化时 stable_count 递增。"""
        # 创建返回相同输出的模拟终端客户端
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="same output")

        # 初始化 StatusDetector
        detector = StatusDetector(mock_client)

        # 创建会话状态
        session_id = "test-session-2"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        detector._session_states[session_id].stable_count = 3
        
        # 首次轮询以设置 last_output
        await detector._poll_session(session_id)
        initial_stable_count = detector._session_states[session_id].stable_count

        # 使用相同输出进行第二次轮询
        await detector._poll_session(session_id)

        # 验证 stable_count 已递增
        assert detector._session_states[session_id].stable_count == initial_stable_count + 1
    
    @pytest.mark.asyncio
    async def test_poll_session_calls_stream_with_strip_ansi_false(self):
        """测试 _poll_session 调用 stream 操作时设置 strip_ansi=False。"""
        # 创建模拟终端客户端
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="\x1b[32mgreen text\x1b[0m")

        # 初始化 StatusDetector
        detector = StatusDetector(mock_client)

        # 创建会话状态
        session_id = "test-session-3"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # 轮询会话
        await detector._poll_session(session_id)

        # 验证 stream 操作使用了正确的参数
        mock_client.request.assert_called_once_with({
            "action": "stream",
            "id": session_id,
            "strip_ansi": False
        })
    
    @pytest.mark.asyncio
    async def test_poll_session_caches_rendered_output(self):
        """测试 _poll_session 将渲染输出缓存到 _live_outputs。"""
        # 创建模拟终端客户端
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="test output")

        # 初始化 StatusDetector
        detector = StatusDetector(mock_client)

        # 创建会话状态
        session_id = "test-session-4"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # 轮询会话
        await detector._poll_session(session_id)

        # 验证输出已缓存
        assert session_id in detector._live_outputs
        # 输出应以 "test output" 开头（pyte 可能会为终端渲染添加换行符）
        assert detector._live_outputs[session_id].startswith("test output")
    
    @pytest.mark.asyncio
    async def test_poll_session_creates_pyte_renderer_if_needed(self):
        """测试 _poll_session 在不存在渲染器时创建 PyteRenderer。"""
        # 创建模拟终端客户端
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="test output")

        # 初始化 StatusDetector
        detector = StatusDetector(mock_client)

        # 创建会话状态
        session_id = "test-session-5"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # 验证尚无渲染器
        assert session_id not in detector._pyte_renderers

        # 轮询会话
        await detector._poll_session(session_id)

        # 验证渲染器已创建
        assert session_id in detector._pyte_renderers
    
    @pytest.mark.asyncio
    async def test_poll_session_raises_error_for_nonexistent_session(self):
        """测试 _poll_session 对不存在的会话抛出 RuntimeError。"""
        # 创建模拟终端客户端
        mock_client = MagicMock()

        # 初始化 StatusDetector
        detector = StatusDetector(mock_client)

        # 尝试轮询不存在的会话
        with pytest.raises(RuntimeError, match="Session not found"):
            await detector._poll_session("nonexistent-session")
    
    @pytest.mark.asyncio
    async def test_poll_session_handles_stream_action_failure(self):
        """测试 stream 操作失败时 _poll_session 抛出 RuntimeError。"""
        # 创建抛出异常的模拟终端客户端
        mock_client = MagicMock()
        mock_client.request = AsyncMock(side_effect=Exception("Stream failed"))

        # 初始化 StatusDetector
        detector = StatusDetector(mock_client)

        # 创建会话状态
        session_id = "test-session-6"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # 尝试轮询会话
        with pytest.raises(RuntimeError, match="Failed to get stream output"):
            await detector._poll_session(session_id)
    
    @pytest.mark.asyncio
    async def test_poll_session_multiple_cycles_with_changes(self):
        """测试带输出变化的多次轮询周期。"""
        # 创建带变化输出的模拟终端客户端
        outputs = ["output 1", "output 2", "output 2", "output 3"]
        mock_client = MagicMock()
        mock_client.request = AsyncMock(side_effect=outputs)
        
        # 初始化 StatusDetector
        detector = StatusDetector(mock_client)

        # 创建会话状态
        session_id = "test-session-7"
        detector._session_states[session_id] = SessionState(session_id=session_id)

        # 第一次轮询：output 1
        await detector._poll_session(session_id)
        assert detector._session_states[session_id].stable_count == 0
        assert detector._session_states[session_id].last_output.startswith("output 1")
        first_output = detector._session_states[session_id].last_output
        
        # 第二次轮询：output 2（已变化）
        await detector._poll_session(session_id)
        assert detector._session_states[session_id].stable_count == 0
        assert detector._session_states[session_id].last_output.startswith("output 2")
        second_output = detector._session_states[session_id].last_output
        assert second_output != first_output
        
        # 第三次轮询：output 2（未变化）
        await detector._poll_session(session_id)
        assert detector._session_states[session_id].stable_count == 1
        assert detector._session_states[session_id].last_output == second_output
        
        # 第四次轮询：output 3（已变化）
        await detector._poll_session(session_id)
        assert detector._session_states[session_id].stable_count == 0
        assert detector._session_states[session_id].last_output.startswith("output 3")
    
    @pytest.mark.asyncio
    async def test_poll_session_with_ansi_sequences(self):
        """测试 _poll_session 正确渲染 ANSI 序列。"""
        # 创建带 ANSI 输出的模拟终端客户端
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="\x1b[32mGreen\x1b[0m \x1b[1mBold\x1b[0m")
        
        # 初始化 StatusDetector
        detector = StatusDetector(mock_client)

        # 创建会话状态
        session_id = "test-session-8"
        detector._session_states[session_id] = SessionState(session_id=session_id)

        # 轮询会话
        await detector._poll_session(session_id)

        # 验证输出已渲染（ANSI 码已移除）
        rendered = detector._live_outputs[session_id]
        assert "\x1b" not in rendered  # No ANSI escape sequences
        assert "Green" in rendered or "Bold" in rendered  # Text content preserved
