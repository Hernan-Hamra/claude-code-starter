# Hooks — guía de uso

4 hooks vienen con el starter. Todos son fail-safe (no bloquean Claude Code si fallan internamente) y autónomos (sin DB, sin API key obligatoria).

## bash_gate.py

**Evento:** `PreToolUse` con matcher `Bash`.
**Acción:** bloquea (decisión `deny`) comandos catastróficos.

### Bloquea

| Patrón | Ejemplo |
|---|---|
| `rm -rf` en raíz/home | `rm -rf /`, `rm -rf ~`, `rm -rf $HOME` |
| `git push --force` a rama protegida | `git push --force origin main` |
| `DROP TABLE/DATABASE/SCHEMA` | `psql -c "DROP TABLE users"` |
| `git reset --hard` sin marcador | `git reset --hard HEAD~5` (necesita `[ok-reset]` en el comando) |
| `dd of=/dev/sd*` | escribir directo a disco físico |
| `chmod -R 777` en raíz/home | `chmod -R 777 /` |

### Cómo bypass (intencional)
Para `git reset --hard` legítimo:
```bash
git reset --hard origin/main  # [ok-reset] migrating to upstream state
```

Para los demás: ejecutalos fuera de Claude Code.

---

## write_gate.py

**Evento:** `PreToolUse` con matcher `Edit|Write|NotebookEdit`.
**Acción:** bloquea escritura a archivos sensibles.

### Bloquea

- `.env`, `.env.production`, `.env.local` (excepto `.env.example`, `.env.template`, `.env.sample`, `.env.dist`)
- `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.crt`, `*.cer`
- `id_rsa`, `id_ed25519`, `id_ecdsa`, `id_dsa` (con o sin `.pub`)
- `*.private`
- `secrets/`, `.secrets/`, `credentials/`, `credenciales/`
- `credentials.json`, `secrets.json`, `api_keys.json`, `tokens.yaml`

### Cómo agregar uno

Editá `bash_gate.py` (no, perdón, `write_gate.py`) — la lista `PATRONES_BLOQUEADOS` es regex. Por ejemplo, para bloquear `.kubeconfig`:

```python
(r"\.kubeconfig$", "kubeconfig with cluster credentials"),
```

---

## tdd_enforcer.py

**Evento:** `PreToolUse` con matcher `Edit|Write|NotebookEdit`.
**Acción:** **avisa** (stderr) si editás producción sin test asociado. **No bloquea.**

### Cómo configurar

Crear `.claude/tdd-config.json`:

```json
{
  "watch_paths": ["src/", "lib/"],
  "tests_dir": "tests/",
  "test_prefix": "test_",
  "exclude_patterns": ["__init__.py", "config.py"],
  "enabled": true
}
```

Por defecto vigila `src/`, `lib/`, `app/`, `tools/`.

### Cómo desactivar
Setear `"enabled": false` en el config, o quitar el hook del `settings.json`.

### Cómo silenciar para un archivo
Agregar el path a `exclude_patterns`.

---

## session_capture.py

**Evento:** `UserPromptSubmit`.
**Acción:** detecta prompts del usuario que parecen contener reglas/preferencias/convenciones y los guarda en JSONL para revisión.

### Heurística

Captura si el prompt:
- Tiene ≥30 caracteres.
- No empieza con `/`, `!`, `$` (slash commands, bang commands, env exports).
- Contiene alguna de estas keywords (configurable):
  - `siempre`, `nunca`, `preferimos`, `from now on`, `always`, `never`, `do not`, etc.

### Sink

Por defecto: JSONL en `.claude/captures.jsonl`. Cada línea un record:

```json
{"ts": "2026-04-26T23:42:00", "session_id": "abc-123", "prompt": "Siempre usá pytest, nunca unittest.", "categoria": "heuristica", "source": "claude-code-starter:session_capture"}
```

### Clasificador opcional con Haiku

Si querés que Claude Haiku confirme antes de guardar (filtra falsos positivos):

```json
{
  "classifier": "anthropic_haiku"
}
```

Necesitás:
- `pip install anthropic`
- `export ANTHROPIC_API_KEY=sk-ant-...`

Costo estimado: ~$0.0005 por captura. Sin keywords → no llama al LLM (free path).

### Cómo revisar las capturas
```bash
# Ver todas
cat .claude/captures.jsonl | jq .

# Solo las de hoy
grep "$(date +%Y-%m-%d)" .claude/captures.jsonl | jq .

# Las clasificadas como "convención"
jq 'select(.categoria=="convencion")' .claude/captures.jsonl
```

---

## Performance

Todos los hooks corren `<3s` en path rápido. El más pesado es `session_capture` con classifier Haiku (~1-2s extra por llamada al LLM).

Si tu hook se siente lento:
- Verificá que no estés haciendo I/O bloqueante.
- Usá disk cache para schemas / config (TTL 5 min).
- Desactivá Haiku classifier si no lo necesitás (ya tenés keyword filtering).

---

## Cómo escribir tu propio hook

Plantilla mínima:

```python
#!/usr/bin/env python
import json
import sys

def main():
    try:
        # CRÍTICO en Windows: leer bytes y decodificar UTF-8 explícito.
        # json.load(sys.stdin) usa cp1252 por default y rompe ñ/á/é.
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw.decode('utf-8'))
    except Exception:
        sys.exit(0)  # fail-safe

    # ...tu lógica acá...

    sys.exit(0)  # 0 = OK, 2 = bloquear

if __name__ == "__main__":
    main()
```

**Reglas que aprendimos peleando con Claude Code:**

1. **Siempre fail-safe.** Excepción → `sys.exit(0)`. Romper Claude Code es peor que no validar.
2. **Lee stdin como bytes + decode UTF-8.** En Windows `json.load(sys.stdin)` usa cp1252 y corrompe acentos.
3. **<3s en path rápido.** Si tu hook necesita DB/red, usá disk cache.
4. **No imprimas a stdout salvo que tu hook explícitamente decida algo.** stdout llega al modelo; ruido = peor performance.
5. **stderr es para warnings.** Tu mensaje aparece en la consola del usuario sin contaminar el contexto del LLM.
