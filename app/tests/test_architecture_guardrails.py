import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.check_architecture import run_audit, count_file_lines, DEFAULT_SOFT_LIMIT, DEFAULT_HARD_LIMIT


class TestArchitectureGuardrails(unittest.TestCase):
    """
    Automated Architecture Guardrail Tests (Issue #21).
    Ensures that the codebase adheres to line-count limits and prevents monolithic 'God Files'.
    """

    def test_current_codebase_passes_guardrails(self):
        """Verify that the current codebase passes the architecture audit with no hard errors or ratchet violations."""
        exit_code, errors, warnings, info = run_audit(strict_ratchet=True)
        self.assertEqual(
            exit_code,
            0,
            f"Architecture guardrails failed with {len(errors)} error(s):\n" + "\n".join(f"  - {e}" for e in errors)
        )

    def test_guardrails_catches_unauthorized_new_monolith(self):
        """Verify that a new un-grandfathered file exceeding the hard limit is flagged as an error."""
        simulated_files = {
            'app/services/new_huge_service.py': 950,
            'app/services/small_service.py': 120
        }

        with patch('scripts.check_architecture.scan_directory', return_value={}), \
             patch('scripts.check_architecture.load_baseline', return_value={}):
            
            with patch('scripts.check_architecture.scan_directory', side_effect=[
                {'app/services/new_huge_service.py': 950},
                {'frontend/src/components/small.jsx': 120}
            ]):
                exit_code, errors, warnings, _ = run_audit(hard_limit=800)
                self.assertEqual(exit_code, 1)
                self.assertTrue(any("HARD LIMIT VIOLATION" in e and "new_huge_service.py" in e for e in errors))

    def test_guardrails_catches_ratchet_growth(self):
        """Verify that an existing grandfathered file growing beyond its baseline tolerance triggers a failure."""
        simulated_baseline = {
            'app/api/routers/legacy_router.py': 600
        }
        # File grew from 600 to 700 (exceeding tolerance of 25 lines)
        simulated_files = {
            'app/api/routers/legacy_router.py': 700
        }

        with patch('scripts.check_architecture.load_baseline', return_value=simulated_baseline), \
             patch('scripts.check_architecture.scan_directory', side_effect=[
                 simulated_files,
                 {}
             ]):
            exit_code, errors, warnings, _ = run_audit(strict_ratchet=True)
            self.assertEqual(exit_code, 1)
            self.assertTrue(any("RATCHET VIOLATION" in e and "legacy_router.py" in e for e in errors))

    def test_guardrails_rewards_refactoring_shrinkage(self):
        """Verify that a grandfathered file shrinking by >50 lines is recorded as refactoring progress."""
        simulated_baseline = {
            'app/api/routers/chat_streaming.py': 2154
        }
        # File successfully modularized down to 1400 lines
        simulated_files = {
            'app/api/routers/chat_streaming.py': 1400
        }

        with patch('scripts.check_architecture.load_baseline', return_value=simulated_baseline), \
             patch('scripts.check_architecture.scan_directory', side_effect=[
                 simulated_files,
                 {}
             ]):
            exit_code, errors, warnings, info = run_audit(strict_ratchet=True)
            self.assertEqual(exit_code, 0)
            self.assertTrue(any("REFACTOR SUCCESS" in i and "chat_streaming.py" in i for i in info))
