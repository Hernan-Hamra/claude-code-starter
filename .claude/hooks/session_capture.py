"""
Session Capture — Hook UserPromptSubmit genérico.

Captura prompts del usuario que parecen contener "aprendizajes" (correcciones,
preferencias, decisiones arquitectónicas) y los guarda en un sink configurable
para revisión posterior.

CONFIG-DRIVEN: lee `.claude/session-capture.json` desde la raíz del proyecto.
Estructura esperada:
{
  "enabled": true,
  "sink": "jsonl",                 // "jsonl" | "sqlite" | "callback"
  "sink_path": ".claude/captures.jsonl",
  "min_chars": 30,
  "trigger_keywords": [
     "no hagas", "siempre", "nunca", "preferimos",
     "from now on", "always", "never", "do not"
  ],
  "skip_prefixes": ["/", "!", "$"]
}

Por defecto usa sink JSONL en `.claude/captures.jsonl` (sin DB, sin LLM, gratis).

Si querés clasificación con LLM (ej Claude Haiku) ANTES de guardar, agregá
`"classifier": "anthropic_haiku"` y exporta `ANTHROPIC_API_KEY`. Si la lib
`anthropic` no está instalada, se ignora silenciosamente.

NUNCA bloquea el turno (exit 0 siempre).

Patrón portado desde ARGOS ~/.claude/hooks/em5_capturar_aprendizaje.py.
Generalizado para `claude-code-starter`.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

DEFAULTS = {
    "enabled": True,
    "sink": "jsonl",
    "sink_path": ".claude/captures.jsonl",
    "min_chars": 30,
    "trigger_keywords": [
        "no hagas", "siempre", "nunca", "preferimos", "preferí", "preferi",
        "from now on", "always", "never", "do not", "don't", "we prefer",
        "convención", "convencion", "convention", "policy", "regla",
    ],
    "skip_prefixes": ["/", "!", "$"],
    "classifier": None,
}


def find_project_root() -> Path:
    p = Path.cwd().resolve()
    for parent in (p, *p.parents):
        if any((parent / m).exists() for m in (".git", "pyproject.toml", "package.json")):
            return parent
    return p


def load_config(root: Path) -> dict:
    cfg_path = root / ".claude" / "session-capture.json"
    if not cfg_path.exists():
        return DEFAULTS
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            user = json.load(f)
    except Exception:
        return DEFAULTS
    return {**DEFAULTS, **user}


def heuristica_disparo(prompt: str, cfg: dict) -> bool:
    """Match rápido: si no hay keyword, no llama clasificador."""
    p = prompt.lower()
    if any(p.startswith(pref) for pref in cfg["skip_prefixes"]):
        return False
    if len(prompt) < cfg["min_chars"]:
        return False
    return any(kw in p for kw in cfg["trigger_keywords"])


def clasificar_anthropic(prompt: str) -> tuple[bool, str]:
    """Si está disponible, llama Claude Haiku para confirmar si vale capturar.

    Devuelve (capturar, clasificacion) — clasificacion ej: "convención", "preferencia".
    Fail-safe: cualquier error → (False, "").
    """
    try:
        import anthropic  # type: ignore
    except ImportError:
        return False, ""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False, ""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=80,
            messages=[{
                "role": "user",
                "content": (
                    "¿Este mensaje contiene una preferencia/convención/regla "
                    "del usuario que valga registrar como aprendizaje del proyecto? "
                    "Responde estrictamente: SI:<categoria> o NO. "
                    "Categorias: preferencia | convencion | regla | decision_arquitectonica.\n\n"
                    f"Mensaje: {prompt[:1000]}"
                ),
            }],
        )
        text = resp.content[0].text.strip() if resp.content else ""
        if text.upper().startswith("SI:"):
            return True, text.split(":", 1)[1].strip().lower()
        return False, ""
    except Exception:
        return False, ""


def escribir_sink_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    try:
        raw = sys.stdin.buffer.read()
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        sys.exit(0)

    prompt = (
        data.get("prompt")
        or data.get("user_message")
        or data.get("message")
        or ""
    )
    if not prompt or not prompt.strip():
        sys.exit(0)

    root = find_project_root()
    cfg = load_config(root)
    if not cfg.get("enabled", True):
        sys.exit(0)

    if not heuristica_disparo(prompt, cfg):
        sys.exit(0)

    categoria = "heuristica"
    if cfg.get("classifier") == "anthropic_haiku":
        capturar, cat = clasificar_anthropic(prompt)
        if not capturar:
            sys.exit(0)
        categoria = cat or "heuristica"

    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "session_id": data.get("session_id"),
        "prompt": prompt[:2000],  # truncamos para no inflar el sink
        "categoria": categoria,
        "source": "claude-code-starter:session_capture",
    }

    sink = cfg.get("sink", "jsonl")
    if sink == "jsonl":
        sink_path = root / cfg["sink_path"]
        try:
            escribir_sink_jsonl(sink_path, record)
            print(
                f"[session_capture] aprendizaje #{int(time.time())} → {sink_path}",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"[session_capture] sink jsonl falló: {e}", file=sys.stderr)
    # otros sinks (sqlite, callback) quedan para starter v2

    sys.exit(0)


if __name__ == "__main__":
    main()
