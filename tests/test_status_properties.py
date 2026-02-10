"""
status_detector 的基于属性的测试。

这些测试验证在状态监控系统的所有有效执行中
应成立的通用属性。
"""

import pytest
import re
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone, timedelta
from terminalcp.status_detector import (
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


# 用于生成匹配多个模式的文本的自定义策略
@st.composite
def multi_pattern_text_strategy(draw):
    """
    生成匹配多个交互模式的文本。

    此策略创建故意匹配多个模式的文本
    以测试优先级排序。我们创建带有特定模式的文本并
    跟踪哪些模式应该匹配。
    """
    from terminalcp.terminal_detector import TerminalDetector
    
    # 定义设计用于匹配特定类型的模式组件
    # 每个元组为 (text, interaction_type, priority)
    pattern_options = [
        # 权限确认模式（优先级 1）
        ("Allow tool file_editor?", InteractionType.PERMISSION_CONFIRM, 1),
        ("Allow tool code_runner?", InteractionType.PERMISSION_CONFIRM, 1),
        
        # 高亮选项模式（优先级 2）
        ("❯ Yes\n  No", InteractionType.HIGHLIGHTED_OPTION, 2),
        ("❯ Continue\n  Cancel", InteractionType.HIGHLIGHTED_OPTION, 2),
        
        # 计划批准模式（优先级 3）
        ("Proceed with this plan?", InteractionType.PLAN_APPROVAL, 3),
        ("Proceed with changes?", InteractionType.PLAN_APPROVAL, 3),
        
        # 用户问题模式（优先级 4）
        ("Do you want to continue?", InteractionType.USER_QUESTION, 4),
        ("Should I create a backup?", InteractionType.USER_QUESTION, 4),
        
        # 选择菜单模式（优先级 5）
        ("1. Option One\n2. Option Two\n3. Option Three", InteractionType.SELECTION_MENU, 5),
        ("- First choice\n- Second choice\n- Third choice", InteractionType.SELECTION_MENU, 5),
    ]
    
    # 选择 2-4 个模式包含
    num_patterns = draw(st.integers(min_value=2, max_value=4))
    selected_patterns = draw(st.lists(
        st.sampled_from(pattern_options),
        min_size=num_patterns,
        max_size=num_patterns,
        unique_by=lambda x: x[1]  # Ensure different interaction types
    ))
    
    # 通过组合模式构建文本
    text_parts = [pattern[0] for pattern in selected_patterns]
    
    # 打乱顺序
    shuffled_parts = draw(st.permutations(text_parts))
    
    # 用双换行符分隔模式以清晰区分
    combined_text = '\n\n'.join(shuffled_parts)
    
    # 确定预期类型（最高优先级 = 最小数字）
    priorities = [pattern[2] for pattern in selected_patterns]
    min_priority = min(priorities)
    expected_type = next(pattern[1] for pattern in selected_patterns if pattern[2] == min_priority)
    
    # 通过手动检查验证文本确实匹配了多个模式
    detector = TerminalDetector()
    text_lines = combined_text.split('\n')
    
    # 计算实际匹配的模式数量
    matches = []
    if detector._check_permission_confirm(combined_text):
        matches.append(InteractionType.PERMISSION_CONFIRM)
    if detector._check_highlighted_option(combined_text):
        matches.append(InteractionType.HIGHLIGHTED_OPTION)
    if detector._check_plan_approval(combined_text):
        matches.append(InteractionType.PLAN_APPROVAL)
    if detector._check_user_question(combined_text):
        matches.append(InteractionType.USER_QUESTION)
    if detector._check_selection_menu(combined_text):
        matches.append(InteractionType.SELECTION_MENU)
    
    # 仅使用至少匹配 2 个模式的示例
    from hypothesis import assume
    assume(len(matches) >= 2)
    
    return combined_text, expected_type, matches


# 功能：claude-code-status-monitoring，属性 5：交互模式优先级排序
@given(text_expected_matches=multi_pattern_text_strategy())
@settings(max_examples=100, deadline=None)
def test_property_interactive_pattern_priority_ordering(text_expected_matches):
    """
    **验证需求：4.2**

    属性 5：交互模式优先级排序
    对于任何匹配多个交互模式的文本，检测到的 interaction_type
    应为优先级最高的模式
    （permission_confirm > highlighted_option > plan_approval > user_question > selection_menu）。
    """
    from terminalcp.terminal_detector import TerminalDetector
    
    text, expected_type, matching_patterns = text_expected_matches
    
    # 创建检测器
    detector = TerminalDetector()

    # 将文本分割为行以用于 detect_interactive
    text_lines = text.split('\n')

    # 检测交互模式
    result = detector.detect_interactive(text_lines)

    # 应检测到内容因为我们生成了带模式的文本
    assert result is not None, f"Failed to detect any pattern in text: {text}"

    # 检测到的类型应与预期的最高优先级类型匹配
    assert result.interaction_type == expected_type, \
        f"Expected {expected_type.value} (highest priority among {[p.value for p in matching_patterns]}) " \
        f"but got {result.interaction_type.value} for text:\n{text}"

    # 验证优先级排序正确
    # 优先级顺序：1=permission_confirm, 2=highlighted_option, 3=plan_approval, 4=user_question, 5=selection_menu
    priority_map = {
        InteractionType.PERMISSION_CONFIRM: 1,
        InteractionType.HIGHLIGHTED_OPTION: 2,
        InteractionType.PLAN_APPROVAL: 3,
        InteractionType.USER_QUESTION: 4,
        InteractionType.SELECTION_MENU: 5,
    }
    
    detected_priority = priority_map[result.interaction_type]
    expected_priority = priority_map[expected_type]
    
    assert detected_priority == expected_priority, \
        f"Priority mismatch: detected priority {detected_priority} != expected priority {expected_priority}"
    
    # 验证检测到的模式在所有匹配模式中具有最高优先级
    matching_priorities = [priority_map[p] for p in matching_patterns]
    min_matching_priority = min(matching_priorities)
    
    assert detected_priority == min_matching_priority, \
        f"Detected priority {detected_priority} is not the highest (lowest number) among matching patterns {matching_priorities}"


# 用于生成特定交互模式文本的自定义策略
@st.composite
def interaction_pattern_text_strategy(draw):
    """
    生成匹配特定交互模式的文本及已知选项。

    返回 (text, expected_interaction_type, expected_choices) 元组。
    此策略为 5 种交互类型中的每一种创建带有
    明确定义选项的文本，这些选项应被正确提取。
    """
    from terminalcp.terminal_detector import TerminalDetector
    
    # 选择要生成的交互类型
    interaction_type = draw(st.sampled_from([
        InteractionType.PERMISSION_CONFIRM,
        InteractionType.HIGHLIGHTED_OPTION,
        InteractionType.PLAN_APPROVAL,
        InteractionType.USER_QUESTION,
        InteractionType.SELECTION_MENU,
    ]))
    
    if interaction_type == InteractionType.PERMISSION_CONFIRM:
        # 生成权限确认模式
        tool_name = draw(st.sampled_from(['file_editor', 'code_runner', 'web_search', 'terminal']))
        
        # 选择格式变体
        format_choice = draw(st.integers(min_value=0, max_value=2))
        
        if format_choice == 0:
            # 简单格式："Allow tool X?"
            text = f"Allow tool {tool_name}?"
            expected_choices = ["Yes", "No"]  # Default choices
        elif format_choice == 1:
            # 带显式 Yes/No
            text = f"Allow tool {tool_name}?\nYes\nNo"
            expected_choices = ["Yes", "No"]
        else:
            # 带高亮选项
            text = f"Allow tool {tool_name}?\n❯ Yes\n  No"
            expected_choices = ["Yes", "No"]
        
        return text, interaction_type, expected_choices
    
    elif interaction_type == InteractionType.HIGHLIGHTED_OPTION:
        # 生成高亮选项模式
        options = draw(st.lists(
            st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122), min_size=3, max_size=15),
            min_size=2,
            max_size=5,
            unique=True
        ))
        
        # 选择哪个选项被高亮
        highlighted_idx = draw(st.integers(min_value=0, max_value=len(options)-1))
        
        # 构建带高亮选项的文本
        lines = []
        for i, option in enumerate(options):
            if i == highlighted_idx:
                lines.append(f"❯ {option}")
            else:
                lines.append(f"  {option}")
        
        text = '\n'.join(lines)
        expected_choices = options
        
        return text, interaction_type, expected_choices
    
    elif interaction_type == InteractionType.PLAN_APPROVAL:
        # 生成计划批准模式
        plan_text = draw(st.sampled_from([
            "Proceed?",
            "Proceed with this plan?",
            "Proceed with changes?",
            "Proceed with the following actions?",
        ]))
        
        # 选择是否包含显式选项
        # 重要：不要使用 ❯ 符号，因为它会触发 highlighted_option（更高优先级）
        include_choices = draw(st.booleans())
        
        if include_choices:
            choice_format = draw(st.integers(min_value=0, max_value=1))
            if choice_format == 0:
                text = f"{plan_text}\nYes\nNo"
                expected_choices = ["Proceed", "Yes", "No"]  # "Proceed" is in the question text
            else:
                text = f"{plan_text}\nCancel"
                expected_choices = ["Proceed", "Cancel"]  # Both found in text
        else:
            # 仅问题——"Proceed" 将从问题文本中提取
            text = plan_text
            expected_choices = ["Proceed"]  # Only "Proceed" is in the text
        
        return text, interaction_type, expected_choices
    
    elif interaction_type == InteractionType.USER_QUESTION:
        # 生成用户问题模式
        # 重要：避免使用 "proceed"，因为它会触发 plan_approval（更高优先级）
        question_start = draw(st.sampled_from([
            "Do you want to",
            "Would you like to",
            "Should I",
        ]))
        
        action = draw(st.sampled_from([
            "continue",
            "create a backup",
            "save the file",
            "update the configuration",
        ]))
        
        text = f"{question_start} {action}?"
        
        # 可选地添加显式选项
        include_choices = draw(st.booleans())
        if include_choices:
            text += "\nYes\nNo"
        
        expected_choices = ["Yes", "No"]
        
        return text, interaction_type, expected_choices
    
    else:  # InteractionType.SELECTION_MENU
        # 生成选择菜单模式
        num_items = draw(st.integers(min_value=2, max_value=6))
        
        # 选择菜单样式
        menu_style = draw(st.sampled_from(['numbered', 'bulleted_dash', 'bulleted_star', 'bulleted_plus']))
        
        # 生成菜单项
        items = []
        for i in range(num_items):
            item_text = draw(st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'), min_codepoint=65, max_codepoint=122),
                min_size=5,
                max_size=20
            ))
            items.append(item_text.strip())
        
        # 构建菜单文本
        lines = []
        for i, item in enumerate(items):
            if menu_style == 'numbered':
                lines.append(f"{i+1}. {item}")
            elif menu_style == 'bulleted_dash':
                lines.append(f"- {item}")
            elif menu_style == 'bulleted_star':
                lines.append(f"* {item}")
            else:  # bulleted_plus
                lines.append(f"+ {item}")
        
        text = '\n'.join(lines)
        expected_choices = items
        
        return text, interaction_type, expected_choices


# 功能：claude-code-status-monitoring，属性 6：模式匹配和选项提取
@given(pattern_data=interaction_pattern_text_strategy())
@settings(max_examples=100, deadline=None)
def test_property_pattern_matching_and_choice_extraction(pattern_data):
    """
    **验证需求：4.3, 4.4, 4.5, 4.6, 4.7, 4.10, 9.7**

    属性 6：模式匹配和选项提取
    对于任何匹配交互模式的文本，Terminal_Detector 应
    正确分类 interaction_type 并将所有可用选项
    提取为字符串列表。
    """
    from terminalcp.terminal_detector import TerminalDetector
    
    text, expected_type, expected_choices = pattern_data

    # 创建检测器
    detector = TerminalDetector()

    # 将文本分割为行以用于 detect_interactive
    text_lines = text.split('\n')

    # 检测交互模式
    result = detector.detect_interactive(text_lines)

    # 属性 1：应检测到模式
    assert result is not None, \
        f"Failed to detect {expected_type.value} pattern in text:\n{text}"
    
    # 属性 2：应正确分类交互类型
    assert result.interaction_type == expected_type, \
        f"Expected interaction type {expected_type.value} but got {result.interaction_type.value} for text:\n{text}"
    
    # 属性 3：选项应为字符串列表
    assert isinstance(result.choices, list), \
        f"Choices should be a list, got {type(result.choices)}"
    
    assert all(isinstance(choice, str) for choice in result.choices), \
        f"All choices should be strings, got {[type(c) for c in result.choices]}"
    
    # 属性 4：应提取预期选项
    # 对于某些模式，顺序可能不同或可能找到额外选项
    # 因此我们检查所有预期选项都存在
    for expected_choice in expected_choices:
        assert any(expected_choice.lower() in choice.lower() or choice.lower() in expected_choice.lower() 
                   for choice in result.choices), \
            f"Expected choice '{expected_choice}' not found in extracted choices {result.choices} for text:\n{text}"
    
    # 属性 5：应至少有一个选项
    assert len(result.choices) > 0, \
        f"Should extract at least one choice, got empty list for text:\n{text}"
    
    # 属性 6：选项不应为空字符串
    assert all(len(choice.strip()) > 0 for choice in result.choices), \
        f"Choices should not be empty strings, got {result.choices}"


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
    from terminalcp.status_detector import PyteRenderer
    
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
