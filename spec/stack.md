# Stack: Python Backend + React Frontend

**Maturity**: Alpha - Velocity over stability. Breaking changes expected.

---

## Python Backend (Lambda Functions)

> **Runtime**: Python 3.11
> **Test Framework**: pytest
> **Formatter**: black
> **Type Checker**: mypy

### Lint & Format
```bash
cd backend
black --check lambda/ tests/
```

### Format (auto-fix)
```bash
cd backend
black lambda/ tests/
```

### Typecheck
```bash
cd backend
mypy lambda/ --ignore-missing-imports
```

### Test
```bash
cd backend
pytest tests/ -v --cov=lambda --cov-report=term-missing
```

### Test (specific file)
```bash
cd backend
pytest tests/test_parser.py -v
```

### Test (with coverage threshold)
```bash
cd backend
pytest tests/ -v --cov=lambda --cov-report=term-missing --cov-fail-under=80
```

---

## React Frontend (Phase 3.4+)

> **Package Manager**: npm
> **Test Runner**: Vitest
> **Build Tool**: Vite

### Lint
```bash
npm run lint --fix
```

### Typecheck
```bash
npm run typecheck
```

### Test
```bash
npm test
```

### Build
```bash
npm run build
```

### E2E Tests (Optional)
```bash
# If playwright.config.ts exists
npm run test:e2e
```
