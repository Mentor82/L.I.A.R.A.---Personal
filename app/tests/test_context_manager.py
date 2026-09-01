import os
import sys
import unittest
from pathlib import Path

# Add app directory to sys.path
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from services.context import (
    TokenEstimator,
    BudgetPolicy,
    BudgetTier,
    StructuredCompactor,
    StructuredSessionState,
    ContextBudgetManager
)


class TestContextBudgetManager(unittest.TestCase):

    def test_token_estimator_limits(self):
        self.assertEqual(TokenEstimator.get_model_context_limit("llama3.2:3b"), 8192)
        self.assertEqual(TokenEstimator.get_model_context_limit("qwen2.5:7b"), 32768)
        self.assertEqual(TokenEstimator.get_model_context_limit("nemotron-3-ultra:cloud"), 131072)
        self.assertEqual(TokenEstimator.get_model_context_limit("unknown_custom_model"), 8192)

    def test_token_estimation(self):
        text = "Das ist ein Beispielsatz für die Token-Schätzung."
        tokens = TokenEstimator.estimate_text_tokens(text)
        self.assertGreater(tokens, 5)
        self.assertLess(tokens, 30)

        messages = [
            {"role": "system", "content": "Du bist LIARA."},
            {"role": "user", "content": "Hallo!"}
        ]
        msg_tokens = TokenEstimator.estimate_messages_tokens(messages)
        self.assertGreaterEqual(msg_tokens, 10)

    def test_budget_policy_tiers(self):
        # 1. Normal (< 55%)
        dec_normal = BudgetPolicy.evaluate(estimated_prompt_tokens=2000, context_limit=8192)
        self.assertEqual(dec_normal.tier, BudgetTier.NORMAL)
        self.assertFalse(dec_normal.should_compact)
        self.assertEqual(dec_normal.recent_window_turns, 10)

        # 2. Prepare (55% - 70%)
        dec_prep = BudgetPolicy.evaluate(estimated_prompt_tokens=5000, context_limit=8192)
        self.assertEqual(dec_prep.tier, BudgetTier.PREPARE)
        self.assertFalse(dec_prep.should_compact)

        # 3. Compact (70% - 80%)
        dec_compact = BudgetPolicy.evaluate(estimated_prompt_tokens=6000, context_limit=8192)
        self.assertEqual(dec_compact.tier, BudgetTier.COMPACT)
        self.assertTrue(dec_compact.should_compact)
        self.assertEqual(dec_compact.recent_window_turns, 6)

        # 4. Aggressive (> 80%)
        dec_aggr = BudgetPolicy.evaluate(estimated_prompt_tokens=7000, context_limit=8192)
        self.assertEqual(dec_aggr.tier, BudgetTier.AGGRESSIVE)
        self.assertTrue(dec_aggr.should_compact)
        self.assertTrue(dec_aggr.should_prune_memory)
        self.assertEqual(dec_aggr.recent_window_turns, 4)

    def test_structured_compactor_preservation(self):
        turns = [
            {"role": "user", "content": "Wir nutzen ab jetzt Port 8100 und qwen3.5:cloud als Vision-Sensor."},
            {"role": "assistant", "content": "Verstanden, Port 8100 ist beschlossen."},
            {"role": "user", "content": "Bitte nur auf Deutsch antworten und niemals jQuery einbinden."}
        ]
        state = StructuredSessionState()
        updated = StructuredCompactor.extract_heuristic_facts(turns, state)

        self.assertGreater(len(updated.decisions), 0)
        self.assertGreater(len(updated.user_constraints), 0)
        
        # Test formatting block
        block = updated.format_context_block()
        self.assertIn("[STRUCTURED SESSION STATE", block)
        self.assertIn("decisions", block)

    def test_context_budget_manager_compaction(self):
        # Build 15 turns
        messages = [{"role": "system", "content": "Du bist LIARA."}]
        for i in range(15):
            messages.append({"role": "user", "content": f"Turn {i}: Wir nutzen Port {8000 + i}. Hier ist langer Text " * 80})
            messages.append({"role": "assistant", "content": f"Antwort {i}: Verstanden." * 40})

        # Process with a small context model to trigger compaction
        res = ContextBudgetManager.process_turn_context(
            messages=messages,
            model_name="llava:7b",  # limit = 4096
            session_state=StructuredSessionState()
        )

        self.assertTrue(res.decision.should_compact)
        self.assertLess(len(res.messages), len(messages))
        self.assertLess(res.optimized_tokens, res.original_tokens)
        self.assertIn("[STRUCTURED SESSION STATE", res.messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
