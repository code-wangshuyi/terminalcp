"""
status_detector 数据结构和枚举的基础测试。

测试 status_detector.py 中定义的核心数据结构，
确保它们被正确定义且可以正确实例化。
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
    """测试枚举定义。"""
    
    def test_terminal_state_values(self):
        """测试 TerminalState 枚举具有正确的值。"""
        assert TerminalState.RUNNING.value == "running"
        assert TerminalState.INTERACTIVE.value == "interactive"
        assert TerminalState.COMPLETED.value == "completed"
    
    def test_task_status_values(self):
        """测试 TaskStatus 枚举具有正确的值。"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.WAITING_FOR_INPUT.value == "waiting_for_input"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
    
    def test_interaction_type_values(self):
        """测试 InteractionType 枚举具有正确的值。"""
        assert InteractionType.PERMISSION_CONFIRM.value == "permission_confirm"
        assert InteractionType.HIGHLIGHTED_OPTION.value == "highlighted_option"
        assert InteractionType.PLAN_APPROVAL.value == "plan_approval"
        assert InteractionType.USER_QUESTION.value == "user_question"
        assert InteractionType.SELECTION_MENU.value == "selection_menu"


class TestTimingInfo:
    """测试 TimingInfo 数据类。"""
    
    def test_timing_info_creation(self):
        """测试 TimingInfo 可以使用所有字段创建。"""
        timing = TimingInfo(
            started_at="2026-02-09T10:30:00Z",
            completed_at="2026-02-09T10:30:45Z",
            duration_seconds=45.2
        )
        assert timing.started_at == "2026-02-09T10:30:00Z"
        assert timing.completed_at == "2026-02-09T10:30:45Z"
        assert timing.duration_seconds == 45.2
    
    def test_timing_info_defaults(self):
        """测试 TimingInfo 所有字段默认为 None。"""
        timing = TimingInfo()
        assert timing.started_at is None
        assert timing.completed_at is None
        assert timing.duration_seconds is None
    
    def test_timing_info_to_dict(self):
        """测试 TimingInfo.to_dict() 返回正确的字典。"""
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
    """测试 StatusDetail 数据类。"""
    
    def test_status_detail_creation(self):
        """测试 StatusDetail 可以使用所有字段创建。"""
        detail = StatusDetail(
            description="Waiting for permission",
            interaction_type="permission_confirm",
            choices=["Yes", "No"]
        )
        assert detail.description == "Waiting for permission"
        assert detail.interaction_type == "permission_confirm"
        assert detail.choices == ["Yes", "No"]
    
    def test_status_detail_defaults(self):
        """测试 StatusDetail 可选字段的默认值。"""
        detail = StatusDetail(description="Running")
        assert detail.description == "Running"
        assert detail.interaction_type is None
        assert detail.choices is None
    
    def test_status_detail_to_dict(self):
        """测试 StatusDetail.to_dict() 返回正确的字典。"""
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
    """测试 StatusResponse 数据类。"""
    
    def test_status_response_creation(self):
        """测试 StatusResponse 可以使用所有字段创建。"""
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
        """测试 StatusResponse.to_dict() 返回正确的字典。"""
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
        """测试 StatusResponse.to_json() 返回有效的 JSON 字符串。"""
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
    """测试 InteractionMatch 数据类。"""
    
    def test_interaction_match_creation(self):
        """测试 InteractionMatch 可以使用所有字段创建。"""
        match = InteractionMatch(
            interaction_type=InteractionType.PERMISSION_CONFIRM,
            choices=["Yes", "No"],
            matched_text="Allow tool file_editor? Yes/No"
        )
        assert match.interaction_type == InteractionType.PERMISSION_CONFIRM
        assert match.choices == ["Yes", "No"]
        assert match.matched_text == "Allow tool file_editor? Yes/No"


class TestInteractionPattern:
    """测试 InteractionPattern 数据类。"""
    
    def test_interaction_pattern_creation(self):
        """测试 InteractionPattern 可以使用所有字段创建。"""
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
    """测试 SessionState 数据类。"""
    
    def test_session_state_creation(self):
        """测试 SessionState 可以使用必需字段创建。"""
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
        """测试带时区的 datetime 的 format_timestamp。"""
        state = SessionState(session_id="test-123")
        dt = datetime(2026, 2, 9, 10, 30, 0, tzinfo=timezone.utc)
        result = state.format_timestamp(dt)
        assert result == "2026-02-09T10:30:00+00:00"
    
    def test_format_timestamp_without_timezone(self):
        """测试 format_timestamp 在缺少时区时添加 UTC。"""
        state = SessionState(session_id="test-123")
        dt = datetime(2026, 2, 9, 10, 30, 0)
        result = state.format_timestamp(dt)
        assert result == "2026-02-09T10:30:00+00:00"
    
    def test_format_timestamp_none(self):
        """测试 format_timestamp 对 None 输入返回 None。"""
        state = SessionState(session_id="test-123")
        result = state.format_timestamp(None)
        assert result is None
    
    def test_calculate_duration(self):
        """测试 calculate_duration 返回正确的秒数持续时间。"""
        state = SessionState(session_id="test-123")
        state.started_at = datetime(2026, 2, 9, 10, 30, 0, tzinfo=timezone.utc)
        state.completed_at = datetime(2026, 2, 9, 10, 30, 45, tzinfo=timezone.utc)
        duration = state.calculate_duration()
        assert duration == 45.0
    
    def test_calculate_duration_with_fractional_seconds(self):
        """测试 calculate_duration 处理小数秒。"""
        state = SessionState(session_id="test-123")
        state.started_at = datetime(2026, 2, 9, 10, 30, 0, 200000, tzinfo=timezone.utc)
        state.completed_at = datetime(2026, 2, 9, 10, 30, 45, 400000, tzinfo=timezone.utc)
        duration = state.calculate_duration()
        assert duration == pytest.approx(45.2, rel=0.01)
    
    def test_calculate_duration_none_started(self):
        """测试 started_at 为 None 时 calculate_duration 返回 None。"""
        state = SessionState(session_id="test-123")
        state.completed_at = datetime(2026, 2, 9, 10, 30, 45, tzinfo=timezone.utc)
        duration = state.calculate_duration()
        assert duration is None
    
    def test_calculate_duration_none_completed(self):
        """测试 completed_at 为 None 时 calculate_duration 返回 None。"""
        state = SessionState(session_id="test-123")
        state.started_at = datetime(2026, 2, 9, 10, 30, 0, tzinfo=timezone.utc)
        duration = state.calculate_duration()
        assert duration is None
    
    def test_to_status_response(self):
        """测试 to_status_response 创建正确的 StatusResponse。"""
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
        """测试已完成状态的 to_status_response。"""
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
    """测试 StatusDetector 类初始化。"""
    
    def test_status_detector_initialization(self):
        """测试 StatusDetector 可以使用 TerminalClient 初始化。"""
        from terminalcp.status_detector import StatusDetector
        from terminalcp.terminal_client import TerminalClient
        
        # 创建模拟终端客户端
        client = TerminalClient()
        
        # 初始化 StatusDetector
        detector = StatusDetector(client)
        
        # 验证初始化
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
        """测试 StatusDetector 使用正确的配置常量。"""
        from terminalcp.status_detector import (
            StatusDetector,
            POLLING_INTERVAL_SECONDS,
            INTERACTIVE_STABILITY_THRESHOLD,
            COMPLETED_STABILITY_THRESHOLD
        )
        from terminalcp.terminal_client import TerminalClient
        
        client = TerminalClient()
        detector = StatusDetector(client)
        
        # 验证配置与常量匹配
        assert detector._polling_interval == POLLING_INTERVAL_SECONDS
        assert detector._interactive_threshold == INTERACTIVE_STABILITY_THRESHOLD
        assert detector._completed_threshold == COMPLETED_STABILITY_THRESHOLD
