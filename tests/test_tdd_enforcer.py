"""Tests for tdd_enforcer.py — config-driven TDD nudge."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "tdd_enforcer.py"


def _run(payload, cwd=None):
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=10,
        cwd=str(cwd) if cwd else None,
    )
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace"), proc.stderr.decode("utf-8", errors="replace")


def _setup_project(tmp_path: Path, *, with_test_for: str = None, config: dict = None):
    """Crea un proyecto temporal con .git/ + src/ + tests/."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".claude").mkdir()
    if with_test_for:
        (tmp_path / "tests" / f"test_{with_test_for}.py").write_text("def test_x(): pass")
    if config:
        (tmp_path / ".claude" / "tdd-config.json").write_text(json.dumps(config))
    return tmp_path


def test_hook_existe():
    assert HOOK.exists()


def test_tool_no_relevante_no_avisa(tmp_path):
    proj = _setup_project(tmp_path)
    payload = {"tool_name": "Read", "tool_input": {"file_path": str(proj / "src" / "foo.py")}}
    rc, _, stderr = _run(payload, cwd=proj)
    assert rc == 0
    assert "TDD ENFORCER" not in stderr


def test_archivo_no_python_no_avisa(tmp_path):
    proj = _setup_project(tmp_path)
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(proj / "README.md")}}
    rc, _, stderr = _run(payload, cwd=proj)
    assert rc == 0
    assert "TDD ENFORCER" not in stderr


def test_archivo_excluido_init_no_avisa(tmp_path):
    proj = _setup_project(tmp_path)
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(proj / "src" / "__init__.py")}}
    rc, _, stderr = _run(payload, cwd=proj)
    assert rc == 0
    assert "TDD ENFORCER" not in stderr


def test_archivo_con_test_existente_no_avisa(tmp_path):
    proj = _setup_project(tmp_path, with_test_for="foo")
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(proj / "src" / "foo.py")}}
    rc, _, stderr = _run(payload, cwd=proj)
    assert rc == 0
    assert "TDD ENFORCER" not in stderr


def test_archivo_sin_test_avisa(tmp_path):
    proj = _setup_project(tmp_path)
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(proj / "src" / "modulo_sin_test.py")}}
    rc, _, stderr = _run(payload, cwd=proj)
    assert rc == 0
    assert "TDD ENFORCER" in stderr


def test_disabled_via_config(tmp_path):
    proj = _setup_project(tmp_path, config={"enabled": False})
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(proj / "src" / "modulo_xyz.py")}}
    rc, _, stderr = _run(payload, cwd=proj)
    assert rc == 0
    assert "TDD ENFORCER" not in stderr


def test_custom_watch_paths(tmp_path):
    """Si el config solo vigila lib/, src/ no debe avisar."""
    proj = _setup_project(tmp_path, config={"watch_paths": ["lib/"]})
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(proj / "src" / "modulo_xyz.py")}}
    rc, _, stderr = _run(payload, cwd=proj)
    assert rc == 0
    assert "TDD ENFORCER" not in stderr


def test_input_invalido_no_falla():
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=b"not-json",
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode == 0
