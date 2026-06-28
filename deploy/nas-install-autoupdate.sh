#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${LUNA_REPO_URL:-https://github.com/song-enzo/luna.git}"
APP_DIR="${LUNA_APP_DIR:-/opt/data/luna}"
BRANCH="${LUNA_BRANCH:-main}"
CRON_MARKER="# LUNA auto update from GitHub"
CRON_LINE="* * * * * LUNA_APP_DIR=$APP_DIR LUNA_BRANCH=$BRANCH bash $APP_DIR/deploy/nas-auto-update.sh >/dev/null 2>&1"

echo "Installing LUNA auto update"
echo "Repository: $REPO_URL"
echo "Directory:  $APP_DIR"
echo "Branch:     $BRANCH"

mkdir -p "$(dirname "$APP_DIR")"

if [ ! -d "$APP_DIR/.git" ]; then
  if [ -d "$APP_DIR" ] && [ "$(find "$APP_DIR" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ]; then
    echo "ERROR: $APP_DIR exists but is not a git checkout."
    echo "Move it aside first, or set LUNA_APP_DIR to a new directory."
    exit 1
  fi

  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
git remote set-url origin "$REPO_URL"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

chmod +x "$APP_DIR/deploy/nas-auto-update.sh" 2>/dev/null || true

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

tmp_cron="$(mktemp)"
crontab -l 2>/dev/null | grep -vF "$CRON_MARKER" | grep -vF "$APP_DIR/deploy/nas-auto-update.sh" > "$tmp_cron" || true
{
  cat "$tmp_cron"
  echo "$CRON_MARKER"
  echo "$CRON_LINE"
} | crontab -
rm -f "$tmp_cron"

mkdir -p "$APP_DIR/.service-logs"
bash "$APP_DIR/deploy/nas-auto-update.sh"

echo "Done. NAS will check GitHub every minute and restart LUNA after new commits."
