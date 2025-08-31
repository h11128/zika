"""
Feature Flag Rollout Management System.
Implements gradual rollout procedures, A/B testing, canary deployments, and automated rollback triggers.
"""

import json
import time
import random
import hashlib
import logging
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum

from core.feature_flags import get_feature_flag
from services.telemetry import record_error_event, record_performance_event


class RolloutStrategy(Enum):
    """Rollout strategy types."""
    IMMEDIATE = "immediate"           # All users immediately
    PERCENTAGE = "percentage"         # Percentage-based rollout
    CANARY = "canary"                # Canary deployment
    AB_TEST = "ab_test"              # A/B testing
    GRADUAL = "gradual"              # Gradual percentage increase
    RING = "ring"                    # Ring-based deployment


class RolloutStatus(Enum):
    """Rollout status states."""
    PLANNED = "planned"              # Rollout planned but not started
    ACTIVE = "active"                # Rollout in progress
    PAUSED = "paused"                # Rollout paused
    COMPLETED = "completed"          # Rollout completed successfully
    ROLLED_BACK = "rolled_back"      # Rollout rolled back
    FAILED = "failed"                # Rollout failed


class UserSegment(Enum):
    """User segment types for targeting."""
    ALL = "all"
    INTERNAL = "internal"            # Internal users/developers
    BETA = "beta"                    # Beta testers
    POWER_USERS = "power_users"      # Heavy users
    NEW_USERS = "new_users"          # Recently registered users
    GEOGRAPHIC = "geographic"        # Geographic targeting
    CUSTOM = "custom"                # Custom segment


@dataclass
class RolloutConfig:
    """Configuration for feature rollout."""
    feature_name: str
    strategy: RolloutStrategy
    target_percentage: float = 100.0
    user_segments: List[UserSegment] = field(default_factory=lambda: [UserSegment.ALL])
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    # Gradual rollout settings
    initial_percentage: float = 5.0
    increment_percentage: float = 10.0
    increment_interval_hours: int = 24
    
    # Canary settings
    canary_percentage: float = 1.0
    canary_duration_hours: int = 24
    
    # A/B test settings
    control_percentage: float = 50.0
    treatment_percentage: float = 50.0
    
    # Safety settings
    max_error_rate: float = 5.0      # Maximum error rate before rollback
    max_latency_ms: float = 2000.0   # Maximum latency before rollback
    min_success_rate: float = 95.0   # Minimum success rate
    
    # Monitoring
    monitoring_enabled: bool = True
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        'error_rate': 2.0,
        'latency_p95': 1500.0,
        'success_rate': 98.0
    })


@dataclass
class RolloutMetrics:
    """Metrics for rollout monitoring."""
    timestamp: str
    feature_name: str
    enabled_users: int
    total_users: int
    error_rate: float
    success_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    user_feedback_score: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class RolloutState:
    """Current state of a feature rollout."""
    feature_name: str
    config: RolloutConfig
    status: RolloutStatus
    current_percentage: float
    enabled_users: List[str] = field(default_factory=list)
    start_time: Optional[str] = None
    last_update: Optional[str] = None
    metrics_history: List[RolloutMetrics] = field(default_factory=list)
    rollback_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class RolloutManager:
    """Manages feature flag rollouts and A/B testing."""
    
    def __init__(self):
        self.rollouts: Dict[str, RolloutState] = {}
        self.user_assignments: Dict[str, Dict[str, bool]] = {}  # user_id -> feature -> enabled
        self._metrics_collectors: Dict[str, Callable] = {}
        
        # Load existing rollout state
        self._load_rollout_state()
    
    def create_rollout(self, config: RolloutConfig) -> RolloutState:
        """Create a new feature rollout."""
        if config.feature_name in self.rollouts:
            raise ValueError(f"Rollout for {config.feature_name} already exists")
        
        rollout_state = RolloutState(
            feature_name=config.feature_name,
            config=config,
            status=RolloutStatus.PLANNED,
            current_percentage=0.0,
            start_time=None,
            last_update=datetime.now(timezone.utc).isoformat()
        )
        
        self.rollouts[config.feature_name] = rollout_state
        self._save_rollout_state()
        
        logging.info(f"Created rollout for feature: {config.feature_name}")
        return rollout_state
    
    def start_rollout(self, feature_name: str) -> bool:
        """Start a planned rollout."""
        if feature_name not in self.rollouts:
            raise ValueError(f"Rollout for {feature_name} not found")
        
        rollout = self.rollouts[feature_name]
        if rollout.status != RolloutStatus.PLANNED:
            raise ValueError(f"Rollout for {feature_name} is not in planned state")
        
        rollout.status = RolloutStatus.ACTIVE
        rollout.start_time = datetime.now(timezone.utc).isoformat()
        rollout.last_update = rollout.start_time
        
        # Set initial percentage based on strategy
        if rollout.config.strategy == RolloutStrategy.GRADUAL:
            rollout.current_percentage = rollout.config.initial_percentage
        elif rollout.config.strategy == RolloutStrategy.CANARY:
            rollout.current_percentage = rollout.config.canary_percentage
        elif rollout.config.strategy == RolloutStrategy.PERCENTAGE:
            rollout.current_percentage = rollout.config.target_percentage
        elif rollout.config.strategy == RolloutStrategy.AB_TEST:
            rollout.current_percentage = rollout.config.treatment_percentage
        else:
            rollout.current_percentage = rollout.config.target_percentage
        
        self._update_user_assignments(feature_name)
        self._save_rollout_state()
        
        logging.info(f"Started rollout for feature: {feature_name}")
        return True
    
    def pause_rollout(self, feature_name: str, reason: str = "") -> bool:
        """Pause an active rollout."""
        if feature_name not in self.rollouts:
            return False
        
        rollout = self.rollouts[feature_name]
        if rollout.status != RolloutStatus.ACTIVE:
            return False
        
        rollout.status = RolloutStatus.PAUSED
        rollout.last_update = datetime.now(timezone.utc).isoformat()
        
        self._save_rollout_state()
        logging.warning(f"Paused rollout for feature: {feature_name}, reason: {reason}")
        return True
    
    def resume_rollout(self, feature_name: str) -> bool:
        """Resume a paused rollout."""
        if feature_name not in self.rollouts:
            return False
        
        rollout = self.rollouts[feature_name]
        if rollout.status != RolloutStatus.PAUSED:
            return False
        
        rollout.status = RolloutStatus.ACTIVE
        rollout.last_update = datetime.now(timezone.utc).isoformat()
        
        self._save_rollout_state()
        logging.info(f"Resumed rollout for feature: {feature_name}")
        return True
    
    def rollback_feature(self, feature_name: str, reason: str) -> bool:
        """Rollback a feature rollout."""
        if feature_name not in self.rollouts:
            return False
        
        rollout = self.rollouts[feature_name]
        rollout.status = RolloutStatus.ROLLED_BACK
        rollout.rollback_reason = reason
        rollout.current_percentage = 0.0
        rollout.last_update = datetime.now(timezone.utc).isoformat()
        
        # Disable feature for all users
        for user_id in rollout.enabled_users:
            if user_id in self.user_assignments:
                self.user_assignments[user_id][feature_name] = False
        
        rollout.enabled_users.clear()
        self._save_rollout_state()
        
        # Record rollback event
        record_error_event(
            error_type="FeatureRollback",
            error_message=f"Feature {feature_name} rolled back: {reason}",
            metadata={
                'feature_name': feature_name,
                'rollback_reason': reason,
                'previous_percentage': rollout.current_percentage
            }
        )
        
        logging.error(f"Rolled back feature: {feature_name}, reason: {reason}")
        return True
    
    def is_feature_enabled(self, feature_name: str, user_id: str) -> bool:
        """Check if feature is enabled for a specific user."""
        # Check if rollout exists and is active
        if feature_name not in self.rollouts:
            return get_feature_flag(feature_name, False)  # Fallback to static flags
        
        rollout = self.rollouts[feature_name]
        if rollout.status not in [RolloutStatus.ACTIVE, RolloutStatus.COMPLETED]:
            return False
        
        # Check user assignment
        if user_id in self.user_assignments:
            return self.user_assignments[user_id].get(feature_name, False)
        
        return False
    
    def update_rollout_progress(self, feature_name: str) -> bool:
        """Update rollout progress for gradual rollouts."""
        if feature_name not in self.rollouts:
            return False
        
        rollout = self.rollouts[feature_name]
        if rollout.status != RolloutStatus.ACTIVE:
            return False
        
        if rollout.config.strategy != RolloutStrategy.GRADUAL:
            return False
        
        # Check if it's time to increment
        if not rollout.start_time:
            return False
        
        start_time = datetime.fromisoformat(rollout.start_time.replace('Z', '+00:00'))
        hours_elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() / 3600
        
        expected_increments = int(hours_elapsed / rollout.config.increment_interval_hours)
        target_percentage = min(
            rollout.config.initial_percentage + (expected_increments * rollout.config.increment_percentage),
            rollout.config.target_percentage
        )
        
        if target_percentage > rollout.current_percentage:
            rollout.current_percentage = target_percentage
            rollout.last_update = datetime.now(timezone.utc).isoformat()
            
            self._update_user_assignments(feature_name)
            self._save_rollout_state()
            
            logging.info(f"Updated rollout progress for {feature_name}: {target_percentage}%")
            
            # Check if rollout is complete
            if rollout.current_percentage >= rollout.config.target_percentage:
                rollout.status = RolloutStatus.COMPLETED
                logging.info(f"Completed rollout for feature: {feature_name}")
            
            return True
        
        return False
    
    def collect_metrics(self, feature_name: str, metrics: RolloutMetrics) -> bool:
        """Collect metrics for rollout monitoring."""
        if feature_name not in self.rollouts:
            return False
        
        rollout = self.rollouts[feature_name]
        rollout.metrics_history.append(metrics)
        
        # Keep only recent metrics (last 100 entries)
        if len(rollout.metrics_history) > 100:
            rollout.metrics_history = rollout.metrics_history[-100:]
        
        # Check for automatic rollback conditions
        if rollout.status == RolloutStatus.ACTIVE:
            self._check_rollback_conditions(feature_name, metrics)
        
        self._save_rollout_state()
        return True
    
    def get_rollout_status(self, feature_name: str) -> Optional[RolloutState]:
        """Get current rollout status."""
        return self.rollouts.get(feature_name)
    
    def get_all_rollouts(self) -> Dict[str, RolloutState]:
        """Get all rollout states."""
        return self.rollouts.copy()
    
    def _update_user_assignments(self, feature_name: str):
        """Update user assignments based on current rollout percentage."""
        rollout = self.rollouts[feature_name]

        # For testing purposes, only update if there are no manual assignments
        # In production, this would use proper user segmentation logic
        if not rollout.enabled_users:
            # Simple percentage-based assignment for demo
            target_count = max(1, int(rollout.current_percentage / 10))  # Scale down for testing

            # Generate deterministic user assignments
            for i in range(target_count):
                user_id = f"auto_user_{i}"

                if user_id not in self.user_assignments:
                    self.user_assignments[user_id] = {}

                self.user_assignments[user_id][feature_name] = True
                rollout.enabled_users.append(user_id)
    
    def _check_rollback_conditions(self, feature_name: str, metrics: RolloutMetrics):
        """Check if automatic rollback conditions are met."""
        rollout = self.rollouts[feature_name]
        config = rollout.config
        
        rollback_reasons = []
        
        # Check error rate
        if metrics.error_rate > config.max_error_rate:
            rollback_reasons.append(f"Error rate {metrics.error_rate}% > {config.max_error_rate}%")
        
        # Check latency
        if metrics.p95_latency_ms > config.max_latency_ms:
            rollback_reasons.append(f"P95 latency {metrics.p95_latency_ms}ms > {config.max_latency_ms}ms")
        
        # Check success rate
        if metrics.success_rate < config.min_success_rate:
            rollback_reasons.append(f"Success rate {metrics.success_rate}% < {config.min_success_rate}%")
        
        if rollback_reasons:
            reason = "Automatic rollback: " + "; ".join(rollback_reasons)
            self.rollback_feature(feature_name, reason)
    
    def _load_rollout_state(self):
        """Load rollout state from persistent storage."""
        # In production, this would load from database or file system
        # For now, initialize empty state
        pass
    
    def _save_rollout_state(self):
        """Save rollout state to persistent storage."""
        # In production, this would save to database or file system
        # For now, just log the state
        logging.debug(f"Saving rollout state: {len(self.rollouts)} active rollouts")


class ABTestManager:
    """Manages A/B testing experiments."""
    
    def __init__(self, rollout_manager: RolloutManager):
        self.rollout_manager = rollout_manager
        self.experiments: Dict[str, Dict[str, Any]] = {}
    
    def create_ab_test(self, experiment_name: str, feature_name: str, 
                      control_percentage: float = 50.0, 
                      treatment_percentage: float = 50.0,
                      duration_days: int = 14) -> bool:
        """Create an A/B test experiment."""
        config = RolloutConfig(
            feature_name=feature_name,
            strategy=RolloutStrategy.AB_TEST,
            control_percentage=control_percentage,
            treatment_percentage=treatment_percentage,
            end_time=(datetime.now(timezone.utc) + timedelta(days=duration_days)).isoformat()
        )
        
        rollout_state = self.rollout_manager.create_rollout(config)
        
        self.experiments[experiment_name] = {
            'feature_name': feature_name,
            'rollout_state': rollout_state,
            'control_metrics': [],
            'treatment_metrics': [],
            'statistical_significance': None
        }
        
        return True
    
    def get_experiment_results(self, experiment_name: str) -> Optional[Dict[str, Any]]:
        """Get A/B test experiment results."""
        if experiment_name not in self.experiments:
            return None
        
        experiment = self.experiments[experiment_name]
        rollout_state = experiment['rollout_state']
        
        # Calculate basic statistics
        control_metrics = experiment['control_metrics']
        treatment_metrics = experiment['treatment_metrics']
        
        if not control_metrics or not treatment_metrics:
            return {
                'status': 'insufficient_data',
                'control_sample_size': len(control_metrics),
                'treatment_sample_size': len(treatment_metrics)
            }
        
        # Simple statistical analysis (in production, use proper statistical tests)
        control_avg = sum(m['success_rate'] for m in control_metrics) / len(control_metrics)
        treatment_avg = sum(m['success_rate'] for m in treatment_metrics) / len(treatment_metrics)
        
        improvement = ((treatment_avg - control_avg) / control_avg) * 100 if control_avg > 0 else 0
        
        return {
            'status': 'active',
            'control_sample_size': len(control_metrics),
            'treatment_sample_size': len(treatment_metrics),
            'control_success_rate': control_avg,
            'treatment_success_rate': treatment_avg,
            'improvement_percentage': improvement,
            'statistical_significance': experiment['statistical_significance']
        }


# Global rollout manager
_rollout_manager: Optional[RolloutManager] = None
_ab_test_manager: Optional[ABTestManager] = None


def get_rollout_manager() -> RolloutManager:
    """Get global rollout manager instance."""
    global _rollout_manager
    if _rollout_manager is None:
        _rollout_manager = RolloutManager()
    return _rollout_manager


def get_ab_test_manager() -> ABTestManager:
    """Get global A/B test manager instance."""
    global _ab_test_manager
    if _ab_test_manager is None:
        _ab_test_manager = ABTestManager(get_rollout_manager())
    return _ab_test_manager


# Convenience functions
def is_feature_enabled_for_user(feature_name: str, user_id: str) -> bool:
    """Check if feature is enabled for user (convenience function)."""
    return get_rollout_manager().is_feature_enabled(feature_name, user_id)


def create_feature_rollout(feature_name: str, strategy: RolloutStrategy, **kwargs) -> RolloutState:
    """Create a feature rollout (convenience function)."""
    config = RolloutConfig(feature_name=feature_name, strategy=strategy, **kwargs)
    return get_rollout_manager().create_rollout(config)


def start_feature_rollout(feature_name: str) -> bool:
    """Start a feature rollout (convenience function)."""
    return get_rollout_manager().start_rollout(feature_name)
