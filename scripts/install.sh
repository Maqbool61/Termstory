#!/bin/bash
# TermStory Installer v0.6.2

set -euo pipefail

echo "=== TermStory Installer v0.6.2 ==="

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
WORK_DIR=$(mktemp -d)

cleanup() { rm -rf "$WORK_DIR"; }
trap cleanup EXIT

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

  # Back up any existing venv so we can roll back on failure
  local backup=""
  if [ -d "$venv" ]; then
    backup=$(mktemp -d)
    mv "$venv" "$backup/termstory-venv"
  fi

  # On any failure below: restore backup (if any) and return 1
  _venv_fail() {
    local msg="$1"
    echo "  $msg"
    rm -rf "$venv"
    [ -n "$backup" ] && mv "$backup/termstory-venv" "$venv"
    [ -n "$backup" ] && rm -rf "$backup"
    return 1
  }

  if ! "$PYTHON" -m venv "$venv" 2>/dev/null; then
    _venv_fail "venv creation failed (is the venv module installed?)" || return 1
  fi

  local pip_rc=0
  "$venv/bin/pip" install --quiet "$SRC_DIR" 2>&1 || pip_rc=$?
  if [ "$pip_rc" -ne 0 ]; then
    _venv_fail "pip install failed (exit $pip_rc)." || return 1
  fi

  if ! "$venv/bin/python" -c "import termstory" 2>/dev/null; then
    _venv_fail "Package not importable after install." || return 1
  fi

  # Success — discard backup
  [ -n "$backup" ] && rm -rf "$backup"

  echo ""
  echo "  ✅ Installed in virtualenv."
  echo "  Run right now:"
  echo "    $venv/bin/termstory today"
  echo ""
  echo "  For permanent access, add to ~/.bashrc or ~/.zshrc:"
  echo '    export PATH="$HOME/.termstory-venv/bin:$PATH"'
  echo ""
}

install_user() {
  echo "  Trying --user install..."

  local pip_ver pip_rc=0
  pip_ver=$(pip_major_version)

  # --break-system-packages required on Debian/Ubuntu with pip >= 23
  if [ "$pip_ver" -ge 23 ]; then
    "$PYTHON" -m pip install --quiet --user --break-system-packages "$SRC_DIR" 2>&1 || pip_rc=$?
  else
    "$PYTHON" -m pip install --quiet --user "$SRC_DIR" 2>&1 || pip_rc=$?
  fi

  if [ "$pip_rc" -ne 0 ]; then
    echo "  pip install failed (exit $pip_rc)."
    return 1
  fi

  # Verify import — don't rely on __version__, it's not guaranteed to exist
  if ! "$PYTHON" -c "import termstory" 2>/dev/null; then
    echo "  Package not importable after user install."
    return 1
  fi

  # Locate the installed binary (Linux ~/.local/bin or macOS Library path)
  local bin_path
  bin_path=$(find \
    "$HOME/.local/bin" \
    "$HOME/Library/Python" \
    -name "termstory" -type f 2>/dev/null | head -1) || true

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
