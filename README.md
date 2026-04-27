# claude-code-starter

> Production-grade `.claude/` configuration for Claude Code. Hooks, slash commands, and sub-agents that protect your repo, enforce TDD, and capture knowledge — out of the box.

[![Tests](https://github.com/Hernan-Hamra/claude-code-starter/actions/workflows/tests.yml/badge.svg)](https://github.com/Hernan-Hamra/claude-code-starter/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

---

## What this gives you

Drop-in `.claude/` directory with **4 hooks**, **5 slash commands**, **3 sub-agents** — all designed for any Python or polyglot project. Zero coupling to a specific stack or DB.

| Layer | Purpose | Files |
|---|---|---|
| **Hooks** | Block dangerous commands, capture session knowledge, enforce TDD | `bash_gate`, `write_gate`, `tdd_enforcer`, `session_capture` |
| **Commands** | Reusable workflows (`/tdd`, `/audit`, `/dev-status`, `/pre-commit-check`, `/release-notes`) | 5 markdown files |
| **Agents** | Specialized sub-agents (test-runner, repo-cleanup, doc-syncer) | 3 markdown files |

---

## Why use this

Vanilla Claude Code is powerful but easy to misconfigure. You probably want:

1. **Safety:** stop Claude from `rm -rf /`, force-pushing to main, or writing `.env` files.
2. **Discipline:** get a nudge when editing production code without tests.
3. **Memory:** capture decisions, conventions, and corrections without manual effort.
4. **Reusable workflows:** `/tdd`, `/audit`, `/release-notes` instead of typing recipes from memory.

This starter ships all of that. No DB, no API key, no external service. Just files.

---

## Install

```bash
# Clone next to your repo (or into ~/.claude for global use)
git clone https://github.com/<you>/claude-code-starter.git
cp -r claude-code-starter/.claude ./your-project/

# (Optional) Customize TDD watch paths
cp claude-code-starter/.claude/tdd-config.example.json your-project/.claude/tdd-config.json

# (Optional) Enable session capture sink
mkdir -p your-project/.claude
touch your-project/.claude/captures.jsonl
```

Then in your `.claude/settings.json` (or merge with what you have):

```json
{
  "permissions": {
    "defaultMode": "ask",
    "deny": [
      "Bash(rm -rf /:*)", "Bash(rm -rf ~:*)",
      "Bash(format:*)", "Bash(mkfs:*)",
      "Bash(curl*|*bash:*)"
    ]
  },
  "hooks": {
    "UserPromptSubmit": [
      { "matcher": "", "hooks": [
        { "type": "command", "command": "python .claude/hooks/session_capture.py" }
      ]}
    ],
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [
        { "type": "command", "command": "python .claude/hooks/bash_gate.py" }
      ]},
      { "matcher": "Edit|Write|NotebookEdit", "hooks": [
        { "type": "command", "command": "python .claude/hooks/write_gate.py" },
        { "type": "command", "command": "python .claude/hooks/tdd_enforcer.py" }
      ]}
    ]
  }
}
```

That's it. Restart Claude Code or run `/hooks` to verify they load.

---

## What each piece does

### Hooks

| Hook | Event | Purpose |
|---|---|---|
| [bash_gate.py](.claude/hooks/bash_gate.py) | PreToolUse Bash | Blocks `rm -rf /`, `git push --force` to main/master, `DROP TABLE`, `git reset --hard` without `[ok-reset]` marker, `dd of=/dev/sd*`, `chmod -R 777 /`. |
| [write_gate.py](.claude/hooks/write_gate.py) | PreToolUse Write/Edit | Blocks writes to `.env` (non-templates), `*.pem`, `*.key`, `id_rsa`, `secrets/`, `credentials.json`, `api_keys.json`. |
| [tdd_enforcer.py](.claude/hooks/tdd_enforcer.py) | PreToolUse Edit/Write | Warns (stderr, doesn't block) when editing production code without an associated `tests/test_<module>.py`. Configurable paths via `.claude/tdd-config.json`. |
| [session_capture.py](.claude/hooks/session_capture.py) | UserPromptSubmit | Captures prompts that contain rules/preferences/conventions to a JSONL file (`.claude/captures.jsonl`). Heuristic-based; optional Claude Haiku classifier. |

### Slash commands

| Command | What it does |
|---|---|
| `/tdd <feature>` | Walks you through the RED → GREEN → REFACTOR cycle. |
| `/audit` | Runs lint + type-check + tests + secrets scan. Reports GO/NO-GO. |
| `/dev-status` | Shows current branch state, open PRs, stale branches, TODO count. |
| `/pre-commit-check` | Verifies staged diff: no secrets, no sensitive files, lint passes. |
| `/release-notes [version]` | Generates Conventional-Commits-style release notes since last tag. |

### Sub-agents

| Agent | When to invoke |
|---|---|
| `test-runner` | Before commit/PR/deploy. Runs full test suite, reports GO/NO-GO. Auto-detects pytest/jest/vitest/go-test. |
| `repo-cleanup` | Periodically. Detects dead code, stale branches, unused deps, old TODOs. **Only proposes**; never deletes without OK. |
| `doc-syncer` | After feature work. Detects code changes, proposes which docs need updating. **Only proposes diffs**. |

---

## Configuration files

### `.claude/tdd-config.json` (optional)
```json
{
  "watch_paths": ["src/", "lib/", "app/"],
  "tests_dir": "tests/",
  "test_prefix": "test_",
  "exclude_patterns": ["__init__.py", "config.py", "fixtures/"],
  "enabled": true
}
```

### `.claude/session-capture.json` (optional)
```json
{
  "enabled": true,
  "sink": "jsonl",
  "sink_path": ".claude/captures.jsonl",
  "min_chars": 30,
  "trigger_keywords": ["always", "never", "preferimos", "convention", "regla"],
  "skip_prefixes": ["/", "!", "$"]
}
```

### `.claude/doc-sync.json` (optional, for doc-syncer agent)
```json
{
  "watchers": [
    { "trigger": "src/**/*.py", "sync_targets": ["README.md", "docs/API.md"], "tipo": "código backend" },
    { "trigger": "migrations/**/*.sql", "sync_targets": ["docs/SCHEMA.md"], "tipo": "schema DB" }
  ]
}
```

---

## What this is NOT

- **Not a Claude Code installer.** Get Claude Code from <https://claude.com/claude-code>.
- **Not a framework.** It's `.claude/` files. Copy what you want, ignore the rest.
- **Not stack-specific.** Hooks and commands work for any project that uses Python/Node/Go/Rust as long as you adapt the test runner.
- **Not a replacement for CI/CD.** Hooks run locally. CI is still your source of truth for protected branches.

---

## Roadmap

**v1 (current):**
- ✅ 4 hooks (bash_gate, write_gate, tdd_enforcer, session_capture)
- ✅ 5 slash commands
- ✅ 3 sub-agents
- ✅ Tests for hooks
- ✅ MIT License

**v2 (planned):**
- More language presets (Rust, Go specific test runners).
- SQLite sink for session_capture (in addition to JSONL).
- Pluggable LLM classifiers (OpenAI, local Ollama).
- More sub-agents: `dependency-auditor`, `migration-helper`.

---

## Contributing

Issues and PRs welcome. Keep contributions:
- Stack-agnostic where possible.
- Documented (README + inline comments).
- Tested (one test per behavior).
- No external dependencies beyond Python stdlib (and optional `anthropic`).

---

## Author

[Hernán Hamra](https://github.com/Hernan-Hamra) — Claude Code & MCP specialist.

For consulting on `.claude/` setup, MCP server hosting, and AI-augmented development workflows: hamrahernan@gmail.com.

---

## License

MIT — see [LICENSE](./LICENSE).

Inspired by patterns developed for the [ARGOS](https://github.com/Hernan-Hamra/argos) project. Generalized and stripped of project-specific coupling for public release.
