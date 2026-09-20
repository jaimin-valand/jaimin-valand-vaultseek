# Contributing

Thanks for contributing to Private Search Engine.

## Development principles

1. Keep the implementation deterministic where practical.
2. Prefer small, testable components over framework-heavy abstractions.
3. Preserve local-first behaviour and avoid unnecessary external dependencies.
4. Add regression tests for behavioural changes.
5. Document architectural trade-offs and explicit limitations.
6. Do not place secrets, private documents, or credentials in fixtures or traces.

## Validation

Run:

```bash
python -m pytest -q
python -m compileall -q private_search_engine
python -m private_search_engine.cli release-gate
```

All three checks should pass before opening a pull request.

## Pull requests

Describe:

- what changed;
- why it changed;
- affected modules/endpoints;
- tests added or updated;
- performance or compatibility impact;
- any known limitations.
