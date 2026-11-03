#!/usr/bin/env python3
"""Verify and exercise the exact registry bundle using isolated qxctl fixtures."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--metadata", type=Path, default=Path("server.json"))
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text())
    assert hashlib.sha256(args.bundle.read_bytes()).hexdigest() == metadata["packages"][0]["fileSha256"]
    with tempfile.TemporaryDirectory(prefix="symphony mcpb check ") as directory:
        root = Path(directory)
        with zipfile.ZipFile(args.bundle) as archive:
            assert archive.testzip() is None
            names = set()
            assert sum(member.file_size for member in archive.infolist()) < 100_000_000
            for member in archive.infolist():
                path = PurePosixPath(member.filename)
                assert not path.is_absolute() and ".." not in path.parts and "\\" not in member.filename
                assert member.filename not in names
                names.add(member.filename)
                mode = member.external_attr >> 16
                assert stat.S_ISREG(mode), member.filename
                destination = root / member.filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(member))
                destination.chmod(0o755 if mode & 0o111 else 0o644)
        manifest = json.loads((root / "manifest.json").read_text())
        assert manifest["server"]["type"] == "binary"
        # The test suite supplies private exact-pinned fixture profiles; no real
        # Symphony installation, credentials or production state is used.
        subprocess.run([os.sys.executable, "tests/test_mcp.py", str(root / "launcher.sh")], check=True)
        print(json.dumps({"bundle_sha256": metadata["packages"][0]["fileSha256"], "platform": os.uname().sysname, "architecture": os.uname().machine, "exact_bundle_mcp_tests": "passed"}))


if __name__ == "__main__":
    main()
