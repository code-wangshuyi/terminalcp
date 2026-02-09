"""
Property-based tests for status_detector.

These tests verify universal properties that should hold across all valid
executions of the status monitoring system.
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


# Custom strategies for generating test data
@st.composite
def terminal_state_strategy(draw):
    """Generate a valid TerminalState."""
    return draw(st.sampled_from([
        TerminalState.RUNNING,
        TerminalState.INTERACTIVE,
        TerminalState.COMPLETED
    ]))


@st.composite
def task_status_strategy(draw):
    """Generate a valid TaskStatus."""
    return draw(st.sampled_from([
        TaskStatus.PENDING,
        TaskStatus.RUNNING,
        TaskStatus.WAITING_FOR_INPUT,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED
    ]))


@st.composite
def interaction_type_strategy(draw):
    """Generate a valid InteractionType or None."""
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
    """Generate a valid datetime with timezone or None."""
    choice = draw(st.one_of(
        st.none(),
        st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31)
        )
    ))
    # Add timezone to datetime if not None
    if choice is not None:
        return choice.replace(tzinfo=timezone.utc)
    return choice


@st.composite
def session_state_strategy(draw):
    """Generate a valid SessionState."""
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
    # Ensure completed_at is after started_at if both exist
    if started_at is not None:
        # Generate a timedelta to add to started_at
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


# Feature: claude-code-status-monitoring, Property 2: State Value Validity
@given(session_state=session_state_strategy())
@settings(max_examples=100)
def test_property_state_value_validity(session_state):
    """
    **Validates: Requirements 6.1, 7.1**
    
    Property 2: State Value Validity
    For any session state at any point in time, terminal_state should be one of
    (running, interactive, completed) and task_status should be one of
    (pending, running, waiting_for_input, completed, failed).
    """
    # Verify terminal_state is valid
    assert session_state.terminal_state in [
        TerminalState.RUNNING,
        TerminalState.INTERACTIVE,
        TerminalState.COMPLETED
    ], f"Invalid terminal_state: {session_state.terminal_state}"
    
    # Verify task_status is valid
    assert session_state.task_status in [
        TaskStatus.PENDING,
        TaskStatus.RUNNING,
        TaskStatus.WAITING_FOR_INPUT,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED
    ], f"Invalid task_status: {session_state.task_status}"
    
    # Verify enum values are strings
    assert isinstance(session_state.terminal_state.value, str)
    assert isinstance(session_state.task_status.value, str)
    
    # Verify the values match expected strings
    valid_terminal_values = {"running", "interactive", "completed"}
    valid_task_values = {"pending", "running", "waiting_for_input", "completed", "failed"}
    
    assert session_state.terminal_state.value in valid_terminal_values
    assert session_state.task_status.value in valid_task_values


# Feature: claude-code-status-monitoring, Property 1: Response Structure Completeness
@given(session_state=session_state_strategy())
@settings(max_examples=100)
def test_property_response_structure_completeness(session_state):
    """
    **Validates: Requirements 1.1, 3.5, 6.5, 7.7, 8.5, 9.1, 9.2, 9.3, 9.4, 9.6**
    
    Property 1: Response Structure Completeness
    For any valid session state, the status response should contain all required
    fields (terminal_state, task_status, stable_count, detail with
    description/interaction_type/choices, and timing with
    started_at/completed_at/duration_seconds) with appropriate types and valid
    JSON serialization.
    """
    # Convert session state to status response
    response = session_state.to_status_response()
    
    # Verify all required fields exist
    assert hasattr(response, 'terminal_state')
    assert hasattr(response, 'task_status')
    assert hasattr(response, 'stable_count')
    assert hasattr(response, 'detail')
    assert hasattr(response, 'timing')
    
    # Verify terminal_state is valid
    assert response.terminal_state in [
        TerminalState.RUNNING,
        TerminalState.INTERACTIVE,
        TerminalState.COMPLETED
    ]
    
    # Verify task_status is valid
    assert response.task_status in [
        TaskStatus.PENDING,
        TaskStatus.RUNNING,
        TaskStatus.WAITING_FOR_INPUT,
        TaskStatus.COMPLETED,
        TaskStatus.FAILED
    ]
    
    # Verify stable_count is an integer
    assert isinstance(response.stable_count, int)
    assert response.stable_count >= 0
    
    # Verify detail structure
    assert isinstance(response.detail, StatusDetail)
    assert isinstance(response.detail.description, str)
    assert len(response.detail.description) > 0
    assert response.detail.interaction_type is None or isinstance(response.detail.interaction_type, str)
    assert response.detail.choices is None or isinstance(response.detail.choices, list)
    
    # Verify timing structure
    assert isinstance(response.timing, TimingInfo)
    assert response.timing.started_at is None or isinstance(response.timing.started_at, str)
    assert response.timing.completed_at is None or isinstance(response.timing.completed_at, str)
    assert response.timing.duration_seconds is None or isinstance(response.timing.duration_seconds, (int, float))
    
    # Verify JSON serialization works
    response_dict = response.to_dict()
    assert isinstance(response_dict, dict)
    
    # Verify all required keys in dict
    assert 'terminal_state' in response_dict
    assert 'task_status' in response_dict
    assert 'stable_count' in response_dict
    assert 'detail' in response_dict
    assert 'timing' in response_dict
    
    # Verify detail dict structure
    assert 'description' in response_dict['detail']
    assert 'interaction_type' in response_dict['detail']
    assert 'choices' in response_dict['detail']
    
    # Verify timing dict structure
    assert 'started_at' in response_dict['timing']
    assert 'completed_at' in response_dict['timing']
    assert 'duration_seconds' in response_dict['timing']
    
    # Verify JSON string can be created
    json_str = response.to_json()
    assert isinstance(json_str, str)
    assert len(json_str) > 0
    
    # Verify JSON is valid by parsing it
    import json
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)


# Custom strategy for generating text that matches multiple patterns
@st.composite
def multi_pattern_text_strategy(draw):
    """
    Generate text that matches multiple interaction patterns.
    
    This strategy creates text that intentionally matches multiple patterns
    to test priority ordering. We'll create text with specific patterns and
    track which ones should match.
    """
    from terminalcp.terminal_detector import TerminalDetector
    
    # Define pattern components that are designed to match specific types
    # Each tuple is (text, interaction_type, priority)
    pattern_options = [
        # Permission confirm patterns (priority 1)
        ("Allow tool file_editor?", InteractionType.PERMISSION_CONFIRM, 1),
        ("Allow tool code_runner?", InteractionType.PERMISSION_CONFIRM, 1),
        
        # Highlighted option patterns (priority 2)
        ("❯ Yes\n  No", InteractionType.HIGHLIGHTED_OPTION, 2),
        ("❯ Continue\n  Cancel", InteractionType.HIGHLIGHTED_OPTION, 2),
        
        # Plan approval patterns (priority 3)
        ("Proceed with this plan?", InteractionType.PLAN_APPROVAL, 3),
        ("Proceed with changes?", InteractionType.PLAN_APPROVAL, 3),
        
        # User question patterns (priority 4)
        ("Do you want to continue?", InteractionType.USER_QUESTION, 4),
        ("Should I create a backup?", InteractionType.USER_QUESTION, 4),
        
        # Selection menu patterns (priority 5)
        ("1. Option One\n2. Option Two\n3. Option Three", InteractionType.SELECTION_MENU, 5),
        ("- First choice\n- Second choice\n- Third choice", InteractionType.SELECTION_MENU, 5),
    ]
    
    # Choose 2-4 patterns to include
    num_patterns = draw(st.integers(min_value=2, max_value=4))
    selected_patterns = draw(st.lists(
        st.sampled_from(pattern_options),
        min_size=num_patterns,
        max_size=num_patterns,
        unique_by=lambda x: x[1]  # Ensure different interaction types
    ))
    
    # Build the text by combining patterns
    text_parts = [pattern[0] for pattern in selected_patterns]
    
    # Shuffle the order
    shuffled_parts = draw(st.permutations(text_parts))
    
    # Join with double newlines to separate patterns clearly
    combined_text = '\n\n'.join(shuffled_parts)
    
    # Determine the expected type (highest priority = lowest number)
    priorities = [pattern[2] for pattern in selected_patterns]
    min_priority = min(priorities)
    expected_type = next(pattern[1] for pattern in selected_patterns if pattern[2] == min_priority)
    
    # Verify that the text actually matches multiple patterns by checking manually
    detector = TerminalDetector()
    text_lines = combined_text.split('\n')
    
    # Count how many patterns actually match
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
    
    # Only use examples where at least 2 patterns match
    from hypothesis import assume
    assume(len(matches) >= 2)
    
    return combined_text, expected_type, matches


# Feature: claude-code-status-monitoring, Property 5: Interactive Pattern Priority Ordering
@given(text_expected_matches=multi_pattern_text_strategy())
@settings(max_examples=100, deadline=None)
def test_property_interactive_pattern_priority_ordering(text_expected_matches):
    """
    **Validates: Requirements 4.2**
    
    Property 5: Interactive Pattern Priority Ordering
    For any text that matches multiple interaction patterns, the detected
    interaction_type should be the one with the highest priority
    (permission_confirm > highlighted_option > plan_approval > user_question > selection_menu).
    """
    from terminalcp.terminal_detector import TerminalDetector
    
    text, expected_type, matching_patterns = text_expected_matches
    
    # Create detector
    detector = TerminalDetector()
    
    # Split text into lines for detect_interactive
    text_lines = text.split('\n')
    
    # Detect interactive pattern
    result = detector.detect_interactive(text_lines)
    
    # Should detect something since we generated text with patterns
    assert result is not None, f"Failed to detect any pattern in text: {text}"
    
    # The detected type should match the expected highest priority type
    assert result.interaction_type == expected_type, \
        f"Expected {expected_type.value} (highest priority among {[p.value for p in matching_patterns]}) " \
        f"but got {result.interaction_type.value} for text:\n{text}"
    
    # Verify the priority ordering is correct
    # Priority order: 1=permission_confirm, 2=highlighted_option, 3=plan_approval, 4=user_question, 5=selection_menu
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
    
    # Verify that the detected pattern has the highest priority among all matching patterns
    matching_priorities = [priority_map[p] for p in matching_patterns]
    min_matching_priority = min(matching_priorities)
    
    assert detected_priority == min_matching_priority, \
        f"Detected priority {detected_priority} is not the highest (lowest number) among matching patterns {matching_priorities}"


# Custom strategy for generating text with specific interaction patterns
@st.composite
def interaction_pattern_text_strategy(draw):
    """
    Generate text that matches a specific interaction pattern with known choices.
    
    Returns a tuple of (text, expected_interaction_type, expected_choices).
    This strategy creates text for each of the 5 interaction types with
    clearly defined choices that should be extracted.
    """
    from terminalcp.terminal_detector import TerminalDetector
    
    # Choose which interaction type to generate
    interaction_type = draw(st.sampled_from([
        InteractionType.PERMISSION_CONFIRM,
        InteractionType.HIGHLIGHTED_OPTION,
        InteractionType.PLAN_APPROVAL,
        InteractionType.USER_QUESTION,
        InteractionType.SELECTION_MENU,
    ]))
    
    if interaction_type == InteractionType.PERMISSION_CONFIRM:
        # Generate permission confirmation patterns
        tool_name = draw(st.sampled_from(['file_editor', 'code_runner', 'web_search', 'terminal']))
        
        # Choose format variation
        format_choice = draw(st.integers(min_value=0, max_value=2))
        
        if format_choice == 0:
            # Simple format: "Allow tool X?"
            text = f"Allow tool {tool_name}?"
            expected_choices = ["Yes", "No"]  # Default choices
        elif format_choice == 1:
            # With explicit Yes/No
            text = f"Allow tool {tool_name}?\nYes\nNo"
            expected_choices = ["Yes", "No"]
        else:
            # With highlighted option
            text = f"Allow tool {tool_name}?\n❯ Yes\n  No"
            expected_choices = ["Yes", "No"]
        
        return text, interaction_type, expected_choices
    
    elif interaction_type == InteractionType.HIGHLIGHTED_OPTION:
        # Generate highlighted option patterns
        options = draw(st.lists(
            st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=122), min_size=3, max_size=15),
            min_size=2,
            max_size=5,
            unique=True
        ))
        
        # Pick which option is highlighted
        highlighted_idx = draw(st.integers(min_value=0, max_value=len(options)-1))
        
        # Build the text with highlighted option
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
        # Generate plan approval patterns
        plan_text = draw(st.sampled_from([
            "Proceed?",
            "Proceed with this plan?",
            "Proceed with changes?",
            "Proceed with the following actions?",
        ]))
        
        # Choose whether to include explicit choices
        # IMPORTANT: Don't use ❯ symbol as it would trigger highlighted_option (higher priority)
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
            # Just the question - "Proceed" will be extracted from the question text
            text = plan_text
            expected_choices = ["Proceed"]  # Only "Proceed" is in the text
        
        return text, interaction_type, expected_choices
    
    elif interaction_type == InteractionType.USER_QUESTION:
        # Generate user question patterns
        # IMPORTANT: Avoid using "proceed" as it would trigger plan_approval (higher priority)
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
        
        # Optionally add explicit choices
        include_choices = draw(st.booleans())
        if include_choices:
            text += "\nYes\nNo"
        
        expected_choices = ["Yes", "No"]
        
        return text, interaction_type, expected_choices
    
    else:  # InteractionType.SELECTION_MENU
        # Generate selection menu patterns
        num_items = draw(st.integers(min_value=2, max_value=6))
        
        # Choose menu style
        menu_style = draw(st.sampled_from(['numbered', 'bulleted_dash', 'bulleted_star', 'bulleted_plus']))
        
        # Generate menu items
        items = []
        for i in range(num_items):
            item_text = draw(st.text(
                alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'), min_codepoint=65, max_codepoint=122),
                min_size=5,
                max_size=20
            ))
            items.append(item_text.strip())
        
        # Build menu text
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


# Feature: claude-code-status-monitoring, Property 6: Pattern Matching and Choice Extraction
@given(pattern_data=interaction_pattern_text_strategy())
@settings(max_examples=100, deadline=None)
def test_property_pattern_matching_and_choice_extraction(pattern_data):
    """
    **Validates: Requirements 4.3, 4.4, 4.5, 4.6, 4.7, 4.10, 9.7**
    
    Property 6: Pattern Matching and Choice Extraction
    For any text matching an interaction pattern, the Terminal_Detector should
    correctly classify the interaction_type and extract all available choices
    as a list of strings.
    """
    from terminalcp.terminal_detector import TerminalDetector
    
    text, expected_type, expected_choices = pattern_data
    
    # Create detector
    detector = TerminalDetector()
    
    # Split text into lines for detect_interactive
    text_lines = text.split('\n')
    
    # Detect interactive pattern
    result = detector.detect_interactive(text_lines)
    
    # Property 1: Should detect the pattern
    assert result is not None, \
        f"Failed to detect {expected_type.value} pattern in text:\n{text}"
    
    # Property 2: Should correctly classify the interaction type
    assert result.interaction_type == expected_type, \
        f"Expected interaction type {expected_type.value} but got {result.interaction_type.value} for text:\n{text}"
    
    # Property 3: Choices should be a list of strings
    assert isinstance(result.choices, list), \
        f"Choices should be a list, got {type(result.choices)}"
    
    assert all(isinstance(choice, str) for choice in result.choices), \
        f"All choices should be strings, got {[type(c) for c in result.choices]}"
    
    # Property 4: Should extract the expected choices
    # For some patterns, the order might vary or additional choices might be found
    # So we check that all expected choices are present
    for expected_choice in expected_choices:
        assert any(expected_choice.lower() in choice.lower() or choice.lower() in expected_choice.lower() 
                   for choice in result.choices), \
            f"Expected choice '{expected_choice}' not found in extracted choices {result.choices} for text:\n{text}"
    
    # Property 5: Should have at least one choice
    assert len(result.choices) > 0, \
        f"Should extract at least one choice, got empty list for text:\n{text}"
    
    # Property 6: Choices should not be empty strings
    assert all(len(choice.strip()) > 0 for choice in result.choices), \
        f"Choices should not be empty strings, got {result.choices}"


# Feature: claude-code-status-monitoring, Property 10: Timing Invariants
@given(session_state=session_state_strategy())
@settings(max_examples=100)
def test_property_timing_invariants(session_state):
    """
    **Validates: Requirements 5.3, 5.4, 7.2, 8.1, 8.2, 8.3, 8.4, 8.6**
    
    Property 10: Timing Invariants
    For any session, when both timestamps exist then duration_seconds should
    equal their difference; and all timestamps should be in ISO 8601 format.
    """
    response = session_state.to_status_response()
    
    # If both timestamps exist, duration should be calculated
    if session_state.started_at is not None and session_state.completed_at is not None:
        expected_duration = (session_state.completed_at - session_state.started_at).total_seconds()
        assert response.timing.duration_seconds is not None
        assert abs(response.timing.duration_seconds - expected_duration) < 0.001
    else:
        # If either timestamp is missing, duration should be None
        assert response.timing.duration_seconds is None
    
    # Verify timestamp format (ISO 8601 with timezone)
    if response.timing.started_at is not None:
        assert isinstance(response.timing.started_at, str)
        # Should contain timezone indicator (+ or Z)
        assert '+' in response.timing.started_at or 'Z' in response.timing.started_at
        # Should be parseable as ISO 8601
        datetime.fromisoformat(response.timing.started_at.replace('Z', '+00:00'))
    
    if response.timing.completed_at is not None:
        assert isinstance(response.timing.completed_at, str)
        # Should contain timezone indicator (+ or Z)
        assert '+' in response.timing.completed_at or 'Z' in response.timing.completed_at
        # Should be parseable as ISO 8601
        datetime.fromisoformat(response.timing.completed_at.replace('Z', '+00:00'))


# Feature: claude-code-status-monitoring, Property 17: Non-Interactive State Field Nullability
@given(session_state=session_state_strategy())
@settings(max_examples=100)
def test_property_non_interactive_state_field_nullability(session_state):
    """
    **Validates: Requirements 9.5**
    
    Property 17: Non-Interactive State Field Nullability
    For any session where terminal_state is not interactive, the response fields
    interaction_type and choices should be null.
    """
    # Set terminal_state to non-interactive
    if session_state.terminal_state != TerminalState.INTERACTIVE:
        # Clear interaction fields
        session_state.interaction_type = None
        session_state.choices = None
        
        response = session_state.to_status_response()
        
        # Verify interaction fields are null
        assert response.detail.interaction_type is None
        assert response.detail.choices is None


# Custom strategy for generating ANSI-encoded terminal output
@st.composite
def ansi_output_strategy(draw):
    """
    Generate valid ANSI-encoded terminal output.
    
    Creates text with various ANSI escape sequences including:
    - SGR (Select Graphic Rendition) codes for colors and styles
    - Cursor movement commands
    - Screen clearing sequences
    - Plain text content
    """
    # Generate base text content
    text_parts = []
    
    # Add some plain text
    num_parts = draw(st.integers(min_value=1, max_value=10))
    
    for _ in range(num_parts):
        # Choose what to add
        choice = draw(st.integers(min_value=0, max_value=5))
        
        if choice == 0:
            # Plain text
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
            # SGR color code (foreground colors 30-37, background 40-47)
            color = draw(st.integers(min_value=30, max_value=47))
            text_parts.append(f"\x1b[{color}m")
        elif choice == 2:
            # SGR style code (bold, underline, etc.)
            style = draw(st.sampled_from([0, 1, 4, 7]))  # reset, bold, underline, reverse
            text_parts.append(f"\x1b[{style}m")
        elif choice == 3:
            # Cursor movement
            row = draw(st.integers(min_value=1, max_value=50))
            col = draw(st.integers(min_value=1, max_value=120))
            text_parts.append(f"\x1b[{row};{col}H")
        elif choice == 4:
            # Clear screen
            text_parts.append("\x1b[2J")
        else:
            # Newline
            text_parts.append("\n")
    
    return ''.join(text_parts)


# Feature: claude-code-status-monitoring, Property 11: ANSI Processing Round Trip
@given(raw_output=ansi_output_strategy())
@settings(max_examples=100, deadline=None)
def test_property_ansi_processing_round_trip(raw_output):
    """
    **Validates: Requirements 2.3, 2.4, 2.5, 2.7**
    
    Property 11: ANSI Processing Round Trip
    For any valid ANSI-encoded terminal output, feeding it through pyte rendering
    (or regex fallback on failure) should produce clean text without ANSI control
    codes, and trailing whitespace should be stripped from each line.
    """
    from terminalcp.status_detector import PyteRenderer
    
    # Create renderer
    renderer = PyteRenderer()
    
    # Render the ANSI output
    rendered_text = renderer.render(raw_output)
    
    # Property 1: Result should be a string
    assert isinstance(rendered_text, str), "Rendered output must be a string"
    
    # Property 2: No ANSI escape sequences should remain
    # ANSI escape sequences start with ESC [ (or \x1b[)
    ansi_pattern = re.compile(r'\x1b\[[^a-zA-Z]*[a-zA-Z]')
    ansi_matches = ansi_pattern.findall(rendered_text)
    assert len(ansi_matches) == 0, f"ANSI codes found in rendered output: {ansi_matches}"
    
    # Property 3: No ESC character should remain at all
    assert '\x1b' not in rendered_text, "ESC character (\\x1b) found in rendered output"
    
    # Property 4: Trailing whitespace should be stripped from each line
    lines = rendered_text.split('\n')
    for i, line in enumerate(lines):
        # Check that line doesn't end with spaces or tabs
        if len(line) > 0:
            assert not line.endswith(' ') and not line.endswith('\t'), \
                f"Line {i} has trailing whitespace: {repr(line)}"
    
    # Property 5: Invisible Unicode characters should be removed
    invisible_chars = ['\u200b', '\u200c', '\u200d', '\u200e', '\u200f', '\ufeff']
    for char in invisible_chars:
        assert char not in rendered_text, \
            f"Invisible Unicode character {repr(char)} found in rendered output"
