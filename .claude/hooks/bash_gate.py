#!/usr/bin/env python
"""
PreToolUse hook para Bash.
Bloquea (deny) comandos catastroficos. SCOPE QUIRURGICO: solo 4 patrones.

1. rm -rf / o rm -rf ~ (no rm -rf ./build)
2. git push --force a main/master (no en feature branches)
3. DROP TABLE / DROP DATABASE (no DROP COLUMN/INDEX)
4. git reset --hard sin marcador [ok-reset]

Lee JSON de stdin con tool_input.command.
Output JSON: {"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": "..."}}
"""
import json
import re
import sys


def chequear(cmd: str) -> tuple[bool, str]:
    """Devuelve (bloqueado, razon). Razon vacia si no bloquea."""
    if not cmd:
        return False, ""

    # Normalizar: una linea, espacios colapsados (pero preservando contenido)
    c = cmd.strip()

    # 1. rm -rf / | rm -rf ~ | rm -rf $HOME | rm -rf /* | rm -rf ~/
    #    Capturamos rm con -r y -f (en cualquier orden) seguido de raiz peligrosa
    if re.search(r"\brm\s+(-[rRfd]+\s+)*-[rRfd]*[rR][rRfd]*\s+(-[rRfd]+\s+)*[/~]\s*\*?(\s|$)", c) \
       or re.search(r"\brm\s+(-[rRfd]+\s+)+\$HOME(/\*)?(\s|$)", c) \
       or re.search(r"\brm\s+(-[rRfd]+\s+)+~/?\s*\*?(\s|$)", c):
        # Pero solo si tambien tiene -f (la combinacion peligrosa es -rf)
        if re.search(r"\brm\s+[^\n]*-[a-zA-Z]*f", c) or re.search(r"\brm\s+[^\n]*--force", c):
            return True, "rm -rf en raiz del FS o $HOME"

    # 1b. Variante explicita: rm -rf / sin nada mas o seguido de espacio/fin
    if re.search(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(\s|$|\*)", c) \
       or re.search(r"\brm\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\s+/(\s|$|\*)", c):
        return True, "rm -rf / (raiz del filesystem)"

    # 2. git push --force a main/master (acepta -f, --force, --force-with-lease)
    if re.search(r"\bgit\s+push\b", c) and \
       re.search(r"(--force(-with-lease)?|--?-?f\b|\s-f\b)", c) and \
       re.search(r"\b(main|master|production|prod)\b", c):
        return True, "git push --force a rama protegida (main/master/production)"

    # 3. DROP TABLE / DROP DATABASE (case-insensitive, no DROP INDEX/COLUMN/CONSTRAINT)
    if re.search(r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", c, re.IGNORECASE):
        return True, "DROP TABLE/DATABASE/SCHEMA en SQL"

    # 4. git reset --hard sin marcador de override
    if re.search(r"\bgit\s+reset\s+--hard\b", c) and "[ok-reset]" not in c:
        return True, "git reset --hard sin marcador [ok-reset] en el comando (agregalo si es intencional)"

    # 5. Bonus: dd if=... of=/dev/sd* (escribir directo a disco)
    if re.search(r"\bdd\s+[^\n]*of=/dev/sd[a-z]", c):
        return True, "dd escribiendo a disco fisico (/dev/sd*)"

    # 6. Bonus: chmod -R 777 / o ~
    if re.search(r"\bchmod\s+-R\s+777\s+[/~]\s*$", c):
        return True, "chmod -R 777 en raiz/home"

    return False, ""


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = payload.get("tool_input", {}) or {}
    cmd = tool_input.get("command", "") or ""

    bloqueado, razon = chequear(cmd)
    if bloqueado:
        decision = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"BASH_GATE: comando catastrofico bloqueado ({razon}).\n"
                    f"Comando: {cmd[:200]}\n"
                    f"Si es intencional, ejecutalo manualmente fuera de Claude Code."
                ),
            }
        }
        sys.stdout.write(json.dumps(decision))
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
