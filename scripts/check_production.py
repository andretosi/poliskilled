"""Check production settings using an ephemeral secret that is never printed or saved."""

import os
import secrets
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
environment = {
    **os.environ,
    "DJANGO_DEBUG": "0",
    "POLISKILLED_DEMO": "0",
    "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
}
subprocess.run(
    [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
    cwd=root,
    env=environment,
    check=True,
)
