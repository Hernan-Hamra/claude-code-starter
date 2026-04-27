"""Tests for session_capture.py — captures preferences/conventions to JSONL."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "session_capture.py"


def _run(payload, cwd=None):
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=10,
        cwd=str(cwd) if cwd else None,
    )
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace"), proc.stderr.decode("utf-8", errors="replace")


def _setup_project(tmp_path: Path, *, config: dict = None):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".claude").mkdir()
    if config:
        (tmp_path / ".claude" / "session-capture.json").write_text(json.dumps(config))
    return tmp_path


def test_hook_existe():
    assert HOOK.exists()


def test_input_vacio_no_falla(tmp_path):
    proj = _setup_project(tmp_path)
    rc, _, _ = _run({"prompt": ""}, cwd=proj)
    assert rc == 0


def test_prompt_corto_no_captura(tmp_path):
    proj = _setup_project(tmp_path)
    rc, _, _ = _run({"prompt": "hola"}, cwd=proj)
    assert rc == 0
    captures = proj / ".claude" / "captures.jsonl"
    assert not captures.exists() or captures.read_text().strip() == ""


def test_prompt_sin_keyword_no_captura(tmp_path):
    proj = _setup_project(tmp_path)
    long_prompt = "Necesito que arreglés este bug en el módulo de pagos por favor"
    rc, _, _ = _run({"prompt": long_prompt}, cwd=proj)
    assert rc == 0
    captures = proj / ".claude" / "captures.jsonl"
    assert not captures.exists() or captures.read_text().strip() == ""


def test_prompt_con_keyword_captura(tmp_path):
    proj = _setup_project(tmp_path)
    long_prompt = "Siempre usá pytest, nunca unittest. Convención del equipo desde el sprint pasado."
    rc, _, stderr = _run({"prompt": long_prompt}, cwd=proj)
    assert rc == 0
    captures = proj / ".claude" / "captures.jsonl"
    assert captures.exists()
    lines = captures.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1
    record = json.loads(lines[0])
    assert "siempre" in record["prompt"].lower() or "nunca" in record["prompt"].lower()


def test_slash_command_skipped(tmp_path):
    """Mensajes que arrancan con /, !, $ no se capturan."""
    proj = _setup_project(tmp_path)
    rc, _, _ = _run({"prompt": "/audit siempre y cuando esto cumpla la regla del proyecto entero"}, cwd=proj)
    assert rc == 0
    captures = proj / ".claude" / "captures.jsonl"
    assert not captures.exists() or captures.read_text().strip() == ""


def test_disabled_via_config(tmp_path):
    proj = _setup_project(tmp_path, config={"enabled": False})
    rc, _, _ = _run({"prompt": "Siempre usá pytest, nunca unittest, convención del equipo"}, cwd=proj)
    assert rc == 0
    captures = proj / ".claude" / "captures.jsonl"
    assert not captures.exists() or captures.read_text().strip() == ""


def test_custom_keywords(tmp_path):
    """Con un keyword custom, otro prompt sin las default keywords debería capturarse."""
    proj = _setup_project(tmp_path, config={"trigger_keywords": ["lavanda"]})
    rc, _, _ = _run({"prompt": "El nuevo deploy usa lavanda como nombre clave para el cluster"}, cwd=proj)
    assert rc == 0
    captures = proj / ".claude" / "captures.jsonl"
    assert captures.exists()


def test_input_invalido_no_falla():
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=b"not-json",
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode == 0


def test_capturas_son_jsonl_validas(tmp_path):
    proj = _setup_project(tmp_path)
    rc, _, _ = _run({"prompt": "Siempre usá pytest, nunca unittest, convención del equipo"}, cwd=proj)
    assert rc == 0
    captures = proj / ".claude" / "captures.jsonl"
    for line in captures.read_text(encoding="utf-8").strip().split("\n"):
        rec = json.loads(line)
        assert "ts" in rec
        assert "prompt" in rec
        assert "categoria" in rec
        assert rec["source"] == "claude-code-starter:session_capture"
