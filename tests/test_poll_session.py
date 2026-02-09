"""
Tests for StatusDetector._poll_session method.

Tests the output polling and stability tracking functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from terminalcp.status_detector import (
    StatusDetector,
    SessionState,
    TerminalState,
    TaskStatus,
)


class TestPollSession:
    """Test _poll_session method."""
    
    @pytest.mark.asyncio
    async def test_poll_session_output_changed_resets_stable_count(self):
        """Test that stable_count resets to 0 when output changes."""
        # Create mock terminal client
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="output line 1\noutput line 2")
        
        # Initialize StatusDetector
        detector = StatusDetector(mock_client)
        
        # Create a session state with non-zero stable_count
        session_id = "test-session-1"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        detector._session_states[session_id].stable_count = 5
        detector._session_states[session_id].last_output = "previous output"
        
        # Poll the session
        await detector._poll_session(session_id)
        
        # Verify stable_count was reset to 0
        assert detector._session_states[session_id].stable_count == 0
        
        # Verify last_output was updated
        assert detector._session_states[session_id].last_output != "previous output"
        
        # Verify output was cached
        assert session_id in detector._live_outputs
        assert detector._live_outputs[session_id] != "previous output"
    
    @pytest.mark.asyncio
    async def test_poll_session_output_unchanged_increments_stable_count(self):
        """Test that stable_count increments when output is unchanged."""
        # Create mock terminal client that returns the same output
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="same output")
        
        # Initialize StatusDetector
        detector = StatusDetector(mock_client)
        
        # Create a session state
        session_id = "test-session-2"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        detector._session_states[session_id].stable_count = 3
        
        # First poll to set last_output
        await detector._poll_session(session_id)
        initial_stable_count = detector._session_states[session_id].stable_count
        
        # Second poll with same output
        await detector._poll_session(session_id)
        
        # Verify stable_count was incremented
        assert detector._session_states[session_id].stable_count == initial_stable_count + 1
    
    @pytest.mark.asyncio
    async def test_poll_session_calls_stream_with_strip_ansi_false(self):
        """Test that _poll_session calls stream action with strip_ansi=False."""
        # Create mock terminal client
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="\x1b[32mgreen text\x1b[0m")
        
        # Initialize StatusDetector
        detector = StatusDetector(mock_client)
        
        # Create a session state
        session_id = "test-session-3"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # Poll the session
        await detector._poll_session(session_id)
        
        # Verify stream action was called with correct parameters
        mock_client.request.assert_called_once_with({
            "action": "stream",
            "id": session_id,
            "strip_ansi": False
        })
    
    @pytest.mark.asyncio
    async def test_poll_session_caches_rendered_output(self):
        """Test that _poll_session caches rendered output in _live_outputs."""
        # Create mock terminal client
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="test output")
        
        # Initialize StatusDetector
        detector = StatusDetector(mock_client)
        
        # Create a session state
        session_id = "test-session-4"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # Poll the session
        await detector._poll_session(session_id)
        
        # Verify output was cached
        assert session_id in detector._live_outputs
        # The output should start with "test output" (pyte may add newlines for terminal rendering)
        assert detector._live_outputs[session_id].startswith("test output")
    
    @pytest.mark.asyncio
    async def test_poll_session_creates_pyte_renderer_if_needed(self):
        """Test that _poll_session creates a PyteRenderer if one doesn't exist."""
        # Create mock terminal client
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="test output")
        
        # Initialize StatusDetector
        detector = StatusDetector(mock_client)
        
        # Create a session state
        session_id = "test-session-5"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # Verify no renderer exists yet
        assert session_id not in detector._pyte_renderers
        
        # Poll the session
        await detector._poll_session(session_id)
        
        # Verify renderer was created
        assert session_id in detector._pyte_renderers
    
    @pytest.mark.asyncio
    async def test_poll_session_raises_error_for_nonexistent_session(self):
        """Test that _poll_session raises RuntimeError for nonexistent session."""
        # Create mock terminal client
        mock_client = MagicMock()
        
        # Initialize StatusDetector
        detector = StatusDetector(mock_client)
        
        # Try to poll a nonexistent session
        with pytest.raises(RuntimeError, match="Session not found"):
            await detector._poll_session("nonexistent-session")
    
    @pytest.mark.asyncio
    async def test_poll_session_handles_stream_action_failure(self):
        """Test that _poll_session raises RuntimeError when stream action fails."""
        # Create mock terminal client that raises an exception
        mock_client = MagicMock()
        mock_client.request = AsyncMock(side_effect=Exception("Stream failed"))
        
        # Initialize StatusDetector
        detector = StatusDetector(mock_client)
        
        # Create a session state
        session_id = "test-session-6"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # Try to poll the session
        with pytest.raises(RuntimeError, match="Failed to get stream output"):
            await detector._poll_session(session_id)
    
    @pytest.mark.asyncio
    async def test_poll_session_multiple_cycles_with_changes(self):
        """Test multiple polling cycles with output changes."""
        # Create mock terminal client with changing output
        outputs = ["output 1", "output 2", "output 2", "output 3"]
        mock_client = MagicMock()
        mock_client.request = AsyncMock(side_effect=outputs)
        
        # Initialize StatusDetector
        detector = StatusDetector(mock_client)
        
        # Create a session state
        session_id = "test-session-7"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # First poll: output 1
        await detector._poll_session(session_id)
        assert detector._session_states[session_id].stable_count == 0
        assert detector._session_states[session_id].last_output.startswith("output 1")
        first_output = detector._session_states[session_id].last_output
        
        # Second poll: output 2 (changed)
        await detector._poll_session(session_id)
        assert detector._session_states[session_id].stable_count == 0
        assert detector._session_states[session_id].last_output.startswith("output 2")
        second_output = detector._session_states[session_id].last_output
        assert second_output != first_output
        
        # Third poll: output 2 (unchanged)
        await detector._poll_session(session_id)
        assert detector._session_states[session_id].stable_count == 1
        assert detector._session_states[session_id].last_output == second_output
        
        # Fourth poll: output 3 (changed)
        await detector._poll_session(session_id)
        assert detector._session_states[session_id].stable_count == 0
        assert detector._session_states[session_id].last_output.startswith("output 3")
    
    @pytest.mark.asyncio
    async def test_poll_session_with_ansi_sequences(self):
        """Test that _poll_session correctly renders ANSI sequences."""
        # Create mock terminal client with ANSI output
        mock_client = MagicMock()
        mock_client.request = AsyncMock(return_value="\x1b[32mGreen\x1b[0m \x1b[1mBold\x1b[0m")
        
        # Initialize StatusDetector
        detector = StatusDetector(mock_client)
        
        # Create a session state
        session_id = "test-session-8"
        detector._session_states[session_id] = SessionState(session_id=session_id)
        
        # Poll the session
        await detector._poll_session(session_id)
        
        # Verify output was rendered (ANSI codes removed)
        rendered = detector._live_outputs[session_id]
        assert "\x1b" not in rendered  # No ANSI escape sequences
        assert "Green" in rendered or "Bold" in rendered  # Text content preserved
