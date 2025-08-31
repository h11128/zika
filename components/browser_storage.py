"""
Enhanced browser storage bridge with localStorage integration and quota management.
Provides hydrate_once(), schedule_save(), and flush_if_due() functionality
with single rerun on hydration, debounced saves, and graceful degradation.
"""

import json
import time
import logging
from typing import Optional, Dict, Any, Callable, Tuple
from datetime import datetime, timezone
from enum import Enum
import streamlit as st
import streamlit.components.v1 as components

from core.feature_flags import get_feature_flag
from services.persistence import (
    UserSnapshot, create_snapshot_from_session, load_snapshot_from_data,
    is_persistence_enabled, MAX_SNAPSHOT_SIZE_BYTES, MAX_INPUT_TEXT_LENGTH
)


# Storage configuration
STORAGE_KEY = "zika_user_snapshot"
SAVE_DEBOUNCE_SECONDS = 2.0  # Debounce saves for 2 seconds
HYDRATION_TIMEOUT_MS = 1000  # Timeout for hydration
HYDRATION_SESSION_KEY = "_browser_storage_hydrated"
SAVE_SCHEDULE_KEY = "_browser_storage_save_scheduled"

# Quota management
STORAGE_QUOTA_WARNING_THRESHOLD = 0.8  # Warn at 80% of quota
STORAGE_QUOTA_CRITICAL_THRESHOLD = 0.95  # Critical at 95% of quota
QUOTA_CHECK_INTERVAL_SECONDS = 30  # Check quota every 30 seconds
LAST_QUOTA_CHECK_KEY = "_last_quota_check"


class StorageStatus(Enum):
    """Storage status levels."""
    AVAILABLE = "available"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"
    DISABLED = "disabled"


class BrowserStorageManager:
    """Manages browser localStorage integration."""
    
    def __init__(self):
        self.last_save_time: float = 0
        self.pending_save: bool = False
        self.hydrated: bool = False
        self.save_scheduled: bool = False
    
    def hydrate_once(self) -> bool:
        """
        Hydrate session state from localStorage once per session with single rerun.

        Returns:
            True if hydration occurred and rerun is needed, False otherwise
        """
        if not is_persistence_enabled():
            return False

        # Check if we've already hydrated this session
        if hasattr(st.session_state, HYDRATION_SESSION_KEY):
            self.hydrated = True
            return False

        # Mark hydration attempt immediately to prevent multiple calls
        st.session_state[HYDRATION_SESSION_KEY] = True
        self.hydrated = True

        try:
            # Try multiple methods to get localStorage data
            stored_data = self._get_from_localstorage_reliable()

            if stored_data:
                snapshot = load_snapshot_from_data(stored_data)
                if snapshot:
                    # Apply to session state
                    snapshot.apply_to_session_state(st.session_state)

                    # Mark successful hydration
                    st.session_state[f"{HYDRATION_SESSION_KEY}_success"] = True
                    st.session_state[f"{HYDRATION_SESSION_KEY}_timestamp"] = time.time()

                    logging.info(f"Session state hydrated from localStorage with {len(snapshot.cards)} cards")
                    return True  # Single rerun needed

            # Mark as attempted even if no data found
            st.session_state[f"{HYDRATION_SESSION_KEY}_attempted"] = True
            logging.debug("No localStorage data found for hydration")

        except Exception as e:
            logging.error(f"Failed to hydrate from localStorage: {e}")
            st.session_state[f"{HYDRATION_SESSION_KEY}_error"] = str(e)

        return False

    def _get_from_localstorage_reliable(self) -> Optional[Dict[str, Any]]:
        """Get data from localStorage using multiple fallback methods."""
        # Method 1: Try session state bridge
        storage_state_key = f"_localStorage_{STORAGE_KEY}"
        if storage_state_key in st.session_state:
            return st.session_state[storage_state_key]

        # Method 2: Try URL parameters (if data was passed via URL)
        try:
            query_params = st.experimental_get_query_params()
            if 'localStorage_data' in query_params:
                data_str = query_params['localStorage_data'][0]
                return json.loads(data_str)
        except Exception:
            pass

        # Method 3: Try the original JavaScript method
        return self._get_from_localstorage()

    def _set_localstorage_in_session(self, data: Dict[str, Any]) -> None:
        """Set localStorage data in session state for reliable access."""
        storage_state_key = f"_localStorage_{STORAGE_KEY}"
        st.session_state[storage_state_key] = data
    
    def schedule_save(self) -> None:
        """Schedule a debounced save to localStorage with improved tracking."""
        if not is_persistence_enabled():
            return

        current_time = time.time()

        # Update scheduling state
        self.pending_save = True
        self.save_scheduled = True

        # Store schedule time in session state for persistence across reruns
        st.session_state[SAVE_SCHEDULE_KEY] = current_time

        # The actual save will happen in flush_if_due()
        logging.debug(f"Save scheduled at {current_time}")

    def flush_if_due(self) -> bool:
        """
        Flush pending save if debounce period has elapsed with improved reliability.

        Returns:
            True if save was performed, False otherwise
        """
        if not is_persistence_enabled():
            return False

        # Check session state for scheduled save
        schedule_time = st.session_state.get(SAVE_SCHEDULE_KEY, 0)
        if not schedule_time and not self.pending_save:
            return False

        current_time = time.time()

        # Check if debounce period has elapsed
        time_since_schedule = current_time - schedule_time
        time_since_last_save = current_time - self.last_save_time

        if time_since_schedule < SAVE_DEBOUNCE_SECONDS and time_since_last_save < SAVE_DEBOUNCE_SECONDS:
            logging.debug(f"Save debounce not elapsed: {time_since_schedule:.2f}s since schedule, {time_since_last_save:.2f}s since last save")
            return False

        try:
            # Check storage quota before attempting save
            quota_status, quota_info = self.check_storage_quota()

            if quota_status == StorageStatus.EXCEEDED:
                logging.warning("Storage quota exceeded, attempting graceful degradation")
                return self._handle_quota_exceeded()

            # Create snapshot from current session state
            snapshot = create_snapshot_from_session(st.session_state)

            if snapshot:
                # Apply graceful degradation if needed
                if quota_status in [StorageStatus.WARNING, StorageStatus.CRITICAL]:
                    snapshot = self._apply_graceful_degradation(snapshot, quota_status)

                # Check if snapshot has meaningful changes
                if self._should_save_snapshot(snapshot):
                    # Save to localStorage
                    success = self._save_to_localstorage(snapshot.to_dict())

                    if success:
                        self.last_save_time = current_time
                        self.pending_save = False
                        self.save_scheduled = False

                        # Clear schedule from session state
                        if SAVE_SCHEDULE_KEY in st.session_state:
                            del st.session_state[SAVE_SCHEDULE_KEY]

                        logging.info(f"Session state saved to localStorage with {len(snapshot.cards)} cards")
                        return True
                else:
                    logging.debug("No meaningful changes to save")

        except Exception as e:
            logging.error(f"Failed to save to localStorage: {e}")

        # Clear pending save even if failed
        self.pending_save = False
        self.save_scheduled = False
        if SAVE_SCHEDULE_KEY in st.session_state:
            del st.session_state[SAVE_SCHEDULE_KEY]
        return False

    def _handle_quota_exceeded(self) -> bool:
        """Handle storage quota exceeded scenario."""
        try:
            # Try to clear old data to make space
            current_data = self._get_from_localstorage()
            if current_data:
                # Remove export history first
                if 'export_history' in current_data:
                    del current_data['export_history']
                    logging.info("Cleared export history to free storage space")

                # Try to save reduced data
                success = self._save_to_localstorage(current_data)
                if success:
                    return True

            # If still failing, clear all storage
            self.clear_storage()
            logging.warning("Cleared all localStorage due to quota exceeded")
            return False

        except Exception as e:
            logging.error(f"Failed to handle quota exceeded: {e}")
            return False

    def _apply_graceful_degradation(self, snapshot: UserSnapshot, quota_status: StorageStatus) -> UserSnapshot:
        """Apply graceful degradation to reduce snapshot size."""
        try:
            if quota_status == StorageStatus.CRITICAL:
                # Aggressive reduction for critical quota
                # Truncate input text
                if len(snapshot.input_text) > MAX_INPUT_TEXT_LENGTH // 2:
                    snapshot.input_text = snapshot.input_text[:MAX_INPUT_TEXT_LENGTH // 2]
                    logging.info("Truncated input text due to critical storage quota")

                # Clear export history
                snapshot.export_history = []
                logging.info("Cleared export history due to critical storage quota")

                # Reduce card count if necessary
                if len(snapshot.cards) > 100:
                    snapshot.cards = snapshot.cards[:100]
                    logging.info("Reduced card count to 100 due to critical storage quota")

            elif quota_status == StorageStatus.WARNING:
                # Moderate reduction for warning quota
                # Truncate input text
                if len(snapshot.input_text) > MAX_INPUT_TEXT_LENGTH * 0.8:
                    snapshot.input_text = snapshot.input_text[:int(MAX_INPUT_TEXT_LENGTH * 0.8)]
                    logging.info("Truncated input text due to storage quota warning")

                # Limit export history
                if len(snapshot.export_history) > 10:
                    snapshot.export_history = snapshot.export_history[-10:]
                    logging.info("Limited export history to 10 entries due to storage quota warning")

            return snapshot

        except Exception as e:
            logging.error(f"Failed to apply graceful degradation: {e}")
            return snapshot

    def _should_save_snapshot(self, snapshot: UserSnapshot) -> bool:
        """Check if snapshot has meaningful changes worth saving."""
        # Always save if we have cards or input text
        if snapshot.cards or snapshot.input_text.strip():
            return True

        # Save if we have non-default configuration
        if (snapshot.options or snapshot.layout or
            snapshot.typography or snapshot.visual or snapshot.preview):
            return True

        # Save if we have export history
        if snapshot.export_history:
            return True

        return False

    def force_save(self) -> bool:
        """Force immediate save to localStorage bypassing debounce."""
        if not is_persistence_enabled():
            return False

        try:
            snapshot = create_snapshot_from_session(st.session_state)

            if snapshot:
                success = self._save_to_localstorage(snapshot.to_dict())

                if success:
                    self.last_save_time = time.time()
                    self.pending_save = False
                    self.save_scheduled = False

                    # Clear schedule from session state
                    if SAVE_SCHEDULE_KEY in st.session_state:
                        del st.session_state[SAVE_SCHEDULE_KEY]

                    logging.info(f"Session state force saved to localStorage with {len(snapshot.cards)} cards")
                    return True

        except Exception as e:
            logging.error(f"Failed to force save to localStorage: {e}")

        return False

    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about storage state for debugging."""
        return {
            'hydrated': self.hydrated,
            'pending_save': self.pending_save,
            'save_scheduled': self.save_scheduled,
            'last_save_time': self.last_save_time,
            'schedule_time': st.session_state.get(SAVE_SCHEDULE_KEY, 0),
            'hydration_success': st.session_state.get(f"{HYDRATION_SESSION_KEY}_success", False),
            'hydration_attempted': st.session_state.get(f"{HYDRATION_SESSION_KEY}_attempted", False),
            'persistence_enabled': is_persistence_enabled()
        }

    def check_storage_quota(self) -> Tuple[StorageStatus, Dict[str, Any]]:
        """
        Check storage quota status and return detailed information.

        Returns:
            Tuple of (StorageStatus, quota_info_dict)
        """
        if not is_persistence_enabled():
            return StorageStatus.DISABLED, {'reason': 'persistence_disabled'}

        try:
            # Check if we should perform quota check (throttled)
            current_time = time.time()
            last_check = st.session_state.get(LAST_QUOTA_CHECK_KEY, 0)

            if current_time - last_check < QUOTA_CHECK_INTERVAL_SECONDS:
                # Use cached result if available
                cached_status = st.session_state.get('_cached_storage_status')
                cached_info = st.session_state.get('_cached_quota_info', {})
                if cached_status:
                    return StorageStatus(cached_status), cached_info

            # Perform actual quota check
            quota_info = self._detect_storage_quota()
            st.session_state[LAST_QUOTA_CHECK_KEY] = current_time

            # Determine status based on usage
            if quota_info.get('quota_exceeded', False):
                status = StorageStatus.EXCEEDED
            elif quota_info.get('usage_ratio', 0) >= STORAGE_QUOTA_CRITICAL_THRESHOLD:
                status = StorageStatus.CRITICAL
            elif quota_info.get('usage_ratio', 0) >= STORAGE_QUOTA_WARNING_THRESHOLD:
                status = StorageStatus.WARNING
            else:
                status = StorageStatus.AVAILABLE

            # Cache result
            st.session_state['_cached_storage_status'] = status.value
            st.session_state['_cached_quota_info'] = quota_info

            return status, quota_info

        except Exception as e:
            logging.error(f"Failed to check storage quota: {e}")
            return StorageStatus.AVAILABLE, {'error': str(e)}

    def _detect_storage_quota(self) -> Dict[str, Any]:
        """Detect localStorage quota using various methods."""
        quota_info = {
            'quota_available': False,
            'quota_bytes': 0,
            'used_bytes': 0,
            'usage_ratio': 0.0,
            'quota_exceeded': False,
            'detection_method': 'unknown'
        }

        try:
            # Method 1: Try to use Storage API if available
            storage_estimate = self._get_storage_estimate()
            if storage_estimate:
                quota_info.update(storage_estimate)
                quota_info['detection_method'] = 'storage_api'
                return quota_info

            # Method 2: Estimate based on current data size
            current_data = self._get_from_localstorage()
            if current_data:
                current_size = len(json.dumps(current_data, ensure_ascii=False).encode('utf-8'))
                quota_info['used_bytes'] = current_size
                quota_info['detection_method'] = 'data_estimation'

                # Assume 5MB localStorage limit (common default)
                estimated_quota = 5 * 1024 * 1024
                quota_info['quota_bytes'] = estimated_quota
                quota_info['quota_available'] = True
                quota_info['usage_ratio'] = current_size / estimated_quota
                quota_info['quota_exceeded'] = current_size > estimated_quota

            # Method 3: Test write to detect quota
            test_result = self._test_storage_capacity()
            if test_result:
                quota_info.update(test_result)
                quota_info['detection_method'] = 'write_test'

        except Exception as e:
            logging.error(f"Storage quota detection failed: {e}")
            quota_info['error'] = str(e)

        return quota_info

    def clear_storage(self) -> bool:
        """Clear localStorage data."""
        try:
            self._clear_localstorage()
            logging.info("localStorage cleared")
            return True
        except Exception as e:
            logging.error(f"Failed to clear localStorage: {e}")
            return False

    def _get_from_localstorage(self) -> Optional[Dict[str, Any]]:
        """Get data from localStorage using JavaScript with session state bridge."""
        if not get_feature_flag('browser_storage_js', True):
            return None

        # Use session state as a bridge for localStorage data
        storage_state_key = f"_localStorage_{STORAGE_KEY}"

        # Check if we already have the data in session state
        if storage_state_key in st.session_state:
            return st.session_state[storage_state_key]

        # JavaScript code to get data from localStorage and store in session state
        js_code = f"""
        <script>
        function getStorageData() {{
            try {{
                const data = localStorage.getItem('{STORAGE_KEY}');
                if (data) {{
                    const parsed = JSON.parse(data);
                    // Store in a hidden input that Streamlit can read
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.id = 'localStorage_data';
                    hiddenInput.value = data;
                    document.body.appendChild(hiddenInput);

                    // Also try to communicate via window name (fallback method)
                    window.name = 'localStorage_data:' + data;

                    console.log('localStorage data retrieved and stored');
                }} else {{
                    console.log('No localStorage data found');
                    const hiddenInput = document.createElement('input');
                    hiddenInput.type = 'hidden';
                    hiddenInput.id = 'localStorage_data';
                    hiddenInput.value = '';
                    document.body.appendChild(hiddenInput);
                }}
            }} catch (error) {{
                console.error('Failed to get localStorage data:', error);
            }}
        }}

        // Execute immediately
        getStorageData();
        </script>
        """

        # Render the JavaScript
        components.html(js_code, height_cm=0, key=f"get_storage_{int(time.time() * 1000)}")

        # Try to get data from session state (may have been set by previous runs)
        return st.session_state.get(storage_state_key, None)
    
    def _save_to_localstorage(self, data: Dict[str, Any]) -> bool:
        """
        Save data to localStorage using JavaScript.

        Returns:
            True if save was successful, False otherwise
        """
        if not get_feature_flag('browser_storage_js', True):
            return False

        try:
            # Convert data to JSON string
            json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

            # Check size before saving
            data_size = len(json_data.encode('utf-8'))
            if data_size > 1024 * 1024:  # 1MB limit
                logging.warning(f"Data size {data_size} bytes exceeds 1MB limit")
                return False

            # Escape for JavaScript
            escaped_data = json_data.replace('\\', '\\\\').replace("'", "\\'")

            # JavaScript code to save data to localStorage
            js_code = f"""
            <script>
            function saveStorageData() {{
                try {{
                    const data = '{escaped_data}';
                    localStorage.setItem('{STORAGE_KEY}', data);
                    console.log('Data saved to localStorage, size:', data.length);

                    // Notify Streamlit of success
                    window.parent.postMessage({{
                        type: 'storage_saved',
                        success: true,
                        size: data.length
                    }}, '*');
                    return true;
                }} catch (error) {{
                    console.error('Failed to save to localStorage:', error);
                    window.parent.postMessage({{
                        type: 'storage_error',
                        error: error.message
                    }}, '*');
                    return false;
                }}
            }}

            // Execute immediately
            saveStorageData();
            </script>
            """

            # Execute JavaScript
            components.html(js_code, height_cm=0, width_cm=0)

            # Store success in session state for verification
            st.session_state[f"_localStorage_save_success_{int(time.time())}"] = True

            return True

        except Exception as e:
            logging.error(f"Failed to prepare localStorage save: {e}")
            return False
        
        # Render the JavaScript
        components.html(js_code, height_cm=0, key=f"save_{int(time.time() * 1000)}")
    
    def _clear_localstorage(self) -> None:
        """Clear localStorage using JavaScript."""
        js_code = f"""
        <script>
        function clearStorageData() {{
            try {{
                localStorage.removeItem('{STORAGE_KEY}');
                console.log('localStorage cleared');
                
                window.parent.postMessage({{
                    type: 'storage_cleared',
                    success: true
                }}, '*');
            }} catch (error) {{
                console.error('Failed to clear localStorage:', error);
                window.parent.postMessage({{
                    type: 'storage_error',
                    error: error.message
                }}, '*');
            }}
        }}
        
        clearStorageData();
        </script>
        """
        
        components.html(js_code, height_cm=0, key=f"clear_{int(time.time() * 1000)}")

    def _get_storage_estimate(self) -> Optional[Dict[str, Any]]:
        """Get storage estimate using Storage API if available."""
        if not get_feature_flag('browser_storage_js', True):
            return None

        try:
            # Use session state to bridge JavaScript results
            estimate_key = f"_storage_estimate_{int(time.time())}"

            js_code = f"""
            <script>
            async function getStorageEstimate() {{
                try {{
                    if ('storage' in navigator && 'estimate' in navigator.storage) {{
                        const estimate = await navigator.storage.estimate();
                        window.parent.postMessage({{
                            type: 'storage_estimate',
                            quota: estimate.quota || 0,
                            usage: estimate.usage || 0,
                            key: '{estimate_key}'
                        }}, '*');
                    }} else {{
                        window.parent.postMessage({{
                            type: 'storage_estimate_unavailable',
                            key: '{estimate_key}'
                        }}, '*');
                    }}
                }} catch (error) {{
                    console.error('Storage estimate failed:', error);
                    window.parent.postMessage({{
                        type: 'storage_estimate_error',
                        error: error.message,
                        key: '{estimate_key}'
                    }}, '*');
                }}
            }}
            getStorageEstimate();
            </script>
            """

            components.html(js_code, height_cm=0, width_cm=0)

            # Check if result is available in session state
            if estimate_key in st.session_state:
                result = st.session_state[estimate_key]
                del st.session_state[estimate_key]

                if result.get('quota') and result.get('usage') is not None:
                    return {
                        'quota_available': True,
                        'quota_bytes': result['quota'],
                        'used_bytes': result['usage'],
                        'usage_ratio': result['usage'] / result['quota'] if result['quota'] > 0 else 0,
                        'quota_exceeded': result['usage'] > result['quota']
                    }

        except Exception as e:
            logging.error(f"Storage estimate failed: {e}")

        return None

    def _test_storage_capacity(self) -> Optional[Dict[str, Any]]:
        """Test storage capacity by attempting to write test data."""
        try:
            # Generate test data of known size
            test_data_size = 1024  # 1KB test
            test_data = "x" * test_data_size
            test_key = f"{STORAGE_KEY}_capacity_test"

            js_code = f"""
            <script>
            try {{
                const testData = '{test_data}';
                localStorage.setItem('{test_key}', testData);
                localStorage.removeItem('{test_key}');

                // Test succeeded - storage has at least this much space
                window.parent.postMessage({{
                    type: 'capacity_test_success',
                    test_size: {test_data_size}
                }}, '*');
            }} catch (error) {{
                window.parent.postMessage({{
                    type: 'capacity_test_failed',
                    error: error.message
                }}, '*');
            }}
            </script>
            """

            components.html(js_code, height_cm=0, width_cm=0)

            # For now, return basic info since we can't easily get the result
            return {
                'quota_available': False,
                'test_performed': True,
                'test_size': test_data_size
            }

        except Exception as e:
            logging.error(f"Storage capacity test failed: {e}")
            return None


# Global storage manager instance
_storage_manager: Optional[BrowserStorageManager] = None


def get_storage_manager() -> BrowserStorageManager:
    """Get or create the global storage manager."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = BrowserStorageManager()
    return _storage_manager


def hydrate_once() -> bool:
    """
    Hydrate session state from localStorage once per session.
    
    Returns:
        True if hydration occurred and rerun is needed, False otherwise
    """
    return get_storage_manager().hydrate_once()


def schedule_save() -> None:
    """Schedule a debounced save to localStorage."""
    get_storage_manager().schedule_save()


def flush_if_due() -> bool:
    """
    Flush pending save if debounce period has elapsed.
    
    Returns:
        True if save was performed, False otherwise
    """
    return get_storage_manager().flush_if_due()


def force_save() -> bool:
    """Force immediate save to localStorage."""
    return get_storage_manager().force_save()


def clear_storage() -> bool:
    """Clear localStorage data."""
    return get_storage_manager().clear_storage()


def get_storage_info() -> Dict[str, Any]:
    """Get storage information and statistics."""
    return get_storage_manager().get_storage_info()


def render_storage_debug_panel() -> None:
    """Render debug panel for storage management."""
    if not get_feature_flag('storage_debug_panel', False):
        return
    
    st.subheader("🔧 存储调试面板")
    
    manager = get_storage_manager()
    info = get_storage_info()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("持久化状态", "启用" if is_persistence_enabled() else "禁用")
        st.metric("已水合", "是" if manager.hydrated else "否")
        st.metric("待保存", "是" if manager.pending_save else "否")
    
    with col2:
        if info.get('has_data'):
            st.metric("数据版本", info.get('version', 'N/A'))
            st.metric("卡片数量", info.get('card_count', 0))
            st.metric("导出记录", info.get('export_count', 0))
        else:
            st.metric("存储状态", "无数据")
    
    with col3:
        if info.get('has_data'):
            size_kb = info.get('size_bytes', 0) / 1024
            st.metric("数据大小", f"{size_kb:.1f} KB")
            
            if info.get('last_modified'):
                try:
                    last_mod = datetime.fromisoformat(info['last_modified'].replace('Z', '+00:00'))
                    st.metric("最后修改", last_mod.strftime('%H:%M:%S'))
                except:
                    st.metric("最后修改", "未知")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 立即保存"):
            if force_save():
                st.success("保存成功")
            else:
                st.error("保存失败")
    
    with col2:
        if st.button("🔄 立即水合"):
            if manager.hydrate_once():
                st.success("水合成功")
                st.rerun()
            else:
                st.info("无需水合")
    
    with col3:
        if st.button("🗑️ 清空存储"):
            if clear_storage():
                st.success("存储已清空")
            else:
                st.error("清空失败")


def use_browser_storage() -> bool:
    """Check if browser storage should be used."""
    return get_feature_flag('browser_storage', False)
