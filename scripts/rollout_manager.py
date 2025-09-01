#!/usr/bin/env python3
"""
Production rollout manager for UI refactor.
Handles gradual rollout, monitoring, and rollback capabilities.
"""

import sys
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.feature_flags import set_feature_flag, get_feature_flag
from services.performance_monitor import get_performance_monitor, validate_performance_targets


@dataclass
class RolloutConfig:
    """Rollout configuration."""
    name: str
    user_percentage: int
    feature_flags: Dict[str, bool]
    duration_hours: int = 24
    success_criteria: Dict[str, float] = None
    
    def __post_init__(self):
        if self.success_criteria is None:
            self.success_criteria = {
                'max_error_rate': 0.02,  # 2%
                'max_response_time_ms': 1000,
                'min_cache_hit_rate': 0.75,
                'max_memory_mb': 60
            }


class RolloutManager:
    """Manages production rollout of UI refactor."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.performance_monitor = get_performance_monitor()
        self.current_config: Optional[RolloutConfig] = None
        self.rollout_start_time: Optional[datetime] = None
        
        # Predefined rollout stages
        self.rollout_stages = [
            RolloutConfig(
                name="canary",
                user_percentage=5,
                feature_flags={
                    'FEATURE_UI_ADAPTER_ENABLED': True,
                    'FEATURE_ADAPTED_INPUTS': True,
                    'FEATURE_ADAPTED_OPTIONS': False,
                    'FEATURE_ADAPTED_SIDEBAR': False,
                    'FEATURE_ERROR_BOUNDARIES': True,
                    'FEATURE_PERFORMANCE_MONITORING': True
                },
                duration_hours=168  # 1 week
            ),
            RolloutConfig(
                name="limited",
                user_percentage=25,
                feature_flags={
                    'FEATURE_UI_ADAPTER_ENABLED': True,
                    'FEATURE_ADAPTED_INPUTS': True,
                    'FEATURE_ADAPTED_OPTIONS': True,
                    'FEATURE_ADAPTED_SIDEBAR': True,
                    'FEATURE_ERROR_BOUNDARIES': True,
                    'FEATURE_PERFORMANCE_OPTIMIZATION': True
                },
                duration_hours=336  # 2 weeks
            ),
            RolloutConfig(
                name="expansion",
                user_percentage=75,
                feature_flags={
                    'FEATURE_UI_ADAPTER_ENABLED': True,
                    'FEATURE_ADAPTED_INPUTS': True,
                    'FEATURE_ADAPTED_OPTIONS': True,
                    'FEATURE_ADAPTED_SIDEBAR': True,
                    'FEATURE_ADAPTED_PREVIEW': True,
                    'FEATURE_ADAPTED_EXPORT': True,
                    'FEATURE_ERROR_BOUNDARIES': True,
                    'FEATURE_PERFORMANCE_OPTIMIZATION': True,
                    'FEATURE_LAZY_LOADING': True,
                    'FEATURE_COMPONENT_CACHING': True
                },
                duration_hours=336  # 2 weeks
            ),
            RolloutConfig(
                name="full",
                user_percentage=100,
                feature_flags={
                    'FEATURE_UI_ADAPTER_ENABLED': True,
                    'FEATURE_ADAPTED_INPUTS': True,
                    'FEATURE_ADAPTED_OPTIONS': True,
                    'FEATURE_ADAPTED_SIDEBAR': True,
                    'FEATURE_ADAPTED_PREVIEW': True,
                    'FEATURE_ADAPTED_EXPORT': True,
                    'FEATURE_ERROR_BOUNDARIES': True,
                    'FEATURE_PERFORMANCE_OPTIMIZATION': True,
                    'FEATURE_LAZY_LOADING': True,
                    'FEATURE_COMPONENT_CACHING': True,
                    'FEATURE_SMART_FALLBACKS': True
                },
                duration_hours=-1  # Permanent
            )
        ]
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging for rollout manager."""
        logger = logging.getLogger('rollout_manager')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = project_root / 'logs' / 'rollout.log'
        log_file.parent.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def start_rollout_stage(self, stage_name: str) -> bool:
        """Start a specific rollout stage."""
        # Find the stage configuration
        stage_config = None
        for config in self.rollout_stages:
            if config.name == stage_name:
                stage_config = config
                break
        
        if not stage_config:
            self.logger.error(f"Unknown rollout stage: {stage_name}")
            return False
        
        self.logger.info(f"Starting rollout stage: {stage_name}")
        self.logger.info(f"Target user percentage: {stage_config.user_percentage}%")
        
        # Apply feature flags
        for flag, value in stage_config.feature_flags.items():
            try:
                set_feature_flag(flag, value)
                self.logger.info(f"Set {flag} = {value}")
            except Exception as e:
                self.logger.error(f"Failed to set {flag}: {e}")
                return False
        
        # Set user percentage (this would integrate with your user targeting system)
        try:
            set_feature_flag('ROLLOUT_USER_PERCENTAGE', stage_config.user_percentage)
            self.logger.info(f"Set user percentage to {stage_config.user_percentage}%")
        except Exception as e:
            self.logger.error(f"Failed to set user percentage: {e}")
            return False
        
        # Record rollout start
        self.current_config = stage_config
        self.rollout_start_time = datetime.now()
        
        # Save rollout state
        self._save_rollout_state()
        
        self.logger.info(f"Rollout stage {stage_name} started successfully")
        return True
    
    def check_rollout_health(self) -> Dict[str, Any]:
        """Check the health of the current rollout."""
        if not self.current_config:
            return {'status': 'no_active_rollout'}
        
        health_report = {
            'stage': self.current_config.name,
            'user_percentage': self.current_config.user_percentage,
            'start_time': self.rollout_start_time.isoformat() if self.rollout_start_time else None,
            'duration_hours': (datetime.now() - self.rollout_start_time).total_seconds() / 3600 if self.rollout_start_time else 0,
            'status': 'healthy',
            'issues': [],
            'metrics': {}
        }
        
        try:
            # Check performance targets
            performance_results = validate_performance_targets()
            health_report['metrics']['performance_targets'] = performance_results
            
            # Check if any performance targets are failing
            failing_targets = [target for target, met in performance_results.items() if not met]
            if failing_targets:
                health_report['status'] = 'degraded'
                health_report['issues'].extend([f"Performance target not met: {target}" for target in failing_targets])
            
        except Exception as e:
            health_report['status'] = 'error'
            health_report['issues'].append(f"Performance check failed: {e}")
        
        try:
            # Check error rates (this would integrate with your monitoring system)
            # For now, we'll simulate this check
            error_rate = self._get_current_error_rate()
            health_report['metrics']['error_rate'] = error_rate
            
            if error_rate > self.current_config.success_criteria['max_error_rate']:
                health_report['status'] = 'critical'
                health_report['issues'].append(f"Error rate too high: {error_rate:.3f}")
            
        except Exception as e:
            health_report['status'] = 'error'
            health_report['issues'].append(f"Error rate check failed: {e}")
        
        # Log health status
        if health_report['status'] == 'healthy':
            self.logger.info(f"Rollout health check: {health_report['status']}")
        else:
            self.logger.warning(f"Rollout health check: {health_report['status']} - Issues: {health_report['issues']}")
        
        return health_report
    
    def _get_current_error_rate(self) -> float:
        """Get current error rate (placeholder for actual monitoring integration)."""
        # This would integrate with your actual monitoring system
        # For now, return a simulated low error rate
        return 0.001  # 0.1%
    
    def should_proceed_to_next_stage(self) -> bool:
        """Check if rollout should proceed to next stage."""
        if not self.current_config or not self.rollout_start_time:
            return False
        
        # Check if minimum duration has passed
        duration = datetime.now() - self.rollout_start_time
        min_duration = timedelta(hours=24)  # Minimum 24 hours per stage
        
        if duration < min_duration:
            self.logger.info(f"Minimum duration not met: {duration.total_seconds()/3600:.1f}h < 24h")
            return False
        
        # Check health
        health = self.check_rollout_health()
        if health['status'] != 'healthy':
            self.logger.warning(f"Health check failed: {health['status']}")
            return False
        
        # Check if target duration reached
        if self.current_config.duration_hours > 0:
            target_duration = timedelta(hours=self.current_config.duration_hours)
            if duration >= target_duration:
                self.logger.info(f"Target duration reached: {duration.total_seconds()/3600:.1f}h >= {self.current_config.duration_hours}h")
                return True
        
        return False
    
    def proceed_to_next_stage(self) -> bool:
        """Proceed to the next rollout stage."""
        if not self.current_config:
            self.logger.error("No active rollout to proceed")
            return False
        
        # Find current stage index
        current_index = -1
        for i, config in enumerate(self.rollout_stages):
            if config.name == self.current_config.name:
                current_index = i
                break
        
        if current_index == -1:
            self.logger.error("Current stage not found in rollout stages")
            return False
        
        # Check if there's a next stage
        if current_index >= len(self.rollout_stages) - 1:
            self.logger.info("Already at final rollout stage")
            return True
        
        # Proceed to next stage
        next_stage = self.rollout_stages[current_index + 1]
        self.logger.info(f"Proceeding from {self.current_config.name} to {next_stage.name}")
        
        return self.start_rollout_stage(next_stage.name)
    
    def rollback(self, target_percentage: int = 0) -> bool:
        """Rollback to a specific user percentage."""
        self.logger.warning(f"Initiating rollback to {target_percentage}% users")
        
        try:
            # Disable all adapter features
            adapter_flags = [
                'FEATURE_UI_ADAPTER_ENABLED',
                'FEATURE_ADAPTED_INPUTS',
                'FEATURE_ADAPTED_OPTIONS',
                'FEATURE_ADAPTED_SIDEBAR',
                'FEATURE_ADAPTED_PREVIEW',
                'FEATURE_ADAPTED_EXPORT',
                'FEATURE_PERFORMANCE_OPTIMIZATION',
                'FEATURE_LAZY_LOADING',
                'FEATURE_COMPONENT_CACHING',
                'FEATURE_SMART_FALLBACKS'
            ]
            
            for flag in adapter_flags:
                set_feature_flag(flag, False)
                self.logger.info(f"Disabled {flag}")
            
            # Set user percentage
            set_feature_flag('ROLLOUT_USER_PERCENTAGE', target_percentage)
            self.logger.info(f"Set user percentage to {target_percentage}%")
            
            # Keep error boundaries and monitoring enabled for safety
            set_feature_flag('FEATURE_ERROR_BOUNDARIES', True)
            set_feature_flag('FEATURE_PERFORMANCE_MONITORING', True)
            
            # Clear current rollout state
            self.current_config = None
            self.rollout_start_time = None
            self._save_rollout_state()
            
            self.logger.warning(f"Rollback to {target_percentage}% completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
    
    def emergency_rollback(self) -> bool:
        """Emergency rollback to 0% users."""
        self.logger.critical("EMERGENCY ROLLBACK INITIATED")
        return self.rollback(0)
    
    def _save_rollout_state(self):
        """Save current rollout state to file."""
        state = {
            'current_config': asdict(self.current_config) if self.current_config else None,
            'rollout_start_time': self.rollout_start_time.isoformat() if self.rollout_start_time else None,
            'last_updated': datetime.now().isoformat()
        }
        
        state_file = project_root / 'rollout_state.json'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_rollout_state(self):
        """Load rollout state from file."""
        state_file = project_root / 'rollout_state.json'
        if not state_file.exists():
            return
        
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
            
            if state['current_config']:
                self.current_config = RolloutConfig(**state['current_config'])
            
            if state['rollout_start_time']:
                self.rollout_start_time = datetime.fromisoformat(state['rollout_start_time'])
            
            self.logger.info("Rollout state loaded from file")
            
        except Exception as e:
            self.logger.error(f"Failed to load rollout state: {e}")


def main():
    """Main CLI interface for rollout manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description='UI Refactor Rollout Manager')
    parser.add_argument('command', choices=['start', 'status', 'proceed', 'rollback', 'emergency'], 
                       help='Command to execute')
    parser.add_argument('--stage', help='Rollout stage for start command')
    parser.add_argument('--percentage', type=int, default=0, help='User percentage for rollback')
    
    args = parser.parse_args()
    
    manager = RolloutManager()
    manager.load_rollout_state()
    
    if args.command == 'start':
        if not args.stage:
            print("Error: --stage required for start command")
            return 1
        
        success = manager.start_rollout_stage(args.stage)
        return 0 if success else 1
    
    elif args.command == 'status':
        health = manager.check_rollout_health()
        print(json.dumps(health, indent=2))
        return 0
    
    elif args.command == 'proceed':
        if manager.should_proceed_to_next_stage():
            success = manager.proceed_to_next_stage()
            return 0 if success else 1
        else:
            print("Not ready to proceed to next stage")
            return 1
    
    elif args.command == 'rollback':
        success = manager.rollback(args.percentage)
        return 0 if success else 1
    
    elif args.command == 'emergency':
        success = manager.emergency_rollback()
        return 0 if success else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
