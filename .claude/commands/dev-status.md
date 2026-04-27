---
description: Estado del repo (branch, commits, PRs, issues abiertos, TODOs)
---

Mostrame el estado actual del proyecto.

```bash
# 1. Branch + uncommitted
git status -sb

# 2. Commits ahead/behind
git log --oneline -10

# 3. PRs abiertos (si hay gh)
command -v gh && gh pr list --limit 10 || echo "gh no instalado"

# 4. Issues abiertos
command -v gh && gh issue list --limit 10 || echo "gh no instalado"

# 5. Branches stale (mergeadas a main)
git branch --merged main 2>/dev/null | grep -v '^\*\|main\|master' | head -10

# 6. TODOs/FIXMEs activos
grep -rn 'TODO\|FIXME' --include='*.py' --include='*.ts' --include='*.js' . 2>/dev/null | wc -l
```

Reportá:
- Branch actual + cuántos commits no pusheados
- Últimos 10 commits con mensaje
- N PRs abiertos / N issues abiertos
- Branches stale candidatas a borrar
- N TODOs en código

Si hay PR/issue urgente (label `priority`, `urgent`) → resaltarlo.
