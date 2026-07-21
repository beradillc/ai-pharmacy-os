"""Clinical AI module — decision-support for safe dispensing (bounded context).

Hexagonal layers: ``domain`` (pure) → ``application`` (use-cases) →
``infrastructure`` (SQLAlchemy) → ``interface`` (HTTP + composition).

Design stance (docs/12_AI_INTEGRATION.md): the safety-critical output is
**deterministic** — drug-interaction findings come from a rule engine over the
``drug_interactions`` reference table, not from the LLM. The LLM only *explains*
findings in natural language, and every recommendation is advisory until a
pharmacist accepts it (human-in-the-loop). This is what lets the module be built
and tested against a mock ``LLMProvider`` with no real API calls.

    # BLOCKER: real drug-knowledge source (licensed) + AI__API_KEY are required
    # before RAG (drug_knowledge_chunks) and a real LLM provider can be wired.
"""
