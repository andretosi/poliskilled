"""Serve a production-configured preview behind Tailscale Serve in WSL."""

import argparse
import os
import secrets
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("hostname", help="The machine's Tailscale DNS name, without https://")
parser.add_argument("--port", type=int, default=8002)
args = parser.parse_args()

os.chdir(Path(__file__).resolve().parent.parent)
os.environ.update(
    DJANGO_DEBUG="0",
    POLISKILLED_DEMO="0",
    DJANGO_ALLOWED_HOSTS=f"{args.hostname},localhost,127.0.0.1",
    DJANGO_CSRF_ORIGINS=f"https://{args.hostname}",
)
# Ephemeral unless the caller supplies a production key; never print or persist it.
os.environ.setdefault("DJANGO_SECRET_KEY", secrets.token_urlsafe(48))
subprocess.run([sys.executable, "manage.py", "collectstatic", "--noinput"], check=True)
os.execv(
    sys.executable,
    [
        sys.executable,
        "-m",
        "gunicorn",
        "poliskilled.wsgi:application",
        "--bind",
        f"127.0.0.1:{args.port}",
        "--workers",
        "2",
    ],
)
