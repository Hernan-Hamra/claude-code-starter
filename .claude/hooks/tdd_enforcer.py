"""
TDD Enforcer — Hook PreToolUse genérico.

Detecta intentos de Edit/Write en código productivo sin test correspondiente.
Avisa por stderr (no bloquea) para no interrumpir el flujo.

CONFIG-DRIVEN: lee `.claude/tdd-config.json` desde la raíz del proyecto.
Estructura esperada:
{
  "watch_paths": ["src/", "lib/", "app/"],
  "tests_dir": "tests/",
  "test_prefix": "test_",
  "exclude_patterns": ["__init__.py", "config.py", "fixtures/"],
  "enabled": true
}

Si no existe el archivo, usa defaults sensibles (Python project layout).

Hook Type: PreToolUse (matcher: Edit|Write|NotebookEdit)
Exit code: 0 (avisa pero no bloquea).

Patrón portado desde ARGOS .claude/hooks/tdd_enforcer.py — versión config-driven
extraída para `claude-code-starter`.
"""
import json
import os
import sys
from pathlib import Path

# Default config (Python project con tests/test_<modulo>.py)
DEFAULTS = {
    "watch_paths": ["src/", "lib/", "app/", "tools/"],
    "tests_dir": "tests/",
    "test_prefix": "test_",
    "exclude_patterns": [
        "__init__.py",
        "config.py",
        "settings.py",
        "fixtures/",
        "_legacy_",
        "archived/",
        "seeds/",
    ],
    "enabled": True,
}


def load_config(root: Path) -> dict:
    """Carga config desde .claude/tdd-config.json o devuelve defaults."""
    config_path = root / ".claude" / "tdd-config.json"
    if not config_path.exists():
        return DEFAULTS
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            user = json.load(f)
    except Exception:
        return DEFAULTS
    cfg = {**DEFAULTS, **user}
    return cfg


def find_project_root() -> Path:
    """Sube hasta encontrar marcadores de proyecto (.git, pyproject.toml, package.json)."""
    p = Path.cwd().resolve()
    for parent in (p, *p.parents):
        if any((parent / m).exists() for m in (".git", "pyproject.toml", "package.json")):
            return parent
    return p


def archivo_necesita_test(path: str, cfg: dict) -> bool:
    p = path.replace("\\", "/")
    if not p.endswith(".py"):
        return False
    if not any(wp in p for wp in cfg["watch_paths"]):
        return False
    if any(ex in p for ex in cfg["exclude_patterns"]):
        return False
    return True


def existe_test_para(path: str, root: Path, cfg: dict) -> bool:
    p = path.replace("\\", "/")
    # Obtener stem del módulo: tools/foo/bar.py → bar
    stem = Path(p).stem
    if not stem:
        return False
    tests_dir = root / cfg["tests_dir"]
    if not tests_dir.exists():
        return False
    prefix = cfg["test_prefix"]
    for f in tests_dir.glob(f"{prefix}*.py"):
        if stem in f.stem:
            return True
    return False


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "NotebookEdit"):
        return

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return

    root = find_project_root()
    cfg = load_config(root)
    if not cfg.get("enabled", True):
        return

    try:
        rel = os.path.relpath(file_path, root).replace("\\", "/")
    except Exception:
        rel = file_path

    if not archivo_necesita_test(rel, cfg):
        return
    if existe_test_para(rel, root, cfg):
        return

    aviso = (
        f"\n[TDD ENFORCER]\n"
        f"  Editando código productivo SIN test asociado:\n"
        f"  → {rel}\n"
        f"  No se encontró {cfg['tests_dir']}{cfg['test_prefix']}*<modulo>*.py\n"
        f"  Recordá: TDD recomendado.\n"
        f"  Flujo: 1) test que falla → 2) código mínimo → 3) refactor\n"
        f"  (Para desactivar: editá .claude/tdd-config.json o setea enabled=false)\n"
    )
    print(aviso, file=sys.stderr)


if __name__ == "__main__":
    main()
