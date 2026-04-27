---
description: Generar release notes desde el último tag
argument-hint: [next_version]
---

Generá release notes para la versión `$ARGUMENTS` (default: vNEXT) desde el último tag.

```bash
# Último tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "(sin tags previos)")
echo "Último tag: $LAST_TAG"

# Commits desde el último tag, agrupados por tipo (Conventional Commits)
git log $LAST_TAG..HEAD --pretty=format:"%h %s" 2>&1 | head -50
```

Agrupá los commits por tipo:

- **🚀 Features (`feat:`)**
- **🐛 Bug fixes (`fix:`)**
- **📚 Docs (`docs:`)**
- **🔧 Refactor (`refactor:`)**
- **🧪 Tests (`test:`)**
- **⚡ Perf (`perf:`)**
- **Otros**

Ignorá merges (`Merge`, `Revert`).

Generá un markdown listo para pegar en GitHub release:

```markdown
## $ARGUMENTS — YYYY-MM-DD

### 🚀 Features
- (commit message corto) (#PR)

### 🐛 Bug fixes
- ...

### 📚 Docs
- ...

**Full changelog:** $LAST_TAG...$ARGUMENTS
```

**Reglas:**
- Si un commit no sigue Conventional Commits → ponerlo en "Otros".
- Si hay breaking changes (`BREAKING CHANGE:` en body) → resaltarlos arriba.
- Si hay <3 commits → no tiene sentido versionar, sugerir esperar.
