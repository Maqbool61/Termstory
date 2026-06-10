import pytest
from termstory.ai import reset_circuit_breaker

@pytest.fixture(autouse=True)
def reset_ai_circuit_breaker():
    """Ensure the AI circuit breaker is reset before every test to prevent cross-test contamination."""
    reset_circuit_breaker()
