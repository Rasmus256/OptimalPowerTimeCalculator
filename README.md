# Optimal Power Time Calculator

A tool for figuring out, not only the next whole hour of cheap electricity, but a custom duration, like the time it takes to run the dishwasher!


## Test and linting
Run the following inside the container:
```
docker run --rm -v $(pwd)/src/api:/app optimal-power-calculator <command>
```

### Tests
Run tests with:
```
 python -m pytest -v
```

### Ruff

Ruff is configured as the project's linter and formatter. The configuration is in `src/api/pyproject.toml`.

#### Check for linting issues with optional fixing
```
python -m ruff check api/ (--fix)
```

#### Format code
```
pytonh -m ruff format src/api/
```
