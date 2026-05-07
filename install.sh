#!/usr/bin/env bash
# Concerto installer
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/omri-alon/concerto/main/install.sh | bash
#   ./install.sh [--dir <install-dir>] [--ref <git-ref>] [--no-web]

set -euo pipefail

REPO_URL="${CONCERTO_REPO_URL:-https://github.com/omri-alon/concerto.git}"
INSTALL_DIR="${CONCERTO_DIR:-$HOME/.concerto}"
GIT_REF="${CONCERTO_REF:-main}"
WITH_WEB=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dir)    INSTALL_DIR="$2"; shift 2 ;;
        --ref)    GIT_REF="$2"; shift 2 ;;
        --no-web) WITH_WEB=0; shift ;;
        -h|--help)
            sed -n '2,5p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
done

log()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!! \033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31mxx \033[0m %s\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "missing required tool: $1"; }

need git
need python3

PY_VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
PY_OK=$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 11) else 0)')
[[ "$PY_OK" == "1" ]] || die "python >= 3.11 required (found $PY_VER)"

command -v claude >/dev/null 2>&1 || warn "Claude Code CLI ('claude') not found on PATH — Concerto needs it at runtime."
command -v sf     >/dev/null 2>&1 || warn "Salesforce CLI ('sf') not found on PATH — required for the GUS tracker."

log "Installing Concerto into $INSTALL_DIR (ref: $GIT_REF)"

if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "Repo exists — fetching updates"
    git -C "$INSTALL_DIR" fetch --tags origin
    git -C "$INSTALL_DIR" checkout "$GIT_REF"
    git -C "$INSTALL_DIR" pull --ff-only origin "$GIT_REF" 2>/dev/null || true
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    git -C "$INSTALL_DIR" checkout "$GIT_REF"
fi

VENV="$INSTALL_DIR/.venv"
if [[ ! -d "$VENV" ]]; then
    log "Creating virtualenv at $VENV"
    python3 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

log "Upgrading pip"
pip install --quiet --upgrade pip

if [[ "$WITH_WEB" == "1" ]]; then
    log "Installing concerto[web]"
    pip install --quiet -e "$INSTALL_DIR[web]"
else
    log "Installing concerto (no web extras)"
    pip install --quiet -e "$INSTALL_DIR"
fi

# Install a launcher on PATH
BIN_DIR="${CONCERTO_BIN_DIR:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"
LAUNCHER="$BIN_DIR/concerto"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec "$VENV/bin/concerto" "\$@"
EOF
chmod +x "$LAUNCHER"

log "Installed launcher at $LAUNCHER"

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) warn "$BIN_DIR is not on PATH — add this to your shell rc:"
       printf '    export PATH="%s:$PATH"\n' "$BIN_DIR" ;;
esac

log "Done. Try: concerto --help"
