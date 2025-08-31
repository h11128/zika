"""
Integration tests for multi-session isolation.
Tests that different sessions don't interfere with each other.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os
import uuid

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class MockSession:
    """Mock session for testing isolation."""
    
    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.state = {}
        self.cache = {}
        self.generation = 1
    
    def get_state(self, key, default=None):
        """Get session state."""
        return self.state.get(key, default)
    
    def set_state(self, key, value):
        """Set session state."""
        old_value = self.state.get(key)
        self.state[key] = value
        return old_value != value
    
    def get_cache(self, key, default=None):
        """Get cached value."""
        return self.cache.get(key, default)
    
    def set_cache(self, key, value):
        """Set cached value."""
        self.cache[key] = value
    
    def clear_cache(self):
        """Clear session cache."""
        self.cache.clear()
    
    def increment_generation(self):
        """Increment session generation."""
        self.generation += 1
        return self.generation


class MockSessionManager:
    """Mock session manager for testing multi-session scenarios."""
    
    def __init__(self):
        self.sessions = {}
        self.current_session_id = None
    
    def create_session(self, session_id=None):
        """Create a new session."""
        session = MockSession(session_id)
        self.sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id):
        """Get existing session."""
        return self.sessions.get(session_id)
    
    def set_current_session(self, session_id):
        """Set current active session."""
        self.current_session_id = session_id
    
    def get_current_session(self):
        """Get current active session."""
        if self.current_session_id:
            return self.sessions.get(self.current_session_id)
        return None
    
    def list_sessions(self):
        """List all sessions."""
        return list(self.sessions.keys())
    
    def cleanup_session(self, session_id):
        """Clean up a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]


class TestSessionStateIsolation:
    """Test that session state is properly isolated."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = MockSessionManager()
    
    def test_different_sessions_have_isolated_state(self):
        """Test that different sessions maintain separate state."""
        # Create two sessions
        session1 = self.session_manager.create_session("session_1")
        session2 = self.session_manager.create_session("session_2")
        
        # Set different state in each session
        session1.set_state('layout_rows', 2)
        session1.set_state('background_color', '#FFFFFF')
        
        session2.set_state('layout_rows', 3)
        session2.set_state('background_color', '#F0F0F0')
        
        # Verify state isolation
        assert session1.get_state('layout_rows') == 2
        assert session1.get_state('background_color') == '#FFFFFF'
        
        assert session2.get_state('layout_rows') == 3
        assert session2.get_state('background_color') == '#F0F0F0'
        
        # Verify no cross-contamination
        assert session1.get_state('layout_rows') != session2.get_state('layout_rows')
        assert session1.get_state('background_color') != session2.get_state('background_color')
    
    def test_session_state_changes_dont_affect_other_sessions(self):
        """Test that changing state in one session doesn't affect others."""
        # Create multiple sessions
        session1 = self.session_manager.create_session("session_1")
        session2 = self.session_manager.create_session("session_2")
        session3 = self.session_manager.create_session("session_3")
        
        # Set initial state in all sessions
        for session in [session1, session2, session3]:
            session.set_state('cards_count', 20)
            session.set_state('current_page', 1)
        
        # Change state in session1
        session1.set_state('cards_count', 30)
        session1.set_state('current_page', 2)
        
        # Verify other sessions are unaffected
        assert session2.get_state('cards_count') == 20
        assert session2.get_state('current_page') == 1
        
        assert session3.get_state('cards_count') == 20
        assert session3.get_state('current_page') == 1
    
    def test_session_creation_starts_with_clean_state(self):
        """Test that new sessions start with clean state."""
        # Create first session and set some state
        session1 = self.session_manager.create_session("session_1")
        session1.set_state('layout_rows', 5)
        session1.set_state('hanzi_font_size_pt', 60)
        
        # Create second session
        session2 = self.session_manager.create_session("session_2")
        
        # Second session should have clean state
        assert session2.get_state('layout_rows') is None
        assert session2.get_state('hanzi_font_size_pt') is None
        
        # First session should retain its state
        assert session1.get_state('layout_rows') == 5
        assert session1.get_state('hanzi_font_size_pt') == 60


class TestSessionCacheIsolation:
    """Test that session caches are properly isolated."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = MockSessionManager()
    
    def test_different_sessions_have_isolated_caches(self):
        """Test that different sessions maintain separate caches."""
        # Create two sessions
        session1 = self.session_manager.create_session("session_1")
        session2 = self.session_manager.create_session("session_2")
        
        # Set different cache values in each session
        session1.set_cache('preview_html', '<div>Session 1 Preview</div>')
        session1.set_cache('export_pdf', b'session1_pdf_data')
        
        session2.set_cache('preview_html', '<div>Session 2 Preview</div>')
        session2.set_cache('export_pdf', b'session2_pdf_data')
        
        # Verify cache isolation
        assert session1.get_cache('preview_html') == '<div>Session 1 Preview</div>'
        assert session1.get_cache('export_pdf') == b'session1_pdf_data'
        
        assert session2.get_cache('preview_html') == '<div>Session 2 Preview</div>'
        assert session2.get_cache('export_pdf') == b'session2_pdf_data'
        
        # Verify no cross-contamination
        assert session1.get_cache('preview_html') != session2.get_cache('preview_html')
        assert session1.get_cache('export_pdf') != session2.get_cache('export_pdf')
    
    def test_cache_clearing_only_affects_current_session(self):
        """Test that clearing cache only affects the current session."""
        # Create multiple sessions with cached data
        session1 = self.session_manager.create_session("session_1")
        session2 = self.session_manager.create_session("session_2")
        
        # Add cache data to both sessions
        session1.set_cache('preview_html', '<div>Session 1</div>')
        session1.set_cache('layout_data', {'rows': 2, 'cols': 3})
        
        session2.set_cache('preview_html', '<div>Session 2</div>')
        session2.set_cache('layout_data', {'rows': 3, 'cols': 4})
        
        # Clear cache in session1
        session1.clear_cache()
        
        # Verify session1 cache is cleared
        assert session1.get_cache('preview_html') is None
        assert session1.get_cache('layout_data') is None
        
        # Verify session2 cache is unaffected
        assert session2.get_cache('preview_html') == '<div>Session 2</div>'
        assert session2.get_cache('layout_data') == {'rows': 3, 'cols': 4}


class TestSessionGenerationIsolation:
    """Test that session generations are properly isolated."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = MockSessionManager()
    
    def test_different_sessions_have_independent_generations(self):
        """Test that session generations are independent."""
        # Create two sessions
        session1 = self.session_manager.create_session("session_1")
        session2 = self.session_manager.create_session("session_2")
        
        # Both should start with generation 1
        assert session1.generation == 1
        assert session2.generation == 1
        
        # Increment generation in session1
        session1.increment_generation()
        session1.increment_generation()
        
        # Verify session1 generation changed
        assert session1.generation == 3
        
        # Verify session2 generation unchanged
        assert session2.generation == 1
        
        # Increment generation in session2
        session2.increment_generation()
        
        # Verify independent generations
        assert session1.generation == 3
        assert session2.generation == 2
    
    def test_session_generation_affects_cache_keys(self):
        """Test that session generation affects cache key computation."""
        # Create session
        session = self.session_manager.create_session("test_session")
        
        # Mock cache key computation that includes generation
        def compute_cache_key(data, generation):
            return f"cache_key_{hash(str(data))}_{generation}"
        
        # Compute cache key with initial generation
        data = {'layout_rows': 2, 'layout_cols': 3}
        key1 = compute_cache_key(data, session.generation)
        
        # Increment generation
        session.increment_generation()
        
        # Compute cache key with new generation
        key2 = compute_cache_key(data, session.generation)
        
        # Keys should be different due to generation change
        assert key1 != key2
        assert key1.endswith('_1')
        assert key2.endswith('_2')


class TestSessionManagerBehavior:
    """Test session manager behavior."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = MockSessionManager()
    
    def test_session_creation_and_retrieval(self):
        """Test session creation and retrieval."""
        # Create session with specific ID
        session = self.session_manager.create_session("test_session")
        assert session.session_id == "test_session"
        
        # Retrieve session
        retrieved = self.session_manager.get_session("test_session")
        assert retrieved is session
        assert retrieved.session_id == "test_session"
    
    def test_session_listing(self):
        """Test session listing functionality."""
        # Initially no sessions
        assert len(self.session_manager.list_sessions()) == 0
        
        # Create multiple sessions
        session1 = self.session_manager.create_session("session_1")
        session2 = self.session_manager.create_session("session_2")
        session3 = self.session_manager.create_session("session_3")
        
        # List should contain all sessions
        sessions = self.session_manager.list_sessions()
        assert len(sessions) == 3
        assert "session_1" in sessions
        assert "session_2" in sessions
        assert "session_3" in sessions
    
    def test_current_session_management(self):
        """Test current session management."""
        # Initially no current session
        assert self.session_manager.get_current_session() is None
        
        # Create and set current session
        session = self.session_manager.create_session("current_session")
        self.session_manager.set_current_session("current_session")
        
        # Verify current session
        current = self.session_manager.get_current_session()
        assert current is session
        assert current.session_id == "current_session"
    
    def test_session_cleanup(self):
        """Test session cleanup functionality."""
        # Create sessions
        session1 = self.session_manager.create_session("session_1")
        session2 = self.session_manager.create_session("session_2")
        
        # Verify sessions exist
        assert len(self.session_manager.list_sessions()) == 2
        
        # Cleanup one session
        self.session_manager.cleanup_session("session_1")
        
        # Verify session removed
        sessions = self.session_manager.list_sessions()
        assert len(sessions) == 1
        assert "session_2" in sessions
        assert "session_1" not in sessions
        
        # Verify session no longer retrievable
        assert self.session_manager.get_session("session_1") is None
        assert self.session_manager.get_session("session_2") is not None


class TestSessionIsolationIntegration:
    """Test session isolation in integrated scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = MockSessionManager()
    
    def test_concurrent_session_operations(self):
        """Test concurrent operations on different sessions."""
        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = self.session_manager.create_session(f"session_{i}")
            sessions.append(session)
        
        # Perform operations on each session
        for i, session in enumerate(sessions):
            session.set_state('layout_rows', i + 2)
            session.set_state('cards_count', (i + 1) * 10)
            session.set_cache(f'cache_key_{i}', f'cache_value_{i}')
            
            # Increment generation different number of times
            for _ in range(i):
                session.increment_generation()
        
        # Verify each session maintains its own state
        for i, session in enumerate(sessions):
            assert session.get_state('layout_rows') == i + 2
            assert session.get_state('cards_count') == (i + 1) * 10
            assert session.get_cache(f'cache_key_{i}') == f'cache_value_{i}'
            assert session.generation == i + 1
            
            # Verify no cross-contamination
            for j in range(5):
                if i != j:
                    assert session.get_cache(f'cache_key_{j}') is None
    
    def test_session_isolation_under_stress(self):
        """Test session isolation under stress conditions."""
        # Create many sessions
        num_sessions = 20
        sessions = []
        
        for i in range(num_sessions):
            session = self.session_manager.create_session(f"stress_session_{i}")
            sessions.append(session)
            
            # Set unique state for each session
            session.set_state('unique_id', i)
            session.set_state('data', f"session_{i}_data")
            session.set_cache('unique_cache', f"cache_{i}")
        
        # Verify isolation is maintained
        for i, session in enumerate(sessions):
            assert session.get_state('unique_id') == i
            assert session.get_state('data') == f"session_{i}_data"
            assert session.get_cache('unique_cache') == f"cache_{i}"
            
            # Verify no interference from other sessions
            for j in range(num_sessions):
                if i != j:
                    other_session = sessions[j]
                    assert session.get_state('unique_id') != other_session.get_state('unique_id')
                    assert session.get_cache('unique_cache') != other_session.get_cache('unique_cache')


if __name__ == "__main__":
    pytest.main([__file__])
