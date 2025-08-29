"""
Unified Preview Pipeline Controller for the UI refactor.
Centralizes preview rendering logic with digest-driven invalidation.
"""

from typing import List, Dict, Any, Tuple, Optional
import streamlit as st

from core.config import AppConfig
from core.feature_flags import use_new_preview_pipeline, use_cache_v2
from ui.state import (
    compute_preview_params_digest, get_session_generation,
    compute_layout_digest, compute_style_digest
)
from services.preview_types import PreviewParams, convert_app_config_to_preview_params
from services.layout import paginate, PaginateInfo
from ui.error_boundaries import with_error_boundary


class PreviewController:
    """Centralized controller for preview rendering pipeline."""
    
    def __init__(self):
        self.last_digest: Optional[str] = None
        self.last_params: Optional[PreviewParams] = None
    
    def render_preview_content_v2(self, processed_cards: List[Dict[str, str]], 
                                 config: AppConfig) -> Tuple[int, int]:
        """
        Unified preview content rendering with digest-driven invalidation.
        
        Args:
            processed_cards: List of card dictionaries
            config: Application configuration
            
        Returns:
            Tuple[int, int]: (cards_per_page, total_pages)
        """
        if not use_new_preview_pipeline():
            # Fallback to legacy implementation
            return self._render_legacy(processed_cards, config)
        
        # Convert AppConfig to PreviewParams at boundary
        preview_params = convert_app_config_to_preview_params(config)
        
        # Compute digest for change detection
        current_digest = self._compute_preview_digest(processed_cards, preview_params)
        
        # Check if we need to invalidate
        digest_changed = self._check_digest_changed(current_digest)
        
        # Calculate pagination
        pagination = paginate(len(processed_cards), 
                            preview_params.layout.rows, 
                            preview_params.layout.cols)
        
        # Clamp navigation index
        self._clamp_nav_index(pagination.total_pages)
        
        # Render based on digest change
        if digest_changed:
            self._render_immediate(processed_cards, preview_params, pagination)
        else:
            self._render_cached(processed_cards, preview_params, pagination)
        
        # Update state
        self.last_digest = current_digest
        self.last_params = preview_params
        
        return pagination.cards_per_page, pagination.total_pages
    
    def _compute_preview_digest(self, processed_cards: List[Dict[str, str]], 
                               params: PreviewParams) -> str:
        """Compute digest for preview parameters and cards."""
        cards_count = len(processed_cards)
        
        # Use existing digest computation from ui/state
        return compute_preview_params_digest(cards_count)
    
    def _check_digest_changed(self, current_digest: str) -> bool:
        """Check if digest has changed since last render."""
        if self.last_digest is None:
            return True
        return self.last_digest != current_digest
    
    def _clamp_nav_index(self, total_pages: int) -> None:
        """Clamp navigation index to valid range."""
        current_page = getattr(st.session_state, 'current_page', 0)
        if current_page >= total_pages:
            st.session_state.current_page = max(0, total_pages - 1)
    
    def _render_immediate(self, processed_cards: List[Dict[str, str]], 
                         params: PreviewParams, pagination: PaginateInfo) -> None:
        """Render preview immediately (no cache)."""
        self._render_preview_ui(processed_cards, params, pagination, use_cache=False)
    
    def _render_cached(self, processed_cards: List[Dict[str, str]], 
                      params: PreviewParams, pagination: PaginateInfo) -> None:
        """Render preview using cache."""
        self._render_preview_ui(processed_cards, params, pagination, use_cache=True)
    
    def _render_preview_ui(self, processed_cards: List[Dict[str, str]], 
                          params: PreviewParams, pagination: PaginateInfo,
                          use_cache: bool = True) -> None:
        """Render the preview UI components."""
        # Import here to avoid circular imports
        from ui.components import render_page_navigation, render_page_info
        
        # Render navigation
        render_page_navigation(pagination.total_pages)
        
        # Render preview content
        if processed_cards:
            self._render_preview_section_v2(processed_cards, params, pagination, use_cache)
        else:
            self._render_empty_preview()
        
        # Render page info
        render_page_info(processed_cards, pagination.cards_per_page, pagination.total_pages)
    
    def _render_preview_section_v2(self, processed_cards: List[Dict[str, str]], 
                                  params: PreviewParams, pagination: PaginateInfo,
                                  use_cache: bool) -> None:
        """Render the preview section with v2 pipeline."""
        current_page = getattr(st.session_state, 'current_page', 0)
        
        if params.visual.preview_mode == '📄 完整页面':
            # Full page preview
            html = self._create_page_preview_html_v2(
                processed_cards, current_page, params, use_cache
            )
            st.components.v1.html(html, height=850)
        else:
            # Simple grid preview
            start_idx = current_page * pagination.cards_per_page
            end_idx = min(start_idx + pagination.cards_per_page, len(processed_cards))
            current_page_cards = processed_cards[start_idx:end_idx]
            
            html = self._create_simple_grid_html_v2(
                current_page_cards, params, use_cache
            )
            st.components.v1.html(html, height=650)
    
    def _create_page_preview_html_v2(self, processed_cards: List[Dict[str, str]], 
                                    page_num: int, params: PreviewParams,
                                    use_cache: bool) -> str:
        """Create page preview HTML with v2 pipeline."""
        if use_cache and use_cache_v2():
            from services.cache_v2 import cached_preview_render
            return cached_preview_render(
                self._create_page_preview_html_immediate,
                processed_cards, page_num, params
            )
        else:
            return self._create_page_preview_html_immediate(
                processed_cards, page_num, params
            )
    
    def _create_simple_grid_html_v2(self, processed_cards: List[Dict[str, str]], 
                                   params: PreviewParams, use_cache: bool) -> str:
        """Create simple grid HTML with v2 pipeline."""
        if use_cache and use_cache_v2():
            from services.cache_v2 import cached_preview_render
            return cached_preview_render(
                self._create_simple_grid_html_immediate,
                processed_cards, params
            )
        else:
            return self._create_simple_grid_html_immediate(processed_cards, params)
    
    def _create_page_preview_html_immediate(self, processed_cards: List[Dict[str, str]], 
                                          page_num: int, params: PreviewParams) -> str:
        """Create page preview HTML immediately."""
        # Import legacy function and convert parameters
        from services.cache import create_page_preview_html
        from services.preview_types import extract_legacy_params
        
        legacy_params = extract_legacy_params(params)
        
        return create_page_preview_html(
            processed_cards, page_num,
            legacy_params['card_size'], legacy_params['gap'], legacy_params['margin'],
            legacy_params['font_hanzi'], legacy_params['font_pinyin'], legacy_params['font_english'],
            legacy_params['page_size'], legacy_params['hanzi_font'], legacy_params['background_color'],
            legacy_params['rows'], legacy_params['cols'], legacy_params['auto_fill']
        )
    
    def _create_simple_grid_html_immediate(self, processed_cards: List[Dict[str, str]], 
                                         params: PreviewParams) -> str:
        """Create simple grid HTML immediately."""
        # Import legacy function and convert parameters
        from services.cache import create_simple_grid_html
        from services.preview_types import extract_legacy_params
        
        legacy_params = extract_legacy_params(params)
        
        return create_simple_grid_html(
            processed_cards, legacy_params['hanzi_font'], legacy_params['background_color'],
            legacy_params['rows'], legacy_params['cols'],
            legacy_params['font_hanzi'], legacy_params['font_pinyin'], legacy_params['font_english'],
            legacy_params['card_size'], legacy_params['auto_fill']
        )
    
    def _render_empty_preview(self) -> None:
        """Render preview for empty cards case."""
        try:
            from services.cache import create_preview_html
            st.components.v1.html(create_preview_html([]), height=650)
        except Exception as e:
            st.error(f"预览渲染错误: {e}")
    
    def _render_legacy(self, processed_cards: List[Dict[str, str]], 
                      config: AppConfig) -> Tuple[int, int]:
        """Fallback to legacy preview rendering."""
        from ui.sections import render_preview_content_legacy
        from services.preview_types import extract_legacy_params
        
        # Convert config to legacy format
        preview_params = convert_app_config_to_preview_params(config)
        legacy_params = extract_legacy_params(preview_params)
        
        # Split into preview and layout params for legacy function
        preview_dict = {
            'hanzi_font': legacy_params['hanzi_font'],
            'background_color': legacy_params['background_color'],
            'preview_mode': legacy_params['preview_mode']
        }
        
        layout_dict = {k: v for k, v in legacy_params.items() 
                      if k not in preview_dict}
        
        return render_preview_content_legacy(processed_cards, preview_dict, layout_dict)


# Global controller instance
_preview_controller: Optional[PreviewController] = None


def get_preview_controller() -> PreviewController:
    """Get or create the global preview controller."""
    global _preview_controller
    if _preview_controller is None:
        _preview_controller = PreviewController()
    return _preview_controller


@with_error_boundary("preview_controller")
def render_preview_content_unified(processed_cards: List[Dict[str, str]], 
                                  config: AppConfig) -> Tuple[int, int]:
    """
    Unified entry point for preview content rendering.
    
    This function serves as the main interface for preview rendering,
    automatically choosing between v2 pipeline and legacy based on feature flags.
    """
    controller = get_preview_controller()
    return controller.render_preview_content_v2(processed_cards, config)
