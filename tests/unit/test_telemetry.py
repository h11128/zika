"""
Unit tests for services/telemetry.py
Tests telemetry collection, sampling, structured logging, and event schemas.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock, Mock

from services.telemetry import (
    EventType, SamplingRate, TelemetryContext, PerformanceEvent, UserActionEvent,
    ErrorEvent, TelemetryCollector, LoggingBackend, get_telemetry_collector,
    set_telemetry_context, record_performance_event, record_user_action_event,
    record_error_event, record_cache_event, get_telemetry_stats, flush_telemetry,
    telemetry_context
)


class TestTelemetryContext:
    """Test telemetry context functionality."""
    
    def test_context_creation(self):
        """Test context creation."""
        context = TelemetryContext(
            request_id="req_123",
            session_generation="sess_456",
            user_id="user_789",
            environment="test",
            code_version="v1.0.0"
        )
        
        assert context.request_id == "req_123"
        assert context.session_generation == "sess_456"
        assert context.user_id == "user_789"
        assert context.environment == "test"
        assert context.code_version == "v1.0.0"
        assert context.timestamp > 0
    
    def test_context_to_dict(self):
        """Test context serialization."""
        context = TelemetryContext(
            request_id="req_123",
            session_generation="sess_456"
        )
        
        data = context.to_dict()
        assert data["request_id"] == "req_123"
        assert data["session_generation"] == "sess_456"
        assert "timestamp" in data


class TestPerformanceEvent:
    """Test performance event functionality."""
    
    def test_performance_event_creation(self):
        """Test performance event creation."""
        context = TelemetryContext("req_123", "sess_456")
        
        event = PerformanceEvent(
            event_type="performance",
            operation="render_preview",
            duration_ms=150.5,
            success=True,
            context=context,
            metadata={"cards_count": 10},
            memory_mb=25.0,
            cache_hit=True
        )
        
        assert event.event_type == "performance"
        assert event.operation == "render_preview"
        assert event.duration_ms == 150.5
        assert event.success is True
        assert event.memory_mb == 25.0
        assert event.cache_hit is True
        assert event.metadata["cards_count"] == 10
    
    def test_performance_event_to_dict(self):
        """Test performance event serialization."""
        context = TelemetryContext("req_123", "sess_456")
        event = PerformanceEvent(
            event_type="performance",
            operation="test_op",
            duration_ms=100.0,
            success=True,
            context=context
        )
        
        data = event.to_dict()
        assert data["event_type"] == "performance"
        assert data["operation"] == "test_op"
        assert data["duration_ms"] == 100.0
        assert data["context"]["request_id"] == "req_123"


class TestUserActionEvent:
    """Test user action event functionality."""
    
    def test_user_action_event_creation(self):
        """Test user action event creation."""
        context = TelemetryContext("req_123", "sess_456")
        
        event = UserActionEvent(
            action="change_card_size",
            component="layout_controls",
            context=context,
            metadata={"old_value": 5.0, "new_value": 6.0},
            input_type="slider",
            value_changed=True,
            validation_errors=[]
        )
        
        assert event.action == "change_card_size"
        assert event.component == "layout_controls"
        assert event.input_type == "slider"
        assert event.value_changed is True
        assert len(event.validation_errors) == 0
    
    def test_user_action_event_with_errors(self):
        """Test user action event with validation errors."""
        context = TelemetryContext("req_123", "sess_456")
        
        event = UserActionEvent(
            action="upload_csv",
            component="file_uploader",
            context=context,
            validation_errors=["Invalid CSV format", "Missing required columns"]
        )
        
        assert len(event.validation_errors) == 2
        assert "Invalid CSV format" in event.validation_errors


class TestErrorEvent:
    """Test error event functionality."""
    
    def test_error_event_creation(self):
        """Test error event creation."""
        context = TelemetryContext("req_123", "sess_456")
        
        event = ErrorEvent(
            error_type="ValidationError",
            error_message="Invalid input data",
            context=context,
            metadata={"input_size": 1000},
            stack_trace="Traceback...",
            component="data_processor",
            severity="warning",
            recoverable=True
        )
        
        assert event.error_type == "ValidationError"
        assert event.error_message == "Invalid input data"
        assert event.stack_trace == "Traceback..."
        assert event.component == "data_processor"
        assert event.severity == "warning"
        assert event.recoverable is True


class TestTelemetryCollector:
    """Test telemetry collector functionality."""
    
    def test_collector_creation(self):
        """Test collector creation."""
        collector = TelemetryCollector(max_buffer_size=500, flush_interval_seconds=10.0)
        
        assert collector._max_buffer_size == 500
        assert collector._flush_interval_seconds == 10.0
        assert len(collector._event_buffer) == 0
        assert len(collector._backends) == 0
    
    def test_context_management(self):
        """Test context management."""
        collector = TelemetryCollector()
        
        context1 = TelemetryContext("req_1", "sess_1")
        context2 = TelemetryContext("req_2", "sess_2")
        
        # Set initial context
        collector.set_context(context1)
        assert collector._current_context == context1
        
        # Push new context
        collector.push_context(context2)
        assert collector._current_context == context2
        assert len(collector._context_stack) == 1
        
        # Pop context
        popped = collector.pop_context()
        assert popped == context2
        assert collector._current_context == context1
    
    @patch('services.telemetry.get_feature_flag')
    def test_sampling_logic(self, mock_feature_flag):
        """Test event sampling logic."""
        mock_feature_flag.return_value = True
        collector = TelemetryCollector()
        
        # Set sampling rates
        collector._sampling_rates[EventType.ERROR] = 1.0  # Always sample
        collector._sampling_rates[EventType.DEBUG] = 0.0  # Never sample
        
        assert collector._should_sample(EventType.ERROR) is True
        assert collector._should_sample(EventType.DEBUG) is False
    
    @patch('services.telemetry.get_feature_flag')
    def test_performance_recording(self, mock_feature_flag):
        """Test performance event recording."""
        mock_feature_flag.return_value = True
        collector = TelemetryCollector()
        # Force sampling to always allow performance events
        collector._sampling_rates[EventType.PERFORMANCE] = 1.0
        context = TelemetryContext("req_123", "sess_456")
        collector.set_context(context)
        
        # Record performance event
        collector.record_performance(
            operation="test_operation",
            duration_ms=250.0,
            success=True,
            metadata={"test": "data"},
            memory_mb=30.0,
            cache_hit=False
        )
        
        # Check that event was collected
        assert len(collector._event_buffer) == 1
        event = collector._event_buffer[0]
        assert event["operation"] == "test_operation"
        assert event["duration_ms"] == 250.0
        assert event["memory_mb"] == 30.0
        assert event["cache_hit"] is False
    
    @patch('services.telemetry.get_feature_flag')
    def test_user_action_recording(self, mock_feature_flag):
        """Test user action event recording."""
        mock_feature_flag.return_value = True
        collector = TelemetryCollector()
        collector._sampling_rates[EventType.USER_ACTION] = 1.0
        context = TelemetryContext("req_123", "sess_456")
        collector.set_context(context)
        
        # Record user action
        collector.record_user_action(
            action="click_export",
            component="export_button",
            metadata={"format": "pdf"},
            input_type="button",
            value_changed=False
        )
        
        # Check that event was collected
        assert len(collector._event_buffer) == 1
        event = collector._event_buffer[0]
        assert event["action"] == "click_export"
        assert event["component"] == "export_button"
        assert event["input_type"] == "button"
    
    @patch('services.telemetry.get_feature_flag')
    def test_error_recording(self, mock_feature_flag):
        """Test error event recording."""
        mock_feature_flag.return_value = True
        collector = TelemetryCollector()
        collector._sampling_rates[EventType.ERROR] = 1.0
        context = TelemetryContext("req_123", "sess_456")
        collector.set_context(context)
        
        # Record error
        collector.record_error(
            error_type="RuntimeError",
            error_message="Something went wrong",
            metadata={"context": "test"},
            component="test_component",
            severity="error",
            recoverable=False
        )
        
        # Check that event was collected
        assert len(collector._event_buffer) == 1
        event = collector._event_buffer[0]
        assert event["error_type"] == "RuntimeError"
        assert event["error_message"] == "Something went wrong"
        assert event["component"] == "test_component"
        assert event["recoverable"] is False
    
    @patch('services.telemetry.get_feature_flag')
    def test_cache_event_recording(self, mock_feature_flag):
        """Test cache event recording."""
        mock_feature_flag.return_value = True
        collector = TelemetryCollector()
        collector._sampling_rates[EventType.CACHE_EVENT] = 1.0
        context = TelemetryContext("req_123", "sess_456")
        collector.set_context(context)
        
        # Record cache event
        collector.record_cache_event(
            operation="get",
            cache_type="preview",
            hit=True,
            metadata={"key": "test_key"}
        )
        
        # Check that event was collected
        assert len(collector._event_buffer) == 1
        event = collector._event_buffer[0]
        assert event["operation"] == "get"
        assert event["cache_type"] == "preview"
        assert event["hit"] is True
    
    @patch('services.telemetry.get_feature_flag')
    def test_backend_management(self, mock_feature_flag):
        """Test backend management."""
        mock_feature_flag.return_value = True
        collector = TelemetryCollector()
        collector._sampling_rates[EventType.PERFORMANCE] = 1.0
        
        # Add mock backend
        mock_backend = Mock()
        collector.add_backend(mock_backend)
        
        assert len(collector._backends) == 1
        
        # Record event and flush
        context = TelemetryContext("req_123", "sess_456")
        collector.set_context(context)
        collector.record_performance("test_op", 100.0)
        
        flushed_count = collector.flush()
        
        assert flushed_count == 1
        mock_backend.assert_called_once()
        
        # Check that backend received the event
        call_args = mock_backend.call_args[0][0]  # First argument (events list)
        assert len(call_args) == 1
        assert call_args[0]["operation"] == "test_op"
    
    @patch('services.telemetry.get_feature_flag')
    def test_statistics(self, mock_feature_flag):
        """Test statistics collection."""
        mock_feature_flag.return_value = True
        collector = TelemetryCollector()
        collector._sampling_rates[EventType.PERFORMANCE] = 1.0
        collector._sampling_rates[EventType.USER_ACTION] = 1.0
        context = TelemetryContext("req_123", "sess_456")
        collector.set_context(context)
        
        # Record some events
        collector.record_performance("op1", 100.0)
        collector.record_user_action("action1", "component1")
        
        stats = collector.get_stats()
        
        assert stats["events_collected"] >= 2
        assert stats["events_sampled"] >= 2
        assert stats["buffer_size"] >= 2
        assert "enabled" in stats
        assert "debug_mode" in stats
    
    @patch('services.telemetry.get_feature_flag')
    def test_buffer_overflow(self, mock_feature_flag):
        """Test buffer overflow handling."""
        mock_feature_flag.return_value = True
        collector = TelemetryCollector(max_buffer_size=2)
        collector._sampling_rates[EventType.PERFORMANCE] = 1.0
        context = TelemetryContext("req_123", "sess_456")
        collector.set_context(context)
        
        # Fill buffer beyond capacity
        for i in range(5):
            collector.record_performance(f"op_{i}", 100.0)
        
        # Buffer should be limited to max size
        assert len(collector._event_buffer) <= 2
        
        # Should have the most recent events
        events = list(collector._event_buffer)
        assert events[-1]["operation"] == "op_4"


class TestLoggingBackend:
    """Test logging backend functionality."""
    
    def test_backend_creation(self):
        """Test backend creation."""
        backend = LoggingBackend("test_logger")
        assert backend.logger.name == "test_logger"
    
    @patch('logging.getLogger')
    def test_event_logging(self, mock_get_logger):
        """Test event logging."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        backend = LoggingBackend()
        
        # Test performance event
        perf_event = {
            'event_type': 'performance',
            'operation': 'test_op',
            'duration_ms': 150.0,
            'success': True,
            'context': {'request_id': 'req_123'}
        }
        
        backend([perf_event])
        
        # Should have logged the event
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        assert call_args[0][0] == 20  # logging.INFO
        assert "PERF [req_123] test_op: 150.0ms ✓" in call_args[0][1]
    
    def test_event_formatting(self):
        """Test event message formatting."""
        backend = LoggingBackend()
        
        # Test different event types
        perf_event = {
            'event_type': 'performance',
            'operation': 'render',
            'duration_ms': 100.0,
            'success': False,
            'context': {'request_id': 'req_123'}
        }
        
        message = backend._format_event(perf_event)
        assert "PERF [req_123] render: 100.0ms ✗" == message
        
        # Test user action event
        user_event = {
            'event_type': 'user_action',
            'action': 'click',
            'component': 'button',
            'context': {'request_id': 'req_456'}
        }
        
        message = backend._format_event(user_event)
        assert "USER [req_456] button.click" == message
        
        # Test error event
        error_event = {
            'event_type': 'error',
            'error_type': 'ValueError',
            'error_message': 'Invalid input',
            'context': {'request_id': 'req_789'}
        }
        
        message = backend._format_event(error_event)
        assert "ERROR [req_789] ValueError: Invalid input" == message


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('services.telemetry.get_telemetry_collector')
    def test_set_telemetry_context(self, mock_get_collector):
        """Test set telemetry context function."""
        mock_collector = Mock()
        mock_get_collector.return_value = mock_collector
        
        set_telemetry_context(
            request_id="req_123",
            session_generation="sess_456",
            user_id="user_789",
            environment="test"
        )
        
        mock_collector.set_context.assert_called_once()
        context = mock_collector.set_context.call_args[0][0]
        assert context.request_id == "req_123"
        assert context.session_generation == "sess_456"
        assert context.user_id == "user_789"
        assert context.environment == "test"
    
    @patch('services.telemetry.get_telemetry_collector')
    def test_record_performance_event(self, mock_get_collector):
        """Test record performance event function."""
        mock_collector = Mock()
        mock_get_collector.return_value = mock_collector
        
        record_performance_event(
            operation="test_op",
            duration_ms=200.0,
            success=True,
            metadata={"test": "data"},
            memory_mb=40.0,
            cache_hit=True
        )
        
        mock_collector.record_performance.assert_called_once_with(
            "test_op", 200.0, True, {"test": "data"}, 40.0, True
        )
    
    @patch('services.telemetry.get_telemetry_collector')
    def test_record_user_action_event(self, mock_get_collector):
        """Test record user action event function."""
        mock_collector = Mock()
        mock_get_collector.return_value = mock_collector
        
        record_user_action_event(
            action="click",
            component="button",
            metadata={"target": "export"},
            value_changed=False
        )
        
        mock_collector.record_user_action.assert_called_once_with(
            "click", "button", {"target": "export"}, value_changed=False
        )
    
    @patch('services.telemetry.get_telemetry_collector')
    def test_record_error_event(self, mock_get_collector):
        """Test record error event function."""
        mock_collector = Mock()
        mock_get_collector.return_value = mock_collector
        
        record_error_event(
            error_type="ValueError",
            error_message="Invalid data",
            metadata={"context": "test"},
            component="validator",
            severity="warning"
        )
        
        mock_collector.record_error.assert_called_once_with(
            "ValueError", "Invalid data", {"context": "test"},
            component="validator", severity="warning"
        )


class TestTelemetryContextManager:
    """Test telemetry context manager."""
    
    @patch('services.telemetry.get_telemetry_collector')
    def test_context_manager_normal_flow(self, mock_get_collector):
        """Test context manager normal flow."""
        mock_collector = Mock()
        mock_get_collector.return_value = mock_collector
        
        with telemetry_context("req_123", "sess_456", environment="test") as ctx:
            assert ctx.request_id == "req_123"
            assert ctx.session_generation == "sess_456"
            assert ctx.environment == "test"
        
        # Should have pushed and popped context
        mock_collector.push_context.assert_called_once()
        mock_collector.pop_context.assert_called_once()
    
    @patch('services.telemetry.get_telemetry_collector')
    @patch('services.telemetry.record_error_event')
    def test_context_manager_exception_handling(self, mock_record_error, mock_get_collector):
        """Test context manager exception handling."""
        mock_collector = Mock()
        mock_get_collector.return_value = mock_collector
        
        try:
            with telemetry_context("req_123", "sess_456"):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should have recorded the error
        mock_record_error.assert_called_once()
        call_args = mock_record_error.call_args[1]
        assert call_args["error_type"] == "ValueError"
        assert call_args["error_message"] == "Test error"


class TestIntegration:
    """Test integration scenarios."""
    
    @patch('services.telemetry.get_feature_flag')
    def test_full_telemetry_workflow(self, mock_feature_flag):
        """Test complete telemetry workflow."""
        mock_feature_flag.return_value = True
        # Create collector with mock backend
        collector = TelemetryCollector()
        # Set all sampling rates to 1.0 to ensure events are collected
        for event_type in EventType:
            collector._sampling_rates[event_type] = 1.0
        mock_backend = Mock()
        collector.add_backend(mock_backend)
        
        # Set context
        context = TelemetryContext("req_123", "sess_456", environment="test")
        collector.set_context(context)
        
        # Record various events
        collector.record_performance("render_preview", 150.0, True, memory_mb=25.0)
        collector.record_user_action("change_setting", "controls", value_changed=True)
        collector.record_error("ValidationError", "Invalid input", severity="warning")
        collector.record_cache_event("get", "preview", True)
        
        # Flush events
        flushed_count = collector.flush()
        
        # Verify results
        assert flushed_count == 4
        mock_backend.assert_called_once()
        
        events = mock_backend.call_args[0][0]
        assert len(events) == 4
        
        # Check event types
        event_types = [event.get('event_type') for event in events]
        assert 'performance' in event_types
        assert 'user_action' in event_types
        assert 'error' in event_types
        assert 'cache_event' in event_types
        
        # Check statistics
        stats = collector.get_stats()
        assert stats['events_collected'] == 4
        assert stats['events_flushed'] == 4


if __name__ == "__main__":
    pytest.main([__file__])
