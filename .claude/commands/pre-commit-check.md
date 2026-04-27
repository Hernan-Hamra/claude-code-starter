---
description: Gate pre-commit — lint + tests + secrets + diff sano
---

Antes de hacer `git commit`, verificá:

```bash
# 1. No hay archivos sensibles staged
git diff --cached --name-only | grep -iE '\.env$|\.pem$|\.key$|secrets/|credentials' && echo "❌ ARCHIVO SENSIBLE STAGED" || echo "✅ ningún archivo sensible"

# 2. No hay secrets en el diff
git diff --cached | grep -iE 'AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|api[_-]?key.*=.*["\x27][^"\x27]{16,}' | head -5

# 3. Archivos staged
git diff --cached --stat

# 4. Lint solo en archivos staged (Python)
git diff --cached --name-only --diff-filter=ACM | grep '\.py$' | xargs -r ruff check 2>&1 | head -20

# 5. Tests del proyecto
python -m pytest tests/ -x -q --ignore=tests/_legacy 2>&1 | tail -10
```

Reportá:
- ✅/❌ Sin archivos sensibles
- ✅/❌ Sin secrets en el diff
- ✅/❌ Lint pasa en archivos staged
- ✅/❌ Tests pasan

**Si todo OK → GO commit.**
**Si algo falla → NO-GO. No commitear.**

Para casos legítimos (ej: agregar template `.env.example`), bypass manual:
`git commit --no-verify` (a tu riesgo).
