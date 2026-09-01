"""
Context Budget Policy
=====================
Definiert Schwellenwerte und Steuerungsstrategien für die dynamische
Kontext-Budgetierung basierend auf dem aktuellen Füllgrad des Modells.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any


class BudgetTier(str, Enum):
    NORMAL = "normal"          # < 55%: Alles bleibt ungekürzt
    PREPARE = "prepare"        # 55% - 70%: Vorbereitung auf Verdichtung
    COMPACT = "compact"        # 70% - 80%: Inkrementelle Struktur-Kompaktierung
    AGGRESSIVE = "aggressive"  # > 80%: Aggressives Budgeting & hartes Fenster


@dataclass
class BudgetDecision:
    """Entscheidung des Budget-Managers für den aktuellen Turn."""
    tier: BudgetTier
    fill_ratio: float
    estimated_prompt_tokens: int
    context_limit: int
    recent_window_turns: int
    should_compact: bool
    should_prune_memory: bool


class BudgetPolicy:
    """Regelwerk für Schwellenwerte und Fenstergrößen."""

    THRESHOLD_PREPARE = 0.55
    THRESHOLD_COMPACT = 0.70
    THRESHOLD_AGGRESSIVE = 0.80

    @classmethod
    def evaluate(
        cls,
        estimated_prompt_tokens: int,
        context_limit: int
    ) -> BudgetDecision:
        """Ermittelt die Budget-Strategie für den aktuellen Request."""
        if context_limit <= 0:
            fill_ratio = 0.0
        else:
            fill_ratio = round(estimated_prompt_tokens / context_limit, 4)

        if fill_ratio < cls.THRESHOLD_PREPARE:
            return BudgetDecision(
                tier=BudgetTier.NORMAL,
                fill_ratio=fill_ratio,
                estimated_prompt_tokens=estimated_prompt_tokens,
                context_limit=context_limit,
                recent_window_turns=10,
                should_compact=False,
                should_prune_memory=False
            )
        elif fill_ratio < cls.THRESHOLD_COMPACT:
            return BudgetDecision(
                tier=BudgetTier.PREPARE,
                fill_ratio=fill_ratio,
                estimated_prompt_tokens=estimated_prompt_tokens,
                context_limit=context_limit,
                recent_window_turns=8,
                should_compact=False,
                should_prune_memory=False
            )
        elif fill_ratio < cls.THRESHOLD_AGGRESSIVE:
            return BudgetDecision(
                tier=BudgetTier.COMPACT,
                fill_ratio=fill_ratio,
                estimated_prompt_tokens=estimated_prompt_tokens,
                context_limit=context_limit,
                recent_window_turns=6,
                should_compact=True,
                should_prune_memory=False
            )
        else:
            return BudgetDecision(
                tier=BudgetTier.AGGRESSIVE,
                fill_ratio=fill_ratio,
                estimated_prompt_tokens=estimated_prompt_tokens,
                context_limit=context_limit,
                recent_window_turns=4,
                should_compact=True,
                should_prune_memory=True
            )
