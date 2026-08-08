from local_agent.context import ContextBudget, ContextManager, ContextPhase, estimate_tokens


def test_token_budget_never_exceeded():
    budget = ContextBudget(total_tokens=50, retrieved_limit=20)
    manager = ContextManager(budget)
    manager.set_retrieved_context(" ".join(["retrieved"] * 100))
    for index in range(10):
        manager.add_message("user", f"message number {index} with extra words")
    assert manager.total_tokens() <= budget.total_tokens


def test_phase_assembly_respects_phase_budget():
    budget = ContextBudget(total_tokens=10_000, retrieved_limit=100)
    manager = ContextManager(budget)
    manager.add_message("user", " ".join(["plan"] * 200))
    assembled = manager.assemble_for_phase(ContextPhase.PLANNING)
    assert estimate_tokens(assembled) <= budget.phase_budgets[ContextPhase.PLANNING]


def test_compaction_preserves_critical_state():
    budget = ContextBudget(total_tokens=200)
    manager = ContextManager(budget)
    manager.add_message("system", "critical task goal", critical=True)
    for index in range(20):
        manager.add_message("user", f"filler {index}")
    result = manager.compact(preserve_critical=True, checkpoint_before=True)
    assert any(message.critical for message in result.messages)
    assert result.checkpoint_boundary is True


def test_retrieved_context_truncation():
    budget = ContextBudget(total_tokens=500, retrieved_limit=10)
    manager = ContextManager(budget)
    truncated = manager.set_retrieved_context(" ".join(["word"] * 100))
    assert estimate_tokens(truncated) <= 10
    assert truncated.endswith("...[truncated]")
