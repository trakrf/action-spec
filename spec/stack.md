# Stack: Python Backend + Vue Frontend

**Maturity**: Alpha - Velocity over stability. Breaking changes expected.

---

## Python Backend (Flask)

> **Runtime**: Python 3.14
> **Package Manager**: uv
> **Test Framework**: pytest
> **Formatter**: black
> **Type Checker**: mypy

### Lint
```bash
just backend lint
```

### Format (auto-fix)
```bash
just backend format
```

### Test
```bash
just backend test
```

### Build
```bash
just backend build
```

---

## Vue Frontend

> **Framework**: Vue 3 (Composition API)
> **Package Manager**: pnpm
> **CSS Framework**: Tailwind CSS v4
> **Test Runner**: Playwright
> **Build Tool**: Vite
> **Linter**: ESLint 9 (flat config)

### Lint
```bash
just frontend lint
```

### Test (E2E with Playwright)
```bash
just frontend test
```

### Build
```bash
just frontend build
```

---

## Monorepo Commands

### Lint All
```bash
just lint
```

### Test All
```bash
just test
```

### Build All
```bash
just build
```

### Validate All (lint + test + build)
```bash
just validate
```
