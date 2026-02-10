"""
Claude Code CLI 会话的终端模式检测。

本模块提供模式匹配能力，用于检测终端输出中的交互式提示
和空闲状态。它使用按优先级排序的正则模式来识别不同类型的用户交互。
"""

import re
from typing import List, Optional
from terminalcp.status_detector import InteractionType, InteractionMatch, InteractionPattern


class TerminalDetector:
    """
    使用正则模式检测交互式提示和空闲状态。

    模式按优先级顺序检查，确保最具体的模式最先匹配。
    这防止了通用模式在更具体的模式之前匹配。
    """
    
    def __init__(self):
        """使用编译后的模式初始化 TerminalDetector。"""
        self._patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> List[InteractionPattern]:
        """
        为每种交互类型编译正则模式。

        模式按优先级排序（数字越小优先级越高）。
        优先级顺序为：
        1. permission_confirm - 最具体，匹配权限请求
        2. highlighted_option - 匹配带 ❯ 的高亮菜单选项
        3. plan_approval - 匹配计划/操作批准提示
        4. user_question - 匹配向用户提出的一般问题
        5. selection_menu - 最通用，匹配任何菜单结构

        返回:
            按优先级排序的 InteractionPattern 对象列表
        """
        patterns = [
            # 优先级 1：权限确认
            # 匹配："Allow tool X?" 或 "Allow tool X? Yes/No"
            InteractionPattern(
                interaction_type=InteractionType.PERMISSION_CONFIRM,
                pattern=re.compile(
                    r'Allow\s+tool\s+\w+\?',
                    re.IGNORECASE | re.MULTILINE
                ),
                priority=1
            ),
            
            # 优先级 2：高亮选项
            # 匹配："❯ Yes" 或 "❯ Option text"
            # 表示带有高亮选择的菜单
            InteractionPattern(
                interaction_type=InteractionType.HIGHLIGHTED_OPTION,
                pattern=re.compile(
                    r'❯\s+\w+',
                    re.MULTILINE
                ),
                priority=2
            ),
            
            # 优先级 3：计划批准
            # 匹配："Proceed?" 或 "Proceed with this plan?"
            InteractionPattern(
                interaction_type=InteractionType.PLAN_APPROVAL,
                pattern=re.compile(
                    r'Proceed(\s+with)?.*\?',
                    re.IGNORECASE | re.MULTILINE
                ),
                priority=3
            ),
            
            # 优先级 4：用户问题
            # 匹配："Do you want to..." 或 "Would you like to..."
            InteractionPattern(
                interaction_type=InteractionType.USER_QUESTION,
                pattern=re.compile(
                    r'(Do\s+you\s+want|Would\s+you\s+like|Should\s+I)',
                    re.IGNORECASE | re.MULTILINE
                ),
                priority=4
            ),
            
            # 优先级 5：选择菜单
            # 匹配：多行选项，可能带编号或项目符号
            # 这是最通用的模式
            InteractionPattern(
                interaction_type=InteractionType.SELECTION_MENU,
                pattern=re.compile(
                    r'(?:^\s*[\d\-\*\+]\s+\w+.*(?:\n|$)){2,}',
                    re.MULTILINE
                ),
                priority=5
            ),
        ]
        
        # 按优先级排序（数字越小越先）
        return sorted(patterns, key=lambda p: p.priority)
    
    def detect_interactive(self, text_lines: List[str]) -> Optional[InteractionMatch]:
        """
        检查给定文本中的交互式提示。

        按优先级顺序检查模式。第一个匹配的模式
        决定交互类型。然后从匹配的文本中提取选项。

        参数:
            text_lines: 渲染输出的最后 N 行

        返回:
            如果找到模式则返回 InteractionMatch，否则返回 None
        """
        # 将行合并为单个文本以进行模式匹配
        text = '\n'.join(text_lines)
        
        # 使用各检查方法按优先级顺序检查模式
        # 优先级 1：权限确认
        result = self._check_permission_confirm(text)
        if result:
            return result
        
        # 优先级 2：高亮选项
        result = self._check_highlighted_option(text)
        if result:
            return result
        
        # 优先级 3：计划批准
        result = self._check_plan_approval(text)
        if result:
            return result
        
        # 优先级 4：用户问题
        result = self._check_user_question(text)
        if result:
            return result
        
        # 优先级 5：选择菜单
        result = self._check_selection_menu(text)
        if result:
            return result
        
        return None
    
    def detect_idle_prompt(self, text: str) -> bool:
        """
        检查文本是否包含空闲提示（❯ 后无跟随文本）。

        空闲提示表示 Claude Code 已完成当前任务，
        正在等待用户的新提示。

        参数:
            text: 渲染后的屏幕文本

        返回:
            如果检测到空闲提示则返回 True
        """
        # 模式：❯ 后仅跟空白或行尾
        # $ 锚点在 MULTILINE 模式下匹配行尾
        idle_pattern = re.compile(r'❯\s*$', re.MULTILINE)
        return idle_pattern.search(text) is not None
    
    def _check_permission_confirm(self, text: str) -> Optional[InteractionMatch]:
        """
        检查权限确认模式。

        匹配如下模式：
        - "Allow tool X?"
        - "Allow tool file_editor? Yes/No"

        参数:
            text: 要检查的文本

        返回:
            如果找到模式则返回 InteractionMatch，否则返回 None
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
        检查高亮选项模式。

        匹配如下模式：
        - "❯ Yes"
        - "❯ Option text"

        表示带有高亮选择的菜单。

        参数:
            text: 要检查的文本

        返回:
            如果找到模式则返回 InteractionMatch，否则返回 None
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
        检查计划批准模式。

        匹配如下模式：
        - "Proceed?"
        - "Proceed with this plan?"

        参数:
            text: 要检查的文本

        返回:
            如果找到模式则返回 InteractionMatch，否则返回 None
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
        检查用户问题模式。

        匹配如下模式：
        - "Do you want to..."
        - "Would you like to..."
        - "Should I..."

        参数:
            text: 要检查的文本

        返回:
            如果找到模式则返回 InteractionMatch，否则返回 None
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
        检查选择菜单模式。

        匹配如下模式：
        - 多行编号项："1. Option"
        - 多行项目符号项："- Option"

        这是最通用的模式。

        参数:
            text: 要检查的文本

        返回:
            如果找到模式则返回 InteractionMatch，否则返回 None
        """
        # 检查是否至少有 2 行看起来像菜单项
        lines = text.split('\n')
        matching_lines = []
        
        for line in lines:
            # 匹配编号项："1. Option" 或 "1) Option"
            # 或项目符号项："- Option"、"* Option"、"+ Option"
            if re.match(r'^\s*[\d\-\*\+][\.\)]*\s+\w+', line):
                matching_lines.append(line)
        
        # 菜单至少需要 2 个匹配行
        if len(matching_lines) >= 2:
            # 使用第一个匹配行作为匹配文本
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
        从匹配的文本中提取可用选项。

        不同交互类型有不同的选项格式：
        - permission_confirm: 通常是 "Yes" 和 "No"
        - highlighted_option: 从菜单中提取所有选项（带 ❯ 的行或纯文本）
        - plan_approval: 通常是 "Yes" 和 "No" 或 "Proceed" 和 "Cancel"
        - user_question: 从上下文提取（Yes/No 或其他选项）
        - selection_menu: 提取编号或项目符号项

        参数:
            text: 包含交互的完整文本
            pattern_type: 检测到的交互类型

        返回:
            可用选项的字符串列表
        """
        choices = []
        
        if pattern_type == InteractionType.PERMISSION_CONFIRM:
            # 在文本中查找显式的 Yes/No
            if re.search(r'\bYes\b', text, re.IGNORECASE):
                choices.append("Yes")
            if re.search(r'\bNo\b', text, re.IGNORECASE):
                choices.append("No")
            
            # 如果未找到显式选项，默认为 Yes/No
            if not choices:
                choices = ["Yes", "No"]
        
        elif pattern_type == InteractionType.HIGHLIGHTED_OPTION:
            # 提取所有看起来像菜单选项的行
            # 查找带 ❯ 的行或缩进的选项行
            lines = text.split('\n')
            for line in lines:
                # 匹配带 ❯ 的行或看起来像选项的缩进文本
                if '❯' in line:
                    # 提取 ❯ 后的文本
                    option_match = re.search(r'❯\s+(.+)', line)
                    if option_match:
                        choices.append(option_match.group(1).strip())
                elif re.match(r'^\s{2,}(\w+)', line):
                    # 不带 ❯ 的缩进选项
                    option_match = re.match(r'^\s{2,}(.+)', line)
                    if option_match:
                        option_text = option_match.group(1).strip()
                        if option_text and not option_text.startswith('❯'):
                            choices.append(option_text)
        
        elif pattern_type == InteractionType.PLAN_APPROVAL:
            # 查找常见的批准选项
            if re.search(r'\bYes\b', text, re.IGNORECASE):
                choices.append("Yes")
            if re.search(r'\bNo\b', text, re.IGNORECASE):
                choices.append("No")
            if re.search(r'\bProceed\b', text, re.IGNORECASE):
                choices.append("Proceed")
            if re.search(r'\bCancel\b', text, re.IGNORECASE):
                choices.append("Cancel")
            
            # 未找到时的默认值
            if not choices:
                choices = ["Yes", "No"]

        elif pattern_type == InteractionType.USER_QUESTION:
            # 查找 Yes/No 或其他常见回复
            if re.search(r'\bYes\b', text, re.IGNORECASE):
                choices.append("Yes")
            if re.search(r'\bNo\b', text, re.IGNORECASE):
                choices.append("No")
            
            # 未找到时的默认值
            if not choices:
                choices = ["Yes", "No"]

        elif pattern_type == InteractionType.SELECTION_MENU:
            # 提取编号或项目符号项
            lines = text.split('\n')
            for line in lines:
                # 匹配编号项："1. Option" 或 "1) Option"
                numbered_match = re.match(r'^\s*\d+[\.\)]\s+(.+)', line)
                if numbered_match:
                    choices.append(numbered_match.group(1).strip())
                    continue
                
                # 匹配项目符号项："- Option" 或 "* Option" 或 "+ Option"
                bulleted_match = re.match(r'^\s*[\-\*\+]\s+(.+)', line)
                if bulleted_match:
                    choices.append(bulleted_match.group(1).strip())
        
        return choices
