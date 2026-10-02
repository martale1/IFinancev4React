import os
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor

import yfinance_runtime as runtime


class YfinanceRuntimeTest(unittest.TestCase):
    def test_current_process_is_alive(self):
        self.assertTrue(runtime._process_exists(os.getpid()))

    def test_another_process_preserves_live_cache(self):
        cache = runtime.yf_cache.get_tz_cache()
        cache.store("RUNTIME_TEST", "Europe/Rome")
        subprocess.run(
            [sys.executable, "-c", "import yfinance_runtime"],
            cwd=str(runtime._runtime_root.parent), check=True, timeout=30,
        )
        self.assertTrue(runtime._runtime_dir.is_dir())
        self.assertEqual(cache.lookup("RUNTIME_TEST"), "Europe/Rome")

    def test_cache_is_ready_for_request_workers(self):
        def lookup(_):
            return runtime.yf_cache.get_tz_cache().lookup("UNKNOWN_TEST")

        with ThreadPoolExecutor(max_workers=8) as workers:
            self.assertEqual(list(workers.map(lookup, range(16))), [None] * 16)


if __name__ == "__main__":
    unittest.main()
