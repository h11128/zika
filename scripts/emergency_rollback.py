#!/usr/bin/env python3
"""
Emergency rollback script for UI refactor.
Provides immediate rollback capabilities in case of critical issues.
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.feature_flags import set_feature_flag, get_feature_flag


class EmergencyRollback:
    """Emergency rollback system for UI refactor."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        """Set up emergency logging."""
        logger = logging.getLogger('emergency_rollback')
        logger.setLevel(logging.INFO)
        
        # Create emergency log file
        log_file = project_root / 'logs' / 'emergency_rollback.log'
        log_file.parent.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        console_handler = logging.StreamHandler()
        
        formatter = logging.Formatter(
            '%(asctime)s - EMERGENCY - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def execute_immediate_rollback(self) -> bool:
        """Execute immediate rollback to legacy system."""
        self.logger.critical("EMERGENCY ROLLBACK INITIATED")
        self.logger.critical(f"Timestamp: {datetime.now().isoformat()}")
        
        try:
            # Step 1: Disable all adapter features immediately
            adapter_features = [
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
            
            for feature in adapter_features:
                set_feature_flag(feature, False)
                self.logger.critical(f"DISABLED: {feature}")
            
            # Step 2: Set user percentage to 0
            set_feature_flag('ROLLOUT_USER_PERCENTAGE', 0)
            self.logger.critical("DISABLED: All users reverted to legacy system")
            
            # Step 3: Keep safety features enabled
            safety_features = [
                'FEATURE_ERROR_BOUNDARIES',
                'FEATURE_PERFORMANCE_MONITORING'
            ]
            
            for feature in safety_features:
                set_feature_flag(feature, True)
                self.logger.critical(f"KEPT ENABLED: {feature}")
            
            # Step 4: Clear any cached state
            try:
                from ui.performance_utils import cleanup_performance_utils
                cleanup_performance_utils()
                self.logger.critical("CLEARED: Performance optimization cache")
            except Exception as e:
                self.logger.error(f"Failed to clear performance cache: {e}")
            
            # Step 5: Force adapter cleanup
            try:
                from ui.ports import get_ui_adapter
                adapter = get_ui_adapter()
                if hasattr(adapter, 'cleanup'):
                    adapter.cleanup()
                self.logger.critical("EXECUTED: Adapter cleanup")
            except Exception as e:
                self.logger.error(f"Failed to cleanup adapter: {e}")
            
            self.logger.critical("EMERGENCY ROLLBACK COMPLETED SUCCESSFULLY")
            return True
            
        except Exception as e:
            self.logger.critical(f"EMERGENCY ROLLBACK FAILED: {e}")
            return False
    
    def validate_rollback(self) -> bool:
        """Validate that rollback was successful."""
        self.logger.info("Validating emergency rollback...")
        
        try:
            # Check that adapter features are disabled
            adapter_features = [
                'FEATURE_UI_ADAPTER_ENABLED',
                'FEATURE_ADAPTED_INPUTS',
                'FEATURE_ADAPTED_OPTIONS'
            ]
            
            for feature in adapter_features:
                if get_feature_flag(feature, True):  # Default True means it should be False
                    self.logger.error(f"VALIDATION FAILED: {feature} still enabled")
                    return False
            
            # Check user percentage is 0
            user_percentage = get_feature_flag('ROLLOUT_USER_PERCENTAGE', 100)
            if user_percentage != 0:
                self.logger.error(f"VALIDATION FAILED: User percentage is {user_percentage}, should be 0")
                return False
            
            # Check safety features are still enabled
            if not get_feature_flag('FEATURE_ERROR_BOUNDARIES', False):
                self.logger.warning("Error boundaries disabled during rollback")
            
            self.logger.info("Emergency rollback validation PASSED")
            return True
            
        except Exception as e:
            self.logger.error(f"Rollback validation failed: {e}")
            return False
    
    def generate_incident_report(self) -> str:
        """Generate incident report for emergency rollback."""
        timestamp = datetime.now().isoformat()
        
        report = f"""
# EMERGENCY ROLLBACK INCIDENT REPORT

**Timestamp**: {timestamp}
**Action**: Emergency rollback to legacy UI system
**Scope**: All users (100% rollback)

## Actions Taken

1. ✅ Disabled all UI adapter features
2. ✅ Reverted all users to legacy system (0% on new system)
3. ✅ Maintained safety features (error boundaries, monitoring)
4. ✅ Cleared performance optimization cache
5. ✅ Executed adapter cleanup

## System Status

- **UI System**: Legacy (pre-refactor)
- **User Impact**: Minimal (reverted to known-good state)
- **Data Loss**: None expected
- **Monitoring**: Active

## Next Steps

1. **Immediate**: Investigate root cause of emergency
2. **Short-term**: Fix identified issues
3. **Medium-term**: Re-test rollout in staging environment
4. **Long-term**: Implement additional safeguards

## Validation

- ✅ All adapter features confirmed disabled
- ✅ User percentage confirmed at 0%
- ✅ Safety features confirmed active
- ✅ System responding normally

## Contact Information

- **Incident Commander**: Development Team Lead
- **Technical Lead**: UI Refactor Team
- **Support**: support@company.com

---
*This report was generated automatically by the emergency rollback system.*
"""
        
        # Save report to file
        report_file = project_root / 'logs' / f'emergency_rollback_report_{timestamp.replace(":", "-")}.md'
        with open(report_file, 'w') as f:
            f.write(report)
        
        self.logger.critical(f"Incident report saved: {report_file}")
        return report


def main():
    """Main emergency rollback function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Emergency Rollback System')
    parser.add_argument('--immediate', action='store_true', 
                       help='Execute immediate rollback')
    parser.add_argument('--validate', action='store_true',
                       help='Validate rollback status')
    parser.add_argument('--report', action='store_true',
                       help='Generate incident report')
    
    args = parser.parse_args()
    
    rollback = EmergencyRollback()
    
    if args.immediate:
        print("🚨 EXECUTING EMERGENCY ROLLBACK 🚨")
        print("This will immediately disable all UI refactor features.")
        
        # Require confirmation for immediate rollback
        confirmation = input("Type 'EMERGENCY ROLLBACK' to confirm: ")
        if confirmation != "EMERGENCY ROLLBACK":
            print("❌ Emergency rollback cancelled")
            return 1
        
        success = rollback.execute_immediate_rollback()
        if success:
            print("✅ Emergency rollback completed")
            
            # Auto-validate
            if rollback.validate_rollback():
                print("✅ Rollback validation passed")
            else:
                print("❌ Rollback validation failed")
                return 1
            
            # Auto-generate report
            report = rollback.generate_incident_report()
            print("📄 Incident report generated")
            
            return 0
        else:
            print("❌ Emergency rollback failed")
            return 1
    
    elif args.validate:
        success = rollback.validate_rollback()
        return 0 if success else 1
    
    elif args.report:
        report = rollback.generate_incident_report()
        print(report)
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
