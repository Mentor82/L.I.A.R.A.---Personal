"""
Unit Tests for Multi-Version Sandbox Runtimes (Python 3.11 - 3.14 & Julia)
=========================================================================
"""

import os
import unittest
from pathlib import Path

os.environ["LIARA_SECRET_KEY"] = "test_secret_key_for_unit_tests_1234567890abcdef"

from services.code_sandbox import (
    normalize_language,
    get_interpreter_binary,
    get_script_filename,
    AVAILABLE_RUNTIMES,
    _build_command,
    MEMORY_LIMITS,
)


class TestSandboxRuntimes(unittest.TestCase):

    def test_normalize_language_python_versions(self):
        """Verify Python 3.11-3.14 aliases normalize correctly."""
        self.assertEqual(normalize_language("python3.11"), "python3.11")
        self.assertEqual(normalize_language("py311"), "python3.11")
        self.assertEqual(normalize_language("3.11"), "python3.11")

        self.assertEqual(normalize_language("python3.12"), "python3.12")
        self.assertEqual(normalize_language("py312"), "python3.12")
        self.assertEqual(normalize_language("3.12"), "python3.12")

        self.assertEqual(normalize_language("python3.13"), "python3.13")
        self.assertEqual(normalize_language("py313"), "python3.13")
        self.assertEqual(normalize_language("3.13"), "python3.13")

        self.assertEqual(normalize_language("python3.14"), "python3.14")
        self.assertEqual(normalize_language("py314"), "python3.14")
        self.assertEqual(normalize_language("3.14"), "python3.14")

        # Default python/py maps to python3.14
        self.assertEqual(normalize_language("python"), "python3.14")
        self.assertEqual(normalize_language("py"), "python3.14")
        self.assertEqual(normalize_language("python3"), "python3.14")

        # Julia
        self.assertEqual(normalize_language("julia"), "julia")
        self.assertEqual(normalize_language("jl"), "julia")

        # Invalid
        self.assertIsNone(normalize_language("rust"))
        self.assertIsNone(normalize_language(""))

    def test_available_runtimes_structure(self):
        """Verify AVAILABLE_RUNTIMES contains 3.11-3.14 and marks 3.14 as default."""
        runtime_ids = [r["id"] for r in AVAILABLE_RUNTIMES]
        self.assertIn("python3.14", runtime_ids)
        self.assertIn("python3.13", runtime_ids)
        self.assertIn("python3.12", runtime_ids)
        self.assertIn("python3.11", runtime_ids)
        self.assertIn("julia", runtime_ids)

        default_runtime = next((r for r in AVAILABLE_RUNTIMES if r.get("default")), None)
        self.assertIsNotNone(default_runtime)
        self.assertEqual(default_runtime["id"], "python3.14")

    def test_memory_limits_defined_for_all_runtimes(self):
        """Verify memory limits exist for each supported runtime."""
        for r in AVAILABLE_RUNTIMES:
            self.assertIn(r["id"], MEMORY_LIMITS)
            self.assertGreater(MEMORY_LIMITS[r["id"]], 0)

    def test_script_filenames(self):
        """Verify script extension mappings."""
        self.assertEqual(get_script_filename("python3.11"), "script.py")
        self.assertEqual(get_script_filename("python3.14"), "script.py")
        self.assertEqual(get_script_filename("julia"), "script.jl")

    def test_build_command_structure(self):
        """Verify command construction for sandboxed runner script."""
        ws_dir = Path("/tmp/session_1/workspace")
        script_path = Path("/tmp/session_1/.runs/run_1/script.py")
        cmd = _build_command("python3.14", ws_dir, script_path)
        self.assertEqual(cmd[0], "sudo")
        self.assertEqual(cmd[1], "-n")
        self.assertEqual(cmd[2], "-u")
        self.assertEqual(cmd[3], "liara-runner")
        self.assertEqual(cmd[4], "--")
        self.assertTrue(cmd[5].endswith("run_sandboxed.sh"))
        self.assertEqual(cmd[6], "python3.14")
        self.assertEqual(cmd[7], str(ws_dir))
        self.assertEqual(cmd[8], str(script_path))


if __name__ == "__main__":
    unittest.main()
