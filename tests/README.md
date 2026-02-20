# Tests

Test suite for HippoGraph neural memory system.

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run with coverage
pytest --cov=src --cov-report=html
```

## Test Structure

```
tests/
├── test_graph_engine.py    # Unit tests for core algorithms
├── test_integration.py     # Integration tests for full workflows
└── __init__.py
```

## Test Categories

- **Unit tests** (`@pytest.mark.unit`): Test individual components in isolation
- **Integration tests** (`@pytest.mark.integration`): Test full workflows
- **Slow tests** (`@pytest.mark.slow`): Performance benchmarks (skipped in CI)

## What's Tested

### Unit Tests (test_graph_engine.py)
- ✅ Spreading activation normalization (0-1 range)
- ✅ Activation decay over iterations
- ✅ Cosine similarity calculation
- ✅ Graph cache data structure
- ✅ Edge weight validation
- ✅ Embedding dimensions (384-dim)
- ✅ L2 normalization for cosine

### Integration Tests (test_integration.py)
- ✅ Database schema validation
- ✅ Note lifecycle (CRUD)
- ✅ Search exact matching
- ✅ Search result ranking
- ✅ Empty query handling
- ✅ Bidirectional edge consistency
- ✅ Graph connectivity
- ✅ Edge weight consistency
- ✅ Search response time < 1s
- ✅ Graph cache O(1) lookup

## Adding New Tests

1. Create test file: `tests/test_*.py`
2. Import pytest: `import pytest`
3. Create test class: `class TestFeature:`
4. Add test methods: `def test_something(self):`
5. Mark appropriately: `@pytest.mark.unit` or `@pytest.mark.integration`

## CI/CD

Tests run automatically on every push via GitHub Actions.
See `.github/workflows/tests.yml` for configuration.
