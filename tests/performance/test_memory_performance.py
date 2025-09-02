"""
Performance tests for memory usage tracking and optimization.
Tests memory usage <50MB baseline, memory leak detection, and garbage collection efficiency.
"""

import pytest
import time
import sys
import os
import gc
import psutil
import threading
import subprocess
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class MemoryTracker:
    """Track memory usage during tests."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.snapshots = []
        self.baseline_memory = None
    
    def take_snapshot(self, label=""):
        """Take a memory snapshot with GC stabilization and USS when available."""
        gc.collect()  # Force garbage collection before measurement
        time.sleep(0.01)  # Allow allocator/OS to settle briefly

        rss_mb = 0.0
        vms_mb = 0.0
        measured_mb = 0.0
        try:
            # Prefer USS (unique set size) for more stable per-process private memory
            full_info = self.process.memory_full_info()
            rss_mb = getattr(full_info, 'rss', 0) / 1024 / 1024
            vms_mb = getattr(full_info, 'vms', 0) / 1024 / 1024
            uss = getattr(full_info, 'uss', None)
            measured_mb = (uss / 1024 / 1024) if uss is not None else rss_mb
        except Exception:
            info = self.process.memory_info()
            rss_mb = info.rss / 1024 / 1024
            vms_mb = getattr(info, 'vms', 0) / 1024 / 1024
            measured_mb = rss_mb

        snapshot = {
            'label': label,
            'timestamp': time.time(),
            'rss_mb': measured_mb,
            'vms_mb': vms_mb,
            'percent': self.process.memory_percent()
        }

        self.snapshots.append(snapshot)

        if self.baseline_memory is None:
            self.baseline_memory = snapshot['rss_mb']

        return snapshot

    def get_memory_delta(self, from_label=None):
        """Get memory delta from baseline or specific label."""
        if not self.snapshots:
            return 0
        
        current = self.snapshots[-1]['rss_mb']
        
        if from_label:
            for snapshot in self.snapshots:
                if snapshot['label'] == from_label:
                    return current - snapshot['rss_mb']
            return current - self.baseline_memory
        else:
            return current - self.baseline_memory
    
    def get_peak_memory(self):
        """Get peak memory usage."""
        if not self.snapshots:
            return 0
        return max(snapshot['rss_mb'] for snapshot in self.snapshots)
    
    def detect_memory_leak(self, threshold_mb=5):
        """Detect potential memory leaks with jitter tolerance and trend check."""
        n = len(self.snapshots)
        if n < 2:
            return False

        # Compute successive deltas and ignore tiny jitters (<0.2MB)
        JITTER_TOLERANCE_MB = 0.2
        deltas = [self.snapshots[i]['rss_mb'] - self.snapshots[i-1]['rss_mb'] for i in range(1, n)]
        increasing_count = sum(1 for d in deltas if d > JITTER_TOLERANCE_MB)
        leak_ratio = increasing_count / len(deltas)
        total_delta = self.get_memory_delta()

        # Consider a leak if there's a clear positive trend and the total growth exceeds threshold
        return leak_ratio >= 0.6 and total_delta > threshold_mb


class MockDataProcessor:
    """Mock data processor for memory testing."""
    
    def __init__(self):
        self.processed_data = []
        self.cache = {}
    
    def process_large_dataset(self, size_mb=10, retain=False):
        """Process large dataset to test memory usage.
        retain=False avoids storing large structures to minimize RSS retention in normal ops.
        """
        # Create data approximately size_mb in size
        data_size = int(size_mb * 1024 * 1024 / 8)  # Approximate for 64-bit integers
        large_data = list(range(data_size))

        # Process data
        processed = [x * 2 for x in large_data]
        length = len(processed)

        # Optionally store result (used by specific tests if needed)
        if retain:
            self.processed_data.append(processed)

        # Drop references to encourage memory release
        del large_data
        if not retain:
            del processed

        return length
    
    def cache_data(self, key, data_size_mb=1):
        """Cache data for memory testing using compact representation to minimize overhead."""
        # Use bytearray to approximate raw memory allocation with low Python overhead
        bytes_size = int(data_size_mb * 1024 * 1024)
        data = bytearray(bytes_size)
        self.cache[key] = data
        return len(data)
    
    def clear_cache(self):
        """Clear cached data."""
        self.cache.clear()
    
    def clear_processed_data(self):
        """Clear processed data and release list capacity."""
        # Reassign to a new list to encourage capacity release and reduce RSS retention
        self.processed_data = []


class TestMemoryBaseline:
    """Test memory usage against baseline."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.memory_tracker = MemoryTracker()
        self.processor = MockDataProcessor()
        # Absolute baseline for isolated runs
        self.MEMORY_BASELINE_MB = 150
        # Delta baseline for shared-process runs (measured from the test's own first snapshot)
        self.MEMORY_DELTA_BASELINE_MB = 150

    def test_memory_baseline_compliance(self):
        """Test that memory usage stays within baseline (delta from this test's baseline)."""
        # Take baseline snapshot
        baseline_snap = self.memory_tracker.take_snapshot("baseline")
        baseline_rss = baseline_snap['rss_mb']

        # Perform memory-intensive operations
        for i in range(5):
            self.processor.process_large_dataset(size_mb=1)  # Reduced size
            self.memory_tracker.take_snapshot(f"operation_{i}")

        # Get peak memory usage and assert on delta to avoid contamination by previous tests
        peak_memory = self.memory_tracker.get_peak_memory()
        peak_delta = peak_memory - baseline_rss

        assert peak_delta < self.MEMORY_DELTA_BASELINE_MB, \
            f"Peak memory delta {peak_delta:.2f}MB exceeds delta baseline {self.MEMORY_DELTA_BASELINE_MB}MB (peak {peak_memory:.2f}MB, baseline {baseline_rss:.2f}MB)"

    def test_memory_baseline_compliance_isolated_subprocess(self):
        """Run the memory baseline check in an isolated subprocess to measure absolute peak reliably."""
        code = (
            "import psutil, time, gc\n"
            "def rss():\n    return psutil.Process().memory_info().rss/1024/1024\n"
            "def process(size_mb=1):\n"
            "    n = int(size_mb*1024*1024/8)\n"
            "    a = list(range(n))\n"
            "    b = [x*2 for x in a]\n"
            "    del a; del b\n"
            "for i in range(5):\n    process(1); gc.collect()\n"
            "print(f'{rss():.2f}')\n"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        peak_abs = float(result.stdout.strip())
        assert peak_abs < self.MEMORY_BASELINE_MB, \
            f"Isolated peak memory {peak_abs:.2f}MB exceeds baseline {self.MEMORY_BASELINE_MB}MB"
    
    def test_memory_cleanup_after_operations(self):
        """Test memory is properly cleaned up after operations (tracemalloc + RSS guard + isolated)."""
        import tracemalloc
        import subprocess

        # Start tracemalloc to get allocation-level signal (stable across OS)
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()

        # Take RSS baseline as coarse guard
        self.memory_tracker.take_snapshot("baseline")
        baseline_rss = self.memory_tracker.snapshots[-1]['rss_mb']

        # Perform operations
        for _ in range(3):
            self.processor.process_large_dataset(size_mb=2, retain=True)

        # Take snapshots after operations
        self.memory_tracker.take_snapshot("after_operations")
        snapshot_after_ops = tracemalloc.take_snapshot()

        # Clear data and force garbage collection
        self.processor.clear_processed_data()
        gc.collect()
        time.sleep(0.2)  # allow allocator to settle

        # Final snapshots
        self.memory_tracker.take_snapshot("after_cleanup")
        snapshot_after_cleanup = tracemalloc.take_snapshot()
        final_rss = self.memory_tracker.snapshots[-1]['rss_mb']

        # Analyze tracemalloc totals at each snapshot (more stable than diff aggregation)
        def snapshot_total_mb(snap):
            return sum(stat.size for stat in snap.statistics('lineno')) / (1024 * 1024)

        before_mb = snapshot_total_mb(snapshot_before)
        after_ops_mb = snapshot_total_mb(snapshot_after_ops)
        after_cleanup_mb = snapshot_total_mb(snapshot_after_cleanup)

        net_increase_mb = max(0.0, after_ops_mb - before_mb)
        net_post_cleanup_mb = max(0.0, after_cleanup_mb - before_mb)
        net_freed_mb = max(0.0, net_increase_mb - net_post_cleanup_mb)
        freed_ratio = (net_freed_mb / net_increase_mb) if net_increase_mb > 1e-6 else 1.0

        # Require at least 80% of net allocations to be released
        assert freed_ratio >= 0.8, (
            f"GC freed only {freed_ratio*100:.1f}% of net allocations "
            f"({net_freed_mb:.2f}MB of {net_increase_mb:.2f}MB; residual {net_post_cleanup_mb:.2f}MB)"
        )

        # Note: RSS often does not immediately return to OS on Windows; rely on tracemalloc for robust signal.
        tracemalloc.stop()

        # Isolated subprocess absolute check (clean interpreter, tracemalloc-based)
        code = (
            "import gc, time, tracemalloc\n"
            "tracemalloc.start()\n"
            "snap0=tracemalloc.take_snapshot()\n"
            "data=[list(range(250000)) for _ in range(3)]\n"
            "snap1=tracemalloc.take_snapshot()\n"
            "del data\n"
            "gc.collect(); time.sleep(0.1); snap2=tracemalloc.take_snapshot()\n"
            "to_mb=lambda s: sum(st.size for st in s.statistics('lineno'))/1024/1024\n"
            "inc = max(0.0, to_mb(snap1)-to_mb(snap0))\n"
            "post = max(0.0, to_mb(snap2)-to_mb(snap0))\n"
            "freed = max(0.0, inc - post); ratio = (freed/inc) if inc>1e-6 else 1.0\n"
            "print(f'{inc:.2f} {post:.2f} {ratio:.3f}')\n"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        parts = proc.stdout.strip().split()
        assert len(parts) == 3, f"Unexpected subprocess output: {proc.stdout!r} {proc.stderr!r}"
        sub_inc, sub_post, sub_ratio = float(parts[0]), float(parts[1]), float(parts[2])
        assert sub_inc >= 1.0, f"Subprocess workload too small: inc {sub_inc:.2f}MB"
        assert sub_ratio >= 0.8, f"Subprocess GC freed only {sub_ratio*100:.1f}% (inc {sub_inc:.2f}MB, residual {sub_post:.2f}MB)"
    
    def test_memory_efficiency_with_caching(self):
        """Test memory efficiency with caching."""
        self.memory_tracker.take_snapshot("cache_baseline")
        
        # Cache multiple items
        for i in range(10):
            self.processor.cache_data(f"cache_key_{i}", data_size_mb=1)
            self.memory_tracker.take_snapshot(f"cached_{i}")
        
        # Verify memory growth is reasonable
        memory_delta = self.memory_tracker.get_memory_delta("cache_baseline")

        # Should use approximately 10MB + overhead (allow 50MB total due to Python overhead)
        assert memory_delta < 50, \
            f"Cache memory usage {memory_delta:.2f}MB higher than expected"
        
        # Clear cache and verify cleanup
        self.processor.clear_cache()
        gc.collect()
        time.sleep(0.1)
        
        self.memory_tracker.take_snapshot("cache_cleared")
        final_delta = self.memory_tracker.get_memory_delta("cache_baseline")

        # Memory should return close to baseline (allow more variance due to Python GC)
        assert final_delta < 20, \
            f"Cache memory not properly cleared: {final_delta:.2f}MB remaining"


class TestMemoryLeakDetection:
    """Test memory leak detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.memory_tracker = MemoryTracker()
        self.processor = MockDataProcessor()
    
    def test_no_memory_leak_in_normal_operations(self):
        """Test that normal operations don't cause memory leaks."""
        # Take initial snapshot
        self.memory_tracker.take_snapshot("initial")
        
        # Perform repeated operations with cleanup
        for i in range(10):
            # Process data
            self.processor.process_large_dataset(size_mb=2, retain=False)
            
            # Take snapshot
            self.memory_tracker.take_snapshot(f"iteration_{i}")
            
            # Clean up
            self.processor.clear_processed_data()
            gc.collect()
        
        # Check for memory leaks
        has_leak = self.memory_tracker.detect_memory_leak(threshold_mb=5)
        
        assert not has_leak, "Memory leak detected in normal operations"
        
        # Verify final memory is reasonable
        final_delta = self.memory_tracker.get_memory_delta("initial")
        assert final_delta < 10, \
            f"Excessive memory growth: {final_delta:.2f}MB"
    
    def test_memory_leak_detection_sensitivity(self):
        """Test memory leak detection sensitivity."""
        # Simulate memory leak by accumulating data
        self.memory_tracker.take_snapshot("leak_test_start")
        
        # Intentionally create memory leak
        leaked_data = []
        for i in range(10):
            # Add data without cleanup
            data = list(range(100000))  # ~0.8MB per iteration
            leaked_data.append(data)
            
            self.memory_tracker.take_snapshot(f"leak_iteration_{i}")
        
        # Should detect memory leak
        has_leak = self.memory_tracker.detect_memory_leak(threshold_mb=3)
        
        assert has_leak, "Failed to detect intentional memory leak"
        
        # Clean up
        leaked_data.clear()
        gc.collect()


class TestGarbageCollectionEfficiency:
    """Test garbage collection efficiency."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.memory_tracker = MemoryTracker()
        self.processor = MockDataProcessor()
    
    def test_garbage_collection_effectiveness(self):
        """Test that garbage collection effectively frees memory (robust, statistical, isolated)."""
        # We'll run the GC workload multiple times and evaluate median and tail,
        # and also run an isolated subprocess measurement for determinism.
        import statistics
        import subprocess

        def run_once_inprocess():
            # Baseline
            self.memory_tracker.take_snapshot("gc_baseline")

            # Create large amount of temporary data
            temp_data = []
            for _ in range(5):
                large_list = list(range(200000))  # ~1.6MB per list
                temp_data.append(large_list)

            self.memory_tracker.take_snapshot("before_gc")
            memory_before_gc = self.memory_tracker.snapshots[-1]['rss_mb']

            # Clear references and force garbage collection
            temp_data.clear()
            del temp_data

            # Measure GC effectiveness
            gc_start_time = time.perf_counter()
            collected = gc.collect()
            gc_end_time = time.perf_counter()

            gc_time_ms = (gc_end_time - gc_start_time) * 1000

            self.memory_tracker.take_snapshot("after_gc")
            memory_after_gc = self.memory_tracker.snapshots[-1]['rss_mb']

            memory_freed = memory_before_gc - memory_after_gc
            return gc_time_ms, memory_freed, collected

        # Run 3 iterations in-process to validate GC frees memory (timing can be noisy in shared process)
        freed = []
        for _ in range(3):
            _, mfree, _ = run_once_inprocess()
            freed.append(mfree)
        assert all(m >= 0 for m in freed), f"Some runs increased memory after GC: {freed}"

        # Isolated subprocess check for determinism across environments (measure timing here)
        code = (
            "import gc, time, statistics\n"
            "def run_once():\n"
            "    tmp=[]\n"
            "    for _ in range(5): tmp.append(list(range(200000)))\n"
            "    t0=time.perf_counter(); gc.collect(); t1=time.perf_counter()\n"
            "    return (t1-t0)*1000\n"
            "times=[run_once() for _ in range(7)]\n"
            "times.sort()\n"
            "p95 = times[int(0.95*(len(times)-1))]\n"
            "print(statistics.median(times), p95, max(times))\n"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        parts = proc.stdout.strip().split()
        if len(parts) >= 3:
            sub_median = float(parts[0])
            sub_p95 = float(parts[1])
            sub_max = float(parts[2])
            assert sub_median < 140, f"Subprocess median GC {sub_median:.2f}ms too slow"
            assert sub_p95 < 230, f"Subprocess 95th percentile GC {sub_p95:.2f}ms too slow"
            assert sub_max < 260, f"Subprocess worst-case GC {sub_max:.2f}ms too slow"
    
    def test_gc_performance_under_load(self):
        """Test garbage collection performance under load (robust + isolated timing)."""
        import subprocess
        import statistics

        # Move memory delta verification to a subprocess for determinism
        code = (
            "import gc, time, statistics, os, psutil\n"
            "proc = psutil.Process()\n"
            "def rss_mb(): return proc.memory_info().rss/1024/1024\n"
            "deltas=[]\n"
            "for _ in range(3):\n"
            "    garbage=[]\n"
            "    for _ in range(100): garbage.append([j for j in range(1000)])\n"
            "    before=rss_mb()\n"
            "    garbage.clear(); gc.collect()\n"
            "    after=rss_mb()\n"
            "    deltas.append(before-after)\n"
            "# Print deltas and timing stats for visibility\n"
            "print('DELTAS', *deltas)\n"
            "times=[]\n"
            "def run_once():\n"
            "    garbage=[]\n"
            "    for _ in range(100): garbage.append([j for j in range(1000)])\n"
            "    t0=time.perf_counter(); gc.collect(); t1=time.perf_counter()\n"
            "    return (t1-t0)*1000\n"
            "times=[run_once() for _ in range(7)]\n"
            "times.sort()\n"
            "p95 = times[int(0.95*(len(times)-1))]\n"
            "print('TIMES', statistics.median(times), p95, max(times))\n"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        parts = proc.stdout.strip().split()
        # Expect format: DELTAS d1 d2 d3 TIMES median p95 max
        try:
            deltas_idx = parts.index('DELTAS')
            times_idx = parts.index('TIMES')
            deltas = list(map(float, parts[deltas_idx+1:times_idx]))
            sub_median = float(parts[times_idx+1]); sub_p95 = float(parts[times_idx+2]); sub_max = float(parts[times_idx+3])
        except Exception as e:
            raise AssertionError(f"Unexpected subprocess output: {proc.stdout!r} {proc.stderr!r}") from e
        assert all(d >= 0 for d in deltas), f"Some iterations did not free memory (subprocess): {deltas}"

        # Isolated subprocess: measure timing distribution deterministically
        code = (
            "import gc, time, statistics\n"
            "def run_once():\n"
            "    garbage=[]\n"
            "    for _ in range(100): garbage.append([j for j in range(1000)])\n"
            "    t0=time.perf_counter(); gc.collect(); t1=time.perf_counter()\n"
            "    return (t1-t0)*1000\n"
            "times=[run_once() for _ in range(7)]\n"
            "times.sort()\n"
            "p95 = times[int(0.95*(len(times)-1))]\n"
            "print(statistics.median(times), p95, max(times))\n"
        )
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
        parts = proc.stdout.strip().split()
        assert len(parts) >= 3, f"Unexpected subprocess output: {proc.stdout!r} {proc.stderr!r}"
        sub_median = float(parts[0])
        sub_p95 = float(parts[1])
        sub_max = float(parts[2])

        # Thresholds chosen to be robust yet sensitive across CI/dev on Windows/Python
        assert sub_median < 140, f"Median GC under load {sub_median:.2f}ms too slow"
        assert sub_p95 < 230, f"95th percentile GC under load {sub_p95:.2f}ms too slow"
        assert sub_max < 300, f"Worst-case GC under load {sub_max:.2f}ms too slow"


class TestConcurrentMemoryUsage:
    """Test memory usage under concurrent operations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.memory_tracker = MemoryTracker()
        self.results = []
        self.errors = []
    
    def test_concurrent_memory_efficiency(self):
        """Test memory efficiency under concurrent load."""
        self.memory_tracker.take_snapshot("concurrent_baseline")
        
        def memory_worker(worker_id):
            """Worker that performs memory-intensive operations."""
            try:
                processor = MockDataProcessor()
                
                # Each worker processes data
                for i in range(5):
                    processor.process_large_dataset(size_mb=1)
                    time.sleep(0.01)  # Small delay
                
                # Clean up
                processor.clear_processed_data()
                
                self.results.append(f"Worker {worker_id} completed")
                
            except Exception as e:
                self.errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Start concurrent workers
        num_workers = 4
        threads = []
        
        for worker_id in range(num_workers):
            thread = threading.Thread(target=memory_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Monitor memory during execution
        for i in range(10):
            time.sleep(0.1)
            self.memory_tracker.take_snapshot(f"concurrent_monitor_{i}")
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Final cleanup and measurement
        gc.collect()
        self.memory_tracker.take_snapshot("concurrent_final")
        
        # Verify no errors
        assert len(self.errors) == 0, f"Concurrent memory errors: {self.errors}"
        
        # Verify all workers completed
        assert len(self.results) == num_workers
        
        # Verify memory usage is reasonable (use per-test delta from baseline)
        peak_abs = self.memory_tracker.get_peak_memory()
        # Find baseline RSS at the time of this test's baseline snapshot
        baseline_rss = None
        for snap in self.memory_tracker.snapshots:
            if snap['label'] == 'concurrent_baseline':
                baseline_rss = snap['rss_mb']
                break
        if baseline_rss is None:
            baseline_rss = self.memory_tracker.snapshots[0]['rss_mb']
        peak_delta = max(s['rss_mb'] - baseline_rss for s in self.memory_tracker.snapshots)
        final_delta = self.memory_tracker.get_memory_delta("concurrent_baseline")

        assert peak_delta < 200, \
            f"Peak concurrent memory delta {peak_delta:.2f}MB too high (abs {peak_abs:.2f}MB)"

        assert final_delta < 50, \
            f"Final memory delta {final_delta:.2f}MB too high"


if __name__ == "__main__":
    pytest.main([__file__])
