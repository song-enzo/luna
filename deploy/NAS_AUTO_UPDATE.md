# LUNA NAS Auto Update

This deploys the flow:

1. Local computer commits and pushes to GitHub.
2. NAS checks `origin/main` once per minute.
3. If a new commit exists, NAS runs `git pull --ff-only`.
4. NAS restarts LUNA with `luna-service.sh restart`.

The scripts protect tracked runtime data with `git update-index --skip-worktree`:

- `luna.db`
- existing tracked files under `photos/`

## One-time NAS install

SSH to the NAS:

```bash
ssh -p 10000 15325516180@192.168.1.22
```

Then run:

```bash
cd /opt/data
git clone https://github.com/song-enzo/luna.git luna
cd /opt/data/luna
chmod +x deploy/nas-install-autoupdate.sh
./deploy/nas-install-autoupdate.sh
```

If `/opt/data/luna` already exists and is already a Git checkout, run only:

```bash
cd /opt/data/luna
git pull --ff-only origin main
chmod +x deploy/nas-install-autoupdate.sh
./deploy/nas-install-autoupdate.sh
```

## Normal local workflow

On the local computer:

```bash
git status
git add deploy/nas-auto-update.sh deploy/nas-install-autoupdate.sh deploy/NAS_AUTO_UPDATE.md
git commit -m "Update LUNA"
git push origin main
```

Within about one minute, the NAS pulls the commit and restarts the site.

Avoid committing `luna.db`, `luna.db-shm`, `luna.db-wal`, or new runtime uploads in `photos/` unless you intentionally want GitHub to carry that data.

## Check status on NAS

```bash
tail -n 80 /opt/data/luna/.service-logs/auto-update.log
sh /opt/data/luna/luna-service.sh status
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8766/
```

## Private repository note

If the GitHub repository is private, configure an SSH deploy key or a GitHub token on the NAS. Do not put a GitHub password in scripts.
