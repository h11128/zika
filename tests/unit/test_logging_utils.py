"""
Unit tests for logging utilities.
Tests session-aware logging, request context, and structured logging.
"""

import pytest
import logging
import json
from unittest.mock import patch, MagicMock
from io import StringIO

from core.logging_utils import (
    SessionAwareFormatter, StructuredFormatter, RequestContext,
    request_context, get_logger, log_session_event, log_performance_metric,
    log_cache_event, operation_logger, get_current_request_context,
    setup_logging, generate_request_id
)


class TestSessionAwareFormatter:
    """Test session-aware log formatting."""
    
    def test_session_aware_formatter_adds_session_context(self):
        """Test that formatter adds session generation to log records."""
        formatter = SessionAwareFormatter()
        
        # Create a log record
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        with patch('core.logging_utils.ui_state_module.get_session_generation', return_value='test-session-123'):
            formatted = formatter.format(record)
            
            assert hasattr(record, 'session_generation')
            assert record.session_generation == 'test-session-123'
            assert hasattr(record, 'request_id')
            assert hasattr(record, 'component')
            assert hasattr(record, 'timestamp')
    
    def test_session_aware_formatter_handles_session_error(self):
        """Test formatter handles session generation errors gracefully."""
        formatter = SessionAwareFormatter()
        
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        with patch('core.logging_utils.ui_state_module.get_session_generation', side_effect=Exception("Session error")):
            formatted = formatter.format(record)
            
            assert record.session_generation == 'unknown'


class TestStructuredFormatter:
    """Test structured JSON log formatting."""
    
    def test_structured_formatter_produces_json(self):
        """Test that structured formatter produces valid JSON."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=10,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        with patch('core.logging_utils.ui_state_module.get_session_generation', return_value='test-session-123'):
            formatted = formatter.format(record)
            
            # Should be valid JSON
            log_data = json.loads(formatted)
            
            assert log_data['level'] == 'INFO'
            assert log_data['message'] == 'Test message'
            assert log_data['session_generation'] == 'test-session-123'
            assert 'timestamp' in log_data
            assert 'request_id' in log_data
            assert 'component' in log_data
    
    def test_structured_formatter_includes_exception(self):
        """Test that structured formatter includes exception info."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name='test_logger',
            level=logging.ERROR,
            pathname='test.py',
            lineno=10,
            msg='Error occurred',
            args=(),
            exc_info=exc_info
        )
        
        with patch('core.logging_utils.ui_state_module.get_session_generation', return_value='test-session-123'):
            formatted = formatter.format(record)
            
            log_data = json.loads(formatted)
            
            assert 'exception' in log_data
            assert 'ValueError' in log_data['exception']
            assert 'Test exception' in log_data['exception']


class TestRequestContext:
    """Test request context management."""
    
    def test_request_context_basic(self):
        """Test basic request context functionality."""
        with request_context('test.component', 'test_operation') as ctx:
            assert ctx.component == 'test.component'
            assert ctx.operation == 'test_operation'
            assert ctx.request_id is not None
            assert ctx.start_time is not None
            assert len(ctx.request_id) == 8  # Short ID
    
    def test_request_context_with_custom_request_id(self):
        """Test request context with custom request ID."""
        custom_id = 'custom123'
        
        with request_context('test.component', 'test_operation', request_id=custom_id) as ctx:
            assert ctx.request_id == custom_id
    
    def test_request_context_with_metadata(self):
        """Test request context with metadata."""
        metadata = {'user_id': 'user123', 'action': 'render'}
        
        with request_context('test.component', 'test_operation', **metadata) as ctx:
            assert ctx.metadata == metadata
    
    def test_request_context_nesting(self):
        """Test nested request contexts."""
        with request_context('outer.component', 'outer_op') as outer_ctx:
            outer_id = outer_ctx.request_id
            
            with request_context('inner.component', 'inner_op') as inner_ctx:
                inner_id = inner_ctx.request_id
                assert inner_id != outer_id
                assert inner_ctx.component == 'inner.component'
            
            # Should restore outer context
            current_ctx = get_current_request_context()
            assert current_ctx.request_id == outer_id
            assert current_ctx.component == 'outer.component'
    
    def test_request_context_exception_handling(self):
        """Test request context handles exceptions properly."""
        with patch('core.logging_utils.logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            with pytest.raises(ValueError):
                with request_context('test.component', 'test_operation'):
                    raise ValueError("Test error")
            
            # Should log error
            assert mock_logger.error.called
            error_call = mock_logger.error.call_args
            assert 'Failed operation' in error_call[0][0]


class TestLoggingFunctions:
    """Test logging utility functions."""
    
    def test_generate_request_id(self):
        """Test request ID generation."""
        req_id = generate_request_id()
        
        assert isinstance(req_id, str)
        assert len(req_id) == 8
        
        # Should be unique
        req_id2 = generate_request_id()
        assert req_id != req_id2
    
    @patch('core.logging_utils.ui_state_module.get_session_generation_info')
    def test_log_session_event(self, mock_get_session_info):
        """Test session event logging."""
        mock_get_session_info.return_value = {'id': 'session123', 'rerun_count': 5}
        
        with patch('core.logging_utils.logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_session_event('cache_miss', cache_key='key123', reason='expired')
            
            # Should log with session info
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args
            assert 'Session event: cache_miss' in call_args[0][0]
            
            extra = call_args[1]['extra']
            assert extra['event_type'] == 'cache_miss'
            assert extra['cache_key'] == 'key123'
            assert extra['reason'] == 'expired'
            assert 'session_info' in extra
    
    def test_log_performance_metric(self):
        """Test performance metric logging."""
        with patch('core.logging_utils.logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_performance_metric('render_time', 150.5, 'ms', component='preview')
            
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args
            assert 'Performance metric: render_time=150.5ms' in call_args[0][0]
            
            extra = call_args[1]['extra']
            assert extra['metric_name'] == 'render_time'
            assert extra['metric_value'] == 150.5
            assert extra['metric_unit'] == 'ms'
            assert extra['component'] == 'preview'
    
    def test_log_cache_event(self):
        """Test cache event logging."""
        with patch('core.logging_utils.logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_cache_event('preview', 'hit', 'key123', size_bytes=1024)
            
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args
            assert 'Cache event: preview.hit' in call_args[0][0]
            
            extra = call_args[1]['extra']
            assert extra['cache_name'] == 'preview'
            assert extra['cache_event_type'] == 'hit'
            assert extra['cache_key'] == 'key123'
            assert extra['size_bytes'] == 1024


class TestOperationLogger:
    """Test operation logger decorator."""
    
    def test_operation_logger_decorator(self):
        """Test operation logger decorator functionality."""
        with patch('core.logging_utils.request_context') as mock_context:
            mock_context.return_value.__enter__ = MagicMock()
            mock_context.return_value.__exit__ = MagicMock()
            
            @operation_logger('test.component', 'test_operation')
            def test_function(x, y):
                return x + y
            
            result = test_function(1, 2)
            
            assert result == 3
            mock_context.assert_called_once_with('test.component', 'test_operation')
    
    def test_operation_logger_default_operation_name(self):
        """Test operation logger with default operation name."""
        with patch('core.logging_utils.request_context') as mock_context:
            mock_context.return_value.__enter__ = MagicMock()
            mock_context.return_value.__exit__ = MagicMock()
            
            @operation_logger('test.component')
            def my_test_function():
                return 'result'
            
            result = my_test_function()
            
            assert result == 'result'
            mock_context.assert_called_once_with('test.component', 'my_test_function')


class TestLoggingSetup:
    """Test logging setup and configuration."""
    
    def test_setup_logging_development(self):
        """Test logging setup for development environment."""
        with patch.dict('os.environ', {'ENVIRONMENT': 'development'}):
            with patch('core.logging_utils.logging.getLogger') as mock_get_logger:
                mock_root_logger = MagicMock()
                mock_get_logger.return_value = mock_root_logger
                
                setup_logging('DEBUG', structured=False)
                
                # Should configure root logger
                mock_root_logger.setLevel.assert_called_with(logging.DEBUG)
    
    def test_setup_logging_production(self):
        """Test logging setup for production environment."""
        with patch.dict('os.environ', {'ENVIRONMENT': 'production'}):
            with patch('core.logging_utils.logging.getLogger') as mock_get_logger:
                mock_root_logger = MagicMock()
                mock_get_logger.return_value = mock_root_logger
                
                setup_logging('INFO', structured=True)
                
                mock_root_logger.setLevel.assert_called_with(logging.INFO)
    
    def test_get_logger_configuration(self):
        """Test logger configuration."""
        with patch('core.logging_utils.logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_logger.handlers = []  # No existing handlers
            mock_get_logger.return_value = mock_logger
            
            logger = get_logger('test.module')
            
            # Should configure handler and formatter
            assert mock_logger.addHandler.called
            assert mock_logger.setLevel.called
