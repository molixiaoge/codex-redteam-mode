#!/usr/bin/env bash
# Codex Red Team Opt-In Mode — macOS/Linux installer launcher.
# Forwards all arguments to install.py.
# Usage: bash install.sh [--codex-home PATH] [--agents-home PATH] [--dry-run] [--uninstall]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_PY="$SCRIPT_DIR/install.py"

# Prefer python3, fall back to python
PYTHON_BIN=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "ERROR: No Python interpreter found (tried python3, python)." >&2
    exit 1
fi

exec "$PYTHON_BIN" "$INSTALL_PY" "$@"
