"""Tests for write_gate.py — blocks writes to sensitive files."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "write_gate.py"


def _run(payload):
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=10,
    )
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace")


def _is_blocked(stdout):
    if not stdout.strip():
        return False
    try:
        data = json.loads(stdout)
        return data.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
    except Exception:
        return False


def test_hook_existe():
    assert HOOK.exists()


def test_archivo_normal_no_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "src/foo.py"}})
    assert rc == 0
    assert not _is_blocked(out)


def test_dot_env_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "/repo/.env"}})
    assert rc == 0
    assert _is_blocked(out)


def test_dot_env_production_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "/repo/.env.production"}})
    assert rc == 0
    assert _is_blocked(out)


def test_dot_env_example_no_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "/repo/.env.example"}})
    assert rc == 0
    assert not _is_blocked(out)


def test_dot_env_template_no_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "/repo/.env.template"}})
    assert rc == 0
    assert not _is_blocked(out)


def test_pem_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "certs/server.pem"}})
    assert rc == 0
    assert _is_blocked(out)


def test_key_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "certs/server.key"}})
    assert rc == 0
    assert _is_blocked(out)


def test_id_rsa_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "/home/user/.ssh/id_rsa"}})
    assert rc == 0
    assert _is_blocked(out)


def test_id_ed25519_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "/home/user/.ssh/id_ed25519"}})
    assert rc == 0
    assert _is_blocked(out)


def test_secrets_dir_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "secrets/api.json"}})
    assert rc == 0
    assert _is_blocked(out)


def test_credentials_json_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "/repo/credentials.json"}})
    assert rc == 0
    assert _is_blocked(out)


def test_api_keys_json_bloqueado():
    rc, out = _run({"tool_input": {"file_path": "config/api_keys.json"}})
    assert rc == 0
    assert _is_blocked(out)


def test_notebook_path_tambien_bloqueado():
    """NotebookEdit usa notebook_path en vez de file_path."""
    rc, out = _run({"tool_input": {"notebook_path": "secrets/data.ipynb"}})
    assert rc == 0
    assert _is_blocked(out)


def test_input_invalido_no_falla():
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=b"not-json",
        capture_output=True,
        timeout=10,
    )
    assert proc.returncode == 0


def test_payload_sin_path_no_falla():
    rc, out = _run({"tool_input": {}})
    assert rc == 0
    assert not _is_blocked(out)
