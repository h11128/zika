#!/usr/bin/env python3
"""
Feature Flag Rollout Management Script.
Provides command-line interface for managing feature rollouts, A/B tests, and monitoring.
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.rollout import (
    RolloutManager, ABTestManager, RolloutStrategy, RolloutStatus, RolloutConfig,
    RolloutMetrics, get_rollout_manager, get_ab_test_manager
)


def create_rollout(args):
    """Create a new feature rollout."""
    manager = get_rollout_manager()
    
    try:
        # Parse strategy
        strategy = RolloutStrategy(args.strategy)
        
        # Create configuration
        config = RolloutConfig(
            feature_name=args.feature,
            strategy=strategy,
            target_percentage=args.target_percentage,
            initial_percentage=args.initial_percentage,
            increment_percentage=args.increment_percentage,
            increment_interval_hours=args.increment_interval,
            canary_percentage=args.canary_percentage,
            max_error_rate=args.max_error_rate,
            max_latency_ms=args.max_latency,
            min_success_rate=args.min_success_rate
        )
        
        # Create rollout
        rollout_state = manager.create_rollout(config)
        
        print(f"✅ Created rollout for feature: {args.feature}")
        print(f"   Strategy: {strategy.value}")
        print(f"   Target: {args.target_percentage}%")
        print(f"   Status: {rollout_state.status.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating rollout: {e}")
        return False


def start_rollout(args):
    """Start a planned rollout."""
    manager = get_rollout_manager()
    
    try:
        success = manager.start_rollout(args.feature)
        
        if success:
            rollout = manager.get_rollout_status(args.feature)
            print(f"🚀 Started rollout for feature: {args.feature}")
            print(f"   Current percentage: {rollout.current_percentage}%")
            print(f"   Status: {rollout.status.value}")
        else:
            print(f"❌ Failed to start rollout for feature: {args.feature}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error starting rollout: {e}")
        return False


def pause_rollout(args):
    """Pause an active rollout."""
    manager = get_rollout_manager()
    
    try:
        success = manager.pause_rollout(args.feature, args.reason or "Manual pause")
        
        if success:
            print(f"⏸️  Paused rollout for feature: {args.feature}")
            if args.reason:
                print(f"   Reason: {args.reason}")
        else:
            print(f"❌ Failed to pause rollout for feature: {args.feature}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error pausing rollout: {e}")
        return False


def resume_rollout(args):
    """Resume a paused rollout."""
    manager = get_rollout_manager()
    
    try:
        success = manager.resume_rollout(args.feature)
        
        if success:
            print(f"▶️  Resumed rollout for feature: {args.feature}")
        else:
            print(f"❌ Failed to resume rollout for feature: {args.feature}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error resuming rollout: {e}")
        return False


def rollback_rollout(args):
    """Rollback a feature rollout."""
    manager = get_rollout_manager()
    
    try:
        success = manager.rollback_feature(args.feature, args.reason)
        
        if success:
            print(f"🔄 Rolled back feature: {args.feature}")
            print(f"   Reason: {args.reason}")
        else:
            print(f"❌ Failed to rollback feature: {args.feature}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error rolling back feature: {e}")
        return False


def update_progress(args):
    """Update rollout progress for gradual rollouts."""
    manager = get_rollout_manager()
    
    try:
        success = manager.update_rollout_progress(args.feature)
        
        if success:
            rollout = manager.get_rollout_status(args.feature)
            print(f"📈 Updated rollout progress for feature: {args.feature}")
            print(f"   Current percentage: {rollout.current_percentage}%")
            print(f"   Status: {rollout.status.value}")
        else:
            print(f"ℹ️  No progress update needed for feature: {args.feature}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating progress: {e}")
        return False


def status_rollout(args):
    """Show rollout status."""
    manager = get_rollout_manager()
    
    try:
        if args.feature:
            # Show specific feature status
            rollout = manager.get_rollout_status(args.feature)
            if rollout:
                print_rollout_status(rollout)
            else:
                print(f"❌ Rollout not found for feature: {args.feature}")
        else:
            # Show all rollouts
            rollouts = manager.get_all_rollouts()
            if rollouts:
                print(f"📊 Active Rollouts ({len(rollouts)}):")
                print("=" * 60)
                for feature_name, rollout in rollouts.items():
                    print_rollout_summary(rollout)
                    print("-" * 60)
            else:
                print("ℹ️  No active rollouts found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return False


def collect_metrics(args):
    """Collect metrics for a rollout."""
    manager = get_rollout_manager()
    
    try:
        metrics = RolloutMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            feature_name=args.feature,
            enabled_users=args.enabled_users,
            total_users=args.total_users,
            error_rate=args.error_rate,
            success_rate=args.success_rate,
            avg_latency_ms=args.avg_latency,
            p95_latency_ms=args.p95_latency
        )
        
        success = manager.collect_metrics(args.feature, metrics)
        
        if success:
            print(f"📊 Collected metrics for feature: {args.feature}")
            print(f"   Error rate: {args.error_rate}%")
            print(f"   Success rate: {args.success_rate}%")
            print(f"   P95 latency: {args.p95_latency}ms")
            
            # Check if rollback occurred
            rollout = manager.get_rollout_status(args.feature)
            if rollout and rollout.status == RolloutStatus.ROLLED_BACK:
                print(f"⚠️  Automatic rollback triggered!")
                print(f"   Reason: {rollout.rollback_reason}")
        else:
            print(f"❌ Failed to collect metrics for feature: {args.feature}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error collecting metrics: {e}")
        return False


def create_ab_test(args):
    """Create an A/B test experiment."""
    ab_manager = get_ab_test_manager()
    
    try:
        success = ab_manager.create_ab_test(
            experiment_name=args.experiment,
            feature_name=args.feature,
            control_percentage=args.control_percentage,
            treatment_percentage=args.treatment_percentage,
            duration_days=args.duration_days
        )
        
        if success:
            print(f"🧪 Created A/B test experiment: {args.experiment}")
            print(f"   Feature: {args.feature}")
            print(f"   Control: {args.control_percentage}%")
            print(f"   Treatment: {args.treatment_percentage}%")
            print(f"   Duration: {args.duration_days} days")
        else:
            print(f"❌ Failed to create A/B test: {args.experiment}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error creating A/B test: {e}")
        return False


def ab_test_results(args):
    """Show A/B test results."""
    ab_manager = get_ab_test_manager()
    
    try:
        results = ab_manager.get_experiment_results(args.experiment)
        
        if results:
            print(f"🧪 A/B Test Results: {args.experiment}")
            print("=" * 50)
            print(f"Status: {results['status']}")
            print(f"Control Sample Size: {results['control_sample_size']}")
            print(f"Treatment Sample Size: {results['treatment_sample_size']}")
            
            if results['status'] == 'active':
                print(f"Control Success Rate: {results['control_success_rate']:.2f}%")
                print(f"Treatment Success Rate: {results['treatment_success_rate']:.2f}%")
                print(f"Improvement: {results['improvement_percentage']:.2f}%")
        else:
            print(f"❌ A/B test not found: {args.experiment}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting A/B test results: {e}")
        return False


def print_rollout_status(rollout):
    """Print detailed rollout status."""
    print(f"🎯 Feature: {rollout.feature_name}")
    print("=" * 50)
    print(f"Status: {rollout.status.value}")
    print(f"Strategy: {rollout.config.strategy.value}")
    print(f"Current Percentage: {rollout.current_percentage}%")
    print(f"Target Percentage: {rollout.config.target_percentage}%")
    
    if rollout.start_time:
        print(f"Started: {rollout.start_time}")
    
    if rollout.last_update:
        print(f"Last Updated: {rollout.last_update}")
    
    if rollout.rollback_reason:
        print(f"Rollback Reason: {rollout.rollback_reason}")
    
    print(f"Enabled Users: {len(rollout.enabled_users)}")
    print(f"Metrics History: {len(rollout.metrics_history)} entries")
    
    # Show recent metrics
    if rollout.metrics_history:
        latest_metrics = rollout.metrics_history[-1]
        print("\nLatest Metrics:")
        print(f"  Error Rate: {latest_metrics.error_rate}%")
        print(f"  Success Rate: {latest_metrics.success_rate}%")
        print(f"  P95 Latency: {latest_metrics.p95_latency_ms}ms")


def print_rollout_summary(rollout):
    """Print rollout summary."""
    status_emoji = {
        RolloutStatus.PLANNED: "📋",
        RolloutStatus.ACTIVE: "🚀",
        RolloutStatus.PAUSED: "⏸️",
        RolloutStatus.COMPLETED: "✅",
        RolloutStatus.ROLLED_BACK: "🔄",
        RolloutStatus.FAILED: "❌"
    }
    
    emoji = status_emoji.get(rollout.status, "❓")
    print(f"{emoji} {rollout.feature_name}")
    print(f"   Status: {rollout.status.value}")
    print(f"   Progress: {rollout.current_percentage}% / {rollout.config.target_percentage}%")
    print(f"   Strategy: {rollout.config.strategy.value}")


def main():
    """Main entry point for rollout management script."""
    parser = argparse.ArgumentParser(description="Manage feature flag rollouts")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create rollout command
    create_parser = subparsers.add_parser('create', help='Create a new rollout')
    create_parser.add_argument('feature', help='Feature name')
    create_parser.add_argument('strategy', choices=['percentage', 'gradual', 'canary', 'ab_test'], 
                              help='Rollout strategy')
    create_parser.add_argument('--target-percentage', type=float, default=100.0,
                              help='Target percentage (default: 100)')
    create_parser.add_argument('--initial-percentage', type=float, default=5.0,
                              help='Initial percentage for gradual rollout (default: 5)')
    create_parser.add_argument('--increment-percentage', type=float, default=10.0,
                              help='Increment percentage for gradual rollout (default: 10)')
    create_parser.add_argument('--increment-interval', type=int, default=24,
                              help='Increment interval in hours (default: 24)')
    create_parser.add_argument('--canary-percentage', type=float, default=1.0,
                              help='Canary percentage (default: 1)')
    create_parser.add_argument('--max-error-rate', type=float, default=5.0,
                              help='Maximum error rate before rollback (default: 5)')
    create_parser.add_argument('--max-latency', type=float, default=2000.0,
                              help='Maximum latency before rollback (default: 2000)')
    create_parser.add_argument('--min-success-rate', type=float, default=95.0,
                              help='Minimum success rate (default: 95)')
    
    # Start rollout command
    start_parser = subparsers.add_parser('start', help='Start a rollout')
    start_parser.add_argument('feature', help='Feature name')
    
    # Pause rollout command
    pause_parser = subparsers.add_parser('pause', help='Pause a rollout')
    pause_parser.add_argument('feature', help='Feature name')
    pause_parser.add_argument('--reason', help='Pause reason')
    
    # Resume rollout command
    resume_parser = subparsers.add_parser('resume', help='Resume a rollout')
    resume_parser.add_argument('feature', help='Feature name')
    
    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback a feature')
    rollback_parser.add_argument('feature', help='Feature name')
    rollback_parser.add_argument('reason', help='Rollback reason')
    
    # Update progress command
    update_parser = subparsers.add_parser('update', help='Update rollout progress')
    update_parser.add_argument('feature', help='Feature name')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show rollout status')
    status_parser.add_argument('feature', nargs='?', help='Feature name (optional)')
    
    # Metrics command
    metrics_parser = subparsers.add_parser('metrics', help='Collect metrics')
    metrics_parser.add_argument('feature', help='Feature name')
    metrics_parser.add_argument('--enabled-users', type=int, required=True,
                               help='Number of enabled users')
    metrics_parser.add_argument('--total-users', type=int, required=True,
                               help='Total number of users')
    metrics_parser.add_argument('--error-rate', type=float, required=True,
                               help='Error rate percentage')
    metrics_parser.add_argument('--success-rate', type=float, required=True,
                               help='Success rate percentage')
    metrics_parser.add_argument('--avg-latency', type=float, required=True,
                               help='Average latency in milliseconds')
    metrics_parser.add_argument('--p95-latency', type=float, required=True,
                               help='P95 latency in milliseconds')
    
    # A/B test commands
    ab_create_parser = subparsers.add_parser('ab-create', help='Create A/B test')
    ab_create_parser.add_argument('experiment', help='Experiment name')
    ab_create_parser.add_argument('feature', help='Feature name')
    ab_create_parser.add_argument('--control-percentage', type=float, default=50.0,
                                 help='Control group percentage (default: 50)')
    ab_create_parser.add_argument('--treatment-percentage', type=float, default=50.0,
                                 help='Treatment group percentage (default: 50)')
    ab_create_parser.add_argument('--duration-days', type=int, default=14,
                                 help='Experiment duration in days (default: 14)')
    
    ab_results_parser = subparsers.add_parser('ab-results', help='Show A/B test results')
    ab_results_parser.add_argument('experiment', help='Experiment name')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    command_map = {
        'create': create_rollout,
        'start': start_rollout,
        'pause': pause_rollout,
        'resume': resume_rollout,
        'rollback': rollback_rollout,
        'update': update_progress,
        'status': status_rollout,
        'metrics': collect_metrics,
        'ab-create': create_ab_test,
        'ab-results': ab_test_results
    }
    
    try:
        success = command_map[args.command](args)
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
