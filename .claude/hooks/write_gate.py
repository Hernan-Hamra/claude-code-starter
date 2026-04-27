#!/usr/bin/env python
"""
PreToolUse hook para Write/Edit/NotebookEdit.
Bloquea (exit 2) escritura en archivos sensibles.

Patrones bloqueados:
- .env, .env.* (excepto .env.example, .env.template, .env.sample)
- *.pem, *.key, *.p12, *.pfx
- secrets/, .secrets/, credentials/
- credenciales*, credentials.json, secrets.json
- id_rsa, id_ed25519, *.private

Lee JSON de stdin con tool_input.file_path.
Output JSON: {"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": "..."}}
"""
import json
import re
import sys
from pathlib import PurePath


PATRONES_BLOQUEADOS = [
    # Variables de entorno (excepto plantillas)
    (r"(^|[/\\])\.env$", "archivo .env (secrets de entorno)"),
    (r"(^|[/\\])\.env\.(?!example|template|sample|dist)[\w\-]+$", "variante de .env con secrets"),
    # Llaves criptograficas
    (r"\.(pem|key|p12|pfx|crt|cer)$", "archivo de credenciales/llaves"),
    (r"(^|[/\\])id_(rsa|ed25519|ecdsa|dsa)(\.pub)?$", "llave SSH"),
    (r"\.private$", "archivo marcado como privado"),
    # Carpetas de secrets
    (r"(^|[/\\])(\.?secrets?|credentials?|credenciales)([/\\]|$)", "carpeta de secrets/credenciales"),
    # Archivos de credenciales conocidos
    (r"(^|[/\\])credenciales[\w\-\.]*\.(json|yaml|yml|toml|env)$", "archivo de credenciales"),
    (r"(^|[/\\])credentials\.(json|yaml|yml|toml)$", "archivo de credenciales"),
    (r"(^|[/\\])secrets?\.(json|yaml|yml|toml)$", "archivo de secrets"),
    # Tokens/API keys
    (r"(^|[/\\])(api[_-]?keys?|tokens?)\.(json|yaml|yml|toml|txt)$", "archivo de tokens/API keys"),
]


def es_sensible(path: str) -> tuple[bool, str]:
    """Devuelve (bloqueado, razon)."""
    if not path:
        return False, ""
    # Normalizar separadores para que regex funcione cross-platform
    p = path.replace("\\", "/")
    # Solo nombre + 2 niveles de carpeta para chequeo rapido
    for patron, razon in PATRONES_BLOQUEADOS:
        if re.search(patron, p, re.IGNORECASE):
            return True, razon
    return False, ""


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # no bloqueamos si no podemos parsear

    tool_input = payload.get("tool_input", {}) or {}
    # Edit/Write usan file_path, NotebookEdit usa notebook_path
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""

    bloqueado, razon = es_sensible(path)
    if bloqueado:
        decision = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"WRITE_GATE: bloqueado escribir en archivo sensible ({razon}): {path}. "
                    f"Si es intencional, hacelo manualmente fuera de Claude Code."
                ),
            }
        }
        sys.stdout.write(json.dumps(decision))
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
