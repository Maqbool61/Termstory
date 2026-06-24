#!/bin/bash
# TermStory Installer v0.6.1

set -euo pipefail

echo "=== TermStory Installer v0.6.1 ==="

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

# ── Helper: run pip and check its real exit code ───────────────────────────────
pip_install() {
  # Usage: pip_install <extra pip args...>
  # Runs pip install with given args, outputs stderr, returns pip's exit code.
  local pip_rc=0
  "$PYTHON" -m pip install --quiet "$@" 2>&1 || pip_rc=$?
  return $pip_rc
}

# ── Install strategies ─────────────────────────────────────────────────────────

install_venv() {
  local final_venv="$HOME/.termstory-venv"
  local staging_venv
  staging_venv=$(mktemp -d)/termstory-venv
  echo "  Trying venv install at $final_venv ..."

  # Build replacement in a staging location so we never destroy a working venv
  if ! "$PYTHON" -m venv "$staging_venv" 2>/dev/null; then
    echo "  venv creation failed (missing venv module?)"
    rm -rf "$staging_venv"
    return 1
  fi

  local pip_rc=0
  "$staging_venv/bin/pip" install --quiet "$SRC_DIR" 2>&1 || pip_rc=$?

  if [ "$pip_rc" -ne 0 ]; then
    echo "  pip install failed (exit $pip_rc)."
    rm -rf "$staging_venv"
    return 1
  fi

  if ! "$staging_venv/bin/python" -c "import termstory" 2>/dev/null; then
    echo "  Package not importable after install."
    rm -rf "$staging_venv"
    return 1
  fi

  # Atomically swap — only now do we destroy the old one
  rm -rf "$final_venv"
  mv "$staging_venv" "$final_venv"

  # Fix shebangs: mv doesn't update absolute interpreter paths in scripts
  sed -i '' "1s|^#!.*python[0-9.]*$|#!$final_venv/bin/python3|" "$final_venv/bin/"* 2>/dev/null || true

  echo ""
  echo "  ✅ Installed in virtualenv."
  echo "  Run right now:"
  echo "    $final_venv/bin/termstory today"
  echo ""
  echo "  For permanent access, add this line to ~/.bashrc or ~/.zshrc:"
  echo '    export PATH="$HOME/.termstory-venv/bin:$PATH"'
  echo ""
  return 0
}

install_user() {
  echo "  Trying --user install..."

  local pip_ver
  pip_ver=$(pip_major_version)

  local pip_rc=0
  # --break-system-packages introduced in pip 23.0 (needed on Debian/Ubuntu 23+)
  if [ "$pip_ver" -ge 23 ] 2>/dev/null; then
    pip_install --user --break-system-packages "$SRC_DIR" || pip_rc=$?
  else
    pip_install --user "$SRC_DIR" || pip_rc=$?
  fi

  if [ "$pip_rc" -ne 0 ]; then
    echo "  pip install failed (exit $pip_rc)."
    return 1
  fi

  # Verify import with the same Python that just installed it
  if ! "$PYTHON" -c "import termstory; print(termstory.__version__)" 2>/dev/null; then
    echo "  Package not importable after user install."
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
