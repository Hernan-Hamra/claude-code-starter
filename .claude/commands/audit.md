---
description: Auditoría rápida del proyecto (lint + tests + secrets + TODOs)
---

Corré la auditoría completa del proyecto. Reportá GO/NO-GO al final.

```bash
# 1. Lint / format check
ruff check . 2>&1 | tail -20 || flake8 . 2>&1 | tail -20

# 2. Type check (si hay mypy/pyright config)
mypy . --ignore-missing-imports 2>&1 | tail -20 || true

# 3. Tests rápidos (sin slow markers)
python -m pytest tests/ -x --ignore=tests/_legacy -q 2>&1 | tail -20

# 4. Secrets scan
git diff HEAD~5..HEAD | grep -iE 'api[_-]?key|secret|password|token' | head -10 || echo "ningun match"

# 5. TODOs sin issue
grep -rn 'TODO\|FIXME\|XXX' --include='*.py' --include='*.ts' --include='*.js' . 2>/dev/null | head -20
```

Reportá:
- ✅/❌ Lint
- ✅/❌ Type check
- ✅/❌ Tests (cuántos pasan, cuántos fallan)
- ⚠️ Secrets en diff reciente
- ⚠️ TODOs sin tracking

**Veredicto final:** GO si lint+type+tests OK. NO-GO si algo crítico falla.

**No modificar nada.** Solo auditar y reportar.
