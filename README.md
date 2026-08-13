# Fake Cost Allocations Demo App

A vibe-coded application to implement a basic API application for allocating and tracking costs across business cost centres.

To be used in testing evaluations, imagining a semi-technical coworker has presented this for evaluation

## Test Scripts

### Pytest

```bash
python -m pytest -rA tests/
```

### Re-generate OpenAPI specification & lint

```bash
rm openapi.json && curl http://localhost:80/openapi.json >> openapi.json && spectral lint openapi.json
```

### Static Analysis scans

#### Semgrep

```bash
semgrep scan
```

#### Bandit

```bash
bandit app/ -r
```

#### SAST

```bash
python -m sast .
```

#### Pip Audit

```bash
pip-audit
```

#### Safety

```bash
safety scan
```

#### Depscan

```bash
depscan app/
```
