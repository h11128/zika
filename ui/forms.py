"""
Form semantics for atomic UI operations.

Provides form context for batch operations and atomic commits.
"""

import streamlit as st
from typing import Dict, Any, List, Callable, Optional, ContextManager
from dataclasses import dataclass, field
from contextlib import contextmanager

from ui.state import get_state_service
from core.feature_flags import get_feature_flag


@dataclass
class FormField:
    """Represents a form field."""
    key: str
    value: Any
    validator: Optional[Callable[[Any], bool]] = None
    error_message: str = ""


@dataclass
class FormContext:
    """Form context for batch operations."""
    form_id: str
    fields: Dict[str, FormField] = field(default_factory=dict)
    is_submitted: bool = False
    has_errors: bool = False
    submit_callback: Optional[Callable[[Dict[str, Any]], None]] = None


class FormManager:
    """Manages form contexts and batch operations."""
    
    def __init__(self):
        self._active_forms: Dict[str, FormContext] = {}
        self._form_stack: List[str] = []
    
    @contextmanager
    def form_context(self, form_id: str, submit_callback: Callable[[Dict[str, Any]], None] = None) -> ContextManager[FormContext]:
        """Create a form context for batch operations."""
        # Create form context
        context = FormContext(
            form_id=form_id,
            submit_callback=submit_callback
        )
        
        self._active_forms[form_id] = context
        self._form_stack.append(form_id)
        
        try:
            yield context
        finally:
            # Clean up
            if form_id in self._form_stack:
                self._form_stack.remove(form_id)
            self._active_forms.pop(form_id, None)
    
    def get_current_form(self) -> Optional[FormContext]:
        """Get the current active form context."""
        if self._form_stack:
            form_id = self._form_stack[-1]
            return self._active_forms.get(form_id)
        return None
    
    def add_field(self, key: str, value: Any, validator: Callable[[Any], bool] = None, error_message: str = "") -> None:
        """Add a field to the current form."""
        current_form = self.get_current_form()
        if current_form:
            field = FormField(
                key=key,
                value=value,
                validator=validator,
                error_message=error_message
            )
            current_form.fields[key] = field
    
    def validate_form(self, form_id: str) -> bool:
        """Validate all fields in a form."""
        context = self._active_forms.get(form_id)
        if not context:
            return True
        
        has_errors = False
        for field in context.fields.values():
            if field.validator and not field.validator(field.value):
                has_errors = True
                break
        
        context.has_errors = has_errors
        return not has_errors
    
    def submit_form(self, form_id: str) -> bool:
        """Submit a form with batch operations."""
        context = self._active_forms.get(form_id)
        if not context:
            return False
        
        # Validate first
        if not self.validate_form(form_id):
            return False
        
        # Collect all field values
        form_data = {field.key: field.value for field in context.fields.values()}
        
        # Use state service for batch update if available
        if get_feature_flag('state_service', False):
            try:
                state_service = get_state_service()
                state_service.update(form_data)
            except Exception:
                # Fallback to session state
                for key, value in form_data.items():
                    st.session_state[key] = value
        else:
            # Direct session state update
            for key, value in form_data.items():
                st.session_state[key] = value
        
        # Call submit callback if provided
        if context.submit_callback:
            try:
                context.submit_callback(form_data)
            except Exception as e:
                st.error(f"Form submission error: {e}")
                return False
        
        context.is_submitted = True
        return True
    
    def get_form_errors(self, form_id: str) -> List[str]:
        """Get validation errors for a form."""
        context = self._active_forms.get(form_id)
        if not context:
            return []
        
        errors = []
        for field in context.fields.values():
            if field.validator and not field.validator(field.value):
                errors.append(field.error_message or f"Invalid value for {field.key}")
        
        return errors


# Global form manager
_form_manager: FormManager = None


def get_form_manager() -> FormManager:
    """Get the global form manager."""
    global _form_manager
    
    if _form_manager is None:
        _form_manager = FormManager()
    
    return _form_manager


@contextmanager
def form_context(form_id: str, submit_callback: Callable[[Dict[str, Any]], None] = None):
    """Create a form context for batch operations."""
    manager = get_form_manager()
    with manager.form_context(form_id, submit_callback) as context:
        yield context


def add_form_field(key: str, value: Any, validator: Callable[[Any], bool] = None, error_message: str = "") -> None:
    """Add a field to the current form context."""
    manager = get_form_manager()
    manager.add_field(key, value, validator, error_message)


def submit_current_form() -> bool:
    """Submit the current form context."""
    manager = get_form_manager()
    current_form = manager.get_current_form()
    
    if current_form:
        return manager.submit_form(current_form.form_id)
    
    return False


def validate_current_form() -> bool:
    """Validate the current form context."""
    manager = get_form_manager()
    current_form = manager.get_current_form()
    
    if current_form:
        return manager.validate_form(current_form.form_id)
    
    return True


def get_current_form_errors() -> List[str]:
    """Get validation errors for the current form."""
    manager = get_form_manager()
    current_form = manager.get_current_form()
    
    if current_form:
        return manager.get_form_errors(current_form.form_id)
    
    return []


# Form validation helpers
def validate_font_size(value: Any, min_size: int = 8, max_size: int = 80) -> bool:
    """Validate font size."""
    try:
        size = float(value)
        return min_size <= size <= max_size
    except (ValueError, TypeError):
        return False


def validate_positive_number(value: Any) -> bool:
    """Validate positive number."""
    try:
        num = float(value)
        return num > 0
    except (ValueError, TypeError):
        return False


def validate_color_hex(value: Any) -> bool:
    """Validate hex color."""
    if not isinstance(value, str):
        return False
    
    if not value.startswith('#'):
        return False
    
    if len(value) not in [4, 7]:
        return False
    
    try:
        int(value[1:], 16)
        return True
    except ValueError:
        return False
