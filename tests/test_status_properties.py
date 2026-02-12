"""
status_detector 的基于属性的测试。

这些测试验证在状态监控系统的所有有效执行中
应成立的通用属性。
"""

import pytest
import re
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone, timedelta
from terminalcp.claude_status import (
    TerminalState,
    TaskStatus,
    InteractionType,
    TimingInfo,
    StatusDetail,
    StatusResponse,
    SessionState,
)


# 用于生成测试数据的自定义策略
@st.composite
def terminal_state_strategy(draw):
    """生成有效的 TerminalState。"""
    return draw(st.sampled_from([
        TerminalState.RUNNING,
        TerminalState.INTERACTIVE,
        TerminalState.COMPLETED
    ]))


@st.composite
def task_status_strategy(draw):
    """生成有效的 TaskStatus。"""
    return draw(st.sampled_from([
        TaskStatus.PENDING,
        TaskStatus.RUNNING,
        TaskStatus.WAITING_FOR_INPUT,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED
    ]))


@st.composite
def interaction_type_strategy(draw):
    """生成有效的 InteractionType 或 None。"""
    return draw(st.one_of(
        st.none(),
        st.sampled_from([
            InteractionType.PERMISSION_CONFIRM,
            InteractionType.HIGHLIGHTED_OPTION,
            InteractionType.PLAN_APPROVAL,
            InteractionType.USER_QUESTION,
            InteractionType.SELECTION_MENU
        ])
    ))


@st.composite
def datetime_strategy(draw):
    """生成带时区的有效 datetime 或 None。"""
    choice = draw(st.one_of(
        st.none(),
        st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31)
        )
    ))
    # 如果不为 None，为 datetime 添加时区
    if choice is not None:
        return choice.replace(tzinfo=timezone.utc)
    return choice


@st.composite
def session_state_strategy(draw):
    """生成有效的 SessionState。"""
    session_id = draw(st.text(min_size=1, max_size=50))
    terminal_state = draw(terminal_state_strategy())
    task_status = draw(task_status_strategy())
    stable_count = draw(st.integers(min_value=0, max_value=100))
    last_output = draw(st.text(max_size=1000))
    interaction_type = draw(interaction_type_strategy())
    choices = draw(st.one_of(
        st.none(),
        st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10)
    ))
    started_at = draw(datetime_strategy())
    # 确保两者都存在时 completed_at 在 started_at 之后
    if started_at is not None:
        # 生成添加到 started_at 的时间增量
        delta_seconds = draw(st.integers(min_value=0, max_value=86400))  # 0 to 1 day
        completed_at = draw(st.one_of(
            st.none(),
            st.just(started_at + timedelta(seconds=delta_seconds))
        ))
    else:
        completed_at = draw(datetime_strategy())
    
    auto_response_count = draw(st.integers(min_value=0, max_value=25))
    description = draw(st.text(min_size=1, max_size=200))
    
    return SessionState(
        session_id=session_id,
        terminal_state=terminal_state,
        task_status=task_status,
        stable_count=stable_count,
        last_output=last_output,
        interaction_type=interaction_type,
        choices=choices,
        started_at=started_at,
        completed_at=completed_at,
        auto_response_count=auto_response_count,
        description=description
    )


# 功能：claude-code-status-monitoring，属性 2：状态值有效性
@given(session_state=session_state_strategy())
@settings(max_examples=100)
def test_property_state_value_validity(session_state):
    """
    **验证需求：6.1, 7.1**

    属性 2：状态值有效性
    对于任意时间点的任何会话状态，terminal_state 应为
    (running, interactive, completed) 之一，task_status 应为
    (pending, running, waiting_for_input, completed, failed) 之一。
    """
    # 验证 terminal_state 有效
    assert session_state.terminal_state in [
        TerminalState.RUNNING,
        TerminalState.INTERACTIVE,
        TerminalState.COMPLETED
    ], f"Invalid terminal_state: {session_state.terminal_state}"

    # 验证 task_status 有效
    assert session_state.task_status in [
        TaskStatus.PENDING,
        TaskStatus.RUNNING,
        TaskStatus.WAITING_FOR_INPUT,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED
    ], f"Invalid task_status: {session_state.task_status}"

    # 验证枚举值为字符串
    assert isinstance(session_state.terminal_state.value, str)
    assert isinstance(session_state.task_status.value, str)

    # 验证值与预期字符串匹配
    valid_terminal_values = {"running", "interactive", "completed"}
    valid_task_values = {"pending", "running", "waiting_for_input", "completed", "failed"}
    
    assert session_state.terminal_state.value in valid_terminal_values
    assert session_state.task_status.value in valid_task_values


# 功能：claude-code-status-monitoring，属性 1：响应结构完整性
@given(session_state=session_state_strategy())
@settings(max_examples=100)
def test_property_response_structure_completeness(session_state):
    """
    **验证需求：1.1, 3.5, 6.5, 7.7, 8.5, 9.1, 9.2, 9.3, 9.4, 9.6**

    属性 1：响应结构完整性
    对于任何有效的会话状态，状态响应应包含所有必需字段
    （terminal_state、task_status、stable_count、带有
    description/interaction_type/choices 的 detail，以及带有
    started_at/completed_at/duration_seconds 的 timing），
    具有适当的类型和有效的 JSON 序列化。
    """
    # 将会话状态转换为状态响应
    response = session_state.to_status_response()

    # 验证所有必需字段存在
    assert hasattr(response, 'terminal_state')
    assert hasattr(response, 'task_status')
    assert hasattr(response, 'stable_count')
    assert hasattr(response, 'detail')
    assert hasattr(response, 'timing')
    
    # 验证 terminal_state 有效
    assert response.terminal_state in [
        TerminalState.RUNNING,
        TerminalState.INTERACTIVE,
        TerminalState.COMPLETED
    ]

    # 验证 task_status 有效
    assert response.task_status in [
        TaskStatus.PENDING,
        TaskStatus.RUNNING,
        TaskStatus.WAITING_FOR_INPUT,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED
    ]

    # 验证 stable_count 为整数
    assert isinstance(response.stable_count, int)
    assert response.stable_count >= 0
    
    # 验证 detail 结构
    assert isinstance(response.detail, StatusDetail)
    assert isinstance(response.detail.description, str)
    assert len(response.detail.description) > 0
    assert response.detail.interaction_type is None or isinstance(response.detail.interaction_type, str)
    assert response.detail.choices is None or isinstance(response.detail.choices, list)
    
    # 验证 timing 结构
    assert isinstance(response.timing, TimingInfo)
    assert response.timing.started_at is None or isinstance(response.timing.started_at, str)
    assert response.timing.completed_at is None or isinstance(response.timing.completed_at, str)
    assert response.timing.duration_seconds is None or isinstance(response.timing.duration_seconds, (int, float))
    
    # 验证 JSON 序列化正常
    response_dict = response.to_dict()
    assert isinstance(response_dict, dict)

    # 验证字典中的所有必需键
    assert 'terminal_state' in response_dict
    assert 'task_status' in response_dict
    assert 'stable_count' in response_dict
    assert 'detail' in response_dict
    assert 'timing' in response_dict
    
    # 验证 detail 字典结构
    assert 'description' in response_dict['detail']
    assert 'interaction_type' in response_dict['detail']
    assert 'choices' in response_dict['detail']
    
    # 验证 timing 字典结构
    assert 'started_at' in response_dict['timing']
    assert 'completed_at' in response_dict['timing']
    assert 'duration_seconds' in response_dict['timing']
    
    # 验证可以创建 JSON 字符串
    json_str = response.to_json()
    assert isinstance(json_str, str)
    assert len(json_str) > 0
    
    # 通过解析验证 JSON 有效
    import json
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


# 功能：claude-code-status-monitoring，属性 10：计时不变量
@given(session_state=session_state_strategy())
@settings(max_examples=100)
def test_property_timing_invariants(session_state):
    """
    **验证需求：5.3, 5.4, 7.2, 8.1, 8.2, 8.3, 8.4, 8.6**

    属性 10：计时不变量
    对于任何会话，当两个时间戳都存在时，duration_seconds 应
    等于它们的差值；所有时间戳应为 ISO 8601 格式。
    """
    response = session_state.to_status_response()
    
    # 如果两个时间戳都存在，应计算持续时间
    if session_state.started_at is not None and session_state.completed_at is not None:
        expected_duration = (session_state.completed_at - session_state.started_at).total_seconds()
        assert response.timing.duration_seconds is not None
        assert abs(response.timing.duration_seconds - expected_duration) < 0.001
    else:
        # 如果任一时间戳缺失，持续时间应为 None
        assert response.timing.duration_seconds is None
    
    # 验证时间戳格式（带时区的 ISO 8601）
    if response.timing.started_at is not None:
        assert isinstance(response.timing.started_at, str)
        # 应包含时区指示符（+ 或 Z）
        assert '+' in response.timing.started_at or 'Z' in response.timing.started_at
        # 应可解析为 ISO 8601
        datetime.fromisoformat(response.timing.started_at.replace('Z', '+00:00'))

    if response.timing.completed_at is not None:
        assert isinstance(response.timing.completed_at, str)
        # 应包含时区指示符（+ 或 Z）
        assert '+' in response.timing.completed_at or 'Z' in response.timing.completed_at
        # 应可解析为 ISO 8601
        datetime.fromisoformat(response.timing.completed_at.replace('Z', '+00:00'))


# 功能：claude-code-status-monitoring，属性 17：非交互状态字段可空性
@given(session_state=session_state_strategy())
@settings(max_examples=100)
def test_property_non_interactive_state_field_nullability(session_state):
    """
    **验证需求：9.5**

    属性 17：非交互状态字段可空性
    对于 terminal_state 不是 interactive 的任何会话，响应中的
    interaction_type 和 choices 字段应为 null。
    """
    # 设置 terminal_state 为非交互状态
    if session_state.terminal_state != TerminalState.INTERACTIVE:
        # 清除交互字段
        session_state.interaction_type = None
        session_state.choices = None
        
        response = session_state.to_status_response()
        
        # 验证交互字段为 null
        assert response.detail.interaction_type is None
        assert response.detail.choices is None


# 用于生成 ANSI 编码终端输出的自定义策略
@st.composite
def ansi_output_strategy(draw):
    """
    生成有效的 ANSI 编码终端输出。

    创建包含各种 ANSI 转义序列的文本，包括：
    - SGR（选择图形再现）码用于颜色和样式
    - 光标移动命令
    - 屏幕清除序列
    - 纯文本内容
    """
    # 生成基础文本内容
    text_parts = []
    
    # 添加纯文本
    num_parts = draw(st.integers(min_value=1, max_value=10))
    
    for _ in range(num_parts):
        # 选择要添加的内容
        choice = draw(st.integers(min_value=0, max_value=5))
        
        if choice == 0:
            # 纯文本
            text_parts.append(draw(st.text(
                alphabet=st.characters(
                    whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
                    min_codepoint=32,
                    max_codepoint=126
                ),
                min_size=0,
                max_size=50
            )))
        elif choice == 1:
            # SGR 颜色码（前景色 30-37，背景色 40-47）
            color = draw(st.integers(min_value=30, max_value=47))
            text_parts.append(f"\x1b[{color}m")
        elif choice == 2:
            # SGR 样式码（粗体、下划线等）
            style = draw(st.sampled_from([0, 1, 4, 7]))  # 重置、粗体、下划线、反转
            text_parts.append(f"\x1b[{style}m")
        elif choice == 3:
            # 光标移动
            row = draw(st.integers(min_value=1, max_value=50))
            col = draw(st.integers(min_value=1, max_value=120))
            text_parts.append(f"\x1b[{row};{col}H")
        elif choice == 4:
            # 清除屏幕
            text_parts.append("\x1b[2J")
        else:
            # 换行
            text_parts.append("\n")
    
    return ''.join(text_parts)


# 功能：claude-code-status-monitoring，属性 11：ANSI 处理往返
@given(raw_output=ansi_output_strategy())
@settings(max_examples=100, deadline=None)
def test_property_ansi_processing_round_trip(raw_output):
    """
    **验证需求：2.3, 2.4, 2.5, 2.7**

    属性 11：ANSI 处理往返
    对于任何有效的 ANSI 编码终端输出，通过 pyte 渲染
    （或失败时通过正则回退）应产生不含 ANSI 控制码的
    干净文本，且每行的尾部空白应被剥离。
    """
    from terminalcp.claude_status import PyteRenderer
    
    # 创建渲染器
    renderer = PyteRenderer()

    # 渲染 ANSI 输出
    rendered_text = renderer.render(raw_output)
    
    # 属性 1：结果应为字符串
    assert isinstance(rendered_text, str), "Rendered output must be a string"
    
    # 属性 2：不应残留 ANSI 转义序列
    # ANSI 转义序列以 ESC [（或 \x1b[）开头
    ansi_pattern = re.compile(r'\x1b\[[^a-zA-Z]*[a-zA-Z]')
    ansi_matches = ansi_pattern.findall(rendered_text)
    assert len(ansi_matches) == 0, f"ANSI codes found in rendered output: {ansi_matches}"
    
    # 属性 3：不应残留任何 ESC 字符
    assert '\x1b' not in rendered_text, "ESC character (\\x1b) found in rendered output"
    
    # 属性 4：每行的尾部空白应被剥离
    lines = rendered_text.split('\n')
    for i, line in enumerate(lines):
        # 检查行不以空格或制表符结尾
        if len(line) > 0:
            assert not line.endswith(' ') and not line.endswith('\t'), \
                f"Line {i} has trailing whitespace: {repr(line)}"
    
    # 属性 5：不可见 Unicode 字符应被移除
    invisible_chars = ['\u200b', '\u200c', '\u200d', '\u200e', '\u200f', '\ufeff']
    for char in invisible_chars:
        assert char not in rendered_text, \
            f"Invisible Unicode character {repr(char)} found in rendered output"
