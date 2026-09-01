"""
Unit tests for prompt builder consent instructions (Issue #26).
"""
from services.prompt_builder import (
    build_consent_required_instructions,
    build_personality_and_instructions_block,
    build_temporal_context,
)


def test_build_consent_required_instructions():
    instructions = build_consent_required_instructions()

    # Must contain clear directives against speculative refusals
    assert "KEINE SPEKULATIVEN VERWEIGERUNGEN" in instructions
    assert "AKTIVES TOOL-CALLING" in instructions
    assert "BEI TATSÄCHLICHEM consent_required FEHLER" in instructions

    # Must mention web_search and not inventing permission blocks
    assert "web_search" in instructions
    assert "consent_required" in instructions


def test_build_personality_and_instructions_block():
    block = build_personality_and_instructions_block(
        username="Mirko",
        personality="helpful",
        custom_instructions="Sei immer präzise.",
    )
    assert "Mirko" in block
    assert "Sei immer präzise." in block


def test_build_temporal_context():
    context = build_temporal_context()
    assert "Uhr" in context
    assert any(month in context for month in [
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember"
    ])
