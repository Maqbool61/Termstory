#!/bin/bash
# TermStory Installer v0.6.0

set -euo pipefail

echo "=== TermStory Installer v0.6.0 ==="

# ── Find Python ────────────────────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON="$cmd"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "❌ Python 3 not found. Please install it and re-run."
  exit 1
fi
echo "  Python: $($PYTHON --version)"
echo "  pip:    $($PYTHON -m pip --version 2>&1 | awk '{print $1, $2}')"

# ── Download & extract ─────────────────────────────────────────────────────────
WORK_DIR=$(mktemp -d)          # avoid shadowing the $TMPDIR env var

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT              # always clean up, success or failure

echo "  Downloading TermStory..."
if ! curl -fsSL \
    "https://github.com/bitflicker64/Termstory/archive/refs/heads/main.tar.gz" \
    -o "$WORK_DIR/termstory.tar.gz"; then
  echo "❌ Download failed. Check your internet connection."
  exit 1
fi

tar -xzf "$WORK_DIR/termstory.tar.gz" -C "$WORK_DIR"
SRC_DIR="$WORK_DIR/Termstory-main"

if [ ! -d "$SRC_DIR" ]; then
  echo "❌ Extracted archive doesn't contain expected directory: $SRC_DIR"
  exit 1
fi

# ── pip version helper ─────────────────────────────────────────────────────────
pip_major_version() {
  "$PYTHON" -c "import pip; print(int(pip.__version__.split('.')[0]))" 2>/dev/null || echo "0"
}

# ── Install strategies ─────────────────────────────────────────────────────────

install_venv() {
  local venv="$HOME/.termstory-venv"
  echo "  Trying venv install at $venv ..."

  # Remove a broken venv from a previous attempt
  [ -d "$venv" ] && rm -rf "$venv"

  if ! "$PYTHON" -m venv "$venv" 2>/dev/null; then
    echo "  venv creation failed (missing venv module?)"
    return 1
  fi

  "$venv/bin/pip" install --quiet "$SRC_DIR" 2>&1 | tail -3

  if "$venv/bin/python" -c "import termstory" 2>/dev/null; then
    echo ""
    echo "  ✅ Installed in virtualenv."
    echo "  Add this line to your ~/.bashrc or ~/.zshrc, then open a new terminal:"
    echo ""
    echo '    export PATH="$HOME/.termstory-venv/bin:$PATH"'
    echo ""
    echo "  Then run:  termstory today"
    return 0
  fi

  echo "  venv install didn't produce a working package."
  return 1
}

install_user() {
  echo "  Trying --user install..."

  local pip_ver
  pip_ver=$(pip_major_version)

  # --break-system-packages introduced in pip 23.0 (needed on Debian/Ubuntu 23+)
  if [ "$pip_ver" -ge 23 ] 2>/dev/null; then
    "$PYTHON" -m pip install --quiet --user --break-system-packages "$SRC_DIR" 2>&1 | tail -3
  else
    "$PYTHON" -m pip install --quiet --user "$SRC_DIR" 2>&1 | tail -3
  fi

  if ! "$PYTHON" -c "import termstory" 2>/dev/null; then
    echo "  User install didn't produce a working package."
    return 1
  fi

  # Locate the installed binary (Linux ~/.local/bin or macOS Library path)
  local bin_path
  bin_path=$(
    find \
      "$HOME/.local/bin" \
      "$HOME/Library/Python" \
      -name "termstory" -type f 2>/dev/null | head -1
  ) || true

  echo ""
  echo "  ✅ Installed."
  if [ -n "$bin_path" ]; then
    echo "  Binary: $bin_path"
    echo "  Run:    termstory today"
    echo "  (Ensure $(dirname "$bin_path") is in your PATH)"
  else
    echo "  Binary not found in standard locations."
    echo "  Run:    $PYTHON -m termstory.cli today"
  fi
  return 0
}

# ── Try venv first, then user, then give up ────────────────────────────────────
if ! install_venv && ! install_user; then
  echo ""
  echo "❌ All install strategies failed."
  echo "   Manual fallback:"
  echo "     git clone https://github.com/bitflicker64/Termstory.git"
  echo "     cd Termstory && pip install ."
  exit 1
fi
