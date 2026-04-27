---
description: TDD wizard — escribí test que falle, después código que pase
argument-hint: [feature_name]
---

Apliquemos TDD para `$ARGUMENTS`.

**Paso 1 — RED (test que falla):**
1. Crear archivo `tests/test_$ARGUMENTS.py` con tests del comportamiento esperado.
2. Correr: `python -m pytest tests/test_$ARGUMENTS.py -v` (o `npm test -- $ARGUMENTS`, según stack).
3. Verificar que FALLA. Si pasa al primer intento, el test es trivial — reescribirlo.

**Paso 2 — GREEN (código mínimo que pasa):**
4. Escribir/editar el código mínimo necesario.
5. Re-correr tests: deben pasar.

**Paso 3 — REFACTOR:**
6. Mejorar el código sin romper tests.
7. Tests deben seguir pasando.

**Paso 4 — Commit:**
8. Test + código en el mismo commit.

**Reglas:**
- Nunca escribir código antes que el test (anti-patrón "test-after").
- Cada test verifica UN comportamiento.
- Casos edge: NULL, vacío, error, límites.

**Aplicar a:** funciones públicas, endpoints API, lógica de negocio, fixes de bug
reproducible.
**No aplicar a:** templates HTML, configs, fixtures, código de glue trivial.
