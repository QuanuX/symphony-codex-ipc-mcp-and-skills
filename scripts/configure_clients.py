#!/usr/bin/env python3
"""Emit a new local MCP client fragment without editing an existing config.

Only POSIX local installations are described by this Alpha. No subprocess,
network request, shell command, secret, or existing host configuration is read.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import PurePosixPath
import sys
from typing import Sequence


def absolute_path(value: str) -> str:
    if not value.startswith("/") or value == "/":
        raise argparse.ArgumentTypeError("use an absolute POSIX file or socket path")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise argparse.ArgumentTypeError("paths must not contain control characters")
    if ".." in PurePosixPath(value).parts:
        raise argparse.ArgumentTypeError("paths must not contain parent traversal")
    return value


def connection(client: str, binary: str, argument: str, target: str, catalog: str | None = None) -> dict:
    server = {"command": binary, "args": [argument, target] + (["--tool-catalog", catalog] if catalog else [])}
    if client == "claude":
        server = {"type": "stdio", **server}
    return {"mcpServers": {"symphony": server}}


def render(client: str, binary: str, argument: str, target: str, catalog: str | None = None) -> str:
    profile = connection(client, binary, argument, target, catalog)
    if client != "codex":
        return json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
    # JSON basic string escaping is also valid for these TOML basic strings.
    command = json.dumps(binary, ensure_ascii=False)
    arguments = json.dumps(profile["mcpServers"]["symphony"]["args"], ensure_ascii=False)
    return (
        "[mcp_servers.symphony]\n"
        f"command = {command}\n"
        f"args = {arguments}\n"
        "startup_timeout_sec = 70\n"
        "tool_timeout_sec = 70\n"
        'default_tools_approval_mode = "writes"\n'
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("codex", "claude", "antigravity", "generic"), required=True)
    parser.add_argument("--binary", type=absolute_path, required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--config", type=absolute_path)
    target.add_argument("--connect-socket", type=absolute_path)
    parser.add_argument("--output", help="create a new private file; refuse an existing path")
    parser.add_argument("--tool-catalog", type=absolute_path, help="Packaged operation catalogue; configure this on an IPC server, not its relay")
    args = parser.parse_args(argv)
    argument, selected = ("--config", args.config) if args.config is not None else ("--connect-socket", args.connect_socket)
    if args.tool_catalog and args.connect_socket:
        parser.error("Configure the catalogue on the IPC server, not its relay")
    result = render(args.client, args.binary, argument, selected, args.tool_catalog)
    if args.output is None:
        sys.stdout.write(result)
        return 0
    try:
        # Exclusive creation also refuses symlinks. Never merge or truncate.
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(result)
    except OSError as error:
        parser.exit(1, f"Unable to create output: {error.strerror}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
