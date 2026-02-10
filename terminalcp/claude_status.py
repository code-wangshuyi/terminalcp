from __future__ import annotations

import re
from typing import Tuple

# Claude Code CLI 处理过程中使用的旋转字符
SPINNER_CHARS = frozenset("·✢✳✶✻✽")

# 匹配行首旋转字符的正则表达式（允许前导空白）
_SPINNER_RE = re.compile(r"^\s*([·✢✳✶✻✽])\s+(.*)", re.MULTILINE)

# 任务完成时显示的词语
COMPLETED_WORDS = frozenset({
    "Baked", "Brewed", "Churned", "Cogitated",
    "Cooked", "Crunched", "Sautéed", "Worked",
})

# 表示 Claude 正在等待用户输入的交互式提示
INTERACTIVE_PROMPTS = (
    "Should I proceed?",
    "Do you want to proceed?",
    "Would you like to proceed?",
    "Would you like to proceed with this plan?",
    "Proceed with this plan?",
    "Ready to submit your answers?",
)

# Claude Code CLI 所有处理中的状态词
PROCESSING_WORDS = frozenset({
    "Accomplishing", "Actioning", "Actualizing", "Adding", "Architecting",
    "Baking", "Beaming", "Beboppin'", "Befuddling", "Billowing", "Blanching",
    "Bloviating", "Boogieing", "Boondoggling", "Booping", "Bootstrapping",
    "Brewing", "Burrowing", "Calculating", "Canoodling", "Caramelizing",
    "Cascading", "Catapulting", "Cerebrating", "Channeling", "Channelling",
    "Choreographing", "Churning", "Clauding", "Coalescing", "Cogitating",
    "Combobulating", "Composing", "Computing", "Concocting", "Considering",
    "Contemplating", "Cooking", "Crafting", "Creating", "Crunching",
    "Crystallizing", "Cultivating", "Deciphering", "Deliberating",
    "Determining", "Dilly-dallying", "Discombobulating", "Doing", "Doodling",
    "Drizzling", "Ebbing", "Effecting", "Elucidating", "Embellishing",
    "Enchanting", "Envisioning", "Evaporating", "Fermenting",
    "Fiddle-faddling", "Finagling", "Flambéing", "Flibbertigibbeting",
    "Flowing", "Flummoxing", "Fluttering", "Forging", "Forming", "Frolicking",
    "Frosting", "Gallivanting", "Galloping", "Garnishing", "Generating",
    "Germinating", "Gitifying", "Grooving", "Gusting", "Harmonizing",
    "Hashing", "Hatching", "Herding", "Honking", "Hullaballooing",
    "Hyperspacing", "Ideating", "Imagining", "Improvising", "Incubating",
    "Inferring", "Infusing", "Ionizing", "Jitterbugging", "Julienning",
    "Kneading", "Leavening", "Levitating", "Lollygagging", "Manifesting",
    "Marinating", "Meandering", "Metamorphosing", "Misting", "Moonwalking",
    "Moseying", "Mulling", "Mustering", "Musing", "Nebulizing", "Nesting",
    "Newspapering", "Noodling", "Nucleating", "Orbiting", "Orchestrating",
    "Osmosing", "Perambulating", "Percolating", "Perusing", "Philosophising",
    "Photosynthesizing", "Pollinating", "Pondering", "Pontificating",
    "Pouncing", "Precipitating", "Prestidigitating", "Processing",
    "Proofing", "Propagating", "Puttering", "Puzzling", "Quantumizing",
    "Razzle-dazzling", "Razzmatazzing", "Recombobulating", "Reticulating",
    "Roosting", "Ruminating", "Sautéing", "Scampering", "Schlepping",
    "Scurrying", "Seasoning", "Shenaniganing", "Shimmying", "Simmering",
    "Skedaddling", "Sketching", "Slithering", "Smooshing", "Sock-hopping",
    "Spelunking", "Spinning", "Sprouting", "Stewing", "Sublimating",
    "Swirling", "Swooping", "Symbioting", "Synthesizing", "Tempering",
    "Thinking", "Thundering", "Tinkering", "Tomfoolering", "Topsy-turvying",
    "Transfiguring", "Transmuting", "Twisting", "Undulating", "Unfurling",
    "Unravelling", "Vibing", "Waddling", "Wandering", "Warping",
    "Whatchamacalliting", "Whirlpooling", "Whirring", "Whisking", "Wibbling",
    "Working", "Wrangling", "Writing", "Zesting", "Zigzagging",
})


def detect_claude_state(output: str) -> Tuple[str, str]:
    """从渲染后的终端输出中检测 Claude Code CLI 的交互状态。

    从下往上扫描整个可见屏幕以查找状态指示符。

    返回:
        (state, detail)，其中 state 为以下之一：
        - "interactive": 等待用户确认
        - "completed": 任务已完成
        - "processing": 正在执行中
        - "idle": 以上都不是
    """
    if not output:
        return ("idle", "")

    lines = output.split("\n")

    # 1. 检查交互式提示（从下往上扫描所有行）
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for prompt in INTERACTIVE_PROMPTS:
            if prompt in stripped:
                return ("interactive", prompt)

    # 2. 检查旋转字符行（从下往上扫描所有行）
    #    旋转字符表示处理中或已完成状态
    for line in reversed(lines):
        m = _SPINNER_RE.match(line)
        if m:
            rest = m.group(2).strip()
            if not rest:
                continue
            first_word = rest.split()[0] if rest.split() else ""
            # 已完成状态：✻ 后跟完成词
            if first_word in COMPLETED_WORDS:
                return ("completed", first_word)
            # 处理中状态：已知词语或系统状态消息
            if first_word in PROCESSING_WORDS:
                return ("processing", rest)
            if rest.endswith("…") or rest.endswith("..."):
                return ("processing", rest)
            # 旋转字符后跟未知文本——仍可能是处理中
            return ("processing", rest)

    return ("idle", "")


def detect_claude_mode(output: str) -> str:
    """从渲染后的终端输出中检测 Claude Code CLI 的提示模式。

    返回:
        "plan"、"accept-edits" 或 "default"
    """
    if not output:
        return "default"

    lines = output.split("\n")

    # 扫描所有行以查找模式指示符
    for line in lines:
        if "⏸" in line and "plan" in line.lower():
            return "plan"
        if "⏵⏵" in line and "accept" in line.lower():
            return "accept-edits"

    return "default"
