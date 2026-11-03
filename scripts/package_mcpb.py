#!/usr/bin/env python3
"""Build a deterministic native MCPB and pinned registry metadata; never publish."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import tempfile
from urllib.parse import urlsplit
import zipfile

VERSION = "0.1.0-alpha.1"
SERVER_NAME = "io.github.QuanuX/symphony"
REPOSITORY = "https://github.com/QuanuX/symphony-codex-ipc-mcp-and-skills"
TARGETS = ("darwin-x86_64", "darwin-arm64", "linux-x86_64", "linux-aarch64")
SOURCE_FILES = {"README.md", "LICENSE", "CMakeLists.txt", "plugin.json", "mcp.json", ".mcp.json", ".gitignore"}
SOURCE_DIRS = {"src", "include", "third_party", "scripts", "tests", "skills", "docs", "adapters", ".claude-plugin", ".codex-plugin", "assets", "packaging"}
FORBIDDEN_PARTS = {"private", "evidence", "test-results", ".git", ".venv", "__pycache__"}
MAX_FILE_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_member(name):
    path = PurePosixPath(name)
    if not name or "\\" in name or path.is_absolute() or any(p in (".", "..", "") for p in name.split("/")):
        raise ValueError("Unsafe archive path: " + repr(name))
    if any(p.lower() in FORBIDDEN_PARTS for p in path.parts):
        raise ValueError("Private/build path cannot be packaged: " + name)
    if path.name in {"connection.json", ".env", ".mcpregistry_token"} or path.suffix in {".pem", ".key", ".pyc"}:
        raise ValueError("Connection profile or credential path cannot be packaged: " + name)
    return path


def read_regular(path, root=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Expected a regular, non-symlink file: " + str(path))
    if root is not None:
        relative = path.relative_to(root)
        cursor = root
        for part in relative.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ValueError("Symlink cannot be packaged: " + str(cursor))
        path.resolve().relative_to(root.resolve())
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("File exceeds MCPB size limit: " + str(path))
    return path.read_bytes()


def validate_binary(data, target):
    """Check the supplied platform label against the executable header, not its name."""
    if target.startswith("darwin-"):
        expected = 0x01000007 if target.endswith("x86_64") else 0x0100000C
        if len(data) < 32 or data[:4] != b"\xcf\xfa\xed\xfe" or struct.unpack_from("<I", data, 4)[0] != expected:
            raise ValueError("Expected a 64-bit little-endian Mach-O executable for " + target)
        if struct.unpack_from("<I", data, 12)[0] != 2:
            raise ValueError("Mach-O input must be an executable for " + target)
    else:
        expected = 62 if target.endswith("x86_64") else 183
        if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", data, 18)[0] != expected:
            raise ValueError("Expected a 64-bit little-endian ELF executable for " + target)
        if struct.unpack_from("<H", data, 16)[0] not in (2, 3):
            raise ValueError("ELF input must be an executable or PIE for " + target)


def binary_inputs(values):
    result = {}
    for value in values:
        target, separator, filename = value.partition("=")
        if not separator or target not in TARGETS or target in result or not filename:
            raise ValueError("Supply each --binary TARGET=PATH exactly once; targets: " + ", ".join(TARGETS))
        path = Path(filename).absolute()
        data = read_regular(path)
        if not path.stat().st_mode & 0o111:
            raise ValueError("Input binary is not executable: " + str(path))
        validate_binary(data, target)
        result[target] = data
    if set(result) != set(TARGETS):
        raise ValueError("All four qualified target binaries are required: " + ", ".join(TARGETS))
    return result


def git(root, *arguments):
    return subprocess.check_output(["git", "-C", str(root), *arguments], stderr=subprocess.PIPE)


def collect_source(root):
    root = root.resolve()
    if Path(git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != root:
        raise ValueError("--source-root must be the standalone repository root")
    members = {}
    tracked = git(root, "ls-files", "--cached", "-z").decode().split("\0")
    for name in sorted(filter(None, tracked)):
        path = safe_member(name)
        if name not in SOURCE_FILES and path.parts[0] not in SOURCE_DIRS:
            continue
        data = read_regular(root / name, root)
        # Profiles must never be shipped, even when renamed or accidentally tracked.
        if data.lstrip().startswith(b"{"):
            try:
                document = json.loads(data)
            except (UnicodeDecodeError, json.JSONDecodeError):
                document = None
            if isinstance(document, dict) and document.get("schema") == "symphony.agent.connection.v1":
                raise ValueError("Connection profile cannot be packaged: " + name)
        if re.search(rb"(?m)^-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----\r?$", data):
            raise ValueError("Private key cannot be packaged: " + name)
        members[name] = (data, 0o644)
    required = {"LICENSE", "CMakeLists.txt", "src/main.cpp", "src/transport.cpp", "include/symphony/transport.hpp", "third_party/nlohmann/json.hpp", "third_party/nlohmann/LICENSE.MIT", "scripts/configure_connection.py", "skills/symphony-admin/SKILL.md", "skills/symphony-setup/SKILL.md", "packaging/mcpb/manifest.json", "packaging/mcpb/launcher.sh", "docs/mcp-registry.md"}
    missing = required - members.keys()
    if missing:
        raise ValueError("Required corresponding source/package files are not tracked: " + ", ".join(sorted(missing)))
    return members


def registry_metadata(release_url, sha256):
    parsed = urlsplit(release_url)
    prefix = "/QuanuX/symphony-codex-ipc-mcp-and-skills/releases/download/"
    if parsed.scheme != "https" or parsed.netloc != "github.com" or not parsed.path.startswith(prefix) or not parsed.path.endswith(".mcpb") or parsed.query or parsed.fragment:
        raise ValueError("--release-url must be an exact public .mcpb release URL in " + REPOSITORY)
    suffix = parsed.path[len(prefix):]
    if len(suffix.split("/")) != 2 or not all(suffix.split("/")) or any(c.isspace() for c in release_url):
        raise ValueError("--release-url must contain one release tag and one asset filename")
    return {
        "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
        "name": SERVER_NAME,
        "title": "Symphony",
        "description": "Inspect and administer a configured Symphony installation through its qxctl contracts.",
        "version": VERSION,
        "repository": {"url": REPOSITORY, "source": "github"},
        "websiteUrl": REPOSITORY + "#readme",
        "packages": [{"registryType": "mcpb", "identifier": release_url, "version": VERSION,
                      "fileSha256": sha256, "transport": {"type": "stdio"}}],
    }


def build(args):
    binaries = binary_inputs(args.binary)
    root = args.source_root.resolve()
    members = collect_source(root)
    manifest = json.loads(members["packaging/mcpb/manifest.json"][0])
    if manifest["version"] != VERSION or manifest["server"]["mcp_config"] != {
        "command": "/bin/sh", "args": ["${__dirname}/launcher.sh", "--config", "${user_config.connection_profile}"]
    }:
        raise ValueError("Unexpected manifest version or launch configuration")
    members["manifest.json"] = (members["packaging/mcpb/manifest.json"][0], 0o644)
    members["launcher.sh"] = (members["packaging/mcpb/launcher.sh"][0], 0o755)
    for target, data in binaries.items():
        members[f"bin/{target}/symphony-mcp"] = (data, 0o755)
    if len(members) > 5000 or sum(len(data) for data, _ in members.values()) > MAX_TOTAL_BYTES:
        raise ValueError("Archive exceeds entry or expanded-size limit")
    registry_metadata(args.release_url, "0" * 64)  # Validate before creating artifacts.
    output = args.output.absolute()
    if output.suffix != ".mcpb":
        raise ValueError("--output must end in .mcpb")
    sidecars = [output.with_suffix(output.suffix + ".sha256"), output.with_suffix(".server.json"), output.with_suffix(".package.json")]
    for destination in [output, *sidecars]:
        if destination.exists() or destination.is_symlink():
            raise ValueError("Refusing to replace an existing artifact: " + str(destination))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, prefix=".mcpb-", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, (data, mode) in sorted(members.items()):
                safe_member(name)
                info = zipfile.ZipInfo(name, (2026, 11, 2, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        if temporary.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Compressed MCPB exceeds 100 MiB")
        package_hash = digest(temporary.read_bytes())
        metadata = registry_metadata(args.release_url, package_hash)
        receipt = {
            "artifact": output.name, "sha256": package_hash, "version": VERSION,
            "source_commit": git(root, "rev-parse", "HEAD").decode().strip(),
            "source_files_match_commit": not bool(git(root, "diff", "--name-only", "HEAD", "--", *sorted(name for name in members if name not in {"manifest.json", "launcher.sh"} and not name.startswith("bin/"))).strip()),
            "source_revision_note": "source_commit is repository HEAD; source_sha256 binds the exact included contents, including any staged or working changes when source_files_match_commit is false.",
            "binary_sha256": {target: digest(data) for target, data in sorted(binaries.items())},
            "source_sha256": {name: digest(data) for name, (data, _) in sorted(members.items()) if not name.startswith("bin/")},
            "files": len(members), "compressed_bytes": temporary.stat().st_size,
            "expanded_bytes": sum(len(data) for data, _ in members.values()),
            "published": False,
            "qualification_note": "Header/architecture and archive checks do not prove runtime qualification or binary-to-source correspondence. Retain the build/test provenance for each input binary.",
        }
        # Hard-link creation is atomic and fails rather than clobbering an existing release.
        os.link(temporary, output)
        for destination, content in zip(sidecars, [package_hash + "  " + output.name + "\n", json.dumps(metadata, indent=2) + "\n", json.dumps(receipt, indent=2) + "\n"]):
            with destination.open("x") as stream:
                stream.write(content)
        return receipt
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--binary", required=True, action="append", metavar="TARGET=PATH")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--release-url", required=True)
    args = parser.parse_args()
    try:
        receipt = build(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
