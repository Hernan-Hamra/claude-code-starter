"""Tests for bash_gate.py — blocks catastrophic Bash commands."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "bash_gate.py"


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


def test_comando_inocente_no_bloquea():
    rc, out = _run({"tool_input": {"command": "ls -la"}})
    assert rc == 0
    assert not _is_blocked(out)


def test_rm_rf_root_bloqueado():
    rc, out = _run({"tool_input": {"command": "rm -rf /"}})
    assert rc == 0
    assert _is_blocked(out)


def test_rm_rf_home_bloqueado():
    rc, out = _run({"tool_input": {"command": "rm -rf ~/"}})
    assert rc == 0
    assert _is_blocked(out)


def test_rm_rf_local_no_bloqueado():
    """rm -rf ./build NO debe bloquearse — es legítimo."""
    rc, out = _run({"tool_input": {"command": "rm -rf ./build"}})
    assert rc == 0
    assert not _is_blocked(out)


def test_git_push_force_main_bloqueado():
    rc, out = _run({"tool_input": {"command": "git push --force origin main"}})
    assert rc == 0
    assert _is_blocked(out)


def test_git_push_force_feature_no_bloqueado():
    """git push --force a una feature branch SÍ debe permitirse."""
    rc, out = _run({"tool_input": {"command": "git push --force origin feature/xyz"}})
    assert rc == 0
    assert not _is_blocked(out)


def test_drop_table_bloqueado():
    rc, out = _run({"tool_input": {"command": 'psql -c "DROP TABLE users"'}})
    assert rc == 0
    assert _is_blocked(out)


def test_drop_database_bloqueado():
    rc, out = _run({"tool_input": {"command": 'psql -c "DROP DATABASE prod"'}})
    assert rc == 0
    assert _is_blocked(out)


def test_drop_index_no_bloqueado():
    """DROP INDEX/COLUMN NO está bloqueado — son operaciones rutinarias."""
    rc, out = _run({"tool_input": {"command": 'psql -c "DROP INDEX idx_foo"'}})
    assert rc == 0
    assert not _is_blocked(out)


def test_git_reset_hard_sin_marcador_bloqueado():
    rc, out = _run({"tool_input": {"command": "git reset --hard HEAD~5"}})
    assert rc == 0
    assert _is_blocked(out)


def test_git_reset_hard_con_marcador_no_bloqueado():
    rc, out = _run({"tool_input": {"command": "git reset --hard origin/main # [ok-reset] migracion"}})
    assert rc == 0
    assert not _is_blocked(out)


def test_dd_a_disco_bloqueado():
    rc, out = _run({"tool_input": {"command": "dd if=/dev/zero of=/dev/sda bs=1M"}})
    assert rc == 0
    assert _is_blocked(out)


def test_chmod_777_root_bloqueado():
    rc, out = _run({"tool_input": {"command": "chmod -R 777 /"}})
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


def test_payload_sin_command_no_falla():
    rc, out = _run({"tool_input": {}})
    assert rc == 0
