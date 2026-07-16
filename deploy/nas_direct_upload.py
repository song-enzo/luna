#!/usr/bin/env python3
import argparse
import os
import posixpath
import stat
import sys
import time
from pathlib import Path

import paramiko


EXCLUDED_DIRS = {
    ".git",
    ".agents",
    ".codex",
    ".cc-connect",
    ".claude",
    ".codex-remote-attachments",
    ".service-logs",
    ".venv",
    ".vscode",
    "__pycache__",
    "backups",
    "downloads",
    "_data",
}

EXCLUDED_PREFIXES = (
    "bak_",
    "_corrupt_html_backup_",
)

EXCLUDED_FILES = {
    ".cloudflared_tunnel.log",
    ".luna-session-secret",
    ".tunnel_output.log",
    "local_config.json",
    "test.txt",
    "test_gemini_key.py",
}

EXCLUDED_SUFFIXES = (
    ".bak",
    ".db",
    ".encbak",
    ".encbak2",
    ".log",
    ".pyc",
    ".sqlite",
    ".sqlite3",
    ".tmp",
)


def should_skip(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    parts = rel.split("/")
    name = path.name

    if any(part in EXCLUDED_DIRS for part in parts):
        return True
    if any(name.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return True
    if name in EXCLUDED_FILES:
        return True
    if name.startswith("test_out") and name.endswith(".html"):
        return True
    if name in {"test_final.html", "test_mobile.html", "served_check.html"}:
        return True
    if name.endswith(EXCLUDED_SUFFIXES) and not (name.startswith("luna") and (".db" in name or name.endswith(".db"))):
        return True
    return False


def collect_files(root: Path) -> list[Path]:
    files = []
    for current_root, dirs, names in os.walk(root):
        current = Path(current_root)
        dirs[:] = [
            d for d in dirs
            if not should_skip(current / d, root)
        ]
        for name in names:
            path = current / name
            if not should_skip(path, root):
                files.append(path)
    return sorted(files)


def remote_exists(sftp: paramiko.SFTPClient, path: str) -> bool:
    try:
        sftp.stat(path)
        return True
    except FileNotFoundError:
        return False


def ensure_remote_dir(sftp: paramiko.SFTPClient, path: str) -> None:
    parts = []
    while path not in ("", "/"):
        parts.append(path)
        path = posixpath.dirname(path)
    for folder in reversed(parts):
        if not remote_exists(sftp, folder):
            sftp.mkdir(folder)


def run(ssh: paramiko.SSHClient, command: str, check: bool = True, password: str | None = None) -> tuple[int, str, str]:
    stdin, stdout, stderr = ssh.exec_command(command)
    if password is not None:
        stdin.write(password + "\n")
        stdin.flush()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    code = stdout.channel.recv_exit_status()
    if check and code != 0:
        raise RuntimeError(f"Command failed ({code}): {command}\n{err or out}")
    return code, out, err


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--remote-dir", default="/opt/data/luna")
    parser.add_argument("--restart-container", default="luna-services")
    args = parser.parse_args()

    root = Path.cwd().resolve()
    files = collect_files(root)
    if not files:
        print("No files selected for upload.")
        return 1

    print(f"Selected {len(files)} files from {root}")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        args.host,
        port=args.port,
        username=args.user,
        password=args.password,
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
    )

    try:
        run(ssh, f"test -d {args.remote_dir!r}")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = f"/tmp/luna-code-backup-{stamp}.tgz"
        backup_cmd = (
            f"tar -C {posixpath.dirname(args.remote_dir)!r} "
            f"--exclude='luna/.venv' --exclude='luna/.git' "
            f"-czf {backup!r} {posixpath.basename(args.remote_dir)!r}"
        )
        run(ssh, backup_cmd)
        print(f"Remote backup created: {backup}")

        sftp = ssh.open_sftp()
        try:
            for index, local in enumerate(files, start=1):
                rel = local.relative_to(root).as_posix()
                remote = posixpath.join(args.remote_dir, rel)
                ensure_remote_dir(sftp, posixpath.dirname(remote))
                sftp.put(str(local), remote)
                mode = local.stat().st_mode
                if mode & stat.S_IXUSR:
                    sftp.chmod(remote, 0o755)
                if index % 25 == 0 or index == len(files):
                    print(f"Uploaded {index}/{len(files)}")
        finally:
            sftp.close()

        try:
            run(ssh, f"docker restart {args.restart_container!r}")
        except RuntimeError:
            run(ssh, f"sudo -S docker restart {args.restart_container!r}", password=args.password)
        code, out, err = run(
            ssh,
            "sleep 3; curl -s -o /dev/null -w '%{http_code}' http://localhost:8766/",
            check=False,
        )
        print(f"Container restarted: {args.restart_container}")
        print(f"Local NAS HTTP status: {(out or err).strip() or 'unknown'}")
    finally:
        ssh.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
