def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


def test_add() -> None:
  assert add(2, 3) == 5
