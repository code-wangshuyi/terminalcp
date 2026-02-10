from __future__ import annotations

from typing import Tuple

# Spinner characters used by Claude Code CLI during processing
SPINNER_CHARS = frozenset("·✢✳✶✻✽")

# Words displayed when a task completes
COMPLETED_WORDS = frozenset({
    "Baked", "Brewed", "Churned", "Cogitated",
    "Cooked", "Crunched", "Sautéed", "Worked",
})

# Interactive prompts that indicate Claude is waiting for user input
INTERACTIVE_PROMPTS = (
    "Should I proceed?",
    "Do you want to proceed?",
    "Would you like to proceed?",
)

# All processing words from Claude Code CLI
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
    """Detect Claude Code CLI interaction state from rendered terminal output.

    Returns:
        (state, detail) where state is one of:
        - "interactive": waiting for user confirmation
        - "completed": task finished
        - "processing": actively working
        - "idle": none of the above
    """
    if not output:
        return ("idle", "")

    lines = output.split("\n")

    # Remove trailing blank lines
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return ("idle", "")

    # 1. Check for interactive prompts (last 5 lines)
    for line in reversed(lines[-5:]):
        stripped = line.strip()
        for prompt in INTERACTIVE_PROMPTS:
            if prompt in stripped:
                return ("interactive", prompt)

    # 2. Check for completed state (last 3 lines)
    for line in reversed(lines[-3:]):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped[0] == "✻":
            rest = stripped[1:].strip()
            if rest in COMPLETED_WORDS:
                return ("completed", rest)

    # 3. Check for processing state (last 3 lines)
    for line in reversed(lines[-3:]):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped[0] in SPINNER_CHARS:
            rest = stripped[1:].strip()
            if rest:
                # Could be a processing word or a system status message
                first_word = rest.split()[0] if rest.split() else ""
                if first_word in PROCESSING_WORDS or rest.endswith("…"):
                    return ("processing", rest)

    return ("idle", "")


def detect_claude_mode(output: str) -> str:
    """Detect Claude Code CLI prompt mode from rendered terminal output.

    Returns:
        "plan", "accept-edits", or "default"
    """
    if not output:
        return "default"

    lines = output.split("\n")

    # Scan last 10 lines for mode indicators
    for line in lines[-10:]:
        if "⏸" in line and "plan" in line.lower():
            return "plan"
        if "⏵⏵" in line and "accept" in line.lower():
            return "accept-edits"

    return "default"
