import os
import sys
import time
import psutil
import gc
import copy
import importlib
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def rss_mb():
    return psutil.Process().memory_info().rss / 1024 / 1024


def measure_once(tag: str, fn):
    gc.collect()
    before = rss_mb()
    t0 = time.perf_counter()
    result = fn()
    dt = (time.perf_counter() - t0) * 1000.0
    after = rss_mb()
    print(f"{tag}: time_ms={dt:.1f} rss_delta_mb={after-before:.2f}")
    return result, dt, after - before


def main():
    import src.dict_utils as du
    data_dir = "data"

    # 1) Cold load (parsing) -> this represents 'no cache' initial cost
    du._MINI_DICT_CACHE.clear()
    du._CEDICT_CACHE.clear()
    d1, t_parse_ms, mem1 = measure_once("cold_load_parse", lambda: du.create_default_dict(data_dir))

    # 2) Warm load (cached) -> represents 'with cache' subsequent loads
    d2, t_cached_ms, mem2 = measure_once("warm_load_cached", lambda: du.create_default_dict(data_dir))

    # 3) Simulate no-cache multiple copies: deep-copy dicts N times to approximate
    N = 2  # create 2 extra copies beyond the original (total ~3 copies)
    copies = []
    def make_copies():
        for _ in range(N):
            copies.append(copy.deepcopy(d1.mini_dict))
            copies.append(copy.deepcopy(d1.cedict_data))
        return len(copies)
    _, t_copies_ms, mem_copies = measure_once("deepcopy_duplicates", make_copies)

    # 4) Reload module to force a re-parse (approx no-cache load in a new interpreter)
    du = importlib.reload(du)
    d3, t_reparse_ms, mem3 = measure_once("module_reload_reparse", lambda: du.create_default_dict(data_dir))

    print("\nSummary:")
    print(f"- Parse once (no cache initial): {t_parse_ms:.1f} ms, +{mem1:.2f} MB RSS")
    print(f"- Subsequent cached load:        {t_cached_ms:.1f} ms, +{mem2:.2f} MB RSS")
    print(f"- Duplicate copies (~2x more):   {t_copies_ms:.1f} ms, +{mem_copies:.2f} MB RSS")
    print(f"- Re-parse after module reload:  {t_reparse_ms:.1f} ms, +{mem3:.2f} MB RSS")


if __name__ == "__main__":
    main()

