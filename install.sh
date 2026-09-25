#!/usr/bin/env bash
# install.sh - installs RetiPulse, a live LoRa status page for NomadNet.
#
# Run as the same user that runs NomadNet:   ./install.sh
# Optional overrides: SCRIPTS_DIR, PAGES_DIR, PYTHON
#
# Safe to re-run: the page and script are updated in place, and any unrelated
# page with the same name is backed up first.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="${SCRIPTS_DIR:-$HOME/scripts}"
PAGES_DIR="${PAGES_DIR:-$HOME/.nomadnetwork/storage/pages}"
PYTHON="${PYTHON:-$(command -v python3 || true)}"
STAMP="$(date +%Y%m%d-%H%M%S)"

say()  { printf '%s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# --- checks -----------------------------------------------------------
[ -n "$PYTHON" ] && [ -x "$PYTHON" ] || die "python3 not found. Install Python 3.9+ or set PYTHON=/full/path/to/python3"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
    || die "$PYTHON is older than 3.9 ($("$PYTHON" --version 2>&1))."
[ -d "$PAGES_DIR" ] || die "NomadNet pages folder not found at $PAGES_DIR. Set PAGES_DIR=/path/to/pages"

say "Python:         $PYTHON ($("$PYTHON" --version 2>&1))"
say "Scripts folder: $SCRIPTS_DIR"
say "Pages folder:   $PAGES_DIR"

# Reticulum config and rnstatus, found the same way the page will find them
CONFIG=""
for c in /etc/reticulum/config "$HOME/.config/reticulum/config" "$HOME/.reticulum/config"; do
    if [ -f "$c" ]; then CONFIG="$c"; break; fi
done
RNSTATUS="$(command -v rnstatus || true)"
[ -z "$RNSTATUS" ] && [ -x "$HOME/.local/bin/rnstatus" ] && RNSTATUS="$HOME/.local/bin/rnstatus"
say "Reticulum config: ${CONFIG:-not found}"
say "rnstatus:         ${RNSTATUS:-not found}"
[ -n "$CONFIG" ] || warn "No Reticulum config found. The page will say it can't read the config."
[ -n "$RNSTATUS" ] || warn "rnstatus not found. The page will show settings only; set RNSTATUS_PATH in retipulse.py."
say ""

# --- script -----------------------------------------------------------
mkdir -p "$SCRIPTS_DIR"
if [ -f "$SCRIPTS_DIR/retipulse.py" ]; then
    cp "$SCRIPTS_DIR/retipulse.py" "$SCRIPTS_DIR/retipulse.py.bak.$STAMP"
    say "Backed up existing retipulse.py"
fi
"$PYTHON" - "$SRC/scripts/retipulse.py" "$SCRIPTS_DIR/retipulse.py" "$PYTHON" "$RNSTATUS" <<'PY'
import re, sys
src, dst, python, rnstatus = sys.argv[1:]
s = open(src, encoding="utf-8").read()
s = re.sub(r"^#!.*", lambda m: "#!" + python, s, count=1)
if rnstatus:   # pages run without your login PATH, so save the full path
    s = re.sub(r"^RNSTATUS_PATH = .*$", lambda m: f"RNSTATUS_PATH = {rnstatus!r}", s, count=1, flags=re.M)
open(dst, "w", encoding="utf-8").write(s)
PY
chmod +x "$SCRIPTS_DIR/retipulse.py"
say "Installed $SCRIPTS_DIR/retipulse.py"

# --- page -------------------------------------------------------------
if [ -e "$PAGES_DIR/retipulse.mu" ] && ! grep -q "from retipulse import" "$PAGES_DIR/retipulse.mu"; then
    cp "$PAGES_DIR/retipulse.mu" "$SCRIPTS_DIR/retipulse.mu.backup.$STAMP"
    say "Backed up an unrelated retipulse.mu to $SCRIPTS_DIR/retipulse.mu.backup.$STAMP"
fi
"$PYTHON" - "$SRC/pages/retipulse.mu" "$PAGES_DIR/retipulse.mu" "$PYTHON" "$SCRIPTS_DIR" <<'PY'
import re, sys
src, dst, python, scripts_dir = sys.argv[1:]
s = open(src, encoding="utf-8").read()
s = re.sub(r"^#!.*", lambda m: "#!" + python, s, count=1)
s = re.sub(r"^SCRIPTS_DIR = .*$", lambda m: f"SCRIPTS_DIR = {scripts_dir!r}", s, count=1, flags=re.M)
open(dst, "w", encoding="utf-8").write(s)
PY
chmod +x "$PAGES_DIR/retipulse.mu"
say "Installed $PAGES_DIR/retipulse.mu"

# --- test run ---------------------------------------------------------
say ""
say "Test run (this is what the page will show):"
if OUT="$("$PAGES_DIR/retipulse.mu" 2>&1)"; then
    printf '%s\n' "$OUT" | head -24 || true
else
    printf '%s\n' "$OUT" | tail -8 || true
    warn "Test run failed; see the error above."
fi

say ""
say "Done. Restart NomadNet so it picks up the new page, for example:"
say "    sudo systemctl restart nomadnet     (or your own service name / start method)"
say "Then visit /page/retipulse.mu on your node, and link to it from your home page:"
say '    `[LoRa Status`:/page/retipulse.mu]'
