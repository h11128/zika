"""
State digest computation for change detection.

Provides efficient state change detection through digest computation.
"""

import hashlib
import json
from typing import Any, Dict, Set, Optional
from dataclasses import dataclass

from .ports import StateDigestPort


@dataclass
class DigestConfig:
    """Configuration for digest computation."""
    include_keys: Optional[Set[str]] = None  # If None, include all
    exclude_keys: Optional[Set[str]] = None  # Keys to exclude
    sort_keys: bool = True  # Sort keys for consistent hashing
    algorithm: str = "sha256"  # Hash algorithm


class StateDigest(StateDigestPort):
    """State digest computation implementation."""
    
    def __init__(self, config: DigestConfig = None):
        self.config = config or DigestConfig()
        self._last_digest: Optional[str] = None
        self._last_state: Optional[Dict[str, Any]] = None
    
    def compute_digest(self, state: Dict[str, Any]) -> str:
        """Compute state digest."""
        # Filter state based on config
        filtered_state = self._filter_state(state)
        
        # Convert to JSON string for hashing
        try:
            state_json = json.dumps(
                filtered_state,
                sort_keys=self.config.sort_keys,
                default=self._json_serializer
            )
        except (TypeError, ValueError) as e:
            # Fallback to string representation
            state_json = str(filtered_state)
        
        # Compute hash
        hasher = hashlib.new(self.config.algorithm)
        hasher.update(state_json.encode('utf-8'))
        digest = hasher.hexdigest()
        
        # Cache for comparison
        self._last_digest = digest
        self._last_state = filtered_state.copy()
        
        return digest
    
    def has_changed(self, old_digest: str, new_digest: str) -> bool:
        """Check if state has changed."""
        return old_digest != new_digest
    
    def compute_incremental_digest(self, state: Dict[str, Any]) -> str:
        """Compute digest with incremental optimization."""
        # If we have a cached state, check for changes first
        if self._last_state is not None:
            filtered_state = self._filter_state(state)
            
            # Quick check: if states are identical, return cached digest
            if filtered_state == self._last_state:
                return self._last_digest
        
        # Compute full digest
        return self.compute_digest(state)
    
    def get_changed_keys(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Set[str]:
        """Get keys that changed between states."""
        old_filtered = self._filter_state(old_state)
        new_filtered = self._filter_state(new_state)
        
        changed_keys = set()
        
        # Check for changed values
        all_keys = set(old_filtered.keys()) | set(new_filtered.keys())
        for key in all_keys:
            old_value = old_filtered.get(key)
            new_value = new_filtered.get(key)
            
            if old_value != new_value:
                changed_keys.add(key)
        
        return changed_keys
    
    def _filter_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Filter state based on configuration."""
        filtered = {}
        
        for key, value in state.items():
            # Skip excluded keys
            if self.config.exclude_keys and key in self.config.exclude_keys:
                continue
            
            # Include only specified keys (if configured)
            if self.config.include_keys and key not in self.config.include_keys:
                continue
            
            # Skip private keys (starting with _)
            if key.startswith('_'):
                continue
            
            filtered[key] = value
        
        return filtered
    
    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-serializable objects."""
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, '_asdict'):  # namedtuple
            return obj._asdict()
        else:
            return str(obj)


# Global digest instance
_state_digest: StateDigest = None


def get_state_digest() -> StateDigest:
    """Get the global state digest."""
    global _state_digest
    
    if _state_digest is None:
        _state_digest = StateDigest()
    
    return _state_digest


def compute_state_digest(state: Dict[str, Any]) -> str:
    """Compute state digest using global instance."""
    digest = get_state_digest()
    return digest.compute_digest(state)


def create_preview_digest_config() -> DigestConfig:
    """Create digest config for preview-related state."""
    return DigestConfig(
        include_keys={
            'card_size_cm', 'gap_cm', 'margin_cm',
            'hanzi_font_size', 'pinyin_font_size', 'english_font_size',
            'page_size', 'hanzi_font_family', 'background_color',
            'layout_rows', 'layout_cols', 'layout_auto_fill', 'preview_mode',
            'processed_cards'
        },
        exclude_keys={'_preview_cache', '_export_cache'},
        sort_keys=True
    )


def create_export_digest_config() -> DigestConfig:
    """Create digest config for export-related state."""
    return DigestConfig(
        include_keys={
            'card_size_cm', 'gap_cm', 'margin_cm',
            'hanzi_font_size', 'pinyin_font_size', 'english_font_size',
            'page_size', 'hanzi_font_family', 'background_color',
            'layout_rows', 'layout_cols', 'layout_auto_fill',
            'processed_cards'
        },
        exclude_keys={'_preview_cache', '_export_cache'},
        sort_keys=True
    )
