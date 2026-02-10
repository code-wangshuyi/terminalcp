"""
Claude Code CLI 会话的状态检测。

本模块为 terminalcp 提供实时状态监控能力，
使自动化编排系统能够以编程方式确定 Claude Code 的
当前执行阶段，而无需手动解析终端输出。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import re


class TerminalState(Enum):
    """
    底层终端输出状态。

    基于稳定性分析和模式匹配，表示终端的当前输出行为。
    """
    RUNNING = "running"
    INTERACTIVE = "interactive"
    COMPLETED = "completed"


class TaskStatus(Enum):
    """
    高层任务执行状态。

    表示任务的执行阶段，跟踪从初始化到完成或失败的进度。
    """
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    COMPLETED = "completed"
    FAILED = "failed"


class InteractionType(Enum):
    """
    终端输出中检测到的交互提示类型。

    按优先级顺序检查，确保最具体的模式最先匹配。
    """
    PERMISSION_CONFIRM = "permission_confirm"
    HIGHLIGHTED_OPTION = "highlighted_option"
    PLAN_APPROVAL = "plan_approval"
    USER_QUESTION = "user_question"
    SELECTION_MENU = "selection_menu"


@dataclass
class TimingInfo:
    """
    任务执行的计时信息。

    跟踪任务的开始时间、完成时间和总持续时间。
    所有时间戳均为 ISO 8601 格式并带时区信息。
    """
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为 JSON 可序列化的字典。"""
        return {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds
        }


@dataclass
class StatusDetail:
    """
    当前状态的详细信息。

    提供人类可读的描述以及终端处于交互状态时的交互相关详情。
    """
    description: str
    interaction_type: Optional[str] = None
    choices: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为 JSON 可序列化的字典。"""
        return {
            "description": self.description,
            "interaction_type": self.interaction_type,
            "choices": self.choices
        }


@dataclass
class StatusResponse:
    """
    get_status 返回的结构化响应。

    包含被监控会话的当前状态的所有信息，
    包括终端状态、任务状态、稳定性指标和计时。
    """
    terminal_state: TerminalState
    task_status: TaskStatus
    stable_count: int
    detail: StatusDetail
    timing: TimingInfo
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为 JSON 可序列化的字典。

        返回:
            所有字段均正确格式化以便 JSON 序列化的字典。
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
        转换为 JSON 字符串。

        返回:
            状态响应的格式化 JSON 字符串表示。
        """
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class InteractionMatch:
    """
    交互模式匹配的结果。

    包含检测到的交互类型、可用选项和匹配的文本。
    """
    interaction_type: InteractionType
    choices: List[str]
    matched_text: str


@dataclass
class InteractionPattern:
    """
    用于检测交互式提示的正则模式。

    模式按优先级顺序检查，优先级值越低越先检查。
    """
    interaction_type: InteractionType
    pattern: Any  # re.Pattern, but using Any to avoid import
    priority: int


@dataclass
class SessionState:
    """
    跟踪被监控会话的状态。

    维护确定当前执行阶段所需的所有信息，
    包括稳定性跟踪、计时和交互详情。
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
        将 datetime 对象格式化为带时区的 ISO 8601 字符串。

        参数:
            dt: 要格式化的 datetime 对象，或 None

        返回:
            带时区的 ISO 8601 格式字符串，如果输入为 None 则返回 None
        """
        if dt is None:
            return None
        # 确保时区已设置
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    
    def calculate_duration(self) -> Optional[float]:
        """
        计算 started_at 和 completed_at 之间的持续时间（秒）。

        返回:
            持续时间（秒），如果任一时间戳缺失则返回 None
        """
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()
    
    def to_status_response(self) -> StatusResponse:
        """
        将会话状态转换为 StatusResponse。

        返回:
            包含所有当前状态信息的 StatusResponse 对象
        """
        # 创建计时信息
        timing = TimingInfo(
            started_at=self.format_timestamp(self.started_at),
            completed_at=self.format_timestamp(self.completed_at),
            duration_seconds=self.calculate_duration()
        )
        
        # 创建详情信息
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


# 配置常量
POLLING_INTERVAL_SECONDS = 1.0
INTERACTIVE_STABILITY_THRESHOLD = 2
COMPLETED_STABILITY_THRESHOLD = 5

# Pyte 配置
PYTE_TERMINAL_COLS = 120
PYTE_TERMINAL_ROWS = 50

# 模式匹配配置
PATTERN_MATCH_LAST_N_LINES = 30

# 自动响应限制
MAX_AUTO_RESPONSES_PER_STEP = 20


class PyteRenderer:
    """
    使用 pyte 将原始 ANSI 输出渲染为干净的屏幕文本。
    渲染失败时回退到正则表达式剥离。

    本类使用可配置的终端尺寸处理本地 pyte 渲染。
    它维护一个 pyte Screen 和 Stream 来处理 ANSI 转义序列
    并提取干净的文本输出。
    """

    def __init__(self, cols: int = PYTE_TERMINAL_COLS, rows: int = PYTE_TERMINAL_ROWS):
        """
        使用可配置的终端尺寸初始化 PyteRenderer。

        参数:
            cols: 终端列数（默认：120）
            rows: 终端行数（默认：50）
        """
        self._cols = cols
        self._rows = rows
        self._screen: Optional[Any] = None  # pyte.Screen
        self._stream: Optional[Any] = None  # pyte.Stream or pyte.ByteStream
        self._initialize_pyte()

    def _initialize_pyte(self) -> None:
        """
        初始化 pyte screen 和 stream。

        尝试导入 pyte 并创建 Screen 和 Stream 实例。
        同时处理 ByteStream（较新 pyte 版本）和普通 Stream。
        """
        try:
            import pyte

            # 使用配置的尺寸创建屏幕
            self._screen = pyte.Screen(self._cols, self._rows)

            # 优先尝试使用 ByteStream（较新的 pyte 版本）
            # 如不可用，回退到普通 Stream
            try:
                self._stream = pyte.ByteStream(self._screen)
            except AttributeError:
                # 较旧的 pyte 版本只有 Stream
                self._stream = pyte.Stream(self._screen)

        except ImportError:
            # pyte 不可用，将使用正则回退
            self._screen = None
            self._stream = None


    def render(self, raw_output: str) -> str:
        """
        将原始 ANSI 输出渲染为干净文本。

        优先尝试使用 pyte 渲染。如果 pyte 不可用或
        渲染失败，回退到基于正则的 ANSI 剥离。

        参数:
            raw_output: 包含 ANSI 转义序列的终端输出

        返回:
            移除了 ANSI 码的干净屏幕文本
        """
        try:
            return self._render_with_pyte(raw_output)
        except Exception:
            # pyte 失败时回退到正则剥离
            return self._render_with_regex(raw_output)

    def _render_with_pyte(self, raw_output: str) -> str:
        """
        尝试使用 pyte 渲染。

        参数:
            raw_output: 包含 ANSI 转义序列的终端输出

        返回:
            从 pyte 显示缓冲区提取的干净屏幕文本

        异常:
            Exception: 当 pyte 不可用或渲染失败时
        """
        if self._screen is None or self._stream is None:
            raise RuntimeError("pyte not available")

        # 重置屏幕以进行新的渲染
        self._screen.reset()

        # 将输出送入 pyte 流
        # 处理字符串和字节输入
        if isinstance(raw_output, str):
            # 对于 ByteStream，编码为字节
            if hasattr(self._stream, 'feed') and 'Byte' in type(self._stream).__name__:
                self._stream.feed(raw_output.encode('utf-8', errors='replace'))
            else:
                # 对于普通 Stream，直接送入字符串
                self._stream.feed(raw_output)
        else:
            # 已经是字节
            self._stream.feed(raw_output)

        # 从屏幕缓冲区提取并清理文本
        return self._extract_screen_text()

    def _render_with_regex(self, raw_output: str) -> str:
        """
        回退方案：使用正则表达式剥离 ANSI 码。

        使用 ansi.py 模块中现有的 strip_ansi() 函数。

        参数:
            raw_output: 包含 ANSI 转义序列的终端输出

        返回:
            移除了 ANSI 码的文本
        """
        from terminalcp.ansi import strip_ansi

        # 剥离 ANSI 码
        clean_text = strip_ansi(raw_output)

        # 应用与 pyte 渲染相同的清理
        return self._clean_text(clean_text)

    def _extract_screen_text(self) -> str:
        """
        从 pyte 屏幕缓冲区提取文本。

        遍历屏幕显示缓冲区并提取文本行，
        然后进行清理以移除尾部空白和不可见 Unicode 字符。

        返回:
            从屏幕缓冲区提取的干净文本
        """
        if self._screen is None:
            return ""

        # 从屏幕显示缓冲区提取行
        lines = []
        for row in range(self._rows):
            # 从屏幕显示获取行
            line = self._screen.display[row]
            lines.append(line)

        # 合并行并清理
        text = '\n'.join(lines)
        return self._clean_text(text)

    def _clean_text(self, text: str) -> str:
        """
        移除尾部空白和不可见 Unicode 字符。

        从每行剥离尾部空白，并移除常见的不可见 Unicode 字符，
        如零宽空格、零宽连接符和其他控制字符。

        参数:
            text: 要清理的文本

        返回:
            移除了尾部空白和不可见字符的干净文本
        """
        # 从每行剥离尾部空白
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]

        # 移除不可见 Unicode 字符
        # 零宽空格、零宽连接符、零宽非连接符等
        invisible_chars = [
            '\u200b',  # 零宽空格
            '\u200c',  # 零宽非连接符
            '\u200d',  # 零宽连接符
            '\u200e',  # 从左到右标记
            '\u200f',  # 从右到左标记
            '\ufeff',  # 零宽不换行空格（BOM）
        ]

        cleaned_lines = []
        for line in lines:
            for char in invisible_chars:
                line = line.replace(char, '')
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)




class StatusDetector:
    """
    编排 Claude Code CLI 会话的状态检测。

    维护每个会话的状态，并协调轮询、渲染和模式匹配。
    本类是状态监控功能的主入口点。
    """
    
    def __init__(self, terminal_client: Any):
        """
        使用 TerminalClient 依赖初始化 StatusDetector。

        参数:
            terminal_client: 用于与终端会话通信的 TerminalClient 实例
        """
        from terminalcp.terminal_detector import TerminalDetector
        
        # 存储终端客户端以发送请求
        self._client = terminal_client
        
        # 每个会话的状态跟踪
        self._session_states: Dict[str, SessionState] = {}
        
        # 每个会话的缓存渲染输出（用于前端显示）
        self._live_outputs: Dict[str, str] = {}
        
        # 每个会话的 pyte 渲染器
        self._pyte_renderers: Dict[str, PyteRenderer] = {}
        
        # 用于模式匹配的终端检测器
        self._terminal_detector = TerminalDetector()
        
        # 配置常量
        self._polling_interval = POLLING_INTERVAL_SECONDS
        self._interactive_threshold = INTERACTIVE_STABILITY_THRESHOLD
        self._completed_threshold = COMPLETED_STABILITY_THRESHOLD

    async def _poll_session(self, session_id: str) -> None:
        """
        执行会话的一次轮询周期。

        根据输出变化和模式匹配更新状态。
        本方法：
        1. 调用 stream 操作并设置 strip_ansi=false 获取原始 ANSI 输出
        2. 使用 pyte 渲染输出
        3. 与之前的输出比较以更新 stable_count
        4. 缓存渲染后的输出

        参数:
            session_id: terminalcp 会话标识符

        异常:
            RuntimeError: 如果会话不存在或 stream 操作失败
        """
        # 获取会话状态
        state = self._session_states.get(session_id)
        if not state:
            raise RuntimeError(f"Session not found: {session_id}")

        # 获取此会话的 pyte 渲染器（如需要则创建）
        if session_id not in self._pyte_renderers:
            self._pyte_renderers[session_id] = PyteRenderer()
        renderer = self._pyte_renderers[session_id]

        # 调用 stream 操作并设置 strip_ansi=false 以获取原始 ANSI 输出
        try:
            raw_output = await self._client.request({
                "action": "stream",
                "id": session_id,
                "strip_ansi": False
            })
        except Exception as e:
            raise RuntimeError(f"Failed to get stream output for session {session_id}: {e}")

        # 使用 pyte 渲染输出
        rendered_output = renderer.render(raw_output)

        # 与之前的输出比较以更新 stable_count
        previous_output = state.last_output
        if rendered_output != previous_output:
            # 输出已变化——将 stable_count 重置为 0
            state.stable_count = 0
        else:
            # 输出未变化——递增 stable_count
            state.stable_count += 1

        # 用当前渲染输出更新 last_output
        state.last_output = rendered_output

        # 将渲染输出缓存到 _live_outputs 供前端访问
        self._live_outputs[session_id] = rendered_output

