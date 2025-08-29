"""
Browser storage bridge with localStorage integration.
Provides hydrate_once(), schedule_save(), and flush_if_due() functionality.
"""

import json
import time
import logging
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timezone
import streamlit as st
import streamlit.components.v1 as components

from core.feature_flags import get_feature_flag
from services.persistence import (
    UserSnapshot, create_snapshot_from_session, load_snapshot_from_data,
    is_persistence_enabled
)


# Storage configuration
STORAGE_KEY = "zika_user_snapshot"
SAVE_DEBOUNCE_SECONDS = 2.0  # Debounce saves for 2 seconds
HYDRATION_TIMEOUT_MS = 1000  # Timeout for hydration


class BrowserStorageManager:
    """Manages browser localStorage integration."""
    
    def __init__(self):
        self.last_save_time: float = 0
        self.pending_save: bool = False
        self.hydrated: bool = False
        self.save_scheduled: bool = False
    
    def hydrate_once(self) -> bool:
        """
        Hydrate session state from localStorage once per session.
        
        Returns:
            True if hydration occurred and rerun is needed, False otherwise
        """
        if not is_persistence_enabled():
            return False
        
        if self.hydrated:
            return False
        
        # Check if we've already hydrated this session
        if hasattr(st.session_state, '_storage_hydrated'):
            self.hydrated = True
            return False
        
        try:
            # Get data from localStorage
            stored_data = self._get_from_localstorage()
            
            if stored_data:
                snapshot = load_snapshot_from_data(stored_data)
                if snapshot:
                    # Apply to session state
                    snapshot.apply_to_session_state(st.session_state)
                    
                    # Mark as hydrated
                    st.session_state._storage_hydrated = True
                    self.hydrated = True
                    
                    logging.info("Session state hydrated from localStorage")
                    return True  # Rerun needed
            
            # Mark as hydrated even if no data found
            st.session_state._storage_hydrated = True
            self.hydrated = True
            
        except Exception as e:
            logging.error(f"Failed to hydrate from localStorage: {e}")
            st.session_state._storage_hydrated = True
            self.hydrated = True
        
        return False
    
    def schedule_save(self) -> None:
        """Schedule a debounced save to localStorage."""
        if not is_persistence_enabled():
            return
        
        self.pending_save = True
        self.save_scheduled = True
        
        # The actual save will happen in flush_if_due()
        logging.debug("Save scheduled")
    
    def flush_if_due(self) -> bool:
        """
        Flush pending save if debounce period has elapsed.
        
        Returns:
            True if save was performed, False otherwise
        """
        if not is_persistence_enabled():
            return False
        
        if not self.pending_save:
            return False
        
        current_time = time.time()
        
        # Check if debounce period has elapsed
        if current_time - self.last_save_time < SAVE_DEBOUNCE_SECONDS:
            return False
        
        try:
            # Create snapshot from current session state
            snapshot = create_snapshot_from_session(st.session_state)
            
            if snapshot:
                # Save to localStorage
                self._save_to_localstorage(snapshot.to_dict())
                
                self.last_save_time = current_time
                self.pending_save = False
                self.save_scheduled = False
                
                logging.debug("Session state saved to localStorage")
                return True
            
        except Exception as e:
            logging.error(f"Failed to save to localStorage: {e}")
        
        # Clear pending save even if failed
        self.pending_save = False
        self.save_scheduled = False
        return False
    
    def force_save(self) -> bool:
        """Force immediate save to localStorage."""
        if not is_persistence_enabled():
            return False
        
        try:
            snapshot = create_snapshot_from_session(st.session_state)
            
            if snapshot:
                self._save_to_localstorage(snapshot.to_dict())
                
                self.last_save_time = time.time()
                self.pending_save = False
                self.save_scheduled = False
                
                logging.info("Session state force saved to localStorage")
                return True
            
        except Exception as e:
            logging.error(f"Failed to force save to localStorage: {e}")
        
        return False
    
    def clear_storage(self) -> bool:
        """Clear localStorage data."""
        try:
            self._clear_localstorage()
            logging.info("localStorage cleared")
            return True
        except Exception as e:
            logging.error(f"Failed to clear localStorage: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information and statistics."""
        try:
            data = self._get_from_localstorage()
            
            if data:
                snapshot = load_snapshot_from_data(data)
                if snapshot:
                    return {
                        'has_data': True,
                        'version': snapshot.version,
                        'created_at': snapshot.created_at,
                        'last_modified': snapshot.last_modified,
                        'size_bytes': snapshot.estimate_size_bytes(),
                        'card_count': len(snapshot.cards),
                        'export_count': len(snapshot.export_history)
                    }
            
            return {'has_data': False}
            
        except Exception as e:
            logging.error(f"Failed to get storage info: {e}")
            return {'has_data': False, 'error': str(e)}
    
    def _get_from_localstorage(self) -> Optional[Dict[str, Any]]:
        """Get data from localStorage using JavaScript."""
        if not get_feature_flag('browser_storage_js', True):
            return None
        
        # JavaScript code to get data from localStorage
        js_code = f"""
        <script>
        function getStorageData() {{
            try {{
                const data = localStorage.getItem('{STORAGE_KEY}');
                if (data) {{
                    const parsed = JSON.parse(data);
                    // Send data to Streamlit
                    window.parent.postMessage({{
                        type: 'storage_data',
                        data: parsed
                    }}, '*');
                }} else {{
                    window.parent.postMessage({{
                        type: 'storage_data',
                        data: null
                    }}, '*');
                }}
            }} catch (error) {{
                console.error('Failed to get localStorage data:', error);
                window.parent.postMessage({{
                    type: 'storage_error',
                    error: error.message
                }}, '*');
            }}
        }}
        
        // Execute immediately
        getStorageData();
        </script>
        """
        
        # Use session state to store the result
        storage_key = f"_storage_result_{int(time.time() * 1000)}"
        
        # Render the JavaScript
        components.html(js_code, height=0, key=storage_key)
        
        # For now, return None as we can't easily get the result synchronously
        # In a real implementation, this would use a more sophisticated
        # communication mechanism
        return None
    
    def _save_to_localstorage(self, data: Dict[str, Any]) -> None:
        """Save data to localStorage using JavaScript."""
        if not get_feature_flag('browser_storage_js', True):
            return
        
        # Convert data to JSON string
        json_data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        
        # Escape for JavaScript
        escaped_data = json_data.replace('\\', '\\\\').replace("'", "\\'")
        
        # JavaScript code to save data to localStorage
        js_code = f"""
        <script>
        function saveStorageData() {{
            try {{
                const data = '{escaped_data}';
                localStorage.setItem('{STORAGE_KEY}', data);
                console.log('Data saved to localStorage');
                
                // Notify Streamlit of success
                window.parent.postMessage({{
                    type: 'storage_saved',
                    success: true
                }}, '*');
            }} catch (error) {{
                console.error('Failed to save to localStorage:', error);
                window.parent.postMessage({{
                    type: 'storage_error',
                    error: error.message
                }}, '*');
            }}
        }}
        
        // Execute immediately
        saveStorageData();
        </script>
        """
        
        # Render the JavaScript
        components.html(js_code, height=0, key=f"save_{int(time.time() * 1000)}")
    
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
        
        components.html(js_code, height=0, key=f"clear_{int(time.time() * 1000)}")


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
