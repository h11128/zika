"""
State validation rules and business logic.

Defines validation rules for state changes and business constraints.
"""

from typing import List, Any, Dict, Callable
from dataclasses import dataclass

from .ports import StateValidationPort, StateChange, StateChangeType


@dataclass
class ValidationRule:
    """A single validation rule."""
    key_pattern: str  # Can be exact key or pattern like "font_*"
    validator: Callable[[Any], bool]
    error_message: str


class StateRules(StateValidationPort):
    """State validation rules implementation."""
    
    def __init__(self):
        self._rules: List[ValidationRule] = []
        self._setup_default_rules()
    
    def validate_change(self, change: StateChange) -> bool:
        """Validate a state change."""
        errors = self.get_validation_errors(change)
        return len(errors) == 0
    
    def get_validation_errors(self, change: StateChange) -> List[str]:
        """Get validation errors for a change."""
        errors = []
        
        for rule in self._rules:
            if self._key_matches_pattern(change.key, rule.key_pattern):
                if not rule.validator(change.new_value):
                    errors.append(rule.error_message)
        
        return errors
    
    def add_rule(self, key_pattern: str, validator: Callable[[Any], bool], error_message: str) -> None:
        """Add a validation rule."""
        rule = ValidationRule(
            key_pattern=key_pattern,
            validator=validator,
            error_message=error_message
        )
        self._rules.append(rule)
    
    def remove_rules(self, key_pattern: str) -> None:
        """Remove all rules for a key pattern."""
        self._rules = [rule for rule in self._rules if rule.key_pattern != key_pattern]
    
    def _setup_default_rules(self) -> None:
        """Setup default validation rules."""
        # Font size rules
        self.add_rule(
            "hanzi_font_size",
            lambda x: isinstance(x, (int, float)) and 20 <= x <= 80,
            "汉字字体大小必须在20-80之间"
        )
        
        self.add_rule(
            "pinyin_font_size", 
            lambda x: isinstance(x, (int, float)) and 10 <= x <= 40,
            "拼音字体大小必须在10-40之间"
        )
        
        self.add_rule(
            "english_font_size",
            lambda x: isinstance(x, (int, float)) and 8 <= x <= 30,
            "英文字体大小必须在8-30之间"
        )
        
        # Layout rules
        self.add_rule(
            "layout_rows",
            lambda x: isinstance(x, int) and 1 <= x <= 10,
            "行数必须在1-10之间"
        )
        
        self.add_rule(
            "layout_cols",
            lambda x: isinstance(x, int) and 1 <= x <= 10,
            "列数必须在1-10之间"
        )
        
        # Card size rules
        self.add_rule(
            "card_size_cm",
            lambda x: isinstance(x, (int, float)) and 3.0 <= x <= 10.0,
            "卡片大小必须在3.0-10.0cm之间"
        )
        
        # Gap and margin rules
        self.add_rule(
            "gap_cm",
            lambda x: isinstance(x, (int, float)) and 0.1 <= x <= 2.0,
            "卡片间距必须在0.1-2.0cm之间"
        )
        
        self.add_rule(
            "margin_cm",
            lambda x: isinstance(x, (int, float)) and 0.5 <= x <= 3.0,
            "页面边距必须在0.5-3.0cm之间"
        )
        
        # Color rules
        self.add_rule(
            "background_color",
            lambda x: isinstance(x, str) and x.startswith('#') and len(x) in [4, 7],
            "背景颜色必须是有效的十六进制颜色代码"
        )
        
        # Page size rules
        self.add_rule(
            "page_size",
            lambda x: isinstance(x, str) and x in ['A4', 'A3', 'A5', 'Letter'],
            "页面大小必须是支持的格式"
        )
    
    def _key_matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern."""
        if pattern == "*":
            return True
        elif pattern.endswith("*"):
            prefix = pattern[:-1]
            return key.startswith(prefix)
        elif pattern.startswith("*"):
            suffix = pattern[1:]
            return key.endswith(suffix)
        else:
            return key == pattern


# Global rules instance
_state_rules: StateRules = None


def get_state_rules() -> StateRules:
    """Get the global state rules."""
    global _state_rules
    
    if _state_rules is None:
        _state_rules = StateRules()
    
    return _state_rules


def validate_state_change(change: StateChange) -> bool:
    """Validate a state change using global rules."""
    rules = get_state_rules()
    return rules.validate_change(change)
