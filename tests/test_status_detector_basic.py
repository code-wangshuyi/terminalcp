"""
Basic tests for status_detector data structures and enums.

Tests the core data structures defined in status_detector.py to ensure
they are properly defined and can be instantiated correctly.
"""

import pytest
from datetime import datetime, timezone
from terminalcp.status_detector import (
    TerminalState,
    TaskStatus,
    InteractionType,
    TimingInfo,
    StatusDetail,
    StatusResponse,
    InteractionMatch,
    InteractionPattern,
    SessionState,
)


class TestEnums:
    """Test enum definitions."""
    
    def test_terminal_state_values(self):
        """Test TerminalState enum has correct values."""
        assert TerminalState.RUNNING.value == "running"
        assert TerminalState.INTERACTIVE.value == "interactive"
        assert TerminalState.COMPLETED.value == "completed"
    
    def test_task_status_values(self):
        """Test TaskStatus enum has correct values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.WAITING_FOR_INPUT.value == "waiting_for_input"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
    
    def test_interaction_type_values(self):
        """Test InteractionType enum has correct values."""
        assert InteractionType.PERMISSION_CONFIRM.value == "permission_confirm"
        assert InteractionType.HIGHLIGHTED_OPTION.value == "highlighted_option"
        assert InteractionType.PLAN_APPROVAL.value == "plan_approval"
        assert InteractionType.USER_QUESTION.value == "user_question"
        assert InteractionType.SELECTION_MENU.value == "selection_menu"


class TestTimingInfo:
    """Test TimingInfo dataclass."""
    
    def test_timing_info_creation(self):
        """Test TimingInfo can be created with all fields."""
        timing = TimingInfo(
            started_at="2026-02-09T10:30:00Z",
            completed_at="2026-02-09T10:30:45Z",
            duration_seconds=45.2
        )
        assert timing.started_at == "2026-02-09T10:30:00Z"
        assert timing.completed_at == "2026-02-09T10:30:45Z"
        assert timing.duration_seconds == 45.2
    
    def test_timing_info_defaults(self):
        """Test TimingInfo defaults to None for all fields."""
        timing = TimingInfo()
        assert timing.started_at is None
        assert timing.completed_at is None
        assert timing.duration_seconds is None
    
    def test_timing_info_to_dict(self):
        """Test TimingInfo.to_dict() returns correct dictionary."""
        timing = TimingInfo(
            started_at="2026-02-09T10:30:00Z",
            completed_at="2026-02-09T10:30:45Z",
            duration_seconds=45.2
        )
        result = timing.to_dict()
        assert result == {
            "started_at": "2026-02-09T10:30:00Z",
            "completed_at": "2026-02-09T10:30:45Z",
            "duration_seconds": 45.2
        }


class TestStatusDetail:
    """Test StatusDetail dataclass."""
    
    def test_status_detail_creation(self):
        """Test StatusDetail can be created with all fields."""
        detail = StatusDetail(
            description="Waiting for permission",
            interaction_type="permission_confirm",
            choices=["Yes", "No"]
        )
        assert detail.description == "Waiting for permission"
        assert detail.interaction_type == "permission_confirm"
        assert detail.choices == ["Yes", "No"]
    
    def test_status_detail_defaults(self):
        """Test StatusDetail defaults for optional fields."""
        detail = StatusDetail(description="Running")
        assert detail.description == "Running"
        assert detail.interaction_type is None
        assert detail.choices is None
    
    def test_status_detail_to_dict(self):
        """Test StatusDetail.to_dict() returns correct dictionary."""
        detail = StatusDetail(
            description="Waiting for permission",
            interaction_type="permission_confirm",
            choices=["Yes", "No"]
        )
        result = detail.to_dict()
        assert result == {
            "description": "Waiting for permission",
            "interaction_type": "permission_confirm",
            "choices": ["Yes", "No"]
        }


class TestStatusResponse:
    """Test StatusResponse dataclass."""
    
    def test_status_response_creation(self):
        """Test StatusResponse can be created with all fields."""
        timing = TimingInfo(started_at="2026-02-09T10:30:00Z")
        detail = StatusDetail(description="Running")
        response = StatusResponse(
            terminal_state=TerminalState.RUNNING,
            task_status=TaskStatus.RUNNING,
            stable_count=0,
            detail=detail,
            timing=timing
        )
        assert response.terminal_state == TerminalState.RUNNING
        assert response.task_status == TaskStatus.RUNNING
        assert response.stable_count == 0
        assert response.detail == detail
        assert response.timing == timing
    
    def test_status_response_to_dict(self):
        """Test StatusResponse.to_dict() returns correct dictionary."""
        timing = TimingInfo(started_at="2026-02-09T10:30:00Z")
        detail = StatusDetail(description="Running")
        response = StatusResponse(
            terminal_state=TerminalState.RUNNING,
            task_status=TaskStatus.RUNNING,
            stable_count=0,
            detail=detail,
            timing=timing
        )
        result = response.to_dict()
        assert result["terminal_state"] == "running"
        assert result["task_status"] == "running"
        assert result["stable_count"] == 0
        assert result["detail"]["description"] == "Running"
        assert result["timing"]["started_at"] == "2026-02-09T10:30:00Z"
    
    def test_status_response_to_json(self):
        """Test StatusResponse.to_json() returns valid JSON string."""
        timing = TimingInfo(started_at="2026-02-09T10:30:00Z")
        detail = StatusDetail(description="Running")
        response = StatusResponse(
            terminal_state=TerminalState.RUNNING,
            task_status=TaskStatus.RUNNING,
            stable_count=0,
            detail=detail,
            timing=timing
        )
        json_str = response.to_json()
        assert isinstance(json_str, str)
        assert "running" in json_str
        assert "2026-02-09T10:30:00Z" in json_str


class TestInteractionMatch:
    """Test InteractionMatch dataclass."""
    
    def test_interaction_match_creation(self):
        """Test InteractionMatch can be created with all fields."""
        match = InteractionMatch(
            interaction_type=InteractionType.PERMISSION_CONFIRM,
            choices=["Yes", "No"],
            matched_text="Allow tool file_editor? Yes/No"
        )
        assert match.interaction_type == InteractionType.PERMISSION_CONFIRM
        assert match.choices == ["Yes", "No"]
        assert match.matched_text == "Allow tool file_editor? Yes/No"


class TestInteractionPattern:
    """Test InteractionPattern dataclass."""
    
    def test_interaction_pattern_creation(self):
        """Test InteractionPattern can be created with all fields."""
        import re
        pattern = InteractionPattern(
            interaction_type=InteractionType.PERMISSION_CONFIRM,
            pattern=re.compile(r"Allow\s+tool"),
            priority=1
        )
        assert pattern.interaction_type == InteractionType.PERMISSION_CONFIRM
        assert pattern.pattern.pattern == r"Allow\s+tool"
        assert pattern.priority == 1


class TestSessionState:
    """Test SessionState dataclass."""
    
    def test_session_state_creation(self):
        """Test SessionState can be created with required fields."""
        state = SessionState(session_id="test-123")
        assert state.session_id == "test-123"
        assert state.terminal_state == TerminalState.RUNNING
        assert state.task_status == TaskStatus.PENDING
        assert state.stable_count == 0
        assert state.last_output == ""
        assert state.interaction_type is None
        assert state.choices is None
        assert state.started_at is None
        assert state.completed_at is None
        assert state.auto_response_count == 0
        assert state.description == "Session initialized"
    
    def test_format_timestamp_with_timezone(self):
        """Test format_timestamp with timezone-aware datetime."""
        state = SessionState(session_id="test-123")
        dt = datetime(2026, 2, 9, 10, 30, 0, tzinfo=timezone.utc)
        result = state.format_timestamp(dt)
        assert result == "2026-02-09T10:30:00+00:00"
    
    def test_format_timestamp_without_timezone(self):
        """Test format_timestamp adds UTC timezone if missing."""
        state = SessionState(session_id="test-123")
        dt = datetime(2026, 2, 9, 10, 30, 0)
        result = state.format_timestamp(dt)
        assert result == "2026-02-09T10:30:00+00:00"
    
    def test_format_timestamp_none(self):
        """Test format_timestamp returns None for None input."""
        state = SessionState(session_id="test-123")
        result = state.format_timestamp(None)
        assert result is None
    
    def test_calculate_duration(self):
        """Test calculate_duration returns correct duration in seconds."""
        state = SessionState(session_id="test-123")
        state.started_at = datetime(2026, 2, 9, 10, 30, 0, tzinfo=timezone.utc)
        state.completed_at = datetime(2026, 2, 9, 10, 30, 45, tzinfo=timezone.utc)
        duration = state.calculate_duration()
        assert duration == 45.0
    
    def test_calculate_duration_with_fractional_seconds(self):
        """Test calculate_duration handles fractional seconds."""
        state = SessionState(session_id="test-123")
        state.started_at = datetime(2026, 2, 9, 10, 30, 0, 200000, tzinfo=timezone.utc)
        state.completed_at = datetime(2026, 2, 9, 10, 30, 45, 400000, tzinfo=timezone.utc)
        duration = state.calculate_duration()
        assert duration == pytest.approx(45.2, rel=0.01)
    
    def test_calculate_duration_none_started(self):
        """Test calculate_duration returns None if started_at is None."""
        state = SessionState(session_id="test-123")
        state.completed_at = datetime(2026, 2, 9, 10, 30, 45, tzinfo=timezone.utc)
        duration = state.calculate_duration()
        assert duration is None
    
    def test_calculate_duration_none_completed(self):
        """Test calculate_duration returns None if completed_at is None."""
        state = SessionState(session_id="test-123")
        state.started_at = datetime(2026, 2, 9, 10, 30, 0, tzinfo=timezone.utc)
        duration = state.calculate_duration()
        assert duration is None
    
    def test_to_status_response(self):
        """Test to_status_response creates correct StatusResponse."""
        state = SessionState(session_id="test-123")
        state.terminal_state = TerminalState.INTERACTIVE
        state.task_status = TaskStatus.WAITING_FOR_INPUT
        state.stable_count = 3
        state.description = "Waiting for permission"
        state.interaction_type = InteractionType.PERMISSION_CONFIRM
        state.choices = ["Yes", "No"]
        state.started_at = datetime(2026, 2, 9, 10, 30, 0, tzinfo=timezone.utc)
        
        response = state.to_status_response()
        
        assert response.terminal_state == TerminalState.INTERACTIVE
        assert response.task_status == TaskStatus.WAITING_FOR_INPUT
        assert response.stable_count == 3
        assert response.detail.description == "Waiting for permission"
        assert response.detail.interaction_type == "permission_confirm"
        assert response.detail.choices == ["Yes", "No"]
        assert response.timing.started_at == "2026-02-09T10:30:00+00:00"
        assert response.timing.completed_at is None
        assert response.timing.duration_seconds is None
    
    def test_to_status_response_with_completion(self):
        """Test to_status_response with completed state."""
        state = SessionState(session_id="test-123")
        state.terminal_state = TerminalState.COMPLETED
        state.task_status = TaskStatus.COMPLETED
        state.stable_count = 8
        state.description = "Task completed"
        state.started_at = datetime(2026, 2, 9, 10, 30, 0, tzinfo=timezone.utc)
        state.completed_at = datetime(2026, 2, 9, 10, 30, 45, tzinfo=timezone.utc)
        
        response = state.to_status_response()
        
        assert response.terminal_state == TerminalState.COMPLETED
        assert response.task_status == TaskStatus.COMPLETED
        assert response.timing.started_at == "2026-02-09T10:30:00+00:00"
        assert response.timing.completed_at == "2026-02-09T10:30:45+00:00"
        assert response.timing.duration_seconds == 45.0



class TestStatusDetector:
    """Test StatusDetector class initialization."""
    
    def test_status_detector_initialization(self):
        """Test StatusDetector can be initialized with TerminalClient."""
        from terminalcp.status_detector import StatusDetector
        from terminalcp.terminal_client import TerminalClient
        
        # Create a mock terminal client
        client = TerminalClient()
        
        # Initialize StatusDetector
        detector = StatusDetector(client)
        
        # Verify initialization
        assert detector._client is client
        assert isinstance(detector._session_states, dict)
        assert len(detector._session_states) == 0
        assert isinstance(detector._live_outputs, dict)
        assert len(detector._live_outputs) == 0
        assert isinstance(detector._pyte_renderers, dict)
        assert len(detector._pyte_renderers) == 0
        assert detector._terminal_detector is not None
        assert detector._polling_interval == 1.0
        assert detector._interactive_threshold == 2
        assert detector._completed_threshold == 5
    
    def test_status_detector_configuration_constants(self):
        """Test StatusDetector uses correct configuration constants."""
        from terminalcp.status_detector import (
            StatusDetector,
            POLLING_INTERVAL_SECONDS,
            INTERACTIVE_STABILITY_THRESHOLD,
            COMPLETED_STABILITY_THRESHOLD
        )
        from terminalcp.terminal_client import TerminalClient
        
        client = TerminalClient()
        detector = StatusDetector(client)
        
        # Verify configuration matches constants
        assert detector._polling_interval == POLLING_INTERVAL_SECONDS
        assert detector._interactive_threshold == INTERACTIVE_STABILITY_THRESHOLD
        assert detector._completed_threshold == COMPLETED_STABILITY_THRESHOLD
