#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${LUNA_APP_DIR:-/opt/data/luna}"
BRANCH="${LUNA_BRANCH:-main}"
LOG_DIR="${LUNA_LOG_DIR:-$APP_DIR/.service-logs}"
LOCK_FILE="${LUNA_LOCK_FILE:-/tmp/luna-auto-update.lock}"
SERVICE_SCRIPT="${LUNA_SERVICE_SCRIPT:-$APP_DIR/luna-service.sh}"

mkdir -p "$LOG_DIR"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG_DIR/auto-update.log"
}

protect_runtime_files() {
  cd "$APP_DIR"

  if git ls-files --error-unmatch luna.db >/dev/null 2>&1; then
    git update-index --skip-worktree luna.db || true
  fi

  if git ls-files --error-unmatch .service-logs/pids >/dev/null 2>&1; then
    git update-index --skip-worktree .service-logs/pids || true
  fi

  git ls-files photos | while IFS= read -r path; do
    [ -n "$path" ] || continue
    git update-index --skip-worktree "$path" || true
  done
}

restart_luna() {
  cd "$APP_DIR"

  if [ -x "$SERVICE_SCRIPT" ] || [ -f "$SERVICE_SCRIPT" ]; then
    sh "$SERVICE_SCRIPT" restart >> "$LOG_DIR/auto-update.log" 2>&1
    return
  fi

  fuser -k 8766/tcp >/dev/null 2>&1 || true
  nohup "$APP_DIR/.venv/bin/python" "$APP_DIR/luna_app.py" \
    >> "$LOG_DIR/flask.log" 2>&1 &
}

(
  flock -n 9 || exit 0

  if [ ! -d "$APP_DIR/.git" ]; then
    log "skip: $APP_DIR is not a git checkout"
    exit 1
  fi

  cd "$APP_DIR"
  protect_runtime_files

  old_head="$(git rev-parse HEAD)"
  git fetch --quiet origin "$BRANCH"
  new_head="$(git rev-parse "origin/$BRANCH")"

  if [ "$old_head" = "$new_head" ]; then
    exit 0
  fi

  log "updating $old_head -> $new_head"
  git pull --ff-only origin "$BRANCH" >> "$LOG_DIR/auto-update.log" 2>&1
  protect_runtime_files
  exec 9>&-
  restart_luna
  log "updated and restarted"
) 9>"$LOCK_FILE"
