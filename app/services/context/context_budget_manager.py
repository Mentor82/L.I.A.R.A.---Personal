"""
Context Budget Manager
======================
Zentraler Einstiegspunkt für die 4-Schichten-Kontextarchitektur:
1. Pinned Constraints
2. Structured Session State (Inkrementell verdichtet)
3. Retrieved 4D Memory (Budget-angepasst)
4. Recent Window (Exakter Wortlaut der jüngsten Turns)
"""
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from services.context.token_estimator import TokenEstimator
from services.context.budget_policy import BudgetPolicy, BudgetTier, BudgetDecision
from services.context.structured_compactor import StructuredCompactor, StructuredSessionState

logger = logging.getLogger(__name__)


@dataclass
class ContextAssemblyResult:
    """Ergebnis der Kontext-Optimierung für den anstehenden LLM-Turn."""
    messages: List[Dict[str, Any]]
    session_state: StructuredSessionState
    decision: BudgetDecision
    original_tokens: int
    optimized_tokens: int
    memory_items: List[Dict[str, Any]]


class ContextBudgetManager:
    """Verwaltet und assembliert den dynamischen Kontext vor dem LLM-Aufruf."""

    @classmethod
    def process_turn_context(
        cls,
        messages: List[Dict[str, Any]],
        model_name: str,
        session_state: Optional[StructuredSessionState] = None,
        memory_items: Optional[List[Dict[str, Any]]] = None,
    ) -> ContextAssemblyResult:
        """
        Analysiert den Kontextbedarf und liefert ein token-optimiertes,
        verlustfreies 4-Zonen-Nachrichtenpaket zurück.
        """
        current_state = session_state or StructuredSessionState()
        mem_list = list(memory_items or [])

        context_limit = TokenEstimator.get_model_context_limit(model_name)
        initial_tokens = TokenEstimator.estimate_messages_tokens(messages)

        decision = BudgetPolicy.evaluate(
            estimated_prompt_tokens=initial_tokens,
            context_limit=context_limit
        )

        logger.info(
            "ContextManager evaluation: model='%s', limit=%d, est_tokens=%d, ratio=%.1f%%, tier='%s'",
            model_name, context_limit, initial_tokens, decision.fill_ratio * 100, decision.tier.value
        )

        # Wenn Normal oder Prepare -> Unverändert durchleiten
        if not decision.should_compact or len(messages) <= decision.recent_window_turns + 1:
            return ContextAssemblyResult(
                messages=messages,
                session_state=current_state,
                decision=decision,
                original_tokens=initial_tokens,
                optimized_tokens=initial_tokens,
                memory_items=mem_list
            )

        # 1. System-Message separieren
        system_msg = None
        dialog_turns = []
        for msg in messages:
            if isinstance(msg, dict) and msg.get("role") == "system" and system_msg is None:
                system_msg = msg
            else:
                dialog_turns.append(msg)

        # 2. Aufteilung in Ältere Turns vs. Recent Window
        window_size = decision.recent_window_turns
        if len(dialog_turns) > window_size:
            older_turns = dialog_turns[:-window_size]
            recent_turns = dialog_turns[-window_size:]
        else:
            older_turns = []
            recent_turns = dialog_turns

        # 3. Ältere Turns inkrementell in den Structured State überführen
        if older_turns:
            updated_state = StructuredCompactor.extract_heuristic_facts(older_turns, current_state)
            updated_state.last_compacted_turn_index += len(older_turns)
        else:
            updated_state = current_state

        # 4. Memory Pruning bei Aggressive Tier
        if decision.should_prune_memory and len(mem_list) > 2:
            mem_list = mem_list[:2]

        # 5. Nachrichten assemblieren
        optimized_messages = []
        if system_msg:
            sys_content = str(system_msg.get("content", ""))
            # State-Block in System-Prompt einbetten falls vorhanden
            state_block = updated_state.format_context_block()
            if state_block and "[STRUCTURED SESSION STATE" not in sys_content:
                sys_content += f"\n\n{state_block}"
            optimized_messages.append({"role": "system", "content": sys_content})

        optimized_messages.extend(recent_turns)

        optimized_tokens = TokenEstimator.estimate_messages_tokens(optimized_messages)

        logger.info(
            "ContextManager compacted: %d turns -> %d recent turns. Tokens: %d -> %d (Saved: %d)",
            len(dialog_turns), len(recent_turns), initial_tokens, optimized_tokens, initial_tokens - optimized_tokens
        )

        return ContextAssemblyResult(
            messages=optimized_messages,
            session_state=updated_state,
            decision=decision,
            original_tokens=initial_tokens,
            optimized_tokens=optimized_tokens,
            memory_items=mem_list
        )
