# PyRIT MCP Server — Installation Guide

Complete installation and setup instructions for running the PyRIT MCP server
locally with VS Code (Claude Code extension and GitHub Copilot), Claude Desktop,
or as a standalone Python process.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1 — Clone the Repository](#step-1--clone-the-repository)
- [Step 2 — Python Environment Setup](#step-2--python-environment-setup)
- [Step 3 — Environment Configuration](#step-3--environment-configuration)
- [Step 4 — Verify the Server Starts](#step-4--verify-the-server-starts)
- [VS Code Setup — Claude Code Extension](#vs-code-setup--claude-code-extension)
- [VS Code Setup — GitHub Copilot (MCP)](#vs-code-setup--github-copilot-mcp)
- [Claude Desktop Setup](#claude-desktop-setup)
- [Docker Setup (Alternative)](#docker-setup-alternative)
- [Troubleshooting](#troubleshooting)
- [Verifying Your Installation](#verifying-your-installation)
- [Uninstalling](#uninstalling)

---

## Prerequisites

Before you begin, ensure you have the following installed:

| Requirement        | Minimum Version | Check Command            |
|--------------------|-----------------|--------------------------|
| Python             | 3.10+           | `python --version`       |
| pip                | 21.0+           | `pip --version`          |
| Git                | any             | `git --version`          |
| VS Code            | 1.85+           | `code --version`         |

**Platform support:** Windows 10/11, macOS 12+, Linux (Ubuntu 20.04+, Fedora 36+).

> **Python 3.13 note:** The server's test suite runs on Python 3.13, but the
> PyRIT library itself currently requires Python < 3.13. If you plan to use
> PyRIT's full capabilities (not just the MCP wrapper), use Python 3.10–3.12.

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/ncasfl/Pyrit-MCP.git
cd Pyrit-MCP
```

---

## Step 2 — Python Environment Setup

### Create a virtual environment

Always use a virtual environment to isolate dependencies from your system Python.

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Windows (Git Bash / MSYS2):**
```bash
python -m venv .venv
source .venv/Scripts/activate
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install the package

Install in editable (development) mode so changes to the source are reflected immediately:

```bash
pip install -e ".[dev]"
```

If the `[dev]` extras are not defined, install the base package and dev dependencies separately:

```bash
pip install -e .
pip install pytest pytest-asyncio pytest-cov ruff mypy
```

### Verify installation

```bash
# The CLI entry point should now be available:
pyrit-mcp --help

# Or run as a Python module:
python -m pyrit_mcp.server --help
```

---

## Step 3 — Environment Configuration

The server reads its configuration from environment variables, typically loaded from a `.env` file.

### Create your .env file

```bash
cp .env.example .env
```

### Minimal configuration (sandbox mode)

For initial setup and testing, use sandbox mode which does not send real HTTP requests:

```ini
# .env — minimal sandbox configuration
PYRIT_SANDBOX_MODE=true
PYRIT_LOG_LEVEL=INFO
PYRIT_DB_PATH=./pyrit_data.db

ATTACKER_BACKEND=ollama
ATTACKER_BASE_URL=http://localhost:11434
ATTACKER_MODEL=dolphin-mistral

SCORER_BACKEND=substring
```

### Configuration with real backends

For production use, configure your attacker and scorer backends. See `.env.example` for all options. Key settings:

| Variable              | Purpose                                               | Example                          |
|-----------------------|-------------------------------------------------------|----------------------------------|
| `ATTACKER_BACKEND`    | Backend for adversarial prompt generation              | `ollama`, `openai`, `azure`      |
| `ATTACKER_MODEL`      | Model name or deployment ID                            | `dolphin-mistral`, `gpt-4o`      |
| `ATTACKER_BASE_URL`   | Backend API URL                                        | `http://localhost:11434`         |
| `ATTACKER_API_KEY_ENV` | Name of env var holding the API key                   | `OPENAI_API_KEY`                 |
| `SCORER_BACKEND`      | Backend for response scoring                           | `openai`, `substring`, `classifier` |
| `SCORER_MODEL`        | Scorer model name                                      | `gpt-4o`                        |
| `PYRIT_SANDBOX_MODE`  | `true` = dry-run mode, no real requests                | `true` or `false`               |

> **Security:** API keys are referenced by env var name (e.g., `ATTACKER_API_KEY_ENV=MY_KEY`),
> never passed as raw values in tool parameters. This prevents keys from appearing in MCP conversation logs.

---

## Step 4 — Verify the Server Starts

Test that the server starts correctly before configuring your IDE:

```bash
# Set environment variables (or use .env):
# On Linux/macOS:
export PYRIT_SANDBOX_MODE=true

# On Windows PowerShell:
$env:PYRIT_SANDBOX_MODE = "true"

# Start the server (it will listen on stdio and block):
pyrit-mcp
```

You should see log output on stderr like:

```
12:34:56 INFO     pyrit_mcp.server — PyRIT MCP Server v0.1.0 starting
12:34:56 INFO     pyrit_mcp.server — Attacker: ollama / dolphin-mistral | Scorer: substring / n/a | Sandbox: True
12:34:56 INFO     pyrit_mcp.server — Database initialised at ./pyrit_data.db
12:34:56 INFO     pyrit_mcp.server — MCP server ready — listening on stdio
```

Press `Ctrl+C` to stop the server once you have confirmed it starts.

---

## VS Code Setup — Claude Code Extension

The [Claude Code extension](https://marketplace.visualstudio.com/items?itemName=anthropics.claude-code) for VS Code supports MCP servers natively.

### Step 1 — Install the extension

1. Open VS Code
2. Go to Extensions (`Ctrl+Shift+X` / `Cmd+Shift+X`)
3. Search for **"Claude Code"** by Anthropic
4. Click **Install**

### Step 2 — Configure the MCP server

Claude Code uses a `claude_desktop_config.json` or project-level `.mcp.json` file for MCP server configuration.

#### Option A: Project-level configuration (recommended)

Create a `.mcp.json` file in your project root:

```json
{
  "mcpServers": {
    "pyrit": {
      "command": "pyrit-mcp",
      "env": {
        "PYRIT_SANDBOX_MODE": "true",
        "PYRIT_LOG_LEVEL": "INFO",
        "PYRIT_DB_PATH": "./pyrit_data.db",
        "ATTACKER_BACKEND": "ollama",
        "ATTACKER_BASE_URL": "http://localhost:11434",
        "ATTACKER_MODEL": "dolphin-mistral",
        "SCORER_BACKEND": "substring"
      }
    }
  }
}
```

> **Note:** If you installed in a virtual environment, use the full path to the
> `pyrit-mcp` executable instead:

**Windows:**
```json
{
  "mcpServers": {
    "pyrit": {
      "command": "C:/path/to/Pyrit-MCP/.venv/Scripts/pyrit-mcp.exe",
      "env": {
        "PYRIT_SANDBOX_MODE": "true",
        "ATTACKER_BACKEND": "ollama",
        "ATTACKER_BASE_URL": "http://localhost:11434",
        "ATTACKER_MODEL": "dolphin-mistral",
        "SCORER_BACKEND": "substring"
      }
    }
  }
}
```

**macOS / Linux:**
```json
{
  "mcpServers": {
    "pyrit": {
      "command": "/path/to/Pyrit-MCP/.venv/bin/pyrit-mcp",
      "env": {
        "PYRIT_SANDBOX_MODE": "true",
        "ATTACKER_BACKEND": "ollama",
        "ATTACKER_BASE_URL": "http://localhost:11434",
        "ATTACKER_MODEL": "dolphin-mistral",
        "SCORER_BACKEND": "substring"
      }
    }
  }
}
```

#### Option B: Using Python module directly

If the `pyrit-mcp` CLI entry point is not available, run the module directly:

```json
{
  "mcpServers": {
    "pyrit": {
      "command": "python",
      "args": ["-m", "pyrit_mcp.server"],
      "env": {
        "PYRIT_SANDBOX_MODE": "true",
        "ATTACKER_BACKEND": "ollama",
        "ATTACKER_BASE_URL": "http://localhost:11434",
        "ATTACKER_MODEL": "dolphin-mistral",
        "SCORER_BACKEND": "substring"
      }
    }
  }
}
```

> **Windows venv tip:** When using `"command": "python"`, ensure the venv is
> activated in your terminal, or use the full path:
> `"command": "C:/path/to/Pyrit-MCP/.venv/Scripts/python.exe"`

#### Option C: Using Docker

```json
{
  "mcpServers": {
    "pyrit": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "C:/path/to/Pyrit-MCP/.env",
        "-v", "pyrit-db:/data",
        "ghcr.io/ncasfl/pyrit-mcp:latest"
      ]
    }
  }
}
```

### Step 3 — Verify in Claude Code

1. Open the Claude Code panel in VS Code
2. The PyRIT tools should appear in the available tools list
3. Test with a prompt like:

   > "List all available PyRIT tools and show me the built-in datasets."

---

## VS Code Setup — GitHub Copilot (MCP)

GitHub Copilot in VS Code supports MCP servers starting with the **Copilot Chat agent mode** (VS Code 1.99+).

### Step 1 — Enable MCP support

1. Open VS Code Settings (`Ctrl+,` / `Cmd+,`)
2. Search for `chat.mcp.enabled`
3. Set it to **true**

Alternatively, add to your `settings.json`:

```json
{
  "chat.mcp.enabled": true
}
```

### Step 2 — Configure the MCP server

GitHub Copilot reads MCP server configuration from `.vscode/mcp.json` in your workspace.

Create `.vscode/mcp.json`:

```json
{
  "servers": {
    "pyrit": {
      "type": "stdio",
      "command": "pyrit-mcp",
      "env": {
        "PYRIT_SANDBOX_MODE": "true",
        "PYRIT_LOG_LEVEL": "INFO",
        "PYRIT_DB_PATH": "./pyrit_data.db",
        "ATTACKER_BACKEND": "ollama",
        "ATTACKER_BASE_URL": "http://localhost:11434",
        "ATTACKER_MODEL": "dolphin-mistral",
        "SCORER_BACKEND": "substring"
      }
    }
  }
}
```

**With a virtual environment (Windows):**

```json
{
  "servers": {
    "pyrit": {
      "type": "stdio",
      "command": "C:/path/to/Pyrit-MCP/.venv/Scripts/pyrit-mcp.exe",
      "env": {
        "PYRIT_SANDBOX_MODE": "true",
        "ATTACKER_BACKEND": "ollama",
        "ATTACKER_BASE_URL": "http://localhost:11434",
        "ATTACKER_MODEL": "dolphin-mistral",
        "SCORER_BACKEND": "substring"
      }
    }
  }
}
```

**With a virtual environment (macOS / Linux):**

```json
{
  "servers": {
    "pyrit": {
      "type": "stdio",
      "command": "/path/to/Pyrit-MCP/.venv/bin/pyrit-mcp",
      "env": {
        "PYRIT_SANDBOX_MODE": "true",
        "ATTACKER_BACKEND": "ollama",
        "ATTACKER_BASE_URL": "http://localhost:11434",
        "ATTACKER_MODEL": "dolphin-mistral",
        "SCORER_BACKEND": "substring"
      }
    }
  }
}
```

**With Docker:**

```json
{
  "servers": {
    "pyrit": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "${workspaceFolder}/.env",
        "-v", "pyrit-db:/data",
        "ghcr.io/ncasfl/pyrit-mcp:latest"
      ]
    }
  }
}
```

### Step 3 — Verify in Copilot Chat

1. Open Copilot Chat (`Ctrl+Shift+I` / `Cmd+Shift+I`)
2. Switch to **Agent** mode (click the mode dropdown at the top of the chat panel)
3. You should see PyRIT tools listed under available tools
4. Test with:

   > "Use the PyRIT MCP server to list all built-in adversarial datasets."

> **Important:** MCP tools in Copilot require **Agent mode** — they do not work
> in the standard Chat or Inline Chat modes.

---

## Claude Desktop Setup

If you prefer Claude Desktop over VS Code, configure the MCP server in Claude Desktop's config file.

### Locate the config file

| Platform | Path |
|----------|------|
| macOS    | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows  | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux    | `~/.config/Claude/claude_desktop_config.json` |

### Add the server configuration

#### Using the installed Python package:

```json
{
  "mcpServers": {
    "pyrit": {
      "command": "pyrit-mcp",
      "env": {
        "PYRIT_SANDBOX_MODE": "true",
        "ATTACKER_BACKEND": "ollama",
        "ATTACKER_BASE_URL": "http://localhost:11434",
        "ATTACKER_MODEL": "dolphin-mistral",
        "SCORER_BACKEND": "substring"
      }
    }
  }
}
```

> Use the full path to `pyrit-mcp` if it is not on your system PATH
> (e.g., `C:/path/to/Pyrit-MCP/.venv/Scripts/pyrit-mcp.exe`).

#### Using Docker:

```json
{
  "mcpServers": {
    "pyrit": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "/absolute/path/to/Pyrit-MCP/.env",
        "-v", "pyrit-db:/data",
        "-v", "/absolute/path/to/Pyrit-MCP/datasets:/datasets",
        "ghcr.io/ncasfl/pyrit-mcp:latest"
      ]
    }
  }
}
```

> **Critical flags:**
> - `--rm` — removes the container after the session ends
> - `-i` — keeps stdin open for stdio transport (**required**)
> - Do **NOT** add `-t` — this breaks the MCP stdio protocol

### Restart Claude Desktop

After saving the config file, fully quit and reopen Claude Desktop.
The PyRIT tools should appear in the tool picker (hammer icon).

---

## Docker Setup (Alternative)

If you prefer not to install Python dependencies locally, run the server entirely in Docker.

### Build the image

```bash
cd Pyrit-MCP
docker build -f docker/Dockerfile -t pyrit-mcp:latest .
```

### Run standalone (for testing)

```bash
docker run --rm -i --env-file .env pyrit-mcp:latest
```

### Run with Docker Compose (full stack with Ollama)

```bash
# CPU-only local inference
docker compose up

# With NVIDIA GPU acceleration
docker compose --profile local-llm-gpu up

# See README.md for all available profiles
```

---

## Troubleshooting

### "pyrit-mcp" is not recognized / command not found

**Cause:** The CLI entry point is not on your PATH.

**Fix:**
```bash
# Activate your virtual environment first:
source .venv/bin/activate        # macOS/Linux
.\.venv\Scripts\Activate.ps1     # Windows PowerShell

# Or use the full path in your MCP config:
# Windows: C:/path/to/Pyrit-MCP/.venv/Scripts/pyrit-mcp.exe
# macOS/Linux: /path/to/Pyrit-MCP/.venv/bin/pyrit-mcp
```

### Server starts but tools don't appear in VS Code

1. Check the server logs in the VS Code output panel (look for "MCP" or "pyrit")
2. Ensure you are using the correct config file location:
   - Claude Code: `.mcp.json` in project root
   - GitHub Copilot: `.vscode/mcp.json`
3. Restart VS Code after changing config files
4. Verify the Python/pyrit-mcp path in the config matches your environment

### Configuration errors on startup

```
[pyrit-mcp] Configuration errors detected.
```

Check your `.env` file against `.env.example`. Common issues:
- Missing required variables (`ATTACKER_BACKEND`, `ATTACKER_MODEL`)
- Invalid backend type (must be one of: `ollama`, `openai`, `azure`, `llamacpp`, `groq`, `lmstudio`)
- Unreachable backend URL (e.g., Ollama not running)

### ModuleNotFoundError: No module named 'pyrit_mcp'

**Cause:** The package is not installed in the Python environment being used.

**Fix:**
```bash
# Ensure you're in the right venv:
which python      # macOS/Linux
where python      # Windows

# Reinstall:
pip install -e .
```

### Permission denied (Windows)

If you get permission errors running `pyrit-mcp.exe`:

1. Run VS Code as administrator (one-time test)
2. Or adjust your execution policy:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### Docker: MCP protocol errors / garbled output

- Ensure you are using `-i` (interactive) but **not** `-t` (pseudo-TTY)
- `-t` injects terminal control characters that break the JSON-RPC protocol
- Correct: `docker run --rm -i ...`
- Wrong: `docker run --rm -it ...`

### Copilot MCP tools not showing

- MCP tools only work in **Agent mode**, not in Chat or Inline Chat
- Ensure `chat.mcp.enabled` is `true` in VS Code settings
- Check the VS Code output panel for MCP-related errors
- You may need VS Code 1.99 or newer

---

## Verifying Your Installation

Run through this checklist to confirm everything is working:

```bash
# 1. Python environment
python --version          # Should be 3.10+
pip show pyrit-mcp        # Should show version 0.1.0

# 2. Server starts
pyrit-mcp                 # Should print startup logs to stderr; Ctrl+C to stop

# 3. Tests pass
pytest tests/ -x -q       # Should show all tests passing

# 4. Linting is clean
ruff check .              # No errors
mypy pyrit_mcp/           # No errors
```

Then in your IDE:
1. Open the MCP-enabled chat interface
2. Ask: *"List all available PyRIT tools"*
3. You should see a response listing 42 tools across 7 domains

---

## Uninstalling

### Remove the Python package

```bash
pip uninstall pyrit-mcp
```

### Remove the virtual environment

```bash
# Delete the .venv directory
rm -rf .venv              # macOS/Linux
rmdir /s /q .venv         # Windows CMD
```

### Remove MCP configuration

Delete the PyRIT entry from your MCP config file:
- Claude Code: Remove the `"pyrit"` key from `.mcp.json`
- GitHub Copilot: Remove the `"pyrit"` key from `.vscode/mcp.json`
- Claude Desktop: Remove the `"pyrit"` key from `claude_desktop_config.json`

### Remove Docker artifacts (if used)

```bash
docker rmi pyrit-mcp:latest
docker volume rm pyrit-db
```
