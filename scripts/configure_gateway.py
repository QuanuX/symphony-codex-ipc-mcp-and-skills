#!/usr/bin/env python3
"""Create a new private, installation-bound gateway profile. Never starts it."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets


def create(args):
    root = args.output.resolve()
    root.mkdir(mode=0o700)  # exclusive; preserve existing configurations
    try:
        token_path = root / "notion-agent.token"
        with os.fdopen(os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
            f.write(secrets.token_urlsafe(48))
        tools = ["symphony_connection", "symphony_discover", "symphony_describe", "symphony_read"]
        if args.allow_writes:
            tools += ["symphony_prepare", "symphony_apply"]
        profile = {
            "schema": "symphony.agent.gateway.v1", "installation_id": args.installation,
            "port": args.port, "allowed_hosts": args.host,
            "allowed_origins": args.origin, "audit_file": str(root / "audit.jsonl"),
            "max_sessions": 1 if args.connect_socket else 8, "session_ttl_seconds": 600,
            "clients": [{"id": "notion-agent", "token_file": str(token_path),
                         "allowed_tools": tools, "allowed_commands": args.command}],
        }
        if args.connect_socket:
            profile["connect_socket"] = str(args.connect_socket.resolve())
        else:
            profile["connection_profile"] = str(args.connection.resolve(strict=True))
        with os.fdopen(os.open(root / "gateway.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as f:
            json.dump(profile, f, indent=2)
            f.write("\n")
        return {"profile": str(root / "gateway.json"), "credential_file": str(token_path),
                "started": False, "writes_enabled_at_gateway": args.allow_writes}
    except Exception:
        # Do not remove a directory that may contain operator changes.
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True, help="New private directory")
    p.add_argument("--installation", required=True)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--connection", type=Path)
    source.add_argument("--connect-socket", type=Path)
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", action="append", required=True, help="Exact Host including port if present")
    p.add_argument("--origin", action="append", default=[])
    p.add_argument("--command", action="append", default=[], help="Allowed command ID; explicit '*' allows all")
    p.add_argument("--allow-writes", action="store_true", help="Also requires enabled commands in local connection profile")
    args = p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", args.installation) or not 1024 <= args.port <= 65535:
        p.error("Invalid installation name or port")
    if "*" in args.host or "*" in args.origin or "null" in args.origin:
        p.error("Use explicit Hosts and Origins")
    print(json.dumps(create(args)))


if __name__ == "__main__":
    main()
