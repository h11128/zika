"""
Monitoring Dashboard for System Observability.

This module provides a UI dashboard to display system health,
performance metrics, and observability data.
"""

from typing import Dict, Any, List
from ui.unified import get_unified_ui
from ui.error_boundary import with_error_boundary


@with_error_boundary("monitoring_dashboard")
def render_monitoring_dashboard() -> None:
    """Render the system monitoring dashboard."""
    ui = get_unified_ui()
    
    ui.header("🔍 系统监控仪表板")
    
    try:
        from services.observability import get_metrics_summary
        metrics = get_metrics_summary()
        
        # Health Status
        render_health_status(ui, metrics)
        
        # Performance Metrics
        render_performance_metrics(ui, metrics)
        
        # Cache Statistics
        render_cache_statistics(ui, metrics)
        
        # Error Tracking
        render_error_tracking(ui, metrics)
        
        # System Information
        render_system_information(ui, metrics)
        
    except ImportError:
        ui.warning("监控系统不可用")
    except Exception as e:
        ui.error(f"监控仪表板错误: {e}")


def render_health_status(ui, metrics: Dict[str, Any]) -> None:
    """Render overall health status."""
    ui.subheader("🏥 系统健康状态")
    
    health_status = metrics.get('health_status', 'unknown')
    uptime = metrics.get('uptime_seconds', 0)
    
    # Health status indicator
    if health_status == 'healthy':
        ui.success(f"✅ 系统健康 (运行时间: {uptime:.1f}秒)")
    elif health_status == 'warning':
        ui.warning(f"⚠️ 系统警告 (运行时间: {uptime:.1f}秒)")
    else:
        ui.error(f"❌ 系统异常 (运行时间: {uptime:.1f}秒)")
    
    # Key metrics in columns
    col1, col2, col3, col4 = ui.columns(4)
    
    perf = metrics.get('performance', {})
    
    with col1:
        ui.metric(
            "平均渲染时间",
            f"{perf.get('avg_render_time_ms', 0):.1f}ms",
            delta=f"目标: <500ms"
        )
    
    with col2:
        ui.metric(
            "缓存命中率",
            f"{perf.get('cache_hit_rate_percent', 0):.1f}%",
            delta=f"目标: >80%"
        )
    
    with col3:
        ui.metric(
            "适配器使用率",
            f"{perf.get('adapter_usage_rate_percent', 0):.1f}%",
            delta=f"目标: >95%"
        )
    
    with col4:
        ui.metric(
            "错误率",
            f"{perf.get('error_rate_per_hour', 0):.2f}/小时",
            delta=f"目标: <1/小时"
        )


def render_performance_metrics(ui, metrics: Dict[str, Any]) -> None:
    """Render performance metrics."""
    ui.subheader("⚡ 性能指标")
    
    perf = metrics.get('performance', {})
    
    # Performance summary
    col1, col2 = ui.columns(2)
    
    with col1:
        ui.write("**渲染性能**")
        ui.write(f"• 平均渲染时间: {perf.get('avg_render_time_ms', 0):.1f}ms")
        ui.write(f"• 最大渲染时间: {perf.get('max_render_time_ms', 0):.1f}ms")
        ui.write(f"• 最小渲染时间: {perf.get('min_render_time_ms', 0):.1f}ms")
        
        # Performance status
        avg_render = perf.get('avg_render_time_ms', 0)
        if avg_render < 100:
            ui.success("🚀 渲染性能优秀")
        elif avg_render < 500:
            ui.info("✅ 渲染性能良好")
        else:
            ui.warning("⚠️ 渲染性能需要优化")
    
    with col2:
        ui.write("**内存使用**")
        memory_mb = perf.get('memory_usage_mb', 0)
        ui.write(f"• 当前内存使用: {memory_mb:.1f}MB")
        
        if memory_mb < 50:
            ui.success("💚 内存使用正常")
        elif memory_mb < 100:
            ui.info("💛 内存使用适中")
        else:
            ui.warning("🔴 内存使用偏高")


def render_cache_statistics(ui, metrics: Dict[str, Any]) -> None:
    """Render cache statistics."""
    ui.subheader("💾 缓存统计")
    
    counters = metrics.get('counters', {})
    perf = metrics.get('performance', {})
    
    col1, col2, col3 = ui.columns(3)
    
    with col1:
        cache_hits = counters.get('cache_hits', 0)
        ui.metric("缓存命中", str(cache_hits))
    
    with col2:
        cache_misses = counters.get('cache_misses', 0)
        ui.metric("缓存未命中", str(cache_misses))
    
    with col3:
        hit_rate = perf.get('cache_hit_rate_percent', 0)
        ui.metric("命中率", f"{hit_rate:.1f}%")
    
    # Cache performance analysis
    total_cache_ops = cache_hits + cache_misses
    if total_cache_ops > 0:
        if hit_rate >= 80:
            ui.success("🎯 缓存性能优秀")
        elif hit_rate >= 60:
            ui.info("📊 缓存性能良好")
        else:
            ui.warning("📉 缓存性能需要改进")
    else:
        ui.info("📊 暂无缓存操作数据")


def render_error_tracking(ui, metrics: Dict[str, Any]) -> None:
    """Render error tracking information."""
    ui.subheader("🚨 错误跟踪")
    
    counters = metrics.get('counters', {})
    perf = metrics.get('performance', {})
    
    error_count = counters.get('errors', 0)
    error_rate = perf.get('error_rate_per_hour', 0)
    
    col1, col2 = ui.columns(2)
    
    with col1:
        ui.metric("总错误数", str(error_count))
    
    with col2:
        ui.metric("错误率", f"{error_rate:.2f}/小时")
    
    # Error status
    if error_count == 0:
        ui.success("✅ 无错误记录")
    elif error_rate < 1:
        ui.info("ℹ️ 错误率在可接受范围内")
    else:
        ui.warning("⚠️ 错误率偏高，需要关注")


def render_system_information(ui, metrics: Dict[str, Any]) -> None:
    """Render system information."""
    ui.subheader("ℹ️ 系统信息")
    
    counters = metrics.get('counters', {})
    
    col1, col2 = ui.columns(2)
    
    with col1:
        ui.write("**适配器使用情况**")
        adapter_calls = counters.get('adapter_calls', 0)
        direct_calls = counters.get('direct_calls', 0)
        total_calls = adapter_calls + direct_calls
        
        ui.write(f"• 适配器调用: {adapter_calls}")
        ui.write(f"• 直接调用: {direct_calls}")
        ui.write(f"• 总调用数: {total_calls}")
        
        if direct_calls == 0:
            ui.success("🎯 完全使用适配器")
        elif direct_calls < adapter_calls * 0.05:  # < 5%
            ui.info("✅ 适配器使用率良好")
        else:
            ui.warning("⚠️ 存在较多直接调用")
    
    with col2:
        ui.write("**事件统计**")
        total_events = metrics.get('total_events', 0)
        recent_events = metrics.get('recent_events', 0)
        
        ui.write(f"• 总事件数: {total_events}")
        ui.write(f"• 近5分钟事件: {recent_events}")
        
        if recent_events > 0:
            ui.info("📊 系统活跃")
        else:
            ui.info("😴 系统空闲")


def render_monitoring_sidebar() -> None:
    """Render monitoring information in sidebar."""
    try:
        from services.observability import get_metrics_summary
        metrics = get_metrics_summary()
        
        ui = get_unified_ui()
        
        with ui.sidebar:
            ui.subheader("📊 系统监控")
            
            # Quick health check
            health_status = metrics.get('health_status', 'unknown')
            if health_status == 'healthy':
                ui.success("✅ 系统健康")
            elif health_status == 'warning':
                ui.warning("⚠️ 系统警告")
            else:
                ui.error("❌ 系统异常")
            
            # Key metrics
            perf = metrics.get('performance', {})
            ui.metric("渲染时间", f"{perf.get('avg_render_time_ms', 0):.0f}ms")
            ui.metric("缓存命中率", f"{perf.get('cache_hit_rate_percent', 0):.0f}%")
            ui.metric("适配器使用率", f"{perf.get('adapter_usage_rate_percent', 0):.0f}%")
            
            # Link to full dashboard
            if ui.button("📊 查看详细监控"):
                ui.info("监控仪表板功能开发中...")
                
    except ImportError:
        pass  # Monitoring not available
    except Exception:
        pass  # Silently fail in sidebar


# Export main functions
__all__ = [
    'render_monitoring_dashboard',
    'render_monitoring_sidebar'
]
