"""
Status detection for Claude Code CLI sessions.

This module provides real-time status monitoring capabilities for terminalcp,
enabling automated orchestration systems to programmatically determine the
current execution phase of Claude Code without manual parsing of terminal output.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import re


class TerminalState(Enum):
    """
    Low-level terminal output state.
    
    Represents the current output behavior of the terminal based on
    stability analysis and pattern matching.
    """
    RUNNING = "running"
    INTERACTIVE = "interactive"
    COMPLETED = "completed"


class TaskStatus(Enum):
    """
    High-level step execution status.
    
    Represents the execution phase of a task, tracking progress from
    initialization through completion or failure.
    """
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    FAILED = "failed"


class InteractionType(Enum):
    """
    Types of interactive prompts detected in terminal output.
    
    These are checked in priority order to ensure the most specific
    pattern is matched first.
    """
    PERMISSION_CONFIRM = "permission_confirm"
    HIGHLIGHTED_OPTION = "highlighted_option"
    PLAN_APPROVAL = "plan_approval"
    USER_QUESTION = "user_question"
    SELECTION_MENU = "selection_menu"


@dataclass
class TimingInfo:
    """
    Timing information for task execution.
    
    Tracks when a task started, completed, and the total duration.
    All timestamps are in ISO 8601 format with timezone information.
    """
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds
        }


@dataclass
class StatusDetail:
    """
    Detailed information about the current status.
    
    Provides human-readable description and interaction-specific details
    when the terminal is in an interactive state.
    """
    description: str
    interaction_type: Optional[str] = None
    choices: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "description": self.description,
            "interaction_type": self.interaction_type,
            "choices": self.choices
        }


@dataclass
class StatusResponse:
    """
    The structured response returned by get_status.
    
    Contains all information about the current state of a monitored session,
    including terminal state, task status, stability metrics, and timing.
    """
    terminal_state: TerminalState
    task_status: TaskStatus
    stable_count: int
    detail: StatusDetail
    timing: TimingInfo
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dictionary.
        
        Returns:
            Dictionary with all fields properly formatted for JSON serialization.
        """
        return {
            "terminal_state": self.terminal_state.value,
            "task_status": self.task_status.value,
            "stable_count": self.stable_count,
            "detail": self.detail.to_dict(),
            "timing": self.timing.to_dict()
        }
    
    def to_json(self) -> str:
        """
        Convert to JSON string.
        
        Returns:
            Formatted JSON string representation of the status response.
        """
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class InteractionMatch:
    """
    Result of interactive pattern matching.
    
    Contains the detected interaction type, available choices,
    and the text that matched the pattern.
    """
    interaction_type: InteractionType
    choices: List[str]
    matched_text: str


@dataclass
class InteractionPattern:
    """
    A regex pattern for detecting interactive prompts.
    
    Patterns are checked in priority order, with lower priority values
    being checked first.
    """
    interaction_type: InteractionType
    pattern: Any  # re.Pattern, but using Any to avoid import
    priority: int


@dataclass
class SessionState:
    """
    Tracks the state of a monitored session.
    
    Maintains all information needed to determine the current execution
    phase, including stability tracking, timing, and interaction details.
    """
    session_id: str
    terminal_state: TerminalState = TerminalState.RUNNING
    task_status: TaskStatus = TaskStatus.PENDING
    stable_count: int = 0
    last_output: str = ""
    interaction_type: Optional[InteractionType] = None
    choices: Optional[List[str]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    auto_response_count: int = 0
    description: str = "Session initialized"
    
    def format_timestamp(self, dt: Optional[datetime]) -> Optional[str]:
        """
        Format a datetime object to ISO 8601 string with timezone.
        
        Args:
            dt: The datetime object to format, or None
            
        Returns:
            ISO 8601 formatted string with timezone, or None if input is None
        """
        if dt is None:
            return None
        # Ensure timezone is set
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    
    def calculate_duration(self) -> Optional[float]:
        """
        Calculate duration in seconds between started_at and completed_at.
        
        Returns:
            Duration in seconds, or None if either timestamp is missing
        """
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    def to_status_response(self) -> StatusResponse:
        """
        Convert session state to a StatusResponse.
        
        Returns:
            StatusResponse object with all current state information
        """
        # Create timing info
        timing = TimingInfo(
            started_at=self.format_timestamp(self.started_at),
            completed_at=self.format_timestamp(self.completed_at),
            duration_seconds=self.calculate_duration()
        )
        
        # Create detail info
        detail = StatusDetail(
            description=self.description,
            interaction_type=self.interaction_type.value if self.interaction_type else None,
            choices=self.choices
        )
        
        return StatusResponse(
            terminal_state=self.terminal_state,
            task_status=self.task_status,
            stable_count=self.stable_count,
            detail=detail,
            timing=timing
        )


# Configuration constants
POLLING_INTERVAL_SECONDS = 1.0
INTERACTIVE_STABILITY_THRESHOLD = 2
COMPLETED_STABILITY_THRESHOLD = 5

# Pyte configuration
PYTE_TERMINAL_COLS = 120
PYTE_TERMINAL_ROWS = 50

# Pattern matching configuration
PATTERN_MATCH_LAST_N_LINES = 30

# Auto-response limits
MAX_AUTO_RESPONSES_PER_STEP = 20


class PyteRenderer:
    """
    Renders raw ANSI output to clean screen text using pyte.
    Falls back to regex stripping on failure.

    This class handles local pyte rendering with a configurable terminal size.
    It maintains a pyte Screen and Stream to process ANSI escape sequences
    and extract clean text output.
    """

    def __init__(self, cols: int = PYTE_TERMINAL_COLS, rows: int = PYTE_TERMINAL_ROWS):
        """
        Initialize PyteRenderer with configurable terminal dimensions.

        Args:
            cols: Number of columns for the terminal (default: 120)
            rows: Number of rows for the terminal (default: 50)
        """
        self._cols = cols
        self._rows = rows
        self._screen: Optional[Any] = None  # pyte.Screen
        self._stream: Optional[Any] = None  # pyte.Stream or pyte.ByteStream
        self._initialize_pyte()

    def _initialize_pyte(self) -> None:
        """
        Initialize pyte screen and stream.

        Attempts to import pyte and create Screen and Stream instances.
        Handles both ByteStream (newer pyte versions) and regular Stream.
        """
        try:
            import pyte

            # Create screen with configured dimensions
            self._screen = pyte.Screen(self._cols, self._rows)

            # Try to use ByteStream first (newer pyte versions)
            # If not available, fall back to regular Stream
            try:
                self._stream = pyte.ByteStream(self._screen)
            except AttributeError:
                # Older pyte versions only have Stream
                self._stream = pyte.Stream(self._screen)

        except ImportError:
            # pyte not available, will use regex fallback
            self._screen = None
            self._stream = None


    def render(self, raw_output: str) -> str:
        """
        Render raw ANSI output to clean text.

        Attempts to render using pyte first. If pyte is not available or
        rendering fails, falls back to regex-based ANSI stripping.

        Args:
            raw_output: Terminal output with ANSI escape sequences

        Returns:
            Clean screen text with ANSI codes removed
        """
        try:
            return self._render_with_pyte(raw_output)
        except Exception:
            # Fall back to regex stripping if pyte fails
            return self._render_with_regex(raw_output)

    def _render_with_pyte(self, raw_output: str) -> str:
        """
        Attempt to render using pyte.

        Args:
            raw_output: Terminal output with ANSI escape sequences

        Returns:
            Clean screen text extracted from pyte display buffer

        Raises:
            Exception: If pyte is not available or rendering fails
        """
        if self._screen is None or self._stream is None:
            raise RuntimeError("pyte not available")

        # Reset screen for fresh rendering
        self._screen.reset()

        # Feed output to pyte stream
        # Handle both string and bytes input
        if isinstance(raw_output, str):
            # For ByteStream, encode to bytes
            if hasattr(self._stream, 'feed') and 'Byte' in type(self._stream).__name__:
                self._stream.feed(raw_output.encode('utf-8', errors='replace'))
            else:
                # For regular Stream, feed string directly
                self._stream.feed(raw_output)
        else:
            # Already bytes
            self._stream.feed(raw_output)

        # Extract and clean text from screen buffer
        return self._extract_screen_text()

    def _render_with_regex(self, raw_output: str) -> str:
        """
        Fallback: strip ANSI codes using regex.

        Uses the existing strip_ansi() function from ansi.py module.

        Args:
            raw_output: Terminal output with ANSI escape sequences

        Returns:
            Text with ANSI codes removed
        """
        from terminalcp.ansi import strip_ansi

        # Strip ANSI codes
        clean_text = strip_ansi(raw_output)

        # Apply same cleaning as pyte rendering
        return self._clean_text(clean_text)

    def _extract_screen_text(self) -> str:
        """
        Extract text from pyte screen buffer.

        Iterates through the screen display buffer and extracts text lines,
        then applies cleaning to remove trailing whitespace and invisible
        Unicode characters.

        Returns:
            Clean text extracted from screen buffer
        """
        if self._screen is None:
            return ""

        # Extract lines from screen display buffer
        lines = []
        for row in range(self._rows):
            # Get the line from the screen display
            line = self._screen.display[row]
            lines.append(line)

        # Join lines and clean
        text = '\n'.join(lines)
        return self._clean_text(text)

    def _clean_text(self, text: str) -> str:
        """
        Remove trailing whitespace and invisible Unicode characters.

        Strips trailing whitespace from each line and removes common
        invisible Unicode characters like zero-width spaces, zero-width
        joiners, and other control characters.

        Args:
            text: Text to clean

        Returns:
            Cleaned text with trailing whitespace and invisible characters removed
        """
        # Strip trailing whitespace from each line
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]

        # Remove invisible Unicode characters
        # Zero-width space, zero-width joiner, zero-width non-joiner, etc.
        invisible_chars = [
            '\u200b',  # Zero-width space
            '\u200c',  # Zero-width non-joiner
            '\u200d',  # Zero-width joiner
            '\u200e',  # Left-to-right mark
            '\u200f',  # Right-to-left mark
            '\ufeff',  # Zero-width no-break space (BOM)
        ]

        cleaned_lines = []
        for line in lines:
            for char in invisible_chars:
                line = line.replace(char, '')
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)




class StatusDetector:
    """
    Orchestrates status detection for Claude Code CLI sessions.
    
    Maintains per-session state and coordinates polling, rendering, and pattern matching.
    This class is the main entry point for status monitoring functionality.
    """
    
    def __init__(self, terminal_client: Any):
        """
        Initialize StatusDetector with TerminalClient dependency.
        
        Args:
            terminal_client: The TerminalClient instance for communicating with terminal sessions
        """
        from terminalcp.terminal_detector import TerminalDetector
        
        # Store the terminal client for making requests
        self._client = terminal_client
        
        # Per-session state tracking
        self._session_states: Dict[str, SessionState] = {}
        
        # Cached rendered output for each session (for frontend display)
        self._live_outputs: Dict[str, str] = {}
        
        # Per-session pyte renderers
        self._pyte_renderers: Dict[str, PyteRenderer] = {}
        
        # Terminal detector for pattern matching
        self._terminal_detector = TerminalDetector()
        
        # Configuration constants
        self._polling_interval = POLLING_INTERVAL_SECONDS
        self._interactive_threshold = INTERACTIVE_STABILITY_THRESHOLD
        self._completed_threshold = COMPLETED_STABILITY_THRESHOLD

    async def _poll_session(self, session_id: str) -> None:
        """
        Execute one polling cycle for a session.

        Updates state based on output changes and pattern matching.
        This method:
        1. Calls stream action with strip_ansi=false to get raw ANSI output
        2. Renders the output using pyte
        3. Compares with previous output to update stable_count
        4. Caches the rendered output

        Args:
            session_id: The terminalcp session identifier

        Raises:
            RuntimeError: If session does not exist or stream action fails
        """
        # Get the session state
        state = self._session_states.get(session_id)
        if not state:
            raise RuntimeError(f"Session not found: {session_id}")

        # Get the pyte renderer for this session (create if needed)
        if session_id not in self._pyte_renderers:
            self._pyte_renderers[session_id] = PyteRenderer()
        renderer = self._pyte_renderers[session_id]

        # Call stream action with strip_ansi=false to get raw ANSI output
        try:
            raw_output = await self._client.request({
                "action": "stream",
                "id": session_id,
                "strip_ansi": False
            })
        except Exception as e:
            raise RuntimeError(f"Failed to get stream output for session {session_id}: {e}")

        # Render the output using pyte
        rendered_output = renderer.render(raw_output)

        # Compare with previous output to update stable_count
        previous_output = state.last_output
        if rendered_output != previous_output:
            # Output changed - reset stable_count to 0
            state.stable_count = 0
        else:
            # Output unchanged - increment stable_count
            state.stable_count += 1

        # Update last_output with current rendered output
        state.last_output = rendered_output

        # Cache rendered output in _live_outputs for frontend access
        self._live_outputs[session_id] = rendered_output

