"""
Terminal pattern detection for Claude Code CLI sessions.

This module provides pattern matching capabilities to detect interactive prompts
and idle states in terminal output. It uses regex patterns checked in priority
order to identify different types of user interactions.
"""

import re
from typing import List, Optional
from terminalcp.status_detector import InteractionType, InteractionMatch, InteractionPattern


class TerminalDetector:
    """
    Detects interactive prompts and idle states using regex patterns.
    
    Patterns are checked in priority order to ensure the most specific
    pattern is matched first. This prevents generic patterns from
    matching before more specific ones.
    """
    
    def __init__(self):
        """Initialize TerminalDetector with compiled patterns."""
        self._patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> List[InteractionPattern]:
        """
        Compile regex patterns for each interaction type.
        
        Patterns are ordered by priority (lower number = higher priority).
        The priority order is:
        1. permission_confirm - Most specific, matches permission requests
        2. highlighted_option - Matches highlighted menu options with ❯
        3. plan_approval - Matches plan/action approval prompts
        4. user_question - Matches general questions to the user
        5. selection_menu - Most generic, matches any menu-like structure
        
        Returns:
            List of InteractionPattern objects sorted by priority
        """
        patterns = [
            # Priority 1: Permission confirmation
            # Matches: "Allow tool X?" or "Allow tool X? Yes/No"
            InteractionPattern(
                interaction_type=InteractionType.PERMISSION_CONFIRM,
                pattern=re.compile(
                    r'Allow\s+tool\s+\w+\?',
                    re.IGNORECASE | re.MULTILINE
                ),
                priority=1
            ),
            
            # Priority 2: Highlighted option
            # Matches: "❯ Yes" or "❯ Option text"
            # This indicates a menu with a highlighted selection
            InteractionPattern(
                interaction_type=InteractionType.HIGHLIGHTED_OPTION,
                pattern=re.compile(
                    r'❯\s+\w+',
                    re.MULTILINE
                ),
                priority=2
            ),
            
            # Priority 3: Plan approval
            # Matches: "Proceed?" or "Proceed with this plan?"
            InteractionPattern(
                interaction_type=InteractionType.PLAN_APPROVAL,
                pattern=re.compile(
                    r'Proceed(\s+with)?.*\?',
                    re.IGNORECASE | re.MULTILINE
                ),
                priority=3
            ),
            
            # Priority 4: User question
            # Matches: "Do you want to..." or "Would you like to..."
            InteractionPattern(
                interaction_type=InteractionType.USER_QUESTION,
                pattern=re.compile(
                    r'(Do\s+you\s+want|Would\s+you\s+like|Should\s+I)',
                    re.IGNORECASE | re.MULTILINE
                ),
                priority=4
            ),
            
            # Priority 5: Selection menu
            # Matches: Multiple lines with options, possibly numbered or bulleted
            # This is the most generic pattern
            InteractionPattern(
                interaction_type=InteractionType.SELECTION_MENU,
                pattern=re.compile(
                    r'(?:^\s*[\d\-\*\+]\s+\w+.*(?:\n|$)){2,}',
                    re.MULTILINE
                ),
                priority=5
            ),
        ]
        
        # Sort by priority (lower number first)
        return sorted(patterns, key=lambda p: p.priority)
    
    def detect_interactive(self, text_lines: List[str]) -> Optional[InteractionMatch]:
        """
        Check for interactive prompts in the given text.
        
        Patterns are checked in priority order. The first matching pattern
        determines the interaction type. Choices are then extracted from
        the matched text.
        
        Args:
            text_lines: The last N lines of rendered output
            
        Returns:
            InteractionMatch if a pattern is found, None otherwise
        """
        # Join lines into single text for pattern matching
        text = '\n'.join(text_lines)
        
        # Check patterns in priority order using individual checker methods
        # Priority 1: Permission confirmation
        result = self._check_permission_confirm(text)
        if result:
            return result
        
        # Priority 2: Highlighted option
        result = self._check_highlighted_option(text)
        if result:
            return result
        
        # Priority 3: Plan approval
        result = self._check_plan_approval(text)
        if result:
            return result
        
        # Priority 4: User question
        result = self._check_user_question(text)
        if result:
            return result
        
        # Priority 5: Selection menu
        result = self._check_selection_menu(text)
        if result:
            return result
        
        return None
    
    def detect_idle_prompt(self, text: str) -> bool:
        """
        Check if the text contains an idle prompt (❯ with no following text).
        
        An idle prompt indicates that Claude Code has finished its current
        task and is waiting for a new prompt from the user.
        
        Args:
            text: The rendered screen text
            
        Returns:
            True if idle prompt is detected
        """
        # Pattern: ❯ followed by only whitespace or end of line
        # The $ anchor matches end of line in MULTILINE mode
        idle_pattern = re.compile(r'❯\s*$', re.MULTILINE)
        return idle_pattern.search(text) is not None
    
    def _check_permission_confirm(self, text: str) -> Optional[InteractionMatch]:
        """
        Check for permission confirmation patterns.
        
        Matches patterns like:
        - "Allow tool X?"
        - "Allow tool file_editor? Yes/No"
        
        Args:
            text: The text to check
            
        Returns:
            InteractionMatch if pattern is found, None otherwise
        """
        pattern = re.compile(r'Allow\s+tool\s+\w+\?', re.IGNORECASE | re.MULTILINE)
        match = pattern.search(text)
        
        if match:
            matched_text = match.group(0)
            choices = self._extract_choices(text, InteractionType.PERMISSION_CONFIRM)
            
            return InteractionMatch(
                interaction_type=InteractionType.PERMISSION_CONFIRM,
                choices=choices,
                matched_text=matched_text
            )
        
        return None
    
    def _check_highlighted_option(self, text: str) -> Optional[InteractionMatch]:
        """
        Check for highlighted option patterns.
        
        Matches patterns like:
        - "❯ Yes"
        - "❯ Option text"
        
        This indicates a menu with a highlighted selection.
        
        Args:
            text: The text to check
            
        Returns:
            InteractionMatch if pattern is found, None otherwise
        """
        pattern = re.compile(r'❯\s+\w+', re.MULTILINE)
        match = pattern.search(text)
        
        if match:
            matched_text = match.group(0)
            choices = self._extract_choices(text, InteractionType.HIGHLIGHTED_OPTION)
            
            return InteractionMatch(
                interaction_type=InteractionType.HIGHLIGHTED_OPTION,
                choices=choices,
                matched_text=matched_text
            )
        
        return None
    
    def _check_plan_approval(self, text: str) -> Optional[InteractionMatch]:
        """
        Check for plan approval patterns.
        
        Matches patterns like:
        - "Proceed?"
        - "Proceed with this plan?"
        
        Args:
            text: The text to check
            
        Returns:
            InteractionMatch if pattern is found, None otherwise
        """
        pattern = re.compile(r'Proceed(\s+with)?.*\?', re.IGNORECASE | re.MULTILINE)
        match = pattern.search(text)
        
        if match:
            matched_text = match.group(0)
            choices = self._extract_choices(text, InteractionType.PLAN_APPROVAL)
            
            return InteractionMatch(
                interaction_type=InteractionType.PLAN_APPROVAL,
                choices=choices,
                matched_text=matched_text
            )
        
        return None
    
    def _check_user_question(self, text: str) -> Optional[InteractionMatch]:
        """
        Check for user question patterns.
        
        Matches patterns like:
        - "Do you want to..."
        - "Would you like to..."
        - "Should I..."
        
        Args:
            text: The text to check
            
        Returns:
            InteractionMatch if pattern is found, None otherwise
        """
        pattern = re.compile(r'(Do\s+you\s+want|Would\s+you\s+like|Should\s+I)', re.IGNORECASE | re.MULTILINE)
        match = pattern.search(text)
        
        if match:
            matched_text = match.group(0)
            choices = self._extract_choices(text, InteractionType.USER_QUESTION)
            
            return InteractionMatch(
                interaction_type=InteractionType.USER_QUESTION,
                choices=choices,
                matched_text=matched_text
            )
        
        return None
    
    def _check_selection_menu(self, text: str) -> Optional[InteractionMatch]:
        """
        Check for selection menu patterns.
        
        Matches patterns like:
        - Multiple numbered lines: "1. Option"
        - Multiple bulleted lines: "- Option"
        
        This is the most generic pattern.
        
        Args:
            text: The text to check
            
        Returns:
            InteractionMatch if pattern is found, None otherwise
        """
        # Check if we have at least 2 lines that look like menu items
        lines = text.split('\n')
        matching_lines = []
        
        for line in lines:
            # Match numbered items: "1. Option" or "1) Option"
            # Or bulleted items: "- Option", "* Option", "+ Option"
            if re.match(r'^\s*[\d\-\*\+][\.\)]*\s+\w+', line):
                matching_lines.append(line)
        
        # Need at least 2 matching lines for a menu
        if len(matching_lines) >= 2:
            # Use the first matching line as the matched text
            matched_text = '\n'.join(matching_lines)
            choices = self._extract_choices(text, InteractionType.SELECTION_MENU)
            
            return InteractionMatch(
                interaction_type=InteractionType.SELECTION_MENU,
                choices=choices,
                matched_text=matched_text
            )
        
        return None
    
    def _extract_choices(self, text: str, pattern_type: InteractionType) -> List[str]:
        """
        Extract available choices from matched text.
        
        Different interaction types have different choice formats:
        - permission_confirm: Usually "Yes" and "No"
        - highlighted_option: Extract all options from menu (lines with ❯ or plain text)
        - plan_approval: Usually "Yes" and "No" or "Proceed" and "Cancel"
        - user_question: Extract from context (Yes/No or other options)
        - selection_menu: Extract numbered or bulleted items
        
        Args:
            text: The full text containing the interaction
            pattern_type: The type of interaction detected
            
        Returns:
            List of available choices as strings
        """
        choices = []
        
        if pattern_type == InteractionType.PERMISSION_CONFIRM:
            # Look for explicit Yes/No in the text
            if re.search(r'\bYes\b', text, re.IGNORECASE):
                choices.append("Yes")
            if re.search(r'\bNo\b', text, re.IGNORECASE):
                choices.append("No")
            
            # If no explicit choices found, default to Yes/No
            if not choices:
                choices = ["Yes", "No"]
        
        elif pattern_type == InteractionType.HIGHLIGHTED_OPTION:
            # Extract all lines that look like menu options
            # Look for lines with ❯ or lines that are indented options
            lines = text.split('\n')
            for line in lines:
                # Match lines with ❯ or indented text that looks like an option
                if '❯' in line:
                    # Extract text after ❯
                    option_match = re.search(r'❯\s+(.+)', line)
                    if option_match:
                        choices.append(option_match.group(1).strip())
                elif re.match(r'^\s{2,}(\w+)', line):
                    # Indented option without ❯
                    option_match = re.match(r'^\s{2,}(.+)', line)
                    if option_match:
                        option_text = option_match.group(1).strip()
                        if option_text and not option_text.startswith('❯'):
                            choices.append(option_text)
        
        elif pattern_type == InteractionType.PLAN_APPROVAL:
            # Look for common approval choices
            if re.search(r'\bYes\b', text, re.IGNORECASE):
                choices.append("Yes")
            if re.search(r'\bNo\b', text, re.IGNORECASE):
                choices.append("No")
            if re.search(r'\bProceed\b', text, re.IGNORECASE):
                choices.append("Proceed")
            if re.search(r'\bCancel\b', text, re.IGNORECASE):
                choices.append("Cancel")
            
            # Default if nothing found
            if not choices:
                choices = ["Yes", "No"]
        
        elif pattern_type == InteractionType.USER_QUESTION:
            # Look for Yes/No or other common responses
            if re.search(r'\bYes\b', text, re.IGNORECASE):
                choices.append("Yes")
            if re.search(r'\bNo\b', text, re.IGNORECASE):
                choices.append("No")
            
            # Default if nothing found
            if not choices:
                choices = ["Yes", "No"]
        
        elif pattern_type == InteractionType.SELECTION_MENU:
            # Extract numbered or bulleted items
            lines = text.split('\n')
            for line in lines:
                # Match numbered items: "1. Option" or "1) Option"
                numbered_match = re.match(r'^\s*\d+[\.\)]\s+(.+)', line)
                if numbered_match:
                    choices.append(numbered_match.group(1).strip())
                    continue
                
                # Match bulleted items: "- Option" or "* Option" or "+ Option"
                bulleted_match = re.match(r'^\s*[\-\*\+]\s+(.+)', line)
                if bulleted_match:
                    choices.append(bulleted_match.group(1).strip())
        
        return choices
