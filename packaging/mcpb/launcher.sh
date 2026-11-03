#!/bin/sh
# Select only an included, qualified executable. Never download or build at launch.
set -eu

bundle_dir=$(CDPATH= cd -P -- "$(dirname -- "$0")" && pwd)
system=$(uname -s)
machine=$(uname -m)
case "$system:$machine" in
    Darwin:x86_64) target=darwin-x86_64 ;;
    Darwin:arm64) target=darwin-arm64 ;;
    Linux:x86_64) target=linux-x86_64 ;;
    Linux:aarch64|Linux:arm64) target=linux-aarch64 ;;
    *)
        printf 'Symphony MCP: unsupported platform %s/%s. This bundle supports macOS and Linux on x86-64 and ARM64.\n' "$system" "$machine" >&2
        exit 64
        ;;
esac
binary="$bundle_dir/bin/$target/symphony-mcp"
if [ ! -f "$binary" ] || [ ! -x "$binary" ]; then
    printf 'Symphony MCP: bundled executable is missing or not executable: %s\n' "$binary" >&2
    exit 66
fi
exec "$binary" "$@"
