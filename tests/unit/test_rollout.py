"""
Unit tests for services/rollout.py
Tests feature flag rollout management, A/B testing, and automated rollback functionality.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from services.rollout import (
    RolloutStrategy, RolloutStatus, UserSegment, RolloutConfig, RolloutMetrics,
    RolloutState, RolloutManager, ABTestManager, get_rollout_manager, get_ab_test_manager,
    is_feature_enabled_for_user, create_feature_rollout, start_feature_rollout
)


class TestRolloutConfig:
    """Test rollout configuration functionality."""
    
    def test_rollout_config_creation(self):
        """Test rollout configuration creation."""
        config = RolloutConfig(
            feature_name="test_feature",
            strategy=RolloutStrategy.GRADUAL,
            target_percentage=100.0,
            initial_percentage=10.0,
            increment_percentage=20.0
        )
        
        assert config.feature_name == "test_feature"
        assert config.strategy == RolloutStrategy.GRADUAL
        assert config.target_percentage == 100.0
        assert config.initial_percentage == 10.0
        assert config.increment_percentage == 20.0
    
    def test_rollout_config_defaults(self):
        """Test rollout configuration defaults."""
        config = RolloutConfig(
            feature_name="test_feature",
            strategy=RolloutStrategy.PERCENTAGE
        )
        
        assert config.target_percentage == 100.0
        assert config.user_segments == [UserSegment.ALL]
        assert config.max_error_rate == 5.0
        assert config.monitoring_enabled is True


class TestRolloutMetrics:
    """Test rollout metrics functionality."""
    
    def test_rollout_metrics_creation(self):
        """Test rollout metrics creation."""
        timestamp = datetime.now(timezone.utc).isoformat()
        metrics = RolloutMetrics(
            timestamp=timestamp,
            feature_name="test_feature",
            enabled_users=100,
            total_users=1000,
            error_rate=1.5,
            success_rate=98.5,
            avg_latency_ms=150.0,
            p95_latency_ms=300.0
        )
        
        assert metrics.feature_name == "test_feature"
        assert metrics.enabled_users == 100
        assert metrics.error_rate == 1.5
        assert metrics.success_rate == 98.5


class TestRolloutState:
    """Test rollout state functionality."""
    
    def test_rollout_state_creation(self):
        """Test rollout state creation."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE)
        state = RolloutState(
            feature_name="test_feature",
            config=config,
            status=RolloutStatus.PLANNED,
            current_percentage=0.0
        )
        
        assert state.feature_name == "test_feature"
        assert state.status == RolloutStatus.PLANNED
        assert state.current_percentage == 0.0
        assert len(state.enabled_users) == 0
    
    def test_rollout_state_to_dict(self):
        """Test rollout state serialization."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE)
        state = RolloutState(
            feature_name="test_feature",
            config=config,
            status=RolloutStatus.ACTIVE,
            current_percentage=50.0
        )
        
        state_dict = state.to_dict()
        
        assert isinstance(state_dict, dict)
        assert state_dict['feature_name'] == "test_feature"
        assert state_dict['current_percentage'] == 50.0


class TestRolloutManager:
    """Test rollout manager functionality."""
    
    @pytest.fixture
    def rollout_manager(self):
        """Create fresh rollout manager for each test."""
        return RolloutManager()
    
    def test_create_rollout(self, rollout_manager):
        """Test creating a new rollout."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE, target_percentage=50.0)
        
        rollout_state = rollout_manager.create_rollout(config)
        
        assert rollout_state.feature_name == "test_feature"
        assert rollout_state.status == RolloutStatus.PLANNED
        assert rollout_state.current_percentage == 0.0
        assert "test_feature" in rollout_manager.rollouts
    
    def test_create_duplicate_rollout(self, rollout_manager):
        """Test creating duplicate rollout raises error."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE)
        
        rollout_manager.create_rollout(config)
        
        with pytest.raises(ValueError, match="already exists"):
            rollout_manager.create_rollout(config)
    
    def test_start_rollout_percentage(self, rollout_manager):
        """Test starting a percentage-based rollout."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE, target_percentage=75.0)
        rollout_manager.create_rollout(config)
        
        success = rollout_manager.start_rollout("test_feature")
        
        assert success is True
        rollout = rollout_manager.rollouts["test_feature"]
        assert rollout.status == RolloutStatus.ACTIVE
        assert rollout.current_percentage == 75.0
        assert rollout.start_time is not None
    
    def test_start_rollout_gradual(self, rollout_manager):
        """Test starting a gradual rollout."""
        config = RolloutConfig(
            "test_feature", 
            RolloutStrategy.GRADUAL, 
            initial_percentage=10.0,
            target_percentage=100.0
        )
        rollout_manager.create_rollout(config)
        
        success = rollout_manager.start_rollout("test_feature")
        
        assert success is True
        rollout = rollout_manager.rollouts["test_feature"]
        assert rollout.status == RolloutStatus.ACTIVE
        assert rollout.current_percentage == 10.0
    
    def test_start_rollout_canary(self, rollout_manager):
        """Test starting a canary rollout."""
        config = RolloutConfig(
            "test_feature", 
            RolloutStrategy.CANARY, 
            canary_percentage=5.0
        )
        rollout_manager.create_rollout(config)
        
        success = rollout_manager.start_rollout("test_feature")
        
        assert success is True
        rollout = rollout_manager.rollouts["test_feature"]
        assert rollout.current_percentage == 5.0
    
    def test_start_nonexistent_rollout(self, rollout_manager):
        """Test starting nonexistent rollout raises error."""
        with pytest.raises(ValueError, match="not found"):
            rollout_manager.start_rollout("nonexistent_feature")
    
    def test_start_already_started_rollout(self, rollout_manager):
        """Test starting already started rollout raises error."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        with pytest.raises(ValueError, match="not in planned state"):
            rollout_manager.start_rollout("test_feature")
    
    def test_pause_rollout(self, rollout_manager):
        """Test pausing an active rollout."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        success = rollout_manager.pause_rollout("test_feature", "Testing pause")
        
        assert success is True
        rollout = rollout_manager.rollouts["test_feature"]
        assert rollout.status == RolloutStatus.PAUSED
    
    def test_resume_rollout(self, rollout_manager):
        """Test resuming a paused rollout."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        rollout_manager.pause_rollout("test_feature")
        
        success = rollout_manager.resume_rollout("test_feature")
        
        assert success is True
        rollout = rollout_manager.rollouts["test_feature"]
        assert rollout.status == RolloutStatus.ACTIVE
    
    def test_rollback_feature(self, rollout_manager):
        """Test rolling back a feature."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        success = rollout_manager.rollback_feature("test_feature", "Critical bug found")
        
        assert success is True
        rollout = rollout_manager.rollouts["test_feature"]
        assert rollout.status == RolloutStatus.ROLLED_BACK
        assert rollout.rollback_reason == "Critical bug found"
        assert rollout.current_percentage == 0.0
        assert len(rollout.enabled_users) == 0
    
    def test_is_feature_enabled_active_rollout(self, rollout_manager):
        """Test feature enabled check for active rollout."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE, target_percentage=100.0)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        # Add user to enabled users
        rollout = rollout_manager.rollouts["test_feature"]
        rollout.enabled_users.append("user_1")
        rollout_manager.user_assignments["user_1"] = {"test_feature": True}
        
        enabled = rollout_manager.is_feature_enabled("test_feature", "user_1")
        assert enabled is True
        
        not_enabled = rollout_manager.is_feature_enabled("test_feature", "user_2")
        assert not_enabled is False
    
    def test_is_feature_enabled_rolled_back(self, rollout_manager):
        """Test feature enabled check for rolled back feature."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        rollout_manager.rollback_feature("test_feature", "Test rollback")
        
        enabled = rollout_manager.is_feature_enabled("test_feature", "user_1")
        assert enabled is False
    
    @patch('services.rollout.get_feature_flag')
    def test_is_feature_enabled_fallback(self, mock_get_flag, rollout_manager):
        """Test feature enabled fallback to static flags."""
        mock_get_flag.return_value = True
        
        enabled = rollout_manager.is_feature_enabled("nonexistent_feature", "user_1")
        
        assert enabled is True
        mock_get_flag.assert_called_once_with("nonexistent_feature", False)
    
    def test_update_rollout_progress_gradual(self, rollout_manager):
        """Test updating gradual rollout progress."""
        config = RolloutConfig(
            "test_feature", 
            RolloutStrategy.GRADUAL,
            initial_percentage=10.0,
            increment_percentage=20.0,
            increment_interval_hours=1,  # 1 hour for testing
            target_percentage=100.0
        )
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        # Simulate time passage
        rollout = rollout_manager.rollouts["test_feature"]
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        rollout.start_time = past_time.isoformat()
        
        success = rollout_manager.update_rollout_progress("test_feature")
        
        assert success is True
        # Should have incremented twice: 10% + 20% + 20% = 50%
        assert rollout.current_percentage == 50.0
    
    def test_update_rollout_progress_completion(self, rollout_manager):
        """Test rollout completion when target reached."""
        config = RolloutConfig(
            "test_feature", 
            RolloutStrategy.GRADUAL,
            initial_percentage=80.0,
            increment_percentage=30.0,
            increment_interval_hours=1,
            target_percentage=100.0
        )
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        # Simulate time passage
        rollout = rollout_manager.rollouts["test_feature"]
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        rollout.start_time = past_time.isoformat()
        
        rollout_manager.update_rollout_progress("test_feature")
        
        # Should be completed at 100%
        assert rollout.current_percentage == 100.0
        assert rollout.status == RolloutStatus.COMPLETED
    
    def test_collect_metrics(self, rollout_manager):
        """Test collecting rollout metrics."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        metrics = RolloutMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            feature_name="test_feature",
            enabled_users=50,
            total_users=100,
            error_rate=1.0,
            success_rate=99.0,
            avg_latency_ms=100.0,
            p95_latency_ms=200.0
        )
        
        success = rollout_manager.collect_metrics("test_feature", metrics)
        
        assert success is True
        rollout = rollout_manager.rollouts["test_feature"]
        assert len(rollout.metrics_history) == 1
        assert rollout.metrics_history[0] == metrics
    
    def test_automatic_rollback_error_rate(self, rollout_manager):
        """Test automatic rollback on high error rate."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE, max_error_rate=2.0)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        # High error rate metrics
        metrics = RolloutMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            feature_name="test_feature",
            enabled_users=50,
            total_users=100,
            error_rate=5.0,  # Above threshold
            success_rate=95.0,
            avg_latency_ms=100.0,
            p95_latency_ms=200.0
        )
        
        rollout_manager.collect_metrics("test_feature", metrics)
        
        rollout = rollout_manager.rollouts["test_feature"]
        assert rollout.status == RolloutStatus.ROLLED_BACK
        assert "Error rate" in rollout.rollback_reason
    
    def test_automatic_rollback_latency(self, rollout_manager):
        """Test automatic rollback on high latency."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE, max_latency_ms=1000.0)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        # High latency metrics
        metrics = RolloutMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            feature_name="test_feature",
            enabled_users=50,
            total_users=100,
            error_rate=1.0,
            success_rate=99.0,
            avg_latency_ms=500.0,
            p95_latency_ms=2000.0  # Above threshold
        )
        
        rollout_manager.collect_metrics("test_feature", metrics)
        
        rollout = rollout_manager.rollouts["test_feature"]
        assert rollout.status == RolloutStatus.ROLLED_BACK
        assert "latency" in rollout.rollback_reason
    
    def test_automatic_rollback_success_rate(self, rollout_manager):
        """Test automatic rollback on low success rate."""
        config = RolloutConfig("test_feature", RolloutStrategy.PERCENTAGE, min_success_rate=98.0)
        rollout_manager.create_rollout(config)
        rollout_manager.start_rollout("test_feature")
        
        # Low success rate metrics
        metrics = RolloutMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            feature_name="test_feature",
            enabled_users=50,
            total_users=100,
            error_rate=1.0,
            success_rate=95.0,  # Below threshold
            avg_latency_ms=100.0,
            p95_latency_ms=200.0
        )
        
        rollout_manager.collect_metrics("test_feature", metrics)
        
        rollout = rollout_manager.rollouts["test_feature"]
        assert rollout.status == RolloutStatus.ROLLED_BACK
        assert "Success rate" in rollout.rollback_reason


class TestABTestManager:
    """Test A/B test manager functionality."""
    
    @pytest.fixture
    def ab_test_manager(self):
        """Create fresh A/B test manager for each test."""
        rollout_manager = RolloutManager()
        return ABTestManager(rollout_manager)
    
    def test_create_ab_test(self, ab_test_manager):
        """Test creating an A/B test."""
        success = ab_test_manager.create_ab_test(
            experiment_name="test_experiment",
            feature_name="test_feature",
            control_percentage=50.0,
            treatment_percentage=50.0,
            duration_days=7
        )
        
        assert success is True
        assert "test_experiment" in ab_test_manager.experiments
        
        experiment = ab_test_manager.experiments["test_experiment"]
        assert experiment['feature_name'] == "test_feature"
        assert experiment['rollout_state'].config.strategy == RolloutStrategy.AB_TEST
    
    def test_get_experiment_results_insufficient_data(self, ab_test_manager):
        """Test getting experiment results with insufficient data."""
        ab_test_manager.create_ab_test("test_experiment", "test_feature")
        
        results = ab_test_manager.get_experiment_results("test_experiment")
        
        assert results is not None
        assert results['status'] == 'insufficient_data'
        assert results['control_sample_size'] == 0
        assert results['treatment_sample_size'] == 0
    
    def test_get_experiment_results_with_data(self, ab_test_manager):
        """Test getting experiment results with data."""
        ab_test_manager.create_ab_test("test_experiment", "test_feature")
        
        # Add mock metrics
        experiment = ab_test_manager.experiments["test_experiment"]
        experiment['control_metrics'] = [
            {'success_rate': 95.0},
            {'success_rate': 96.0},
            {'success_rate': 94.0}
        ]
        experiment['treatment_metrics'] = [
            {'success_rate': 97.0},
            {'success_rate': 98.0},
            {'success_rate': 96.0}
        ]
        
        results = ab_test_manager.get_experiment_results("test_experiment")
        
        assert results is not None
        assert results['status'] == 'active'
        assert results['control_sample_size'] == 3
        assert results['treatment_sample_size'] == 3
        assert results['control_success_rate'] == 95.0
        assert results['treatment_success_rate'] == 97.0
        assert results['improvement_percentage'] > 0
    
    def test_get_nonexistent_experiment_results(self, ab_test_manager):
        """Test getting results for nonexistent experiment."""
        results = ab_test_manager.get_experiment_results("nonexistent")
        assert results is None


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('services.rollout.get_rollout_manager')
    def test_is_feature_enabled_for_user(self, mock_get_manager):
        """Test is_feature_enabled_for_user convenience function."""
        mock_manager = MagicMock()
        mock_manager.is_feature_enabled.return_value = True
        mock_get_manager.return_value = mock_manager
        
        enabled = is_feature_enabled_for_user("test_feature", "user_1")
        
        assert enabled is True
        mock_manager.is_feature_enabled.assert_called_once_with("test_feature", "user_1")
    
    @patch('services.rollout.get_rollout_manager')
    def test_create_feature_rollout(self, mock_get_manager):
        """Test create_feature_rollout convenience function."""
        mock_manager = MagicMock()
        mock_rollout_state = MagicMock()
        mock_manager.create_rollout.return_value = mock_rollout_state
        mock_get_manager.return_value = mock_manager
        
        rollout_state = create_feature_rollout("test_feature", RolloutStrategy.PERCENTAGE)
        
        assert rollout_state == mock_rollout_state
        mock_manager.create_rollout.assert_called_once()
    
    @patch('services.rollout.get_rollout_manager')
    def test_start_feature_rollout(self, mock_get_manager):
        """Test start_feature_rollout convenience function."""
        mock_manager = MagicMock()
        mock_manager.start_rollout.return_value = True
        mock_get_manager.return_value = mock_manager
        
        success = start_feature_rollout("test_feature")
        
        assert success is True
        mock_manager.start_rollout.assert_called_once_with("test_feature")


class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_rollout_lifecycle(self):
        """Test complete rollout lifecycle."""
        manager = RolloutManager()
        
        # Create rollout
        config = RolloutConfig(
            "integration_test_feature",
            RolloutStrategy.GRADUAL,
            initial_percentage=10.0,
            increment_percentage=30.0,
            target_percentage=100.0
        )
        rollout_state = manager.create_rollout(config)
        assert rollout_state.status == RolloutStatus.PLANNED
        
        # Start rollout
        manager.start_rollout("integration_test_feature")
        rollout = manager.rollouts["integration_test_feature"]
        assert rollout.status == RolloutStatus.ACTIVE
        assert rollout.current_percentage == 10.0
        
        # Collect good metrics
        good_metrics = RolloutMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            feature_name="integration_test_feature",
            enabled_users=10,
            total_users=100,
            error_rate=0.5,
            success_rate=99.5,
            avg_latency_ms=50.0,
            p95_latency_ms=100.0
        )
        manager.collect_metrics("integration_test_feature", good_metrics)
        
        # Verify no rollback occurred
        assert rollout.status == RolloutStatus.ACTIVE
        
        # Simulate progress update
        rollout.start_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        manager.update_rollout_progress("integration_test_feature")
        
        # Should have incremented
        assert rollout.current_percentage == 40.0  # 10% + 30%
        
        # Get status
        status = manager.get_rollout_status("integration_test_feature")
        assert status is not None
        assert status.feature_name == "integration_test_feature"


if __name__ == "__main__":
    pytest.main([__file__])
