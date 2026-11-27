#!/usr/bin/env python3
"""Helpers for uc-node's tests, and for test builds by hand.

Everything here is made in a directory the caller gives, with values from
the safe values register (uc-contracts, safe-values-and-substitutions): the
client example-org, the domain example.org, batches raw-1970-01-01-NN, the
key file example-org-raw-initial-id_ed25519. The passwords are made up here,
for tests only. Nothing reads ~/.secrets/ or ~/.private/.

As a script, it makes a whole test setup for an Incus build:

    python3 tests/helpers.py setup <directory> [--label raw] [--batch raw-1970-01-01-01]

which makes <directory>/secrets (a uc-node secrets root holding the batch),
<directory>/uc/example-org/uc-inventory (a client inventory holding
intake/<fqdn>.yml), and a throwaway SSH key, then prints the environment
and the scripts/build command to run. It prints no password and no hash.
"""
from __future__ import annotations

import argparse
import fcntl
import os
import select
import subprocess
import sys
import termios
import time
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

CLIENT = "example-org"
DOMAIN = "example.org"
BATCH = "raw-1970-01-01-01"
KEY_NAME = "example-org-raw-initial-id_ed25519"
# Made up for the tests only. The batch password is at least 15 characters
# (RN-ACC-08).
ROOT_PASSWORD = "made-up root password, tests only"
BATCH_PASSWORD = "made-up batch password, tests only"


def private_dir(path: Path) -> Path:
    """Make path and any missing parents, each mode 0700."""
    missing = []
    for directory in [path, *path.parents]:
        if directory.exists():
            break
        missing.append(directory)
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)
        directory.chmod(0o700)
    return path


def crypt_hash(password: str, salt: str | None = None) -> str:
    """SHA-512 crypt, as scripts/new-batch makes it, the password on stdin."""
    argv = ["openssl", "passwd", "-6"] + (["-salt", salt] if salt else []) + ["-stdin"]
    result = subprocess.run(argv, input=password + "\n", capture_output=True, text=True, check=True)
    return result.stdout.strip()


def hash_matches(password: str, value: str) -> bool:
    """Whether a $6$ hash was made from password."""
    parts = value.split("$")
    return len(parts) == 4 and parts[1] == "6" and crypt_hash(password, parts[2]) == value


def make_secrets_root(base: Path) -> Path:
    """A uc-node secrets root, base/secrets, with batches/, all mode 0700."""
    root = private_dir(base / "secrets")
    private_dir(root / "batches")
    return root


def make_batch(root: Path, batch: str = BATCH, root_password: str = ROOT_PASSWORD,
               batch_password: str = BATCH_PASSWORD) -> Path:
    """A batch file as scripts/new-batch writes it."""
    path = private_dir(root / "batches") / f"{batch}.yml"
    path.write_text(
        "---\n"
        f"root_password_hash: '{crypt_hash(root_password)}'\n"
        f"initial_password_hash: '{crypt_hash(batch_password)}'\n",
        encoding="utf-8",
    )
    path.chmod(0o600)
    return path


def make_client_inventory(base: Path, client: str = CLIENT) -> Path:
    """<base>/uc/<client>/uc-inventory, with intake/ and candidates/. The
    client folder is mode 0700, as guide 0 makes it."""
    client_dir = private_dir(base / "uc" / client)
    inventory = client_dir / "uc-inventory"
    for sub in ("intake", "candidates"):
        (inventory / sub).mkdir(parents=True, exist_ok=True)
    return inventory


def make_ssh_key(directory: Path) -> Path:
    """A throwaway ed25519 key pair, named as the register names it. Returns
    the path of the public key."""
    private = directory / KEY_NAME
    if not private.exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", KEY_NAME, "-f", str(private)],
                       check=True, capture_output=True)
    return private.with_suffix(".pub")


def node_definition(public_key: str, label: str = "raw", batch: str = BATCH, **extra) -> dict:
    data = {
        "client_domain": DOMAIN,
        "node_label": label,
        "platform": "incus",
        "initial_username": "initial",
        "ssh_public_key": public_key,
        "ssh_port": 22,
        "ssh_sources": [],
        "raw_node_batch": batch,
    }
    data.update(extra)
    return data


def write_node_definition(inventory: Path, data: dict) -> Path:
    path = inventory / "intake" / f"{data['node_label']}.{data['client_domain']}.yml"
    path.write_text("---\n" + yaml.safe_dump(data, sort_keys=False, width=80), encoding="utf-8")
    path.chmod(0o644)
    return path


def run_on_terminal(argv, answers, env=None, cwd=None, timeout=30):
    """Run argv with a pseudo-terminal as its controlling terminal, so
    getpass reads from it. answers is a list of (prompt, answer): each
    answer is typed once its prompt has appeared. Returns (status, output)."""
    master, slave = os.openpty()

    def make_controlling_terminal():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)

    process = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave, env=env, cwd=cwd,
                               preexec_fn=make_controlling_terminal, close_fds=True)
    os.close(slave)
    output = b""
    pending = list(answers)
    seen = 0
    deadline = time.monotonic() + timeout
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
            if pending:
                prompt, answer = pending[0]
                where = output.find(prompt.encode(), seen)
                if where >= 0:
                    seen = where + len(prompt)
                    os.write(master, answer.encode() + b"\n")
                    pending.pop(0)
            elif process.poll() is not None and not ready:
                break
        else:
            process.kill()
            raise TimeoutError(f"{argv} did not finish; output so far: {output.decode(errors='replace')}")
    finally:
        os.close(master)
    return process.wait(timeout=timeout), output.decode(errors="replace")


def setup(directory: Path, label: str, batch: str) -> None:
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    root = make_secrets_root(directory)
    make_batch(root, batch)
    inventory = make_client_inventory(directory)
    public = make_ssh_key(directory)
    data = node_definition(public.read_text().strip(), label=label, batch=batch)
    path = write_node_definition(inventory, data)
    print(f"Secrets root:      {root}")
    print(f"Client inventory:  {inventory}")
    print(f"Node definition:   {path}")
    print(f"SSH key:           {public.with_suffix('')}")
    print("\nRun, from the uc-node checkout:\n")
    print(f"  UC_NODE_SECRETS_DIR={root} scripts/build {inventory} {label}.{DOMAIN}")


def main(argv):
    parser = argparse.ArgumentParser(description="Make a test setup for an Incus build.")
    sub = parser.add_subparsers(dest="command", required=True)
    make = sub.add_parser("setup", help="make a secrets root, a client inventory and a node definition")
    make.add_argument("directory", type=Path)
    make.add_argument("--label", default="raw")
    make.add_argument("--batch", default=BATCH)
    args = parser.parse_args(argv)
    setup(args.directory, args.label, args.batch)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
